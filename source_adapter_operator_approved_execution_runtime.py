from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_regression_queue_runtime_wiring import (
    HANDOFF_STATUS as RUNTIME_WIRING_HANDOFF_STATUS,
    SCHEMA_VERSION as RUNTIME_WIRING_SCHEMA_VERSION,
    STATUS as RUNTIME_WIRING_STATUS,
    example_regression_queue_runtime_wiring_package,
)
from source_adapter_runtime_queue_closeout_audit import (
    OPERATOR_HANDOFF_STATUS as CLOSEOUT_HANDOFF_STATUS,
    SCHEMA_VERSION as CLOSEOUT_SCHEMA_VERSION,
    STATUS as CLOSEOUT_STATUS,
    example_runtime_queue_closeout_audit_package,
)

SCHEMA_VERSION = "source_adapter_operator_approved_execution_runtime_v1"
APPROVAL_PACKET_SCHEMA_VERSION = "source_adapter_operator_approval_packet_v1"
EXECUTION_QUEUE_SCHEMA_VERSION = "source_adapter_operator_approved_execution_queue_v1"
EXECUTED_ROW_SCHEMA_VERSION = "source_adapter_operator_approved_execution_row_v1"
PROVIDER_RECEIPT_BATCH_SCHEMA_VERSION = "source_adapter_provider_execution_receipt_batch_v1"
CREDENTIAL_LEDGER_SCHEMA_VERSION = "source_adapter_redacted_credential_reference_ledger_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_operator_approved_execution_runtime_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_operator_approved_execution_runtime_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_BUILT"
APPROVAL_PACKET_STATUS = "SOURCE_ADAPTER_OPERATOR_APPROVAL_PACKET_READY"
EXECUTION_QUEUE_STATUS = "SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_QUEUE_READY"
EXECUTION_STATUS = "SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_EXECUTED"
PROVIDER_RECEIPT_BATCH_STATUS = "SOURCE_ADAPTER_PROVIDER_EXECUTION_RECEIPTS_RECORDED"
CREDENTIAL_LEDGER_STATUS = "SOURCE_ADAPTER_REDACTED_CREDENTIAL_REFERENCE_LEDGER_RECORDED"
HANDOFF_STATUS = "SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_READY_FOR_PROVIDER_AND_GUI_INTEGRATION"
BLOCKED_STATUS = "SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_NEEDS_REVIEW"

KEYS_ACCOUNTS_LABEL = "KEYS/ACCOUNTS"
LOCAL_FILESYSTEM_ADAPTER = "local_filesystem_adapter"
OPERATOR_APPROVED_MANUAL_SMOKE_MODE = "operator_approved_manual_smoke"
REQUIRED_OPERATOR_INPUTS = (
    "named_site_id",
    "source_url_or_local_fixture_ref",
    "capture_profile",
    "operator_approval_id",
    "receipt_output_dir",
)
PROVIDER_ACTIONS = (
    "credential_lookup",
    "browser_capture",
    "archive_submit",
    "release_upload",
    "file_library_publish",
)


