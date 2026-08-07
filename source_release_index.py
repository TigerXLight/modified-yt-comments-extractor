from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_release_index_v1"
INVENTORY_SCHEMA_VERSION = "source_release_inventory_v1"
EXPORT_HANDOFF_SCHEMA_VERSION = "source_release_export_bundle_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_release_index_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


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


def _safe_basename(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "/" in text or "\\" in text or re.match(r"^[a-zA-Z]:", text):
        raise ValueError("artifact filenames must be safe basenames, not paths")
    return text


def _normalise_artifacts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    artifacts: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        filename = _safe_basename(item.get("filename") or item.get("basename") or item.get("safe_basename"))
        if not filename:
            continue
        artifacts.append(
            {
                "role": _clean_identifier(item.get("role") or item.get("artifact_role"), fallback="artifact"),
                "filename": filename,
                "sha256": str(item.get("sha256") or "").strip(),
                "byte_count": item.get("byte_count") if isinstance(item.get("byte_count"), int) and item.get("byte_count") >= 0 else 0,
                "source_stage": _clean_identifier(item.get("source_stage") or item.get("input_stage"), fallback="source_approved_release"),
            }
        )
    artifacts.sort(key=lambda entry: (entry["role"], entry["filename"]))
    return artifacts


def _normalise_notes(*note_sources: Iterable[str] | None) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()
    for source in note_sources:
        if not source:
            continue
        for note in source:
            text = str(note or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            notes.append(text)
    return notes


@dataclass(frozen=True)
class SourceReleaseIndexOutputs:
    release_index_record: dict[str, Any]
    release_inventory: dict[str, Any]
    export_bundle_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "release_index_record": self.release_index_record,
            "release_inventory": self.release_inventory,
            "export_bundle_handoff": self.export_bundle_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_release_index(
    *,
    approved_release_package: Mapping[str, Any],
    approved_release_manifest: Mapping[str, Any] | None = None,
    release_index_handoff: Mapping[str, Any] | None = None,
    indexer_id: str = "manual_indexer",
    release_index_profile: str = "source_adapter_shared_release_index_v1",
    release_notes: Iterable[str] | None = None,
) -> SourceReleaseIndexOutputs:
    package = _coerce_mapping(approved_release_package, name="approved_release_package")
    manifest = _coerce_mapping(approved_release_manifest, name="approved_release_manifest")
    handoff = _coerce_mapping(release_index_handoff, name="release_index_handoff")

    if package.get("schema_version") != "source_approved_release_v1":
        raise ValueError("approved_release_package schema_version must be source_approved_release_v1")
    if package.get("release_status") != "READY_FOR_RELEASE_INDEX":
        raise ValueError("approved_release_package.release_status must be READY_FOR_RELEASE_INDEX")
    if package.get("approved_by_review_decision") is not True:
        raise ValueError("approved release package must be approved by review decision")

    approved_release_id = _clean_identifier(package.get("approved_release_id"), fallback="source.approved_release")
    evidence_review_package_id = _clean_identifier(package.get("evidence_review_package_id"), fallback="source.evidence_review")
    queue_item_id = _clean_identifier(package.get("queue_item_id"), fallback="source.evidence_queue")
    total_export_package_id = _clean_identifier(package.get("total_export_package_id"), fallback="source.total_export_package")
    capture_bundle_id = _clean_identifier(package.get("capture_bundle_id"), fallback="source.capture_bundle")
    adapter = _clean_identifier(package.get("adapter_id"), fallback="source")
    source_url = _first_text(package, ("source_url", "url", "canonical_url"), default="")

    if manifest:
        if manifest.get("schema_version") != "source_approved_release_manifest_v1":
            raise ValueError("approved_release_manifest schema_version mismatch")
        if str(manifest.get("approved_release_id") or "") != approved_release_id:
            raise ValueError("approved_release_manifest.approved_release_id mismatch")
        if manifest.get("manifest_status") != "READY_FOR_RELEASE_INDEX":
            raise ValueError("approved_release_manifest must be READY_FOR_RELEASE_INDEX")

    if handoff:
        if handoff.get("schema_version") != "source_approved_release_index_handoff_v1":
            raise ValueError("release_index_handoff schema_version mismatch")
        if str(handoff.get("approved_release_id") or "") != approved_release_id:
            raise ValueError("release_index_handoff.approved_release_id mismatch")
        if str(handoff.get("queue_item_id") or "") != queue_item_id:
            raise ValueError("release_index_handoff.queue_item_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_RELEASE_INDEX":
            raise ValueError("release_index_handoff must be READY_FOR_RELEASE_INDEX")
        if handoff.get("required_next_stage") != "source_release_index":
            raise ValueError("release_index_handoff.required_next_stage must be source_release_index")

    artifacts = _normalise_artifacts(package.get("artifact_index"))
    if not artifacts:
        raise ValueError("release index requires at least one approved release artifact")

    content_summary = package.get("content_summary") if isinstance(package.get("content_summary"), Mapping) else {}
    comment_summary = package.get("comment_summary") if isinstance(package.get("comment_summary"), Mapping) else {}
    artifact_roles = sorted({artifact["role"] for artifact in artifacts})
    profile = _clean_identifier(release_index_profile, fallback="source_adapter_shared_release_index_v1")
    indexer = _clean_identifier(indexer_id, fallback="manual_indexer")
    notes = _normalise_notes(release_notes, package.get("release_notes") if isinstance(package.get("release_notes"), list) else [])

    index_seed = {
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": evidence_review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "release_index_profile": profile,
    }
    release_index_id = f"{adapter}.release_index.{_stable_hash(index_seed)}"
    release_fingerprint = str(package.get("release_fingerprint") or _stable_hash({"artifacts": artifacts}, length=16))
    index_fingerprint = _stable_hash(
        {
            "release_index_id": release_index_id,
            "approved_release_id": approved_release_id,
            "release_fingerprint": release_fingerprint,
            "artifact_roles": artifact_roles,
        },
        length=16,
    )

    release_entry = {
        "approved_release_id": approved_release_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "evidence_review_package_id": evidence_review_package_id,
        "artifact_count": len(artifacts),
        "artifact_roles": artifact_roles,
        "release_fingerprint": release_fingerprint,
        "index_fingerprint": index_fingerprint,
    }

    release_index_record = {
        "schema_version": SCHEMA_VERSION,
        "release_index_id": release_index_id,
        "release_index_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": evidence_review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "release_index_profile": profile,
        "indexed_by": indexer,
        "content_summary": dict(content_summary),
        "comment_summary": dict(comment_summary),
        "artifact_count": len(artifacts),
        "artifact_roles": artifact_roles,
        "artifact_index": artifacts,
        "release_fingerprint": release_fingerprint,
        "index_fingerprint": index_fingerprint,
        "release_notes": notes,
    }

    release_inventory = {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "release_index_id": release_index_id,
        "inventory_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "adapter_id": adapter,
        "source_url": source_url,
        "release_count": 1,
        "release_entries": [release_entry],
    }

    export_bundle_handoff = {
        "schema_version": EXPORT_HANDOFF_SCHEMA_VERSION,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": evidence_review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "handoff_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "required_next_stage": "source_release_export_bundle",
        "release_export_inputs": [
            {"role": "source_release_index_record", "id": release_index_id, "filename_hint": f"{release_index_id}.source_release_index_record.json"},
            {"role": "source_release_inventory", "id": release_index_id, "filename_hint": f"{release_index_id}.source_release_inventory.json"},
            {"role": "source_approved_release_package", "id": approved_release_id, "filename_hint": f"{approved_release_id}.source_approved_release_package.json"},
        ],
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "queue_item_id": queue_item_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "manual_or_live_actions_started": False,
        "input_mode": "explicit_approved_release_json_only",
        "release_index_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "next_actions": [
            "Pass the export-bundle handoff to the shared source_release_export_bundle stage.",
            "Keep the approved release, Evidence Queue, and Evidence Review records immutable.",
            "Use this shared release-index contract for future adapters rather than cloning MSN-specific index modules.",
        ],
    }

    return SourceReleaseIndexOutputs(
        release_index_record=release_index_record,
        release_inventory=release_inventory,
        export_bundle_handoff=export_bundle_handoff,
        operator_summary=operator_summary,
    )


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")
