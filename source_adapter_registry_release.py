from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

PACKAGE_SCHEMA_VERSION = "source_adapter_registry_release_package_v1"
UPDATE_PACKAGE_SCHEMA_VERSION = "source_adapter_registry_update_package_v1"
RELEASE_RECORD_SCHEMA_VERSION = "source_adapter_registry_release_record_v1"
FROZEN_REGISTRY_SCHEMA_VERSION = "source_adapter_frozen_registry_v1"
ROLLOUT_HANDOFF_SCHEMA_VERSION = "source_adapter_registry_rollout_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_registry_release_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}
_READY_UPDATE_STATUS = "ADAPTER_REGISTRY_UPDATE_READY"
_READY_HANDOFF_STATUS = "READY_FOR_SOURCE_ADAPTER_RELEASE_REVIEW"
_READY_RELEASE_STATUS = "ADAPTER_REGISTRY_RELEASE_READY"


class SourceAdapterRegistryReleaseError(ValueError):
    """Raised when adapter registry release input is invalid."""


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
        raise SourceAdapterRegistryReleaseError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterRegistryReleaseError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterRegistryReleaseError(f"{name} must not include local path fields: {', '.join(present)}")


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


def _normalise_registry_rows(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(_coerce_sequence(value, name="registry_rows")):
        row = _coerce_mapping(raw, name=f"registry_rows[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        if adapter_id in seen:
            raise SourceAdapterRegistryReleaseError(f"duplicate adapter_id: {adapter_id}")
        seen.add(adapter_id)
        rows.append(
            {
                "adapter_id": adapter_id,
                "display_name": str(row.get("display_name") or adapter_id.replace("_", " ").title()),
                "source_kind": str(row.get("source_kind") or "unknown"),
                "domains": _normalise_text_list(row.get("domains", []), name=f"registry_rows[{index}].domains"),
                "artifact_roles": _normalise_text_list(row.get("artifact_roles", []), name=f"registry_rows[{index}].artifact_roles"),
                "shared_stage_coverage": _normalise_text_list(
                    row.get("shared_stage_coverage", []),
                    name=f"registry_rows[{index}].shared_stage_coverage",
                ),
                "registered_for_shared_pipeline": bool(row.get("registered_for_shared_pipeline")),
                "adapter_specific_module_required": bool(row.get("adapter_specific_module_required")),
                "coverage_status": str(row.get("coverage_status") or "UNKNOWN").strip().upper(),
                "registry_action": str(row.get("registry_action") or "ADD_OR_REFRESH_SHARED_ADAPTER").strip().upper(),
            }
        )
    return sorted(rows, key=lambda item: item["adapter_id"])


def build_source_adapter_registry_release(adapter_registry_update_package: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic local-only adapter registry release package.

    This is a release gate over an already accepted registry update package. It
    writes release artifacts only and deliberately does not mutate application
    registry files, launch browsers, fetch network resources, or start manual
    actions.
    """

    package = _coerce_mapping(adapter_registry_update_package, name="adapter_registry_update_package")
    _assert_no_forbidden_keys(package, name="adapter_registry_update_package")

    update_id = str(package.get("source_adapter_registry_update_id") or "").strip()
    acceptance_id = str(package.get("source_adapter_coverage_acceptance_id") or "").strip()
    registry_update_status = str(package.get("registry_update_status") or "").strip().upper()
    release_handoff = _coerce_mapping(package.get("adapter_registry_release_handoff", {}), name="adapter_registry_release_handoff")
    handoff_status = str(release_handoff.get("handoff_status") or "").strip().upper()
    rows = _normalise_registry_rows(package.get("registry_rows", []))

    issues: list[str] = []
    if package.get("schema_version") != UPDATE_PACKAGE_SCHEMA_VERSION:
        issues.append("registry update package schema_version is not source_adapter_registry_update_package_v1")
    if not update_id.startswith("source_adapter_registry_update."):
        issues.append("source_adapter_registry_update_id is missing or invalid")
    if not acceptance_id:
        issues.append("source_adapter_coverage_acceptance_id is required")
    if registry_update_status != _READY_UPDATE_STATUS:
        issues.append(f"registry_update_status must be {_READY_UPDATE_STATUS}")
    if handoff_status != _READY_HANDOFF_STATUS:
        issues.append(f"adapter_registry_release_handoff.handoff_status must be {_READY_HANDOFF_STATUS}")
    if release_handoff.get("manual_or_live_actions_started") is not False:
        issues.append("adapter registry release handoff must not start manual or live actions")
    if not rows:
        issues.append("registry_rows must contain at least one adapter row")
    for row in rows:
        if not row["registered_for_shared_pipeline"]:
            issues.append(f"adapter {row['adapter_id']} is not registered_for_shared_pipeline")
        if not row["shared_stage_coverage"]:
            issues.append(f"adapter {row['adapter_id']} has no shared_stage_coverage")

    status = _READY_RELEASE_STATUS if not issues else "ADAPTER_REGISTRY_RELEASE_BLOCKED"
    base = {
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "adapter_ids": [row["adapter_id"] for row in rows],
        "issue_count": len(issues),
    }
    release_id = f"source_adapter_registry_release.{_stable_hash(base)}"
    released_adapter_ids = [row["adapter_id"] for row in rows if row["registered_for_shared_pipeline"]]

    release_record = {
        "schema_version": RELEASE_RECORD_SCHEMA_VERSION,
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "registry_release_status": status,
        "adapter_count": len(rows),
        "released_adapter_count": len(released_adapter_ids),
        "issue_count": len(issues),
        "issues": issues,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    frozen_registry = {
        "schema_version": FROZEN_REGISTRY_SCHEMA_VERSION,
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": update_id,
        "adapter_count": len(rows),
        "adapters": [
            {
                "adapter_id": row["adapter_id"],
                "display_name": row["display_name"],
                "source_kind": row["source_kind"],
                "domains": row["domains"],
                "artifact_roles": row["artifact_roles"],
                "shared_stage_coverage": row["shared_stage_coverage"],
                "registered_for_shared_pipeline": row["registered_for_shared_pipeline"],
                "adapter_specific_module_required": row["adapter_specific_module_required"],
                "release_status": "RELEASED_FOR_SHARED_PIPELINE"
                if status == _READY_RELEASE_STATUS and row["registered_for_shared_pipeline"]
                else "NOT_RELEASED",
            }
            for row in rows
        ],
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    rollout_handoff = {
        "schema_version": ROLLOUT_HANDOFF_SCHEMA_VERSION,
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": update_id,
        "handoff_status": "READY_FOR_APP_SOURCE_SELECTION_WIRING" if status == _READY_RELEASE_STATUS else status,
        "adapter_count": len(rows),
        "released_adapter_ids": released_adapter_ids,
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_registry_release_id": release_id,
        "registry_release_status": status,
        "adapter_count": len(rows),
        "released_adapter_count": len(released_adapter_ids),
        "issue_count": len(issues),
        "registry_mutation_applied": False,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Wire the frozen registry snapshot into app source selection only after this release package is reviewed.",
            "Keep live navigation and external archive/provider work behind explicit operator approval gates.",
            "Continue adding adapter-specific modules only for released rows that explicitly require unique extraction code.",
        ],
    }
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "registry_release_status": status,
        "registry_update_status": registry_update_status,
        "handoff_status": handoff_status,
        "adapter_count": len(rows),
        "released_adapter_count": len(released_adapter_ids),
        "issue_count": len(issues),
        "issues": issues,
        "registry_rows": rows,
        "adapter_registry_release_record": release_record,
        "source_adapter_frozen_registry": frozen_registry,
        "source_adapter_registry_rollout_handoff": rollout_handoff,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SourceAdapterRegistryReleaseError("JSON input must be an object")
    return dict(data)


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).write_bytes(_json_bytes(data))


if __name__ == "__main__":
    package = build_source_adapter_registry_release(
        {
            "schema_version": UPDATE_PACKAGE_SCHEMA_VERSION,
            "source_adapter_registry_update_id": "source_adapter_registry_update.example",
            "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
            "registry_update_status": "ADAPTER_REGISTRY_UPDATE_READY",
            "registry_rows": [
                {
                    "adapter_id": "article",
                    "display_name": "Article",
                    "source_kind": "web",
                    "domains": ["article.example"],
                    "artifact_roles": ["article_html_or_text", "metadata_json"],
                    "shared_stage_coverage": ["content_extraction", "pipeline_closeout"],
                    "registered_for_shared_pipeline": True,
                }
            ],
            "adapter_registry_release_handoff": {
                "handoff_status": "READY_FOR_SOURCE_ADAPTER_RELEASE_REVIEW",
                "manual_or_live_actions_started": False,
            },
        }
    )
    assert package["registry_release_status"] == _READY_RELEASE_STATUS, package
    print("Source Adapter Registry Release self-test passed.")
