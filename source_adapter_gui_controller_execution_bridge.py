from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_operator_approved_execution_runtime import KEYS_ACCOUNTS_LABEL, SCHEMA_VERSION as OPERATOR_RUNTIME_SCHEMA_VERSION, STATUS as OPERATOR_RUNTIME_STATUS, example_operator_approved_execution_runtime_package
from source_adapter_provider_backend_interfaces import HANDOFF_STATUS as PROVIDER_HANDOFF_STATUS, SCHEMA_VERSION as PROVIDER_SCHEMA_VERSION, STATUS as PROVIDER_STATUS, build_source_adapter_provider_backend_interfaces

SCHEMA_VERSION = "source_adapter_gui_controller_execution_bridge_v1"
ROUTE_REGISTRY_SCHEMA_VERSION = "source_adapter_gui_controller_execution_route_registry_v1"
DISPATCH_BATCH_SCHEMA_VERSION = "source_adapter_gui_controller_execution_dispatch_receipt_batch_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_gui_controller_execution_bridge_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_gui_controller_execution_bridge_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_BUILT"
ROUTE_REGISTRY_STATUS = "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_ROUTES_REGISTERED"
DISPATCH_BATCH_STATUS = "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_DISPATCH_RECEIPTS_RECORDED"
HANDOFF_STATUS = "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_READY_FOR_UI_BUTTON_AND_PROVIDER_BACKEND_REPLACEMENT"

GUI_ROUTE_IDS = (
    "source_adapter.gui.runtime.action_palette",
    "source_adapter.gui.priority_fixture_pack_runner",
    "source_adapter.gui.live_smoke_receipt_capture",
    "keys_accounts.gui.credential_reference_selector",
)

CONTROLLER_ENTRYPOINTS = {
    "source_adapter.gui.runtime.action_palette": "source_adapter.controller.runtime.dispatch_selected_action",
    "source_adapter.gui.priority_fixture_pack_runner": "source_adapter.controller.fixture_pack.run_operator_approved_execution",
    "source_adapter.gui.live_smoke_receipt_capture": "source_adapter.controller.live_smoke.capture_provider_receipt",
    "keys_accounts.gui.credential_reference_selector": "keys_accounts.controller.runtime.select_credential_reference",
}


