from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_adapter_runtime_ui_provider_integration_bridge_v1"
INTEGRATION_BATCH_SCHEMA_VERSION = "source_adapter_runtime_ui_provider_integration_batch_v1"
BINDING_INDEX_SCHEMA_VERSION = "source_adapter_runtime_ui_provider_binding_index_v1"
OPERATOR_ACCEPTANCE_HANDOFF_SCHEMA_VERSION = "source_adapter_runtime_operator_acceptance_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_runtime_ui_provider_integration_bridge_operator_summary_v1"
RUNTIME_UI_PROVIDER_INTEGRATION_STATUS = "SOURCE_ADAPTER_RUNTIME_UI_PROVIDER_INTEGRATIONS_BUILT"
RUNTIME_OPERATOR_ACCEPTANCE_READY_STATUS = "SOURCE_ADAPTER_RUNTIME_READY_FOR_OPERATOR_ACCEPTANCE"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_SURFACE_CATALOG: dict[str, dict[str, str]] = {
    "operator_url_fetch": {
        "ui_surface_id": "source_adapter.ui.url_fetch_load",
        "provider_surface_id": "source_adapter_runtime.operator_url_fetch",
        "binding_kind": "source_url_action",
        "operator_action_label": "Fetch or load source URL",
        "provider_integration_role": "url_fetch_or_embedded_browser_load",
    },
    "browser_launch": {
        "ui_surface_id": "source_adapter.ui.lightweight_browser_launch",
        "provider_surface_id": "lightweight_in_app_browser_capture.launch_for_adapter",
        "binding_kind": "browser_action",
        "operator_action_label": "Launch lightweight browser",
        "provider_integration_role": "browser_process_or_embedded_shell_launch",
    },
    "folder_scan": {
        "ui_surface_id": "source_adapter.ui.artifact_folder_scan",
        "provider_surface_id": "source_adapter_runtime.scan_artifact_folder",
        "binding_kind": "folder_action",
        "operator_action_label": "Scan artifact folder",
        "provider_integration_role": "operator_selected_folder_scan",
    },
    "credential_lookup": {
        "ui_surface_id": "keys_accounts.ui.credential_reference_selector",
        "provider_surface_id": "source_adapter_runtime.resolve_credential_reference",
        "binding_kind": "keys_accounts_action",
        "operator_action_label": "Resolve Keys/Accounts credential reference",
        "provider_integration_role": "keys_accounts_reference_resolution",
    },
    "archive_submit": {
        "ui_surface_id": "source_adapter.ui.archive_provider_submit",
        "provider_surface_id": "source_adapter_runtime.submit_archive_request",
        "binding_kind": "archive_provider_action",
        "operator_action_label": "Submit archive provider request",
        "provider_integration_role": "archive_provider_submit",
    },
    "release_upload": {
        "ui_surface_id": "source_adapter.ui.release_artifact_upload",
        "provider_surface_id": "source_adapter_runtime.upload_release_artifact",
        "binding_kind": "release_action",
        "operator_action_label": "Upload release artifact",
        "provider_integration_role": "release_export_or_library_upload",
    },
    "app_registry_mutation": {
        "ui_surface_id": "source_adapter.ui.adapter_registry_mutation",
        "provider_surface_id": "source_adapter_runtime.apply_registry_mutation",
        "binding_kind": "registry_action",
        "operator_action_label": "Apply app/adapter registry mutation",
        "provider_integration_role": "application_state_or_adapter_registry_update",
    },
    "file_library_publication": {
        "ui_surface_id": "source_adapter.ui.file_library_publication",
        "provider_surface_id": "source_adapter_runtime.publish_file_library_artifact",
        "binding_kind": "file_library_action",
        "operator_action_label": "Publish file-library artifact",
        "provider_integration_role": "persistent_file_library_write",
    },
}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()[:length]


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _as_mapping_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return [_as_mapping(item, f"{label} item") for item in value]


