from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_OFFLINE_BUNDLE_WRITER_SCHEMA_VERSION = "source_offline_bundle_writer_v1"
SOURCE_OFFLINE_BUNDLE_WRITER_SCOPE = (
    "local offline evidence bundle writer; writes only caller-supplied local/temp artifacts "
    "and metadata, performs no live capture, network, archive submission, or file movement"
)


class OfflineBundleStatus(str, Enum):
    WRITTEN = "written"
    FAILED = "failed"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(value: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(value), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(value), sort_keys=True, separators=(",", ":"))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in value) or "artifact"


@dataclass(frozen=True)
class OfflineBundleStoredEntry:
    entry_name: str
    sha256: str
    size_bytes: int
    source_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OfflineEvidenceBundleWriteResult:
    bundle_id: str
    status: OfflineBundleStatus
    output_name: str
    sha256: str
    size_bytes: int
    entries: tuple[OfflineBundleStoredEntry, ...]
    manifest_entry: str = "manifest.json"
    source_provenance_entry: str = "source_provenance.json"
    no_live_capture_performed: bool = True
    schema_version: str = SOURCE_OFFLINE_BUNDLE_WRITER_SCHEMA_VERSION
    scope: str = SOURCE_OFFLINE_BUNDLE_WRITER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["entry_count"] = len(self.entries)
        return data


def _json_bytes(value: Any) -> bytes:
    return (_stable_json(value, pretty=True) + "\n").encode("utf-8")


def _add_bytes(zip_file: zipfile.ZipFile, entries: list[OfflineBundleStoredEntry], name: str, payload: bytes, source_name: str = "") -> None:
    zip_file.writestr(name, payload)
    entries.append(
        OfflineBundleStoredEntry(
            entry_name=name,
            sha256=_sha256_bytes(payload),
            size_bytes=len(payload),
            source_name=source_name,
        )
    )


def write_offline_evidence_bundle(
    *,
    output_zip_path: str | Path,
    source_url: str,
    source_label: str = "",
    article_text: str = "",
    page_outline_text: str = "",
    html_snapshot: str = "",
    comments: Sequence[Mapping[str, Any]] = (),
    livechat: Sequence[Mapping[str, Any]] = (),
    selected_media_metadata: Sequence[Mapping[str, Any]] = (),
    archive_results: Sequence[Mapping[str, Any]] = (),
    screenshot_paths: Sequence[str | Path] = (),
    no_live_capture_performed: bool = True,
) -> OfflineEvidenceBundleWriteResult:
    output_path = Path(output_zip_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    entries: list[OfflineBundleStoredEntry] = []
    manifest = {
        "schema_version": SOURCE_OFFLINE_BUNDLE_WRITER_SCHEMA_VERSION,
        "source_label": source_label,
        "source_url": source_url,
        "entry_plan": [
            "source_provenance.json",
            "article/article_text.txt",
            "article/visible_page_outline.txt",
            "article/rendered_dom_snapshot.html",
            "comments/comments.json",
            "livechat/livechat.json",
            "media/selected_media_metadata.json",
            "archive/archive_results.json",
            "hashes.json",
            "viewer_manifest.json",
            "index.html",
        ],
        "no_live_capture_performed": bool(no_live_capture_performed),
        "user_review_required": True,
    }
    provenance = {
        "schema_version": "source_offline_bundle_provenance_v1",
        "source_label": source_label,
        "source_url": source_url,
        "provenance": "caller_supplied_local_fixture_or_operator_review_metadata",
        "network_performed": False,
        "archive_provider_call_performed": False,
        "file_movement_performed": False,
    }
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        _add_bytes(bundle, entries, "manifest.json", _json_bytes(manifest))
        _add_bytes(bundle, entries, "source_provenance.json", _json_bytes(provenance))
        _add_bytes(bundle, entries, "article/article_text.txt", article_text.encode("utf-8"))
        _add_bytes(bundle, entries, "article/visible_page_outline.txt", page_outline_text.encode("utf-8"))
        _add_bytes(bundle, entries, "article/rendered_dom_snapshot.html", html_snapshot.encode("utf-8"))
        _add_bytes(bundle, entries, "comments/comments.json", _json_bytes(list(comments)))
        _add_bytes(bundle, entries, "livechat/livechat.json", _json_bytes(list(livechat)))
        _add_bytes(bundle, entries, "media/selected_media_metadata.json", _json_bytes(list(selected_media_metadata)))
        _add_bytes(bundle, entries, "archive/archive_results.json", _json_bytes(list(archive_results)))
        for screenshot_path_value in screenshot_paths:
            screenshot_path = Path(screenshot_path_value)
            if not screenshot_path.is_file():
                continue
            payload = screenshot_path.read_bytes()
            _add_bytes(
                bundle,
                entries,
                f"screenshots/{_safe_name(screenshot_path.name)}",
                payload,
                source_name=screenshot_path.name,
            )
        hashes_payload = {
            "schema_version": "source_offline_bundle_hashes_v1",
            "entries": [entry.to_dict() for entry in entries],
        }
        _add_bytes(bundle, entries, "hashes.json", _json_bytes(hashes_payload))
        viewer = {
            "schema_version": "source_offline_bundle_viewer_manifest_v1",
            "source_label": source_label,
            "source_url": source_url,
            "entry_count": len(entries),
            "review_required": True,
        }
        _add_bytes(bundle, entries, "viewer_manifest.json", _json_bytes(viewer))
        index_html = (
            "<!doctype html><meta charset=\"utf-8\"><title>Source Evidence Bundle</title>"
            "<h1>Source Evidence Bundle</h1><p>Open viewer_manifest.json for metadata.</p>"
        )
        _add_bytes(bundle, entries, "index.html", index_html.encode("utf-8"))
    return OfflineEvidenceBundleWriteResult(
        bundle_id="offline_evidence_bundle_" + hashlib.sha256(output_path.read_bytes()).hexdigest()[:16],
        status=OfflineBundleStatus.WRITTEN,
        output_name=output_path.name,
        sha256=_sha256_bytes(output_path.read_bytes()),
        size_bytes=output_path.stat().st_size,
        entries=tuple(entries),
    )
