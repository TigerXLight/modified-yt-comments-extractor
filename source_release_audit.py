from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_release_audit_v1"
TRACEABILITY_SCHEMA_VERSION = "source_release_traceability_map_v1"
ARCHIVE_HANDOFF_SCHEMA_VERSION = "source_release_archive_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_release_audit_operator_summary_v1"

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
        sha256 = str(item.get("sha256") or "").strip()
        artifacts.append(
            {
                "role": _clean_identifier(item.get("role") or item.get("artifact_role"), fallback="artifact"),
                "filename": filename,
                "sha256": sha256,
                "byte_count": item.get("byte_count") if isinstance(item.get("byte_count"), int) and item.get("byte_count") >= 0 else 0,
                "source_stage": _clean_identifier(item.get("source_stage") or item.get("input_stage"), fallback="source_release_index"),
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


def _trace_node(node_id: str, node_type: str, *, status: str = "RECORDED") -> dict[str, str]:
    return {"node_id": node_id, "node_type": node_type, "status": status}


@dataclass(frozen=True)
class SourceReleaseAuditOutputs:
    release_audit_report: dict[str, Any]
    traceability_map: dict[str, Any]
    archive_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "release_audit_report": self.release_audit_report,
            "traceability_map": self.traceability_map,
            "archive_handoff": self.archive_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_release_audit(
    *,
    release_index_record: Mapping[str, Any],
    release_inventory: Mapping[str, Any] | None = None,
    export_bundle_handoff: Mapping[str, Any] | None = None,
    auditor_id: str = "manual_auditor",
    audit_profile: str = "source_adapter_shared_release_audit_v1",
    audit_notes: Iterable[str] | None = None,
) -> SourceReleaseAuditOutputs:
    record = _coerce_mapping(release_index_record, name="release_index_record")
    inventory = _coerce_mapping(release_inventory, name="release_inventory")
    handoff = _coerce_mapping(export_bundle_handoff, name="export_bundle_handoff")

    if record.get("schema_version") != "source_release_index_v1":
        raise ValueError("release_index_record schema_version must be source_release_index_v1")
    if record.get("release_index_status") != "READY_FOR_RELEASE_EXPORT_BUNDLE":
        raise ValueError("release_index_record.release_index_status must be READY_FOR_RELEASE_EXPORT_BUNDLE")

    release_index_id = _clean_identifier(record.get("release_index_id"), fallback="source.release_index")
    approved_release_id = _clean_identifier(record.get("approved_release_id"), fallback="source.approved_release")
    evidence_review_package_id = _clean_identifier(record.get("evidence_review_package_id"), fallback="source.evidence_review")
    queue_item_id = _clean_identifier(record.get("queue_item_id"), fallback="source.evidence_queue")
    total_export_package_id = _clean_identifier(record.get("total_export_package_id"), fallback="source.total_export_package")
    capture_bundle_id = _clean_identifier(record.get("capture_bundle_id"), fallback="source.capture_bundle")
    adapter = _clean_identifier(record.get("adapter_id"), fallback="source")
    source_url = str(record.get("source_url") or "").strip()
    if not source_url:
        raise ValueError("release_index_record.source_url is required")

    if inventory:
        if inventory.get("schema_version") != "source_release_inventory_v1":
            raise ValueError("release_inventory schema_version must be source_release_inventory_v1")
        if str(inventory.get("release_index_id") or "") != release_index_id:
            raise ValueError("release_inventory.release_index_id mismatch")
        if inventory.get("inventory_status") != "READY_FOR_RELEASE_EXPORT_BUNDLE":
            raise ValueError("release_inventory must be READY_FOR_RELEASE_EXPORT_BUNDLE")

    if handoff:
        if handoff.get("schema_version") != "source_release_export_bundle_handoff_v1":
            raise ValueError("export_bundle_handoff schema_version mismatch")
        if str(handoff.get("release_index_id") or "") != release_index_id:
            raise ValueError("export_bundle_handoff.release_index_id mismatch")
        if str(handoff.get("approved_release_id") or "") != approved_release_id:
            raise ValueError("export_bundle_handoff.approved_release_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_RELEASE_EXPORT_BUNDLE":
            raise ValueError("export_bundle_handoff must be READY_FOR_RELEASE_EXPORT_BUNDLE")

    artifacts = _normalise_artifacts(record.get("artifact_index"))
    if not artifacts:
        raise ValueError("release audit requires a non-empty release_index_record.artifact_index")

    artifact_roles = sorted({artifact["role"] for artifact in artifacts})
    artifact_hashes = [artifact["sha256"] for artifact in artifacts if artifact.get("sha256")]
    release_fingerprint = str(record.get("release_fingerprint") or _stable_hash({"artifacts": artifacts}, length=16))
    index_fingerprint = str(record.get("index_fingerprint") or _stable_hash({"release_index_id": release_index_id}, length=16))
    profile = _clean_identifier(audit_profile, fallback="source_adapter_shared_release_audit_v1")
    auditor = _clean_identifier(auditor_id, fallback="manual_auditor")
    notes = _normalise_notes(audit_notes, record.get("release_notes") if isinstance(record.get("release_notes"), list) else [])

    audit_seed = {
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "queue_item_id": queue_item_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "release_fingerprint": release_fingerprint,
        "index_fingerprint": index_fingerprint,
        "audit_profile": profile,
    }
    release_audit_id = f"{adapter}.release_audit.{_stable_hash(audit_seed)}"
    audit_fingerprint = _stable_hash(
        {
            "release_audit_id": release_audit_id,
            "release_index_id": release_index_id,
            "approved_release_id": approved_release_id,
            "artifact_hashes": artifact_hashes,
            "artifact_roles": artifact_roles,
        },
        length=16,
    )

    checks = [
        {
            "check_id": "schema_and_status",
            "status": "PASS",
            "detail": "Release index record schema and ready status are valid.",
        },
        {
            "check_id": "safe_artifact_basenames",
            "status": "PASS",
            "detail": "All audited artifacts use safe basenames without full local paths.",
        },
        {
            "check_id": "immutable_prior_stages",
            "status": "PASS",
            "detail": "Audit creates new records and does not mutate prior shared-stage records.",
        },
        {
            "check_id": "manual_live_safety",
            "status": "PASS",
            "detail": "No browser, network, credential, archive, or upload action is started by this audit stage.",
        },
    ]

    release_audit_report = {
        "schema_version": SCHEMA_VERSION,
        "release_audit_id": release_audit_id,
        "audit_status": "READY_FOR_ARCHIVE_HANDOFF",
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": evidence_review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "audit_profile": profile,
        "audited_by": auditor,
        "artifact_count": len(artifacts),
        "artifact_roles": artifact_roles,
        "artifact_index": artifacts,
        "release_fingerprint": release_fingerprint,
        "index_fingerprint": index_fingerprint,
        "audit_fingerprint": audit_fingerprint,
        "audit_checks": checks,
        "audit_notes": notes,
    }

    traceability_nodes = [
        _trace_node(capture_bundle_id, "source_capture_bundle"),
        _trace_node(total_export_package_id, "source_total_export_package"),
        _trace_node(queue_item_id, "source_evidence_queue"),
        _trace_node(evidence_review_package_id, "source_evidence_review"),
        _trace_node(approved_release_id, "source_approved_release"),
        _trace_node(release_index_id, "source_release_index"),
        _trace_node(release_audit_id, "source_release_audit", status="READY_FOR_ARCHIVE_HANDOFF"),
    ]
    traceability_edges = [
        {"from": capture_bundle_id, "to": total_export_package_id, "relationship": "packaged_as_total_export"},
        {"from": total_export_package_id, "to": queue_item_id, "relationship": "queued_for_review"},
        {"from": queue_item_id, "to": evidence_review_package_id, "relationship": "reviewed_as"},
        {"from": evidence_review_package_id, "to": approved_release_id, "relationship": "approved_as"},
        {"from": approved_release_id, "to": release_index_id, "relationship": "indexed_as"},
        {"from": release_index_id, "to": release_audit_id, "relationship": "audited_as"},
    ]

    traceability_map = {
        "schema_version": TRACEABILITY_SCHEMA_VERSION,
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "queue_item_id": queue_item_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "traceability_status": "READY_FOR_ARCHIVE_HANDOFF",
        "traceability_nodes": traceability_nodes,
        "traceability_edges": traceability_edges,
        "artifact_index": artifacts,
        "audit_fingerprint": audit_fingerprint,
    }

    archive_handoff = {
        "schema_version": ARCHIVE_HANDOFF_SCHEMA_VERSION,
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "evidence_review_package_id": evidence_review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": total_export_package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "handoff_status": "READY_FOR_ARCHIVE_HANDOFF",
        "required_next_stage": "source_archive_handoff",
        "archive_handoff_inputs": [
            {"role": "source_release_audit_report", "id": release_audit_id, "filename_hint": f"{release_audit_id}.source_release_audit_report.json"},
            {"role": "source_release_traceability_map", "id": release_audit_id, "filename_hint": f"{release_audit_id}.source_release_traceability_map.json"},
            {"role": "source_release_index_record", "id": release_index_id, "filename_hint": f"{release_index_id}.source_release_index_record.json"},
        ],
        "archive_submission_started": False,
        "manual_or_live_actions_started": False,
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "release_audit_id": release_audit_id,
        "release_index_id": release_index_id,
        "approved_release_id": approved_release_id,
        "queue_item_id": queue_item_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "manual_or_live_actions_started": False,
        "archive_submission_started": False,
        "input_mode": "explicit_release_index_json_only",
        "audit_status": "READY_FOR_ARCHIVE_HANDOFF",
        "next_actions": [
            "Pass the archive handoff to the shared source_archive_handoff stage.",
            "Keep release index, approved release, Evidence Review, and Evidence Queue records immutable.",
            "Use this shared release-audit contract for future adapters rather than cloning MSN-specific audit modules.",
        ],
    }

    return SourceReleaseAuditOutputs(
        release_audit_report=release_audit_report,
        traceability_map=traceability_map,
        archive_handoff=archive_handoff,
        operator_summary=operator_summary,
    )


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")
