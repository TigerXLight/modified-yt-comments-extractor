from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_runtime_controller_provider_closeout_verifier_v1"
EXPECTED_STATUS = "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_CLOSEOUT_BUILT"
EXPECTED_HANDOFF = "SOURCE_ADAPTER_RUNTIME_READY_FOR_PRIORITY_FIXTURES_AND_MANUAL_LIVE_SMOKE"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_runtime_controller_provider_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = _mapping(package)
    if pkg.get("schema_version") != "source_adapter_runtime_controller_provider_closeout_v1":
        _issue(issues, "package schema_version mismatch")
    if pkg.get("runtime_controller_provider_closeout_status") != EXPECTED_STATUS:
        _issue(issues, "runtime controller/provider closeout status mismatch")
    bridge_id = str(pkg.get("source_adapter_runtime_controller_provider_closeout_id") or "")
    if not bridge_id:
        _issue(issues, "source_adapter_runtime_controller_provider_closeout_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero")

    controller = _mapping(pkg.get("source_adapter_runtime_controller_install_manifest"))
    controller_caps: set[str] = set()
    if not controller:
        _issue(issues, "controller install manifest is required")
    else:
        rows = _list(controller.get("controller_install_rows"))
        if controller.get("schema_version") != "source_adapter_runtime_controller_install_manifest_v1":
            _issue(issues, "controller install manifest schema_version mismatch")
        if controller.get("controller_route_count") != len(rows):
            _issue(issues, "controller route count mismatch")
        if controller.get("keys_accounts_surface_id") != "keys_accounts.ui.credential_reference_selector":
            _issue(issues, "KEYS/ACCOUNTS surface id mismatch")
        for index, row in enumerate(rows):
            row_map = _mapping(row)
            cap = str(row_map.get("capability_id") or "")
            controller_caps.add(cap)
            if not cap:
                _issue(issues, f"controller row {index} missing capability_id")
            if row_map.get("install_status") != "INSTALLED_IN_SHARED_RUNTIME_CONTROLLER_MANIFEST":
                _issue(issues, f"controller row {index} install status mismatch")
            if row_map.get("confirmation_required") is not True:
                _issue(issues, f"controller row {index} must require confirmation")

    provider = _mapping(pkg.get("source_adapter_runtime_provider_execution_registry"))
    provider_caps: set[str] = set()
    if not provider:
        _issue(issues, "provider execution registry is required")
    else:
        rows = _list(provider.get("provider_registry_rows"))
        if provider.get("schema_version") != "source_adapter_runtime_provider_execution_registry_v1":
            _issue(issues, "provider execution registry schema_version mismatch")
        if provider.get("provider_adapter_count") != len(rows):
            _issue(issues, "provider adapter count mismatch")
        for index, row in enumerate(rows):
            row_map = _mapping(row)
            provider_caps.add(str(row_map.get("capability_id") or ""))
            if row_map.get("receipt_required") is not True:
                _issue(issues, f"provider row {index} must require receipt")
            if row_map.get("entrypoint_status") != "BOUND_TO_SHARED_PROVIDER_EXECUTION_REGISTRY":
                _issue(issues, f"provider row {index} entrypoint status mismatch")

    dispatch = _mapping(pkg.get("source_adapter_runtime_dispatch_table"))
    dispatch_caps: set[str] = set()
    dispatch_ids: set[str] = set()
    if not dispatch:
        _issue(issues, "runtime dispatch table is required")
    else:
        rows = _list(dispatch.get("runtime_dispatch_rows"))
        if dispatch.get("schema_version") != "source_adapter_runtime_dispatch_table_v1":
            _issue(issues, "runtime dispatch table schema_version mismatch")
        if dispatch.get("dispatch_row_count") != len(rows):
            _issue(issues, "runtime dispatch row count mismatch")
        for index, row in enumerate(rows):
            row_map = _mapping(row)
            cap = str(row_map.get("capability_id") or "")
            dispatch_caps.add(cap)
            row_id = str(row_map.get("runtime_dispatch_row_id") or "")
            if row_id in dispatch_ids:
                _issue(issues, f"duplicate runtime dispatch row id: {row_id}")
            dispatch_ids.add(row_id)
            if not _list(row_map.get("payload_fields")) or not _list(row_map.get("receipt_fields")):
                _issue(issues, f"dispatch row {index} missing payload or receipt fields")
            if row_map.get("dispatch_status") != "ROUTED_THROUGH_SHARED_RUNTIME_DISPATCH_TABLE":
                _issue(issues, f"dispatch row {index} status mismatch")
    if controller_caps != provider_caps or controller_caps != dispatch_caps:
        _issue(issues, "controller/provider/dispatch capability sets mismatch")

    ledger = _mapping(pkg.get("source_adapter_runtime_operator_approval_ledger"))
    if not ledger:
        _issue(issues, "operator approval ledger is required")
    else:
        rows = _list(ledger.get("approval_ledger_rows"))
        if ledger.get("schema_version") != "source_adapter_runtime_operator_approval_ledger_v1":
            _issue(issues, "operator approval ledger schema_version mismatch")
        if ledger.get("approval_count") != len(rows):
            _issue(issues, "operator approval count mismatch")
        ledger_caps = {str(_mapping(row).get("capability_id") or "") for row in rows}
        if ledger_caps != dispatch_caps:
            _issue(issues, "approval ledger capability set mismatch")

    seed_batch = _mapping(pkg.get("source_adapter_runtime_fixture_receipt_seed_batch"))
    if not seed_batch:
        _issue(issues, "fixture receipt seed batch is required")
    else:
        seeds = _list(seed_batch.get("fixture_receipt_seed_rows"))
        if seed_batch.get("schema_version") != "source_adapter_runtime_fixture_receipt_seed_batch_v1":
            _issue(issues, "fixture receipt seed batch schema_version mismatch")
        if seed_batch.get("fixture_receipt_seed_count") != len(seeds):
            _issue(issues, "fixture receipt seed count mismatch")

    priority = _mapping(pkg.get("source_adapter_priority_adapter_fixture_seed_bundle"))
    if not priority:
        _issue(issues, "priority adapter fixture seed bundle is required")
    else:
        seeds = _list(priority.get("priority_adapter_fixture_seeds"))
        if priority.get("schema_version") != "source_adapter_priority_adapter_fixture_seed_bundle_v1":
            _issue(issues, "priority adapter fixture seed bundle schema_version mismatch")
        if priority.get("priority_fixture_seed_count") != len(seeds):
            _issue(issues, "priority fixture seed count mismatch")
        if len(seeds) < 5:
            _issue(issues, "priority fixture seeds should cover at least five adapter families")

    smoke = _mapping(pkg.get("source_adapter_runtime_manual_live_smoke_execution_matrix"))
    if not smoke:
        _issue(issues, "manual/live smoke execution matrix is required")
    else:
        rows = _list(smoke.get("manual_live_smoke_execution_rows"))
        if smoke.get("schema_version") != "source_adapter_runtime_manual_live_smoke_execution_matrix_v1":
            _issue(issues, "manual/live smoke execution matrix schema_version mismatch")
        if smoke.get("manual_live_smoke_execution_count") != len(rows):
            _issue(issues, "manual/live smoke execution count mismatch")
        smoke_caps = {str(_mapping(row).get("capability_id") or "") for row in rows}
        if smoke_caps != dispatch_caps:
            _issue(issues, "manual/live smoke capability set mismatch")

    audit = _mapping(pkg.get("source_adapter_runtime_controller_provider_roadmap_audit"))
    if not audit:
        _issue(issues, "roadmap audit is required")
    else:
        if audit.get("schema_version") != "source_adapter_runtime_controller_provider_roadmap_audit_v1":
            _issue(issues, "roadmap audit schema_version mismatch")
        if set(audit.get("capability_ids") or []) != dispatch_caps:
            _issue(issues, "roadmap audit capability set mismatch")

    handoff = _mapping(pkg.get("source_adapter_runtime_controller_provider_final_handoff"))
    handoff_status = str(handoff.get("handoff_status") or "")
    if not handoff:
        _issue(issues, "final handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_runtime_controller_provider_final_handoff_v1":
            _issue(issues, "final handoff schema_version mismatch")
        if handoff_status != EXPECTED_HANDOFF:
            _issue(issues, "final handoff status mismatch")
        if handoff.get("ready_for_controller_runtime_dispatch") is not True:
            _issue(issues, "final handoff must be ready for controller runtime dispatch")
        if handoff.get("ready_for_operator_approved_manual_live_smoke") is not True:
            _issue(issues, "final handoff must be ready for manual/live smoke")

    verified = not issues
    return {
        "schema_version": SCHEMA_VERSION,
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_controller_provider_closeout_id": bridge_id,
        "capability_count": len(dispatch_caps),
        "controller_route_count": controller.get("controller_route_count", 0),
        "provider_adapter_count": provider.get("provider_adapter_count", 0),
        "dispatch_row_count": dispatch.get("dispatch_row_count", 0),
        "handoff_status": handoff_status,
    }


def main() -> None:
    from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
    from source_adapter_runtime_operator_acceptance_closeout import build_source_adapter_runtime_operator_acceptance_closeout
    from source_adapter_runtime_operator_acceptance_closeout_test import fixture_runtime_ui_provider_integration_bridge

    accepted = build_source_adapter_runtime_operator_acceptance_closeout(fixture_runtime_ui_provider_integration_bridge())
    package = build_source_adapter_runtime_controller_provider_closeout(accepted)
    verification = verify_source_adapter_runtime_controller_provider_closeout(package)
    if not verification["verified"]:
        raise SystemExit(verification)
    print("Source Adapter Runtime Controller Provider Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
