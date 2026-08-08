from __future__ import annotations

import json
from typing import Any, Mapping
from source_adapter_total_export_finalization_runtime import STATUS, HANDOFF_STATUS, example_source_adapter_total_export_finalization_runtime_package

SCHEMA_VERSION = "source_adapter_total_export_finalization_runtime_verifier_v1"


def verify_source_adapter_total_export_finalization_runtime_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("status") != STATUS:
        issues.append({"issue_id": "status_not_ready", "severity": "error"})
    handoff = package.get("handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error"})
    if package.get("operator_summary", {}).get("keys_accounts_label") != "KEYS/ACCOUNTS":
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error"})
    if int(package.get("issue_count", 0)) != 0:
        issues.append({"issue_id": "package_reported_issues", "severity": "error"})
    return {"schema_version": SCHEMA_VERSION, "id": package.get("id"), "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None, "issue_count": len(issues), "issues": issues, "verified": not issues}

if __name__ == "__main__":
    print(json.dumps(verify_source_adapter_total_export_finalization_runtime_package(example_source_adapter_total_export_finalization_runtime_package()), indent=2, sort_keys=True))
