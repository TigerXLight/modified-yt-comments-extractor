from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_source_selection_package_v1"
ROLLOUT_PACKAGE_SCHEMA_VERSION = "source_adapter_registry_rollout_package_v1"
CATALOG_SCHEMA_VERSION = "source_adapter_source_selection_catalog_v1"
ROUTE_INDEX_SCHEMA_VERSION = "source_adapter_capture_route_index_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_source_selection_capture_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_source_selection_operator_summary_v1"

_READY_ROLLOUT_STATUS = "ADAPTER_REGISTRY_ROLLOUT_READY"
_READY_SELECTION_STATUS = "SOURCE_ADAPTER_SELECTION_READY"
_BLOCKED_SELECTION_STATUS = "SOURCE_ADAPTER_SELECTION_BLOCKED"
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}


class SourceAdapterSourceSelectionError(ValueError):
    """Raised when source adapter source selection input is invalid."""


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
        raise SourceAdapterSourceSelectionError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterSourceSelectionError(f"{name} must be a JSON array")
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
        raise SourceAdapterSourceSelectionError(f"{name} must not include local path fields: {', '.join(present)}")


def _assert_no_forbidden_keys(value: object, *, name: str) -> None:
    if isinstance(value, Mapping):
        _ensure_no_local_paths(value, name=name)
        for key, child in value.items():
            _assert_no_forbidden_keys(child, name=f"{name}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, name=f"{name}[{index}]")


def _rollout_options(rollout_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    index = _coerce_mapping(
        rollout_package.get("source_adapter_selection_option_index", {}),
        name="source_adapter_selection_option_index",
    )
    raw_options = _coerce_sequence(index.get("options", []), name="source_adapter_selection_option_index.options")
    options: list[dict[str, Any]] = []
    seen: set[str] = set()
    for option_index, raw in enumerate(raw_options):
        option = _coerce_mapping(raw, name=f"source_adapter_selection_option_index.options[{option_index}]")
        adapter_id = _clean_identifier(option.get("adapter_id"), fallback=f"adapter_{option_index + 1}").lower()
        if adapter_id in seen:
            raise SourceAdapterSourceSelectionError(f"duplicate adapter_id: {adapter_id}")
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
                "shared_stage_coverage": _normalise_text_list(
                    option.get("shared_stage_coverage", []), name=f"options[{option_index}].shared_stage_coverage"
                ),
                "requires_adapter_specific_module": bool(option.get("requires_adapter_specific_module", False)),
                "selection_enabled": bool(option.get("selection_enabled", False)),
            }
        )
    return options


