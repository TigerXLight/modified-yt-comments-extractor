from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_approved_release_v1"
MANIFEST_SCHEMA_VERSION = "source_approved_release_manifest_v1"
INDEX_HANDOFF_SCHEMA_VERSION = "source_approved_release_index_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_approved_release_operator_summary_v1"

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
                "source_stage": _clean_identifier(item.get("source_stage") or item.get("input_stage"), fallback="source_evidence_review"),
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
class SourceApprovedReleaseOutputs:
    approved_release_package: dict[str, Any]
    approved_release_manifest: dict[str, Any]
    release_index_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "approved_release_package": self.approved_release_package,
            "approved_release_manifest": self.approved_release_manifest,
            "release_index_handoff": self.release_index_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_approved_release(
    *,
    evidence_review_package: Mapping[str, Any],
    evidence_review_decision: Mapping[str, Any],
    release_handoff: Mapping[str, Any] | None = None,
    releaser_id: str = "manual_releaser",
    release_profile: str = "source_adapter_shared_approved_release_v1",
    release_notes: Iterable[str] | None = None,
) -> SourceApprovedReleaseOutputs:
    package = _coerce_mapping(evidence_review_package, name="evidence_review_package")
    decision = _coerce_mapping(evidence_review_decision, name="evidence_review_decision")
    handoff = _coerce_mapping(release_handoff, name="release_handoff")

    if package.get("schema_version") != "source_evidence_review_v1":
        raise ValueError("evidence_review_package schema_version must be source_evidence_review_v1")
    if package.get("review_package_status") != "READY_FOR_REVIEW_DECISION":
        raise ValueError("evidence_review_package.review_package_status must be READY_FOR_REVIEW_DECISION")
    if decision.get("schema_version") != "source_evidence_review_decision_v1":
        raise ValueError("evidence_review_decision schema_version must be source_evidence_review_decision_v1")
    if decision.get("decision") != "APPROVED" or decision.get("approved_for_release") is not True:
        raise ValueError("only APPROVED Evidence Review decisions can build an approved release")
    if decision.get("missing_required_action_ids"):
        raise ValueError("approved release requires no missing required review actions")

    review_package_id = _clean_identifier(package.get("evidence_review_package_id"), fallback="source.evidence_review")
    queue_item_id = _clean_identifier(package.get("queue_item_id"), fallback="source.evidence_queue")
    total_export_package_id = _clean_identifier(package.get("total_export_package_id"), fallback="source.total_export_package")
    capture_bundle_id = _clean_identifier(package.get("capture_bundle_id"), fallback="source.capture_bundle")
    adapter = _clean_identifier(package.get("adapter_id"), fallback="source")
    source_url = _first_text(package, ("source_url", "url", "canonical_url"), default="")

    if str(decision.get("evidence_review_package_id") or "") != review_package_id:
        raise ValueError("evidence_review_decision.evidence_review_package_id mismatch")
    if str(decision.get("queue_item_id") or "") != queue_item_id:
        raise ValueError("evidence_review_decision.queue_item_id mismatch")

    if handoff:
        if handoff.get("schema_version") != "source_evidence_review_release_handoff_v1":
            raise ValueError("release_handoff schema_version mismatch")
        if str(handoff.get("evidence_review_package_id") or "") != review_package_id:
            raise ValueError("release_handoff.evidence_review_package_id mismatch")
        if str(handoff.get("queue_item_id") or "") != queue_item_id:
            raise ValueError("release_handoff.queue_item_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_APPROVED_RELEASE":
            raise ValueError("release_handoff must be READY_FOR_APPROVED_RELEASE")
        if handoff.get("decision") != "APPROVED":
            raise ValueError("release_handoff.decision must be APPROVED")

    artifacts = _normalise_artifacts(package.get("artifact_index"))
    if not artifacts:
        raise ValueError("approved release requires at least one reviewed artifact")

    content_summary = package.get("content_summary") if isinstance(package.get("content_summary"), Mapping) else {}
    comment_summary = package.get("comment_summary") if isinstance(package.get("comment_summary"), Mapping) else {}
    release_inputs = handoff.get("release_inputs") if isinstance(handoff.get("release_inputs"), list) else []
    profile = _clean_identifier(release_profile, fallback="source_adapter_shared_approved_release_v1")
    releaser = _clean_identifier(releaser_id, fallback="manual_releaser")
    notes = _normalise_notes(release_notes, decision.get("review_notes") if isinstance(decision.get("review_notes"), list) else [])

    release_seed = {
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "release_profile": profile,
    }
    approved_release_id = f"{adapter}.approved_release.{_stable_hash(release_seed)}"

    artifact_roles = sorted({artifact["role"] for artifact in artifacts})
    artifact_sha256_values = [artifact["sha256"] for artifact in artifacts if artifact.get("sha256")]
    release_fingerprint = _stable_hash(
        {
            "approved_release_id": approved_release_id,
            "artifact_sha256_values": artifact_sha256_values,
            "content_summary": dict(content_summary),
            "comment_summary": dict(comment_summary),
        },
        length=16,
    )

    approved_release_package = {
        "schema_version": SCHEMA_VERSION,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "release_profile": profile,
        "release_status": "READY_FOR_RELEASE_INDEX",
        "approved_by_review_decision": True,
        "reviewer_id": _clean_identifier(decision.get("reviewer_id"), fallback="manual_reviewer"),
        "releaser_id": releaser,
        "content_summary": dict(content_summary),
        "comment_summary": dict(comment_summary),
        "artifact_count": len(artifacts),
        "artifact_roles": artifact_roles,
        "artifact_index": artifacts,
        "release_inputs": release_inputs,
        "release_notes": notes,
        "release_fingerprint": release_fingerprint,
    }

    approved_release_manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "approved_release_id": approved_release_id,
        "manifest_status": "READY_FOR_RELEASE_INDEX",
        "adapter_id": adapter,
        "source_url": source_url,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "artifact_count": len(artifacts),
        "artifact_roles": artifact_roles,
        "release_fingerprint": release_fingerprint,
    }

    release_index_handoff = {
        "schema_version": INDEX_HANDOFF_SCHEMA_VERSION,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "handoff_status": "READY_FOR_RELEASE_INDEX",
        "required_next_stage": "source_release_index",
        "release_index_inputs": [
            {"role": "source_approved_release_package", "id": approved_release_id, "filename_hint": f"{approved_release_id}.source_approved_release_package.json"},
            {"role": "source_approved_release_manifest", "id": approved_release_id, "filename_hint": f"{approved_release_id}.source_approved_release_manifest.json"},
        ],
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "manual_or_live_actions_started": False,
        "input_mode": "explicit_approved_review_json_only",
        "decision": "APPROVED",
        "release_status": "READY_FOR_RELEASE_INDEX",
        "next_actions": [
            "Pass the release-index handoff to the shared source_release_index stage.",
            "Keep the original Evidence Queue and Evidence Review records immutable.",
            "Use this shared approved-release contract for future adapters rather than cloning MSN-specific release modules.",
        ],
    }

    return SourceApprovedReleaseOutputs(
        approved_release_package=approved_release_package,
        approved_release_manifest=approved_release_manifest,
        release_index_handoff=release_index_handoff,
        operator_summary=operator_summary,
    )


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")
