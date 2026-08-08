from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_named_site_smoke_execution import (
    ACTION_RECEIPT_BATCH_STATUS,
    HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    MATRIX_STATUS,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_named_site_smoke_execution_verifier_v1"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def verify_source_adapter_named_site_smoke_execution_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "named-site smoke execution schema was not recognised"})
    if package.get("named_site_smoke_execution_status") != STATUS:
        issues.append({"issue_id": "execution_not_built", "severity": "error", "message": "named-site smoke execution status was not built"})
    matrix = package.get("source_adapter_named_site_smoke_execution_matrix") or {}
    batch = package.get("source_adapter_named_site_provider_action_receipt_batch") or {}
    manifest = package.get("source_adapter_named_site_smoke_execution_manifest") or {}
    handoff = package.get("source_adapter_named_site_smoke_execution_handoff") or {}
    site_rows = _rows(matrix, "named_site_smoke_execution_site_rows")
    receipt_rows = _rows(batch, "named_site_provider_action_receipt_rows")
    if matrix.get("named_site_smoke_execution_matrix_status") != MATRIX_STATUS:
        issues.append({"issue_id": "matrix_not_ready", "severity": "error", "message": "named-site smoke execution matrix was not ready"})
    if batch.get("named_site_provider_action_receipt_batch_status") != ACTION_RECEIPT_BATCH_STATUS:
        issues.append({"issue_id": "action_receipts_not_ready", "severity": "error", "message": "named-site provider action receipts were not ready"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "named-site smoke handoff was not ready"})
    if len(site_rows) != 5:
        issues.append({"issue_id": "unexpected_site_count", "severity": "error", "message": "expected five named-site smoke execution rows"})
    if len(receipt_rows) != 25:
        issues.append({"issue_id": "unexpected_action_receipt_count", "severity": "error", "message": "expected 25 named-site action receipt rows"})
    for row in receipt_rows:
        if not row.get("provider_command_execution_succeeded"):
            issues.append({"issue_id": "provider_action_receipt_failed", "severity": "error", "message": "provider action receipt did not succeed", "row_id": row.get("named_site_provider_action_receipt_id")})
        receipt_path = row.get("provider_receipt_path")
        if receipt_path and not Path(str(receipt_path)).exists():
            issues.append({"issue_id": "provider_receipt_path_missing", "severity": "error", "message": "provider receipt path does not exist", "path": str(receipt_path)})
        if row.get("raw_credential_material_stored"):
            issues.append({"issue_id": "raw_credential_material_stored", "severity": "error", "message": "raw credential material was marked as stored"})
    manifest_path = manifest.get("manifest_path")
    if not manifest_path or not Path(str(manifest_path)).exists():
        issues.append({"issue_id": "manifest_missing", "severity": "error", "message": "named-site smoke manifest was not written"})
    if package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "named_site_execution_site_count": len(site_rows),
        "named_site_provider_action_receipt_row_count": len(receipt_rows),
        "handoff_status": handoff.get("handoff_status"),
        "source_adapter_named_site_smoke_execution_id": package.get("source_adapter_named_site_smoke_execution_id"),
    }


if __name__ == "__main__":
    from source_adapter_named_site_smoke_execution import example_named_site_smoke_execution_package

    print(json.dumps(verify_source_adapter_named_site_smoke_execution_package(example_named_site_smoke_execution_package()), indent=2, sort_keys=True))
