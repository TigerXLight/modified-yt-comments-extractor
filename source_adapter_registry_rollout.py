from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_registry_rollout_package_v1"
REGISTRY_RELEASE_PACKAGE_SCHEMA_VERSION = "source_adapter_registry_release_package_v1"
SELECTION_PLAN_SCHEMA_VERSION = "source_adapter_source_selection_wiring_plan_v1"
OPTION_INDEX_SCHEMA_VERSION = "source_adapter_selection_option_index_v1"
VALIDATION_CHECKLIST_SCHEMA_VERSION = "source_adapter_registry_rollout_validation_checklist_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_registry_rollout_app_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_registry_rollout_operator_summary_v1"

_READY_RELEASE_STATUS = "ADAPTER_REGISTRY_RELEASE_READY"
_READY_HANDOFF_STATUS = "READY_FOR_APP_SOURCE_SELECTION_WIRING"
_READY_ROLLOUT_STATUS = "ADAPTER_REGISTRY_ROLLOUT_READY"
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}


class SourceAdapterRegistryRolloutError(ValueError):
    """Raised when source adapter registry rollout input is invalid."""


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
        raise SourceAdapterRegistryRolloutError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterRegistryRolloutError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterRegistryRolloutError(f"{name} must not include local path fields: {', '.join(present)}")


