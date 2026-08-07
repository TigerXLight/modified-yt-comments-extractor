from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from source_archive_handoff import build_source_archive_handoff

SCHEMA_VERSION = "source_adapter_archive_handoff_bridge_v1"
ARCHIVE_HANDOFF_BATCH_SCHEMA_VERSION = "source_adapter_archive_handoff_batch_v1"
ARCHIVE_RESULT_INTAKE_BATCH_SCHEMA_VERSION = "source_adapter_archive_result_intake_batch_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_archive_handoff_bridge_operator_summary_v1"
ARCHIVE_HANDOFF_BRIDGE_STATUS = "SHARED_ARCHIVE_HANDOFFS_BUILT"
ARCHIVE_RESULT_INTAKE_READY_STATUS = "READY_FOR_SHARED_ARCHIVE_RESULT_INTAKE"

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


def _release_audit_outputs(release_audit_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(release_audit_bridge_package.get("release_audit_outputs"), "release_audit_outputs")


def _release_audit_output_parts(output: Mapping[str, Any], index: int) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    report = _as_mapping(output.get("release_audit_report"), f"release_audit_outputs[{index}].release_audit_report")
    traceability = _as_mapping(output.get("traceability_map"), f"release_audit_outputs[{index}].traceability_map")
    archive_handoff = _as_mapping(output.get("archive_handoff"), f"release_audit_outputs[{index}].archive_handoff")
    return report, traceability, archive_handoff


def _row_from_archive_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    package = _as_mapping(outputs.get("archive_handoff_package"), "archive_handoff_package")
    tasks = _as_mapping(outputs.get("provider_tasks"), "provider_tasks")
    templates = _as_mapping(outputs.get("result_templates"), "result_templates")
    intake = _as_mapping(outputs.get("result_intake_handoff"), "result_intake_handoff")
    archive_handoff_id = _safe_id(package.get("archive_handoff_id"), label="archive_handoff_id")
    return {
        "adapter_id": _safe_text(package.get("adapter_id"), ""),
        "source_url": _safe_text(package.get("source_url"), ""),
        "queue_item_id": _safe_text(package.get("queue_item_id"), ""),
        "approved_release_id": _safe_text(package.get("approved_release_id"), ""),
        "release_index_id": _safe_text(package.get("release_index_id"), ""),
        "release_audit_id": _safe_text(package.get("release_audit_id"), ""),
        "archive_handoff_id": archive_handoff_id,
        "handoff_status": package.get("handoff_status", ""),
        "provider_task_status": tasks.get("task_status", ""),
        "template_status": templates.get("template_status", ""),
        "result_intake_handoff_status": intake.get("handoff_status", ""),
        "required_next_stage": intake.get("required_next_stage", ""),
        "archive_provider_count": package.get("archive_provider_count", 0),
        "archive_providers": list(package.get("archive_providers", [])) if isinstance(package.get("archive_providers"), list) else [],
        "artifact_count": package.get("artifact_count", 0),
        "artifact_roles": list(package.get("artifact_roles", [])) if isinstance(package.get("artifact_roles"), list) else [],
        "archive_submission_started": package.get("archive_submission_started"),
        "manual_or_live_actions_started": package.get("manual_or_live_actions_started"),
        "handoff_fingerprint": package.get("handoff_fingerprint", ""),
    }


def build_source_adapter_archive_handoff_bridge(
    release_audit_bridge_package: Mapping[str, Any],
    *,
    archive_providers: Sequence[str] | None = None,
    operator_id: str = "manual_archive_operator",
    handoff_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared Archive Handoff outputs from Adapter Release Audit Bridge output."""

    package = _as_mapping(release_audit_bridge_package, "release_audit_bridge_package")
    if package.get("release_audit_bridge_status") != "SHARED_RELEASE_AUDITS_BUILT":
        raise ValueError("release audit bridge package must be SHARED_RELEASE_AUDITS_BUILT")
    handoff = package.get("source_adapter_archive_handoff_batch_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_ARCHIVE_HANDOFF":
        raise ValueError("release audit bridge handoff must be READY_FOR_SHARED_ARCHIVE_HANDOFF")
    if handoff.get("ready_for_archive_handoff") is not True:
        raise ValueError("release audit bridge handoff must be ready_for_archive_handoff")

    notes = _normalise_notes(handoff_notes)
    release_audit_outputs = _release_audit_outputs(package)
    if not release_audit_outputs:
        raise ValueError("at least one Release Audit output is required")

    archive_handoff_outputs: list[dict[str, Any]] = []
    archive_handoff_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    seen_archive_handoff_ids: set[str] = set()

    for index, output in enumerate(release_audit_outputs):
        report, traceability, release_archive_handoff = _release_audit_output_parts(output, index)
        release_audit_id = _safe_id(report.get("release_audit_id"), label="release_audit_id", fallback=f"release_audit_{index}")
        try:
            outputs = build_source_archive_handoff(
                release_audit_report=report,
                traceability_map=traceability,
                release_archive_handoff=release_archive_handoff,
                archive_providers=archive_providers,
                operator_id=operator_id,
                handoff_notes=notes,
            ).as_dict()
            row = _row_from_archive_outputs(outputs)
        except Exception as exc:  # deterministic batch issue capture for operator review
            issue_rows.append(f"{release_audit_id}: {exc}")
            continue
        if row["archive_handoff_id"] in seen_archive_handoff_ids:
            issue_rows.append(f"duplicate archive handoff id: {row['archive_handoff_id']}")
            continue
        seen_archive_handoff_ids.add(row["archive_handoff_id"])
        archive_handoff_outputs.append(dict(outputs))
        archive_handoff_rows.append(row)

    built = bool(archive_handoff_outputs) and not issue_rows
    archive_handoff_batch = {
        "schema_version": ARCHIVE_HANDOFF_BATCH_SCHEMA_VERSION,
        "archive_handoff_count": len(archive_handoff_outputs),
        "archive_handoff_rows": archive_handoff_rows,
        "archive_providers": sorted({provider for row in archive_handoff_rows for provider in row.get("archive_providers", [])}),
    }
    result_intake_batch_handoff = {
        "schema_version": ARCHIVE_RESULT_INTAKE_BATCH_SCHEMA_VERSION,
        "handoff_status": ARCHIVE_RESULT_INTAKE_READY_STATUS if built else "ARCHIVE_HANDOFF_BRIDGE_BLOCKED",
        "ready_for_archive_result_intake": built,
        "required_next_stage": "source_archive_result_intake",
        "archive_handoff_ids": [row["archive_handoff_id"] for row in archive_handoff_rows],
        "archive_result_intake_inputs": [
            {
                "role": "source_archive_result_intake_handoff",
                "id": row["archive_handoff_id"],
                "filename_hint": f"{row['archive_handoff_id']}.source_archive_result_intake_handoff.json",
            }
            for row in archive_handoff_rows
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": ARCHIVE_HANDOFF_BRIDGE_STATUS if built else "ARCHIVE_HANDOFF_BRIDGE_BLOCKED",
        "archive_handoff_count": len(archive_handoff_outputs),
        "issue_count": len(issue_rows),
        "archive_provider_count": len(archive_handoff_batch["archive_providers"]),
        "archive_providers": archive_handoff_batch["archive_providers"],
        "handoff_notes": notes,
        "implemented_stage": "source_archive_handoff",
        "next_actions": [
            "Route each archive-handoff output to operator archive submission and result-template completion.",
            "Pass completed archive result templates to the source_archive_result_intake stage.",
            "Use this shared archive handoff bridge for future adapters unless a source has a genuinely unique archive handoff shape.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "archive_handoff_bridge_status": ARCHIVE_HANDOFF_BRIDGE_STATUS if built else "ARCHIVE_HANDOFF_BRIDGE_BLOCKED",
        "source_adapter_release_audit_bridge_id": _safe_text(package.get("source_adapter_release_audit_bridge_id"), ""),
        "archive_handoff_count": len(archive_handoff_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "archive_handoff_outputs": archive_handoff_outputs,
        "source_adapter_archive_handoff_batch": archive_handoff_batch,
        "source_adapter_archive_result_intake_batch_handoff": result_intake_batch_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_archive_handoff",
            "input_source": "source_adapter_release_audit_bridge",
            "per_adapter_path": "release_audit_output_plus_shared_archive_handoff_builder",
            "multi_adapter_batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_archive_handoff_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned)
    result["source_adapter_archive_handoff_bridge_id"] = bridge_id
    result["source_adapter_archive_handoff_batch"] = dict(archive_handoff_batch, source_adapter_archive_handoff_bridge_id=bridge_id)
    result["source_adapter_archive_result_intake_batch_handoff"] = dict(result_intake_batch_handoff, source_adapter_archive_handoff_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_archive_handoff_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_archive_handoff_bridge_package": dict(pkg),
        "source_adapter_archive_handoff_output_batch": deepcopy(pkg.get("archive_handoff_outputs", [])),
        "source_adapter_archive_handoff_batch": deepcopy(pkg.get("source_adapter_archive_handoff_batch", {})),
        "source_adapter_archive_result_intake_batch_handoff": deepcopy(pkg.get("source_adapter_archive_result_intake_batch_handoff", {})),
        "source_adapter_archive_handoff_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_release_audit_bridge import build_source_adapter_release_audit_bridge
    from source_adapter_release_audit_bridge_test import fixture_release_index_bridge

    release_audit_bridge = build_source_adapter_release_audit_bridge(fixture_release_index_bridge())
    result = build_source_adapter_archive_handoff_bridge(release_audit_bridge)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
