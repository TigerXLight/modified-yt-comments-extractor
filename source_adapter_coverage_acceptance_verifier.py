from __future__ import annotations

from typing import Any, Mapping

VERIFIER_SCHEMA_VERSION = "source_adapter_coverage_acceptance_verifier_v1"


def verify_source_adapter_coverage_acceptance(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    acceptance_id = str(package.get("source_adapter_coverage_acceptance_id") or "")
    if not acceptance_id:
        issues.append("source_adapter_coverage_acceptance_id is required")
    if package.get("schema_version") != "source_adapter_coverage_acceptance_package_v1":
        issues.append("schema_version must be source_adapter_coverage_acceptance_package_v1")
    closeout_id = str(package.get("source_adapter_fixture_pipeline_closeout_id") or "")
    if not closeout_id:
        issues.append("source_adapter_fixture_pipeline_closeout_id is required")
    acceptance_record = package.get("acceptance_record")
    if not isinstance(acceptance_record, Mapping):
        issues.append("acceptance_record must be present")
        acceptance_record = {}
    registry_handoff = package.get("adapter_registry_handoff")
    if not isinstance(registry_handoff, Mapping):
        issues.append("adapter_registry_handoff must be present")
        registry_handoff = {}
    if acceptance_record.get("source_adapter_coverage_acceptance_id") != acceptance_id:
        issues.append("acceptance_record id does not match package")
    if registry_handoff.get("source_adapter_coverage_acceptance_id") != acceptance_id:
        issues.append("adapter_registry_handoff id does not match package")
    status = str(package.get("acceptance_status") or "")
    if status == "ADAPTER_COVERAGE_ACCEPTED":
        if int(package.get("accepted_adapter_count") or 0) != int(package.get("adapter_count") or 0):
            issues.append("accepted package must have accepted_adapter_count equal adapter_count")
        if registry_handoff.get("handoff_status") != "READY_FOR_ADAPTER_REGISTRY_UPDATE":
            issues.append("accepted package must hand off to adapter registry update")
    else:
        if int(package.get("accepted_adapter_count") or 0) != 0:
            issues.append("non-accepted package must not count accepted adapters")
    if int(package.get("issue_count") or 0) != len(package.get("issues", [])):
        issues.append("issue_count does not match issues length")
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "source_adapter_fixture_pipeline_closeout_id": closeout_id,
        "acceptance_status": status,
        "adapter_count": int(package.get("adapter_count") or 0),
        "accepted_adapter_count": int(package.get("accepted_adapter_count") or 0),
    }
