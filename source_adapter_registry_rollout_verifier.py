from __future__ import annotations

from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_registry_rollout_package_v1"
VERIFIER_SCHEMA_VERSION = "source_adapter_registry_rollout_verifier_v1"
_READY_ROLLOUT_STATUS = "ADAPTER_REGISTRY_ROLLOUT_READY"
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


def verify_source_adapter_registry_rollout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        issues.append("unexpected schema_version")
    rollout_id = str(package.get("source_adapter_registry_rollout_id") or "")
    if not rollout_id.startswith("source_adapter_registry_rollout."):
        issues.append("source_adapter_registry_rollout_id is missing or invalid")
    if not str(package.get("source_adapter_registry_release_id") or "").startswith("source_adapter_registry_release."):
        issues.append("source_adapter_registry_release_id is missing or invalid")
    if not str(package.get("source_adapter_registry_update_id") or "").startswith("source_adapter_registry_update."):
        issues.append("source_adapter_registry_update_id is missing or invalid")
    rows = package.get("released_adapters", [])
    if not isinstance(rows, list) or not rows:
        issues.append("released_adapters must contain at least one adapter")
        row_count = 0
    else:
        row_count = len(rows)
    if int(package.get("adapter_count") or 0) != row_count:
        issues.append("adapter_count does not match released_adapters")
    embedded_issues = package.get("issues", [])
    if not isinstance(embedded_issues, list):
        issues.append("issues must be a JSON array")
        embedded_count = 0
    else:
        embedded_count = len(embedded_issues)
    if int(package.get("issue_count") or 0) != embedded_count:
        issues.append("issue_count does not match issues")
    plan = package.get("source_adapter_source_selection_wiring_plan", {})
    if not isinstance(plan, Mapping):
        issues.append("source_adapter_source_selection_wiring_plan must be a JSON object")
    else:
        if plan.get("source_adapter_registry_rollout_id") != rollout_id:
            issues.append("source selection wiring plan id does not match package")
        if plan.get("app_files_mutated") is not False:
            issues.append("rollout stage must not mutate app files")
        if plan.get("manual_or_live_actions_started") is not False:
            issues.append("rollout stage must not start manual/live actions")
    option_index = package.get("source_adapter_selection_option_index", {})
    if not isinstance(option_index, Mapping):
        issues.append("source_adapter_selection_option_index must be a JSON object")
    else:
        options = option_index.get("options", [])
        if isinstance(options, list) and len(options) != row_count:
            issues.append("selection option count does not match released_adapters")
    handoff = package.get("source_adapter_registry_rollout_app_handoff", {})
    if not isinstance(handoff, Mapping):
        issues.append("source_adapter_registry_rollout_app_handoff must be a JSON object")
    else:
        if handoff.get("source_adapter_registry_rollout_id") != rollout_id:
            issues.append("app handoff id does not match package")
        if handoff.get("app_files_mutated") is not False:
            issues.append("app handoff must not mutate app files")
        if handoff.get("manual_or_live_actions_started") is not False:
            issues.append("app handoff must not start manual or live actions")
    _walk_forbidden(package, issues, "package")
    verified = not issues and embedded_count == 0 and package.get("registry_rollout_status") == _READY_ROLLOUT_STATUS
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": rollout_id,
        "source_adapter_registry_release_id": package.get("source_adapter_registry_release_id", ""),
        "source_adapter_registry_update_id": package.get("source_adapter_registry_update_id", ""),
        "registry_rollout_status": package.get("registry_rollout_status", ""),
        "adapter_count": package.get("adapter_count", 0),
        "issue_count": len(issues),
        "issues": issues,
        "verified": verified,
    }


if __name__ == "__main__":
    from source_adapter_registry_rollout import REGISTRY_RELEASE_PACKAGE_SCHEMA_VERSION, build_source_adapter_registry_rollout

    package = build_source_adapter_registry_rollout(
        {
            "schema_version": REGISTRY_RELEASE_PACKAGE_SCHEMA_VERSION,
            "source_adapter_registry_release_id": "source_adapter_registry_release.example",
            "source_adapter_registry_update_id": "source_adapter_registry_update.example",
            "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
            "registry_release_status": "ADAPTER_REGISTRY_RELEASE_READY",
            "source_adapter_frozen_registry": {
                "adapters": [
                    {
                        "adapter_id": "article",
                        "shared_stage_coverage": ["content_extraction"],
                        "release_status": "RELEASED_FOR_SHARED_PIPELINE",
                    }
                ]
            },
            "source_adapter_registry_rollout_handoff": {
                "handoff_status": "READY_FOR_APP_SOURCE_SELECTION_WIRING",
                "registry_mutation_applied": False,
                "manual_or_live_actions_started": False,
            },
        }
    )
    result = verify_source_adapter_registry_rollout(package)
    assert result["verified"] is True, result
    print("Source Adapter Registry Rollout verifier self-test passed.")
