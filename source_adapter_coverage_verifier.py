from __future__ import annotations

from typing import Any, Mapping

from source_adapter_coverage import PIPELINE_STAGE_IDS

SCHEMA_VERSION = "source_adapter_coverage_verifier_v1"


def verify_source_adapter_coverage(payload: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if payload.get("schema_version") != "source_adapter_coverage_v1":
        issues.append("unexpected schema_version")
    if payload.get("coverage_strategy") != "one_framework_many_adapters":
        issues.append("coverage_strategy must be one_framework_many_adapters")
    adapters = payload.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        issues.append("at least one adapter is required")
    stage_matrix = payload.get("stage_matrix")
    if not isinstance(stage_matrix, list):
        issues.append("stage_matrix must be present")
    else:
        stage_ids = [row.get("stage_id") for row in stage_matrix if isinstance(row, Mapping)]
        for required in PIPELINE_STAGE_IDS:
            if required not in stage_ids:
                issues.append(f"missing pipeline stage: {required}")
        for row in stage_matrix:
            if not isinstance(row, Mapping):
                issues.append("stage_matrix row must be an object")
                continue
            if row.get("adapter_specific_module_required") is not False:
                issues.append(f"{row.get('stage_id', '<unknown>')}: adapter_specific_module_required must be false")
            if row.get("coverage_mode") != "shared_framework":
                issues.append(f"{row.get('stage_id', '<unknown>')}: coverage_mode must be shared_framework")
    browser = payload.get("lightweight_browser_plan")
    if not isinstance(browser, Mapping):
        issues.append("lightweight_browser_plan is required")
    else:
        if browser.get("execution_mode") != "operator_approved_manual_only":
            issues.append("lightweight browser execution_mode must remain operator_approved_manual_only")
        if browser.get("live_network_default") is not False:
            issues.append("lightweight browser live_network_default must be false")
        if browser.get("approval_required_before_navigation") is not True:
            issues.append("lightweight browser must require approval before navigation")
    operator = payload.get("operator_summary")
    if not isinstance(operator, Mapping):
        issues.append("operator_summary is required")
    else:
        if operator.get("manual_or_live_actions_started") is not False:
            issues.append("coverage planning must not start manual/live actions")
        if operator.get("live_network_default") is not False:
            issues.append("operator live_network_default must be false")
    return {
        "schema_version": SCHEMA_VERSION,
        "coverage_id": payload.get("coverage_id"),
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }
