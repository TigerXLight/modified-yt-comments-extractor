from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_adapter_runtime_operator_acceptance_closeout_v1"
ACCEPTANCE_BATCH_SCHEMA_VERSION = "source_adapter_runtime_operator_acceptance_batch_v1"
EXECUTION_CONTRACTS_SCHEMA_VERSION = "source_adapter_runtime_execution_contracts_v1"
PROVIDER_ADAPTER_INDEX_SCHEMA_VERSION = "source_adapter_provider_execution_adapter_index_v1"
GUI_CONTROLLER_BINDING_SCHEMA_VERSION = "source_adapter_gui_controller_binding_manifest_v1"
RECEIPT_TEMPLATE_INDEX_SCHEMA_VERSION = "source_adapter_runtime_receipt_template_index_v1"
PRIORITY_FIXTURE_PACK_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_plan_v1"
MANUAL_SMOKE_PLAN_SCHEMA_VERSION = "source_adapter_manual_live_smoke_acceptance_plan_v1"
ROADMAP_CLOSEOUT_SCHEMA_VERSION = "source_adapter_runtime_roadmap_closeout_index_v1"
FINAL_HANDOFF_SCHEMA_VERSION = "source_adapter_runtime_final_closeout_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_runtime_operator_acceptance_closeout_operator_summary_v1"

RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT_STATUS = "SOURCE_ADAPTER_RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT_BUILT"
RUNTIME_READY_FOR_CONTROLLER_AND_SMOKE_STATUS = "SOURCE_ADAPTER_RUNTIME_READY_FOR_CONTROLLER_INSTALL_AND_MANUAL_LIVE_SMOKE"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")

