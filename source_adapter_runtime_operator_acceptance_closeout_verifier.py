from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_runtime_operator_acceptance_closeout_verifier_v1"
EXPECTED_STATUS = "SOURCE_ADAPTER_RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT_BUILT"
EXPECTED_HANDOFF = "SOURCE_ADAPTER_RUNTIME_READY_FOR_CONTROLLER_INSTALL_AND_MANUAL_LIVE_SMOKE"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def verify_source_adapter_runtime_operator_acceptance_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_runtime_operator_acceptance_closeout_v1":
        _issue(issues, "schema_version must be source_adapter_runtime_operator_acceptance_closeout_v1")
    if pkg.get("runtime_operator_acceptance_closeout_status") != EXPECTED_STATUS:
        _issue(issues, "runtime_operator_acceptance_closeout_status mismatch")
    bridge_id = str(pkg.get("source_adapter_runtime_operator_acceptance_closeout_id") or "")
    if not bridge_id:
        _issue(issues, "source_adapter_runtime_operator_acceptance_closeout_id is required")
    input_id = str(pkg.get("source_adapter_runtime_ui_provider_integration_bridge_id") or "")
    if not input_id:
        _issue(issues, "source_adapter_runtime_ui_provider_integration_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero")

    acceptance_batch = _mapping(pkg.get("source_adapter_runtime_operator_acceptance_batch"))
    acceptance_rows = []
    if not acceptance_batch:
        _issue(issues, "source_adapter_runtime_operator_acceptance_batch is required")
    else:
        if acceptance_batch.get("schema_version") != "source_adapter_runtime_operator_acceptance_batch_v1":
            _issue(issues, "acceptance batch schema_version mismatch")
        acceptance_rows = _list(acceptance_batch.get("acceptance_rows"))
        if not acceptance_rows:
            _issue(issues, "acceptance rows are required")
        if acceptance_batch.get("accepted_capability_count") != len(acceptance_rows):
            _issue(issues, "accepted capability count mismatch")

    capability_ids: set[str] = set()
    approval_ids: set[str] = set()
    for index, row in enumerate(acceptance_rows):
        if not isinstance(row, Mapping):
            _issue(issues, f"acceptance_rows[{index}] must be an object")
            continue
        capability_id = str(row.get("capability_id") or "")
        if not capability_id:
            _issue(issues, f"acceptance_rows[{index}] missing capability_id")
        if capability_id in capability_ids:
            _issue(issues, f"duplicate capability_id: {capability_id}")
        capability_ids.add(capability_id)
        approval_id = str(row.get("operator_approval_id") or "")
        if not approval_id:
            _issue(issues, f"acceptance_rows[{index}] missing operator_approval_id")
        approval_ids.add(approval_id)
        if row.get("approval_gate_status") != "OPERATOR_APPROVAL_RECORDED":
            _issue(issues, f"acceptance_rows[{index}] approval gate status mismatch")
        if row.get("execution_authorization_status") != "READY_FOR_OPERATOR_APPROVED_EXECUTION":
            _issue(issues, f"acceptance_rows[{index}] execution authorization mismatch")
        if "operator_approved_live" not in _list(row.get("execution_modes")):
            _issue(issues, f"acceptance_rows[{index}] missing operator_approved_live execution mode")

    contracts_doc = _mapping(pkg.get("source_adapter_runtime_execution_contracts"))
    contract_capabilities: set[str] = set()
    contract_ids: set[str] = set()
    if not contracts_doc:
        _issue(issues, "source_adapter_runtime_execution_contracts is required")
    else:
        if contracts_doc.get("schema_version") != "source_adapter_runtime_execution_contracts_v1":
            _issue(issues, "execution contracts schema_version mismatch")
        contracts = _list(contracts_doc.get("runtime_execution_contracts"))
        if contracts_doc.get("execution_contract_count") != len(contracts):
            _issue(issues, "execution contract count mismatch")
        for index, contract in enumerate(contracts):
            if not isinstance(contract, Mapping):
                _issue(issues, f"runtime_execution_contracts[{index}] must be an object")
                continue
            contract_capabilities.add(str(contract.get("capability_id") or ""))
            contract_ids.add(str(contract.get("runtime_execution_contract_id") or ""))
            if contract.get("operator_approval_required") is not True:
                _issue(issues, f"runtime_execution_contracts[{index}] must require operator approval")
            if not _list(contract.get("payload_fields")) or not _list(contract.get("receipt_fields")):
                _issue(issues, f"runtime_execution_contracts[{index}] missing payload or receipt fields")
    if contract_capabilities != capability_ids:
        _issue(issues, "execution contract capability set mismatch")

    provider_index = _mapping(pkg.get("source_adapter_provider_execution_adapter_index"))
    provider_capabilities: set[str] = set()
    provider_ids: set[str] = set()
    if not provider_index:
        _issue(issues, "source_adapter_provider_execution_adapter_index is required")
    else:
        adapters = _list(provider_index.get("provider_execution_adapters"))
        if provider_index.get("schema_version") != "source_adapter_provider_execution_adapter_index_v1":
            _issue(issues, "provider adapter index schema_version mismatch")
        if provider_index.get("provider_adapter_count") != len(adapters):
            _issue(issues, "provider adapter count mismatch")
        for index, adapter in enumerate(adapters):
            if not isinstance(adapter, Mapping):
                _issue(issues, f"provider_execution_adapters[{index}] must be an object")
                continue
            provider_capabilities.add(str(adapter.get("capability_id") or ""))
            provider_ids.add(str(adapter.get("provider_execution_adapter_id") or ""))
            if adapter.get("receipt_required") is not True:
                _issue(issues, f"provider_execution_adapters[{index}] must require receipt")
    if provider_capabilities != capability_ids:
        _issue(issues, "provider adapter capability set mismatch")

    gui_manifest = _mapping(pkg.get("source_adapter_gui_controller_binding_manifest"))
    route_capabilities: set[str] = set()
    route_ids: set[str] = set()
    if not gui_manifest:
        _issue(issues, "source_adapter_gui_controller_binding_manifest is required")
    else:
        routes = _list(gui_manifest.get("routes"))
        if gui_manifest.get("schema_version") != "source_adapter_gui_controller_binding_manifest_v1":
            _issue(issues, "GUI/controller manifest schema_version mismatch")
        if gui_manifest.get("route_count") != len(routes):
            _issue(issues, "GUI route count mismatch")
        if gui_manifest.get("keys_accounts_surface_id") != "keys_accounts.ui.credential_reference_selector":
            _issue(issues, "KEYS/ACCOUNTS surface id mismatch")
        for index, route in enumerate(routes):
            if not isinstance(route, Mapping):
                _issue(issues, f"routes[{index}] must be an object")
                continue
            route_capabilities.add(str(route.get("capability_id") or ""))
            route_ids.add(str(route.get("controller_route_id") or ""))
            if route.get("confirmation_required") is not True:
                _issue(issues, f"routes[{index}] must require confirmation")
    if route_capabilities != capability_ids:
        _issue(issues, "GUI route capability set mismatch")

    receipt_index = _mapping(pkg.get("source_adapter_runtime_receipt_template_index"))
    if not receipt_index:
        _issue(issues, "source_adapter_runtime_receipt_template_index is required")
    else:
        templates = _list(receipt_index.get("receipt_templates"))
        if receipt_index.get("schema_version") != "source_adapter_runtime_receipt_template_index_v1":
            _issue(issues, "receipt template index schema_version mismatch")
        if receipt_index.get("receipt_template_count") != len(templates):
            _issue(issues, "receipt template count mismatch")

    fixture_plan = _mapping(pkg.get("source_adapter_priority_fixture_pack_plan"))
    if not fixture_plan:
        _issue(issues, "source_adapter_priority_fixture_pack_plan is required")
    else:
        packs = _list(fixture_plan.get("priority_fixture_packs"))
        if fixture_plan.get("schema_version") != "source_adapter_priority_fixture_pack_plan_v1":
            _issue(issues, "priority fixture pack schema_version mismatch")
        if fixture_plan.get("fixture_pack_count") != len(packs):
            _issue(issues, "priority fixture pack count mismatch")
        if len(packs) < 5:
            _issue(issues, "priority fixture pack plan should cover at least five adapter families")

    smoke_plan = _mapping(pkg.get("source_adapter_manual_live_smoke_acceptance_plan"))
    if not smoke_plan:
        _issue(issues, "source_adapter_manual_live_smoke_acceptance_plan is required")
    else:
        scenarios = _list(smoke_plan.get("scenarios"))
        if smoke_plan.get("schema_version") != "source_adapter_manual_live_smoke_acceptance_plan_v1":
            _issue(issues, "manual/live smoke plan schema_version mismatch")
        if smoke_plan.get("scenario_count") != len(scenarios):
            _issue(issues, "manual/live smoke scenario count mismatch")
        if smoke_plan.get("execution_mode") != "operator_approved_manual_smoke":
            _issue(issues, "manual/live smoke execution mode mismatch")

    roadmap = _mapping(pkg.get("source_adapter_runtime_roadmap_closeout_index"))
    if not roadmap:
        _issue(issues, "source_adapter_runtime_roadmap_closeout_index is required")
    else:
        if roadmap.get("schema_version") != "source_adapter_runtime_roadmap_closeout_index_v1":
            _issue(issues, "roadmap closeout schema_version mismatch")
        if set(roadmap.get("integrated_capability_ids") or []) != capability_ids:
            _issue(issues, "roadmap integrated capability ids mismatch")

    handoff = _mapping(pkg.get("source_adapter_runtime_final_closeout_handoff"))
    handoff_status = ""
    if not handoff:
        _issue(issues, "source_adapter_runtime_final_closeout_handoff is required")
    else:
        handoff_status = str(handoff.get("handoff_status") or "")
        if handoff.get("schema_version") != "source_adapter_runtime_final_closeout_handoff_v1":
            _issue(issues, "final closeout handoff schema_version mismatch")
        if handoff_status != EXPECTED_HANDOFF:
            _issue(issues, "final closeout handoff status mismatch")
        if handoff.get("ready_for_controller_install") is not True:
            _issue(issues, "final handoff must be ready for controller install")
        if handoff.get("ready_for_manual_live_smoke") is not True:
            _issue(issues, "final handoff must be ready for manual live smoke")
        if set(handoff.get("integrated_capability_ids") or []) != capability_ids:
            _issue(issues, "final handoff capability ids mismatch")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_operator_acceptance_closeout_id": bridge_id,
        "source_adapter_runtime_ui_provider_integration_bridge_id": input_id,
        "accepted_capability_count": len(capability_ids),
        "provider_adapter_count": len(provider_ids),
        "controller_route_count": len(route_ids),
        "handoff_status": handoff_status,
    }
