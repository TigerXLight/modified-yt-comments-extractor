from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from capture_msn_manual_capture_bundle import MSNManualCaptureBundle, msn_manual_capture_bundle_to_json
from total_export_manifest import (
    ASSET_EXTRACTED_TEXT,
    ASSET_JSON_EXPORT,
    ASSET_MANIFEST,
    ExportAsset,
    TotalExportManifest,
    manifest_filename,
    safe_package_id,
)


MSN_MANUAL_TOTAL_EXPORT_MANIFEST_SCHEMA_VERSION = "msn_manual_total_export_manifest_v1"

_SAFE_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")
_SECRET_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_json_bytes(value))


def _host_hint(url: str) -> str:
    host = re.sub(r"^https?://", "", str(url), flags=re.I).split("/", 1)[0].lower()
    return host[:80] or "unknown-host"


def _safe_name(value: str, *, field_name: str) -> str:
    text = safe_package_id(str(value or "").strip())
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    if _SECRET_RE.search(text) or _FULL_PATH_RE.search(text) or not _SAFE_PREFIX_RE.match(text):
        raise ValueError(f"unsafe {field_name}: {value!r}")
    return text


def _asset(path: str, *, role: str, source_url: str, payload: bytes, mime_type: str) -> ExportAsset:
    return ExportAsset(
        asset_type=role,
        path=path,
        description=f"MSN manual capture {role.replace('_', ' ')}",
        source_url=source_url,
        sha256=_sha256_bytes(payload),
        mime_type=mime_type,
        size_bytes=len(payload),
    )


@dataclass(frozen=True)
class MSNManualTotalExportPacket:
    schema_version: str
    package_id: str
    source_url: str
    source_url_host_hint: str
    manifest_file_name: str
    manifest: dict[str, Any]
    asset_paths: tuple[str, ...]
    article_text_file_name: str
    comments_json_file_name: str | None
    bundle_json_file_name: str
    article_text_sha256: str
    comments_json_sha256: str | None
    bundle_json_sha256: str
    manifest_sha256: str
    packet_sha256: str
    article_text_char_count: int
    comment_count: int
    total_export_manifest_implemented: bool = True
    ready_for_total_export_review: bool = True
    review_required: bool = True
    manual_operator_artifacts_supplied: bool = True
    data_extraction_implemented: bool = True
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    archive_submission_performed_by_tool: bool = False
    media_download_performed_by_tool: bool = False
    credential_value_read: bool = False
    raw_html_payload_included: bool = False
    raw_media_payload_included: bool = False
    full_local_path_serialized: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_msn_manual_total_export_packet(
    *,
    bundle: MSNManualCaptureBundle,
    package_id: str | None = None,
) -> MSNManualTotalExportPacket:
    if not bundle.ready_for_total_export_review:
        raise ValueError("MSN manual capture bundle is not ready for Total Export review")
    safe_id = _safe_name(package_id or f"msn_manual_{bundle.source_url_host_hint}", field_name="package_id")

    article_bytes = bundle.article_text.encode("utf-8")
    comments_payload = {"comments": list(bundle.comments), "comment_count": bundle.comment_count}
    comments_bytes = _json_bytes(comments_payload) if bundle.comment_count else b""
    bundle_bytes = msn_manual_capture_bundle_to_json(bundle).encode("utf-8")

    article_path = f"page_capture/{safe_id}_article_text.txt"
    comments_path = f"metadata/{safe_id}_comments.json" if bundle.comment_count else None
    bundle_path = f"metadata/{safe_id}_msn_manual_capture_bundle.json"
    manifest_path = f"metadata/{manifest_filename(safe_id)}"

    assets = [
        _asset(article_path, role=ASSET_EXTRACTED_TEXT, source_url=bundle.source_url, payload=article_bytes, mime_type="text/plain; charset=utf-8"),
        _asset(bundle_path, role=ASSET_JSON_EXPORT, source_url=bundle.source_url, payload=bundle_bytes, mime_type="application/json"),
    ]
    if comments_path is not None:
        assets.append(_asset(comments_path, role=ASSET_JSON_EXPORT, source_url=bundle.source_url, payload=comments_bytes, mime_type="application/json"))

    manifest = TotalExportManifest(
        package_id=safe_id,
        source_urls=[bundle.source_url],
        output_folder="",
        capture_options=[
            "manual_operator_artifacts",
            "msn_article_text_extraction",
            "msn_comments_extraction" if bundle.comment_count else "msn_comments_not_supplied",
            "review_required",
        ],
        assets=assets + [
            ExportAsset(
                asset_type=ASSET_MANIFEST,
                path=manifest_path,
                description="MSN manual capture Total Export manifest",
                source_url=bundle.source_url,
                sha256="computed-after-manifest-build",
                mime_type="application/json",
                size_bytes=0,
            )
        ],
        notes="MSN manual capture package assembled from explicit operator-supplied artifacts; review required before treating capture as complete or verified.",
        app_version="manual_msn_total_export_v1",
    )
    manifest_dict = manifest.to_dict()
    # The manifest cannot include its own final sha256 without a circular hash.
    # Store the manifest file hash in the surrounding packet and store result; keep
    # the manifest asset entry as a declared output with an accurate byte count.
    manifest_dict["assets"][-1]["sha256"] = ""
    manifest_dict["assets"][-1]["size_bytes"] = len(_json_bytes(manifest_dict))
    manifest_dict["assets"][-1]["size_bytes"] = len(_json_bytes(manifest_dict))
    manifest_hash = _sha256_json(manifest_dict)

    base_packet = {
        "package_id": safe_id,
        "source_url": bundle.source_url,
        "manifest": manifest_dict,
        "article_text_sha256": _sha256_bytes(article_bytes),
        "comments_json_sha256": _sha256_bytes(comments_bytes) if comments_bytes else None,
        "bundle_json_sha256": _sha256_bytes(bundle_bytes),
        "comment_count": bundle.comment_count,
    }
    asset_paths = tuple(asset["path"] for asset in manifest_dict["assets"])
    return MSNManualTotalExportPacket(
        schema_version=MSN_MANUAL_TOTAL_EXPORT_MANIFEST_SCHEMA_VERSION,
        package_id=safe_id,
        source_url=bundle.source_url,
        source_url_host_hint=_host_hint(bundle.source_url),
        manifest_file_name=manifest_path,
        manifest=manifest_dict,
        asset_paths=asset_paths,
        article_text_file_name=article_path,
        comments_json_file_name=comments_path,
        bundle_json_file_name=bundle_path,
        article_text_sha256=_sha256_bytes(article_bytes),
        comments_json_sha256=_sha256_bytes(comments_bytes) if comments_bytes else None,
        bundle_json_sha256=_sha256_bytes(bundle_bytes),
        manifest_sha256=manifest_hash,
        packet_sha256=_sha256_json(base_packet),
        article_text_char_count=len(bundle.article_text),
        comment_count=bundle.comment_count,
    )


def msn_manual_total_export_packet_to_json(packet: MSNManualTotalExportPacket) -> str:
    return _json_bytes(packet.to_dict()).decode("utf-8")
