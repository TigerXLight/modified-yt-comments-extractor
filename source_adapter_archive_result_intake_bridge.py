from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from source_archive_result_intake import build_source_archive_result_intake

SCHEMA_VERSION = "source_adapter_archive_result_intake_bridge_v1"
ARCHIVE_RESULT_INTAKE_BATCH_SCHEMA_VERSION = "source_adapter_archive_result_intake_batch_v1"
ARCHIVE_REVIEW_BATCH_HANDOFF_SCHEMA_VERSION = "source_adapter_archive_review_batch_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_archive_result_intake_bridge_operator_summary_v1"
ARCHIVE_RESULT_INTAKE_BRIDGE_STATUS = "SHARED_ARCHIVE_RESULT_INTAKES_BUILT"
ARCHIVE_REVIEW_READY_STATUS = "READY_FOR_SHARED_ARCHIVE_REVIEW"

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


def _archive_handoff_outputs(archive_handoff_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(archive_handoff_bridge_package.get("archive_handoff_outputs"), "archive_handoff_outputs")


def _archive_handoff_output_parts(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    package = _as_mapping(output.get("archive_handoff_package"), f"archive_handoff_outputs[{index}].archive_handoff_package")
    tasks = _as_mapping(output.get("provider_tasks"), f"archive_handoff_outputs[{index}].provider_tasks")
    templates = _as_mapping(output.get("result_templates"), f"archive_handoff_outputs[{index}].result_templates")
    handoff = _as_mapping(output.get("result_intake_handoff"), f"archive_handoff_outputs[{index}].result_intake_handoff")
    return package, tasks, templates, handoff


def _normalise_operator_result_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        if isinstance(value.get("operator_archive_results"), list):
            return _as_mapping_list(value["operator_archive_results"], f"{label}.operator_archive_results")
        if isinstance(value.get("results"), list):
            return _as_mapping_list(value["results"], f"{label}.results")
        if value.get("schema_version") == "source_archive_operator_result_v1" or value.get("archive_url") or value.get("url"):
            return [value]
        raise TypeError(f"{label} mapping must contain operator_archive_results, results, or one operator result")
    if isinstance(value, list):
        return _as_mapping_list(value, label)
    raise TypeError(f"{label} must be a mapping or list")


def _group_operator_results(operator_archive_results: Any, archive_handoff_ids: Sequence[str]) -> dict[str, list[Mapping[str, Any]]]:
    if operator_archive_results is None:
        raise ValueError("operator archive results are required")
    wanted = set(archive_handoff_ids)
    grouped: dict[str, list[Mapping[str, Any]]] = {archive_handoff_id: [] for archive_handoff_id in archive_handoff_ids}

    if isinstance(operator_archive_results, Mapping):
        if isinstance(operator_archive_results.get("archive_results_by_handoff"), Mapping):
            source_map = operator_archive_results["archive_results_by_handoff"]
        elif isinstance(operator_archive_results.get("operator_archive_results_by_handoff"), Mapping):
            source_map = operator_archive_results["operator_archive_results_by_handoff"]
        elif any(_safe_text(key) in wanted for key in operator_archive_results.keys()):
            source_map = operator_archive_results
        elif len(archive_handoff_ids) == 1:
            grouped[archive_handoff_ids[0]] = _normalise_operator_result_list(operator_archive_results, "operator_archive_results")
            return grouped
        else:
            source_map = operator_archive_results
        for key, value in source_map.items():
            handoff_id = _safe_text(key)
            if handoff_id not in wanted:
                raise ValueError(f"operator archive results include unknown archive_handoff_id: {handoff_id}")
            grouped[handoff_id] = _normalise_operator_result_list(value, f"operator_archive_results[{handoff_id}]")
        return grouped

    result_list = _normalise_operator_result_list(operator_archive_results, "operator_archive_results")
    if len(archive_handoff_ids) == 1 and not any(_safe_text(result.get("archive_handoff_id")) for result in result_list):
        grouped[archive_handoff_ids[0]] = result_list
        return grouped
    for result in result_list:
        handoff_id = _safe_text(result.get("archive_handoff_id"))
        if not handoff_id:
            raise ValueError("each operator result must include archive_handoff_id for multi-handoff batches")
        if handoff_id not in wanted:
            raise ValueError(f"operator result references unknown archive_handoff_id: {handoff_id}")
        result_copy = dict(result)
        result_copy.pop("archive_handoff_id", None)
        grouped[handoff_id].append(result_copy)
    return grouped


def _row_from_result_intake_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    record = _as_mapping(outputs.get("archive_result_intake_record"), "archive_result_intake_record")
    receipt_index = _as_mapping(outputs.get("archive_receipt_index"), "archive_receipt_index")
    review_handoff = _as_mapping(outputs.get("archive_review_handoff"), "archive_review_handoff")
    summary = _as_mapping(outputs.get("operator_summary"), "operator_summary")
    archive_result_intake_id = _safe_id(record.get("archive_result_intake_id"), label="archive_result_intake_id")
    return {
        "adapter_id": _safe_text(record.get("adapter_id"), ""),
        "source_url": _safe_text(record.get("source_url"), ""),
        "queue_item_id": _safe_text(record.get("queue_item_id"), ""),
        "approved_release_id": _safe_text(record.get("approved_release_id"), ""),
        "release_index_id": _safe_text(record.get("release_index_id"), ""),
        "release_audit_id": _safe_text(record.get("release_audit_id"), ""),
        "archive_handoff_id": _safe_text(record.get("archive_handoff_id"), ""),
        "archive_result_intake_id": archive_result_intake_id,
        "intake_status": record.get("intake_status", ""),
        "archive_review_handoff_status": review_handoff.get("handoff_status", ""),
        "required_next_stage": review_handoff.get("required_next_stage", ""),
        "receipt_count": receipt_index.get("receipt_count", 0),
        "operator_supplied_result_count": record.get("operator_supplied_result_count", 0),
        "received_provider_ids": list(record.get("received_provider_ids", [])) if isinstance(record.get("received_provider_ids"), list) else [],
        "missing_provider_ids": list(record.get("missing_provider_ids", [])) if isinstance(record.get("missing_provider_ids"), list) else [],
        "operator_summary_status": summary.get("status", ""),
        "online_validation_performed": record.get("online_validation_performed"),
        "archive_submission_performed_by_app": record.get("archive_submission_performed_by_app"),
        "manual_or_live_actions_started_by_app": record.get("manual_or_live_actions_started_by_app"),
    }


def build_source_adapter_archive_result_intake_bridge(
    archive_handoff_bridge_package: Mapping[str, Any],
    operator_archive_results: Any,
    *,
    operator_id: str = "manual_archive_operator",
    intake_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Archive Result Intake outputs from Adapter Archive Handoff Bridge output."""

    package = _as_mapping(archive_handoff_bridge_package, "archive_handoff_bridge_package")
    if package.get("archive_handoff_bridge_status") != "SHARED_ARCHIVE_HANDOFFS_BUILT":
        raise ValueError("archive handoff bridge package must be SHARED_ARCHIVE_HANDOFFS_BUILT")
    handoff = package.get("source_adapter_archive_result_intake_batch_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_ARCHIVE_RESULT_INTAKE":
        raise ValueError("archive handoff bridge handoff must be READY_FOR_SHARED_ARCHIVE_RESULT_INTAKE")
    if handoff.get("ready_for_archive_result_intake") is not True:
        raise ValueError("archive handoff bridge handoff must be ready_for_archive_result_intake")

    notes = _normalise_notes(intake_notes)
    archive_handoff_outputs = _archive_handoff_outputs(package)
    if not archive_handoff_outputs:
        raise ValueError("at least one Archive Handoff output is required")

    handoff_ids: list[str] = []
    for index, output in enumerate(archive_handoff_outputs):
        archive_package, _, _, _ = _archive_handoff_output_parts(output, index)
        handoff_ids.append(_safe_id(archive_package.get("archive_handoff_id"), label="archive_handoff_id", fallback=f"archive_handoff_{index}"))
    grouped_results = _group_operator_results(operator_archive_results, handoff_ids)

    result_intake_outputs: list[dict[str, Any]] = []
    result_intake_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_result_intake_ids: set[str] = set()

    for index, output in enumerate(archive_handoff_outputs):
        archive_package, provider_tasks, result_templates, result_intake_handoff = _archive_handoff_output_parts(output, index)
        archive_handoff_id = handoff_ids[index]
        try:
            results = grouped_results.get(archive_handoff_id, [])
            if not results:
                raise ValueError("operator archive result list is empty")
            outputs = build_source_archive_result_intake(
                archive_handoff_package=archive_package,
                provider_tasks=provider_tasks,
                result_templates=result_templates,
                result_intake_handoff=result_intake_handoff,
                operator_archive_results=results,
                operator_id=operator_id,
                intake_notes=notes,
            ).as_dict()
            row = _row_from_result_intake_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            issue_rows.append(f"{archive_handoff_id}: {exc}")
            continue
        if row["archive_result_intake_id"] in seen_result_intake_ids:
            issue_rows.append(f"duplicate archive result intake id: {row['archive_result_intake_id']}")
            continue
        seen_result_intake_ids.add(row["archive_result_intake_id"])
        result_intake_outputs.append(dict(outputs))
        result_intake_rows.append(row)

    built = bool(result_intake_outputs) and not issue_rows
    archive_result_intake_batch = {
        "schema_version": ARCHIVE_RESULT_INTAKE_BATCH_SCHEMA_VERSION,
        "archive_result_intake_count": len(result_intake_outputs),
        "archive_result_intake_rows": result_intake_rows,
        "archive_handoff_ids": [row["archive_handoff_id"] for row in result_intake_rows],
        "archive_result_intake_ids": [row["archive_result_intake_id"] for row in result_intake_rows],
        "receipt_count": sum(int(row.get("receipt_count") or 0) for row in result_intake_rows),
        "operator_supplied_result_count": sum(int(row.get("operator_supplied_result_count") or 0) for row in result_intake_rows),
    }
    archive_review_batch_handoff = {
        "schema_version": ARCHIVE_REVIEW_BATCH_HANDOFF_SCHEMA_VERSION,
        "handoff_status": ARCHIVE_REVIEW_READY_STATUS if built else "ARCHIVE_RESULT_INTAKE_BRIDGE_BLOCKED",
        "ready_for_archive_review": built,
        "required_next_stage": "source_archive_review",
        "archive_result_intake_ids": [row["archive_result_intake_id"] for row in result_intake_rows],
        "archive_review_inputs": [
            {
                "role": "source_archive_review_handoff",
                "id": row["archive_result_intake_id"],
                "filename_hint": f"{row['archive_result_intake_id']}.source_archive_review_handoff.json",
            }
            for row in result_intake_rows
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": ARCHIVE_RESULT_INTAKE_BRIDGE_STATUS if built else "ARCHIVE_RESULT_INTAKE_BRIDGE_BLOCKED",
        "archive_result_intake_count": len(result_intake_outputs),
        "issue_count": len(issue_rows),
        "receipt_count": archive_result_intake_batch["receipt_count"],
        "operator_supplied_result_count": archive_result_intake_batch["operator_supplied_result_count"],
        "intake_notes": notes,
        "implemented_stage": "source_archive_result_intake",
        "next_actions": [
            "Route each archive result intake output to the shared source_archive_review stage.",
            "Record archive-review decisions against the operator-supplied archive URLs and receipts.",
            "Use this shared archive result intake bridge for future adapters unless a source has a genuinely unique archive-result shape.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "archive_result_intake_bridge_status": ARCHIVE_RESULT_INTAKE_BRIDGE_STATUS if built else "ARCHIVE_RESULT_INTAKE_BRIDGE_BLOCKED",
        "source_adapter_archive_handoff_bridge_id": _safe_text(package.get("source_adapter_archive_handoff_bridge_id"), ""),
        "archive_result_intake_count": len(result_intake_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "archive_result_intake_outputs": result_intake_outputs,
        "source_adapter_archive_result_intake_batch": archive_result_intake_batch,
        "source_adapter_archive_review_batch_handoff": archive_review_batch_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_archive_result_intake",
            "input_stage": "source_adapter_archive_handoff_bridge",
            "output_stage": "source_archive_review",
            "per_adapter_module_required": False,
            "batch_supported": True,
            "operator_archive_results_grouped_by_handoff": True,
        },
    }
    bridge_id = f"source_adapter_archive_result_intake_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned, source_adapter_archive_result_intake_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_archive_result_intake_bridge_package": dict(pkg),
        "source_adapter_archive_result_intake_output_batch": deepcopy(pkg.get("archive_result_intake_outputs", [])),
        "source_adapter_archive_result_intake_batch": deepcopy(pkg.get("source_adapter_archive_result_intake_batch", {})),
        "source_adapter_archive_review_batch_handoff": deepcopy(pkg.get("source_adapter_archive_review_batch_handoff", {})),
        "source_adapter_archive_result_intake_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_archive_handoff_bridge import build_source_adapter_archive_handoff_bridge
    from source_adapter_archive_handoff_bridge_test import fixture_release_audit_bridge

    archive_handoff_bridge = build_source_adapter_archive_handoff_bridge(fixture_release_audit_bridge())
    first_handoff_id = archive_handoff_bridge["archive_handoff_outputs"][0]["archive_handoff_package"]["archive_handoff_id"]
    result = build_source_adapter_archive_result_intake_bridge(
        archive_handoff_bridge,
        {first_handoff_id: [{"schema_version": "source_archive_operator_result_v1", "provider_id": "archive_today", "archive_url": "https://archive.example/fixture-story"}]},
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
