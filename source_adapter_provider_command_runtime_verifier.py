from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_provider_command_runtime import (
    HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    RECEIPT_BATCH_STATUS,
    REQUEST_MATRIX_STATUS,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_provider_command_runtime_verifier_v1"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def verify_source_adapter_provider_command_runtime_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "provider command runtime schema was not recognised"})
    if package.get("provider_command_runtime_status") != STATUS:
        issues.append({"issue_id": "runtime_not_built", "severity": "error", "message": "provider command runtime status was not built"})
    matrix = package.get("source_adapter_provider_command_request_matrix") or {}
    batch = package.get("source_adapter_provider_command_execution_receipt_batch") or {}
    handoff = package.get("source_adapter_provider_command_runtime_handoff") or {}
    request_rows = _rows(matrix, "provider_command_request_rows")
    receipt_rows = _rows(batch, "provider_command_execution_receipt_rows")
    if matrix.get("provider_command_request_matrix_status") != REQUEST_MATRIX_STATUS:
        issues.append({"issue_id": "request_matrix_not_ready", "severity": "error", "message": "provider command request matrix was not ready"})
    if batch.get("provider_command_execution_receipt_batch_status") != RECEIPT_BATCH_STATUS:
        issues.append({"issue_id": "receipt_batch_not_ready", "severity": "error", "message": "provider command execution receipts were not ready"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "provider command runtime handoff was not ready"})
    if len(request_rows) != 25:
        issues.append({"issue_id": "unexpected_request_count", "severity": "error", "message": "expected 25 provider command request rows"})
    if len(receipt_rows) != 25:
        issues.append({"issue_id": "unexpected_receipt_count", "severity": "error", "message": "expected 25 provider command execution receipt rows"})
    for row in receipt_rows:
        if row.get("returncode") != 0 or not row.get("execution_succeeded"):
            issues.append({"issue_id": "command_execution_failed", "severity": "error", "message": "provider command row did not succeed", "row_id": row.get("provider_command_execution_receipt_id")})
        path = Path(str(row.get("receipt_path") or ""))
        if not path.exists():
            issues.append({"issue_id": "missing_receipt_file", "severity": "error", "message": "provider command receipt file was not written", "path": str(path)})
        else:
            text = path.read_text(encoding="utf-8")
            if "hidden-token-value" in text:
                issues.append({"issue_id": "secret_material_leaked", "severity": "error", "message": "raw secret material appeared in receipt text", "path": str(path)})
    if package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "provider_command_request_row_count": len(request_rows),
        "provider_command_execution_receipt_row_count": len(receipt_rows),
        "handoff_status": handoff.get("handoff_status"),
        "source_adapter_provider_command_runtime_id": package.get("source_adapter_provider_command_runtime_id"),
    }


if __name__ == "__main__":
    from source_adapter_provider_command_runtime import example_provider_command_runtime_package

    print(json.dumps(verify_source_adapter_provider_command_runtime_package(example_provider_command_runtime_package()), indent=2, sort_keys=True))
