from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_capture_setup_package_v1"
SOURCE_SELECTION_SCHEMA_VERSION = "source_adapter_source_selection_package_v1"
SETUP_PLAN_SCHEMA_VERSION = "source_adapter_capture_setup_plan_v1"
ARTIFACT_INTAKE_SCHEMA_VERSION = "source_adapter_capture_artifact_intake_plan_v1"
BROWSER_HANDOFF_SCHEMA_VERSION = "source_adapter_lightweight_browser_capture_setup_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_capture_setup_operator_summary_v1"

_READY_SELECTION_STATUS = "SOURCE_ADAPTER_SELECTION_READY"
_READY_CAPTURE_SETUP_STATUS = "SOURCE_ADAPTER_CAPTURE_SETUP_READY"
_BLOCKED_CAPTURE_SETUP_STATUS = "SOURCE_ADAPTER_CAPTURE_SETUP_BLOCKED"
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}


class SourceAdapterCaptureSetupError(ValueError):
    """Raised when source adapter capture-setup input is invalid."""


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(data: Mapping[str, Any], *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()[:length]


def _clean_identifier(value: object, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _coerce_mapping(value: object, *, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SourceAdapterCaptureSetupError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterCaptureSetupError(f"{name} must be a JSON array")
    return list(value)


def _normalise_text_list(value: object, *, name: str) -> list[str]:
    items: set[str] = set()
    for raw in _coerce_sequence(value or [], name=name):
        text = str(raw).strip()
        if text:
            items.add(text)
    return sorted(items)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterCaptureSetupError(f"{name} must not include local path fields: {', '.join(present)}")


def _assert_no_forbidden_keys(value: object, *, name: str) -> None:
    if isinstance(value, Mapping):
        _ensure_no_local_paths(value, name=name)
        for key, child in value.items():
            _assert_no_forbidden_keys(child, name=f"{name}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, name=f"{name}[{index}]")


def _selection_options(selection_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    catalog = _coerce_mapping(selection_package.get("source_selection_catalog", {}), name="source_selection_catalog")
    raw_options = _coerce_sequence(catalog.get("options", []), name="source_selection_catalog.options")
    options: list[dict[str, Any]] = []
    seen: set[str] = set()
    for option_index, raw in enumerate(raw_options):
        option = _coerce_mapping(raw, name=f"source_selection_catalog.options[{option_index}]")
        adapter_id = _clean_identifier(option.get("adapter_id"), fallback=f"adapter_{option_index + 1}").lower()
        if adapter_id in seen:
            raise SourceAdapterCaptureSetupError(f"duplicate adapter_id: {adapter_id}")
        seen.add(adapter_id)
        options.append(
            {
                "adapter_id": adapter_id,
                "display_name": str(option.get("display_name") or adapter_id.replace("_", " ").title()),
                "source_kind": str(option.get("source_kind") or "unknown"),
                "domains": _normalise_text_list(option.get("domains", []), name=f"options[{option_index}].domains"),
                "artifact_roles": _normalise_text_list(
                    option.get("artifact_roles", []), name=f"options[{option_index}].artifact_roles"
                ),
                "selection_enabled": bool(option.get("selection_enabled", False)),
                "requires_adapter_specific_module": bool(option.get("requires_adapter_specific_module", False)),
                "capture_route_key": str(option.get("capture_route_key") or f"{adapter_id}.shared_capture_route"),
            }
        )
    return options


def _selection_routes(selection_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    route_index = _coerce_mapping(selection_package.get("capture_route_index", {}), name="capture_route_index")
    raw_routes = _coerce_sequence(route_index.get("routes", []), name="capture_route_index.routes")
    routes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for route_index_number, raw in enumerate(raw_routes):
        route = _coerce_mapping(raw, name=f"capture_route_index.routes[{route_index_number}]")
        adapter_id = _clean_identifier(route.get("adapter_id"), fallback=f"adapter_{route_index_number + 1}").lower()
        if adapter_id in seen:
            raise SourceAdapterCaptureSetupError(f"duplicate route adapter_id: {adapter_id}")
        seen.add(adapter_id)
        routes.append(
            {
                "adapter_id": adapter_id,
                "capture_route_key": str(route.get("capture_route_key") or f"{adapter_id}.shared_capture_route"),
                "route_mode": str(route.get("route_mode") or "shared_pipeline_stage_sequence"),
                "source_kind": str(route.get("source_kind") or "unknown"),
                "artifact_roles": _normalise_text_list(
                    route.get("artifact_roles", []), name=f"routes[{route_index_number}].artifact_roles"
                ),
                "shared_stage_coverage": _normalise_text_list(
                    route.get("shared_stage_coverage", []), name=f"routes[{route_index_number}].shared_stage_coverage"
                ),
                "requires_manual_approval_before_live_navigation": bool(
                    route.get("requires_manual_approval_before_live_navigation", True)
                ),
            }
        )
    return routes


def _browser_capabilities_for_roles(artifact_roles: Sequence[str]) -> list[str]:
    role_set = set(artifact_roles)
    capabilities = {"operator_url_load", "render_wait"}
    if role_set.intersection({"article_html_or_text", "comments_json_or_text", "dom_snapshot", "metadata_json"}):
        capabilities.add("dom_snapshot")
    if "screenshot" in role_set:
        capabilities.add("screenshot_capture")
    if "comments_json_or_text" in role_set:
        capabilities.add("shadow_root_operator_snippet")
    return sorted(capabilities)


def build_source_adapter_capture_setup(source_selection_package: Mapping[str, Any]) -> dict[str, Any]:
    """Build a local capture setup package from source adapter source selection output."""

    source_selection_package = _coerce_mapping(source_selection_package, name="source_selection_package")
    _assert_no_forbidden_keys(source_selection_package, name="source_selection_package")
    if source_selection_package.get("schema_version") != SOURCE_SELECTION_SCHEMA_VERSION:
        raise SourceAdapterCaptureSetupError(
            "source_selection_package must use source_adapter_source_selection_package_v1"
        )

    selection_status = str(source_selection_package.get("selection_status") or "").strip().upper()
    selection_id = str(source_selection_package.get("source_adapter_source_selection_id") or "").strip()
    rollout_id = str(source_selection_package.get("source_adapter_registry_rollout_id") or "").strip()
    release_id = str(source_selection_package.get("source_adapter_registry_release_id") or "").strip()
    options = _selection_options(source_selection_package)
    routes = _selection_routes(source_selection_package)
    route_by_adapter = {route["adapter_id"]: route for route in routes}

    issues: list[str] = []
    if selection_status != _READY_SELECTION_STATUS:
        issues.append(f"selection_status must be {_READY_SELECTION_STATUS}")
    if not selection_id:
        issues.append("source_adapter_source_selection_id is required")
    if not rollout_id:
        issues.append("source_adapter_registry_rollout_id is required")
    if not options:
        issues.append("at least one source selection option is required")
    if not routes:
        issues.append("at least one capture route is required")

    setup_rows: list[dict[str, Any]] = []
    for option in options:
        route = route_by_adapter.get(option["adapter_id"])
        if not option["selection_enabled"]:
            issues.append(f"adapter {option['adapter_id']} is not selection_enabled")
        if route is None:
            issues.append(f"adapter {option['adapter_id']} has no capture route")
            route = {
                "capture_route_key": option["capture_route_key"],
                "route_mode": "shared_pipeline_stage_sequence",
                "artifact_roles": option["artifact_roles"],
                "shared_stage_coverage": [],
                "requires_manual_approval_before_live_navigation": True,
            }
        artifact_roles = sorted(set(option["artifact_roles"] or route.get("artifact_roles", [])))
        if not artifact_roles:
            issues.append(f"adapter {option['adapter_id']} has no artifact_roles")
        if not route.get("shared_stage_coverage"):
            issues.append(f"adapter {option['adapter_id']} has no shared_stage_coverage")
        setup_rows.append(
            {
                "adapter_id": option["adapter_id"],
                "display_name": option["display_name"],
                "source_kind": option["source_kind"],
                "domains": option["domains"],
                "capture_route_key": str(route.get("capture_route_key") or option["capture_route_key"]),
                "route_mode": str(route.get("route_mode") or "shared_pipeline_stage_sequence"),
                "artifact_roles": artifact_roles,
                "required_operator_inputs": [
                    "explicit_source_url_or_local_source_reference",
                    "adapter_selection_confirmation",
                    "capture_artifact_destination_confirmation",
                ],
                "capture_steps": [
                    "confirm_adapter_selection",
                    "prepare_operator_capture_context",
                    "request_explicit_approval_before_live_navigation",
                    "collect_declared_artifact_roles_after_operator_action",
                    "handoff_to_shared_artifact_collection",
                ],
                "browser_capabilities_required": _browser_capabilities_for_roles(artifact_roles),
                "requires_manual_approval_before_live_navigation": True,
                "live_network_default": False,
                "manual_or_live_actions_started": False,
                "app_files_mutated": False,
                "registry_mutation_applied": False,
            }
        )

    status = _READY_CAPTURE_SETUP_STATUS if not issues else _BLOCKED_CAPTURE_SETUP_STATUS
    base = {
        "source_adapter_source_selection_id": selection_id,
        "source_adapter_registry_rollout_id": rollout_id,
        "adapter_ids": [row["adapter_id"] for row in setup_rows],
        "issue_count": len(issues),
    }
    capture_setup_id = f"source_adapter_capture_setup.{_stable_hash(base)}"

    capture_setup_plan = {
        "schema_version": SETUP_PLAN_SCHEMA_VERSION,
        "source_adapter_capture_setup_id": capture_setup_id,
        "source_adapter_source_selection_id": selection_id,
        "capture_setup_status": status,
        "adapter_count": len(setup_rows),
        "setup_count": len(setup_rows),
        "setup_rows": setup_rows,
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }

    artifact_rows = [
        {
            "adapter_id": row["adapter_id"],
            "capture_route_key": row["capture_route_key"],
            "expected_artifact_roles": row["artifact_roles"],
            "artifact_collection_stage": "source_artifact_collection",
            "requires_explicit_operator_supplied_files": True,
            "scan_directories": False,
            "accept_absolute_paths": False,
        }
        for row in setup_rows
    ]
    artifact_intake_plan = {
        "schema_version": ARTIFACT_INTAKE_SCHEMA_VERSION,
        "source_adapter_capture_setup_id": capture_setup_id,
        "source_adapter_source_selection_id": selection_id,
        "artifact_intake_status": "READY_FOR_EXPLICIT_ARTIFACT_INTAKE" if status == _READY_CAPTURE_SETUP_STATUS else status,
        "adapter_count": len(artifact_rows),
        "artifact_intake_rows": artifact_rows,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "scan_directories": False,
        "app_files_mutated": False,
        "registry_mutation_applied": False,
    }

    capability_rows = [
        {
            "adapter_id": row["adapter_id"],
            "capture_route_key": row["capture_route_key"],
            "capabilities_required": row["browser_capabilities_required"],
            "approval_required_before_navigation": True,
            "approved_launch_performed": False,
            "live_network_default": False,
        }
        for row in setup_rows
    ]
    lightweight_browser_handoff = {
        "schema_version": BROWSER_HANDOFF_SCHEMA_VERSION,
        "source_adapter_capture_setup_id": capture_setup_id,
        "source_adapter_source_selection_id": selection_id,
        "handoff_status": "READY_FOR_APPROVED_BROWSER_CAPTURE_SETUP" if status == _READY_CAPTURE_SETUP_STATUS else status,
        "capability_binding_count": len(capability_rows),
        "capability_bindings": capability_rows,
        "expected_next_stage": "operator_approved_capture_session_planning",
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_capture_setup_id": capture_setup_id,
        "capture_setup_status": status,
        "adapter_count": len(setup_rows),
        "setup_count": len(setup_rows),
        "issue_count": len(issues),
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Use this capture setup package to wire the app source selector to shared capture routes.",
            "Keep browser navigation behind explicit operator approval before any live action.",
            "Route completed operator artifacts into source_artifact_collection rather than source-specific clones.",
        ],
    }

    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_capture_setup_id": capture_setup_id,
        "source_adapter_source_selection_id": selection_id,
        "source_adapter_registry_rollout_id": rollout_id,
        "source_adapter_registry_release_id": release_id,
        "selection_status": selection_status,
        "capture_setup_status": status,
        "adapter_count": len(setup_rows),
        "route_count": len(routes),
        "setup_count": len(setup_rows),
        "issue_count": len(issues),
        "issues": issues,
        "capture_setup_plan": capture_setup_plan,
        "artifact_intake_plan": artifact_intake_plan,
        "lightweight_browser_capture_setup_handoff": lightweight_browser_handoff,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise SourceAdapterCaptureSetupError("input JSON must be an object")
    return dict(data)


def write_json(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(_json_bytes(data))


def demo_source_selection_package() -> dict[str, Any]:
    return {
        "schema_version": SOURCE_SELECTION_SCHEMA_VERSION,
        "source_adapter_source_selection_id": "source_adapter_source_selection.example",
        "source_adapter_registry_rollout_id": "source_adapter_registry_rollout.example",
        "source_adapter_registry_release_id": "source_adapter_registry_release.example",
        "source_adapter_registry_update_id": "source_adapter_registry_update.example",
        "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
        "selection_status": _READY_SELECTION_STATUS,
        "source_selection_catalog": {
            "schema_version": "source_adapter_source_selection_catalog_v1",
            "source_adapter_source_selection_id": "source_adapter_source_selection.example",
            "selection_status": _READY_SELECTION_STATUS,
            "adapter_count": 1,
            "options": [
                {
                    "adapter_id": "article",
                    "display_name": "Article",
                    "source_kind": "web_article",
                    "domains": ["article.example"],
                    "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot"],
                    "selection_enabled": True,
                    "requires_adapter_specific_module": False,
                    "ui_group": "Web Article",
                    "capture_route_key": "article.shared_capture_route",
                }
            ],
            "app_files_mutated": False,
            "registry_mutation_applied": False,
            "manual_or_live_actions_started": False,
            "live_network_default": False,
        },
        "capture_route_index": {
            "schema_version": "source_adapter_capture_route_index_v1",
            "source_adapter_source_selection_id": "source_adapter_source_selection.example",
            "source_adapter_registry_rollout_id": "source_adapter_registry_rollout.example",
            "route_count": 1,
            "routes": [
                {
                    "adapter_id": "article",
                    "capture_route_key": "article.shared_capture_route",
                    "route_mode": "shared_pipeline_stage_sequence",
                    "source_kind": "web_article",
                    "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot"],
                    "shared_stage_coverage": [
                        "source_discovery",
                        "lightweight_browser_capture",
                        "artifact_collection",
                        "content_extraction",
                        "capture_bundle",
                        "total_export_package",
                        "evidence_queue",
                        "evidence_review",
                        "approved_release",
                        "release_index",
                        "release_audit",
                        "archive_handoff",
                        "archive_result_intake",
                        "archive_review",
                        "pipeline_closeout",
                    ],
                    "requires_manual_approval_before_live_navigation": True,
                    "live_network_default": False,
                }
            ],
            "app_files_mutated": False,
            "registry_mutation_applied": False,
            "manual_or_live_actions_started": False,
            "live_network_default": False,
        },
        "source_selection_capture_handoff": {
            "schema_version": "source_adapter_source_selection_capture_handoff_v1",
            "source_adapter_source_selection_id": "source_adapter_source_selection.example",
            "source_adapter_registry_rollout_id": "source_adapter_registry_rollout.example",
            "handoff_status": "READY_FOR_CAPTURE_SETUP_WIRING",
            "adapter_count": 1,
            "route_count": 1,
            "expected_next_stage": "capture_setup_source_selector_wiring",
            "app_files_mutated": False,
            "registry_mutation_applied": False,
            "manual_or_live_actions_started": False,
            "live_network_default": False,
        },
        "issues": [],
    }


if __name__ == "__main__":
    package = build_source_adapter_capture_setup(demo_source_selection_package())
    assert package["capture_setup_status"] == _READY_CAPTURE_SETUP_STATUS, package
    assert package["capture_setup_plan"]["setup_count"] == 1, package
    assert package["artifact_intake_plan"]["artifact_intake_status"] == "READY_FOR_EXPLICIT_ARTIFACT_INTAKE", package
    assert package["lightweight_browser_capture_setup_handoff"]["handoff_status"] == "READY_FOR_APPROVED_BROWSER_CAPTURE_SETUP", package
    assert package["operator_summary"]["manual_or_live_actions_started"] is False, package
    print("Source Adapter Capture Setup self-test passed.")