_CAPABILITY_EXECUTION_SPEC: dict[str, dict[str, Any]] = {
    "operator_url_fetch": {
        "controller_route_id": "source_adapter.controller.runtime.url_fetch_load",
        "controller_action": "runtime_url_fetch_or_load",
        "provider_execution_adapter_id": "source_adapter.provider.url_fetch_load",
        "provider_action": "fetch_or_load_operator_supplied_url",
        "side_effect_channel": "network_or_embedded_browser",
        "payload_fields": ["source_url", "adapter_id", "render_wait_ms", "capture_profile"],
        "receipt_fields": ["source_url", "loaded_url", "http_status_or_browser_status", "content_digest", "artifact_refs"],
        "fixture_profile": "saved_article_html_or_text",
        "manual_smoke_goal": "Load an explicit operator supplied source URL and capture visible render artifacts.",
    },
    "browser_launch": {
        "controller_route_id": "source_adapter.controller.runtime.lightweight_browser_launch",
        "controller_action": "runtime_launch_lightweight_browser",
        "provider_execution_adapter_id": "source_adapter.provider.lightweight_browser_launch",
        "provider_action": "launch_embedded_or_configured_browser_shell",
        "side_effect_channel": "browser_process_or_embedded_shell",
        "payload_fields": ["adapter_id", "source_url", "browser_profile", "viewport_profile"],
        "receipt_fields": ["browser_session_id", "adapter_id", "source_url", "launch_status", "artifact_refs"],
        "fixture_profile": "expected_lightweight_browser_capture_json",
        "manual_smoke_goal": "Open the lightweight browser route for an adapter and record the launched browser session receipt.",
    },
    "folder_scan": {
        "controller_route_id": "source_adapter.controller.runtime.artifact_folder_scan",
        "controller_action": "runtime_scan_operator_artifact_folder",
        "provider_execution_adapter_id": "source_adapter.provider.artifact_folder_scan",
        "provider_action": "scan_operator_selected_artifact_folder",
        "side_effect_channel": "filesystem_read",
        "payload_fields": ["folder_path", "adapter_id", "artifact_role_filter", "hash_files"],
        "receipt_fields": ["folder_path", "file_count", "artifact_roles", "sha256_index", "collection_id"],
        "fixture_profile": "saved_artifact_folder_manifest_json",
        "manual_smoke_goal": "Scan an operator-selected artifact folder and emit a hash-indexed artifact manifest.",
    },
    "credential_lookup": {
        "controller_route_id": "keys_accounts.controller.runtime.credential_lookup",
        "controller_action": "runtime_resolve_keys_accounts_reference",
        "provider_execution_adapter_id": "keys_accounts.provider.credential_reference_lookup",
        "provider_action": "resolve_credential_reference_metadata",
        "side_effect_channel": "keys_accounts_reference_store",
        "payload_fields": ["credential_reference_id", "provider_id", "adapter_id", "purpose"],
        "receipt_fields": ["credential_reference_id", "provider_id", "lookup_status", "redacted_reference_hash"],
        "fixture_profile": "keys_accounts_redacted_reference_json",
        "manual_smoke_goal": "Resolve a KEYS/ACCOUNTS credential reference without exposing secret material in receipts.",
    },
    "archive_submit": {
        "controller_route_id": "source_adapter.controller.runtime.archive_provider_submit",
        "controller_action": "runtime_submit_archive_provider_request",
        "provider_execution_adapter_id": "source_adapter.provider.archive_submit",
        "provider_action": "submit_archive_provider_job",
        "side_effect_channel": "archive_provider_network",
        "payload_fields": ["archive_provider_id", "source_url", "artifact_refs", "submit_profile"],
        "receipt_fields": ["archive_provider_id", "archive_job_id", "archive_url", "submission_status", "submitted_artifacts"],
        "fixture_profile": "archive_provider_receipt_json",
        "manual_smoke_goal": "Submit an approved archive provider request and record provider receipt metadata.",
    },
    "release_upload": {
        "controller_route_id": "source_adapter.controller.runtime.release_artifact_upload",
        "controller_action": "runtime_upload_release_artifact",
        "provider_execution_adapter_id": "source_adapter.provider.release_upload",
        "provider_action": "upload_approved_release_artifact",
        "side_effect_channel": "release_export_or_file_store",
        "payload_fields": ["release_artifact_path", "release_index_id", "destination_profile", "sha256"],
        "receipt_fields": ["release_upload_id", "destination_uri", "sha256", "upload_status", "release_index_id"],
        "fixture_profile": "release_upload_receipt_json",
        "manual_smoke_goal": "Upload an approved release artifact and bind the upload receipt to the release index.",
    },
    "app_registry_mutation": {
        "controller_route_id": "source_adapter.controller.runtime.adapter_registry_mutation",
        "controller_action": "runtime_apply_adapter_registry_mutation",
        "provider_execution_adapter_id": "source_adapter.provider.app_registry_mutation",
        "provider_action": "apply_adapter_registry_or_app_state_mutation",
        "side_effect_channel": "application_state_or_registry_write",
        "payload_fields": ["mutation_id", "registry_patch", "operator_reason", "adapter_id"],
        "receipt_fields": ["mutation_id", "registry_revision", "mutation_status", "changed_adapter_ids"],
        "fixture_profile": "adapter_registry_mutation_receipt_json",
        "manual_smoke_goal": "Apply an approved adapter/app registry mutation and record the revision receipt.",
    },
    "file_library_publication": {
        "controller_route_id": "source_adapter.controller.runtime.file_library_publication",
        "controller_action": "runtime_publish_file_library_artifact",
        "provider_execution_adapter_id": "source_adapter.provider.file_library_publication",
        "provider_action": "publish_artifact_to_file_library",
        "side_effect_channel": "persistent_file_library_write",
        "payload_fields": ["artifact_path", "library_destination_path", "sha256", "publication_profile"],
        "receipt_fields": ["library_file_id", "library_path", "sha256", "publication_status"],
        "fixture_profile": "file_library_publication_receipt_json",
        "manual_smoke_goal": "Publish a selected artifact to the file library and record persistent library metadata.",
    },
}

