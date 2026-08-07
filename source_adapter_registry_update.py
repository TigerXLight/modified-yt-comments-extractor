from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_registry_update_v1"
PACKAGE_SCHEMA_VERSION = "source_adapter_registry_update_package_v1"
RECORD_SCHEMA_VERSION = "source_adapter_registry_update_record_v1"
READINESS_INDEX_SCHEMA_VERSION = "source_adapter_readiness_index_v1"
RELEASE_HANDOFF_SCHEMA_VERSION = "source_adapter_registry_release_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_registry_update_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}
_READY_HANDOFF_STATUS = "READY_FOR_ADAPTER_REGISTRY_UPDATE"


class SourceAdapterRegistryUpdateError(ValueError):
    """Raised when adapter registry update input is invalid."""


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
        raise SourceAdapterRegistryUpdateError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterRegistryUpdateError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterRegistryUpdateError(f"{name} must not include local path fields: {', '.join(present)}")


def _assert_no_forbidden_keys(value: object, *, name: str) -> None:
    if isinstance(value, Mapping):
        _ensure_no_local_paths(value, name=name)
        for key, child in value.items():
            _assert_no_forbidden_keys(child, name=f"{name}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, name=f"{name}[{index}]")


def _normalise_stage_list(value: object, *, name: str) -> list[str]:
    stages: list[str] = []
    for index, raw_stage in enumerate(_coerce_sequence(value or [], name=name)):
        stage = _clean_identifier(raw_stage, fallback=f"stage_{index + 1}").lower()
        if stage not in stages:
            stages.append(stage)
    return stages


def _existing_registry_rows(existing_registry: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if existing_registry is None:
        return {}
    registry = _coerce_mapping(existing_registry, name="existing_registry")
    _assert_no_forbidden_keys(registry, name="existing_registry")
    rows: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_coerce_sequence(registry.get("adapters", []), name="existing_registry.adapters")):
        row = _coerce_mapping(raw, name=f"existing_registry.adapters[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        rows[adapter_id] = {
            "adapter_id": adapter_id,
            "display_name": str(row.get("display_name") or adapter_id.replace("_", " ").title()),
            "source_kind": str(row.get("source_kind") or "unknown"),
            "domains": sorted({str(domain).strip() for domain in row.get("domains", []) if str(domain).strip()}),
            "artifact_roles": sorted({str(role).strip() for role in row.get("artifact_roles", []) if str(role).strip()}),
            "shared_stage_coverage": _normalise_stage_list(row.get("shared_stage_coverage", []), name=f"existing_registry.adapters[{index}].shared_stage_coverage"),
            "registered_for_shared_pipeline": bool(row.get("registered_for_shared_pipeline")),
            "adapter_specific_module_required": bool(row.get("adapter_specific_module_required")),
            "coverage_status": str(row.get("coverage_status") or "EXISTING"),
        }
    return rows


def _handoff_rows(adapter_registry_handoff: Mapping[str, Any]) -> tuple[str, str, list[dict[str, Any]]]:
    handoff = _coerce_mapping(adapter_registry_handoff, name="adapter_registry_handoff")
    _assert_no_forbidden_keys(handoff, name="adapter_registry_handoff")
    acceptance_id = str(handoff.get("source_adapter_coverage_acceptance_id") or "").strip()
    if not acceptance_id:
        raise SourceAdapterRegistryUpdateError("source_adapter_coverage_acceptance_id is required")
    handoff_status = str(handoff.get("handoff_status") or "").strip().upper()
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_coerce_sequence(handoff.get("adapters", []), name="adapter_registry_handoff.adapters")):
        row = _coerce_mapping(raw, name=f"adapter_registry_handoff.adapters[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        rows.append(
            {
                "adapter_id": adapter_id,
                "coverage_status": str(row.get("coverage_status") or "").strip().upper(),
                "shared_stage_coverage": _normalise_stage_list(
                    row.get("shared_stage_coverage", []),
                    name=f"adapter_registry_handoff.adapters[{index}].shared_stage_coverage",
                ),
                "accepted_for_shared_pipeline": bool(row.get("accepted_for_shared_pipeline")),
                "display_name": str(row.get("display_name") or adapter_id.replace("_", " ").title()),
                "source_kind": str(row.get("source_kind") or "unknown"),
                "domains": sorted({str(domain).strip() for domain in row.get("domains", []) if str(domain).strip()}),
                "artifact_roles": sorted({str(role).strip() for role in row.get("artifact_roles", []) if str(role).strip()}),
                "adapter_specific_module_required": bool(row.get("adapter_specific_module_required")),
            }
        )
    return acceptance_id, handoff_status, rows


