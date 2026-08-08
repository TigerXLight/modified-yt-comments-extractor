from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_operator_approved_execution_runtime import (
    KEYS_ACCOUNTS_LABEL,
    PROVIDER_ACTIONS,
    SCHEMA_VERSION as EXECUTION_RUNTIME_SCHEMA_VERSION,
    STATUS as EXECUTION_RUNTIME_STATUS,
    example_operator_approved_execution_runtime_package,
)

SCHEMA_VERSION = "source_adapter_provider_backend_interfaces_v1"
REQUEST_SCHEMA_VERSION = "source_adapter_provider_backend_request_v1"
RECEIPT_BATCH_SCHEMA_VERSION = "source_adapter_provider_backend_execution_receipt_batch_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_provider_backend_interfaces_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_provider_backend_interfaces_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_BUILT"
REQUEST_MATRIX_STATUS = "SOURCE_ADAPTER_PROVIDER_BACKEND_REQUEST_MATRIX_READY"
BACKEND_REGISTRY_STATUS = "SOURCE_ADAPTER_PROVIDER_BACKEND_REGISTRY_READY"
RECEIPT_BATCH_STATUS = "SOURCE_ADAPTER_PROVIDER_BACKEND_EXECUTION_RECEIPTS_READY"
HANDOFF_STATUS = "SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_READY_FOR_GUI_CONTROLLER_AND_PROVIDER_SPECIFIC_BACKENDS"

LOCAL_BACKEND_ID = "source_adapter.provider_backend.local_filesystem_receipt_backend"
PROVIDER_ACTION_HANDLERS = {
    "credential_lookup": "execute_credential_reference_lookup",
    "browser_capture": "execute_browser_capture",
    "archive_submit": "execute_archive_submission",
    "release_upload": "execute_release_upload",
    "file_library_publish": "execute_file_library_publish",
}


