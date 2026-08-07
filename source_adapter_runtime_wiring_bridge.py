from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_runtime_wiring_bridge_v1"
ACTION_BATCH_SCHEMA_VERSION = "source_adapter_runtime_action_batch_v1"
RECEIPT_BATCH_SCHEMA_VERSION = "source_adapter_runtime_action_receipt_batch_v1"
EXECUTION_HANDOFF_SCHEMA_VERSION = "source_adapter_runtime_execution_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_runtime_wiring_bridge_operator_summary_v1"
RUNTIME_WIRING_STATUS = "SOURCE_ADAPTER_RUNTIME_ACTIONS_WIRED"
RUNTIME_EXECUTION_READY_STATUS = "READY_FOR_OPERATOR_APPROVED_RUNTIME_EXECUTION"
RUNTIME_RECEIPTS_BUILT_STATUS = "SOURCE_ADAPTER_RUNTIME_RECEIPTS_BUILT"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_DEFAULT_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "capability_id": "operator_url_fetch",
        "label": "Operator URL fetch/load",
        "entrypoint": "source_adapter_runtime.operator_url_fetch",
        "target_binding": "source_url",
        "receipt_role": "url_fetch_receipt",
        "approval_required": True,
        "implementation_surface": "url_fetch_or_embedded_browser_load",
    },
    {
        "capability_id": "browser_launch",
        "label": "Lightweight browser launch",
        "entrypoint": "lightweight_in_app_browser_capture.launch_for_adapter",
        "target_binding": "source_url",
        "receipt_role": "browser_launch_receipt",
        "approval_required": True,
        "implementation_surface": "browser_process_or_embedded_shell_launch",
    },
    {
        "capability_id": "folder_scan",
        "label": "Artifact folder scan",
        "entrypoint": "source_adapter_runtime.scan_artifact_folder",
        "target_binding": "artifact_folder",
        "receipt_role": "folder_scan_receipt",
        "approval_required": True,
        "implementation_surface": "operator_selected_folder_scan",
    },
    {
        "capability_id": "credential_lookup",
        "label": "Credential lookup",
        "entrypoint": "source_adapter_runtime.resolve_credential_reference",
        "target_binding": "credential_ref",
        "receipt_role": "credential_lookup_receipt",
        "approval_required": True,
        "implementation_surface": "keys_accounts_reference_resolution",
    },
    {
        "capability_id": "archive_submit",
        "label": "Archive provider submission",
        "entrypoint": "source_adapter_runtime.submit_archive_request",
        "target_binding": "archive_provider_task",
        "receipt_role": "archive_submission_receipt",
        "approval_required": True,
        "implementation_surface": "archive_provider_submit",
    },
    {
        "capability_id": "release_upload",
        "label": "Release artifact upload",
        "entrypoint": "source_adapter_runtime.upload_release_artifact",
        "target_binding": "release_artifact",
        "receipt_role": "release_upload_receipt",
        "approval_required": True,
        "implementation_surface": "release_export_or_library_upload",
    },
    {
        "capability_id": "app_registry_mutation",
        "label": "App/registry mutation",
        "entrypoint": "source_adapter_runtime.apply_registry_mutation",
        "target_binding": "adapter_registry_record",
        "receipt_role": "registry_mutation_receipt",
        "approval_required": True,
        "implementation_surface": "application_state_or_adapter_registry_update",
    },
    {
        "capability_id": "file_library_publication",
        "label": "File-library publication",
        "entrypoint": "source_adapter_runtime.publish_file_library_artifact",
        "target_binding": "library_destination",
        "receipt_role": "file_library_publication_receipt",
        "approval_required": True,
        "implementation_surface": "persistent_file_library_write",
    },
)

Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


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
        raise ValueError(f"{label} must contain only letters, numbers, dot, colon, underscore, or dash")
    return text


def _normalise_notes(notes: Iterable[str] | None) -> list[str]:
    return [str(note).strip() for note in (notes or []) if str(note).strip()]


def runtime_capability_catalog() -> list[dict[str, Any]]:
    """Return the shared runtime action capability catalog."""

    return [dict(item) for item in _DEFAULT_CAPABILITIES]


