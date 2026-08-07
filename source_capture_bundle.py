from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_capture_bundle_v1"
MANIFEST_SCHEMA_VERSION = "source_capture_manifest_v1"
HANDOFF_SCHEMA_VERSION = "source_capture_total_export_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_capture_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FULL_PATH_RE = re.compile(r"(^[a-zA-Z]:[\\/])|(^[\\/])|([\\/])")

BUNDLE_INPUT_ROLES = {
    "content_extraction": "content_extraction_json",
    "comment_extraction": "comment_extraction_json",
    "artifact_collection": "artifact_collection_json",
}


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(data: Mapping[str, Any], *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()[:length]


def _clean_identifier(value: object, *, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _first_text(mapping: Mapping[str, Any], keys: Iterable[str], *, default: str = "") -> str:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _first_int(mapping: Mapping[str, Any], keys: Iterable[str], *, default: int = 0) -> int:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return default


def _coerce_mapping(value: Mapping[str, Any] | None, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return dict(value)


def _safe_basename(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("artifact filename must not be blank")
    if name in {".", ".."} or ".." in Path(name).parts:
        raise ValueError(f"artifact filename is not safe: {name!r}")
    if _FULL_PATH_RE.search(name):
        raise ValueError(f"artifact filename must be a basename, not a path: {name!r}")
    return name


def _iter_artifact_candidates(stage_name: str, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for key in ("artifacts", "source_artifacts", "stored_files", "files", "artifact_ledger"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    candidates.append(dict(item))
    if stage_name == "content_extraction":
        for key in ("content_artifact", "source_artifact"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                candidates.append(dict(value))
    if stage_name == "comment_extraction":
        value = payload.get("comment_artifact")
        if isinstance(value, Mapping):
            candidates.append(dict(value))
    return candidates


def _artifact_filename(item: Mapping[str, Any]) -> str | None:
    for key in ("filename", "basename", "artifact_filename", "safe_basename", "relative_name"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return _safe_basename(value)
    return None


def _artifact_sha256(item: Mapping[str, Any]) -> str:
    for key in ("sha256", "content_sha256", "artifact_sha256"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _artifact_byte_count(item: Mapping[str, Any]) -> int:
    for key in ("byte_count", "size_bytes", "bytes"):
        value = item.get(key)
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0


def _build_artifact_index(
    *,
    content_extraction: Mapping[str, Any],
    comment_extraction: Mapping[str, Any],
    artifact_collection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    artifact_index: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    stage_payloads = [
        ("artifact_collection", artifact_collection),
        ("content_extraction", content_extraction),
        ("comment_extraction", comment_extraction),
    ]
    for stage_name, payload in stage_payloads:
        for item in _iter_artifact_candidates(stage_name, payload):
            filename = _artifact_filename(item)
            if not filename:
                continue
            role = _first_text(item, ("role", "artifact_role", "type"), default=stage_name)
            role = _clean_identifier(role, fallback=stage_name)
            key = (filename, role)
            if key in seen:
                continue
            seen.add(key)
            artifact_index.append(
                {
                    "filename": filename,
                    "input_stage": stage_name,
                    "role": role,
                    "sha256": _artifact_sha256(item),
                    "byte_count": _artifact_byte_count(item),
                }
            )
    artifact_index.sort(key=lambda item: (item["input_stage"], item["role"], item["filename"]))
    return artifact_index


def _comment_count(comment_extraction: Mapping[str, Any]) -> int:
    count = _first_int(comment_extraction, ("comment_count", "total_comments", "comments_count"), default=-1)
    if count >= 0:
        return count
    comments = comment_extraction.get("comments")
    if isinstance(comments, list):
        return len(comments)
    comment_index = comment_extraction.get("comment_index")
    if isinstance(comment_index, list):
        return len(comment_index)
    return 0


def _body_text(content_extraction: Mapping[str, Any]) -> str:
    direct = _first_text(content_extraction, ("body_text", "article_text", "text", "content_text"), default="")
    if direct:
        return direct
    body = content_extraction.get("body")
    if isinstance(body, Mapping):
        return _first_text(body, ("text", "plain_text", "body_text"), default="")
    return ""


def _title_text(content_extraction: Mapping[str, Any]) -> str:
    direct = _first_text(content_extraction, ("title", "headline", "article_title"), default="")
    if direct:
        return direct
    article = content_extraction.get("article")
    if isinstance(article, Mapping):
        return _first_text(article, ("title", "headline"), default="")
    return ""


def _extract_source_url(
    *,
    source_url: str | None,
    content_extraction: Mapping[str, Any],
    artifact_collection: Mapping[str, Any],
) -> str:
    if source_url and source_url.strip():
        return source_url.strip()
    for mapping in (content_extraction, artifact_collection):
        found = _first_text(mapping, ("source_url", "url", "canonical_url", "original_url"), default="")
        if found:
            return found
    source = content_extraction.get("source")
    if isinstance(source, Mapping):
        found = _first_text(source, ("url", "source_url", "canonical_url"), default="")
        if found:
            return found
    return ""


def _extract_adapter_id(
    *,
    adapter_id: str | None,
    content_extraction: Mapping[str, Any],
    comment_extraction: Mapping[str, Any],
    artifact_collection: Mapping[str, Any],
) -> str:
    if adapter_id and adapter_id.strip():
        return _clean_identifier(adapter_id, fallback="source")
    for mapping in (content_extraction, comment_extraction, artifact_collection):
        found = _first_text(mapping, ("adapter_id", "source_adapter_id", "source_id"), default="")
        if found:
            return _clean_identifier(found, fallback="source")
    return "source"


def _input_stage_id(payload: Mapping[str, Any], keys: Iterable[str], *, fallback: str) -> str:
    value = _first_text(payload, keys, default="")
    return _clean_identifier(value, fallback=fallback)


@dataclass(frozen=True)
class SourceCaptureBundleOutputs:
    capture_bundle: dict[str, Any]
    capture_manifest: dict[str, Any]
    total_export_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "capture_bundle": self.capture_bundle,
            "capture_manifest": self.capture_manifest,
            "total_export_handoff": self.total_export_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_capture_bundle(
    *,
    content_extraction: Mapping[str, Any],
    comment_extraction: Mapping[str, Any] | None = None,
    artifact_collection: Mapping[str, Any] | None = None,
    adapter_id: str | None = None,
    source_url: str | None = None,
    operator_notes: Iterable[str] | None = None,
) -> SourceCaptureBundleOutputs:
    content = _coerce_mapping(content_extraction, name="content_extraction")
    comments = _coerce_mapping(comment_extraction, name="comment_extraction")
    collection = _coerce_mapping(artifact_collection, name="artifact_collection")

    title = _title_text(content)
    body = _body_text(content)
    if not title and not body:
        raise ValueError("content extraction must include title/headline or body/article text")

    adapter = _extract_adapter_id(
        adapter_id=adapter_id,
        content_extraction=content,
        comment_extraction=comments,
        artifact_collection=collection,
    )
    url = _extract_source_url(source_url=source_url, content_extraction=content, artifact_collection=collection)
    content_id = _input_stage_id(
        content,
        ("content_extraction_id", "extraction_id", "stage_id"),
        fallback=f"{adapter}.content_extraction",
    )
    comment_id = ""
    if comments:
        comment_id = _input_stage_id(
            comments,
            ("comment_extraction_id", "comments_extraction_id", "extraction_id", "stage_id"),
            fallback=f"{adapter}.comment_extraction",
        )
    collection_id = ""
    if collection:
        collection_id = _input_stage_id(
            collection,
            ("artifact_collection_id", "collection_id", "stage_id"),
            fallback=f"{adapter}.artifact_collection",
        )

    artifact_index = _build_artifact_index(
        content_extraction=content,
        comment_extraction=comments,
        artifact_collection=collection,
    )
    comments_count = _comment_count(comments)
    notes = [str(note).strip() for note in (operator_notes or []) if str(note).strip()]

    identity_seed = {
        "adapter_id": adapter,
        "source_url": url,
        "content_extraction_id": content_id,
        "comment_extraction_id": comment_id,
        "artifact_collection_id": collection_id,
        "title": title,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest() if body else "",
        "comment_count": comments_count,
        "artifact_index": artifact_index,
    }
    bundle_id = f"{adapter}.capture_bundle.{_stable_hash(identity_seed)}"

    capture_manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "capture_bundle_id": bundle_id,
        "adapter_id": adapter,
        "source_url": url,
        "input_stage_ids": {
            "artifact_collection_id": collection_id,
            "content_extraction_id": content_id,
            "comment_extraction_id": comment_id,
        },
        "artifact_count": len(artifact_index),
        "comment_count": comments_count,
        "has_comments": bool(comments),
        "artifact_roles": sorted({item["role"] for item in artifact_index}),
    }

    total_export_handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "capture_bundle_id": bundle_id,
        "adapter_id": adapter,
        "source_url": url,
        "handoff_status": "READY_FOR_TOTAL_EXPORT_PACKAGE",
        "required_next_stage": "source_total_export_package",
        "package_inputs": [
            {
                "role": "source_capture_bundle",
                "id": bundle_id,
                "filename_hint": f"{bundle_id}.source_capture_bundle.json",
            },
            {
                "role": "source_capture_manifest",
                "id": bundle_id,
                "filename_hint": f"{bundle_id}.source_capture_manifest.json",
            },
        ],
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "capture_bundle_id": bundle_id,
        "adapter_id": adapter,
        "source_url": url,
        "manual_or_live_actions_started": False,
        "input_mode": "explicit_json_inputs_only",
        "content_ready": bool(title or body),
        "comments_ready": bool(comments),
        "artifact_count": len(artifact_index),
        "comment_count": comments_count,
        "operator_notes": notes,
        "next_actions": [
            "Review the capture bundle and manifest.",
            "Pass the Total Export handoff to the shared source_total_export_package stage.",
            "Add adapter-specific fixtures only when extraction differs from the shared contract.",
        ],
    }

    capture_bundle = {
        "schema_version": SCHEMA_VERSION,
        "capture_bundle_id": bundle_id,
        "adapter_id": adapter,
        "source_url": url,
        "input_roles": dict(BUNDLE_INPUT_ROLES),
        "input_stage_ids": capture_manifest["input_stage_ids"],
        "content": {
            "title": title,
            "body_text": body,
            "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest() if body else "",
            "body_char_count": len(body),
            "content_extraction_id": content_id,
        },
        "comments": {
            "comment_extraction_id": comment_id,
            "comment_count": comments_count,
            "available": bool(comments),
        },
        "artifact_index": artifact_index,
        "capture_manifest": capture_manifest,
        "total_export_handoff": total_export_handoff,
        "operator_summary": operator_summary,
    }

    return SourceCaptureBundleOutputs(
        capture_bundle=capture_bundle,
        capture_manifest=capture_manifest,
        total_export_handoff=total_export_handoff,
        operator_summary=operator_summary,
    )


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")
