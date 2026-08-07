from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_total_export_package_v1"
EXPORT_MANIFEST_SCHEMA_VERSION = "source_total_export_manifest_v1"
EVIDENCE_HANDOFF_SCHEMA_VERSION = "source_total_export_evidence_queue_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_total_export_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FULL_PATH_RE = re.compile(r"(^[a-zA-Z]:[\\/])|(^[\\/])|([\\/])")


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


def _coerce_mapping(value: Mapping[str, Any] | None, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return dict(value)


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


def _safe_basename(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("artifact filename must not be blank")
    parts = Path(name).parts
    if name in {".", ".."} or ".." in parts:
        raise ValueError(f"artifact filename is not safe: {name!r}")
    if _FULL_PATH_RE.search(name):
        raise ValueError(f"artifact filename must be a basename, not a path: {name!r}")
    return name


def _safe_optional_basename(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return _safe_basename(text)


def _capture_bundle_id(capture_bundle: Mapping[str, Any]) -> str:
    return _clean_identifier(capture_bundle.get("capture_bundle_id"), fallback="source.capture_bundle")


def _adapter_id(capture_bundle: Mapping[str, Any], *, fallback: str = "source") -> str:
    return _clean_identifier(capture_bundle.get("adapter_id"), fallback=fallback)


def _source_url(capture_bundle: Mapping[str, Any], handoff: Mapping[str, Any]) -> str:
    return _first_text(capture_bundle, ("source_url", "url", "canonical_url"), default=_first_text(handoff, ("source_url", "url"), default=""))


def _content_payload(capture_bundle: Mapping[str, Any]) -> dict[str, Any]:
    content = capture_bundle.get("content")
    if not isinstance(content, Mapping):
        raise ValueError("capture_bundle.content object is required")
    title = _first_text(content, ("title", "headline", "article_title"), default="")
    body_text = _first_text(content, ("body_text", "article_text", "text", "content_text"), default="")
    body_sha256 = _first_text(content, ("body_sha256", "sha256"), default="")
    if body_text and not body_sha256:
        body_sha256 = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
    if not title and not body_text:
        raise ValueError("capture_bundle.content must include title/headline or body text")
    return {
        "title": title,
        "body_text": body_text,
        "body_sha256": body_sha256,
        "body_char_count": len(body_text),
        "content_extraction_id": _first_text(content, ("content_extraction_id", "extraction_id"), default=""),
    }


def _comment_payload(capture_bundle: Mapping[str, Any]) -> dict[str, Any]:
    comments = capture_bundle.get("comments")
    if not isinstance(comments, Mapping):
        return {
            "available": False,
            "comment_count": 0,
            "comment_extraction_id": "",
        }
    count = _first_int(comments, ("comment_count", "total_comments", "comments_count"), default=0)
    return {
        "available": bool(comments.get("available")) or count > 0,
        "comment_count": max(count, 0),
        "comment_extraction_id": _first_text(comments, ("comment_extraction_id", "comments_extraction_id", "extraction_id"), default=""),
    }


def _artifact_index(capture_bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    artifacts = capture_bundle.get("artifact_index")
    if not isinstance(artifacts, list):
        return []
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in artifacts:
        if not isinstance(item, Mapping):
            continue
        filename = _safe_optional_basename(
            item.get("filename")
            or item.get("basename")
            or item.get("artifact_filename")
            or item.get("safe_basename")
            or item.get("relative_name")
        )
        if not filename:
            continue
        role = _clean_identifier(item.get("role") or item.get("artifact_role") or item.get("type"), fallback="artifact")
        key = (filename, role)
        if key in seen:
            continue
        seen.add(key)
        byte_count = item.get("byte_count")
        if not isinstance(byte_count, int) or byte_count < 0:
            byte_count = 0
        result.append(
            {
                "filename": filename,
                "role": role,
                "input_stage": _clean_identifier(item.get("input_stage"), fallback="capture_bundle"),
                "sha256": str(item.get("sha256") or "").strip(),
                "byte_count": byte_count,
            }
        )
    result.sort(key=lambda entry: (entry["role"], entry["filename"]))
    return result


def _input_stage_ids(capture_bundle: Mapping[str, Any]) -> dict[str, str]:
    value = capture_bundle.get("input_stage_ids")
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(raw or "") for key, raw in value.items() if str(raw or "").strip()}


def _handoff_from_bundle(capture_bundle: Mapping[str, Any], explicit_handoff: Mapping[str, Any]) -> dict[str, Any]:
    if explicit_handoff:
        return dict(explicit_handoff)
    embedded = capture_bundle.get("total_export_handoff")
    if isinstance(embedded, Mapping):
        return dict(embedded)
    return {}


@dataclass(frozen=True)
class SourceTotalExportPackageOutputs:
    total_export_package: dict[str, Any]
    total_export_manifest: dict[str, Any]
    evidence_queue_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_export_package": self.total_export_package,
            "total_export_manifest": self.total_export_manifest,
            "evidence_queue_handoff": self.evidence_queue_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_total_export_package(
    *,
    capture_bundle: Mapping[str, Any],
    capture_manifest: Mapping[str, Any] | None = None,
    total_export_handoff: Mapping[str, Any] | None = None,
    export_profile: str = "source_adapter_shared_v1",
    package_notes: Iterable[str] | None = None,
) -> SourceTotalExportPackageOutputs:
    bundle = _coerce_mapping(capture_bundle, name="capture_bundle")
    manifest_input = _coerce_mapping(capture_manifest, name="capture_manifest")
    handoff = _handoff_from_bundle(bundle, _coerce_mapping(total_export_handoff, name="total_export_handoff"))

    schema = bundle.get("schema_version")
    if schema and schema != "source_capture_bundle_v1":
        raise ValueError("capture_bundle schema_version must be source_capture_bundle_v1")
    capture_bundle_id = _capture_bundle_id(bundle)
    adapter = _adapter_id(bundle)
    source_url = _source_url(bundle, handoff)
    content = _content_payload(bundle)
    comments = _comment_payload(bundle)
    artifacts = _artifact_index(bundle)
    input_stage_ids = _input_stage_ids(bundle)
    notes = [str(note).strip() for note in (package_notes or []) if str(note).strip()]
    profile = _clean_identifier(export_profile, fallback="source_adapter_shared_v1")

    if handoff:
        if handoff.get("capture_bundle_id") and str(handoff.get("capture_bundle_id")) != capture_bundle_id:
            raise ValueError("total_export_handoff.capture_bundle_id mismatch")
        status = str(handoff.get("handoff_status") or "").strip()
        if status and status != "READY_FOR_TOTAL_EXPORT_PACKAGE":
            raise ValueError("total_export_handoff must be READY_FOR_TOTAL_EXPORT_PACKAGE")
    if manifest_input and manifest_input.get("capture_bundle_id") and str(manifest_input.get("capture_bundle_id")) != capture_bundle_id:
        raise ValueError("capture_manifest.capture_bundle_id mismatch")

    identity_seed = {
        "adapter_id": adapter,
        "source_url": source_url,
        "capture_bundle_id": capture_bundle_id,
        "export_profile": profile,
        "content_sha256": content["body_sha256"],
        "comment_count": comments["comment_count"],
        "artifact_index": artifacts,
    }
    package_id = f"{adapter}.total_export_package.{_stable_hash(identity_seed)}"

    total_export_manifest = {
        "schema_version": EXPORT_MANIFEST_SCHEMA_VERSION,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "export_profile": profile,
        "artifact_count": len(artifacts),
        "comment_count": comments["comment_count"],
        "content_ready": bool(content["title"] or content["body_text"]),
        "comments_ready": comments["available"],
        "package_files": [
            {
                "role": "source_total_export_package",
                "filename_hint": f"{package_id}.source_total_export_package.json",
            },
            {
                "role": "source_total_export_manifest",
                "filename_hint": f"{package_id}.source_total_export_manifest.json",
            },
        ],
    }

    evidence_queue_handoff = {
        "schema_version": EVIDENCE_HANDOFF_SCHEMA_VERSION,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "handoff_status": "READY_FOR_EVIDENCE_QUEUE",
        "required_next_stage": "source_evidence_queue",
        "queue_inputs": [
            {
                "role": "source_total_export_package",
                "id": package_id,
                "filename_hint": f"{package_id}.source_total_export_package.json",
            },
            {
                "role": "source_total_export_manifest",
                "id": package_id,
                "filename_hint": f"{package_id}.source_total_export_manifest.json",
            },
        ],
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "manual_or_live_actions_started": False,
        "input_mode": "explicit_capture_bundle_json_only",
        "export_profile": profile,
        "artifact_count": len(artifacts),
        "comment_count": comments["comment_count"],
        "package_notes": notes,
        "next_actions": [
            "Review the Total Export package and manifest.",
            "Pass the Evidence Queue handoff to the shared source_evidence_queue stage.",
            "Keep future adapters on shared package contracts unless their export shape genuinely differs.",
        ],
    }

    total_export_package = {
        "schema_version": SCHEMA_VERSION,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "export_profile": profile,
        "export_status": "READY_FOR_EVIDENCE_QUEUE",
        "input_stage_ids": input_stage_ids,
        "content": content,
        "comments": comments,
        "artifact_index": artifacts,
        "capture_manifest_summary": {
            "schema_version": str(manifest_input.get("schema_version") or bundle.get("capture_manifest", {}).get("schema_version") or ""),
            "artifact_count": len(artifacts),
            "comment_count": comments["comment_count"],
        },
        "total_export_manifest": total_export_manifest,
        "evidence_queue_handoff": evidence_queue_handoff,
        "operator_summary": operator_summary,
    }

    return SourceTotalExportPackageOutputs(
        total_export_package=total_export_package,
        total_export_manifest=total_export_manifest,
        evidence_queue_handoff=evidence_queue_handoff,
        operator_summary=operator_summary,
    )


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")
