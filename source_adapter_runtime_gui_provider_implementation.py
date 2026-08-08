from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_next_roadmap_work_order_execution_closeout import (
    HANDOFF_STATUS as WORK_ORDER_HANDOFF_STATUS,
    STATUS as WORK_ORDER_STATUS,
    example_next_roadmap_work_order_execution_closeout_package,
)

SCHEMA_VERSION = "source_adapter_runtime_gui_provider_implementation_v1"
ROUTE_REGISTRY_SCHEMA_VERSION = "source_adapter_runtime_gui_controller_route_registry_v1"
PROVIDER_REGISTRY_SCHEMA_VERSION = "source_adapter_runtime_provider_execution_registry_v1"
CREDENTIAL_SELECTOR_SCHEMA_VERSION = "source_adapter_keys_accounts_credential_reference_selector_v1"
BINDING_MATRIX_SCHEMA_VERSION = "source_adapter_runtime_controller_provider_binding_matrix_v1"
DISPATCH_SMOKE_SCHEMA_VERSION = "source_adapter_runtime_dispatch_smoke_receipt_batch_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_runtime_gui_provider_implementation_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_runtime_gui_provider_implementation_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_RUNTIME_GUI_PROVIDER_IMPLEMENTATION_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_RUNTIME_GUI_PROVIDER_IMPLEMENTATION_READY_FOR_FIXTURE_PACK_EXECUTION"
BLOCKED_STATUS = "SOURCE_ADAPTER_RUNTIME_GUI_PROVIDER_IMPLEMENTATION_NEEDS_REVIEW"

DRY_RUN_MODE = "dry_run"
OPERATOR_APPROVED_MODE = "operator_approved_manual_smoke"


