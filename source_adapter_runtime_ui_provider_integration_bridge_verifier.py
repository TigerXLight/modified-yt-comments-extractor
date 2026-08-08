from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_runtime_ui_provider_integration_bridge_verifier_v1"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_runtime_ui_provider_integration_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_runtime_ui_provider_integration_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_runtime_ui_provider_integration_bridge_v1")
    if pkg.get("runtime_ui_provider_integration_status") != "SOURCE_ADAPTER_RUNTIME_UI_PROVIDER_INTEGRATIONS_BUILT":
        _issue(issues, "runtime_ui_provider_integration_status must be SOURCE_ADAPTER_RUNTIME_UI_PROVIDER_INTEGRATIONS_BUILT")
    bridge_id = str(pkg.get("source_adapter_runtime_ui_provider_integration_bridge_id") or "")
    if not bridge_id:
        _issue(issues, "source_adapter_runtime_ui_provider_integration_bridge_id is required")
    input_id = str(pkg.get("source_adapter_runtime_receipt_review_bridge_id") or "")
    if not input_id:
        _issue(issues, "source_adapter_runtime_receipt_review_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified UI/provider integration bridge output")

    batch = pkg.get("source_adapter_runtime_ui_provider_integration_batch")
    if not isinstance(batch, Mapping):
        _issue(issues, "source_adapter_runtime_ui_provider_integration_batch is required")
        rows = []
    else:
        if batch.get("schema_version") != "source_adapter_runtime_ui_provider_integration_batch_v1":
            _issue(issues, "integration batch schema_version mismatch")
        rows = batch.get("runtime_ui_provider_integration_rows")
        if not isinstance(rows, list) or not rows:
            _issue(issues, "integration batch must contain runtime_ui_provider_integration_rows")
            rows = []
        if batch.get("integrated_capability_count") != len(rows):
            _issue(issues, "integrated capability count mismatch")

    seen_capabilities: set[str] = set()
    ui_surfaces: set[str] = set()
    provider_surfaces: set[str] = set()
    runtime_actions: set[str] = set()
    receipt_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            _issue(issues, f"integration rows[{index}] must be an object")
            continue
        capability_id = str(row.get("capability_id") or "")
        if not capability_id:
            _issue(issues, f"integration rows[{index}] missing capability_id")
        if capability_id in seen_capabilities:
            _issue(issues, f"duplicate integrated capability_id: {capability_id}")
        seen_capabilities.add(capability_id)
        if row.get("integration_status") != "BOUND_TO_SHARED_UI_PROVIDER_SURFACE":
            _issue(issues, f"integration rows[{index}] status mismatch")
        ui_surface = str(row.get("ui_surface_id") or "")
        provider_surface = str(row.get("provider_surface_id") or "")
        if not ui_surface:
            _issue(issues, f"integration rows[{index}] missing ui_surface_id")
        if not provider_surface:
            _issue(issues, f"integration rows[{index}] missing provider_surface_id")
        ui_surfaces.add(ui_surface)
        provider_surfaces.add(provider_surface)
        action_ids = row.get("runtime_action_ids")
        if not isinstance(action_ids, list) or not action_ids:
            _issue(issues, f"integration rows[{index}] missing runtime_action_ids")
        else:
            runtime_actions.update(str(item) for item in action_ids)
        row_receipts = row.get("runtime_action_receipt_ids")
        if not isinstance(row_receipts, list) or not row_receipts:
            _issue(issues, f"integration rows[{index}] missing runtime_action_receipt_ids")
        else:
            receipt_ids.update(str(item) for item in row_receipts)

    index_doc = pkg.get("source_adapter_runtime_ui_provider_binding_index")
    if not isinstance(index_doc, Mapping):
        _issue(issues, "source_adapter_runtime_ui_provider_binding_index is required")
    else:
        if index_doc.get("schema_version") != "source_adapter_runtime_ui_provider_binding_index_v1":
            _issue(issues, "binding index schema_version mismatch")
        if index_doc.get("binding_status") != "SOURCE_ADAPTER_RUNTIME_READY_FOR_OPERATOR_ACCEPTANCE":
            _issue(issues, "binding index status mismatch")
        if set(index_doc.get("integrated_capability_ids") or []) != seen_capabilities:
            _issue(issues, "binding index integrated_capability_ids mismatch")
        if set(index_doc.get("ui_surface_ids") or []) != ui_surfaces:
            _issue(issues, "binding index ui_surface_ids mismatch")
        if set(index_doc.get("provider_surface_ids") or []) != provider_surfaces:
            _issue(issues, "binding index provider_surface_ids mismatch")
        if set(index_doc.get("runtime_action_ids") or []) != runtime_actions:
            _issue(issues, "binding index runtime_action_ids mismatch")
        if set(index_doc.get("runtime_action_receipt_ids") or []) != receipt_ids:
            _issue(issues, "binding index runtime_action_receipt_ids mismatch")

    handoff = pkg.get("source_adapter_runtime_operator_acceptance_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_runtime_operator_acceptance_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_runtime_operator_acceptance_handoff_v1":
            _issue(issues, "operator acceptance handoff schema_version mismatch")
        if handoff.get("handoff_status") != "SOURCE_ADAPTER_RUNTIME_READY_FOR_OPERATOR_ACCEPTANCE":
            _issue(issues, "operator acceptance handoff status mismatch")
        if handoff.get("required_next_stage") != "source_adapter_runtime_operator_acceptance":
            _issue(issues, "operator acceptance handoff required_next_stage mismatch")
        if handoff.get("ready_for_operator_acceptance") is not True:
            _issue(issues, "operator acceptance handoff must be ready")
        if set(handoff.get("integrated_capability_ids") or []) != seen_capabilities:
            _issue(issues, "operator acceptance handoff capability mismatch")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_ui_provider_integration_bridge_id": bridge_id,
        "source_adapter_runtime_receipt_review_bridge_id": input_id,
        "integrated_capability_count": len(rows),
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