@dataclass(frozen=True)
class SourceAdapterProviderBackendInterfaces:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def short_hash(value: Any, length: int = 12) -> str:
    return sha256_text(value)[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _runtime_execution_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(runtime_package, "source_adapter_operator_approved_execution_rows")


def _provider_receipt_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    batch = runtime_package.get("source_adapter_provider_execution_receipt_batch") or {}
    if not isinstance(batch, Mapping):
        return []
    return _rows(batch, "provider_execution_receipt_rows")


def _credential_ledger_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    ledger = runtime_package.get("source_adapter_redacted_credential_reference_ledger") or {}
    if not isinstance(ledger, Mapping):
        return []
    return _rows(ledger, "credential_reference_ledger_rows")


def _validate_runtime(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if runtime_package.get("schema_version") != EXECUTION_RUNTIME_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_execution_runtime_schema", "severity": "error", "message": "operator approved execution runtime schema was not recognised"})
    if runtime_package.get("operator_approved_execution_runtime_status") != EXECUTION_RUNTIME_STATUS:
        issues.append({"issue_id": "execution_runtime_not_built", "severity": "error", "message": "operator approved execution runtime was not built"})
    if runtime_package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    if len(_runtime_execution_rows(runtime_package)) != 5:
        issues.append({"issue_id": "unexpected_execution_row_count", "severity": "error", "message": "expected five named-site execution rows"})
    return issues


def build_provider_backend_registry() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, action in enumerate(PROVIDER_ACTIONS):
        rows.append({
            "schema_version": "source_adapter_provider_backend_registry_row_v1",
            "row_index": index,
            "provider_action": action,
            "provider_backend_registry_row_id": stable_id("source_adapter.provider_backend_registry_row", action),
            "provider_backend_id": LOCAL_BACKEND_ID,
            "callable_handler": PROVIDER_ACTION_HANDLERS[action],
            "backend_mode": "operator_approved_executable_local_backend",
            "provider_specific_backend_pluggable": True,
            "receipt_required": True,
            "receipt_redaction_required": action == "credential_lookup",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return {
        "schema_version": "source_adapter_provider_backend_registry_v1",
        "provider_backend_registry_status": BACKEND_REGISTRY_STATUS,
        "provider_backend_id": LOCAL_BACKEND_ID,
        "provider_backend_row_count": len(rows),
        "provider_actions": list(PROVIDER_ACTIONS),
        "provider_backend_registry_rows": rows,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def _request_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    runtime_receipts = _provider_receipt_rows(runtime_package)
    receipt_by_execution: dict[str, list[dict[str, Any]]] = {}
    for receipt in runtime_receipts:
        execution_id = str(receipt.get("source_operator_approved_execution_row_id") or "")
        if execution_id:
            receipt_by_execution.setdefault(execution_id, []).append(receipt)
    rows: list[dict[str, Any]] = []
    for execution in _runtime_execution_rows(runtime_package):
        execution_id = str(execution.get("operator_approved_execution_row_id"))
        receipts = receipt_by_execution.get(execution_id, [])
        for action in PROVIDER_ACTIONS:
            prior = next((row for row in receipts if row.get("provider_action") == action), {})
            credential_reference_id = execution.get("credential_reference_id")
            payload = {
                "named_site_id": execution.get("named_site_id"),
                "adapter_id": execution.get("adapter_id"),
                "source_kind": execution.get("source_kind"),
                "provider_action": action,
                "source_url_or_local_fixture_ref": prior.get("source_url_or_local_fixture_ref") or execution.get("named_site_id"),
                "receipt_output_dir": execution.get("receipt_output_dir"),
                "credential_reference_id": credential_reference_id if action == "credential_lookup" else None,
            }
            rows.append({
                "schema_version": REQUEST_SCHEMA_VERSION,
                "row_index": len(rows),
                "provider_backend_request_id": stable_id("source_adapter.provider_backend_request", {"execution": execution_id, "action": action}),
                "source_operator_approved_execution_row_id": execution_id,
                "source_provider_execution_receipt_id": prior.get("provider_execution_receipt_id"),
                "provider_backend_id": LOCAL_BACKEND_ID,
                "provider_action": action,
                "callable_handler": PROVIDER_ACTION_HANDLERS[action],
                "request_payload": payload,
                "request_payload_sha256": sha256_text(payload),
                "request_ready": True,
                "operator_approved": True,
                "receipt_required": True,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            })
    return rows


def _execute_request(row: Mapping[str, Any], output_root: Path) -> dict[str, Any]:
    payload = dict(row.get("request_payload") or {})
    named_site_id = str(payload.get("named_site_id") or f"row_{row.get('row_index')}")
    action = str(row.get("provider_action"))
    action_dir = output_root / named_site_id / action
    action_dir.mkdir(parents=True, exist_ok=True)
    receipt_payload = {
        "schema_version": "source_adapter_provider_backend_execution_receipt_payload_v1",
        "provider_backend_id": LOCAL_BACKEND_ID,
        "provider_action": action,
        "named_site_id": named_site_id,
        "adapter_id": payload.get("adapter_id"),
        "source_kind": payload.get("source_kind"),
        "callable_handler": row.get("callable_handler"),
        "operator_approved": True,
        "execution_performed": True,
        "backend_execution_mode": "local_executable_receipt_backend",
        "provider_specific_backend_required_for_remote_work": True,
        "raw_credential_material_stored": False,
        "credential_reference_id": payload.get("credential_reference_id") if action == "credential_lookup" else None,
        "redacted_credential_reference_hash": sha256_text(payload.get("credential_reference_id")) if action == "credential_lookup" else None,
    }
    receipt_path = action_dir / "provider_backend_execution_receipt.json"
    receipt_path.write_text(json.dumps(receipt_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "schema_version": "source_adapter_provider_backend_execution_receipt_row_v1",
        "row_index": int(row.get("row_index", 0)),
        "provider_backend_execution_receipt_id": stable_id("source_adapter.provider_backend_execution_receipt", receipt_payload),
        "source_provider_backend_request_id": row.get("provider_backend_request_id"),
        "source_operator_approved_execution_row_id": row.get("source_operator_approved_execution_row_id"),
        "provider_backend_id": LOCAL_BACKEND_ID,
        "provider_action": action,
        "callable_handler": row.get("callable_handler"),
        "execution_performed": True,
        "receipt_path": str(receipt_path),
        "receipt_payload_sha256": sha256_text(receipt_payload),
        "raw_credential_material_stored": False,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def build_source_adapter_provider_backend_interfaces(
    runtime_package: Mapping[str, Any] | None = None,
    *,
    output_dir: str | Path | None = None,
    operator_id: str = "operator",
    execution_notes: Sequence[str] | None = None,
) -> SourceAdapterProviderBackendInterfaces:
    runtime_package = runtime_package or example_operator_approved_execution_runtime_package()
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="source_adapter_provider_backend_interfaces_"))
    output_root = Path(output_dir)
    issues = _validate_runtime(runtime_package)
    registry = build_provider_backend_registry()
    request_rows = _request_rows(runtime_package)
    receipts = [_execute_request(row, output_root) for row in request_rows]
    credential_ledger_rows = _credential_ledger_rows(runtime_package)
    ready = not issues and len(request_rows) == 25 and len(receipts) == 25 and all(row.get("execution_performed") for row in receipts)
    backend_id = stable_id("source_adapter.provider_backend_interfaces", {"runtime": runtime_package.get("source_adapter_operator_approved_execution_runtime_id"), "requests": request_rows})
    request_matrix = {
        "schema_version": "source_adapter_provider_backend_request_matrix_v1",
        "provider_backend_request_matrix_status": REQUEST_MATRIX_STATUS,
        "provider_backend_request_row_count": len(request_rows),
        "provider_actions": list(PROVIDER_ACTIONS),
        "provider_backend_request_rows": request_rows,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    receipt_batch = {
        "schema_version": RECEIPT_BATCH_SCHEMA_VERSION,
        "provider_backend_execution_receipt_batch_status": RECEIPT_BATCH_STATUS if ready else "SOURCE_ADAPTER_PROVIDER_BACKEND_EXECUTION_RECEIPTS_NEED_REVIEW",
        "provider_backend_execution_receipt_row_count": len(receipts),
        "expected_provider_backend_execution_receipt_row_count": len(request_rows),
        "provider_backend_execution_receipt_rows": receipts,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else "SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_NEED_REVIEW",
        "source_adapter_provider_backend_interfaces_id": backend_id,
        "provider_backend_registry_ready": registry["provider_backend_registry_status"] == BACKEND_REGISTRY_STATUS,
        "provider_backend_request_matrix_ready": True,
        "provider_backend_receipts_ready": ready,
        "provider_specific_backend_pluggable": True,
        "required_next_stage": "gui_controller_execution_bridge_and_provider_specific_backend_replacement",
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else "SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_NEED_REVIEW",
        "operator_id": str(operator_id),
        "provider_backend_row_count": registry["provider_backend_row_count"],
        "provider_backend_request_row_count": len(request_rows),
        "provider_backend_execution_receipt_row_count": len(receipts),
        "credential_reference_ledger_row_count": len(credential_ledger_rows),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Wire provider backend interfaces into GUI/controller execution dispatch.",
            "Replace local executable receipt backend rows with provider-specific browser/archive/release/library backends as configured.",
            "Keep KEYS/ACCOUNTS credential references redacted in backend receipts.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "provider_backend_interfaces_status": STATUS if ready else "SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_NEED_REVIEW",
        "source_adapter_provider_backend_interfaces_id": backend_id,
        "source_adapter_operator_approved_execution_runtime_id": runtime_package.get("source_adapter_operator_approved_execution_runtime_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": issues,
        "provider_backend_logic": {
            "actual_backend_interfaces_built": True,
            "local_executable_provider_backend_receipts_written": ready,
            "provider_specific_backends_pluggable": True,
            "keys_accounts_references_preserved_redacted": True,
        },
        "source_adapter_provider_backend_registry": registry,
        "source_adapter_provider_backend_request_matrix": request_matrix,
        "source_adapter_provider_backend_execution_receipt_batch": receipt_batch,
        "source_adapter_redacted_credential_reference_ledger": {
            "schema_version": "source_adapter_provider_backend_credential_reference_ledger_v1",
            "credential_reference_ledger_row_count": len(credential_ledger_rows),
            "credential_reference_ledger_rows": credential_ledger_rows,
            "raw_credential_material_stored": False,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        },
        "source_adapter_provider_backend_interfaces_handoff": handoff,
        "operator_summary": summary,
        "execution_notes": list(execution_notes or []),
    }
    return SourceAdapterProviderBackendInterfaces(package)


def example_provider_backend_interfaces_package() -> dict[str, Any]:
    return build_source_adapter_provider_backend_interfaces(operator_id="example_operator", execution_notes=["deterministic provider backend interfaces example"]).as_dict()


def main() -> None:
    package = example_provider_backend_interfaces_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["provider_backend_interfaces_status"] == STATUS
    assert package["source_adapter_provider_backend_execution_receipt_batch"]["provider_backend_execution_receipt_row_count"] == 25
    print("Source Adapter Provider Backend Interfaces self-test passed.")


if __name__ == "__main__":
    main()
