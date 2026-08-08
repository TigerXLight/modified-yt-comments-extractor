from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_release_archive_delivery_runtime import DELIVERY_RECEIPT_BATCH_STATUS, HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, STATUS, example_release_archive_delivery_runtime_package

SCHEMA_VERSION = "source_adapter_release_archive_delivery_runtime_verifier_v1"

def _rows(container: Mapping[str, Any], key: str):
    value = container.get(key) or []
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []

def verify_source_adapter_release_archive_delivery_runtime_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("release_archive_delivery_runtime_status") != STATUS:
        issues.append({"issue_id": "status_not_ready", "severity": "error"})
    handoff = package.get("source_adapter_release_archive_delivery_runtime_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error"})
    plan = package.get("source_adapter_release_archive_delivery_plan") or {}
    receipts = package.get("source_adapter_release_archive_delivery_receipt_batch") or {}
    if not isinstance(plan, Mapping) or plan.get("delivery_plan_row_count") != 20:
        issues.append({"issue_id": "unexpected_delivery_plan_row_count", "severity": "error"})
    if not isinstance(receipts, Mapping) or receipts.get("delivery_receipt_row_count") != 20:
        issues.append({"issue_id": "unexpected_delivery_receipt_row_count", "severity": "error"})
    if isinstance(receipts, Mapping) and receipts.get("release_archive_delivery_receipt_batch_status") != DELIVERY_RECEIPT_BATCH_STATUS:
        issues.append({"issue_id": "receipt_batch_not_ready", "severity": "error"})
    for row in _rows(receipts, "release_archive_delivery_receipt_rows"):
        path = Path(str(row.get("delivery_output_path")))
        if not path.exists():
            issues.append({"issue_id": "delivery_output_missing", "severity": "error", "path": str(path)})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error"})
    return {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_release_archive_delivery_runtime_id": package.get("source_adapter_release_archive_delivery_runtime_id"),
        "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
        "delivery_plan_row_count": plan.get("delivery_plan_row_count") if isinstance(plan, Mapping) else None,
        "delivery_receipt_row_count": receipts.get("delivery_receipt_row_count") if isinstance(receipts, Mapping) else None,
        "delivered_named_site_count": receipts.get("delivered_named_site_count") if isinstance(receipts, Mapping) else None,
        "issue_count": len(issues),
        "issues": issues,
        "verified": not issues,
    }

def main() -> None:
    print(json.dumps(verify_source_adapter_release_archive_delivery_runtime_package(example_release_archive_delivery_runtime_package()), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