def _assert_no_forbidden_keys(value: object, *, name: str) -> None:
    if isinstance(value, Mapping):
        _ensure_no_local_paths(value, name=name)
        for key, child in value.items():
            _assert_no_forbidden_keys(child, name=f"{name}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, name=f"{name}[{index}]")


def _normalise_text_list(value: object, *, name: str) -> list[str]:
    items: set[str] = set()
    for raw in _coerce_sequence(value or [], name=name):
        text = str(raw).strip()
        if text:
            items.add(text)
    return sorted(items)


def _released_rows(registry_release_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    frozen = _coerce_mapping(registry_release_package.get("source_adapter_frozen_registry", {}), name="source_adapter_frozen_registry")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(_coerce_sequence(frozen.get("adapters", []), name="source_adapter_frozen_registry.adapters")):
        row = _coerce_mapping(raw, name=f"source_adapter_frozen_registry.adapters[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        if adapter_id in seen:
            raise SourceAdapterRegistryRolloutError(f"duplicate adapter_id: {adapter_id}")
        seen.add(adapter_id)
        release_status = str(row.get("release_status") or "").strip().upper()
        if release_status != "RELEASED_FOR_SHARED_PIPELINE":
            continue
        rows.append(
            {
                "adapter_id": adapter_id,
                "display_name": str(row.get("display_name") or adapter_id.replace("_", " ").title()),
                "source_kind": str(row.get("source_kind") or "unknown"),
                "domains": _normalise_text_list(row.get("domains", []), name=f"adapters[{index}].domains"),
                "artifact_roles": _normalise_text_list(row.get("artifact_roles", []), name=f"adapters[{index}].artifact_roles"),
                "shared_stage_coverage": _normalise_text_list(
                    row.get("shared_stage_coverage", []), name=f"adapters[{index}].shared_stage_coverage"
                ),
                "adapter_specific_module_required": bool(row.get("adapter_specific_module_required")),
                "release_status": release_status,
            }
        )
    return sorted(rows, key=lambda item: item["adapter_id"])


def build_source_adapter_registry_rollout(registry_release_package: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic local-only adapter registry rollout package.

    The rollout stage converts a reviewed/frozen adapter registry release into
    app-source-selection wiring instructions. It is intentionally a package and
    handoff boundary only: it does not edit GUI files, mutate registry state,
    launch browsers, fetch URLs, read credentials, submit archives, or start
    manual/live actions.
    """

    source = _coerce_mapping(registry_release_package, name="registry_release_package")
    _assert_no_forbidden_keys(source, name="registry_release_package")

    release_id = str(source.get("source_adapter_registry_release_id") or "").strip()
    update_id = str(source.get("source_adapter_registry_update_id") or "").strip()
    acceptance_id = str(source.get("source_adapter_coverage_acceptance_id") or "").strip()
    release_status = str(source.get("registry_release_status") or "").strip().upper()
    rollout_handoff = _coerce_mapping(source.get("source_adapter_registry_rollout_handoff", {}), name="source_adapter_registry_rollout_handoff")
    handoff_status = str(rollout_handoff.get("handoff_status") or "").strip().upper()
    rows = _released_rows(source)

    issues: list[str] = []
    if source.get("schema_version") != REGISTRY_RELEASE_PACKAGE_SCHEMA_VERSION:
        issues.append("registry release package schema_version is not source_adapter_registry_release_package_v1")
    if not release_id.startswith("source_adapter_registry_release."):
        issues.append("source_adapter_registry_release_id is missing or invalid")
    if not update_id.startswith("source_adapter_registry_update."):
        issues.append("source_adapter_registry_update_id is missing or invalid")
    if not acceptance_id:
        issues.append("source_adapter_coverage_acceptance_id is required")
    if release_status != _READY_RELEASE_STATUS:
        issues.append(f"registry_release_status must be {_READY_RELEASE_STATUS}")
    if handoff_status != _READY_HANDOFF_STATUS:
        issues.append(f"source_adapter_registry_rollout_handoff.handoff_status must be {_READY_HANDOFF_STATUS}")
    if rollout_handoff.get("registry_mutation_applied") is not False:
        issues.append("rollout handoff must not have registry_mutation_applied")
    if rollout_handoff.get("manual_or_live_actions_started") is not False:
        issues.append("rollout handoff must not start manual or live actions")
    if not rows:
        issues.append("source_adapter_frozen_registry must contain at least one released adapter")
    for row in rows:
        if not row["shared_stage_coverage"]:
            issues.append(f"released adapter {row['adapter_id']} has no shared_stage_coverage")

    status = _READY_ROLLOUT_STATUS if not issues else "ADAPTER_REGISTRY_ROLLOUT_BLOCKED"
    base = {
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": update_id,
        "adapter_ids": [row["adapter_id"] for row in rows],
        "issue_count": len(issues),
    }
    rollout_id = f"source_adapter_registry_rollout.{_stable_hash(base)}"

    selection_options = [
        {
            "adapter_id": row["adapter_id"],
            "display_name": row["display_name"],
            "source_kind": row["source_kind"],
            "domains": row["domains"],
            "artifact_roles": row["artifact_roles"],
            "shared_stage_coverage": row["shared_stage_coverage"],
            "requires_adapter_specific_module": row["adapter_specific_module_required"],
            "selection_enabled": status == _READY_ROLLOUT_STATUS,
        }
        for row in rows
    ]
    source_selection_wiring_plan = {
        "schema_version": SELECTION_PLAN_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": rollout_id,
        "source_adapter_registry_release_id": release_id,
        "wiring_status": "READY_FOR_LOCAL_APP_SOURCE_SELECTION_WIRING" if status == _READY_ROLLOUT_STATUS else status,
        "adapter_count": len(selection_options),
        "selection_option_ids": [row["adapter_id"] for row in selection_options],
        "wiring_targets": [
            "source selection catalogue/view-model",
            "capture setup source-kind dropdown",
            "shared pipeline stage routing display",
            "fixture/readiness summary panel",
        ],
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    selection_option_index = {
        "schema_version": OPTION_INDEX_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": rollout_id,
        "adapter_count": len(selection_options),
        "options": selection_options,
        "app_files_mutated": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    rollout_validation_checklist = {
        "schema_version": VALIDATION_CHECKLIST_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": rollout_id,
        "rollout_status": status,
        "required_checks": [
            {"check_id": "release_package_verified", "required": True, "complete": status == _READY_ROLLOUT_STATUS},
            {"check_id": "frozen_registry_present", "required": True, "complete": bool(rows)},
            {"check_id": "source_selection_options_written", "required": True, "complete": bool(selection_options)},
            {"check_id": "no_app_file_mutation_in_rollout_stage", "required": True, "complete": True},
            {"check_id": "no_manual_or_live_actions_started", "required": True, "complete": True},
        ],
        "issue_count": len(issues),
        "issues": issues,
    }
    app_handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": rollout_id,
        "source_adapter_registry_release_id": release_id,
        "handoff_status": "READY_FOR_SOURCE_SELECTION_IMPLEMENTATION" if status == _READY_ROLLOUT_STATUS else status,
        "adapter_count": len(selection_options),
        "released_adapter_ids": [row["adapter_id"] for row in selection_options],
        "expected_next_stage": "source_selection_wiring",
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": rollout_id,
        "rollout_status": status,
        "adapter_count": len(selection_options),
        "issue_count": len(issues),
        "app_files_mutated": False,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Use the rollout package to wire released source adapters into app source selection.",
            "Keep wiring local and fixture-backed; do not navigate live sources from this stage.",
            "Only enable adapter-specific code paths for rows that explicitly require them.",
        ],
    }
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": rollout_id,
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "registry_release_status": release_status,
        "registry_rollout_status": status,
        "handoff_status": handoff_status,
        "adapter_count": len(selection_options),
        "issue_count": len(issues),
        "issues": issues,
        "released_adapters": rows,
        "source_adapter_source_selection_wiring_plan": source_selection_wiring_plan,
        "source_adapter_selection_option_index": selection_option_index,
        "source_adapter_registry_rollout_validation_checklist": rollout_validation_checklist,
        "source_adapter_registry_rollout_app_handoff": app_handoff,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SourceAdapterRegistryRolloutError("JSON input must be an object")
    return dict(data)


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).write_bytes(_json_bytes(data))


if __name__ == "__main__":
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
                        "display_name": "Article",
                        "source_kind": "web",
                        "domains": ["article.example"],
                        "artifact_roles": ["article_html_or_text", "metadata_json"],
                        "shared_stage_coverage": ["content_extraction", "pipeline_closeout"],
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
    assert package["registry_rollout_status"] == _READY_ROLLOUT_STATUS, package
    print("Source Adapter Registry Rollout self-test passed.")
