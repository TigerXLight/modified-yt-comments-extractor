from __future__ import annotations

from typing import Any, Mapping, Sequence

from source_adapter_operator_approved_execution_runtime import (
    APPROVAL_PACKET_STATUS,
    CREDENTIAL_LEDGER_STATUS,
    EXECUTION_QUEUE_STATUS,
    HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    PROVIDER_ACTIONS,
    PROVIDER_RECEIPT_BATCH_STATUS,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_operator_approved_execution_runtime_verifier_v1"
FORBIDDEN_SECRET_KEYS = {"credential_value", "raw_credential", "password", "api_key", "access_token", "session_cookie"}
FORBIDDEN_VALUE_MARKERS = ("BEGIN PRIVATE KEY", "sk-", "xoxb-", "sessionid=", "password=")


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _walk_secret_like(value: Any, path: str = "package") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in FORBIDDEN_SECRET_KEYS:
                findings.append(f"{path}.{key}")
            findings.extend(_walk_secret_like(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_walk_secret_like(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if any(marker in value for marker in FORBIDDEN_VALUE_MARKERS):
            findings.append(path)
    return findings


def verify_source_adapter_operator_approved_execution_runtime(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "operator approved execution runtime schema was not recognised"})
    if package.get("operator_approved_execution_runtime_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "operator approved execution runtime is not built"})

    approval_packet = package.get("source_adapter_operator_approval_packet") or {}
    execution_queue = package.get("source_adapter_operator_approved_execution_queue") or {}
    execution_rows = _rows(package.get("source_adapter_operator_approved_execution_rows"))
    receipt_batch = package.get("source_adapter_provider_execution_receipt_batch") or {}
    credential_ledger = package.get("source_adapter_redacted_credential_reference_ledger") or {}
    handoff = package.get("source_adapter_operator_approved_execution_runtime_handoff") or {}
    summary = package.get("operator_summary") or {}

    approval_rows = _rows(approval_packet.get("approval_packet_rows")) if isinstance(approval_packet, Mapping) else []
    queue_rows = _rows(execution_queue.get("execution_queue_rows")) if isinstance(execution_queue, Mapping) else []
    receipt_rows = _rows(receipt_batch.get("provider_execution_receipt_rows")) if isinstance(receipt_batch, Mapping) else []
    ledger_rows = _rows(credential_ledger.get("credential_reference_ledger_rows")) if isinstance(credential_ledger, Mapping) else []

    if approval_packet.get("operator_approval_packet_status") != APPROVAL_PACKET_STATUS or len(approval_rows) != 5:
        issues.append({"issue_id": "approval_packet_not_ready", "severity": "error", "message": "expected five approved operator packet rows"})
    if execution_queue.get("execution_queue_status") != EXECUTION_QUEUE_STATUS or len(queue_rows) != 5:
        issues.append({"issue_id": "execution_queue_not_ready", "severity": "error", "message": "expected five execution queue rows"})
    if len(execution_rows) != 5:
        issues.append({"issue_id": "execution_row_count_mismatch", "severity": "error", "message": "expected five executed rows"})
    expected_receipt_count = len(execution_rows) * len(PROVIDER_ACTIONS)
    if receipt_batch.get("provider_receipt_batch_status") != PROVIDER_RECEIPT_BATCH_STATUS or len(receipt_rows) != expected_receipt_count:
        issues.append({"issue_id": "provider_receipt_count_mismatch", "severity": "error", "message": f"expected {expected_receipt_count} provider receipts"})
    if credential_ledger.get("credential_reference_ledger_status") != CREDENTIAL_LEDGER_STATUS or len(ledger_rows) != 5:
        issues.append({"issue_id": "credential_ledger_not_recorded", "severity": "error", "message": "expected five redacted credential reference ledger rows"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "operator approved execution handoff is not ready"})
    if summary.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "summary_keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})

    for row in approval_rows:
        row_id = str(row.get("operator_approval_packet_row_id") or row.get("row_index"))
        if row.get("operator_approved") is not True:
            issues.append({"issue_id": "approval_row_not_operator_approved", "severity": "error", "message": row_id})
        if row.get("missing_operator_inputs"):
            issues.append({"issue_id": "approval_row_missing_inputs", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "approval_row_keys_accounts_changed", "severity": "error", "message": row_id})

    for row in queue_rows:
        row_id = str(row.get("execution_queue_row_id") or row.get("row_index"))
        if row.get("operator_approved") is not True:
            issues.append({"issue_id": "queue_row_not_approved", "severity": "error", "message": row_id})
        if set(row.get("provider_actions") or []) != set(PROVIDER_ACTIONS):
            issues.append({"issue_id": "queue_row_missing_provider_actions", "severity": "error", "message": row_id})

    for row in execution_rows:
        row_id = str(row.get("operator_approved_execution_row_id") or row.get("row_index"))
        if row.get("execution_performed") is not True:
            issues.append({"issue_id": "execution_row_not_performed", "severity": "error", "message": row_id})
        if row.get("provider_action_count") != len(PROVIDER_ACTIONS):
            issues.append({"issue_id": "execution_row_provider_action_count_mismatch", "severity": "error", "message": row_id})
        if row.get("remote_network_performed") is not False:
            issues.append({"issue_id": "execution_row_unexpected_remote_network", "severity": "error", "message": row_id})
        if row.get("raw_credential_material_stored") is not False:
            issues.append({"issue_id": "execution_row_raw_credential_material_stored", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "execution_row_keys_accounts_changed", "severity": "error", "message": row_id})

    for receipt in receipt_rows:
        receipt_id = str(receipt.get("provider_execution_receipt_id") or receipt.get("provider_action"))
        if receipt.get("provider_call_performed") is not True:
            issues.append({"issue_id": "provider_receipt_not_performed", "severity": "error", "message": receipt_id})
        if receipt.get("raw_credential_material_stored") is not False:
            issues.append({"issue_id": "provider_receipt_raw_credential_material_stored", "severity": "error", "message": receipt_id})
        if not receipt.get("redacted_credential_reference_hash"):
            issues.append({"issue_id": "provider_receipt_missing_redacted_reference_hash", "severity": "error", "message": receipt_id})
        if receipt.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "provider_receipt_keys_accounts_changed", "severity": "error", "message": receipt_id})

    secret_findings = _walk_secret_like(package)
    if secret_findings:
        issues.append({"issue_id": "secret_like_material_present", "severity": "error", "message": "; ".join(secret_findings[:5])})

    verified = not issues
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_operator_approved_execution_runtime_id": package.get("source_adapter_operator_approved_execution_runtime_id"),
        "approval_packet_row_count": len(approval_rows),
        "execution_queue_row_count": len(queue_rows),
        "executed_row_count": len(execution_rows),
        "provider_receipt_row_count": len(receipt_rows),
        "credential_reference_ledger_row_count": len(ledger_rows),
        "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
    }