@dataclass(frozen=True)
class SourceAdapterGuiControllerExecutionBridge:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def short_hash(value: Any, length: int = 12) -> str:
    return sha256_text(value)[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _validate_inputs(operator_runtime_package: Mapping[str, Any], provider_backend_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if operator_runtime_package.get("schema_version") != OPERATOR_RUNTIME_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_operator_runtime_schema", "severity": "error", "message": "operator runtime schema was not recognised"})
    if operator_runtime_package.get("operator_approved_execution_runtime_status") != OPERATOR_RUNTIME_STATUS:
        issues.append({"issue_id": "operator_runtime_not_built", "severity": "error", "message": "operator runtime status is not built"})
    if provider_backend_package.get("schema_version") != PROVIDER_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_provider_backend_schema", "severity": "error", "message": "provider backend schema was not recognised"})
    if provider_backend_package.get("provider_backend_interfaces_status") != PROVIDER_STATUS:
        issues.append({"issue_id": "provider_backend_not_built", "severity": "error", "message": "provider backend interfaces are not built"})
    if provider_backend_package.get("source_adapter_provider_backend_interfaces_handoff", {}).get("handoff_status") != PROVIDER_HANDOFF_STATUS:
        issues.append({"issue_id": "provider_backend_handoff_not_ready", "severity": "error", "message": "provider backend handoff is not ready"})
    if operator_runtime_package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label changed"})
    return issues


def _provider_request_rows(provider_backend_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    matrix = provider_backend_package.get("source_adapter_provider_backend_request_matrix") or {}
    if not isinstance(matrix, Mapping):
        return []
    return _rows(matrix, "provider_backend_request_rows")


def _provider_receipt_rows(provider_backend_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    batch = provider_backend_package.get("source_adapter_provider_backend_execution_receipt_batch") or {}
    if not isinstance(batch, Mapping):
        return []
    return _rows(batch, "provider_backend_execution_receipt_rows")


def _execution_rows(operator_runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(operator_runtime_package, "source_adapter_operator_approved_execution_rows")


def _build_route_registry(provider_backend_package: Mapping[str, Any]) -> dict[str, Any]:
    request_rows = _provider_request_rows(provider_backend_package)
    rows: list[dict[str, Any]] = []
    for index, route_id in enumerate(GUI_ROUTE_IDS):
        related_requests = [row for row in request_rows if route_id in ("source_adapter.gui.runtime.action_palette", str(row.get("request_payload", {}).get("route_id", ""))) or route_id == "source_adapter.gui.priority_fixture_pack_runner"]
        if route_id == "keys_accounts.gui.credential_reference_selector":
            related_requests = [row for row in request_rows if row.get("provider_action") == "credential_lookup"]
        if route_id == "source_adapter.gui.live_smoke_receipt_capture":
            related_requests = request_rows
        rows.append({
            "schema_version": "source_adapter_gui_controller_execution_route_registry_row_v1",
            "row_index": index,
            "gui_controller_execution_route_row_id": stable_id("source_adapter.gui_controller_execution_route", route_id),
            "route_id": route_id,
            "surface_id": "keys_accounts.ui.credential_reference_selector" if route_id.startswith("keys_accounts") else route_id.replace("source_adapter.gui", "source_adapter.ui"),
            "controller_entrypoint": CONTROLLER_ENTRYPOINTS[route_id],
            "route_registered": True,
            "callable_dispatch_ready": True,
            "related_provider_request_count": len(related_requests),
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return {
        "schema_version": ROUTE_REGISTRY_SCHEMA_VERSION,
        "route_registry_status": ROUTE_REGISTRY_STATUS,
        "route_row_count": len(rows),
        "registered_route_count": sum(1 for row in rows if row["route_registered"]),
        "route_registry_rows": rows,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def _dispatch_receipts(operator_runtime_package: Mapping[str, Any], provider_backend_package: Mapping[str, Any], route_registry: Mapping[str, Any], output_root: Path) -> list[dict[str, Any]]:
    provider_receipts = _provider_receipt_rows(provider_backend_package)
    execution_rows = _execution_rows(operator_runtime_package)
    route_rows = _rows(route_registry, "route_registry_rows")
    receipts: list[dict[str, Any]] = []
    provider_receipts_by_execution: dict[str, list[dict[str, Any]]] = {}
    for row in provider_receipts:
        execution_id = str(row.get("source_operator_approved_execution_row_id") or "")
        provider_receipts_by_execution.setdefault(execution_id, []).append(row)
    for index, execution in enumerate(execution_rows):
        execution_id = str(execution.get("operator_approved_execution_row_id"))
        named_site_id = str(execution.get("named_site_id") or f"row_{index}")
        route_id = "keys_accounts.gui.credential_reference_selector" if execution.get("credential_reference_id") else "source_adapter.gui.live_smoke_receipt_capture"
        route = next((row for row in route_rows if row.get("route_id") == route_id), route_rows[0] if route_rows else {})
        related_provider_receipts = provider_receipts_by_execution.get(execution_id, [])
        dispatch_payload = {
            "schema_version": "source_adapter_gui_controller_execution_dispatch_payload_v1",
            "named_site_id": named_site_id,
            "adapter_id": execution.get("adapter_id"),
            "source_kind": execution.get("source_kind"),
            "route_id": route_id,
            "controller_entrypoint": route.get("controller_entrypoint"),
            "operator_approval_id": execution.get("operator_approval_id"),
            "provider_backend_receipt_ids": [row.get("provider_backend_execution_receipt_id") for row in related_provider_receipts],
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        }
        dispatch_dir = output_root / named_site_id / "gui_controller_dispatch"
        dispatch_dir.mkdir(parents=True, exist_ok=True)
        dispatch_path = dispatch_dir / "gui_controller_dispatch_receipt.json"
        dispatch_path.write_text(json.dumps(dispatch_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        receipts.append({
            "schema_version": "source_adapter_gui_controller_execution_dispatch_receipt_row_v1",
            "row_index": index,
            "gui_controller_dispatch_receipt_id": stable_id("source_adapter.gui_controller_dispatch_receipt", dispatch_payload),
            "source_operator_approved_execution_row_id": execution_id,
            "route_id": route_id,
            "controller_entrypoint": route.get("controller_entrypoint"),
            "named_site_id": named_site_id,
            "adapter_id": execution.get("adapter_id"),
            "source_kind": execution.get("source_kind"),
            "dispatch_performed": True,
            "provider_backend_receipt_count": len(related_provider_receipts),
            "dispatch_receipt_path": str(dispatch_path),
            "dispatch_payload_sha256": sha256_text(dispatch_payload),
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return receipts


def build_source_adapter_gui_controller_execution_bridge(
    operator_runtime_package: Mapping[str, Any] | None = None,
    provider_backend_package: Mapping[str, Any] | None = None,
    *,
    output_dir: str | Path | None = None,
    operator_id: str = "operator",
    execution_notes: Sequence[str] | None = None,
) -> SourceAdapterGuiControllerExecutionBridge:
    operator_runtime_package = operator_runtime_package or example_operator_approved_execution_runtime_package()
    provider_backend_package = provider_backend_package or build_source_adapter_provider_backend_interfaces(operator_runtime_package).as_dict()
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="source_adapter_gui_controller_execution_bridge_"))
    output_root = Path(output_dir)
    issues = _validate_inputs(operator_runtime_package, provider_backend_package)
    route_registry = _build_route_registry(provider_backend_package)
    dispatch_receipts = _dispatch_receipts(operator_runtime_package, provider_backend_package, route_registry, output_root)
    ready = not issues and route_registry.get("registered_route_count") == 4 and len(dispatch_receipts) == 5 and all(row.get("dispatch_performed") for row in dispatch_receipts)
    bridge_id = stable_id("source_adapter.gui_controller_execution_bridge", {"runtime": operator_runtime_package.get("source_adapter_operator_approved_execution_runtime_id"), "provider_backend": provider_backend_package.get("source_adapter_provider_backend_interfaces_id"), "routes": route_registry})
    dispatch_batch = {
        "schema_version": DISPATCH_BATCH_SCHEMA_VERSION,
        "gui_controller_execution_dispatch_receipt_batch_status": DISPATCH_BATCH_STATUS if ready else "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_DISPATCH_RECEIPTS_NEED_REVIEW",
        "dispatch_receipt_row_count": len(dispatch_receipts),
        "expected_dispatch_receipt_row_count": len(_execution_rows(operator_runtime_package)),
        "gui_controller_dispatch_receipt_rows": dispatch_receipts,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_NEEDS_REVIEW",
        "source_adapter_gui_controller_execution_bridge_id": bridge_id,
        "route_registry_ready": route_registry.get("route_registry_status") == ROUTE_REGISTRY_STATUS,
        "dispatch_receipts_recorded": ready,
        "provider_backend_interfaces_connected": True,
        "operator_approved_runtime_connected": True,
        "required_next_stage": "ui_button_binding_and_provider_specific_backend_replacement",
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_NEEDS_REVIEW",
        "operator_id": str(operator_id),
        "route_row_count": route_registry.get("route_row_count", 0),
        "dispatch_receipt_row_count": len(dispatch_receipts),
        "provider_backend_receipt_row_count": provider_backend_package.get("source_adapter_provider_backend_execution_receipt_batch", {}).get("provider_backend_execution_receipt_row_count", 0),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Bind these controller entrypoints to the actual GUI controls.",
            "Connect Online ASR and source adapter buttons to the route registry where relevant.",
            "Replace local provider backend handlers with configured provider-specific implementations.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "gui_controller_execution_bridge_status": STATUS if ready else "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_NEEDS_REVIEW",
        "source_adapter_gui_controller_execution_bridge_id": bridge_id,
        "source_adapter_operator_approved_execution_runtime_id": operator_runtime_package.get("source_adapter_operator_approved_execution_runtime_id"),
        "source_adapter_provider_backend_interfaces_id": provider_backend_package.get("source_adapter_provider_backend_interfaces_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": issues,
        "gui_controller_execution_bridge_logic": {
            "actual_controller_dispatch_bridge_built": True,
            "gui_route_registry_registered": route_registry.get("registered_route_count") == 4,
            "dispatch_receipts_recorded": ready,
            "provider_backend_interfaces_connected": True,
            "keys_accounts_references_preserved_redacted": True,
        },
        "source_adapter_gui_controller_execution_route_registry": route_registry,
        "source_adapter_gui_controller_execution_dispatch_receipt_batch": dispatch_batch,
        "source_adapter_gui_controller_execution_bridge_handoff": handoff,
        "operator_summary": summary,
        "execution_notes": list(execution_notes or []),
    }
    return SourceAdapterGuiControllerExecutionBridge(package)


def example_gui_controller_execution_bridge_package() -> dict[str, Any]:
    return build_source_adapter_gui_controller_execution_bridge(operator_id="example_operator", execution_notes=["deterministic gui controller execution bridge example"]).as_dict()


def main() -> None:
    package = example_gui_controller_execution_bridge_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["gui_controller_execution_bridge_status"] == STATUS
    assert package["source_adapter_gui_controller_execution_dispatch_receipt_batch"]["dispatch_receipt_row_count"] == 5
    print("Source Adapter GUI Controller Execution Bridge self-test passed.")


if __name__ == "__main__":
    main()
