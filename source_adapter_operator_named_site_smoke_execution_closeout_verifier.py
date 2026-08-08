from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from source_adapter_operator_named_site_smoke_execution_closeout import (
    HANDOFF_SCHEMA_VERSION,
    HANDOFF_STATUS,
    LOCAL_FIXTURE_EXECUTION_SCHEMA_VERSION,
    MANUAL_SMOKE_EXECUTION_SCHEMA_VERSION,
    RECEIPT_ACCEPTANCE_SCHEMA_VERSION,
    ROADMAP_FINAL_CLOSEOUT_SCHEMA_VERSION,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_operator_named_site_smoke_execution_closeout_verifier_v1"


def _issue(issue_id: str, message: str, *, severity: str = "error", **extra: Any) -> dict[str, Any]:
    issue = {"issue_id": issue_id, "severity": severity, "message": message}
    issue.update(extra)
    return issue


def _rows(container: Mapping[str, Any], key: str) -> list[Any]:
    rows = container.get(key)
    return rows if isinstance(rows, list) else []


def verify_source_adapter_operator_named_site_smoke_execution_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not isinstance(package, Mapping):
        return {
            "schema_version": VERIFIER_SCHEMA_VERSION,
            "verified": False,
            "issue_count": 1,
            "issues": [_issue("package_type", "package must be a mapping")],
        }
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("schema_version", "unexpected operator named-site smoke execution closeout schema", actual=package.get("schema_version")))
    if package.get("operator_named_site_smoke_execution_closeout_status") != STATUS:
        issues.append(_issue("status", "operator named-site smoke execution closeout status is not built", actual=package.get("operator_named_site_smoke_execution_closeout_status")))
    if package.get("issue_count") != len(package.get("issues", [])):
        issues.append(_issue("issue_count", "issue_count must equal the length of issues"))
    local_batch = package.get("source_adapter_operator_named_site_local_fixture_execution_batch") or {}
    if local_batch.get("schema_version") != LOCAL_FIXTURE_EXECUTION_SCHEMA_VERSION:
        issues.append(_issue("local_batch_schema", "local fixture execution batch schema is invalid"))
    local_rows = _rows(local_batch, "local_fixture_execution_rows")
    if local_batch.get("local_fixture_execution_count") != len(local_rows):
        issues.append(_issue("local_fixture_count", "local fixture execution count does not match row count"))
    if not local_rows:
        issues.append(_issue("missing_local_rows", "local fixture execution rows are required"))
    local_site_ids: set[str] = set()
    for row in local_rows:
        if not isinstance(row, Mapping):
            issues.append(_issue("local_row_type", "local fixture execution row must be a mapping"))
            continue
        site_pack_id = row.get("site_pack_id")
        if site_pack_id in local_site_ids:
            issues.append(_issue("duplicate_local_site_pack", "local fixture execution rows must have unique site_pack_id", site_pack_id=site_pack_id))
        local_site_ids.add(str(site_pack_id))
        if not row.get("operator_named_site_id"):
            issues.append(_issue("local_named_site", "local fixture row must include operator_named_site_id", site_pack_id=site_pack_id))
        if not row.get("source_url"):
            issues.append(_issue("local_source_url", "local fixture row must include source_url", site_pack_id=site_pack_id))
        manifest = row.get("fixture_manifest") or {}
        if not manifest.get("fixture_files"):
            issues.append(_issue("fixture_manifest", "fixture manifest must include fixture files", site_pack_id=site_pack_id))
        receipt = row.get("local_fixture_execution_receipt") or {}
        if receipt.get("receipt_status") != "LOCAL_FIXTURE_EXECUTION_RECEIPT_ACCEPTED":
            issues.append(_issue("local_receipt", "local fixture execution receipt must be accepted", site_pack_id=site_pack_id))
        if row.get("ready_for_operator_approved_manual_smoke") is not True:
            issues.append(_issue("local_ready_flag", "local fixture row must be ready for manual smoke", site_pack_id=site_pack_id))
    manual_batch = package.get("source_adapter_operator_named_site_manual_smoke_execution_batch") or {}
    if manual_batch.get("schema_version") != MANUAL_SMOKE_EXECUTION_SCHEMA_VERSION:
        issues.append(_issue("manual_batch_schema", "manual smoke execution batch schema is invalid"))
    manual_rows = _rows(manual_batch, "manual_smoke_execution_rows")
    if manual_batch.get("manual_smoke_execution_count") != len(manual_rows):
        issues.append(_issue("manual_smoke_count", "manual smoke execution count does not match row count"))
    if not manual_rows:
        issues.append(_issue("missing_manual_rows", "manual smoke execution rows are required"))
    for row in manual_rows:
        if not isinstance(row, Mapping):
            issues.append(_issue("manual_row_type", "manual smoke execution row must be a mapping"))
            continue
        row_id = row.get("operator_named_site_manual_smoke_execution_row_id")
        if row.get("execution_mode") != "operator_approved_manual_smoke":
            issues.append(_issue("manual_execution_mode", "manual smoke execution mode must be operator-approved", row_id=row_id))
        if row.get("receipt_capture_required") is not True:
            issues.append(_issue("manual_receipt_required", "manual smoke execution must require receipt capture", row_id=row_id))
        if row.get("missing_receipt_fields"):
            issues.append(_issue("manual_missing_receipt_fields", "manual smoke receipt has missing fields", row_id=row_id, missing_receipt_fields=row.get("missing_receipt_fields")))
        if row.get("manual_smoke_execution_status") != "OPERATOR_RECORDED_SMOKE_RECEIPT_ACCEPTED":
            issues.append(_issue("manual_status", "manual smoke execution receipt must be accepted", row_id=row_id, actual=row.get("manual_smoke_execution_status")))
        payload = row.get("receipt_payload") or {}
        for required_field in row.get("expected_receipt_fields") or []:
            if required_field not in payload:
                issues.append(_issue("manual_expected_field", "manual smoke receipt missing expected field", row_id=row_id, field=required_field))
        if payload.get("credential_reference_id") and not payload.get("redacted_reference_hash"):
            issues.append(_issue("credential_redaction", "credential receipt must include redacted reference hash", row_id=row_id))
    acceptance = package.get("source_adapter_operator_named_site_receipt_acceptance_index") or {}
    if acceptance.get("schema_version") != RECEIPT_ACCEPTANCE_SCHEMA_VERSION:
        issues.append(_issue("acceptance_schema", "receipt acceptance index schema is invalid"))
    if acceptance.get("receipt_acceptance_status") != "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_RECEIPTS_ACCEPTED":
        issues.append(_issue("acceptance_status", "receipt acceptance index is not accepted", actual=acceptance.get("receipt_acceptance_status")))
    if acceptance.get("accepted_local_fixture_receipt_count") != len(local_rows):
        issues.append(_issue("accepted_local_count", "all local fixture receipts must be accepted"))
    if acceptance.get("accepted_manual_smoke_receipt_count") != len(manual_rows):
        issues.append(_issue("accepted_manual_count", "all manual smoke receipts must be accepted"))
    if acceptance.get("keys_accounts_redacted_credential_references_ok") is not True:
        issues.append(_issue("keys_accounts_redaction", "KEYS/ACCOUNTS credential references must be redacted in receipts"))
    roadmap = package.get("source_adapter_operator_named_site_roadmap_final_closeout") or {}
    if roadmap.get("schema_version") != ROADMAP_FINAL_CLOSEOUT_SCHEMA_VERSION:
        issues.append(_issue("roadmap_schema", "roadmap final closeout schema is invalid"))
    if roadmap.get("runtime_receipt_coverage_complete") is not True:
        issues.append(_issue("roadmap_receipt_coverage", "roadmap final closeout must mark runtime receipt coverage complete"))
    if roadmap.get("keys_accounts_lookup_surface") != "keys_accounts.ui.credential_reference_selector":
        issues.append(_issue("keys_accounts_surface", "KEYS/ACCOUNTS lookup surface must be preserved"))
    handoff = package.get("source_adapter_operator_named_site_smoke_execution_handoff") or {}
    if handoff.get("schema_version") != HANDOFF_SCHEMA_VERSION:
        issues.append(_issue("handoff_schema", "operator named-site smoke execution handoff schema is invalid"))
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append(_issue("handoff_status", "handoff is not ready for final audit", actual=handoff.get("handoff_status")))
    for flag in ("ready_for_source_evidence_roadmap_final_audit", "ready_for_priority_fixture_regression_promotion", "ready_for_operator_approved_provider_receipt_attachment"):
        if handoff.get(flag) is not True:
            issues.append(_issue("handoff_ready_flag", "handoff ready flag must be true", flag=flag))
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": deepcopy(issues),
        "source_adapter_operator_named_site_smoke_execution_closeout_id": package.get("source_adapter_operator_named_site_smoke_execution_closeout_id"),
        "priority_site_pack_count": len(local_rows),
        "local_fixture_execution_count": len(local_rows),
        "manual_smoke_execution_count": len(manual_rows),
        "accepted_manual_smoke_receipt_count": acceptance.get("accepted_manual_smoke_receipt_count"),
        "handoff_status": handoff.get("handoff_status"),
    }


def main() -> None:
    from source_adapter_operator_named_site_smoke_execution_closeout import example_operator_named_site_smoke_execution_closeout_package

    result = verify_source_adapter_operator_named_site_smoke_execution_closeout(example_operator_named_site_smoke_execution_closeout_package())
    assert result["verified"], result
    print("Source Adapter Operator Named Site Smoke Execution Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
