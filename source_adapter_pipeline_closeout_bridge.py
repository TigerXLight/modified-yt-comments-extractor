from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_pipeline_closeout import build_source_pipeline_closeout

SCHEMA_VERSION = "source_adapter_pipeline_closeout_bridge_v1"
PIPELINE_CLOSEOUT_BATCH_SCHEMA_VERSION = "source_adapter_pipeline_closeout_batch_v1"
ROADMAP_HANDOFF_SCHEMA_VERSION = "source_adapter_shared_pipeline_roadmap_closeout_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_pipeline_closeout_bridge_operator_summary_v1"
PIPELINE_CLOSEOUT_BRIDGE_STATUS = "SHARED_PIPELINE_CLOSEOUTS_BUILT"
SHARED_PIPELINE_COMPLETE_STATUS = "SOURCE_ADAPTER_SHARED_PIPELINE_COMPLETE"

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


def _archive_review_outputs(archive_review_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(archive_review_bridge_package.get("archive_review_outputs"), "archive_review_outputs")


def _output_parts(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    package = _as_mapping(output.get("archive_review_package"), f"archive_review_outputs[{index}].archive_review_package")
    decision = _as_mapping(output.get("archive_review_decision"), f"archive_review_outputs[{index}].archive_review_decision")
    closeout = _as_mapping(output.get("archive_review_closeout"), f"archive_review_outputs[{index}].archive_review_closeout")
    return package, decision, closeout


def _row_from_pipeline_closeout(output: Mapping[str, Any]) -> dict[str, Any]:
    report = _as_mapping(output.get("closeout_report"), "closeout_report")
    inventory = _as_mapping(output.get("stage_inventory"), "stage_inventory")
    handoff = _as_mapping(output.get("roadmap_closeout_handoff"), "roadmap_closeout_handoff")
    summary = _as_mapping(output.get("operator_summary"), "operator_summary")
    closeout_id = _safe_id(report.get("source_pipeline_closeout_id"), label="source_pipeline_closeout_id")
    return {
        "source_pipeline_closeout_id": closeout_id,
        "adapter_id": _safe_text(report.get("adapter_id"), ""),
        "source_url": _safe_text(report.get("source_url"), ""),
        "queue_item_id": _safe_text(report.get("pipeline_ids", {}).get("queue_item_id") if isinstance(report.get("pipeline_ids"), Mapping) else "", ""),
        "total_export_package_id": _safe_text(report.get("pipeline_ids", {}).get("total_export_package_id") if isinstance(report.get("pipeline_ids"), Mapping) else "", ""),
        "approved_release_id": _safe_text(report.get("pipeline_ids", {}).get("approved_release_id") if isinstance(report.get("pipeline_ids"), Mapping) else "", ""),
        "release_index_id": _safe_text(report.get("pipeline_ids", {}).get("release_index_id") if isinstance(report.get("pipeline_ids"), Mapping) else "", ""),
        "release_audit_id": _safe_text(report.get("pipeline_ids", {}).get("release_audit_id") if isinstance(report.get("pipeline_ids"), Mapping) else "", ""),
        "archive_handoff_id": _safe_text(report.get("pipeline_ids", {}).get("archive_handoff_id") if isinstance(report.get("pipeline_ids"), Mapping) else "", ""),
        "archive_result_intake_id": _safe_text(report.get("pipeline_ids", {}).get("archive_result_intake_id") if isinstance(report.get("pipeline_ids"), Mapping) else "", ""),
        "archive_review_package_id": _safe_text(report.get("archive_review_package_id"), ""),
        "archive_review_decision_id": _safe_text(report.get("archive_review_decision_id"), ""),
        "archive_review_closeout_id": _safe_text(report.get("archive_review_closeout_id"), ""),
        "final_status": _safe_text(report.get("final_status"), ""),
        "archive_decision": _safe_text(report.get("archive_decision"), ""),
        "stage_count": int(inventory.get("stage_count") or 0),
        "complete_stage_count": int(inventory.get("complete_stage_count") or 0),
        "follow_up_stage_count": int(inventory.get("follow_up_stage_count") or 0),
        "remaining_follow_up_stages": list(handoff.get("remaining_follow_up_stages") or []),
        "operator_action_required": bool(summary.get("operator_action_required")),
    }


def build_source_adapter_pipeline_closeout_bridge(
    archive_review_bridge_package: Mapping[str, Any],
    *,
    operator_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared pipeline closeout outputs from Adapter Archive Review Bridge output."""

    package = _as_mapping(archive_review_bridge_package, "archive_review_bridge_package")
    if package.get("archive_review_bridge_status") != "SHARED_ARCHIVE_REVIEWS_BUILT":
        raise ValueError("archive review bridge package must be SHARED_ARCHIVE_REVIEWS_BUILT")
    handoff = package.get("source_adapter_pipeline_closeout_batch_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_PIPELINE_CLOSEOUT":
        raise ValueError("archive review bridge handoff must be READY_FOR_SHARED_PIPELINE_CLOSEOUT")
    if handoff.get("ready_for_pipeline_closeout") is not True:
        raise ValueError("archive review bridge handoff must be ready_for_pipeline_closeout")

    notes = _normalise_notes(operator_notes)
    archive_review_outputs = _archive_review_outputs(package)
    if not archive_review_outputs:
        raise ValueError("at least one Archive Review output is required")

    pipeline_closeout_outputs: list[dict[str, Any]] = []
    pipeline_closeout_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_closeout_ids: set[str] = set()

    for index, output in enumerate(archive_review_outputs):
        archive_review_package, archive_review_decision, archive_review_closeout = _output_parts(output, index)
        archive_review_package_id = _safe_id(
            archive_review_package.get("archive_review_package_id"),
            label="archive_review_package_id",
            fallback=f"archive_review_{index}",
        )
        try:
            closeout_output = build_source_pipeline_closeout(
                archive_review_package,
                archive_review_decision=archive_review_decision,
                archive_review_closeout=archive_review_closeout,
                operator_notes=notes,
            )
            row = _row_from_pipeline_closeout(closeout_output)
        except Exception as exc:  # deterministic batch issue capture for operator review
            issue_rows.append(f"{archive_review_package_id}: {exc}")
            continue
        if row["source_pipeline_closeout_id"] in seen_closeout_ids:
            issue_rows.append(f"duplicate source pipeline closeout id: {row['source_pipeline_closeout_id']}")
            continue
        seen_closeout_ids.add(row["source_pipeline_closeout_id"])
        pipeline_closeout_outputs.append(dict(closeout_output))
        pipeline_closeout_rows.append(row)

    complete_count = sum(1 for row in pipeline_closeout_rows if row["final_status"] == "SOURCE_PIPELINE_COMPLETE")
    follow_up_count = len(pipeline_closeout_rows) - complete_count
    built = bool(pipeline_closeout_outputs) and not issue_rows
    shared_complete = built and complete_count == len(pipeline_closeout_rows) and bool(pipeline_closeout_rows)

    pipeline_closeout_batch = {
        "schema_version": PIPELINE_CLOSEOUT_BATCH_SCHEMA_VERSION,
        "pipeline_closeout_count": len(pipeline_closeout_outputs),
        "complete_count": complete_count,
        "follow_up_count": follow_up_count,
        "pipeline_closeout_rows": pipeline_closeout_rows,
    }
    roadmap_handoff = {
        "schema_version": ROADMAP_HANDOFF_SCHEMA_VERSION,
        "handoff_status": SHARED_PIPELINE_COMPLETE_STATUS if shared_complete else "SOURCE_ADAPTER_SHARED_PIPELINE_FOLLOW_UP_REQUIRED",
        "shared_pipeline_complete": shared_complete,
        "pipeline_closeout_count": len(pipeline_closeout_outputs),
        "complete_count": complete_count,
        "follow_up_count": follow_up_count,
        "source_pipeline_closeout_ids": [row["source_pipeline_closeout_id"] for row in pipeline_closeout_rows],
        "archive_review_package_ids": [row["archive_review_package_id"] for row in pipeline_closeout_rows],
        "completed_shared_stages": [
            "source_discovery",
            "lightweight_browser_capture",
            "artifact_collection",
            "content_extraction",
            "comments_extraction",
            "capture_bundle",
            "total_export_package",
            "evidence_queue",
            "evidence_review",
            "approved_release",
            "release_index",
            "release_audit",
            "archive_handoff",
            "archive_result_intake",
            "archive_review",
            "pipeline_closeout",
        ] if shared_complete else [],
        "required_next_stage": "source_adapter_runtime_wiring_or_fixture_expansion" if shared_complete else "source_archive_review_follow_up",
        "next_work_items": [
            "Wire explicit operator-approved runtime actions into the shared adapter flow where the roadmap calls for browser, URL, archive, release, or file-library execution.",
            "Expand adapter specs and fixture coverage without cloning the MSN-specific pipeline per source.",
            "Keep each live/provider mutation represented by a named approval record, action receipt, and deterministic local fixture.",
        ] if shared_complete else ["Resolve archive review follow-up rows before shared adapter closeout."],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": PIPELINE_CLOSEOUT_BRIDGE_STATUS if built else "PIPELINE_CLOSEOUT_BRIDGE_BLOCKED",
        "shared_pipeline_complete": shared_complete,
        "pipeline_closeout_count": len(pipeline_closeout_outputs),
        "complete_count": complete_count,
        "follow_up_count": follow_up_count,
        "issue_count": len(issue_rows),
        "operator_notes": notes,
        "implemented_stage": "source_pipeline_closeout",
        "next_actions": roadmap_handoff["next_work_items"],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_closeout_bridge_status": PIPELINE_CLOSEOUT_BRIDGE_STATUS if built else "PIPELINE_CLOSEOUT_BRIDGE_BLOCKED",
        "source_adapter_archive_review_bridge_id": _safe_text(package.get("source_adapter_archive_review_bridge_id"), ""),
        "pipeline_closeout_count": len(pipeline_closeout_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "pipeline_closeout_outputs": pipeline_closeout_outputs,
        "source_adapter_pipeline_closeout_batch": pipeline_closeout_batch,
        "source_adapter_shared_pipeline_roadmap_closeout_handoff": roadmap_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_pipeline_closeout",
            "input_stage": "source_adapter_archive_review_bridge",
            "output_stage": "source_adapter_runtime_wiring_or_fixture_expansion",
            "per_adapter_module_required": False,
            "batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_pipeline_closeout_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned, source_adapter_pipeline_closeout_bridge_id=bridge_id)
    result["source_adapter_pipeline_closeout_batch"] = dict(pipeline_closeout_batch, source_adapter_pipeline_closeout_bridge_id=bridge_id)
    result["source_adapter_shared_pipeline_roadmap_closeout_handoff"] = dict(roadmap_handoff, source_adapter_pipeline_closeout_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_pipeline_closeout_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_pipeline_closeout_bridge_package": dict(pkg),
        "source_adapter_pipeline_closeout_output_batch": deepcopy(pkg.get("pipeline_closeout_outputs", [])),
        "source_adapter_pipeline_closeout_batch": deepcopy(pkg.get("source_adapter_pipeline_closeout_batch", {})),
        "source_adapter_shared_pipeline_roadmap_closeout_handoff": deepcopy(pkg.get("source_adapter_shared_pipeline_roadmap_closeout_handoff", {})),
        "source_adapter_pipeline_closeout_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_pipeline_closeout_bridge_test import fixture_archive_review_bridge

    result = build_source_adapter_pipeline_closeout_bridge(fixture_archive_review_bridge())
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