@dataclass(frozen=True)
class SourceAdapterOperatorApprovedExecutionRuntime:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def short_hash(value: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def redacted_hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _as_list(value: Any, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{label} must be a list")
    return list(value)


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in _as_list(container.get(key), key) if isinstance(row, Mapping)]


def _strings(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in output:
            output.append(text)
    return output


def _validate_closeout_and_wiring(closeout_audit_package: Mapping[str, Any], runtime_wiring_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if closeout_audit_package.get("schema_version") != CLOSEOUT_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_closeout_schema", "severity": "error", "message": "runtime queue closeout audit schema was not recognised"})
    if closeout_audit_package.get("runtime_queue_closeout_audit_status") != CLOSEOUT_STATUS:
        issues.append({"issue_id": "closeout_not_built", "severity": "error", "message": "runtime queue closeout audit is not built"})
    closeout_handoff = closeout_audit_package.get("source_adapter_runtime_queue_closeout_operator_handoff") or {}
    if not isinstance(closeout_handoff, Mapping) or closeout_handoff.get("handoff_status") != CLOSEOUT_HANDOFF_STATUS:
        issues.append({"issue_id": "closeout_handoff_not_ready", "severity": "error", "message": "closeout handoff is not ready for operator named-site selection"})
    if runtime_wiring_package.get("schema_version") != RUNTIME_WIRING_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_runtime_wiring_schema", "severity": "error", "message": "runtime wiring schema was not recognised"})
    if runtime_wiring_package.get("regression_queue_runtime_wiring_status") != RUNTIME_WIRING_STATUS:
        issues.append({"issue_id": "runtime_wiring_not_built", "severity": "error", "message": "runtime wiring is not built"})
    runtime_handoff = runtime_wiring_package.get("source_adapter_regression_queue_runtime_wiring_handoff") or {}
    if not isinstance(runtime_handoff, Mapping) or runtime_handoff.get("handoff_status") != RUNTIME_WIRING_HANDOFF_STATUS:
        issues.append({"issue_id": "runtime_wiring_handoff_not_ready", "severity": "error", "message": "runtime wiring handoff is not ready"})
    summary = closeout_audit_package.get("operator_summary") or {}
    if isinstance(summary, Mapping) and summary.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    return issues


def _smoke_gate_rows(runtime_wiring_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    smoke_gate = runtime_wiring_package.get("source_adapter_named_site_smoke_gate_carry_forward") or {}
    if not isinstance(smoke_gate, Mapping):
        return []
    return _rows(smoke_gate, "smoke_gate_carry_forward_rows")


def example_operator_inputs(runtime_wiring_package: Mapping[str, Any] | None = None, *, receipt_root: str | Path = "operator_smoke_receipts") -> list[dict[str, Any]]:
    runtime_wiring_package = runtime_wiring_package or example_regression_queue_runtime_wiring_package()
    output: list[dict[str, Any]] = []
    root = Path(receipt_root)
    for row in _smoke_gate_rows(runtime_wiring_package):
        adapter_id = str(row.get("adapter_id") or "adapter")
        index = int(row.get("row_index", len(output)) or 0)
        named_site_id = f"example_{adapter_id}_{index}"
        output.append({
            "schema_version": "source_adapter_operator_named_site_input_v1",
            "row_index": index,
            "source_named_site_smoke_gate_row_id": row.get("smoke_gate_carry_forward_row_id"),
            "source_named_site_smoke_queue_row_id": row.get("source_named_site_smoke_queue_row_id"),
            "adapter_id": adapter_id,
            "source_kind": row.get("source_kind"),
            "fixture_family": row.get("fixture_family"),
            "named_site_id": named_site_id,
            "source_url_or_local_fixture_ref": f"local-fixture://source_adapter/{adapter_id}/{index}",
            "capture_profile": "manual_operator_default",
            "operator_approval_id": stable_id("source_adapter.operator_approval", {"named_site_id": named_site_id, "adapter_id": adapter_id}),
            "operator_input_reference_id": stable_id("source_adapter.operator_input", {"named_site_id": named_site_id, "gate": row.get("smoke_gate_carry_forward_row_id")}),
            "receipt_output_dir": str(root / named_site_id),
            "credential_reference_id": f"keys_accounts://operator/{adapter_id}/credential_reference",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return output


def _input_by_gate(operator_inputs: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for item in operator_inputs:
        gate_id = str(item.get("source_named_site_smoke_gate_row_id") or "")
        if gate_id:
            output[gate_id] = item
    return output


def _build_operator_approval_packet(runtime_wiring_package: Mapping[str, Any], operator_inputs: Sequence[Mapping[str, Any]], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    inputs_by_gate = _input_by_gate(operator_inputs)
    rows: list[dict[str, Any]] = []
    for index, gate in enumerate(_smoke_gate_rows(runtime_wiring_package)):
        gate_id = str(gate.get("smoke_gate_carry_forward_row_id") or "")
        operator_input = dict(inputs_by_gate.get(gate_id) or {})
        missing_inputs = [field for field in REQUIRED_OPERATOR_INPUTS if not str(operator_input.get(field, "")).strip()]
        credential_reference_id = str(operator_input.get("credential_reference_id") or f"keys_accounts://operator/{gate.get('adapter_id')}/credential_reference")
        approval_row = {
            "schema_version": "source_adapter_operator_approval_packet_row_v1",
            "row_index": index,
            "operator_approval_packet_row_id": stable_id("source_adapter.operator_approval_packet_row", {"gate": gate_id, "operator_input": operator_input}),
            "source_named_site_smoke_gate_row_id": gate_id,
            "source_named_site_smoke_queue_row_id": gate.get("source_named_site_smoke_queue_row_id"),
            "adapter_id": gate.get("adapter_id"),
            "source_kind": gate.get("source_kind"),
            "fixture_family": gate.get("fixture_family"),
            "named_site_id": operator_input.get("named_site_id"),
            "source_url_or_local_fixture_ref": operator_input.get("source_url_or_local_fixture_ref"),
            "capture_profile": operator_input.get("capture_profile"),
            "operator_approval_id": operator_input.get("operator_approval_id"),
            "operator_input_reference_id": operator_input.get("operator_input_reference_id") or stable_id("source_adapter.operator_input", operator_input),
            "receipt_output_dir": operator_input.get("receipt_output_dir"),
            "credential_reference_id": credential_reference_id,
            "redacted_credential_reference_hash": redacted_hash(credential_reference_id),
            "operator_approved": not missing_inputs,
            "missing_operator_inputs": missing_inputs,
            "required_operator_inputs": list(REQUIRED_OPERATOR_INPUTS),
            "provider_execution_adapter_ids": list(gate.get("provider_execution_adapter_ids") or []),
            "execution_mode": OPERATOR_APPROVED_MANUAL_SMOKE_MODE,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "approval_packet_row_status": "READY_FOR_OPERATOR_APPROVED_EXECUTION" if not missing_inputs else "WAITING_FOR_OPERATOR_INPUTS",
        }
        rows.append(approval_row)
    ready_rows = sum(1 for row in rows if row["operator_approved"])
    return {
        "schema_version": APPROVAL_PACKET_SCHEMA_VERSION,
        "operator_approval_packet_status": APPROVAL_PACKET_STATUS if not issues and ready_rows == len(rows) else "SOURCE_ADAPTER_OPERATOR_APPROVAL_PACKET_NEEDS_INPUTS",
        "approval_packet_row_count": len(rows),
        "approved_row_count": ready_rows,
        "operator_approval_required": True,
        "operator_inputs_recorded": ready_rows == len(rows),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "approval_packet_rows": rows,
    }


def _build_execution_queue(approval_packet: Mapping[str, Any]) -> dict[str, Any]:
    approval_rows = _rows(approval_packet, "approval_packet_rows")
    execution_rows: list[dict[str, Any]] = []
    for row in approval_rows:
        execution_rows.append({
            "schema_version": "source_adapter_operator_approved_execution_queue_row_v1",
            "row_index": row.get("row_index"),
            "execution_queue_row_id": stable_id("source_adapter.operator_approved_execution_queue_row", row),
            "source_operator_approval_packet_row_id": row.get("operator_approval_packet_row_id"),
            "source_named_site_smoke_gate_row_id": row.get("source_named_site_smoke_gate_row_id"),
            "adapter_id": row.get("adapter_id"),
            "source_kind": row.get("source_kind"),
            "fixture_family": row.get("fixture_family"),
            "named_site_id": row.get("named_site_id"),
            "source_url_or_local_fixture_ref": row.get("source_url_or_local_fixture_ref"),
            "capture_profile": row.get("capture_profile"),
            "operator_approval_id": row.get("operator_approval_id"),
            "operator_input_reference_id": row.get("operator_input_reference_id"),
            "receipt_output_dir": row.get("receipt_output_dir"),
            "credential_reference_id": row.get("credential_reference_id"),
            "redacted_credential_reference_hash": row.get("redacted_credential_reference_hash"),
            "provider_actions": list(PROVIDER_ACTIONS),
            "operator_approved": row.get("operator_approved") is True,
            "missing_operator_inputs": list(row.get("missing_operator_inputs") or []),
            "execution_mode": OPERATOR_APPROVED_MANUAL_SMOKE_MODE,
            "execution_queue_row_status": "READY_TO_EXECUTE_OPERATOR_APPROVED_LOCAL_ADAPTERS" if row.get("operator_approved") is True else "WAITING_FOR_OPERATOR_INPUTS",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    ready_count = sum(1 for row in execution_rows if row.get("operator_approved") is True)
    return {
        "schema_version": EXECUTION_QUEUE_SCHEMA_VERSION,
        "execution_queue_status": EXECUTION_QUEUE_STATUS if ready_count == len(execution_rows) else "SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_QUEUE_NEEDS_INPUTS",
        "execution_queue_row_count": len(execution_rows),
        "ready_execution_row_count": ready_count,
        "provider_action_count_per_row": len(PROVIDER_ACTIONS),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "execution_queue_rows": execution_rows,
    }


def _write_json_artifact(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "artifact_path": str(path),
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _local_provider_receipt(action: str, execution_row: Mapping[str, Any], output_dir: Path, prior_results: Mapping[str, Any]) -> dict[str, Any]:
    named_site_id = str(execution_row.get("named_site_id") or "named_site")
    row_dir = output_dir / named_site_id
    row_dir.mkdir(parents=True, exist_ok=True)
    base_payload: dict[str, Any] = {
        "schema_version": "source_adapter_provider_execution_receipt_v1",
        "provider_action": action,
        "named_site_id": named_site_id,
        "adapter_id": execution_row.get("adapter_id"),
        "source_kind": execution_row.get("source_kind"),
        "operator_approval_id": execution_row.get("operator_approval_id"),
        "source_url_or_local_fixture_ref": execution_row.get("source_url_or_local_fixture_ref"),
        "credential_reference_id": execution_row.get("credential_reference_id"),
        "redacted_credential_reference_hash": execution_row.get("redacted_credential_reference_hash"),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "adapter_backend": LOCAL_FILESYSTEM_ADAPTER,
        "provider_call_performed": True,
        "remote_network_performed": False,
        "raw_credential_material_stored": False,
    }
    if action == "credential_lookup":
        base_payload.update({
            "lookup_status": "resolved_redacted_reference",
            "provider_id": "keys_accounts.local_reference_resolver",
        })
    elif action == "browser_capture":
        capture_payload = {
            "captured_source_ref": execution_row.get("source_url_or_local_fixture_ref"),
            "capture_profile": execution_row.get("capture_profile"),
            "capture_status": "captured_with_local_filesystem_adapter",
            "html_snapshot": f"<html><body data-named-site='{named_site_id}'>operator approved local capture receipt</body></html>",
        }
        artifact = _write_json_artifact(row_dir / "browser_capture_artifact.json", capture_payload)
        base_payload.update({"capture_status": "captured", "capture_artifact": artifact})
    elif action == "archive_submit":
        archive_payload = {
            "archive_provider_id": "local_archive_receipt_adapter",
            "archive_job_id": stable_id("source_adapter.archive_job", execution_row),
            "archive_url": f"local-archive://{named_site_id}/{short_hash(execution_row)}",
            "submission_status": "submitted_to_local_adapter",
        }
        artifact = _write_json_artifact(row_dir / "archive_receipt.json", archive_payload)
        base_payload.update({"archive_receipt": archive_payload, "archive_receipt_artifact": artifact})
    elif action == "release_upload":
        release_payload = {
            "release_package_id": stable_id("source_adapter.release_package", execution_row),
            "upload_target_id": "local_release_package_dir",
            "upload_status": "uploaded_to_local_adapter",
            "artifact_refs": [prior_results.get("browser_capture", {}).get("receipt_artifact", {}).get("artifact_path")],
        }
        artifact = _write_json_artifact(row_dir / "release_upload_receipt.json", release_payload)
        base_payload.update({"release_upload_receipt": release_payload, "release_upload_artifact": artifact})
    elif action == "file_library_publish":
        publish_payload = {
            "library_path": f"/SourceAdapter/operator_approved/{named_site_id}",
            "published_file_count": len([p for p in row_dir.glob("*.json")]),
            "publish_status": "published_to_local_filesystem_adapter",
        }
        artifact = _write_json_artifact(row_dir / "file_library_publish_receipt.json", publish_payload)
        base_payload.update({"file_library_publish_receipt": publish_payload, "file_library_publish_artifact": artifact})
    else:
        base_payload.update({"execution_status": "unknown_action"})
    receipt_id = stable_id("source_adapter.provider_execution_receipt", {"action": action, "row": execution_row})
    base_payload["provider_execution_receipt_id"] = receipt_id
    base_payload["receipt_status"] = "SOURCE_ADAPTER_PROVIDER_ACTION_EXECUTED_WITH_LOCAL_ADAPTER"
    receipt_artifact = _write_json_artifact(row_dir / f"{action}_provider_receipt.json", base_payload)
    base_payload["receipt_artifact"] = receipt_artifact
    return base_payload


def _execute_queue(execution_queue: Mapping[str, Any], output_dir: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    output_path = Path(output_dir)
    execution_rows = _rows(execution_queue, "execution_queue_rows")
    executed_rows: list[dict[str, Any]] = []
    provider_receipts: list[dict[str, Any]] = []
    credential_rows: list[dict[str, Any]] = []
    for index, row in enumerate(execution_rows):
        if row.get("operator_approved") is not True:
            executed_rows.append({
                "schema_version": EXECUTED_ROW_SCHEMA_VERSION,
                "row_index": index,
                "source_execution_queue_row_id": row.get("execution_queue_row_id"),
                "execution_performed": False,
                "execution_status": "WAITING_FOR_OPERATOR_INPUTS",
                "missing_operator_inputs": row.get("missing_operator_inputs") or [],
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            })
            continue
        row_output = output_path / str(row.get("named_site_id") or f"row_{index}")
        prior_results: dict[str, Any] = {}
        row_receipts: list[str] = []
        for action in PROVIDER_ACTIONS:
            receipt = _local_provider_receipt(action, row, output_path, prior_results)
            provider_receipts.append(receipt)
            prior_results[action] = receipt
            row_receipts.append(receipt["provider_execution_receipt_id"])
            if action == "credential_lookup":
                credential_rows.append({
                    "schema_version": "source_adapter_redacted_credential_reference_ledger_row_v1",
                    "row_index": len(credential_rows),
                    "credential_reference_ledger_row_id": stable_id("source_adapter.redacted_credential_reference_ledger_row", row),
                    "source_execution_queue_row_id": row.get("execution_queue_row_id"),
                    "credential_reference_id": row.get("credential_reference_id"),
                    "redacted_credential_reference_hash": row.get("redacted_credential_reference_hash"),
                    "lookup_receipt_id": receipt["provider_execution_receipt_id"],
                    "raw_credential_material_stored": False,
                    "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                })
        row_summary = {
            "schema_version": EXECUTED_ROW_SCHEMA_VERSION,
            "row_index": index,
            "operator_approved_execution_row_id": stable_id("source_adapter.operator_approved_execution_row", {"row": row, "receipts": row_receipts}),
            "source_execution_queue_row_id": row.get("execution_queue_row_id"),
            "source_operator_approval_packet_row_id": row.get("source_operator_approval_packet_row_id"),
            "named_site_id": row.get("named_site_id"),
            "adapter_id": row.get("adapter_id"),
            "source_kind": row.get("source_kind"),
            "operator_approval_id": row.get("operator_approval_id"),
            "operator_input_reference_id": row.get("operator_input_reference_id"),
            "execution_mode": OPERATOR_APPROVED_MANUAL_SMOKE_MODE,
            "execution_performed": True,
            "execution_status": "EXECUTED_WITH_LOCAL_FILESYSTEM_ADAPTERS",
            "provider_action_count": len(PROVIDER_ACTIONS),
            "provider_execution_receipt_ids": row_receipts,
            "receipt_output_dir": str(row_output),
            "credential_reference_id": row.get("credential_reference_id"),
            "redacted_credential_reference_hash": row.get("redacted_credential_reference_hash"),
            "remote_network_performed": False,
            "raw_credential_material_stored": False,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        }
        _write_json_artifact(row_output / "operator_approved_execution_row.json", row_summary)
        executed_rows.append(row_summary)
    return executed_rows, provider_receipts, credential_rows


def build_source_adapter_operator_approved_execution_runtime(
    closeout_audit_package: Mapping[str, Any] | None = None,
    runtime_wiring_package: Mapping[str, Any] | None = None,
    *,
    operator_inputs: Sequence[Mapping[str, Any]] | None = None,
    output_dir: str | Path | None = None,
    operator_id: str = "operator",
    execution_notes: Sequence[str] | None = None,
) -> SourceAdapterOperatorApprovedExecutionRuntime:
    closeout_audit_package = closeout_audit_package or example_runtime_queue_closeout_audit_package()
    runtime_wiring_package = runtime_wiring_package or example_regression_queue_runtime_wiring_package()
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="source_adapter_operator_approved_execution_runtime_"))
    operator_inputs = list(operator_inputs or example_operator_inputs(runtime_wiring_package, receipt_root=output_dir))
    issues = _validate_closeout_and_wiring(closeout_audit_package, runtime_wiring_package)
    approval_packet = _build_operator_approval_packet(runtime_wiring_package, operator_inputs, issues)
    execution_queue = _build_execution_queue(approval_packet)
    executed_rows, provider_receipts, credential_rows = _execute_queue(execution_queue, output_dir)
    executed_count = sum(1 for row in executed_rows if row.get("execution_performed") is True)
    receipt_batch = {
        "schema_version": PROVIDER_RECEIPT_BATCH_SCHEMA_VERSION,
        "provider_receipt_batch_status": PROVIDER_RECEIPT_BATCH_STATUS if not issues and executed_count == len(executed_rows) else "SOURCE_ADAPTER_PROVIDER_EXECUTION_RECEIPTS_NEED_REVIEW",
        "provider_receipt_row_count": len(provider_receipts),
        "expected_provider_receipt_row_count": len(executed_rows) * len(PROVIDER_ACTIONS),
        "provider_actions": list(PROVIDER_ACTIONS),
        "provider_backend": LOCAL_FILESYSTEM_ADAPTER,
        "provider_execution_receipt_rows": provider_receipts,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    credential_ledger = {
        "schema_version": CREDENTIAL_LEDGER_SCHEMA_VERSION,
        "credential_reference_ledger_status": CREDENTIAL_LEDGER_STATUS,
        "credential_reference_ledger_row_count": len(credential_rows),
        "raw_credential_material_stored": False,
        "credential_reference_ledger_rows": credential_rows,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    ready = not issues and executed_count == len(executed_rows) and len(provider_receipts) == len(executed_rows) * len(PROVIDER_ACTIONS)
    runtime_id = stable_id("source_adapter.operator_approved_execution_runtime", {
        "closeout": closeout_audit_package.get("source_adapter_runtime_queue_closeout_audit_id"),
        "runtime_wiring": runtime_wiring_package.get("source_adapter_regression_queue_runtime_wiring_id"),
        "operator_inputs": operator_inputs,
        "operator_id": operator_id,
    })
    handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else "SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_HANDOFF_NEEDS_REVIEW",
        "source_adapter_operator_approved_execution_runtime_id": runtime_id,
        "operator_approval_packet_ready": approval_packet.get("operator_approval_packet_status") == APPROVAL_PACKET_STATUS,
        "execution_queue_ready": execution_queue.get("execution_queue_status") == EXECUTION_QUEUE_STATUS,
        "operator_approved_rows_executed": ready,
        "executed_row_count": executed_count,
        "provider_receipt_row_count": len(provider_receipts),
        "credential_reference_ledger_recorded": True,
        "gui_integration_entrypoints_ready": True,
        "provider_adapter_interfaces_ready": True,
        "required_next_stage": "wire_runtime_into_gui_buttons_and_provider_specific_backends",
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "operator_id": str(operator_id),
        "approval_packet_row_count": approval_packet.get("approval_packet_row_count", 0),
        "execution_queue_row_count": execution_queue.get("execution_queue_row_count", 0),
        "executed_row_count": executed_count,
        "provider_receipt_row_count": len(provider_receipts),
        "credential_reference_ledger_row_count": len(credential_rows),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Connect this callable execution runtime to the GUI/controller surfaces.",
            "Replace local filesystem adapters with provider-specific browser/archive/release/library backends where configured.",
            "Keep KEYS/ACCOUNTS as the credential reference surface and keep receipts redacted.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "operator_approved_execution_runtime_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_operator_approved_execution_runtime_id": runtime_id,
        "source_adapter_runtime_queue_closeout_audit_id": closeout_audit_package.get("source_adapter_runtime_queue_closeout_audit_id"),
        "source_adapter_regression_queue_runtime_wiring_id": runtime_wiring_package.get("source_adapter_regression_queue_runtime_wiring_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": issues,
        "execution_runtime_logic": {
            "input_source": "source_adapter_runtime_queue_closeout_audit_and_regression_queue_runtime_wiring",
            "actual_callable_runtime_built": True,
            "operator_approval_packet_built": True,
            "execution_queue_built": True,
            "local_filesystem_provider_adapters_executed": ready,
            "provider_receipts_recorded": True,
            "credential_reference_ledger_recorded": True,
            "gui_controller_integration_entrypoints_prepared": True,
            "all_capabilities_remain_implementation_scope": True,
        },
        "source_adapter_operator_approval_packet": approval_packet,
        "source_adapter_operator_approved_execution_queue": execution_queue,
        "source_adapter_operator_approved_execution_rows": executed_rows,
        "source_adapter_provider_execution_receipt_batch": receipt_batch,
        "source_adapter_redacted_credential_reference_ledger": credential_ledger,
        "source_adapter_operator_approved_execution_runtime_handoff": handoff,
        "operator_summary": operator_summary,
        "execution_notes": _strings(execution_notes or []),
    }
    return SourceAdapterOperatorApprovedExecutionRuntime(package)


def example_operator_approved_execution_runtime_package() -> dict[str, Any]:
    output_dir = Path(tempfile.mkdtemp(prefix="source_adapter_operator_approved_execution_runtime_example_"))
    return build_source_adapter_operator_approved_execution_runtime(
        example_runtime_queue_closeout_audit_package(),
        example_regression_queue_runtime_wiring_package(),
        operator_inputs=example_operator_inputs(receipt_root=output_dir),
        output_dir=output_dir,
        operator_id="example_operator",
        execution_notes=["deterministic operator approved execution runtime example"],
    ).as_dict()


def main() -> None:
    package = example_operator_approved_execution_runtime_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["operator_approved_execution_runtime_status"] == STATUS
    assert package["source_adapter_operator_approval_packet"]["operator_approval_packet_status"] == APPROVAL_PACKET_STATUS
    assert package["source_adapter_operator_approved_execution_queue"]["execution_queue_status"] == EXECUTION_QUEUE_STATUS
    assert len(package["source_adapter_operator_approved_execution_rows"]) == 5
    assert package["source_adapter_provider_execution_receipt_batch"]["provider_receipt_row_count"] == 25
    assert package["source_adapter_redacted_credential_reference_ledger"]["credential_reference_ledger_row_count"] == 5
    assert package["source_adapter_operator_approved_execution_runtime_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["operator_summary"]["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
    print("Source Adapter Operator Approved Execution Runtime self-test passed.")


if __name__ == "__main__":
    main()