_PRIORITY_ADAPTERS: list[dict[str, Any]] = [
    {
        "adapter_id": "article",
        "display_name": "Article / news page",
        "source_kind": "web_article",
        "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot", "archive_receipt_json"],
        "fixture_types": [
            "saved_article_html_or_text",
            "expected_content_extraction_json",
            "expected_total_export_package_json",
            "expected_archive_receipt_json",
        ],
    },
    {
        "adapter_id": "social_post",
        "display_name": "Social post / thread",
        "source_kind": "social_media",
        "artifact_roles": ["post_html_or_text", "thread_json_or_text", "screenshot", "metadata_json", "archive_receipt_json"],
        "fixture_types": [
            "saved_post_html_or_text",
            "saved_thread_json_or_text",
            "expected_comment_extraction_json",
            "expected_release_archive_json",
        ],
    },
    {
        "adapter_id": "comments_thread",
        "display_name": "Comments / replies thread",
        "source_kind": "comments",
        "artifact_roles": ["comments_json_or_text", "dom_snapshot", "screenshot", "metadata_json"],
        "fixture_types": ["saved_comments_json_or_text", "expected_comments_extraction_json", "expected_capture_bundle_json"],
    },
    {
        "adapter_id": "media_transcript",
        "display_name": "Media transcript / ASR source",
        "source_kind": "media_or_transcript",
        "artifact_roles": ["media_metadata_json", "transcript_text_or_json", "screenshot", "source_url_metadata"],
        "fixture_types": ["saved_transcript_text_or_json", "expected_total_export_package_json", "expected_evidence_queue_json"],
    },
    {
        "adapter_id": "archive_receipt",
        "display_name": "Archive provider receipt",
        "source_kind": "archive_provider",
        "artifact_roles": ["archive_receipt_json", "archived_url_metadata", "provider_status_json"],
        "fixture_types": ["archive_provider_receipt_json", "expected_archive_result_intake_json", "expected_archive_review_json"],
    },
]


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


def runtime_operator_execution_capability_catalog() -> dict[str, dict[str, Any]]:
    """Return the runtime acceptance/execution capability catalog."""

    return deepcopy(_CAPABILITY_EXECUTION_SPEC)


def priority_adapter_fixture_catalog() -> list[dict[str, Any]]:
    """Return priority source-adapter fixture pack rows."""

    return deepcopy(_PRIORITY_ADAPTERS)


