from __future__ import annotations

import json
from typing import Any, Mapping

from source_adapter_smoke_receipt_review_integration import (
    DECISION_BATCH_STATUS,
    EVIDENCE_INTEGRATION_STATUS,
    HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    RELEASE_GATE_STATUS,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_smoke_receipt_review_integration_verifier_v1"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def verify_source_adapter_smoke_receipt_review_integration_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "smoke receipt review integration schema was not recognised"})
    if package.get("smoke_receipt_review_integration_status") != STATUS:
        issues.append({"issue_id": "integration_not_built", "severity": "error", "message": "smoke receipt review integration was not built"})
    decisions = package.get("source_adapter_smoke_receipt_review_decision_batch") or {}
    integration = package.get("source_adapter_smoke_receipt_evidence_integration") or {}
    gate = package.get("source_adapter_smoke_receipt_release_export_gate") or {}
    handoff = package.get("source_adapter_smoke_receipt_review_integration_handoff") or {}
    decision_rows = _rows(decisions, "smoke_receipt_review_decision_rows")
    integration_rows = _rows(integration, "smoke_receipt_evidence_integration_rows")
    if decisions.get("smoke_receipt_review_decision_batch_status") != DECISION_BATCH_STATUS:
        issues.append({"issue_id": "decision_batch_not_ready", "severity": "error", "message": "review decisions were not ready"})
    if integration.get("smoke_receipt_evidence_integration_status") != EVIDENCE_INTEGRATION_STATUS:
        issues.append({"issue_id": "evidence_integration_not_ready", "severity": "error", "message": "evidence integration rows were not ready"})
    if gate.get("release_export_gate_status") != RELEASE_GATE_STATUS or not gate.get("ready_for_release_export_integration"):
        issues.append({"issue_id": "release_export_gate_not_ready", "severity": "error", "message": "release/export gate was not ready"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "review integration handoff was not ready"})
    if len(decision_rows) != 25:
        issues.append({"issue_id": "unexpected_decision_count", "severity": "error", "message": "expected 25 review decision rows"})
    if len(integration_rows) != 5:
        issues.append({"issue_id": "unexpected_evidence_integration_count", "severity": "error", "message": "expected five evidence integration rows"})
    if any(row.get("raw_credential_material_stored") for row in decision_rows):
        issues.append({"issue_id": "raw_credential_material_stored", "severity": "error", "message": "raw credential material was present in review decisions"})
    if package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "smoke_receipt_review_decision_row_count": len(decision_rows),
        "smoke_receipt_evidence_integration_row_count": len(integration_rows),
        "handoff_status": handoff.get("handoff_status"),
        "source_adapter_smoke_receipt_review_integration_id": package.get("source_adapter_smoke_receipt_review_integration_id"),
    }


if __name__ == "__main__":
    from source_adapter_smoke_receipt_review_integration import example_smoke_receipt_review_integration_package

    print(json.dumps(verify_source_adapter_smoke_receipt_review_integration_package(example_smoke_receipt_review_integration_package()), indent=2, sort_keys=True))
