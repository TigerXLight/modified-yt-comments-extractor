from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from source_adapter_priority_site_pack_execution_closeout import (
    HANDOFF_STATUS,
    HANDOFF_SCHEMA_VERSION,
    LOCAL_FIXTURE_RUN_PLAN_SCHEMA_VERSION,
    MANUAL_SMOKE_PLAN_SCHEMA_VERSION,
    ROADMAP_CLOSEOUT_SCHEMA_VERSION,
    SCHEMA_VERSION,
    SITE_PACK_MATRIX_SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_priority_site_pack_execution_closeout_verifier_v1"


def _issue(issue_id: str, message: str, *, severity: str = "error", **extra: Any) -> dict[str, Any]:
    issue = {"issue_id": issue_id, "severity": severity, "message": message}
    issue.update(extra)
    return issue


def _rows(container: Mapping[str, Any], key: str) -> list[Any]:
    rows = container.get(key)
    return rows if isinstance(rows, list) else []


def verify_source_adapter_priority_site_pack_execution_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not isinstance(package, Mapping):
        return {
            "schema_version": VERIFIER_SCHEMA_VERSION,
            "verified": False,
            "issue_count": 1,
            "issues": [_issue("package_type", "package must be a mapping")],
        }
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("schema_version", "unexpected priority site pack closeout schema", actual=package.get("schema_version")))
    if package.get("priority_site_pack_execution_closeout_status") != STATUS:
        issues.append(_issue("status", "priority site pack execution closeout status is not built", actual=package.get("priority_site_pack_execution_closeout_status")))
    if package.get("issue_count") != len(package.get("issues", [])):
        issues.append(_issue("issue_count", "issue_count must equal the length of issues"))
    matrix = package.get("source_adapter_priority_site_fixture_pack_matrix") or {}
    if matrix.get("schema_version") != SITE_PACK_MATRIX_SCHEMA_VERSION:
        issues.append(_issue("matrix_schema", "site fixture pack matrix schema is invalid"))
    site_pack_rows = _rows(matrix, "priority_site_pack_rows")
    if not site_pack_rows:
        issues.append(_issue("missing_site_pack_rows", "site fixture pack matrix must contain rows"))
    if matrix.get("priority_site_pack_count") != len(site_pack_rows):
        issues.append(_issue("site_pack_count", "priority site pack count does not match row count"))
    site_pack_ids: set[str] = set()
    for row in site_pack_rows:
        if not isinstance(row, Mapping):
            issues.append(_issue("site_pack_row_type", "site pack row must be a mapping"))
            continue
        site_pack_id = row.get("site_pack_id")
        if not site_pack_id:
            issues.append(_issue("site_pack_id", "site pack row is missing site_pack_id"))
        elif site_pack_id in site_pack_ids:
            issues.append(_issue("duplicate_site_pack_id", "site_pack_id must be unique", site_pack_id=site_pack_id))
        site_pack_ids.add(str(site_pack_id))
        for required_key in ("adapter_id", "source_kind", "fixture_types", "artifact_roles", "capability_ids", "expected_pipeline_stages"):
            if not row.get(required_key):
                issues.append(_issue("site_pack_required_key", "site pack row is missing required key", site_pack_id=site_pack_id, key=required_key))
        if row.get("site_specific_code_status") != "ADAPTER_SPEC_AND_FIXTURE_MAPPING_FIRST":
            issues.append(_issue("site_specific_code_status", "site pack should preserve adapter spec and fixture mapping first strategy", site_pack_id=site_pack_id))
    local_plan = package.get("source_adapter_priority_site_local_fixture_run_plan") or {}
    if local_plan.get("schema_version") != LOCAL_FIXTURE_RUN_PLAN_SCHEMA_VERSION:
        issues.append(_issue("local_plan_schema", "local fixture run plan schema is invalid"))
    local_rows = _rows(local_plan, "local_fixture_run_rows")
    if local_plan.get("local_fixture_run_count") != len(local_rows):
        issues.append(_issue("local_fixture_count", "local fixture run count does not match row count"))
    if len(local_rows) != len(site_pack_rows):
        issues.append(_issue("local_fixture_site_pack_coverage", "each site pack should have one local fixture run row"))
    manual_plan = package.get("source_adapter_priority_site_manual_smoke_plan") or {}
    if manual_plan.get("schema_version") != MANUAL_SMOKE_PLAN_SCHEMA_VERSION:
        issues.append(_issue("manual_smoke_plan_schema", "manual smoke plan schema is invalid"))
    manual_rows = _rows(manual_plan, "manual_smoke_rows")
    if manual_plan.get("manual_smoke_row_count") != len(manual_rows):
        issues.append(_issue("manual_smoke_count", "manual smoke count does not match row count"))
    if not manual_rows:
        issues.append(_issue("missing_manual_smoke_rows", "manual smoke plan must contain at least one row"))
    for row in manual_rows:
        if not isinstance(row, Mapping):
            issues.append(_issue("manual_smoke_row_type", "manual smoke row must be a mapping"))
            continue
        if row.get("execution_mode") != "operator_approved_manual_smoke":
            issues.append(_issue("manual_smoke_execution_mode", "manual smoke row must use operator-approved execution mode"))
        if row.get("operator_named_site_required") is not True:
            issues.append(_issue("manual_smoke_named_site", "manual smoke row must require a named site"))
        if row.get("receipt_capture_required") is not True:
            issues.append(_issue("manual_smoke_receipts", "manual smoke row must require receipt capture"))
        if not row.get("expected_receipt_fields"):
            issues.append(_issue("manual_smoke_receipt_fields", "manual smoke row must define receipt fields"))
    roadmap = package.get("source_adapter_priority_site_roadmap_closeout") or {}
    if roadmap.get("schema_version") != ROADMAP_CLOSEOUT_SCHEMA_VERSION:
        issues.append(_issue("roadmap_schema", "roadmap closeout schema is invalid"))
    if roadmap.get("keys_accounts_lookup_surface") != "keys_accounts.ui.credential_reference_selector":
        issues.append(_issue("keys_accounts_surface", "KEYS/ACCOUNTS lookup surface must be preserved"))
    handoff = package.get("source_adapter_priority_site_pack_execution_handoff") or {}
    if handoff.get("schema_version") != HANDOFF_SCHEMA_VERSION:
        issues.append(_issue("handoff_schema", "handoff schema is invalid"))
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append(_issue("handoff_status", "handoff status is not ready", actual=handoff.get("handoff_status")))
    for flag in ("ready_for_local_fixture_authoring", "ready_for_local_fixture_execution", "ready_for_operator_approved_manual_smoke"):
        if handoff.get(flag) is not True:
            issues.append(_issue("handoff_ready_flag", "handoff ready flag must be true", flag=flag))
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": deepcopy(issues),
        "source_adapter_priority_site_pack_execution_closeout_id": package.get("source_adapter_priority_site_pack_execution_closeout_id"),
        "priority_site_pack_count": len(site_pack_rows),
        "local_fixture_run_count": len(local_rows),
        "manual_smoke_row_count": len(manual_rows),
        "handoff_status": handoff.get("handoff_status"),
    }


def main() -> None:
    from source_adapter_priority_site_pack_execution_closeout import example_priority_site_pack_execution_closeout_package

    result = verify_source_adapter_priority_site_pack_execution_closeout(example_priority_site_pack_execution_closeout_package())
    assert result["verified"], result
    print("Source Adapter Priority Site Pack Execution Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
