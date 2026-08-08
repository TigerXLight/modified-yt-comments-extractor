from __future__ import annotations

import json
from typing import Any, Mapping

from source_adapter_local_asr_benchmark_lock_ticket_runtime import HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, LOCAL_ASR_PROFILE, ONLINE_ASR_CANDIDATE, ROW_KEY, STATUS, example_source_adapter_local_asr_benchmark_lock_ticket_runtime_package


def verify_source_adapter_local_asr_benchmark_lock_ticket_runtime(package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    package = dict(package or example_source_adapter_local_asr_benchmark_lock_ticket_runtime_package())
    rows = list(package.get(ROW_KEY, []))
    issues: list[str] = []
    if package.get("status") != STATUS:
        issues.append("status_mismatch")
    if package.get("handoff", {}).get("handoff_status") != HANDOFF_STATUS:
        issues.append("handoff_status_mismatch")
    if package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append("keys_accounts_label_mismatch")
    if package.get("operator_summary", {}).get("local_asr_profile") != LOCAL_ASR_PROFILE:
        issues.append("local_asr_profile_mismatch")
    if package.get("operator_summary", {}).get("online_asr_candidate") != ONLINE_ASR_CANDIDATE:
        issues.append("online_asr_candidate_mismatch")
    if not package.get("operator_summary", {}).get("online_asr_adjacent_to_local_asr"):
        issues.append("online_asr_adjacency_missing")
    if not rows:
        issues.append("missing_rows")
    if rows and any(row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL for row in rows):
        issues.append("row_keys_accounts_label_mismatch")
    if any(row.get("credential_secret_material_present") for row in rows):
        issues.append("secret_material_leak")
    if any(not row.get("receipt_required") for row in rows):
        issues.append("receipt_not_required")
    if any(row.get("network_execution_requires_explicit_operator_run") and not row.get("operator_approval_required") for row in rows):
        issues.append("network_execution_without_approval")
    if any(not row.get("online_asr_adjacent_to_local_asr") for row in rows):
        issues.append("row_online_asr_adjacency_missing")
    return {
        "schema_version": "source_adapter_local_asr_benchmark_lock_ticket_runtime_verification_v1",
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "status": package.get("status"),
        "handoff_status": package.get("handoff", {}).get("handoff_status"),
        "row_count": len(rows),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


if __name__ == "__main__":
    print(json.dumps(verify_source_adapter_local_asr_benchmark_lock_ticket_runtime(), indent=2, sort_keys=True))