@dataclass(frozen=True)
class SourceAdapterRuntimeGuiProviderImplementation:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def short_hash(value: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def as_list(value: Any, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{label} must be a list")
    return list(value)


def _strings(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in output:
            output.append(text)
    return output


def _validate_work_order_package(work_order_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if work_order_package.get("schema_version") != "source_adapter_next_roadmap_work_order_execution_closeout_v1":
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "next roadmap work-order execution schema was not recognised"})
    if work_order_package.get("next_roadmap_work_order_execution_closeout_status") != WORK_ORDER_STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "next roadmap work-order execution closeout is not built"})
    if int(work_order_package.get("issue_count", 0) or 0) != 0:
        issues.append({"issue_id": "upstream_issues_present", "severity": "error", "message": "next roadmap work-order execution contains upstream issues"})
    handoff = work_order_package.get("source_adapter_next_roadmap_execution_ready_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != WORK_ORDER_HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "next roadmap execution handoff is not ready"})
    for key in (
        "source_adapter_runtime_gui_controller_hardening_manifest",
        "source_adapter_provider_execution_activation_manifest",
        "source_adapter_priority_fixture_pack_authoring_manifest",
        "source_adapter_live_smoke_receipt_capture_manifest",
        "source_adapter_regular_regression_promotion_manifest",
    ):
        if not isinstance(work_order_package.get(key), Mapping):
            issues.append({"issue_id": f"missing_{key}", "severity": "error", "message": f"{key} is missing"})
    return issues


class RuntimeControllerRegistry:
    """Small dispatch registry used by GUI/controller tests and CLI fixture runs."""

    def __init__(self, route_rows: Sequence[Mapping[str, Any]], provider_rows: Sequence[Mapping[str, Any]]):
        self.routes = {str(row.get("route_id")): dict(row) for row in route_rows if row.get("route_id")}
        self.providers = {str(row.get("provider_execution_adapter_id")): dict(row) for row in provider_rows if row.get("provider_execution_adapter_id")}

    def register_route(self, route_row: Mapping[str, Any]) -> None:
        route_id = str(route_row.get("route_id") or "").strip()
        if not route_id:
            raise ValueError("route_id is required")
        self.routes[route_id] = dict(route_row)

    def register_provider(self, provider_row: Mapping[str, Any]) -> None:
        provider_id = str(provider_row.get("provider_execution_adapter_id") or "").strip()
        if not provider_id:
            raise ValueError("provider_execution_adapter_id is required")
        self.providers[provider_id] = dict(provider_row)

    def dispatch(
        self,
        *,
        route_id: str,
        provider_execution_adapter_id: str,
        payload: Mapping[str, Any],
        execution_mode: str = DRY_RUN_MODE,
        operator_approval_id: str = "operator.approval.local_fixture",
    ) -> dict[str, Any]:
        route = self.routes.get(route_id)
        if route is None:
            raise KeyError(f"route not registered: {route_id}")
        provider = self.providers.get(provider_execution_adapter_id)
        if provider is None:
            raise KeyError(f"provider not registered: {provider_execution_adapter_id}")
        expected_fields = [str(field) for field in provider.get("expected_receipt_fields") or []]
        missing_fields = [field for field in expected_fields if field not in payload]
        receipt_payload = {field: payload.get(field, f"fixture_{field}") for field in expected_fields}
        receipt_seed = {
            "route_id": route_id,
            "provider_execution_adapter_id": provider_execution_adapter_id,
            "execution_mode": execution_mode,
            "payload": receipt_payload,
        }
        return {
            "schema_version": "source_adapter_runtime_dispatch_receipt_v1",
            "runtime_dispatch_receipt_id": stable_id("source_adapter.runtime_dispatch_receipt", receipt_seed),
            "route_id": route_id,
            "controller_entrypoint": route.get("controller_entrypoint"),
            "surface_id": route.get("surface_id"),
            "provider_execution_adapter_id": provider_execution_adapter_id,
            "capability_id": provider.get("capability_id"),
            "execution_mode": execution_mode,
            "operator_approval_id": operator_approval_id,
            "payload_sha256": hashlib.sha256(canonical_json(receipt_payload).encode("utf-8")).hexdigest(),
            "receipt_role": route.get("receipt_role"),
            "expected_receipt_fields": expected_fields,
            "missing_receipt_fields": missing_fields,
            "field_presence": {field: field in payload for field in expected_fields},
            "receipt_payload": receipt_payload,
            "receipt_status": "SOURCE_ADAPTER_RUNTIME_DISPATCH_RECEIPT_RECORDED" if not missing_fields else "SOURCE_ADAPTER_RUNTIME_DISPATCH_RECEIPT_RECORDED_WITH_MISSING_FIELDS",
        }


def _route_rows(work_order_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    manifest = work_order_package.get("source_adapter_runtime_gui_controller_hardening_manifest") or {}
    return [dict(row) for row in as_list(manifest.get("route_rows"), "route_rows") if isinstance(row, Mapping)]


def _provider_rows(work_order_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    manifest = work_order_package.get("source_adapter_provider_execution_activation_manifest") or {}
    return [dict(row) for row in as_list(manifest.get("provider_activation_rows"), "provider_activation_rows") if isinstance(row, Mapping)]


def _build_route_registry(work_order_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, route in enumerate(_route_rows(work_order_package)):
        route_id = str(route.get("route_id") or "").strip()
        required_inputs = _strings(route.get("required_inputs") or [])
        rows.append({
            "schema_version": "source_adapter_runtime_gui_controller_route_registry_row_v1",
            "row_index": index,
            "runtime_route_registry_row_id": stable_id("source_adapter.runtime_route_registry", {"route_id": route_id, "index": index}),
            "route_id": route_id,
            "surface_id": route.get("surface_id"),
            "controller_entrypoint": route.get("controller_entrypoint"),
            "required_inputs": required_inputs,
            "receipt_role": route.get("receipt_role"),
            "sidebar_label": route.get("sidebar_label", ""),
            "dispatch_modes": [DRY_RUN_MODE, OPERATOR_APPROVED_MODE],
            "route_status": "REGISTERED_FOR_RUNTIME_DISPATCH" if not issues else "NEEDS_REGISTRATION_REVIEW",
        })
    return {
        "schema_version": ROUTE_REGISTRY_SCHEMA_VERSION,
        "route_registry_status": "SOURCE_ADAPTER_RUNTIME_GUI_CONTROLLER_ROUTES_REGISTERED" if rows and not issues else "SOURCE_ADAPTER_RUNTIME_GUI_CONTROLLER_ROUTES_NEED_REVIEW",
        "route_count": len(rows),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "route_rows": rows,
    }


def _build_provider_registry(work_order_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, provider in enumerate(_provider_rows(work_order_package)):
        provider_id = str(provider.get("provider_execution_adapter_id") or "").strip()
        expected_fields = _strings(provider.get("expected_receipt_fields") or [])
        rows.append({
            "schema_version": "source_adapter_runtime_provider_execution_registry_row_v1",
            "row_index": index,
            "runtime_provider_registry_row_id": stable_id("source_adapter.runtime_provider_registry", {"provider": provider_id, "index": index}),
            "provider_execution_adapter_id": provider_id,
            "capability_id": provider.get("capability_id"),
            "supported_execution_modes": _strings(provider.get("execution_modes") or [DRY_RUN_MODE, OPERATOR_APPROVED_MODE]),
            "expected_receipt_fields": expected_fields,
            "credential_surface": provider.get("credential_surface"),
            "receipt_capture_required": bool(provider.get("receipt_capture_required", True)),
            "handler_name": f"handle_{provider_id.replace('.', '_')}",
            "provider_status": "ACTIVE_FOR_RUNTIME_DISPATCH" if not issues else "NEEDS_PROVIDER_REVIEW",
        })
    return {
        "schema_version": PROVIDER_REGISTRY_SCHEMA_VERSION,
        "provider_registry_status": "SOURCE_ADAPTER_RUNTIME_PROVIDER_EXECUTION_REGISTRY_ACTIVE" if rows and not issues else "SOURCE_ADAPTER_RUNTIME_PROVIDER_EXECUTION_REGISTRY_NEEDS_REVIEW",
        "provider_count": len(rows),
        "provider_rows": rows,
    }


def _build_credential_selector(route_registry: Mapping[str, Any], provider_registry: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    key_routes = [row for row in as_list(route_registry.get("route_rows"), "route_rows") if isinstance(row, Mapping) and str(row.get("route_id", "")).startswith("keys_accounts")]
    provider_rows = [row for row in as_list(provider_registry.get("provider_rows"), "provider_rows") if isinstance(row, Mapping) and row.get("credential_surface") == "keys_accounts.ui.credential_reference_selector"]
    selector_rows: list[dict[str, Any]] = []
    for index, provider in enumerate(provider_rows):
        selector_rows.append({
            "schema_version": "source_adapter_keys_accounts_credential_reference_selector_row_v1",
            "row_index": index,
            "credential_selector_row_id": stable_id("keys_accounts.credential_selector", {"provider": provider.get("provider_execution_adapter_id"), "index": index}),
            "provider_execution_adapter_id": provider.get("provider_execution_adapter_id"),
            "capability_id": provider.get("capability_id"),
            "credential_surface": "keys_accounts.ui.credential_reference_selector",
            "selector_inputs": ["provider_id", "credential_reference_id", "purpose"],
            "receipt_fields": ["credential_reference_id", "provider_id", "lookup_status", "redacted_reference_hash"],
            "selector_status": "READY_FOR_REFERENCE_SELECTION" if not issues else "NEEDS_SELECTOR_REVIEW",
        })
    return {
        "schema_version": CREDENTIAL_SELECTOR_SCHEMA_VERSION,
        "credential_selector_status": "KEYS_ACCOUNTS_CREDENTIAL_REFERENCE_SELECTOR_ACTIVE" if key_routes and selector_rows and not issues else "KEYS_ACCOUNTS_CREDENTIAL_REFERENCE_SELECTOR_NEEDS_REVIEW",
        "sidebar_label": "KEYS/ACCOUNTS",
        "surface_id": "keys_accounts.ui.credential_reference_selector",
        "route_count": len(key_routes),
        "provider_reference_count": len(selector_rows),
        "reference_only_receipts": True,
        "selector_rows": selector_rows,
    }


def _provider_id_for_route(route: Mapping[str, Any], provider_rows: Sequence[Mapping[str, Any]]) -> str:
    route_id = str(route.get("route_id") or "")
    if route_id.startswith("keys_accounts"):
        for provider in provider_rows:
            if provider.get("provider_execution_adapter_id") == "keys_accounts.provider.credential_reference_lookup":
                return str(provider.get("provider_execution_adapter_id"))
    for provider in provider_rows:
        if provider.get("provider_execution_adapter_id") == "source_adapter.provider.archive_submit":
            return str(provider.get("provider_execution_adapter_id"))
    return str(provider_rows[0].get("provider_execution_adapter_id")) if provider_rows else ""


def _build_binding_matrix(route_registry: Mapping[str, Any], provider_registry: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    routes = [dict(row) for row in as_list(route_registry.get("route_rows"), "route_rows") if isinstance(row, Mapping)]
    providers = [dict(row) for row in as_list(provider_registry.get("provider_rows"), "provider_rows") if isinstance(row, Mapping)]
    rows: list[dict[str, Any]] = []
    for index, route in enumerate(routes):
        provider_id = _provider_id_for_route(route, providers)
        provider = next((row for row in providers if row.get("provider_execution_adapter_id") == provider_id), {})
        rows.append({
            "schema_version": "source_adapter_runtime_controller_provider_binding_row_v1",
            "row_index": index,
            "controller_provider_binding_row_id": stable_id("source_adapter.controller_provider_binding", {"route": route.get("route_id"), "provider": provider_id, "index": index}),
            "route_id": route.get("route_id"),
            "surface_id": route.get("surface_id"),
            "controller_entrypoint": route.get("controller_entrypoint"),
            "provider_execution_adapter_id": provider_id,
            "capability_id": provider.get("capability_id"),
            "binding_status": "BOUND_FOR_RUNTIME_DISPATCH" if provider_id and not issues else "NEEDS_BINDING_REVIEW",
        })
    return {
        "schema_version": BINDING_MATRIX_SCHEMA_VERSION,
        "binding_matrix_status": "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_BINDINGS_ACTIVE" if rows and not issues else "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_BINDINGS_NEED_REVIEW",
        "binding_count": len(rows),
        "binding_rows": rows,
    }


def _payload_for_provider(provider: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in provider.get("expected_receipt_fields") or []:
        key = str(field)
        if key == "redacted_reference_hash":
            payload[key] = hashlib.sha256(b"credential-reference-fixture").hexdigest()
        elif key.endswith("_count"):
            payload[key] = 1
        elif key.endswith("status") or key == "lookup_status" or key == "submission_status" or key == "upload_status" or key == "publish_status":
            payload[key] = "fixture_accepted"
        elif key.endswith("_refs") or key == "submitted_artifacts":
            payload[key] = ["fixture_artifact_ref"]
        elif key.endswith("sha256"):
            payload[key] = hashlib.sha256(f"fixture:{key}".encode("utf-8")).hexdigest()
        else:
            payload[key] = f"fixture_{key}"
    return payload


def _route_id_for_provider(provider: Mapping[str, Any], route_registry: Mapping[str, Any]) -> str:
    if provider.get("provider_execution_adapter_id") == "keys_accounts.provider.credential_reference_lookup":
        return "keys_accounts.gui.credential_reference_selector"
    routes = [row for row in as_list(route_registry.get("route_rows"), "route_rows") if isinstance(row, Mapping)]
    preferred = next((row for row in routes if row.get("route_id") == "source_adapter.gui.runtime.action_palette"), None)
    return str((preferred or routes[0]).get("route_id")) if routes else ""


def _build_dispatch_smoke_receipts(route_registry: Mapping[str, Any], provider_registry: Mapping[str, Any], operator_id: str, issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    provider_rows = [dict(row) for row in as_list(provider_registry.get("provider_rows"), "provider_rows") if isinstance(row, Mapping)]
    dispatcher = RuntimeControllerRegistry(
        [dict(row) for row in as_list(route_registry.get("route_rows"), "route_rows") if isinstance(row, Mapping)],
        provider_rows,
    )
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, provider in enumerate(provider_rows):
            route_id = _route_id_for_provider(provider, route_registry)
            receipt = dispatcher.dispatch(
                route_id=route_id,
                provider_execution_adapter_id=str(provider.get("provider_execution_adapter_id")),
                payload=_payload_for_provider(provider),
                execution_mode=DRY_RUN_MODE,
                operator_approval_id=f"{operator_id}.dry_run.approval",
            )
            receipt.update({
                "row_index": index,
                "dispatch_smoke_row_id": stable_id("source_adapter.dispatch_smoke", {"receipt": receipt.get("runtime_dispatch_receipt_id"), "index": index}),
                "dispatch_smoke_status": "ACCEPTED_FOR_LOCAL_RUNTIME_FIXTURE_DISPATCH" if not receipt.get("missing_receipt_fields") else "NEEDS_RECEIPT_FIELD_REVIEW",
            })
            rows.append(receipt)
    return {
        "schema_version": DISPATCH_SMOKE_SCHEMA_VERSION,
        "dispatch_smoke_receipt_batch_status": "SOURCE_ADAPTER_RUNTIME_DISPATCH_SMOKE_RECEIPTS_ACCEPTED" if rows and len(rows) == len(provider_rows) else "SOURCE_ADAPTER_RUNTIME_DISPATCH_SMOKE_RECEIPTS_NEED_REVIEW",
        "dispatch_smoke_receipt_count": len(rows),
        "provider_count": len(provider_rows),
        "dispatch_smoke_receipt_rows": rows,
    }


def _build_handoff(
    implementation_id: str,
    route_registry: Mapping[str, Any],
    provider_registry: Mapping[str, Any],
    credential_selector: Mapping[str, Any],
    binding_matrix: Mapping[str, Any],
    dispatch_smoke: Mapping[str, Any],
    issues: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ready = (
        not issues
        and route_registry.get("route_registry_status") == "SOURCE_ADAPTER_RUNTIME_GUI_CONTROLLER_ROUTES_REGISTERED"
        and provider_registry.get("provider_registry_status") == "SOURCE_ADAPTER_RUNTIME_PROVIDER_EXECUTION_REGISTRY_ACTIVE"
        and credential_selector.get("credential_selector_status") == "KEYS_ACCOUNTS_CREDENTIAL_REFERENCE_SELECTOR_ACTIVE"
        and binding_matrix.get("binding_matrix_status") == "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_BINDINGS_ACTIVE"
        and dispatch_smoke.get("dispatch_smoke_receipt_batch_status") == "SOURCE_ADAPTER_RUNTIME_DISPATCH_SMOKE_RECEIPTS_ACCEPTED"
    )
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_runtime_gui_provider_implementation_id": implementation_id,
        "ready_for_priority_fixture_pack_execution": ready,
        "ready_for_gui_controller_installation": ready,
        "ready_for_provider_dry_run_execution": ready,
        "ready_for_keys_accounts_reference_selection": ready,
        "ready_for_operator_approved_live_smoke_receipt_capture": ready,
        "required_next_stage": "priority_fixture_pack_execution_and_live_smoke_capture" if ready else "runtime_gui_provider_implementation_review",
        "route_count": route_registry.get("route_count", 0),
        "provider_count": provider_registry.get("provider_count", 0),
        "dispatch_smoke_receipt_count": dispatch_smoke.get("dispatch_smoke_receipt_count", 0),
    }


def build_source_adapter_runtime_gui_provider_implementation(
    next_roadmap_work_order_execution_closeout_package: Mapping[str, Any],
    *,
    operator_id: str = "operator",
    implementation_notes: Sequence[str] | None = None,
) -> SourceAdapterRuntimeGuiProviderImplementation:
    work_order_package = as_mapping(next_roadmap_work_order_execution_closeout_package, "next_roadmap_work_order_execution_closeout_package")
    issues = _validate_work_order_package(work_order_package)
    route_registry = _build_route_registry(work_order_package, issues)
    provider_registry = _build_provider_registry(work_order_package, issues)
    credential_selector = _build_credential_selector(route_registry, provider_registry, issues)
    binding_matrix = _build_binding_matrix(route_registry, provider_registry, issues)
    dispatch_smoke = _build_dispatch_smoke_receipts(route_registry, provider_registry, operator_id, issues)
    implementation_id = stable_id("source_adapter.runtime_gui_provider_implementation", {
        "work_order_execution_id": work_order_package.get("source_adapter_next_roadmap_work_order_execution_closeout_id"),
        "operator_id": operator_id,
        "route_count": route_registry.get("route_count"),
        "provider_count": provider_registry.get("provider_count"),
    })
    handoff = _build_handoff(implementation_id, route_registry, provider_registry, credential_selector, binding_matrix, dispatch_smoke, issues)
    ready = handoff.get("handoff_status") == HANDOFF_STATUS
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "route_count": route_registry.get("route_count", 0),
        "provider_count": provider_registry.get("provider_count", 0),
        "binding_count": binding_matrix.get("binding_count", 0),
        "dispatch_smoke_receipt_count": dispatch_smoke.get("dispatch_smoke_receipt_count", 0),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "next_actions": [
            "Run priority fixture packs through the registered runtime controller/provider dispatch receipts.",
            "Install GUI/controller call sites against the route registry and binding matrix.",
            "Run provider execution in dry-run mode before named operator-approved live smoke rows.",
            "Preserve KEYS/ACCOUNTS credential references and redacted receipt hashes in stored receipts.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "runtime_gui_provider_implementation_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_runtime_gui_provider_implementation_id": implementation_id,
        "source_adapter_next_roadmap_work_order_execution_closeout_id": work_order_package.get("source_adapter_next_roadmap_work_order_execution_closeout_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": list(issues),
        "implementation_notes": _strings(implementation_notes or []),
        "implementation_logic": {
            "input_source": "source_adapter_next_roadmap_work_order_execution_closeout",
            "gui_controller_routes_registered": True,
            "provider_execution_registry_active": True,
            "controller_provider_bindings_active": True,
            "dispatch_smoke_receipts_recorded": True,
            "keys_accounts_reference_selector_active": True,
            "operator_approved_execution_rows_preserved": True,
            "largest_stable_patch_mode_preserved": True,
        },
        "source_adapter_runtime_gui_controller_route_registry": route_registry,
        "source_adapter_runtime_provider_execution_registry": provider_registry,
        "source_adapter_keys_accounts_credential_reference_selector": credential_selector,
        "source_adapter_runtime_controller_provider_binding_matrix": binding_matrix,
        "source_adapter_runtime_dispatch_smoke_receipt_batch": dispatch_smoke,
        "source_adapter_runtime_gui_provider_implementation_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterRuntimeGuiProviderImplementation(package)


def example_runtime_gui_provider_implementation_package() -> dict[str, Any]:
    return build_source_adapter_runtime_gui_provider_implementation(
        example_next_roadmap_work_order_execution_closeout_package(),
        operator_id="example_operator",
    ).as_dict()


def main() -> None:
    package = example_runtime_gui_provider_implementation_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["runtime_gui_provider_implementation_status"] == STATUS
    assert package["source_adapter_runtime_gui_provider_implementation_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_runtime_gui_controller_route_registry"]["route_count"] >= 4
    assert package["source_adapter_runtime_provider_execution_registry"]["provider_count"] >= 4
    assert package["source_adapter_keys_accounts_credential_reference_selector"]["sidebar_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Runtime GUI Provider Implementation self-test passed.")


if __name__ == "__main__":
    main()
