from __future__ import annotations

import json
from typing import Any, Mapping

from source_adapter_scroll_plan_executor_runtime import HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, ROW_KEY, ROW_STATUS, STATUS, example_source_adapter_scroll_plan_executor_runtime_package

SCHEMA_VERSION = "source_adapter_scroll_plan_executor_runtime_verifier_v1"


def verify_source_adapter_scroll_plan_executor_runtime(package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    package = dict(package or example_source_adapter_scroll_plan_executor_runtime_package())
    rows = list(package.get(ROW_KEY) or [])
    issues: list[str] = []
    if package.get("status") != STATUS:
        issues.append("unexpected package status")
    if package.get("handoff", {}).get("handoff_status") != HANDOFF_STATUS:
        issues.append("unexpected handoff status")
    if not rows:
        issues.append("missing runtime rows")
    if any(row.get("row_status") != ROW_STATUS for row in rows):
        issues.append("unexpected row status")
    if any(row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL for row in rows):
        issues.append("KEYS/ACCOUNTS label missing")
    if any(row.get("credential_secret_material_present") for row in rows):
        issues.append("credential secret material present")
    if not all(row.get("receipt_required") for row in rows):
        issues.append("receipt requirement missing")
    if not all(row.get("implemented_runtime_surface") for row in rows):
        issues.append("runtime surface flag missing")
    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "status": package.get("status"),
        "handoff_status": package.get("handoff", {}).get("handoff_status"),
        "row_count": len(rows),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


if __name__ == "__main__":
    print(json.dumps(verify_source_adapter_scroll_plan_executor_runtime(), indent=2, sort_keys=True))
