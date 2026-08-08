from __future__ import annotations

from typing import Any, Mapping, Sequence

from source_adapter_gui_controller_execution_bridge import DISPATCH_BATCH_STATUS, HANDOFF_STATUS, KEYS_ACCOUNTS_LABEL, ROUTE_REGISTRY_STATUS, SCHEMA_VERSION, STATUS

VERIFY_SCHEMA_VERSION = "source_adapter_gui_controller_execution_bridge_verifier_v1"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def verify_source_adapter_gui_controller_execution_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "unexpected GUI controller bridge schema"})
    if package.get("gui_controller_execution_bridge_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "GUI controller bridge status is not built"})
    registry = package.get("source_adapter_gui_controller_execution_route_registry") or {}
    batch = package.get("source_adapter_gui_controller_execution_dispatch_receipt_batch") or {}
    handoff = package.get("source_adapter_gui_controller_execution_bridge_handoff") or {}
    route_rows = _rows(registry, "route_registry_rows")
    dispatch_rows = _rows(batch, "gui_controller_dispatch_receipt_rows")
    if registry.get("route_registry_status") != ROUTE_REGISTRY_STATUS or len(route_rows) != 4:
        issues.append({"issue_id": "route_registry_not_ready", "severity": "error", "message": "expected four registered GUI/controller routes"})
    if batch.get("gui_controller_execution_dispatch_receipt_batch_status") != DISPATCH_BATCH_STATUS or len(dispatch_rows) != 5:
        issues.append({"issue_id": "dispatch_receipt_count_mismatch", "severity": "error", "message": "expected five GUI/controller dispatch receipts"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "handoff status is not ready"})
    if package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label changed"})
    for row in dispatch_rows:
        if row.get("dispatch_performed") is not True:
            issues.append({"issue_id": "dispatch_not_performed", "severity": "error", "message": "dispatch row was not performed"})
        if "raw_credential" in row or "secret" in row:
            issues.append({"issue_id": "secret_like_material_present", "severity": "error", "message": "secret-like material appeared in a GUI/controller dispatch row"})
    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "route_row_count": len(route_rows),
        "dispatch_receipt_row_count": len(dispatch_rows),
        "handoff_status": handoff.get("handoff_status"),
        "source_adapter_gui_controller_execution_bridge_id": package.get("source_adapter_gui_controller_execution_bridge_id"),
    }
