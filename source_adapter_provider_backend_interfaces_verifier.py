from __future__ import annotations

from typing import Any, Mapping, Sequence

from source_adapter_provider_backend_interfaces import HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, PROVIDER_ACTIONS, RECEIPT_BATCH_STATUS, SCHEMA_VERSION, STATUS

VERIFY_SCHEMA_VERSION = "source_adapter_provider_backend_interfaces_verifier_v1"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def verify_source_adapter_provider_backend_interfaces(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "unexpected provider backend interfaces schema"})
    if package.get("provider_backend_interfaces_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "provider backend interfaces status is not built"})
    registry = package.get("source_adapter_provider_backend_registry") or {}
    request_matrix = package.get("source_adapter_provider_backend_request_matrix") or {}
    receipt_batch = package.get("source_adapter_provider_backend_execution_receipt_batch") or {}
    handoff = package.get("source_adapter_provider_backend_interfaces_handoff") or {}
    request_rows = _rows(request_matrix, "provider_backend_request_rows")
    receipt_rows = _rows(receipt_batch, "provider_backend_execution_receipt_rows")
    if registry.get("provider_backend_row_count") != len(PROVIDER_ACTIONS):
        issues.append({"issue_id": "provider_backend_row_count_mismatch", "severity": "error", "message": "provider backend registry must contain all provider actions"})
    if len(request_rows) != 25:
        issues.append({"issue_id": "request_row_count_mismatch", "severity": "error", "message": "expected twenty-five provider backend request rows"})
    if len(receipt_rows) != 25 or receipt_batch.get("provider_backend_execution_receipt_batch_status") != RECEIPT_BATCH_STATUS:
        issues.append({"issue_id": "receipt_row_count_mismatch", "severity": "error", "message": "expected twenty-five provider backend execution receipts"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "handoff status is not ready"})
    if package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label changed"})
    for row in receipt_rows:
        if row.get("execution_performed") is not True:
            issues.append({"issue_id": "backend_receipt_not_executed", "severity": "error", "message": "backend receipt row was not executed"})
        if "raw_credential" in row or "secret" in row:
            issues.append({"issue_id": "secret_like_material_present", "severity": "error", "message": "secret-like material appeared in a provider backend receipt row"})
    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "provider_backend_row_count": registry.get("provider_backend_row_count", 0),
        "provider_backend_request_row_count": len(request_rows),
        "provider_backend_execution_receipt_row_count": len(receipt_rows),
        "handoff_status": handoff.get("handoff_status"),
        "source_adapter_provider_backend_interfaces_id": package.get("source_adapter_provider_backend_interfaces_id"),
    }
