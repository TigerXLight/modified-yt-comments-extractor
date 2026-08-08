from __future__ import annotations

import json
from typing import Any, Mapping

from source_adapter_evidence_export_runtime_bridge import HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, STATUS, example_evidence_export_runtime_bridge_package

SCHEMA_VERSION = "source_adapter_evidence_export_runtime_bridge_verifier_v1"

def verify_source_adapter_evidence_export_runtime_bridge_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("evidence_export_runtime_bridge_status") != STATUS:
        issues.append({"issue_id": "status_not_ready", "severity": "error"})
    handoff = package.get("source_adapter_evidence_export_runtime_bridge_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error"})
    expected_counts = {
        "source_adapter_evidence_export_queue": ("evidence_export_queue_row_count", 5),
        "source_adapter_total_export_source_package": ("total_export_source_row_count", 5),
        "source_adapter_release_index_runtime_package": ("release_index_runtime_row_count", 5),
        "source_adapter_archive_handoff_runtime_package": ("archive_handoff_runtime_row_count", 5),
    }
    for key, (count_key, expected) in expected_counts.items():
        value = package.get(key) or {}
        if not isinstance(value, Mapping) or value.get(count_key) != expected:
            issues.append({"issue_id": f"unexpected_{count_key}", "severity": "error", "expected": expected, "observed": value.get(count_key) if isinstance(value, Mapping) else None})
        if isinstance(value, Mapping) and value.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": f"{key}_keys_accounts_label_changed", "severity": "error"})
    if package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "operator_summary_keys_accounts_label_changed", "severity": "error"})
    return {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_evidence_export_runtime_bridge_id": package.get("source_adapter_evidence_export_runtime_bridge_id"),
        "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
        "evidence_export_queue_row_count": (package.get("source_adapter_evidence_export_queue") or {}).get("evidence_export_queue_row_count"),
        "total_export_source_row_count": (package.get("source_adapter_total_export_source_package") or {}).get("total_export_source_row_count"),
        "release_index_runtime_row_count": (package.get("source_adapter_release_index_runtime_package") or {}).get("release_index_runtime_row_count"),
        "archive_handoff_runtime_row_count": (package.get("source_adapter_archive_handoff_runtime_package") or {}).get("archive_handoff_runtime_row_count"),
        "issue_count": len(issues),
        "issues": issues,
        "verified": not issues,
    }

def main() -> None:
    print(json.dumps(verify_source_adapter_evidence_export_runtime_bridge_package(example_evidence_export_runtime_bridge_package()), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
