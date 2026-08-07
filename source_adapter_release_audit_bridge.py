from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_release_audit import build_source_release_audit

SCHEMA_VERSION = "source_adapter_release_audit_bridge_v1"
RELEASE_AUDIT_BATCH_SCHEMA_VERSION = "source_adapter_release_audit_batch_v1"
ARCHIVE_HANDOFF_BATCH_SCHEMA_VERSION = "source_adapter_archive_handoff_batch_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_release_audit_bridge_operator_summary_v1"
RELEASE_AUDIT_BRIDGE_STATUS = "SHARED_RELEASE_AUDITS_BUILT"
ARCHIVE_HANDOFF_READY_STATUS = "READY_FOR_SHARED_ARCHIVE_HANDOFF"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()[:length]


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _as_mapping_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return [_as_mapping(item, f"{label} item") for item in value]


def _safe_text(value: Any, default: str = "") -> str:
    return str(value if value is not None else default).replace("\r", " ").strip()


def _safe_id(value: Any, *, label: str, fallback: str = "") -> str:
    text = _safe_text(value, fallback)
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} must contain only letters, numbers, dot, underscore, or dash")
    return text


def _normalise_notes(notes: Iterable[str] | None) -> list[str]:
    return [str(note).strip() for note in (notes or []) if str(note).strip()]


