from __future__ import annotations

from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_source_selection_package_v1"
_READY_SELECTION_STATUS = "SOURCE_ADAPTER_SELECTION_READY"
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


def verify_source_adapter_source_selection_package(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not _is_mapping(package):
        issues.append("package must be a JSON object")
        return {
            "schema_version": "source_adapter_source_selection_verifier_v1",
            "verified": False,
            "issue_count": len(issues),
            "issues": issues,
            "source_adapter_source_selection_id": "",
            "selection_status": "",
            "adapter_count": 0,
            "route_count": 0,
        }

    if package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        issues.append("schema_version must be source_adapter_source_selection_package_v1")
    if package.get("selection_status") != _READY_SELECTION_STATUS:
        issues.append("selection_status must be SOURCE_ADAPTER_SELECTION_READY")

    catalog = package.get("source_selection_catalog", {})
    if not _is_mapping(catalog):
        issues.append("source_selection_catalog must be a JSON object")
        catalog_options: list[Any] = []
    else:
        catalog_options = list(catalog.get("options", [])) if _is_sequence(catalog.get("options", [])) else []
        if not catalog_options:
            issues.append("source_selection_catalog.options must not be empty")
        if catalog.get("app_files_mutated") is not False:
            issues.append("source_selection_catalog.app_files_mutated must be false")
        if catalog.get("manual_or_live_actions_started") is not False:
            issues.append("source_selection_catalog.manual_or_live_actions_started must be false")

    route_index = package.get("capture_route_index", {})
    if not _is_mapping(route_index):
        issues.append("capture_route_index must be a JSON object")
        routes: list[Any] = []
    else:
        routes = list(route_index.get("routes", [])) if _is_sequence(route_index.get("routes", [])) else []
        if not routes:
            issues.append("capture_route_index.routes must not be empty")
        if route_index.get("app_files_mutated") is not False:
            issues.append("capture_route_index.app_files_mutated must be false")
        if route_index.get("manual_or_live_actions_started") is not False:
            issues.append("capture_route_index.manual_or_live_actions_started must be false")

    handoff = package.get("source_selection_capture_handoff", {})
    if not _is_mapping(handoff):
        issues.append("source_selection_capture_handoff must be a JSON object")
    else:
        if handoff.get("handoff_status") != "READY_FOR_CAPTURE_SETUP_WIRING":
            issues.append("source_selection_capture_handoff.handoff_status must be READY_FOR_CAPTURE_SETUP_WIRING")
        if handoff.get("app_files_mutated") is not False:
            issues.append("source_selection_capture_handoff.app_files_mutated must be false")
        if handoff.get("manual_or_live_actions_started") is not False:
            issues.append("source_selection_capture_handoff.manual_or_live_actions_started must be false")

    issues.extend(_collect_forbidden_path_fields(package))
    embedded_issues = package.get("issues", [])
    embedded_count = len(embedded_issues) if _is_sequence(embedded_issues) else 1
    if embedded_count:
        issues.append("package contains embedded issues")

    verified = not issues
    return {
        "schema_version": "source_adapter_source_selection_verifier_v1",
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_source_selection_id": str(package.get("source_adapter_source_selection_id", "")),
        "source_adapter_registry_rollout_id": str(package.get("source_adapter_registry_rollout_id", "")),
        "selection_status": str(package.get("selection_status", "")),
        "adapter_count": int(package.get("adapter_count", 0) or 0),
        "route_count": int(package.get("route_count", 0) or 0),
    }


if __name__ == "__main__":
    from source_adapter_source_selection import build_source_adapter_source_selection, demo_rollout_package

    package = build_source_adapter_source_selection(demo_rollout_package())
    verification = verify_source_adapter_source_selection_package(package)
    assert verification["verified"] is True, verification
    mutated = dict(package)
    mutated["source_selection_catalog"] = dict(package["source_selection_catalog"])
    mutated["source_selection_catalog"]["app_files_mutated"] = True
    assert verify_source_adapter_source_selection_package(mutated)["verified"] is False
    print("Source Adapter Source Selection verifier self-test passed.")
