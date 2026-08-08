from __future__ import annotations

import json
from typing import Any, Mapping

from source_adapter_operator_delivery_receipt_closeout import HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, STATUS, example_operator_delivery_receipt_closeout_package

SCHEMA_VERSION = "source_adapter_operator_delivery_receipt_closeout_verifier_v1"

def _rows(container: Mapping[str, Any], key: str):
    value = container.get(key) or []
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []

def verify_source_adapter_operator_delivery_receipt_closeout_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("operator_delivery_receipt_closeout_status") != STATUS:
        issues.append({"issue_id": "status_not_ready", "severity": "error"})
    handoff = package.get("source_adapter_operator_delivery_receipt_closeout_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error"})
    review = package.get("source_adapter_operator_delivery_receipt_review") or {}
    acceptance = package.get("source_adapter_operator_delivery_acceptance_matrix") or {}
    gate = package.get("source_adapter_operator_delivery_release_gate") or {}
    if not isinstance(review, Mapping) or review.get("operator_delivery_receipt_review_row_count") != 20:
        issues.append({"issue_id": "unexpected_review_row_count", "severity": "error"})
    if not isinstance(acceptance, Mapping) or acceptance.get("operator_delivery_acceptance_row_count") != 5:
        issues.append({"issue_id": "unexpected_acceptance_row_count", "severity": "error"})
    if not isinstance(gate, Mapping) or gate.get("release_section_completion_ready") is not True:
        issues.append({"issue_id": "release_section_completion_not_ready", "severity": "error"})
    for section_name, row_key in [
        ("source_adapter_operator_delivery_receipt_review", "operator_delivery_receipt_review_rows"),
        ("source_adapter_operator_delivery_acceptance_matrix", "operator_delivery_acceptance_rows"),
    ]:
        section = package.get(section_name) or {}
        if isinstance(section, Mapping):
            for row in _rows(section, row_key):
                if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
                    issues.append({"issue_id": f"{section_name}_keys_accounts_label_changed", "severity": "error"})
    return {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_operator_delivery_receipt_closeout_id": package.get("source_adapter_operator_delivery_receipt_closeout_id"),
        "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
        "operator_delivery_receipt_review_row_count": review.get("operator_delivery_receipt_review_row_count") if isinstance(review, Mapping) else None,
        "operator_delivery_acceptance_row_count": acceptance.get("operator_delivery_acceptance_row_count") if isinstance(acceptance, Mapping) else None,
        "release_section_completion_ready": gate.get("release_section_completion_ready") if isinstance(gate, Mapping) else None,
        "issue_count": len(issues),
        "issues": issues,
        "verified": not issues,
    }

def main() -> None:
    print(json.dumps(verify_source_adapter_operator_delivery_receipt_closeout_package(example_operator_delivery_receipt_closeout_package()), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
