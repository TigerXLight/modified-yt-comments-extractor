from __future__ import annotations

from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_capture_setup_package_v1"
_READY_CAPTURE_SETUP_STATUS = "SOURCE_ADAPTER_CAPTURE_SETUP_READY"
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}


def _is_mapping(value: object) -> bool:
    return isinstance(value, Mapping)


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _collect_forbidden_path_fields(value: object, *, prefix: str = "package") -> list[str]:
    issues: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}"
            if str(key) in _FORBIDDEN_PATH_FIELDS:
                issues.append(f"forbidden local path field: {child_prefix}")
            issues.extend(_collect_forbidden_path_fields(child, prefix=child_prefix))
    elif _is_sequence(value):
        for index, child in enumerate(value):
            issues.extend(_collect_forbidden_path_fields(child, prefix=f"{prefix}[{index}]"))
    return issues


def verify_source_adapter_capture_setup_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not _is_mapping(package):
        issues.append("package must be a JSON object")
        return {
            "schema_version": "source_adapter_capture_setup_verifier_v1",
            "verified": False,
            "issue_count": len(issues),
            "issues": issues,
            "source_adapter_capture_setup_id": "",
            "capture_setup_status": "",
            "adapter_count": 0,
            "setup_count": 0,
        }

    if package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        issues.append("schema_version must be source_adapter_capture_setup_package_v1")
    if package.get("capture_setup_status") != _READY_CAPTURE_SETUP_STATUS:
        issues.append("capture_setup_status must be SOURCE_ADAPTER_CAPTURE_SETUP_READY")

    setup_plan = package.get("capture_setup_plan", {})
    if not _is_mapping(setup_plan):
        issues.append("capture_setup_plan must be a JSON object")
        setup_rows: list[Any] = []
    else:
        setup_rows = list(setup_plan.get("setup_rows", [])) if _is_sequence(setup_plan.get("setup_rows", [])) else []
        if not setup_rows:
            issues.append("capture_setup_plan.setup_rows must not be empty")
        if setup_plan.get("app_files_mutated") is not False:
            issues.append("capture_setup_plan.app_files_mutated must be false")
        if setup_plan.get("manual_or_live_actions_started") is not False:
            issues.append("capture_setup_plan.manual_or_live_actions_started must be false")
        for index, row in enumerate(setup_rows):
            if not _is_mapping(row):
                issues.append(f"capture_setup_plan.setup_rows[{index}] must be a JSON object")
                continue
            if row.get("requires_manual_approval_before_live_navigation") is not True:
                issues.append(f"setup row {index} must require manual approval before live navigation")
            if row.get("manual_or_live_actions_started") is not False:
                issues.append(f"setup row {index} manual_or_live_actions_started must be false")

    artifact_plan = package.get("artifact_intake_plan", {})
    if not _is_mapping(artifact_plan):
        issues.append("artifact_intake_plan must be a JSON object")
    else:
        rows = artifact_plan.get("artifact_intake_rows", [])
        if not _is_sequence(rows) or not rows:
            issues.append("artifact_intake_plan.artifact_intake_rows must not be empty")
        if artifact_plan.get("scan_directories") is not False:
            issues.append("artifact_intake_plan.scan_directories must be false")
        if artifact_plan.get("manual_or_live_actions_started") is not False:
            issues.append("artifact_intake_plan.manual_or_live_actions_started must be false")

    browser_handoff = package.get("lightweight_browser_capture_setup_handoff", {})
    if not _is_mapping(browser_handoff):
        issues.append("lightweight_browser_capture_setup_handoff must be a JSON object")
    else:
        if browser_handoff.get("handoff_status") != "READY_FOR_APPROVED_BROWSER_CAPTURE_SETUP":
            issues.append(
                "lightweight_browser_capture_setup_handoff.handoff_status must be READY_FOR_APPROVED_BROWSER_CAPTURE_SETUP"
            )
        if browser_handoff.get("manual_or_live_actions_started") is not False:
            issues.append("lightweight_browser_capture_setup_handoff.manual_or_live_actions_started must be false")
        bindings = browser_handoff.get("capability_bindings", [])
        if not _is_sequence(bindings) or not bindings:
            issues.append("lightweight_browser_capture_setup_handoff.capability_bindings must not be empty")

    issues.extend(_collect_forbidden_path_fields(package))
    embedded_issues = package.get("issues", [])
    embedded_count = len(embedded_issues) if _is_sequence(embedded_issues) else 1
    if embedded_count:
        issues.append("package contains embedded issues")

    verified = not issues
    return {
        "schema_version": "source_adapter_capture_setup_verifier_v1",
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_capture_setup_id": str(package.get("source_adapter_capture_setup_id", "")),
        "source_adapter_source_selection_id": str(package.get("source_adapter_source_selection_id", "")),
        "capture_setup_status": str(package.get("capture_setup_status", "")),
        "adapter_count": int(package.get("adapter_count", 0) or 0),
        "setup_count": int(package.get("setup_count", 0) or 0),
    }


if __name__ == "__main__":
    from source_adapter_capture_setup import build_source_adapter_capture_setup, demo_source_selection_package

    package = build_source_adapter_capture_setup(demo_source_selection_package())
    verification = verify_source_adapter_capture_setup_package(package)
    assert verification["verified"] is True, verification
    mutated = dict(package)
    mutated["capture_setup_plan"] = dict(package["capture_setup_plan"])
    mutated["capture_setup_plan"]["manual_or_live_actions_started"] = True
    assert verify_source_adapter_capture_setup_package(mutated)["verified"] is False
    print("Source Adapter Capture Setup verifier self-test passed.")
