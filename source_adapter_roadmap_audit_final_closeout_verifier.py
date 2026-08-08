from __future__ import annotations

from typing import Any, Mapping

from source_adapter_roadmap_audit_final_closeout import (
    COMPLETION_INDEX_SCHEMA_VERSION,
    FINAL_HANDOFF_SCHEMA_VERSION,
    HANDOFF_STATUS,
    LIVE_EXECUTION_ACCEPTANCE_SCHEMA_VERSION,
    MASTER_AUDIT_SCHEMA_VERSION,
    REGRESSION_PROMOTION_SCHEMA_VERSION,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_roadmap_audit_final_closeout_verifier_v1"


def _issue(issue_id: str, message: str, *, severity: str = "error") -> dict[str, Any]:
    return {"issue_id": issue_id, "severity": severity, "message": message}


def verify_source_adapter_roadmap_audit_final_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("unexpected_schema", "roadmap audit final closeout schema was not recognised"))
    if package.get("roadmap_audit_final_closeout_status") != STATUS:
        issues.append(_issue("unexpected_status", "roadmap audit final closeout status is not built"))
    if not package.get("source_adapter_roadmap_audit_final_closeout_id"):
        issues.append(_issue("missing_closeout_id", "final closeout id is required"))
    if package.get("issue_count") != len(package.get("issues", [])):
        issues.append(_issue("issue_count_mismatch", "issue_count must match issues length"))
    completion = package.get("source_adapter_roadmap_completion_index") or {}
    if completion.get("schema_version") != COMPLETION_INDEX_SCHEMA_VERSION:
        issues.append(_issue("completion_index_schema", "completion index schema was not recognised"))
    if completion.get("completion_status") != "SOURCE_ADAPTER_ROADMAP_REQUIRED_SECTIONS_CLOSED":
        issues.append(_issue("completion_index_not_closed", "roadmap completion index is not closed"))
    if completion.get("closed_section_count", 0) < completion.get("required_section_count", 0):
        issues.append(_issue("closed_section_shortfall", "closed section count is below required section count"))
    regression = package.get("source_adapter_regression_promotion_manifest") or {}
    if regression.get("schema_version") != REGRESSION_PROMOTION_SCHEMA_VERSION:
        issues.append(_issue("regression_manifest_schema", "regression promotion manifest schema was not recognised"))
    if regression.get("regression_promotion_status") != "SOURCE_ADAPTER_NAMED_SITE_FIXTURES_READY_FOR_REGRESSION_PROMOTION":
        issues.append(_issue("regression_not_ready", "named-site fixture rows are not ready for regression promotion"))
    if regression.get("ready_promotion_row_count") != regression.get("promotion_row_count"):
        issues.append(_issue("promotion_row_shortfall", "ready promotion rows must match promotion row count"))
    live = package.get("source_adapter_live_execution_acceptance_manifest") or {}
    if live.get("schema_version") != LIVE_EXECUTION_ACCEPTANCE_SCHEMA_VERSION:
        issues.append(_issue("live_manifest_schema", "live execution acceptance manifest schema was not recognised"))
    if live.get("live_execution_acceptance_status") != "SOURCE_ADAPTER_OPERATOR_APPROVED_LIVE_EXECUTION_RECEIPTS_ACCEPTED":
        issues.append(_issue("live_execution_not_accepted", "operator-approved live execution receipts are not accepted"))
    if live.get("keys_accounts_redacted_credential_references_ok") is not True:
        issues.append(_issue("keys_accounts_redaction_missing", "KEYS/ACCOUNTS redacted credential reference status must be true"))
    master = package.get("source_adapter_master_coverage_audit_closeout") or {}
    if master.get("schema_version") != MASTER_AUDIT_SCHEMA_VERSION:
        issues.append(_issue("master_audit_schema", "master coverage audit closeout schema was not recognised"))
    if master.get("coverage_audit_closed") is not True:
        issues.append(_issue("master_audit_not_closed", "master coverage audit must be closed"))
    if master.get("keys_accounts_label") != "KEYS/ACCOUNTS":
        issues.append(_issue("keys_accounts_label", "KEYS/ACCOUNTS label must be preserved"))
    handoff = package.get("source_adapter_final_release_handoff") or {}
    if handoff.get("schema_version") != FINAL_HANDOFF_SCHEMA_VERSION:
        issues.append(_issue("handoff_schema", "final release handoff schema was not recognised"))
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append(_issue("handoff_not_ready", "final release handoff is not ready"))
    verified = not issues
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_roadmap_audit_final_closeout_id": package.get("source_adapter_roadmap_audit_final_closeout_id"),
        "closed_section_count": completion.get("closed_section_count", 0),
        "promotion_row_count": regression.get("promotion_row_count", 0),
        "live_execution_row_count": live.get("live_execution_row_count", 0),
        "handoff_status": handoff.get("handoff_status"),
    }


def main() -> None:
    from source_adapter_roadmap_audit_final_closeout import example_roadmap_audit_final_closeout_package

    verification = verify_source_adapter_roadmap_audit_final_closeout(example_roadmap_audit_final_closeout_package())
    assert verification["verified"], verification
    print("Source Adapter Roadmap Audit Final Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