def _integration_rows(ui_provider_integration_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    batch = _as_mapping(
        ui_provider_integration_bridge_package.get("source_adapter_runtime_ui_provider_integration_batch"),
        "source_adapter_runtime_ui_provider_integration_batch",
    )
    return _as_mapping_list(batch.get("runtime_ui_provider_integration_rows"), "runtime_ui_provider_integration_rows")


def _capability_filter(enabled_capabilities: Iterable[str] | None) -> set[str] | None:
    if enabled_capabilities is None:
        return None
    values = {_safe_id(item, label="enabled capability") for item in enabled_capabilities}
    unknown = sorted(values - set(_CAPABILITY_EXECUTION_SPEC))
    if unknown:
        raise ValueError(f"unknown runtime operator acceptance capabilities: {unknown}")
    return values


def _acceptance_row(
    integration_row: Mapping[str, Any],
    index: int,
    *,
    operator_id: str,
    acceptance_profile: str,
    acceptance_decision: str,
) -> dict[str, Any]:
    capability_id = _safe_id(integration_row.get("capability_id"), label="capability_id")
    spec = _CAPABILITY_EXECUTION_SPEC.get(capability_id)
    if not spec:
        raise ValueError(f"missing runtime execution spec for capability: {capability_id}")
    runtime_action_ids = [str(item) for item in integration_row.get("runtime_action_ids") or []]
    runtime_receipt_ids = [str(item) for item in integration_row.get("runtime_action_receipt_ids") or []]
    unsigned = {
        "schema_version": "source_adapter_runtime_operator_acceptance_row_v1",
        "capability_id": capability_id,
        "ui_surface_id": _safe_text(integration_row.get("ui_surface_id")),
        "provider_surface_id": _safe_text(integration_row.get("provider_surface_id")),
        "controller_route_id": spec["controller_route_id"],
        "controller_action": spec["controller_action"],
        "provider_execution_adapter_id": spec["provider_execution_adapter_id"],
        "provider_action": spec["provider_action"],
        "runtime_action_ids": runtime_action_ids,
        "runtime_action_receipt_ids": runtime_receipt_ids,
        "operator_id": operator_id,
        "acceptance_profile": acceptance_profile,
        "acceptance_decision": acceptance_decision,
        "approval_gate_status": "OPERATOR_APPROVAL_RECORDED",
        "execution_authorization_status": "READY_FOR_OPERATOR_APPROVED_EXECUTION",
        "execution_modes": ["dry_run", "operator_approved_live"],
        "receipt_policy": "one_action_one_receipt_with_redacted_sensitive_fields",
        "row_index": index,
    }
    return dict(unsigned, operator_approval_id=f"source_adapter.operator_approval.{_stable_hash(unsigned)}")


def _execution_contract(acceptance: Mapping[str, Any], index: int) -> dict[str, Any]:
    capability_id = _safe_id(acceptance.get("capability_id"), label="capability_id")
    spec = _CAPABILITY_EXECUTION_SPEC[capability_id]
    unsigned = {
        "schema_version": "source_adapter_runtime_execution_contract_v1",
        "capability_id": capability_id,
        "operator_approval_id": acceptance.get("operator_approval_id"),
        "controller_route_id": spec["controller_route_id"],
        "provider_execution_adapter_id": spec["provider_execution_adapter_id"],
        "provider_action": spec["provider_action"],
        "payload_fields": list(spec["payload_fields"]),
        "receipt_fields": list(spec["receipt_fields"]),
        "side_effect_channel": spec["side_effect_channel"],
        "execution_modes": ["dry_run", "operator_approved_live"],
        "local_test_mode": "deterministic_receipt_fixture",
        "operator_approval_required": True,
        "redaction_policy": "hash_sensitive_or_secret_values_before_receipt_storage",
        "receipt_schema_version": "source_adapter_runtime_action_execution_receipt_v1",
        "contract_index": index,
    }
    return dict(unsigned, runtime_execution_contract_id=f"source_adapter.runtime_execution_contract.{_stable_hash(unsigned)}")


def _provider_adapter(acceptance: Mapping[str, Any], contract: Mapping[str, Any], index: int) -> dict[str, Any]:
    capability_id = _safe_id(acceptance.get("capability_id"), label="capability_id")
    spec = _CAPABILITY_EXECUTION_SPEC[capability_id]
    unsigned = {
        "schema_version": "source_adapter_provider_execution_adapter_v1",
        "capability_id": capability_id,
        "provider_execution_adapter_id": spec["provider_execution_adapter_id"],
        "provider_surface_id": acceptance.get("provider_surface_id"),
        "provider_action": spec["provider_action"],
        "runtime_execution_contract_id": contract.get("runtime_execution_contract_id"),
        "side_effect_channel": spec["side_effect_channel"],
        "supported_execution_modes": ["dry_run", "operator_approved_live"],
        "receipt_required": True,
        "adapter_status": "READY_FOR_CONTROLLER_BINDING_AND_OPERATOR_APPROVED_EXECUTION",
        "adapter_index": index,
    }
    return dict(unsigned, provider_execution_adapter_record_id=f"source_adapter.provider_execution_adapter.{_stable_hash(unsigned)}")


def _gui_route(acceptance: Mapping[str, Any], contract: Mapping[str, Any], index: int) -> dict[str, Any]:
    capability_id = _safe_id(acceptance.get("capability_id"), label="capability_id")
    spec = _CAPABILITY_EXECUTION_SPEC[capability_id]
    ui_label = "KEYS/ACCOUNTS credential lookup" if capability_id == "credential_lookup" else capability_id.replace("_", " ").title()
    unsigned = {
        "schema_version": "source_adapter_gui_controller_route_v1",
        "capability_id": capability_id,
        "ui_surface_id": acceptance.get("ui_surface_id"),
        "controller_route_id": spec["controller_route_id"],
        "controller_action": spec["controller_action"],
        "provider_execution_adapter_id": spec["provider_execution_adapter_id"],
        "runtime_execution_contract_id": contract.get("runtime_execution_contract_id"),
        "display_label": ui_label,
        "keys_accounts_surface": capability_id == "credential_lookup",
        "confirmation_required": True,
        "receipt_panel_required": True,
        "route_status": "READY_FOR_SHARED_CONTROLLER_INSTALL",
        "route_index": index,
    }
    return dict(unsigned, gui_controller_route_id=f"source_adapter.gui_controller_route.{_stable_hash(unsigned)}")


def _receipt_template(acceptance: Mapping[str, Any], contract: Mapping[str, Any], index: int) -> dict[str, Any]:
    capability_id = _safe_id(acceptance.get("capability_id"), label="capability_id")
    spec = _CAPABILITY_EXECUTION_SPEC[capability_id]
    unsigned = {
        "schema_version": "source_adapter_runtime_receipt_template_v1",
        "capability_id": capability_id,
        "runtime_execution_contract_id": contract.get("runtime_execution_contract_id"),
        "operator_approval_id": acceptance.get("operator_approval_id"),
        "required_receipt_fields": list(spec["receipt_fields"]),
        "redacted_fields": ["credential_secret", "api_key", "token", "password"],
        "status_values": ["DRY_RUN_RECEIPT_RECORDED", "OPERATOR_APPROVED_RECEIPT_RECORDED", "PROVIDER_ERROR_RECEIPT_RECORDED"],
        "hash_policy": "sha256_for_artifacts_and_redacted_secret_references",
        "template_index": index,
    }
    return dict(unsigned, runtime_receipt_template_id=f"source_adapter.runtime_receipt_template.{_stable_hash(unsigned)}")


def _fixture_pack(adapter: Mapping[str, Any], runtime_contracts: list[Mapping[str, Any]], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_priority_fixture_pack_v1",
        "adapter_id": adapter["adapter_id"],
        "display_name": adapter["display_name"],
        "source_kind": adapter["source_kind"],
        "artifact_roles": list(adapter["artifact_roles"]),
        "fixture_types": list(adapter["fixture_types"]),
        "runtime_capability_ids": [contract["capability_id"] for contract in runtime_contracts],
        "expected_pipeline_outputs": [
            "artifact_collection",
            "content_or_comment_extraction",
            "capture_bundle",
            "total_export_package",
            "evidence_queue",
            "release_archive_closeout",
        ],
        "fixture_pack_status": "READY_FOR_LOCAL_FIXTURE_AUTHORING_AND_SHARED_PIPELINE_EXECUTION",
        "pack_index": index,
    }
    return dict(unsigned, fixture_pack_id=f"source_adapter.priority_fixture_pack.{_stable_hash(unsigned)}")


def _manual_smoke_scenario(acceptance: Mapping[str, Any], contract: Mapping[str, Any], index: int) -> dict[str, Any]:
    capability_id = _safe_id(acceptance.get("capability_id"), label="capability_id")
    spec = _CAPABILITY_EXECUTION_SPEC[capability_id]
    unsigned = {
        "schema_version": "source_adapter_manual_live_smoke_scenario_v1",
        "capability_id": capability_id,
        "operator_approval_id": acceptance.get("operator_approval_id"),
        "runtime_execution_contract_id": contract.get("runtime_execution_contract_id"),
        "controller_route_id": spec["controller_route_id"],
        "provider_execution_adapter_id": spec["provider_execution_adapter_id"],
        "manual_smoke_goal": spec["manual_smoke_goal"],
        "required_operator_inputs": list(spec["payload_fields"]),
        "expected_receipt_fields": list(spec["receipt_fields"]),
        "execution_mode": "operator_approved_manual_smoke",
        "live_execution_requires_named_site_or_provider": True,
        "scenario_status": "READY_FOR_OPERATOR_APPROVED_MANUAL_SMOKE",
        "scenario_index": index,
    }
    return dict(unsigned, manual_smoke_scenario_id=f"source_adapter.manual_live_smoke.{_stable_hash(unsigned)}")


def build_source_adapter_runtime_operator_acceptance_closeout(
    ui_provider_integration_bridge_package: Mapping[str, Any],
    *,
    enabled_capabilities: Iterable[str] | None = None,
    operator_id: str = "operator",
    acceptance_profile: str = "source_adapter_runtime_operator_acceptance_v1",
    acceptance_decision: str = "ACCEPTED_FOR_OPERATOR_APPROVED_EXECUTION",
    acceptance_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build the combined runtime operator acceptance/execution closeout package."""

    package = _as_mapping(ui_provider_integration_bridge_package, "ui_provider_integration_bridge_package")
    if package.get("runtime_ui_provider_integration_status") != "SOURCE_ADAPTER_RUNTIME_UI_PROVIDER_INTEGRATIONS_BUILT":
        raise ValueError("runtime UI/provider integration package must be SOURCE_ADAPTER_RUNTIME_UI_PROVIDER_INTEGRATIONS_BUILT")
    handoff = _as_mapping(package.get("source_adapter_runtime_operator_acceptance_handoff"), "operator_acceptance_handoff")
    if handoff.get("handoff_status") != "SOURCE_ADAPTER_RUNTIME_READY_FOR_OPERATOR_ACCEPTANCE":
        raise ValueError("operator acceptance handoff must be SOURCE_ADAPTER_RUNTIME_READY_FOR_OPERATOR_ACCEPTANCE")
    if handoff.get("required_next_stage") != "source_adapter_runtime_operator_acceptance":
        raise ValueError("operator acceptance handoff must request source_adapter_runtime_operator_acceptance")
    if handoff.get("ready_for_operator_acceptance") is not True:
        raise ValueError("operator acceptance handoff must be ready")

    operator_id = _safe_id(operator_id, label="operator_id")
    acceptance_profile = _safe_id(acceptance_profile, label="acceptance_profile")
    acceptance_decision = _safe_id(acceptance_decision, label="acceptance_decision")
    selected = _capability_filter(enabled_capabilities)
    notes = _normalise_notes(acceptance_notes)

    rows = [row for row in _integration_rows(package) if selected is None or row.get("capability_id") in selected]
    if not rows:
        raise ValueError("at least one runtime UI/provider integration row is required")

    acceptance_rows = [
        _acceptance_row(
            row,
            index,
            operator_id=operator_id,
            acceptance_profile=acceptance_profile,
            acceptance_decision=acceptance_decision,
        )
        for index, row in enumerate(rows)
    ]
    execution_contracts = [_execution_contract(row, index) for index, row in enumerate(acceptance_rows)]
    provider_adapters = [
        _provider_adapter(acceptance, contract, index)
        for index, (acceptance, contract) in enumerate(zip(acceptance_rows, execution_contracts))
    ]
    gui_routes = [
        _gui_route(acceptance, contract, index)
        for index, (acceptance, contract) in enumerate(zip(acceptance_rows, execution_contracts))
    ]
    receipt_templates = [
        _receipt_template(acceptance, contract, index)
        for index, (acceptance, contract) in enumerate(zip(acceptance_rows, execution_contracts))
    ]
    fixture_packs = [_fixture_pack(adapter, execution_contracts, index) for index, adapter in enumerate(_PRIORITY_ADAPTERS)]
    smoke_scenarios = [
        _manual_smoke_scenario(acceptance, contract, index)
        for index, (acceptance, contract) in enumerate(zip(acceptance_rows, execution_contracts))
    ]

    integrated_capability_ids = [row["capability_id"] for row in acceptance_rows]
    controller_route_ids = [route["controller_route_id"] for route in gui_routes]
    provider_adapter_ids = [adapter["provider_execution_adapter_id"] for adapter in provider_adapters]
    execution_contract_ids = [contract["runtime_execution_contract_id"] for contract in execution_contracts]
    operator_approval_ids = [row["operator_approval_id"] for row in acceptance_rows]

    acceptance_batch = {
        "schema_version": ACCEPTANCE_BATCH_SCHEMA_VERSION,
        "operator_id": operator_id,
        "acceptance_profile": acceptance_profile,
        "acceptance_decision": acceptance_decision,
        "accepted_capability_count": len(acceptance_rows),
        "operator_approval_ids": operator_approval_ids,
        "acceptance_rows": acceptance_rows,
    }
    execution_contract_doc = {
        "schema_version": EXECUTION_CONTRACTS_SCHEMA_VERSION,
        "runtime_execution_status": "SOURCE_ADAPTER_RUNTIME_EXECUTION_CONTRACTS_READY",
        "execution_contract_count": len(execution_contracts),
        "execution_contract_ids": execution_contract_ids,
        "execution_modes": ["dry_run", "operator_approved_live"],
        "runtime_execution_contracts": execution_contracts,
    }
    provider_index = {
        "schema_version": PROVIDER_ADAPTER_INDEX_SCHEMA_VERSION,
        "provider_adapter_status": "SOURCE_ADAPTER_PROVIDER_EXECUTION_ADAPTERS_READY",
        "provider_adapter_count": len(provider_adapters),
        "provider_execution_adapter_ids": provider_adapter_ids,
        "provider_execution_adapters": provider_adapters,
    }
    gui_manifest = {
        "schema_version": GUI_CONTROLLER_BINDING_SCHEMA_VERSION,
        "gui_controller_binding_status": "SOURCE_ADAPTER_GUI_CONTROLLER_ROUTES_READY",
        "route_count": len(gui_routes),
        "controller_route_ids": controller_route_ids,
        "keys_accounts_surface_id": "keys_accounts.ui.credential_reference_selector",
        "routes": gui_routes,
    }
    receipt_template_index = {
        "schema_version": RECEIPT_TEMPLATE_INDEX_SCHEMA_VERSION,
        "receipt_template_status": "SOURCE_ADAPTER_RUNTIME_RECEIPT_TEMPLATES_READY",
        "receipt_template_count": len(receipt_templates),
        "runtime_receipt_template_ids": [item["runtime_receipt_template_id"] for item in receipt_templates],
        "receipt_templates": receipt_templates,
    }
    priority_fixture_pack_plan = {
        "schema_version": PRIORITY_FIXTURE_PACK_SCHEMA_VERSION,
        "fixture_pack_status": "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACKS_READY_FOR_AUTHORING",
        "fixture_pack_count": len(fixture_packs),
        "fixture_pack_ids": [item["fixture_pack_id"] for item in fixture_packs],
        "priority_fixture_packs": fixture_packs,
    }
    manual_live_smoke_plan = {
        "schema_version": MANUAL_SMOKE_PLAN_SCHEMA_VERSION,
        "manual_live_smoke_status": "SOURCE_ADAPTER_MANUAL_LIVE_SMOKE_SCENARIOS_READY",
        "scenario_count": len(smoke_scenarios),
        "manual_live_smoke_scenario_ids": [item["manual_smoke_scenario_id"] for item in smoke_scenarios],
        "execution_mode": "operator_approved_manual_smoke",
        "scenarios": smoke_scenarios,
    }
    roadmap_closeout_index = {
        "schema_version": ROADMAP_CLOSEOUT_SCHEMA_VERSION,
        "roadmap_closeout_status": "SOURCE_ADAPTER_SHARED_RUNTIME_ROADMAP_CLOSEOUT_READY",
        "closed_runtime_sections": [
            "operator_acceptance",
            "runtime_execution_contracts",
            "gui_controller_route_manifest",
            "provider_execution_adapter_index",
            "receipt_template_index",
            "priority_fixture_pack_plan",
            "manual_live_smoke_acceptance_plan",
        ],
        "capability_count": len(integrated_capability_ids),
        "integrated_capability_ids": integrated_capability_ids,
        "controller_route_ids": controller_route_ids,
        "provider_execution_adapter_ids": provider_adapter_ids,
        "fixture_pack_ids": priority_fixture_pack_plan["fixture_pack_ids"],
        "manual_live_smoke_scenario_ids": manual_live_smoke_plan["manual_live_smoke_scenario_ids"],
    }
    final_handoff = {
        "schema_version": FINAL_HANDOFF_SCHEMA_VERSION,
        "handoff_status": RUNTIME_READY_FOR_CONTROLLER_AND_SMOKE_STATUS,
        "required_next_stage": "source_adapter_runtime_controller_install_and_manual_live_smoke",
        "ready_for_controller_install": True,
        "ready_for_provider_execution_adapter_install": True,
        "ready_for_priority_fixture_authoring": True,
        "ready_for_manual_live_smoke": True,
        "integrated_capability_ids": integrated_capability_ids,
        "controller_route_ids": controller_route_ids,
        "provider_execution_adapter_ids": provider_adapter_ids,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT_STATUS,
        "accepted_capability_count": len(acceptance_rows),
        "controller_route_count": len(gui_routes),
        "provider_adapter_count": len(provider_adapters),
        "fixture_pack_count": len(fixture_packs),
        "manual_live_smoke_scenario_count": len(smoke_scenarios),
        "next_actions": [
            "Install the generated controller routes into the GUI runtime dispatcher.",
            "Bind provider execution adapters to operator-approved runtime handlers.",
            "Author priority adapter fixture packs and run manual/live smoke only with named operator inputs.",
        ],
    }

    unsigned_package = {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_runtime_ui_provider_integration_bridge_id": package.get(
            "source_adapter_runtime_ui_provider_integration_bridge_id", ""
        ),
        "runtime_operator_acceptance_closeout_status": RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT_STATUS,
        "accepted_capability_count": len(acceptance_rows),
        "issue_count": 0,
        "issues": [],
        "source_adapter_runtime_operator_acceptance_batch": acceptance_batch,
        "source_adapter_runtime_execution_contracts": execution_contract_doc,
        "source_adapter_provider_execution_adapter_index": provider_index,
        "source_adapter_gui_controller_binding_manifest": gui_manifest,
        "source_adapter_runtime_receipt_template_index": receipt_template_index,
        "source_adapter_priority_fixture_pack_plan": priority_fixture_pack_plan,
        "source_adapter_manual_live_smoke_acceptance_plan": manual_live_smoke_plan,
        "source_adapter_runtime_roadmap_closeout_index": roadmap_closeout_index,
        "source_adapter_runtime_final_closeout_handoff": final_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "input_source": "source_adapter_runtime_ui_provider_integration_bridge",
            "combined_runtime_sections": roadmap_closeout_index["closed_runtime_sections"],
            "multi_capability_batch_supported": True,
            "operator_approved_live_execution_surface": True,
            "keys_accounts_lookup_surface": "keys_accounts.ui.credential_reference_selector",
        },
        "acceptance_notes": notes,
    }
    bridge_id = f"source_adapter_runtime_operator_acceptance_closeout.{_stable_hash(unsigned_package)}"
    return dict(unsigned_package, source_adapter_runtime_operator_acceptance_closeout_id=bridge_id)