def _release_index_outputs(release_index_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(release_index_bridge_package.get("release_index_outputs"), "release_index_outputs")


def _release_index_output_parts(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    record = _as_mapping(output.get("release_index_record"), f"release_index_outputs[{index}].release_index_record")
    inventory = _as_mapping(output.get("release_inventory"), f"release_index_outputs[{index}].release_inventory")
    handoff = _as_mapping(output.get("export_bundle_handoff"), f"release_index_outputs[{index}].export_bundle_handoff")
    return record, inventory, handoff


def _row_from_audit_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    report = _as_mapping(outputs.get("release_audit_report"), "release_audit_report")
    traceability = _as_mapping(outputs.get("traceability_map"), "traceability_map")
    archive_handoff = _as_mapping(outputs.get("archive_handoff"), "archive_handoff")
    release_audit_id = _safe_id(report.get("release_audit_id"), label="release_audit_id")
    return {
        "adapter_id": _safe_text(report.get("adapter_id"), ""),
        "source_url": _safe_text(report.get("source_url"), ""),
        "queue_item_id": _safe_text(report.get("queue_item_id"), ""),
        "approved_release_id": _safe_text(report.get("approved_release_id"), ""),
        "release_index_id": _safe_text(report.get("release_index_id"), ""),
        "release_audit_id": release_audit_id,
        "audit_status": report.get("audit_status", ""),
        "traceability_status": traceability.get("traceability_status", ""),
        "handoff_status": archive_handoff.get("handoff_status", ""),
        "required_next_stage": archive_handoff.get("required_next_stage", ""),
        "artifact_count": report.get("artifact_count", 0),
        "artifact_roles": list(report.get("artifact_roles", [])) if isinstance(report.get("artifact_roles"), list) else [],
        "audit_fingerprint": report.get("audit_fingerprint", ""),
    }


def build_source_adapter_release_audit_bridge(
    release_index_bridge_package: Mapping[str, Any],
    *,
    auditor_id: str = "manual_auditor",
    audit_profile: str = "source_adapter_shared_release_audit_v1",
    audit_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Release Audit outputs from Adapter Release Index Bridge output."""

    package = _as_mapping(release_index_bridge_package, "release_index_bridge_package")
    if package.get("release_index_bridge_status") != "SHARED_RELEASE_INDEXES_BUILT":
        raise ValueError("release index bridge package must be SHARED_RELEASE_INDEXES_BUILT")
    handoff = package.get("source_adapter_release_audit_batch_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_RELEASE_AUDIT":
        raise ValueError("release index bridge handoff must be READY_FOR_SHARED_RELEASE_AUDIT")
    if handoff.get("ready_for_release_audit") is not True:
        raise ValueError("release index bridge handoff must be ready_for_release_audit")

    notes = _normalise_notes(audit_notes)
    release_index_outputs = _release_index_outputs(package)
    if not release_index_outputs:
        raise ValueError("at least one Release Index output is required")

    release_audit_outputs: list[dict[str, Any]] = []
    release_audit_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_release_audit_ids: set[str] = set()

    for index, output in enumerate(release_index_outputs):
        release_index_record, release_inventory, export_bundle_handoff = _release_index_output_parts(output, index)
        release_index_id = _safe_id(release_index_record.get("release_index_id"), label="release_index_id", fallback=f"release_index_{index}")
        try:
            outputs = build_source_release_audit(
                release_index_record=release_index_record,
                release_inventory=release_inventory,
                export_bundle_handoff=export_bundle_handoff,
                auditor_id=auditor_id,
                audit_profile=audit_profile,
                audit_notes=notes,
            ).as_dict()
            row = _row_from_audit_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            issue_rows.append(f"{release_index_id}: {exc}")
            continue
        if row["release_audit_id"] in seen_release_audit_ids:
            issue_rows.append(f"duplicate release audit id: {row['release_audit_id']}")
            continue
        seen_release_audit_ids.add(row["release_audit_id"])
        release_audit_outputs.append(dict(outputs))
        release_audit_rows.append(row)

    built = bool(release_audit_outputs) and not issue_rows
    release_audit_batch = {
        "schema_version": RELEASE_AUDIT_BATCH_SCHEMA_VERSION,
        "release_audit_count": len(release_audit_outputs),
        "release_audit_rows": release_audit_rows,
        "audit_profile": audit_profile,
    }
    archive_handoff_batch = {
        "schema_version": ARCHIVE_HANDOFF_BATCH_SCHEMA_VERSION,
        "handoff_status": ARCHIVE_HANDOFF_READY_STATUS if built else "RELEASE_AUDIT_BRIDGE_BLOCKED",
        "ready_for_archive_handoff": built,
        "required_next_stage": "source_archive_handoff",
        "release_audit_ids": [row["release_audit_id"] for row in release_audit_rows],
        "archive_handoff_inputs": [
            {
                "role": "source_release_audit_report",
                "id": row["release_audit_id"],
                "filename_hint": f"{row['release_audit_id']}.source_release_audit_report.json",
            }
            for row in release_audit_rows
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": RELEASE_AUDIT_BRIDGE_STATUS if built else "RELEASE_AUDIT_BRIDGE_BLOCKED",
        "release_audit_count": len(release_audit_outputs),
        "issue_count": len(issue_rows),
        "audit_profile": audit_profile,
        "audit_notes": notes,
        "implemented_stage": "source_release_audit",
        "next_actions": [
            "Pass release-audit outputs and archive handoff metadata to the source_archive_handoff stage.",
            "Keep Release Index, Approved Release, Evidence Review, and Evidence Queue records immutable.",
            "Use this shared release-audit bridge for future adapters unless a source has a genuinely unique audit-shape requirement.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "release_audit_bridge_status": RELEASE_AUDIT_BRIDGE_STATUS if built else "RELEASE_AUDIT_BRIDGE_BLOCKED",
        "source_adapter_release_index_bridge_id": _safe_text(package.get("source_adapter_release_index_bridge_id"), ""),
        "release_audit_count": len(release_audit_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "release_audit_outputs": release_audit_outputs,
        "source_adapter_release_audit_batch": release_audit_batch,
        "source_adapter_archive_handoff_batch_handoff": archive_handoff_batch,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_release_audit",
            "input_source": "source_adapter_release_index_bridge",
            "per_adapter_path": "release_index_output_plus_shared_release_audit_builder",
            "multi_adapter_batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_release_audit_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned)
    result["source_adapter_release_audit_bridge_id"] = bridge_id
    result["source_adapter_release_audit_batch"] = dict(release_audit_batch, source_adapter_release_audit_bridge_id=bridge_id)
    result["source_adapter_archive_handoff_batch_handoff"] = dict(archive_handoff_batch, source_adapter_release_audit_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_release_audit_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_release_audit_bridge_package": dict(pkg),
        "source_adapter_release_audit_output_batch": deepcopy(pkg.get("release_audit_outputs", [])),
        "source_adapter_release_audit_batch": deepcopy(pkg.get("source_adapter_release_audit_batch", {})),
        "source_adapter_archive_handoff_batch_handoff": deepcopy(pkg.get("source_adapter_archive_handoff_batch_handoff", {})),
        "source_adapter_release_audit_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_release_index_bridge import build_source_adapter_release_index_bridge
    from source_adapter_release_index_bridge_test import fixture_approved_release_bridge

    release_index_bridge = build_source_adapter_release_index_bridge(fixture_approved_release_bridge())
    result = build_source_adapter_release_audit_bridge(release_index_bridge)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
