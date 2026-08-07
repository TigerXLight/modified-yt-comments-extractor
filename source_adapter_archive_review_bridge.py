from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_archive_review import build_source_archive_review

SCHEMA_VERSION = "source_adapter_archive_review_bridge_v1"
ARCHIVE_REVIEW_BATCH_SCHEMA_VERSION = "source_adapter_archive_review_batch_v1"
PIPELINE_CLOSEOUT_HANDOFF_SCHEMA_VERSION = "source_adapter_pipeline_closeout_batch_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_archive_review_bridge_operator_summary_v1"
ARCHIVE_REVIEW_BRIDGE_STATUS = "SHARED_ARCHIVE_REVIEWS_BUILT"
PIPELINE_CLOSEOUT_HANDOFF_STATUS = "READY_FOR_SHARED_PIPELINE_CLOSEOUT"

_ALLOWED_DECISIONS = {"APPROVED", "REJECTED", "REVISION_REQUESTED"}
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


def _normalise_decision(value: Any) -> dict[str, Any]:
    if value is None:
        return {"decision": "APPROVED"}
    if isinstance(value, str):
        decision = value.strip().upper()
        if decision not in _ALLOWED_DECISIONS:
            raise ValueError("archive review decision must be APPROVED, REJECTED, or REVISION_REQUESTED")
        return {"decision": decision}
    decision = dict(_as_mapping(value, "archive_reviewer_decision"))
    if "decision" not in decision and "review_decision" in decision:
        decision["decision"] = decision["review_decision"]
    if "decision" not in decision and "archive_decision" in decision:
        decision["decision"] = decision["archive_decision"]
    decision_text = _safe_text(decision.get("decision"), "APPROVED").upper()
    if decision_text not in _ALLOWED_DECISIONS:
        raise ValueError("archive review decision must be APPROVED, REJECTED, or REVISION_REQUESTED")
    decision["decision"] = decision_text
    return decision


def _decision_for_intake(archive_reviewer_decision: Any, archive_result_intake_id: str) -> dict[str, Any]:
    if archive_reviewer_decision is None:
        return {"decision": "APPROVED"}
    if isinstance(archive_reviewer_decision, str):
        return _normalise_decision(archive_reviewer_decision)
    decision_root = _as_mapping(archive_reviewer_decision, "archive_reviewer_decision")
    by_id = decision_root.get("decisions_by_archive_result_intake_id")
    if isinstance(by_id, Mapping) and isinstance(by_id.get(archive_result_intake_id), (Mapping, str)):
        return _normalise_decision(by_id[archive_result_intake_id])
    per_item = decision_root.get("per_archive_result_intake_decisions")
    if isinstance(per_item, list):
        for item in per_item:
            if isinstance(item, Mapping) and _safe_text(item.get("archive_result_intake_id")) == archive_result_intake_id:
                return _normalise_decision(item)
    shared = {
        key: value
        for key, value in decision_root.items()
        if key not in {"decisions_by_archive_result_intake_id", "per_archive_result_intake_decisions"}
    }
    return _normalise_decision(shared)


