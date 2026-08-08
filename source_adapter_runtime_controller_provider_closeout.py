from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_adapter_runtime_controller_provider_closeout_v1"
CONTROLLER_INSTALL_SCHEMA_VERSION = "source_adapter_runtime_controller_install_manifest_v1"
PROVIDER_REGISTRY_SCHEMA_VERSION = "source_adapter_runtime_provider_execution_registry_v1"
DISPATCH_TABLE_SCHEMA_VERSION = "source_adapter_runtime_dispatch_table_v1"
APPROVAL_LEDGER_SCHEMA_VERSION = "source_adapter_runtime_operator_approval_ledger_v1"
FIXTURE_SEED_SCHEMA_VERSION = "source_adapter_runtime_fixture_receipt_seed_batch_v1"
MANUAL_SMOKE_MATRIX_SCHEMA_VERSION = "source_adapter_runtime_manual_live_smoke_execution_matrix_v1"
PRIORITY_FIXTURE_SEED_SCHEMA_VERSION = "source_adapter_priority_adapter_fixture_seed_bundle_v1"
ROADMAP_AUDIT_SCHEMA_VERSION = "source_adapter_runtime_controller_provider_roadmap_audit_v1"
FINAL_HANDOFF_SCHEMA_VERSION = "source_adapter_runtime_controller_provider_final_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_runtime_controller_provider_closeout_operator_summary_v1"

