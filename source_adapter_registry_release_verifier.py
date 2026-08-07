from __future__ import annotations

from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_registry_release_package_v1"
VERIFIER_SCHEMA_VERSION = "source_adapter_registry_release_verifier_v1"
_READY_RELEASE_STATUS = "ADAPTER_REGISTRY_RELEASE_READY"
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


def verify_source_adapter_registry_release(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        issues.append("unexpected schema_version")
    release_id = str(package.get("source_adapter_registry_release_id") or "")
    if not release_id.startswith("source_adapter_registry_release."):
        issues.append("source_adapter_registry_release_id is missing or invalid")
    if not str(package.get("source_adapter_registry_update_id") or "").startswith("source_adapter_registry_update."):
        issues.append("source_adapter_registry_update_id is missing or invalid")
    if not package.get("source_adapter_coverage_acceptance_id"):
        issues.append("source_adapter_coverage_acceptance_id is required")
    rows = package.get("registry_rows", [])
    if not isinstance(rows, list) or not rows:
        issues.append("registry_rows must contain at least one adapter row")
        row_count = 0
    else:
        row_count = len(rows)
    if int(package.get("adapter_count") or 0) != row_count:
        issues.append("adapter_count does not match registry_rows")
    embedded_issues = package.get("issues", [])
    if not isinstance(embedded_issues, list):
        issues.append("issues must be a JSON array")
        embedded_count = 0
    else:
        embedded_count = len(embedded_issues)
    if int(package.get("issue_count") or 0) != embedded_count:
        issues.append("issue_count does not match issues")
    record = package.get("adapter_registry_release_record", {})
    if not isinstance(record, Mapping):
        issues.append("adapter_registry_release_record must be a JSON object")
    else:
        if record.get("source_adapter_registry_release_id") != release_id:
            issues.append("adapter_registry_release_record id does not match package")
        if record.get("registry_mutation_applied") is not False:
            issues.append("adapter registry release must not mutate registry files")
        if record.get("manual_or_live_actions_started") is not False:
            issues.append("adapter registry release must not start manual or live actions")
    frozen = package.get("source_adapter_frozen_registry", {})
    if not isinstance(frozen, Mapping):
        issues.append("source_adapter_frozen_registry must be a JSON object")
    else:
        if frozen.get("source_adapter_registry_release_id") != release_id:
            issues.append("source_adapter_frozen_registry id does not match package")
        frozen_rows = frozen.get("adapters", [])
        if isinstance(frozen_rows, list) and len(frozen_rows) != row_count:
            issues.append("source_adapter_frozen_registry adapter count does not match registry_rows")
    handoff = package.get("source_adapter_registry_rollout_handoff", {})
    if not isinstance(handoff, Mapping):
        issues.append("source_adapter_registry_rollout_handoff must be a JSON object")
    else:
        if handoff.get("source_adapter_registry_release_id") != release_id:
            issues.append("source_adapter_registry_rollout_handoff id does not match package")
        if handoff.get("registry_mutation_applied") is not False:
            issues.append("source_adapter_registry_rollout_handoff must not mutate registry files")
    _walk_forbidden(package, issues, "package")
    verified = not issues and embedded_count == 0 and package.get("registry_release_status") == _READY_RELEASE_STATUS
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": package.get("source_adapter_registry_update_id", ""),
        "source_adapter_coverage_acceptance_id": package.get("source_adapter_coverage_acceptance_id", ""),
        "registry_release_status": package.get("registry_release_status", ""),
        "adapter_count": package.get("adapter_count", 0),
        "issue_count": len(issues),
        "issues": issues,
        "verified": verified,
    }


if __name__ == "__main__":
    from source_adapter_registry_release import UPDATE_PACKAGE_SCHEMA_VERSION, build_source_adapter_registry_release

    package = build_source_adapter_registry_release(
        {
            "schema_version": UPDATE_PACKAGE_SCHEMA_VERSION,
            "source_adapter_registry_update_id": "source_adapter_registry_update.example",
            "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
            "registry_update_status": "ADAPTER_REGISTRY_UPDATE_READY",
            "registry_rows": [
                {
                    "adapter_id": "article",
                    "shared_stage_coverage": ["content_extraction"],
                    "registered_for_shared_pipeline": True,
                }
            ],
            "adapter_registry_release_handoff": {
                "handoff_status": "READY_FOR_SOURCE_ADAPTER_RELEASE_REVIEW",
                "manual_or_live_actions_started": False,
            },
        }
    )
    result = verify_source_adapter_registry_release(package)
    assert result["verified"] is True, result
    print("Source Adapter Registry Release verifier self-test passed.")