def build_source_adapter_registry_update(
    adapter_registry_handoff: Mapping[str, Any],
    existing_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic local-only adapter registry update package.

    This returns the registry update artifacts only. It does not mutate the
    application registry, fetch URLs, launch browsers, or start fixture work.
    """

    acceptance_id, handoff_status, handoff_rows = _handoff_rows(adapter_registry_handoff)
    registry_rows = _existing_registry_rows(existing_registry)
    issues: list[str] = []
    if handoff_status != _READY_HANDOFF_STATUS:
        issues.append(f"handoff_status must be {_READY_HANDOFF_STATUS}")
    if not handoff_rows:
        issues.append("adapter registry handoff does not contain adapters")

    update_rows: list[dict[str, Any]] = []
    for row in handoff_rows:
        adapter_id = row["adapter_id"]
        existing = registry_rows.get(adapter_id, {})
        if not row["accepted_for_shared_pipeline"]:
            issues.append(f"adapter {adapter_id} is not accepted for shared pipeline registration")
        if not row["shared_stage_coverage"]:
            issues.append(f"adapter {adapter_id} has no accepted shared stage coverage")
        merged_stage_coverage = sorted(set(existing.get("shared_stage_coverage", [])) | set(row["shared_stage_coverage"]))
        update_rows.append(
            {
                "adapter_id": adapter_id,
                "display_name": row["display_name"] or existing.get("display_name") or adapter_id.replace("_", " ").title(),
                "source_kind": row["source_kind"] if row["source_kind"] != "unknown" else existing.get("source_kind", "unknown"),
                "domains": sorted(set(existing.get("domains", [])) | set(row["domains"])),
                "artifact_roles": sorted(set(existing.get("artifact_roles", [])) | set(row["artifact_roles"])),
                "coverage_status": row["coverage_status"] or existing.get("coverage_status", "ACCEPTED_SHARED_FIXTURE_COVERAGE"),
                "shared_stage_coverage": merged_stage_coverage,
                "registered_for_shared_pipeline": bool(row["accepted_for_shared_pipeline"]),
                "adapter_specific_module_required": bool(
                    row["adapter_specific_module_required"] or existing.get("adapter_specific_module_required", False)
                ),
                "registry_action": "ADD_OR_REFRESH_SHARED_ADAPTER",
            }
        )

    status = "ADAPTER_REGISTRY_UPDATE_READY" if not issues else "ADAPTER_REGISTRY_UPDATE_BLOCKED"
    base = {
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "handoff_status": handoff_status,
        "adapter_ids": [row["adapter_id"] for row in update_rows],
        "adapter_count": len(update_rows),
        "issue_count": len(issues),
    }
    update_id = f"source_adapter_registry_update.{_stable_hash(base)}"
    registry_record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "registry_update_status": status,
        "handoff_status": handoff_status,
        "adapter_count": len(update_rows),
        "accepted_adapter_count": sum(1 for row in update_rows if row["registered_for_shared_pipeline"]),
        "issue_count": len(issues),
        "issues": issues,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    readiness_index = {
        "schema_version": READINESS_INDEX_SCHEMA_VERSION,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "registry_update_status": status,
        "adapter_count": len(update_rows),
        "adapters": [
            {
                "adapter_id": row["adapter_id"],
                "coverage_status": row["coverage_status"],
                "registered_for_shared_pipeline": row["registered_for_shared_pipeline"],
                "shared_stage_count": len(row["shared_stage_coverage"]),
                "adapter_specific_module_required": row["adapter_specific_module_required"],
                "operator_only": True,
                "live_network_default": False,
            }
            for row in update_rows
        ],
    }
    release_handoff = {
        "schema_version": RELEASE_HANDOFF_SCHEMA_VERSION,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "handoff_status": "READY_FOR_SOURCE_ADAPTER_RELEASE_REVIEW" if status == "ADAPTER_REGISTRY_UPDATE_READY" else status,
        "adapter_count": len(update_rows),
        "registered_adapter_ids": [row["adapter_id"] for row in update_rows if row["registered_for_shared_pipeline"]],
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_registry_update_id": update_id,
        "registry_update_status": status,
        "adapter_count": len(update_rows),
        "issue_count": len(issues),
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Review the local adapter registry update package before wiring it into app-facing source selection.",
            "Keep accepted shared-stage adapters registered as specs unless a row explicitly requires adapter code.",
            "Continue to block any adapter whose coverage acceptance handoff is not ready.",
        ],
    }
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "registry_update_status": status,
        "handoff_status": handoff_status,
        "adapter_count": len(update_rows),
        "accepted_adapter_count": registry_record["accepted_adapter_count"],
        "issue_count": len(issues),
        "issues": issues,
        "registry_rows": update_rows,
        "adapter_registry_record": registry_record,
        "adapter_readiness_index": readiness_index,
        "adapter_registry_release_handoff": release_handoff,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SourceAdapterRegistryUpdateError("JSON input must be an object")
    return dict(data)


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).write_bytes(_json_bytes(data))


if __name__ == "__main__":
    handoff = {
        "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
        "handoff_status": "READY_FOR_ADAPTER_REGISTRY_UPDATE",
        "adapters": [
            {
                "adapter_id": "article",
                "coverage_status": "ACCEPTED_SHARED_FIXTURE_COVERAGE",
                "shared_stage_coverage": ["content_extraction", "pipeline_closeout"],
                "accepted_for_shared_pipeline": True,
            }
        ],
    }
    result = build_source_adapter_registry_update(handoff)
    assert result["registry_update_status"] == "ADAPTER_REGISTRY_UPDATE_READY", result
    print("Source Adapter Registry Update self-test passed.")