CONTROLLER_PROVIDER_CLOSEOUT_STATUS = "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_CLOSEOUT_BUILT"
READY_FOR_PRIORITY_FIXTURES_AND_MANUAL_SMOKE = "SOURCE_ADAPTER_RUNTIME_READY_FOR_PRIORITY_FIXTURES_AND_MANUAL_LIVE_SMOKE"
EXPECTED_INPUT_STATUS = "SOURCE_ADAPTER_RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT_BUILT"
EXPECTED_INPUT_HANDOFF_STATUS = "SOURCE_ADAPTER_RUNTIME_READY_FOR_CONTROLLER_INSTALL_AND_MANUAL_LIVE_SMOKE"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_SECRET_FIELD_RE = re.compile(r"(secret|token|api[_-]?key|password|credential)", re.I)


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:12]


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_id(value: Any, *, label: str = "id") -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} contains unsupported characters: {text}")
    return text


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _notes(values: Iterable[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        text = _safe_text(value)
        if text:
            out.append(text)
    return out


def _redacted_value(key: str, value: Any) -> Any:
    if _SECRET_FIELD_RE.search(key):
        digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
        return {"redacted": True, "sha256": digest}
    if isinstance(value, Mapping):
        return {str(k): _redacted_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redacted_value(key, item) for item in value]
    return value


def _redacted_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(k): _redacted_value(str(k), v) for k, v in payload.items()}


def _index_by(rows: Iterable[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        row_id = str(row.get(key) or "")
        if row_id:
            indexed[row_id] = row
    return indexed


def _capability_filter(enabled_capabilities: Iterable[str] | None) -> set[str] | None:
    if enabled_capabilities is None:
        return None
    return {_safe_id(value, label="enabled_capability") for value in enabled_capabilities}


def _accepted_rows(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    batch = _mapping(package.get("source_adapter_runtime_operator_acceptance_batch"), "operator_acceptance_batch")
    rows = [_mapping(row, "acceptance_row") for row in _list(batch.get("acceptance_rows"))]
    if not rows:
        raise ValueError("operator acceptance rows are required")
    return rows


def _contracts(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    doc = _mapping(package.get("source_adapter_runtime_execution_contracts"), "execution_contracts")
    rows = [_mapping(row, "runtime_execution_contract") for row in _list(doc.get("runtime_execution_contracts"))]
    if not rows:
        raise ValueError("runtime execution contracts are required")
    return rows


def _provider_adapters(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    doc = _mapping(package.get("source_adapter_provider_execution_adapter_index"), "provider_adapter_index")
    rows = [_mapping(row, "provider_execution_adapter") for row in _list(doc.get("provider_execution_adapters"))]
    if not rows:
        raise ValueError("provider execution adapters are required")
    return rows


def _gui_routes(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    doc = _mapping(package.get("source_adapter_gui_controller_binding_manifest"), "gui_controller_binding_manifest")
    rows = [_mapping(row, "gui_controller_route") for row in _list(doc.get("routes"))]
    if not rows:
        raise ValueError("GUI/controller routes are required")
    return rows


def _receipt_templates(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    doc = _mapping(package.get("source_adapter_runtime_receipt_template_index"), "receipt_template_index")
    rows = [_mapping(row, "runtime_receipt_template") for row in _list(doc.get("receipt_templates"))]
    if not rows:
        raise ValueError("runtime receipt templates are required")
    return rows


def _fixture_packs(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    doc = _mapping(package.get("source_adapter_priority_fixture_pack_plan"), "priority_fixture_pack_plan")
    rows = [_mapping(row, "priority_fixture_pack") for row in _list(doc.get("priority_fixture_packs"))]
    if not rows:
        raise ValueError("priority fixture packs are required")
    return rows


def _manual_smoke_scenarios(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    doc = _mapping(package.get("source_adapter_manual_live_smoke_acceptance_plan"), "manual_live_smoke_plan")
    rows = [_mapping(row, "manual_live_smoke_scenario") for row in _list(doc.get("scenarios"))]
    if not rows:
        raise ValueError("manual/live smoke scenarios are required")
    return rows


def _controller_install_row(route: Mapping[str, Any], acceptance: Mapping[str, Any], contract: Mapping[str, Any], provider: Mapping[str, Any], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_runtime_controller_install_row_v1",
        "capability_id": route.get("capability_id"),
        "controller_route_id": route.get("controller_route_id"),
        "controller_action": route.get("controller_action"),
        "gui_controller_route_id": route.get("gui_controller_route_id"),
        "ui_surface_id": route.get("ui_surface_id"),
        "display_label": route.get("display_label"),
        "runtime_execution_contract_id": contract.get("runtime_execution_contract_id"),
        "operator_approval_id": acceptance.get("operator_approval_id"),
        "provider_execution_adapter_id": provider.get("provider_execution_adapter_id"),
        "provider_action": provider.get("provider_action"),
        "confirmation_required": True,
        "receipt_panel_required": True,
        "install_status": "INSTALLED_IN_SHARED_RUNTIME_CONTROLLER_MANIFEST",
        "row_index": index,
    }
    return dict(unsigned, controller_install_row_id=f"source_adapter.controller_install.{_stable_hash(unsigned)}")


def _provider_registry_row(provider: Mapping[str, Any], contract: Mapping[str, Any], template: Mapping[str, Any], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_runtime_provider_registry_row_v1",
        "capability_id": provider.get("capability_id"),
        "provider_execution_adapter_id": provider.get("provider_execution_adapter_id"),
        "provider_execution_adapter_record_id": provider.get("provider_execution_adapter_record_id"),
        "provider_action": provider.get("provider_action"),
        "provider_surface_id": provider.get("provider_surface_id"),
        "runtime_execution_contract_id": contract.get("runtime_execution_contract_id"),
        "runtime_receipt_template_id": template.get("runtime_receipt_template_id"),
        "side_effect_channel": provider.get("side_effect_channel"),
        "supported_execution_modes": list(provider.get("supported_execution_modes") or ["dry_run", "operator_approved_live"]),
        "receipt_required": True,
        "entrypoint_status": "BOUND_TO_SHARED_PROVIDER_EXECUTION_REGISTRY",
        "row_index": index,
    }
    return dict(unsigned, provider_registry_row_id=f"source_adapter.provider_registry.{_stable_hash(unsigned)}")


def _dispatch_row(controller_row: Mapping[str, Any], provider_row: Mapping[str, Any], contract: Mapping[str, Any], template: Mapping[str, Any], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_runtime_dispatch_row_v1",
        "capability_id": controller_row.get("capability_id"),
        "controller_route_id": controller_row.get("controller_route_id"),
        "controller_action": controller_row.get("controller_action"),
        "provider_execution_adapter_id": provider_row.get("provider_execution_adapter_id"),
        "provider_action": provider_row.get("provider_action"),
        "runtime_execution_contract_id": contract.get("runtime_execution_contract_id"),
        "runtime_receipt_template_id": template.get("runtime_receipt_template_id"),
        "payload_fields": list(contract.get("payload_fields") or []),
        "receipt_fields": list(template.get("required_receipt_fields") or []),
        "approval_flow": "operator_approval_id_required_for_operator_approved_live",
        "dry_run_handler": "source_adapter.runtime.dispatch.deterministic_receipt",
        "operator_approved_handler": "source_adapter.runtime.dispatch.provider_entrypoint",
        "dispatch_status": "ROUTED_THROUGH_SHARED_RUNTIME_DISPATCH_TABLE",
        "row_index": index,
    }
    return dict(unsigned, runtime_dispatch_row_id=f"source_adapter.runtime_dispatch.{_stable_hash(unsigned)}")


def _approval_ledger_row(acceptance: Mapping[str, Any], dispatch: Mapping[str, Any], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_runtime_operator_approval_ledger_row_v1",
        "operator_approval_id": acceptance.get("operator_approval_id"),
        "capability_id": acceptance.get("capability_id"),
        "operator_id": acceptance.get("operator_id"),
        "acceptance_profile": acceptance.get("acceptance_profile"),
        "acceptance_decision": acceptance.get("acceptance_decision"),
        "runtime_dispatch_row_id": dispatch.get("runtime_dispatch_row_id"),
        "allowed_execution_modes": ["dry_run", "operator_approved_live"],
        "ledger_status": "OPERATOR_APPROVAL_AVAILABLE_FOR_RUNTIME_EXECUTION",
        "row_index": index,
    }
    return dict(unsigned, approval_ledger_row_id=f"source_adapter.approval_ledger.{_stable_hash(unsigned)}")


def _fixture_receipt_seed(dispatch: Mapping[str, Any], ledger: Mapping[str, Any], index: int) -> dict[str, Any]:
    capability_id = str(dispatch.get("capability_id") or "")
    base_payload = {field: f"fixture_{field}" for field in dispatch.get("payload_fields") or []}
    unsigned = {
        "schema_version": "source_adapter_runtime_fixture_receipt_seed_v1",
        "capability_id": capability_id,
        "runtime_dispatch_row_id": dispatch.get("runtime_dispatch_row_id"),
        "operator_approval_id": ledger.get("operator_approval_id"),
        "fixture_payload": base_payload,
        "expected_receipt_fields": list(dispatch.get("receipt_fields") or []),
        "expected_receipt_statuses": ["DRY_RUN_RECEIPT_RECORDED", "OPERATOR_APPROVED_RECEIPT_RECORDED"],
        "fixture_status": "READY_FOR_LOCAL_AND_OPERATOR_APPROVED_RECEIPT_TESTING",
        "row_index": index,
    }
    return dict(unsigned, fixture_receipt_seed_id=f"source_adapter.fixture_receipt_seed.{_stable_hash(unsigned)}")


def _manual_smoke_execution_row(scenario: Mapping[str, Any], dispatch: Mapping[str, Any], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_runtime_manual_smoke_execution_row_v1",
        "capability_id": scenario.get("capability_id"),
        "manual_smoke_scenario_id": scenario.get("manual_smoke_scenario_id"),
        "runtime_dispatch_row_id": dispatch.get("runtime_dispatch_row_id"),
        "controller_route_id": scenario.get("controller_route_id"),
        "provider_execution_adapter_id": scenario.get("provider_execution_adapter_id"),
        "operator_approval_id": scenario.get("operator_approval_id"),
        "required_operator_inputs": list(scenario.get("required_operator_inputs") or []),
        "expected_receipt_fields": list(scenario.get("expected_receipt_fields") or []),
        "manual_smoke_goal": scenario.get("manual_smoke_goal"),
        "execution_mode": "operator_approved_manual_smoke",
        "smoke_status": "READY_FOR_NAMED_OPERATOR_INPUT_AND_APPROVAL",
        "row_index": index,
    }
    return dict(unsigned, manual_smoke_execution_row_id=f"source_adapter.manual_smoke_execution.{_stable_hash(unsigned)}")


def _priority_fixture_seed(pack: Mapping[str, Any], dispatch_rows: list[Mapping[str, Any]], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_priority_adapter_fixture_seed_v1",
        "adapter_id": pack.get("adapter_id"),
        "display_name": pack.get("display_name"),
        "source_kind": pack.get("source_kind"),
        "artifact_roles": list(pack.get("artifact_roles") or []),
        "fixture_types": list(pack.get("fixture_types") or []),
        "runtime_dispatch_row_ids": [row.get("runtime_dispatch_row_id") for row in dispatch_rows],
        "expected_pipeline_outputs": list(pack.get("expected_pipeline_outputs") or []),
        "fixture_seed_status": "READY_FOR_PRIORITY_ADAPTER_FIXTURE_AUTHORING_AND_EXECUTION",
        "row_index": index,
    }
    return dict(unsigned, priority_adapter_fixture_seed_id=f"source_adapter.priority_fixture_seed.{_stable_hash(unsigned)}")


def build_source_adapter_runtime_controller_provider_closeout(
    operator_acceptance_closeout_package: Mapping[str, Any],
    *,
    enabled_capabilities: Iterable[str] | None = None,
    operator_id: str = "operator",
    install_profile: str = "source_adapter_runtime_controller_provider_install_v1",
    closeout_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build the runtime controller/provider installation, execution, fixture, and smoke closeout package."""

    package = _mapping(operator_acceptance_closeout_package, "operator_acceptance_closeout_package")
    if package.get("runtime_operator_acceptance_closeout_status") != EXPECTED_INPUT_STATUS:
        raise ValueError("operator acceptance closeout package must be SOURCE_ADAPTER_RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT_BUILT")
    handoff = _mapping(package.get("source_adapter_runtime_final_closeout_handoff"), "runtime_final_closeout_handoff")
    if handoff.get("handoff_status") != EXPECTED_INPUT_HANDOFF_STATUS:
        raise ValueError("runtime final closeout handoff must be SOURCE_ADAPTER_RUNTIME_READY_FOR_CONTROLLER_INSTALL_AND_MANUAL_LIVE_SMOKE")
    if handoff.get("required_next_stage") != "source_adapter_runtime_controller_install_and_manual_live_smoke":
        raise ValueError("runtime final closeout handoff must request source_adapter_runtime_controller_install_and_manual_live_smoke")
    if handoff.get("ready_for_controller_install") is not True or handoff.get("ready_for_manual_live_smoke") is not True:
        raise ValueError("runtime final closeout handoff must be ready for controller install and manual/live smoke")

    selected = _capability_filter(enabled_capabilities)
    operator_id = _safe_id(operator_id, label="operator_id")
    install_profile = _safe_id(install_profile, label="install_profile")
    notes = _notes(closeout_notes)

    accepted = [row for row in _accepted_rows(package) if selected is None or row.get("capability_id") in selected]
    if not accepted:
        raise ValueError("at least one accepted runtime capability is required")
    capability_ids = [str(row.get("capability_id")) for row in accepted]

    contracts = _index_by(_contracts(package), "capability_id")
    providers = _index_by(_provider_adapters(package), "capability_id")
    routes = _index_by(_gui_routes(package), "capability_id")
    templates = _index_by(_receipt_templates(package), "capability_id")
    smoke = _index_by(_manual_smoke_scenarios(package), "capability_id")

    controller_rows: list[dict[str, Any]] = []
    provider_rows: list[dict[str, Any]] = []
    dispatch_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    fixture_receipt_rows: list[dict[str, Any]] = []
    smoke_rows: list[dict[str, Any]] = []
    for index, acceptance in enumerate(accepted):
        capability_id = _safe_id(acceptance.get("capability_id"), label="capability_id")
        if capability_id not in contracts or capability_id not in providers or capability_id not in routes or capability_id not in templates:
            raise ValueError(f"runtime capability is missing controller/provider/contract/template binding: {capability_id}")
        controller = _controller_install_row(routes[capability_id], acceptance, contracts[capability_id], providers[capability_id], index)
        provider = _provider_registry_row(providers[capability_id], contracts[capability_id], templates[capability_id], index)
        dispatch = _dispatch_row(controller, provider, contracts[capability_id], templates[capability_id], index)
        ledger = _approval_ledger_row(acceptance, dispatch, index)
        seed = _fixture_receipt_seed(dispatch, ledger, index)
        scenario = smoke.get(capability_id)
        if not scenario:
            raise ValueError(f"runtime capability is missing manual smoke scenario: {capability_id}")
        smoke_execution = _manual_smoke_execution_row(scenario, dispatch, index)
        controller_rows.append(controller)
        provider_rows.append(provider)
        dispatch_rows.append(dispatch)
        ledger_rows.append(ledger)
        fixture_receipt_rows.append(seed)
        smoke_rows.append(smoke_execution)

    priority_seeds = [_priority_fixture_seed(pack, dispatch_rows, index) for index, pack in enumerate(_fixture_packs(package))]
    dispatch_ids = [row["runtime_dispatch_row_id"] for row in dispatch_rows]

    controller_manifest = {
        "schema_version": CONTROLLER_INSTALL_SCHEMA_VERSION,
        "install_profile": install_profile,
        "controller_install_status": "SOURCE_ADAPTER_RUNTIME_CONTROLLER_ROUTES_INSTALLED_IN_SHARED_MANIFEST",
        "controller_route_count": len(controller_rows),
        "controller_route_ids": [row["controller_route_id"] for row in controller_rows],
        "controller_install_rows": controller_rows,
        "keys_accounts_surface_id": "keys_accounts.ui.credential_reference_selector",
    }
    provider_registry = {
        "schema_version": PROVIDER_REGISTRY_SCHEMA_VERSION,
        "provider_registry_status": "SOURCE_ADAPTER_RUNTIME_PROVIDER_EXECUTION_REGISTRY_BUILT",
        "provider_adapter_count": len(provider_rows),
        "provider_execution_adapter_ids": [row["provider_execution_adapter_id"] for row in provider_rows],
        "provider_registry_rows": provider_rows,
    }
    dispatch_table = {
        "schema_version": DISPATCH_TABLE_SCHEMA_VERSION,
        "runtime_dispatch_status": "SOURCE_ADAPTER_RUNTIME_DISPATCH_TABLE_READY",
        "dispatch_row_count": len(dispatch_rows),
        "runtime_dispatch_row_ids": dispatch_ids,
        "supported_execution_modes": ["dry_run", "operator_approved_live"],
        "runtime_dispatch_rows": dispatch_rows,
    }
    approval_ledger = {
        "schema_version": APPROVAL_LEDGER_SCHEMA_VERSION,
        "operator_id": operator_id,
        "approval_ledger_status": "SOURCE_ADAPTER_RUNTIME_OPERATOR_APPROVAL_LEDGER_READY",
        "approval_count": len(ledger_rows),
        "operator_approval_ids": [row["operator_approval_id"] for row in ledger_rows],
        "approval_ledger_rows": ledger_rows,
    }
    fixture_seed_batch = {
        "schema_version": FIXTURE_SEED_SCHEMA_VERSION,
        "fixture_receipt_seed_status": "SOURCE_ADAPTER_RUNTIME_FIXTURE_RECEIPT_SEEDS_READY",
        "fixture_receipt_seed_count": len(fixture_receipt_rows),
        "fixture_receipt_seed_rows": fixture_receipt_rows,
    }
    manual_smoke_matrix = {
        "schema_version": MANUAL_SMOKE_MATRIX_SCHEMA_VERSION,
        "manual_live_smoke_matrix_status": "SOURCE_ADAPTER_MANUAL_LIVE_SMOKE_EXECUTION_MATRIX_READY",
        "manual_live_smoke_execution_count": len(smoke_rows),
        "execution_mode": "operator_approved_manual_smoke",
        "manual_live_smoke_execution_rows": smoke_rows,
    }
    priority_fixture_seed_bundle = {
        "schema_version": PRIORITY_FIXTURE_SEED_SCHEMA_VERSION,
        "priority_fixture_seed_status": "SOURCE_ADAPTER_PRIORITY_FIXTURE_SEEDS_READY",
        "priority_fixture_seed_count": len(priority_seeds),
        "priority_adapter_fixture_seeds": priority_seeds,
    }
    roadmap_audit = {
        "schema_version": ROADMAP_AUDIT_SCHEMA_VERSION,
        "roadmap_audit_status": "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_ROADMAP_SECTIONS_CLOSED",
        "closed_sections": [
            "runtime_operator_acceptance",
            "runtime_controller_route_install_manifest",
            "runtime_provider_execution_registry",
            "runtime_dispatch_table",
            "operator_approval_ledger",
            "runtime_fixture_receipt_seeds",
            "priority_adapter_fixture_seed_bundle",
            "manual_live_smoke_execution_matrix",
        ],
        "capability_count": len(capability_ids),
        "capability_ids": capability_ids,
        "dispatch_row_ids": dispatch_ids,
    }
    final_handoff = {
        "schema_version": FINAL_HANDOFF_SCHEMA_VERSION,
        "handoff_status": READY_FOR_PRIORITY_FIXTURES_AND_MANUAL_SMOKE,
        "required_next_stage": "source_adapter_priority_fixtures_and_operator_approved_manual_live_smoke",
        "ready_for_priority_fixture_execution": True,
        "ready_for_operator_approved_manual_live_smoke": True,
        "ready_for_controller_runtime_dispatch": True,
        "runtime_dispatch_row_ids": dispatch_ids,
        "capability_ids": capability_ids,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": CONTROLLER_PROVIDER_CLOSEOUT_STATUS,
        "capability_count": len(capability_ids),
        "controller_route_count": len(controller_rows),
        "provider_adapter_count": len(provider_rows),
        "dispatch_row_count": len(dispatch_rows),
        "priority_fixture_seed_count": len(priority_seeds),
        "manual_live_smoke_execution_count": len(smoke_rows),
        "next_actions": [
            "Run priority adapter fixture packs through the shared runtime dispatch table.",
            "Use named operator inputs for manual/live smoke routes and preserve action receipts.",
            "Keep KEYS/ACCOUNTS lookups on redacted credential references in runtime receipts.",
        ],
    }

    unsigned_package = {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_runtime_operator_acceptance_closeout_id": package.get("source_adapter_runtime_operator_acceptance_closeout_id", ""),
        "runtime_controller_provider_closeout_status": CONTROLLER_PROVIDER_CLOSEOUT_STATUS,
        "capability_count": len(capability_ids),
        "issue_count": 0,
        "issues": [],
        "source_adapter_runtime_controller_install_manifest": controller_manifest,
        "source_adapter_runtime_provider_execution_registry": provider_registry,
        "source_adapter_runtime_dispatch_table": dispatch_table,
        "source_adapter_runtime_operator_approval_ledger": approval_ledger,
        "source_adapter_runtime_fixture_receipt_seed_batch": fixture_seed_batch,
        "source_adapter_priority_adapter_fixture_seed_bundle": priority_fixture_seed_bundle,
        "source_adapter_runtime_manual_live_smoke_execution_matrix": manual_smoke_matrix,
        "source_adapter_runtime_controller_provider_roadmap_audit": roadmap_audit,
        "source_adapter_runtime_controller_provider_final_handoff": final_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "input_source": "source_adapter_runtime_operator_acceptance_closeout",
            "controller_routes_installed_in_shared_manifest": True,
            "provider_execution_registry_built": True,
            "runtime_dispatch_available": True,
            "operator_approval_ledger_ready": True,
            "keys_accounts_surface_id": "keys_accounts.ui.credential_reference_selector",
            "multi_capability_batch_supported": True,
        },
        "closeout_notes": notes,
    }
    return dict(
        unsigned_package,
        source_adapter_runtime_controller_provider_closeout_id=f"source_adapter_runtime_controller_provider_closeout.{_stable_hash(unsigned_package)}",
    )


def execute_source_adapter_runtime_action(
    controller_provider_closeout_package: Mapping[str, Any],
    *,
    capability_id: str,
    payload: Mapping[str, Any],
    execution_mode: str = "dry_run",
    operator_approval_id: str | None = None,
    operator_id: str = "operator",
) -> dict[str, Any]:
    """Dispatch a runtime action through the generated controller/provider table and return a deterministic receipt."""

    package = _mapping(controller_provider_closeout_package, "controller_provider_closeout_package")
    if package.get("runtime_controller_provider_closeout_status") != CONTROLLER_PROVIDER_CLOSEOUT_STATUS:
        raise ValueError("runtime controller/provider closeout package must be built")
    capability_id = _safe_id(capability_id, label="capability_id")
    execution_mode = _safe_id(execution_mode, label="execution_mode")
    if execution_mode not in {"dry_run", "operator_approved_live"}:
        raise ValueError("execution_mode must be dry_run or operator_approved_live")
    payload_map = dict(_mapping(payload, "payload"))
    dispatch_table = _mapping(package.get("source_adapter_runtime_dispatch_table"), "runtime_dispatch_table")
    dispatch_rows = _index_by([_mapping(row, "dispatch_row") for row in _list(dispatch_table.get("runtime_dispatch_rows"))], "capability_id")
    if capability_id not in dispatch_rows:
        raise ValueError(f"capability is not available in runtime dispatch table: {capability_id}")
    dispatch = dispatch_rows[capability_id]
    ledger_doc = _mapping(package.get("source_adapter_runtime_operator_approval_ledger"), "operator_approval_ledger")
    ledger_rows = _index_by([_mapping(row, "approval_ledger_row") for row in _list(ledger_doc.get("approval_ledger_rows"))], "capability_id")
    ledger = ledger_rows.get(capability_id)
    if not ledger:
        raise ValueError(f"capability is missing operator approval ledger row: {capability_id}")
    expected_approval_id = str(ledger.get("operator_approval_id") or "")
    if execution_mode == "operator_approved_live" and operator_approval_id != expected_approval_id:
        raise ValueError("operator_approved_live execution requires the matching operator_approval_id")

    required_payload_fields = [str(field) for field in dispatch.get("payload_fields") or []]
    missing_payload_fields = [field for field in required_payload_fields if field not in payload_map]
    receipt_status = "DRY_RUN_RECEIPT_RECORDED" if execution_mode == "dry_run" else "OPERATOR_APPROVED_RECEIPT_RECORDED"
    receipt_body = {
        field: payload_map.get(field, f"{capability_id}:{field}:pending") for field in dispatch.get("receipt_fields") or []
    }
    receipt_body = _redacted_payload(receipt_body)
    unsigned_receipt = {
        "schema_version": "source_adapter_runtime_action_execution_receipt_v1",
        "capability_id": capability_id,
        "runtime_dispatch_row_id": dispatch.get("runtime_dispatch_row_id"),
        "controller_route_id": dispatch.get("controller_route_id"),
        "controller_action": dispatch.get("controller_action"),
        "provider_execution_adapter_id": dispatch.get("provider_execution_adapter_id"),
        "provider_action": dispatch.get("provider_action"),
        "operator_id": _safe_id(operator_id, label="operator_id"),
        "operator_approval_id": expected_approval_id if execution_mode == "operator_approved_live" else operator_approval_id or "",
        "execution_mode": execution_mode,
        "receipt_status": receipt_status,
        "missing_payload_fields": missing_payload_fields,
        "payload_sha256": hashlib.sha256(_stable_json(_redacted_payload(payload_map)).encode("utf-8")).hexdigest(),
        "receipt_body": receipt_body,
    }
    return dict(unsigned_receipt, runtime_action_execution_receipt_id=f"source_adapter.runtime_action_receipt.{_stable_hash(unsigned_receipt)}")


def runtime_controller_provider_capabilities(package: Mapping[str, Any]) -> list[str]:
    built = _mapping(package, "controller_provider_closeout_package")
    table = _mapping(built.get("source_adapter_runtime_dispatch_table"), "runtime_dispatch_table")
    return [str(row.get("capability_id")) for row in _list(table.get("runtime_dispatch_rows")) if isinstance(row, Mapping)]


def main() -> None:
    from source_adapter_runtime_operator_acceptance_closeout_test import fixture_runtime_ui_provider_integration_bridge
    from source_adapter_runtime_operator_acceptance_closeout import build_source_adapter_runtime_operator_acceptance_closeout
    from source_adapter_runtime_controller_provider_closeout_verifier import verify_source_adapter_runtime_controller_provider_closeout

    accepted = build_source_adapter_runtime_operator_acceptance_closeout(
        fixture_runtime_ui_provider_integration_bridge(), operator_id="operator.fixture"
    )
    package = build_source_adapter_runtime_controller_provider_closeout(accepted, operator_id="operator.fixture")
    verification = verify_source_adapter_runtime_controller_provider_closeout(package)
    if not verification["verified"]:
        raise SystemExit(verification)
    receipt = execute_source_adapter_runtime_action(
        package,
        capability_id="credential_lookup",
        payload={"credential_reference_id": "ref.fixture", "provider_id": "archive", "adapter_id": "article", "purpose": "manual_smoke"},
    )
    if receipt["receipt_status"] != "DRY_RUN_RECEIPT_RECORDED":
        raise SystemExit(receipt)
    print("Source Adapter Runtime Controller Provider Closeout self-test passed.")


if __name__ == "__main__":
    main()
