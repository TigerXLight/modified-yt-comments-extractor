from __future__ import annotations

from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_registry_update_package_v1"
VERIFIER_SCHEMA_VERSION = "source_adapter_registry_update_verifier_v1"

_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}


def _walk_forbidden(value: object, issues: list[str], prefix: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in _FORBIDDEN_PATH_FIELDS:
                issues.append(f"forbidden local path field at {prefix}.{key}")
            _walk_forbidden(child, issues, f"{prefix}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _walk_forbidden(child, issues, f"{prefix}[{index}]")


def verify_source_adapter_registry_update(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        issues.append("unexpected schema_version")
    update_id = str(package.get("source_adapter_registry_update_id") or "")
    if not update_id.startswith("source_adapter_registry_update."):
        issues.append("source_adapter_registry_update_id is missing or invalid")
    if not package.get("source_adapter_coverage_acceptance_id"):
        issues.append("source_adapter_coverage_acceptance_id is required")
    rows = package.get("registry_rows", [])
    if not isinstance(rows, list) or not rows:
        issues.append("registry_rows must contain at least one adapter row")
    if int(package.get("adapter_count") or 0) != len(rows) if isinstance(rows, list) else True:
        issues.append("adapter_count does not match registry_rows")
    embedded_issues = package.get("issues", [])
    if not isinstance(embedded_issues, list):
        issues.append("issues must be a JSON array")
        embedded_count = 0
    else:
        embedded_count = len(embedded_issues)
    if int(package.get("issue_count") or 0) != embedded_count:
        issues.append("issue_count does not match issues")
    record = package.get("adapter_registry_record", {})
    if not isinstance(record, Mapping):
        issues.append("adapter_registry_record must be a JSON object")
    else:
        if record.get("source_adapter_registry_update_id") != update_id:
            issues.append("adapter_registry_record id does not match package")
        if record.get("manual_or_live_actions_started") is not False:
            issues.append("adapter_registry_record must not start manual or live actions")
    handoff = package.get("adapter_registry_release_handoff", {})
    if not isinstance(handoff, Mapping):
        issues.append("adapter_registry_release_handoff must be a JSON object")
    else:
        if handoff.get("source_adapter_registry_update_id") != update_id:
            issues.append("adapter_registry_release_handoff id does not match package")
    _walk_forbidden(package, issues, "package")
    verified = not issues and embedded_count == 0 and package.get("registry_update_status") == "ADAPTER_REGISTRY_UPDATE_READY"
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": package.get("source_adapter_coverage_acceptance_id", ""),
        "registry_update_status": package.get("registry_update_status", ""),
        "adapter_count": package.get("adapter_count", 0),
        "issue_count": len(issues),
        "issues": issues,
        "verified": verified,
    }


if __name__ == "__main__":
    from source_adapter_registry_update import build_source_adapter_registry_update

    package = build_source_adapter_registry_update(
        {
            "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
            "handoff_status": "READY_FOR_ADAPTER_REGISTRY_UPDATE",
            "adapters": [
                {
                    "adapter_id": "article",
                    "coverage_status": "ACCEPTED_SHARED_FIXTURE_COVERAGE",
                    "shared_stage_coverage": ["content_extraction"],
                    "accepted_for_shared_pipeline": True,
                }
            ],
        }
    )
    result = verify_source_adapter_registry_update(package)
    assert result["verified"] is True, result
    print("Source Adapter Registry Update verifier self-test passed.")