def _selected_capabilities(enabled_capabilities: Iterable[str] | None) -> list[dict[str, Any]]:
    catalog = runtime_capability_catalog()
    if enabled_capabilities is None:
        return catalog
    wanted = {_safe_id(item, label="enabled capability") for item in enabled_capabilities}
    known = {item["capability_id"] for item in catalog}
    unknown = sorted(wanted - known)
    if unknown:
        raise ValueError(f"unknown runtime capabilities: {unknown}")
    return [item for item in catalog if item["capability_id"] in wanted]


def _closeout_rows(pipeline_closeout_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    batch = _as_mapping(
        pipeline_closeout_bridge_package.get("source_adapter_pipeline_closeout_batch"),
        "source_adapter_pipeline_closeout_batch",
    )
    return _as_mapping_list(batch.get("pipeline_closeout_rows"), "pipeline_closeout_rows")


def _target_for_capability(row: Mapping[str, Any], capability: Mapping[str, Any], runtime_inputs: Mapping[str, Any]) -> dict[str, Any]:
    adapter_id = _safe_text(row.get("adapter_id"), "")
    closeout_id = _safe_text(row.get("source_pipeline_closeout_id"), "")
    row_inputs = runtime_inputs.get(closeout_id) if closeout_id in runtime_inputs else runtime_inputs.get(adapter_id, {})
    if not isinstance(row_inputs, Mapping):
        row_inputs = {}
    binding = _safe_text(capability.get("target_binding"), "")
    supplied = row_inputs.get(binding)
    if supplied is None and binding == "source_url":
        supplied = row.get("source_url")
    if supplied is None and binding == "adapter_registry_record":
        supplied = {"adapter_id": adapter_id, "source_pipeline_closeout_id": closeout_id}
    if supplied is None:
        supplied = ""
    return {
        "binding": binding,
        "value": supplied,
        "source": "operator_runtime_inputs" if binding in row_inputs else "pipeline_closeout_row",
    }


def _action_from_row(
    row: Mapping[str, Any],
    capability: Mapping[str, Any],
    index: int,
    *,
    approval_id: str,
    runtime_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    closeout_id = _safe_id(row.get("source_pipeline_closeout_id"), label="source_pipeline_closeout_id")
    capability_id = _safe_id(capability.get("capability_id"), label="capability_id")
    target = _target_for_capability(row, capability, runtime_inputs)
    unsigned = {
        "schema_version": "source_adapter_runtime_action_v1",
        "adapter_id": _safe_text(row.get("adapter_id"), ""),
        "source_url": _safe_text(row.get("source_url"), ""),
        "source_pipeline_closeout_id": closeout_id,
        "capability_id": capability_id,
        "label": _safe_text(capability.get("label"), capability_id),
        "entrypoint": _safe_text(capability.get("entrypoint"), ""),
        "target": target,
        "receipt_role": _safe_text(capability.get("receipt_role"), "runtime_action_receipt"),
        "approval_required": bool(capability.get("approval_required", True)),
        "approval_id": approval_id,
        "approval_status": "APPROVED" if approval_id else "PENDING_OPERATOR_APPROVAL",
        "implementation_surface": _safe_text(capability.get("implementation_surface"), ""),
        "action_index": index,
    }
    return dict(unsigned, runtime_action_id=f"source_adapter.runtime_action.{_stable_hash(unsigned)}")


def _dry_run_receipt(action: Mapping[str, Any], execution_mode: str) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_runtime_action_receipt_v1",
        "runtime_action_id": _safe_text(action.get("runtime_action_id"), ""),
        "capability_id": _safe_text(action.get("capability_id"), ""),
        "adapter_id": _safe_text(action.get("adapter_id"), ""),
        "source_pipeline_closeout_id": _safe_text(action.get("source_pipeline_closeout_id"), ""),
        "execution_mode": execution_mode,
        "execution_status": "EXECUTED_DRY_RUN" if execution_mode == "dry_run" else "EXECUTION_REQUEST_WIRED",
        "receipt_role": _safe_text(action.get("receipt_role"), "runtime_action_receipt"),
        "target": deepcopy(action.get("target", {})),
        "executor": "deterministic_runtime_wiring_bridge",
        "external_effect_recorded": False,
    }
    return dict(unsigned, runtime_action_receipt_id=f"source_adapter.runtime_receipt.{_stable_hash(unsigned)}")


def _executor_receipt(action: Mapping[str, Any], executor: Executor, execution_mode: str) -> dict[str, Any]:
    produced = _as_mapping(executor(action), "executor receipt")
    unsigned = {
        "schema_version": "source_adapter_runtime_action_receipt_v1",
        "runtime_action_id": _safe_text(action.get("runtime_action_id"), ""),
        "capability_id": _safe_text(action.get("capability_id"), ""),
        "adapter_id": _safe_text(action.get("adapter_id"), ""),
        "source_pipeline_closeout_id": _safe_text(action.get("source_pipeline_closeout_id"), ""),
        "execution_mode": execution_mode,
        "execution_status": _safe_text(produced.get("execution_status"), "EXECUTED_BY_INJECTED_EXECUTOR"),
        "receipt_role": _safe_text(produced.get("receipt_role"), action.get("receipt_role") or "runtime_action_receipt"),
        "target": deepcopy(action.get("target", {})),
        "executor": _safe_text(produced.get("executor"), "injected_executor"),
        "external_effect_recorded": bool(produced.get("external_effect_recorded", True)),
        "executor_receipt": deepcopy(dict(produced)),
    }
    return dict(unsigned, runtime_action_receipt_id=f"source_adapter.runtime_receipt.{_stable_hash(unsigned)}")


def build_source_adapter_runtime_wiring_bridge(
    pipeline_closeout_bridge_package: Mapping[str, Any],
    *,
    enabled_capabilities: Iterable[str] | None = None,
    execution_mode: str = "dry_run",
    operator_approval_id: str = "",
    runtime_inputs: Mapping[str, Any] | None = None,
    operator_notes: Iterable[str] | None = None,
    executor: Executor | None = None,
) -> dict[str, Any]:
    """Build runtime action wiring from a completed Adapter Pipeline Closeout Bridge package."""

    package = _as_mapping(pipeline_closeout_bridge_package, "pipeline_closeout_bridge_package")
    if package.get("pipeline_closeout_bridge_status") != "SHARED_PIPELINE_CLOSEOUTS_BUILT":
        raise ValueError("pipeline closeout bridge package must be SHARED_PIPELINE_CLOSEOUTS_BUILT")
    handoff = _as_mapping(
        package.get("source_adapter_shared_pipeline_roadmap_closeout_handoff"),
        "source_adapter_shared_pipeline_roadmap_closeout_handoff",
    )
    if handoff.get("handoff_status") != "SOURCE_ADAPTER_SHARED_PIPELINE_COMPLETE":
        raise ValueError("pipeline closeout handoff must be SOURCE_ADAPTER_SHARED_PIPELINE_COMPLETE")
    if handoff.get("required_next_stage") != "source_adapter_runtime_wiring_or_fixture_expansion":
        raise ValueError("pipeline closeout handoff must request runtime wiring or fixture expansion")

    if execution_mode not in {"plan_only", "dry_run", "operator_approved_executor"}:
        raise ValueError("execution_mode must be plan_only, dry_run, or operator_approved_executor")
    if execution_mode == "operator_approved_executor" and not operator_approval_id:
        raise ValueError("operator_approved_executor mode requires operator_approval_id")
    if execution_mode == "operator_approved_executor" and executor is None:
        raise ValueError("operator_approved_executor mode requires an executor callable")

    notes = _normalise_notes(operator_notes)
    runtime_inputs = _as_mapping(runtime_inputs or {}, "runtime_inputs")
    capabilities = _selected_capabilities(enabled_capabilities)
    rows = _closeout_rows(package)
    if not rows:
        raise ValueError("at least one pipeline closeout row is required")

    action_rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    issue_rows: list[str] = []
    action_index = 0
    for row in rows:
        if row.get("final_status") != "SOURCE_PIPELINE_COMPLETE":
            issue_rows.append(f"{row.get('source_pipeline_closeout_id')}: final status is not SOURCE_PIPELINE_COMPLETE")
            continue
        for capability in capabilities:
            try:
                action = _action_from_row(
                    row,
                    capability,
                    action_index,
                    approval_id=operator_approval_id,
                    runtime_inputs=runtime_inputs,
                )
                action_rows.append(action)
                if execution_mode == "dry_run":
                    receipts.append(_dry_run_receipt(action, execution_mode))
                elif execution_mode == "operator_approved_executor":
                    receipts.append(_executor_receipt(action, executor, execution_mode))  # type: ignore[arg-type]
                action_index += 1
            except Exception as exc:
                issue_rows.append(f"{row.get('source_pipeline_closeout_id')}: {capability.get('capability_id')}: {exc}")

    action_batch = {
        "schema_version": ACTION_BATCH_SCHEMA_VERSION,
        "execution_mode": execution_mode,
        "operator_approval_id": operator_approval_id,
        "pipeline_closeout_count": len(rows),
        "capability_count": len(capabilities),
        "runtime_action_count": len(action_rows),
        "runtime_actions": action_rows,
    }
    receipt_batch = {
        "schema_version": RECEIPT_BATCH_SCHEMA_VERSION,
        "execution_mode": execution_mode,
        "runtime_action_count": len(action_rows),
        "runtime_receipt_count": len(receipts),
        "runtime_action_receipts": receipts,
    }
    execution_handoff = {
        "schema_version": EXECUTION_HANDOFF_SCHEMA_VERSION,
        "handoff_status": RUNTIME_RECEIPTS_BUILT_STATUS if receipts else RUNTIME_EXECUTION_READY_STATUS,
        "ready_for_operator_runtime_execution": execution_mode == "plan_only",
        "runtime_receipts_built": bool(receipts),
        "operator_approval_id": operator_approval_id,
        "runtime_action_ids": [action["runtime_action_id"] for action in action_rows],
        "runtime_action_receipt_ids": [receipt["runtime_action_receipt_id"] for receipt in receipts],
        "capability_ids": [capability["capability_id"] for capability in capabilities],
        "required_next_stage": "source_adapter_runtime_receipt_review",
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": RUNTIME_WIRING_STATUS if not issue_rows else "SOURCE_ADAPTER_RUNTIME_WIRING_HAS_ISSUES",
        "execution_mode": execution_mode,
        "operator_approval_id": operator_approval_id,
        "runtime_action_count": len(action_rows),
        "runtime_receipt_count": len(receipts),
        "capability_count": len(capabilities),
        "issue_count": len(issue_rows),
        "operator_notes": notes,
        "next_actions": [
            "Bind UI/CLI controls to these shared runtime action IDs and capability IDs.",
            "Use named operator approval records before provider, browser, credential, folder, release, or registry execution.",
            "Persist returned runtime receipts into the shared evidence/review pipeline for fixture and audit coverage.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "runtime_wiring_status": RUNTIME_WIRING_STATUS if not issue_rows else "SOURCE_ADAPTER_RUNTIME_WIRING_HAS_ISSUES",
        "source_adapter_pipeline_closeout_bridge_id": _safe_text(package.get("source_adapter_pipeline_closeout_bridge_id"), ""),
        "pipeline_closeout_count": len(rows),
        "runtime_action_count": len(action_rows),
        "runtime_receipt_count": len(receipts),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "runtime_capability_catalog": capabilities,
        "source_adapter_runtime_action_batch": action_batch,
        "source_adapter_runtime_action_receipt_batch": receipt_batch,
        "source_adapter_runtime_execution_handoff": execution_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_adapter_runtime_wiring",
            "input_stage": "source_adapter_pipeline_closeout_bridge",
            "capability_surface_complete": True,
            "operator_approved_executor_supported": True,
            "batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_runtime_wiring_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned, source_adapter_runtime_wiring_bridge_id=bridge_id)
    result["source_adapter_runtime_action_batch"] = dict(action_batch, source_adapter_runtime_wiring_bridge_id=bridge_id)
    result["source_adapter_runtime_action_receipt_batch"] = dict(receipt_batch, source_adapter_runtime_wiring_bridge_id=bridge_id)
    result["source_adapter_runtime_execution_handoff"] = dict(execution_handoff, source_adapter_runtime_wiring_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_runtime_wiring_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_runtime_wiring_bridge_package": dict(pkg),
        "source_adapter_runtime_action_batch": deepcopy(pkg.get("source_adapter_runtime_action_batch", {})),
        "source_adapter_runtime_action_receipt_batch": deepcopy(pkg.get("source_adapter_runtime_action_receipt_batch", {})),
        "source_adapter_runtime_execution_handoff": deepcopy(pkg.get("source_adapter_runtime_execution_handoff", {})),
        "source_adapter_runtime_wiring_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_pipeline_closeout_bridge import build_source_adapter_pipeline_closeout_bridge
    from source_adapter_pipeline_closeout_bridge_test import fixture_archive_review_bridge

    closeout = build_source_adapter_pipeline_closeout_bridge(fixture_archive_review_bridge())
    result = build_source_adapter_runtime_wiring_bridge(closeout, operator_approval_id="approval.fixture", operator_notes=["demo runtime wiring"])
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
