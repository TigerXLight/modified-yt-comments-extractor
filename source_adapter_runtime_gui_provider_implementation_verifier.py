from __future__ import annotations

from typing import Any, Mapping

from source_adapter_runtime_gui_provider_implementation import HANDOFF_STATUS, SCHEMA_VERSION, STATUS

VERIFIER_SCHEMA_VERSION = "source_adapter_runtime_gui_provider_implementation_verifier_v1"


def _rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _unique(values: list[str]) -> bool:
    return len(values) == len(set(values))


def verify_source_adapter_runtime_gui_provider_implementation(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "runtime GUI provider implementation schema was not recognised"})
    if package.get("runtime_gui_provider_implementation_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "runtime GUI provider implementation status is not built"})
    route_registry = package.get("source_adapter_runtime_gui_controller_route_registry") or {}
    provider_registry = package.get("source_adapter_runtime_provider_execution_registry") or {}
    credential_selector = package.get("source_adapter_keys_accounts_credential_reference_selector") or {}
    binding_matrix = package.get("source_adapter_runtime_controller_provider_binding_matrix") or {}
    dispatch_smoke = package.get("source_adapter_runtime_dispatch_smoke_receipt_batch") or {}
    handoff = package.get("source_adapter_runtime_gui_provider_implementation_handoff") or {}
    route_rows = _rows(route_registry.get("route_rows"))
    provider_rows = _rows(provider_registry.get("provider_rows"))
    binding_rows = _rows(binding_matrix.get("binding_rows"))
    receipt_rows = _rows(dispatch_smoke.get("dispatch_smoke_receipt_rows"))
    route_ids = [str(row.get("route_id")) for row in route_rows]
    provider_ids = [str(row.get("provider_execution_adapter_id")) for row in provider_rows]
    if route_registry.get("route_registry_status") != "SOURCE_ADAPTER_RUNTIME_GUI_CONTROLLER_ROUTES_REGISTERED" or len(route_rows) < 4:
        issues.append({"issue_id": "route_registry_not_ready", "severity": "error", "message": "runtime route registry is not ready"})
    if provider_registry.get("provider_registry_status") != "SOURCE_ADAPTER_RUNTIME_PROVIDER_EXECUTION_REGISTRY_ACTIVE" or len(provider_rows) < 4:
        issues.append({"issue_id": "provider_registry_not_ready", "severity": "error", "message": "runtime provider registry is not ready"})
    if credential_selector.get("credential_selector_status") != "KEYS_ACCOUNTS_CREDENTIAL_REFERENCE_SELECTOR_ACTIVE":
        issues.append({"issue_id": "credential_selector_not_ready", "severity": "error", "message": "KEYS/ACCOUNTS credential selector is not active"})
    if credential_selector.get("sidebar_label") != "KEYS/ACCOUNTS":
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    if binding_matrix.get("binding_matrix_status") != "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_BINDINGS_ACTIVE" or len(binding_rows) != len(route_rows):
        issues.append({"issue_id": "binding_matrix_not_ready", "severity": "error", "message": "controller/provider binding matrix is not ready"})
    if dispatch_smoke.get("dispatch_smoke_receipt_batch_status") != "SOURCE_ADAPTER_RUNTIME_DISPATCH_SMOKE_RECEIPTS_ACCEPTED" or len(receipt_rows) != len(provider_rows):
        issues.append({"issue_id": "dispatch_smoke_receipts_not_ready", "severity": "error", "message": "runtime dispatch smoke receipts are not accepted"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "runtime GUI provider implementation handoff is not ready"})
    if not _unique(route_ids):
        issues.append({"issue_id": "duplicate_route_ids", "severity": "error", "message": "route ids are not unique"})
    if not _unique(provider_ids):
        issues.append({"issue_id": "duplicate_provider_ids", "severity": "error", "message": "provider ids are not unique"})
    for row in receipt_rows:
        if row.get("missing_receipt_fields"):
            issues.append({"issue_id": "missing_receipt_fields", "severity": "error", "message": str(row.get("runtime_dispatch_receipt_id"))})
        if row.get("execution_mode") != "dry_run":
            issues.append({"issue_id": "unexpected_smoke_execution_mode", "severity": "error", "message": str(row.get("runtime_dispatch_receipt_id"))})
    verified = not issues
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_gui_provider_implementation_id": package.get("source_adapter_runtime_gui_provider_implementation_id"),
        "route_count": len(route_rows),
        "provider_count": len(provider_rows),
        "binding_count": len(binding_rows),
        "dispatch_smoke_receipt_count": len(receipt_rows),
        "handoff_status": handoff.get("handoff_status"),
    }