def _safe_text(value: Any, default: str = "") -> str:
    return str(value if value is not None else default).replace("\r", " ").strip()


def _safe_id(value: Any, *, label: str, fallback: str = "") -> str:
    text = _safe_text(value, fallback)
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} must contain only letters, numbers, dot, colon, underscore, or dash")
    return text


def _normalise_notes(notes: Iterable[str] | None) -> list[str]:
    return [str(note).strip() for note in (notes or []) if str(note).strip()]


def runtime_ui_provider_surface_catalog() -> dict[str, dict[str, str]]:
    """Return the shared runtime UI/provider surface catalog."""

    return {capability_id: dict(surface) for capability_id, surface in _SURFACE_CATALOG.items()}


def _accepted_review_rows(runtime_receipt_review_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    batch = _as_mapping(
        runtime_receipt_review_bridge_package.get("source_adapter_runtime_receipt_review_batch"),
        "source_adapter_runtime_receipt_review_batch",
    )
    rows = _as_mapping_list(batch.get("review_rows"), "review_rows")
    return [row for row in rows if row.get("review_decision") in {"ACCEPTED", "ACCEPTED_WITH_NOTES"}]


def _capability_filter(enabled_capabilities: Iterable[str] | None) -> set[str] | None:
    if enabled_capabilities is None:
        return None
    values = {_safe_id(item, label="enabled capability") for item in enabled_capabilities}
    unknown = sorted(values - set(_SURFACE_CATALOG))
    if unknown:
        raise ValueError(f"unknown runtime UI/provider capabilities: {unknown}")
    return values


def _group_by_capability(rows: list[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        capability_id = _safe_id(row.get("capability_id"), label="capability_id")
        grouped.setdefault(capability_id, []).append(row)
    return grouped


def _integration_row(
    capability_id: str,
    rows: list[Mapping[str, Any]],
    index: int,
    *,
    integration_profile: str,
    operator_id: str,
) -> dict[str, Any]:
    surface = _SURFACE_CATALOG.get(capability_id)
    if not surface:
        raise ValueError(f"missing UI/provider surface for capability: {capability_id}")
    runtime_action_ids = sorted({_safe_text(row.get("runtime_action_id"), "") for row in rows if row.get("runtime_action_id")})
    runtime_receipt_ids = sorted(
        {_safe_text(row.get("runtime_action_receipt_id"), "") for row in rows if row.get("runtime_action_receipt_id")}
    )
    adapter_ids = sorted({_safe_text(row.get("adapter_id"), "") for row in rows if row.get("adapter_id")})
    source_pipeline_closeout_ids = sorted(
        {_safe_text(row.get("source_pipeline_closeout_id"), "") for row in rows if row.get("source_pipeline_closeout_id")}
    )
    unsigned = {
        "schema_version": "source_adapter_runtime_ui_provider_integration_row_v1",
        "capability_id": capability_id,
        "ui_surface_id": surface["ui_surface_id"],
        "provider_surface_id": surface["provider_surface_id"],
        "binding_kind": surface["binding_kind"],
        "operator_action_label": surface["operator_action_label"],
        "provider_integration_role": surface["provider_integration_role"],
        "runtime_action_ids": runtime_action_ids,
        "runtime_action_receipt_ids": runtime_receipt_ids,
        "adapter_ids": adapter_ids,
        "source_pipeline_closeout_ids": source_pipeline_closeout_ids,
        "integration_profile": integration_profile,
        "operator_id": operator_id,
        "integration_status": "BOUND_TO_SHARED_UI_PROVIDER_SURFACE",
        "approval_status": "APPROVED_RUNTIME_RECEIPTS_REQUIRED",
        "row_index": index,
    }
    return dict(unsigned, runtime_ui_provider_integration_row_id=f"source_adapter.runtime_ui_provider_integration_row.{_stable_hash(unsigned)}")


def build_source_adapter_runtime_ui_provider_integration_bridge(
    runtime_receipt_review_bridge_package: Mapping[str, Any],
    *,
    enabled_capabilities: Iterable[str] | None = None,
    integration_profile: str = "source_adapter_runtime_ui_provider_integration_v1",
    operator_id: str = "operator",
    integration_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build UI/provider bindings from accepted runtime receipt review output."""

    package = _as_mapping(runtime_receipt_review_bridge_package, "runtime_receipt_review_bridge_package")
    if package.get("runtime_receipt_review_status") != "SOURCE_ADAPTER_RUNTIME_RECEIPTS_REVIEWED":
        raise ValueError("runtime receipt review package must be SOURCE_ADAPTER_RUNTIME_RECEIPTS_REVIEWED")
    handoff = _as_mapping(package.get("source_adapter_runtime_acceptance_handoff"), "source_adapter_runtime_acceptance_handoff")
    if handoff.get("required_next_stage") != "source_adapter_runtime_ui_provider_integration":
        raise ValueError("runtime acceptance handoff must request source_adapter_runtime_ui_provider_integration")
    if handoff.get("handoff_status") != "SOURCE_ADAPTER_RUNTIME_READY_FOR_UI_OR_PROVIDER_INTEGRATION":
        raise ValueError("runtime acceptance handoff must be ready for UI/provider integration")

    integration_profile = _safe_id(integration_profile, label="integration_profile")
    operator_id = _safe_id(operator_id, label="operator_id")
    notes = _normalise_notes(integration_notes)
    wanted = _capability_filter(enabled_capabilities)
    accepted_rows = _accepted_review_rows(package)
    if wanted is not None:
        accepted_rows = [row for row in accepted_rows if row.get("capability_id") in wanted]

    issues: list[str] = []
    grouped = _group_by_capability(accepted_rows)
    if not grouped:
        issues.append("accepted runtime receipt review rows are required for UI/provider integration")

    integration_rows: list[dict[str, Any]] = []
    for index, capability_id in enumerate(sorted(grouped)):
        try:
            integration_rows.append(
                _integration_row(
                    capability_id,
                    grouped[capability_id],
                    index,
                    integration_profile=integration_profile,
                    operator_id=operator_id,
                )
            )
        except Exception as exc:
            issues.append(f"{capability_id}: {exc}")

    accepted_capability_ids = sorted(grouped)
    integrated_capability_ids = sorted(row["capability_id"] for row in integration_rows)
    missing_integrations = sorted(set(accepted_capability_ids) - set(integrated_capability_ids))
    if missing_integrations:
        issues.append(f"missing UI/provider integration rows: {missing_integrations}")
    runtime_integration_status = RUNTIME_UI_PROVIDER_INTEGRATION_STATUS if not issues else "SOURCE_ADAPTER_RUNTIME_UI_PROVIDER_INTEGRATION_HAS_ISSUES"
    handoff_status = RUNTIME_OPERATOR_ACCEPTANCE_READY_STATUS if not issues else "SOURCE_ADAPTER_RUNTIME_OPERATOR_ACCEPTANCE_REVIEW_REQUIRED"
    bridge_input_id = _safe_text(package.get("source_adapter_runtime_receipt_review_bridge_id"), "")

    integration_batch = {
        "schema_version": INTEGRATION_BATCH_SCHEMA_VERSION,
        "integration_profile": integration_profile,
        "accepted_capability_count": len(accepted_capability_ids),
        "integrated_capability_count": len(integration_rows),
        "runtime_ui_provider_integration_rows": integration_rows,
    }
    binding_index = {
        "schema_version": BINDING_INDEX_SCHEMA_VERSION,
        "binding_status": handoff_status,
        "integrated_capability_ids": integrated_capability_ids,
        "ui_surface_ids": [row["ui_surface_id"] for row in integration_rows],
        "provider_surface_ids": [row["provider_surface_id"] for row in integration_rows],
        "runtime_action_ids": sorted({item for row in integration_rows for item in row["runtime_action_ids"]}),
        "runtime_action_receipt_ids": sorted({item for row in integration_rows for item in row["runtime_action_receipt_ids"]}),
    }
    operator_acceptance_handoff = {
        "schema_version": OPERATOR_ACCEPTANCE_HANDOFF_SCHEMA_VERSION,
        "handoff_status": handoff_status,
        "ready_for_operator_acceptance": not issues,
        "required_next_stage": "source_adapter_runtime_operator_acceptance",
        "source_adapter_runtime_receipt_review_bridge_id": bridge_input_id,
        "integrated_capability_ids": integrated_capability_ids,
        "operator_acceptance_inputs": [
            "runtime_action_ids",
            "runtime_action_receipt_ids",
            "ui_surface_ids",
            "provider_surface_ids",
            "operator_action_labels",
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": runtime_integration_status,
        "operator_id": operator_id,
        "integration_profile": integration_profile,
        "accepted_capability_count": len(accepted_capability_ids),
        "integrated_capability_count": len(integration_rows),
        "issue_count": len(issues),
        "integration_notes": notes,
        "next_actions": [
            "Surface the integrated runtime actions in shared UI and CLI entry points.",
            "Carry provider surface IDs and receipt IDs into operator acceptance evidence.",
            "Use the same integration batch for URL, browser, folder, Keys/Accounts, archive, release, registry, and file-library actions.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "runtime_ui_provider_integration_status": runtime_integration_status,
        "source_adapter_runtime_receipt_review_bridge_id": bridge_input_id,
        "accepted_capability_count": len(accepted_capability_ids),
        "integrated_capability_count": len(integration_rows),
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_ui_provider_integration_batch": integration_batch,
        "source_adapter_runtime_ui_provider_binding_index": binding_index,
        "source_adapter_runtime_operator_acceptance_handoff": operator_acceptance_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_adapter_runtime_ui_provider_integration",
            "input_stage": "source_adapter_runtime_receipt_review_bridge",
            "ui_provider_surfaces_bound": True,
            "operator_acceptance_handoff_built": True,
            "batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_runtime_ui_provider_integration_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned, source_adapter_runtime_ui_provider_integration_bridge_id=bridge_id)
    result["source_adapter_runtime_ui_provider_integration_batch"] = dict(
        integration_batch,
        source_adapter_runtime_ui_provider_integration_bridge_id=bridge_id,
    )
    result["source_adapter_runtime_ui_provider_binding_index"] = dict(
        binding_index,
        source_adapter_runtime_ui_provider_integration_bridge_id=bridge_id,
    )
    result["source_adapter_runtime_operator_acceptance_handoff"] = dict(
        operator_acceptance_handoff,
        source_adapter_runtime_ui_provider_integration_bridge_id=bridge_id,
    )
    result["operator_summary"] = dict(operator_summary, source_adapter_runtime_ui_provider_integration_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_runtime_ui_provider_integration_bridge_package": dict(pkg),
        "source_adapter_runtime_ui_provider_integration_batch": deepcopy(pkg.get("source_adapter_runtime_ui_provider_integration_batch", {})),
        "source_adapter_runtime_ui_provider_binding_index": deepcopy(pkg.get("source_adapter_runtime_ui_provider_binding_index", {})),
        "source_adapter_runtime_operator_acceptance_handoff": deepcopy(pkg.get("source_adapter_runtime_operator_acceptance_handoff", {})),
        "source_adapter_runtime_ui_provider_integration_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    from source_adapter_runtime_receipt_review_bridge_test import fixture_runtime_wiring_bridge
    from source_adapter_runtime_receipt_review_bridge import build_source_adapter_runtime_receipt_review_bridge

    review = build_source_adapter_runtime_receipt_review_bridge(fixture_runtime_wiring_bridge())
    package = build_source_adapter_runtime_ui_provider_integration_bridge(review, integration_notes=["manual self-test fixture"])
    print(json.dumps(package, indent=2, sort_keys=True, ensure_ascii=False))
