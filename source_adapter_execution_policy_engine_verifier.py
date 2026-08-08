from __future__ import annotations

import json
from typing import Any, Mapping

from source_adapter_execution_policy_engine import HANDOFF_STATUS, ROW_KEY, STATUS, example_source_adapter_execution_policy_engine_package

SCHEMA_VERSION = "source_adapter_execution_policy_engine_verifier_v1"


def verify_source_adapter_execution_policy_engine_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("status") != STATUS:
        issues.append({"issue_id": "status_mismatch", "severity": "error", "observed": package.get("status")})
    rows = package.get(ROW_KEY) or []
    if len(rows) != 25:
        issues.append({"issue_id": "row_count_mismatch", "severity": "error", "observed": len(rows)})
    for index, row in enumerate(rows if isinstance(rows, list) else []):
        if not isinstance(row, Mapping):
            issues.append({"issue_id": "row_not_mapping", "severity": "error", "row_index": index})
            continue
        if row.get("keys_accounts_label") != "KEYS/ACCOUNTS":
            issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "row_index": index})
        if row.get("credential_secret_material_present"):
            issues.append({"issue_id": "secret_material_present", "severity": "error", "row_index": index})
        if not row.get("receipt_required"):
            issues.append({"issue_id": "receipt_not_required", "severity": "error", "row_index": index})
    handoff = package.get("handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error"})
    return {
        "schema_version": SCHEMA_VERSION,
        "id": package.get("id"),
        "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
        "row_count": len(rows) if isinstance(rows, list) else 0,
        "issue_count": len(issues),
        "issues": issues,
        "verified": not issues,
    }


if __name__ == "__main__":
    print(json.dumps(verify_source_adapter_execution_policy_engine_package(example_source_adapter_execution_policy_engine_package()), indent=2, sort_keys=True))