def build_source_adapter_source_selection(rollout_package: Mapping[str, Any]) -> dict[str, Any]:
    """Build a local source-selection package from a reviewed registry rollout package."""

    rollout_package = _coerce_mapping(rollout_package, name="rollout_package")
    _assert_no_forbidden_keys(rollout_package, name="rollout_package")
    if rollout_package.get("schema_version") != ROLLOUT_PACKAGE_SCHEMA_VERSION:
        raise SourceAdapterSourceSelectionError("rollout_package must use source_adapter_registry_rollout_package_v1")

    rollout_status = str(rollout_package.get("registry_rollout_status") or "").strip().upper()
    rollout_id = str(rollout_package.get("source_adapter_registry_rollout_id") or "").strip()
    release_id = str(rollout_package.get("source_adapter_registry_release_id") or "").strip()
    update_id = str(rollout_package.get("source_adapter_registry_update_id") or "").strip()
    acceptance_id = str(rollout_package.get("source_adapter_coverage_acceptance_id") or "").strip()
    options = _rollout_options(rollout_package)

    issues: list[str] = []
    if rollout_status != _READY_ROLLOUT_STATUS:
        issues.append(f"registry_rollout_status must be {_READY_ROLLOUT_STATUS}")
    if not rollout_id:
        issues.append("source_adapter_registry_rollout_id is required")
    if not release_id:
        issues.append("source_adapter_registry_release_id is required")
    if not options:
        issues.append("at least one released selection option is required")
    for option in options:
        if not option["selection_enabled"]:
            issues.append(f"adapter {option['adapter_id']} is not selection_enabled")
        if not option["shared_stage_coverage"]:
            issues.append(f"adapter {option['adapter_id']} has no shared_stage_coverage")
        if not option["artifact_roles"]:
            issues.append(f"adapter {option['adapter_id']} has no artifact_roles")

    status = _READY_SELECTION_STATUS if not issues else _BLOCKED_SELECTION_STATUS
    base = {
        "source_adapter_registry_rollout_id": rollout_id,
        "source_adapter_registry_release_id": release_id,
        "adapter_ids": [option["adapter_id"] for option in options],
        "issue_count": len(issues),
    }
    selection_id = f"source_adapter_source_selection.{_stable_hash(base)}"

    catalog_options = [
        {
            "adapter_id": option["adapter_id"],
            "display_name": option["display_name"],
            "source_kind": option["source_kind"],
            "domains": option["domains"],
            "artifact_roles": option["artifact_roles"],
            "selection_enabled": status == _READY_SELECTION_STATUS and option["selection_enabled"],
            "requires_adapter_specific_module": option["requires_adapter_specific_module"],
            "ui_group": option["source_kind"].replace("_", " ").title(),
            "capture_route_key": f"{option['adapter_id']}.shared_capture_route",
        }
        for option in options
    ]

    source_selection_catalog = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "source_adapter_source_selection_id": selection_id,
        "source_adapter_registry_rollout_id": rollout_id,
        "selection_status": status,
        "adapter_count": len(catalog_options),
        "options": catalog_options,
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }

    route_rows = [
        {
            "adapter_id": option["adapter_id"],
            "capture_route_key": f"{option['adapter_id']}.shared_capture_route",
            "route_mode": "shared_pipeline_stage_sequence",
            "source_kind": option["source_kind"],
            "artifact_roles": option["artifact_roles"],
            "shared_stage_coverage": option["shared_stage_coverage"],
            "requires_manual_approval_before_live_navigation": True,
            "live_network_default": False,
        }
        for option in options
    ]
    capture_route_index = {
        "schema_version": ROUTE_INDEX_SCHEMA_VERSION,
        "source_adapter_source_selection_id": selection_id,
        "source_adapter_registry_rollout_id": rollout_id,
        "route_count": len(route_rows),
        "routes": route_rows,
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }

    capture_handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "source_adapter_source_selection_id": selection_id,
        "source_adapter_registry_rollout_id": rollout_id,
        "handoff_status": "READY_FOR_CAPTURE_SETUP_WIRING" if status == _READY_SELECTION_STATUS else status,
        "adapter_count": len(catalog_options),
        "route_count": len(route_rows),
        "expected_next_stage": "capture_setup_source_selector_wiring",
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_source_selection_id": selection_id,
        "selection_status": status,
        "adapter_count": len(catalog_options),
        "route_count": len(route_rows),
        "issue_count": len(issues),
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Use this source-selection package to wire the app source selector/view-model.",
            "Display released adapters as shared-pipeline source options without cloning MSN-specific flows.",
            "Require explicit operator approval before any live navigation or browser capture action.",
        ],
    }

    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_source_selection_id": selection_id,
        "source_adapter_registry_rollout_id": rollout_id,
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "registry_rollout_status": rollout_status,
        "selection_status": status,
        "adapter_count": len(catalog_options),
        "route_count": len(route_rows),
        "issue_count": len(issues),
        "issues": issues,
        "source_selection_catalog": source_selection_catalog,
        "capture_route_index": capture_route_index,
        "source_selection_capture_handoff": capture_handoff,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise SourceAdapterSourceSelectionError("input JSON must be an object")
    return dict(data)


def write_json(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(_json_bytes(data))


def demo_rollout_package() -> dict[str, Any]:
    return {
        "schema_version": ROLLOUT_PACKAGE_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": "source_adapter_registry_rollout.example",
        "source_adapter_registry_release_id": "source_adapter_registry_release.example",
        "source_adapter_registry_update_id": "source_adapter_registry_update.example",
        "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
        "registry_rollout_status": _READY_ROLLOUT_STATUS,
        "source_adapter_selection_option_index": {
            "schema_version": "source_adapter_selection_option_index_v1",
            "source_adapter_registry_rollout_id": "source_adapter_registry_rollout.example",
            "adapter_count": 1,
            "options": [
                {
                    "adapter_id": "article",
                    "display_name": "Article",
                    "source_kind": "web_article",
                    "domains": ["article.example"],
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
                    "requires_adapter_specific_module": False,
                    "selection_enabled": True,
                }
            ],
            "app_files_mutated": False,
            "registry_mutation_applied": False,
            "manual_or_live_actions_started": False,
            "live_network_default": False,
        },
    }


if __name__ == "__main__":
    package = build_source_adapter_source_selection(demo_rollout_package())
    assert package["selection_status"] == _READY_SELECTION_STATUS, package
    assert package["source_selection_catalog"]["adapter_count"] == 1, package
    assert package["capture_route_index"]["route_count"] == 1, package
    assert package["source_selection_capture_handoff"]["handoff_status"] == "READY_FOR_CAPTURE_SETUP_WIRING", package
    assert package["operator_summary"]["manual_or_live_actions_started"] is False, package
    print("Source Adapter Source Selection self-test passed.")