def _archive_result_intake_outputs(archive_result_intake_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(archive_result_intake_bridge_package.get("archive_result_intake_outputs"), "archive_result_intake_outputs")


def _output_parts(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    record = _as_mapping(output.get("archive_result_intake_record"), f"archive_result_intake_outputs[{index}].archive_result_intake_record")
    receipt_index = _as_mapping(output.get("archive_receipt_index"), f"archive_result_intake_outputs[{index}].archive_receipt_index")
    handoff = _as_mapping(output.get("archive_review_handoff"), f"archive_result_intake_outputs[{index}].archive_review_handoff")
    return record, receipt_index, handoff


def _row_from_archive_review_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    package = _as_mapping(outputs.get("archive_review_package"), "archive_review_package")
    decision = _as_mapping(outputs.get("archive_review_decision"), "archive_review_decision")
    closeout = _as_mapping(outputs.get("archive_review_closeout"), "archive_review_closeout")
    summary = _as_mapping(outputs.get("operator_summary"), "operator_summary")
    archive_review_package_id = _safe_id(package.get("archive_review_package_id"), label="archive_review_package_id")
    return {
        "adapter_id": _safe_text(package.get("adapter_id"), ""),
        "source_url": _safe_text(package.get("source_url"), ""),
        "queue_item_id": _safe_text(package.get("queue_item_id"), ""),
        "capture_bundle_id": _safe_text(package.get("capture_bundle_id"), ""),
        "total_export_package_id": _safe_text(package.get("total_export_package_id"), ""),
        "evidence_review_package_id": _safe_text(package.get("evidence_review_package_id"), ""),
        "approved_release_id": _safe_text(package.get("approved_release_id"), ""),
        "release_index_id": _safe_text(package.get("release_index_id"), ""),
        "release_audit_id": _safe_text(package.get("release_audit_id"), ""),
        "archive_handoff_id": _safe_text(package.get("archive_handoff_id"), ""),
        "archive_result_intake_id": _safe_text(package.get("archive_result_intake_id"), ""),
        "archive_review_package_id": archive_review_package_id,
        "review_status": package.get("review_status", ""),
        "decision": decision.get("decision", ""),
        "decision_status": decision.get("decision_status", ""),
        "closeout_status": closeout.get("closeout_status", ""),
        "source_pipeline_status": closeout.get("source_pipeline_status", ""),
        "required_next_stage": closeout.get("required_next_stage", ""),
        "ready_for_final_closeout": bool(decision.get("ready_for_final_closeout")),
        "receipt_count": package.get("receipt_count", 0),
        "approved_receipt_count": package.get("approved_receipt_count", 0),
        "needs_operator_followup": bool(summary.get("needs_operator_followup")),
    }


def build_source_adapter_archive_review_bridge(
    archive_result_intake_bridge_package: Mapping[str, Any],
    *,
    archive_reviewer_decision: Any = None,
    reviewer_id: str = "manual_archive_reviewer",
    review_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Archive Review outputs from Adapter Archive Result Intake Bridge output."""

    package = _as_mapping(archive_result_intake_bridge_package, "archive_result_intake_bridge_package")
    if package.get("archive_result_intake_bridge_status") != "SHARED_ARCHIVE_RESULT_INTAKES_BUILT":
        raise ValueError("archive result intake bridge package must be SHARED_ARCHIVE_RESULT_INTAKES_BUILT")
    handoff = package.get("source_adapter_archive_review_batch_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_ARCHIVE_REVIEW":
        raise ValueError("archive result intake bridge handoff must be READY_FOR_SHARED_ARCHIVE_REVIEW")
    if handoff.get("ready_for_archive_review") is not True:
        raise ValueError("archive result intake bridge handoff must be ready_for_archive_review")

    notes = _normalise_notes(review_notes)
    intake_outputs = _archive_result_intake_outputs(package)
    if not intake_outputs:
        raise ValueError("at least one Archive Result Intake output is required")

    archive_review_outputs: list[dict[str, Any]] = []
    archive_review_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_review_ids: set[str] = set()

    for index, output in enumerate(intake_outputs):
        record, receipt_index, archive_review_handoff = _output_parts(output, index)
        archive_result_intake_id = _safe_id(
            record.get("archive_result_intake_id"),
            label="archive_result_intake_id",
            fallback=f"archive_result_intake_{index}",
        )
        try:
            decision = _decision_for_intake(archive_reviewer_decision, archive_result_intake_id)
            outputs = build_source_archive_review(
                archive_result_intake_record=record,
                archive_receipt_index=receipt_index,
                archive_review_handoff=archive_review_handoff,
                reviewer_id=reviewer_id,
                decision=decision["decision"],
                review_notes=notes + _normalise_notes(decision.get("review_notes") if isinstance(decision.get("review_notes"), list) else None),
            ).as_dict()
            row = _row_from_archive_review_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            issue_rows.append(f"{archive_result_intake_id}: {exc}")
            continue
        if row["archive_review_package_id"] in seen_review_ids:
            issue_rows.append(f"duplicate archive review package id: {row['archive_review_package_id']}")
            continue
        seen_review_ids.add(row["archive_review_package_id"])
        archive_review_outputs.append(dict(outputs))
        archive_review_rows.append(row)

    built = bool(archive_review_outputs) and not issue_rows
    approved_count = sum(1 for row in archive_review_rows if row["decision"] == "APPROVED")
    rejected_count = sum(1 for row in archive_review_rows if row["decision"] == "REJECTED")
    revision_count = sum(1 for row in archive_review_rows if row["decision"] == "REVISION_REQUESTED")
    archive_complete_count = sum(1 for row in archive_review_rows if row["closeout_status"] == "ARCHIVE_COMPLETE")
    ready_for_pipeline_closeout = built and approved_count == len(archive_review_rows) and bool(archive_review_rows)

    archive_review_batch = {
        "schema_version": ARCHIVE_REVIEW_BATCH_SCHEMA_VERSION,
        "archive_review_count": len(archive_review_outputs),
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "revision_requested_count": revision_count,
        "archive_complete_count": archive_complete_count,
        "receipt_count": sum(int(row.get("receipt_count") or 0) for row in archive_review_rows),
        "approved_receipt_count": sum(int(row.get("approved_receipt_count") or 0) for row in archive_review_rows),
        "archive_review_rows": archive_review_rows,
    }
    pipeline_closeout_handoff = {
        "schema_version": PIPELINE_CLOSEOUT_HANDOFF_SCHEMA_VERSION,
        "handoff_status": PIPELINE_CLOSEOUT_HANDOFF_STATUS if ready_for_pipeline_closeout else "ARCHIVE_REVIEW_BRIDGE_PENDING_OR_BLOCKED",
        "ready_for_pipeline_closeout": ready_for_pipeline_closeout,
        "required_next_stage": "source_pipeline_closeout" if ready_for_pipeline_closeout else "source_archive_result_intake_or_review_retry",
        "archive_review_package_ids": [row["archive_review_package_id"] for row in archive_review_rows],
        "archive_result_intake_ids": [row["archive_result_intake_id"] for row in archive_review_rows],
        "pipeline_closeout_inputs": [
            {
                "role": "source_archive_review_closeout",
                "id": row["archive_review_package_id"],
                "filename_hint": f"{row['archive_review_package_id']}.source_archive_review_closeout.json",
            }
            for row in archive_review_rows
            if row["closeout_status"] == "ARCHIVE_COMPLETE"
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": ARCHIVE_REVIEW_BRIDGE_STATUS if built else "ARCHIVE_REVIEW_BRIDGE_BLOCKED",
        "archive_review_count": len(archive_review_outputs),
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "revision_requested_count": revision_count,
        "archive_complete_count": archive_complete_count,
        "issue_count": len(issue_rows),
        "reviewer_id": reviewer_id,
        "review_notes": notes,
        "implemented_stage": "source_archive_review",
        "next_actions": [
            "Pass approved archive review closeouts to the shared source_pipeline_closeout stage.",
            "Use rejected or revision-requested archive review rows to trigger explicit archive-result retry or review follow-up.",
            "Reuse this shared archive review bridge for future adapters unless archive-review evidence shape becomes adapter-specific.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "archive_review_bridge_status": ARCHIVE_REVIEW_BRIDGE_STATUS if built else "ARCHIVE_REVIEW_BRIDGE_BLOCKED",
        "source_adapter_archive_result_intake_bridge_id": _safe_text(package.get("source_adapter_archive_result_intake_bridge_id"), ""),
        "archive_review_count": len(archive_review_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "archive_review_outputs": archive_review_outputs,
        "source_adapter_archive_review_batch": archive_review_batch,
        "source_adapter_pipeline_closeout_batch_handoff": pipeline_closeout_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_archive_review",
            "input_stage": "source_adapter_archive_result_intake_bridge",
            "output_stage": "source_pipeline_closeout",
            "per_adapter_module_required": False,
            "batch_supported": True,
            "per_archive_result_intake_decisions_supported": True,
        },
    }
    bridge_id = f"source_adapter_archive_review_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned, source_adapter_archive_review_bridge_id=bridge_id)
    result["source_adapter_archive_review_batch"] = dict(archive_review_batch, source_adapter_archive_review_bridge_id=bridge_id)
    result["source_adapter_pipeline_closeout_batch_handoff"] = dict(pipeline_closeout_handoff, source_adapter_archive_review_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_archive_review_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_archive_review_bridge_package": dict(pkg),
        "source_adapter_archive_review_output_batch": deepcopy(pkg.get("archive_review_outputs", [])),
        "source_adapter_archive_review_batch": deepcopy(pkg.get("source_adapter_archive_review_batch", {})),
        "source_adapter_pipeline_closeout_batch_handoff": deepcopy(pkg.get("source_adapter_pipeline_closeout_batch_handoff", {})),
        "source_adapter_archive_review_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_archive_result_intake_bridge_test import fixture_archive_handoff_bridge, fixture_operator_results
    from source_adapter_archive_result_intake_bridge import build_source_adapter_archive_result_intake_bridge

    archive_handoff_bridge = fixture_archive_handoff_bridge()
    archive_result_intake_bridge = build_source_adapter_archive_result_intake_bridge(
        archive_handoff_bridge,
        fixture_operator_results(archive_handoff_bridge),
    )
    result = build_source_adapter_archive_review_bridge(archive_result_intake_bridge, archive_reviewer_decision={"decision": "APPROVED"})
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
