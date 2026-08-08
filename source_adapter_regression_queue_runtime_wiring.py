from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_priority_fixture_regression_promotion import (
    HANDOFF_STATUS as PROMOTION_HANDOFF_STATUS,
    SCHEMA_VERSION as PROMOTION_SCHEMA_VERSION,
    STATUS as PROMOTION_STATUS,
    example_priority_fixture_regression_promotion_package,
)
from source_adapter_runtime_gui_provider_implementation import (
    HANDOFF_STATUS as RUNTIME_GUI_PROVIDER_HANDOFF_STATUS,
    SCHEMA_VERSION as RUNTIME_GUI_PROVIDER_SCHEMA_VERSION,
    STATUS as RUNTIME_GUI_PROVIDER_STATUS,
    example_runtime_gui_provider_implementation_package,
)

SCHEMA_VERSION = "source_adapter_regression_queue_runtime_wiring_v1"
LOCAL_RUNNER_QUEUE_SCHEMA_VERSION = "source_adapter_local_regression_runner_queue_installation_v1"
EXPANDED_BINDING_SCHEMA_VERSION = "source_adapter_runtime_controller_provider_expanded_binding_matrix_v1"
GUI_CALL_SITE_WIRING_SCHEMA_VERSION = "source_adapter_gui_controller_call_site_runtime_wiring_v1"
ACCEPTANCE_RECEIPT_BATCH_SCHEMA_VERSION = "source_adapter_local_regression_acceptance_receipt_batch_v1"
SMOKE_GATE_CARRY_FORWARD_SCHEMA_VERSION = "source_adapter_named_site_smoke_gate_carry_forward_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_regression_queue_runtime_wiring_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_regression_queue_runtime_wiring_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_REGRESSION_QUEUE_RUNTIME_WIRING_BUILT"
LOCAL_RUNNER_QUEUE_STATUS = "SOURCE_ADAPTER_LOCAL_REGRESSION_RUNNER_QUEUE_INSTALLED"
EXPANDED_BINDING_STATUS = "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_EXPANDED_BINDINGS_READY"
GUI_CALL_SITE_WIRING_STATUS = "SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITES_WIRED_FOR_LOCAL_DRY_RUN"
ACCEPTANCE_RECEIPT_BATCH_STATUS = "SOURCE_ADAPTER_LOCAL_REGRESSION_ACCEPTANCE_RECEIPTS_READY"
SMOKE_GATE_CARRY_FORWARD_STATUS = "SOURCE_ADAPTER_NAMED_SITE_SMOKE_APPROVAL_GATE_CARRIED_FORWARD_UNEXECUTED"
HANDOFF_STATUS = "SOURCE_ADAPTER_REGRESSION_QUEUE_RUNTIME_WIRING_READY_FOR_CLOSEOUT_AUDIT"
BLOCKED_STATUS = "SOURCE_ADAPTER_REGRESSION_QUEUE_RUNTIME_WIRING_NEEDS_REVIEW"

DRY_RUN_MODE = "dry_run"
LOCAL_PLAN_ONLY_MODE = "local_plan_only"
OPERATOR_APPROVED_MANUAL_SMOKE_MODE = "operator_approved_manual_smoke"
KEYS_ACCOUNTS_LABEL = "KEYS/ACCOUNTS"
KEYS_ACCOUNTS_SURFACE = "keys_accounts.ui.credential_reference_selector"
KEYS_ACCOUNTS_PROVIDER = "keys_accounts.provider.credential_reference_lookup"


@dataclass(frozen=True)
class SourceAdapterRegressionQueueRuntimeWiring:
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


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in as_list(container.get(key), key) if isinstance(row, Mapping)]


def _validate_inputs(promotion_package: Mapping[str, Any], runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if promotion_package.get("schema_version") != PROMOTION_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_promotion_schema", "severity": "error", "message": "priority fixture regression promotion schema was not recognised"})
    if promotion_package.get("priority_fixture_regression_promotion_status") != PROMOTION_STATUS:
        issues.append({"issue_id": "promotion_not_built", "severity": "error", "message": "priority fixture regression promotion is not built"})
    promotion_handoff = promotion_package.get("source_adapter_priority_fixture_regression_promotion_handoff") or {}
    if not isinstance(promotion_handoff, Mapping) or promotion_handoff.get("handoff_status") != PROMOTION_HANDOFF_STATUS:
        issues.append({"issue_id": "promotion_handoff_not_ready", "severity": "error", "message": "priority fixture regression promotion handoff is not ready"})
    promotion_summary = promotion_package.get("operator_summary") or {}
    if not isinstance(promotion_summary, Mapping) or promotion_summary.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "promotion_keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved by promotion"})

    if runtime_package.get("schema_version") != RUNTIME_GUI_PROVIDER_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_runtime_schema", "severity": "error", "message": "runtime GUI provider implementation schema was not recognised"})
    if runtime_package.get("runtime_gui_provider_implementation_status") != RUNTIME_GUI_PROVIDER_STATUS:
        issues.append({"issue_id": "runtime_gui_provider_not_built", "severity": "error", "message": "runtime GUI provider implementation is not built"})
    runtime_handoff = runtime_package.get("source_adapter_runtime_gui_provider_implementation_handoff") or {}
    if not isinstance(runtime_handoff, Mapping) or runtime_handoff.get("handoff_status") != RUNTIME_GUI_PROVIDER_HANDOFF_STATUS:
        issues.append({"issue_id": "runtime_handoff_not_ready", "severity": "error", "message": "runtime GUI provider handoff is not ready"})

    regression_queue = promotion_package.get("source_adapter_priority_fixture_regression_queue") or {}
    gui_plan = promotion_package.get("source_adapter_gui_controller_call_site_installation_plan") or {}
    smoke_gate = promotion_package.get("source_adapter_named_site_smoke_operator_approval_gate") or {}
    route_registry = runtime_package.get("source_adapter_runtime_gui_controller_route_registry") or {}
    provider_registry = runtime_package.get("source_adapter_runtime_provider_execution_registry") or {}
    binding_matrix = runtime_package.get("source_adapter_runtime_controller_provider_binding_matrix") or {}
    if not isinstance(regression_queue, Mapping) or len(_rows(regression_queue, "promoted_regression_queue_rows")) != 20:
        issues.append({"issue_id": "promotion_queue_row_count_mismatch", "severity": "error", "message": "expected twenty promoted regression queue rows"})
    if not isinstance(gui_plan, Mapping) or len(_rows(gui_plan, "call_site_installation_rows")) < 4:
        issues.append({"issue_id": "gui_call_site_plan_missing", "severity": "error", "message": "expected GUI/controller call-site installation rows"})
    if not isinstance(smoke_gate, Mapping) or len(_rows(smoke_gate, "named_site_smoke_gate_rows")) != 5:
        issues.append({"issue_id": "named_site_smoke_gate_missing", "severity": "error", "message": "expected five named-site smoke gate rows"})
    if not isinstance(route_registry, Mapping) or len(_rows(route_registry, "route_rows")) < 4:
        issues.append({"issue_id": "runtime_route_registry_missing", "severity": "error", "message": "expected runtime GUI/controller route registry rows"})
    if not isinstance(provider_registry, Mapping) or len(_rows(provider_registry, "provider_rows")) < 4:
        issues.append({"issue_id": "runtime_provider_registry_missing", "severity": "error", "message": "expected runtime provider registry rows"})
    if not isinstance(binding_matrix, Mapping) or not _rows(binding_matrix, "binding_rows"):
        issues.append({"issue_id": "runtime_binding_matrix_missing", "severity": "error", "message": "expected runtime controller/provider binding rows"})
    return issues


def _promotion_queue_rows(promotion_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(promotion_package.get("source_adapter_priority_fixture_regression_queue") or {}, "promoted_regression_queue_rows")


def _promotion_gui_rows(promotion_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(promotion_package.get("source_adapter_gui_controller_call_site_installation_plan") or {}, "call_site_installation_rows")


def _promotion_smoke_gate_rows(promotion_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(promotion_package.get("source_adapter_named_site_smoke_operator_approval_gate") or {}, "named_site_smoke_gate_rows")


def _runtime_route_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(runtime_package.get("source_adapter_runtime_gui_controller_route_registry") or {}, "route_rows")


def _runtime_provider_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(runtime_package.get("source_adapter_runtime_provider_execution_registry") or {}, "provider_rows")


def _runtime_binding_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(runtime_package.get("source_adapter_runtime_controller_provider_binding_matrix") or {}, "binding_rows")


def _index_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row.get(key)): dict(row) for row in rows if row.get(key)}


def _build_local_runner_queue(promotion_package: Mapping[str, Any], runtime_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]], wiring_notes: Sequence[str]) -> dict[str, Any]:
    queue_rows = _promotion_queue_rows(promotion_package)
    route_index = _index_by(_runtime_route_rows(runtime_package), "route_id")
    provider_index = _index_by(_runtime_provider_rows(runtime_package), "provider_execution_adapter_id")
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, row in enumerate(queue_rows):
            route_id = str(row.get("route_id") or "")
            provider_id = str(row.get("provider_execution_adapter_id") or "")
            route = route_index.get(route_id, {})
            provider = provider_index.get(provider_id, {})
            installed = bool(route and provider and not row.get("missing_receipt_fields"))
            rows.append({
                "schema_version": "source_adapter_local_regression_runner_queue_installation_row_v1",
                "row_index": index,
                "local_runner_queue_row_id": stable_id("source_adapter.local_regression_runner_queue_row", {"source": row.get("promoted_regression_queue_row_id"), "index": index}),
                "source_promoted_regression_queue_row_id": row.get("promoted_regression_queue_row_id"),
                "source_priority_dispatch_receipt_row_id": row.get("source_priority_dispatch_receipt_row_id"),
                "source_runtime_dispatch_receipt_id": row.get("source_runtime_dispatch_receipt_id"),
                "fixture_pack_id": row.get("fixture_pack_id"),
                "fixture_family": row.get("fixture_family"),
                "adapter_id": row.get("adapter_id"),
                "source_kind": row.get("source_kind"),
                "capability_id": row.get("capability_id"),
                "route_id": route_id,
                "surface_id": row.get("surface_id"),
                "runtime_route_registry_row_id": route.get("runtime_route_registry_row_id"),
                "controller_entrypoint": row.get("controller_entrypoint") or route.get("controller_entrypoint"),
                "provider_execution_adapter_id": provider_id,
                "runtime_provider_registry_row_id": provider.get("runtime_provider_registry_row_id"),
                "local_fixture_dir": row.get("local_fixture_dir"),
                "local_runner_entrypoint": "source_adapter.local_regression_runner.run_dry_run_queue_row",
                "local_runner_command_group": "source_adapter_priority_fixture_regular_regression_tail",
                "local_runner_command_label": f"source_adapter:{row.get('adapter_id')}:{row.get('capability_id')}",
                "expected_receipt_fields": list(row.get("expected_receipt_fields") or []),
                "field_presence": dict(row.get("field_presence") or {}),
                "missing_receipt_fields": list(row.get("missing_receipt_fields") or []),
                "payload_sha256": row.get("payload_sha256"),
                "execution_mode": DRY_RUN_MODE,
                "queue_installation_mode": "local_regression_runner_installation_only",
                "queue_installation_status": "INSTALLED_FOR_LOCAL_REGRESSION_DRY_RUN" if installed else "NEEDS_ROUTE_OR_PROVIDER_REGISTRATION_REVIEW",
                "accepted_for_local_regression_runner": installed,
                "local_runner_acceptance_recorded": installed,
                "execution_performed": False,
                "provider_call_performed": False,
                "controller_call_performed": False,
                "live_execution_allowed": False,
                "network_allowed": False,
                "archive_submission_performed": False,
                "release_upload_performed": False,
                "file_library_mutation_performed": False,
                "credential_storage_allowed": False,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                "keys_accounts_surface_preserved": row.get("keys_accounts_surface_preserved") is True or provider_id == KEYS_ACCOUNTS_PROVIDER,
                "redacted_reference_hash_preserved": row.get("redacted_reference_hash_preserved") is True,
            })
    installed_count = sum(1 for row in rows if row.get("queue_installation_status") == "INSTALLED_FOR_LOCAL_REGRESSION_DRY_RUN")
    return {
        "schema_version": LOCAL_RUNNER_QUEUE_SCHEMA_VERSION,
        "local_runner_queue_status": LOCAL_RUNNER_QUEUE_STATUS if rows and installed_count == len(rows) else "SOURCE_ADAPTER_LOCAL_REGRESSION_RUNNER_QUEUE_NEEDS_REVIEW",
        "installation_mode": "local_regression_runner_installation_only",
        "execution_mode": DRY_RUN_MODE,
        "wiring_notes": _strings(wiring_notes),
        "source_promoted_regression_queue_row_count": len(queue_rows),
        "local_runner_queue_row_count": len(rows),
        "installed_queue_row_count": installed_count,
        "fixture_pack_count": len(_strings(row.get("fixture_pack_id") for row in rows)),
        "adapter_count": len(_strings(row.get("adapter_id") for row in rows)),
        "provider_count": len(_strings(row.get("provider_execution_adapter_id") for row in rows)),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "local_runner_queue_rows": rows,
    }


def _build_expanded_binding_matrix(local_runner_queue: Mapping[str, Any], runtime_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_bindings = _runtime_binding_rows(runtime_package)
    source_binding_keys = {(str(row.get("route_id")), str(row.get("provider_execution_adapter_id"))) for row in source_bindings}
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, row in enumerate(_rows(local_runner_queue, "local_runner_queue_rows")):
            route_id = str(row.get("route_id") or "")
            provider_id = str(row.get("provider_execution_adapter_id") or "")
            direct_source_binding = (route_id, provider_id) in source_binding_keys
            registered = bool(row.get("runtime_route_registry_row_id") and row.get("runtime_provider_registry_row_id"))
            rows.append({
                "schema_version": "source_adapter_runtime_controller_provider_expanded_binding_row_v1",
                "row_index": index,
                "expanded_binding_row_id": stable_id("source_adapter.expanded_controller_provider_binding", {"queue_row": row.get("local_runner_queue_row_id"), "index": index}),
                "source_local_runner_queue_row_id": row.get("local_runner_queue_row_id"),
                "source_promoted_regression_queue_row_id": row.get("source_promoted_regression_queue_row_id"),
                "route_id": route_id,
                "surface_id": row.get("surface_id"),
                "runtime_route_registry_row_id": row.get("runtime_route_registry_row_id"),
                "controller_entrypoint": row.get("controller_entrypoint"),
                "provider_execution_adapter_id": provider_id,
                "runtime_provider_registry_row_id": row.get("runtime_provider_registry_row_id"),
                "capability_id": row.get("capability_id"),
                "direct_source_binding_existed": direct_source_binding,
                "expanded_from_promoted_regression_queue": True,
                "binding_expansion_mode": "local_dry_run_only",
                "binding_status": "BOUND_FOR_LOCAL_REGRESSION_DRY_RUN" if registered else "NEEDS_ROUTE_OR_PROVIDER_REGISTRATION_REVIEW",
                "local_dispatch_receipt_construction_allowed": registered,
                "provider_call_allowed": False,
                "network_allowed": False,
                "credential_storage_allowed": False,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            })
    bound_count = sum(1 for row in rows if row.get("binding_status") == "BOUND_FOR_LOCAL_REGRESSION_DRY_RUN")
    return {
        "schema_version": EXPANDED_BINDING_SCHEMA_VERSION,
        "expanded_binding_matrix_status": EXPANDED_BINDING_STATUS if rows and bound_count == len(rows) else "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_EXPANDED_BINDINGS_NEED_REVIEW",
        "binding_expansion_mode": "local_dry_run_only",
        "expanded_binding_row_count": len(rows),
        "bound_expanded_binding_row_count": bound_count,
        "source_runtime_binding_row_count": len(source_bindings),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "expanded_binding_rows": rows,
    }


def _build_gui_call_site_wiring(promotion_package: Mapping[str, Any], runtime_package: Mapping[str, Any], expanded_binding_matrix: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    route_index = _index_by(_runtime_route_rows(runtime_package), "route_id")
    binding_rows = _rows(expanded_binding_matrix, "expanded_binding_rows")
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, planned in enumerate(_promotion_gui_rows(promotion_package)):
            route_id = str(planned.get("route_id") or "")
            runtime_route = route_index.get(route_id, {})
            related_bindings = [row for row in binding_rows if row.get("route_id") == route_id]
            wired = bool(runtime_route and planned.get("installation_mode") == LOCAL_PLAN_ONLY_MODE)
            rows.append({
                "schema_version": "source_adapter_gui_controller_call_site_runtime_wiring_row_v1",
                "row_index": index,
                "gui_call_site_runtime_wiring_row_id": stable_id("source_adapter.gui_call_site_runtime_wiring", {"route": route_id, "index": index}),
                "source_call_site_installation_row_id": planned.get("call_site_installation_row_id"),
                "runtime_route_registry_row_id": runtime_route.get("runtime_route_registry_row_id"),
                "route_id": route_id,
                "surface_id": planned.get("surface_id") or runtime_route.get("surface_id"),
                "controller_entrypoint": planned.get("controller_entrypoint") or runtime_route.get("controller_entrypoint"),
                "install_target": planned.get("install_target"),
                "provider_execution_adapter_ids": _strings(planned.get("provider_execution_adapter_ids") or [row.get("provider_execution_adapter_id") for row in related_bindings]),
                "capability_ids": _strings(planned.get("capability_ids") or [row.get("capability_id") for row in related_bindings]),
                "related_expanded_binding_row_count": len(related_bindings),
                "wiring_mode": "local_runtime_registry_wiring_only",
                "wiring_status": "WIRED_IN_LOCAL_RUNTIME_REGISTRY_FOR_DRY_RUN" if wired else "NEEDS_RUNTIME_ROUTE_REGISTRY_REVIEW",
                "gui_mutation_performed": False,
                "runtime_route_mutation_performed": False,
                "controller_call_performed": False,
                "provider_call_performed": False,
                "network_allowed": False,
                "credential_storage_allowed": False,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                "keys_accounts_surface_preserved": planned.get("keys_accounts_surface_preserved") is True or planned.get("surface_id") == KEYS_ACCOUNTS_SURFACE,
            })
    wired_count = sum(1 for row in rows if row.get("wiring_status") == "WIRED_IN_LOCAL_RUNTIME_REGISTRY_FOR_DRY_RUN")
    return {
        "schema_version": GUI_CALL_SITE_WIRING_SCHEMA_VERSION,
        "gui_call_site_runtime_wiring_status": GUI_CALL_SITE_WIRING_STATUS if rows and wired_count == len(rows) else "SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITES_NEED_WIRING_REVIEW",
        "wiring_mode": "local_runtime_registry_wiring_only",
        "call_site_wiring_row_count": len(rows),
        "wired_call_site_row_count": wired_count,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "gui_call_site_wiring_rows": rows,
    }


def _build_acceptance_receipts(local_runner_queue: Mapping[str, Any], expanded_binding_matrix: Mapping[str, Any], operator_id: str, issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    binding_index = _index_by(_rows(expanded_binding_matrix, "expanded_binding_rows"), "source_local_runner_queue_row_id")
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, queue_row in enumerate(_rows(local_runner_queue, "local_runner_queue_rows")):
            binding = binding_index.get(str(queue_row.get("local_runner_queue_row_id")), {})
            ready = queue_row.get("queue_installation_status") == "INSTALLED_FOR_LOCAL_REGRESSION_DRY_RUN" and binding.get("binding_status") == "BOUND_FOR_LOCAL_REGRESSION_DRY_RUN" and not queue_row.get("missing_receipt_fields")
            receipt_seed = {
                "queue_row": queue_row.get("local_runner_queue_row_id"),
                "binding": binding.get("expanded_binding_row_id"),
                "operator_id": operator_id,
                "payload_sha256": queue_row.get("payload_sha256"),
            }
            rows.append({
                "schema_version": "source_adapter_local_regression_acceptance_receipt_row_v1",
                "row_index": index,
                "local_regression_acceptance_receipt_id": stable_id("source_adapter.local_regression_acceptance_receipt", receipt_seed),
                "source_local_runner_queue_row_id": queue_row.get("local_runner_queue_row_id"),
                "source_expanded_binding_row_id": binding.get("expanded_binding_row_id"),
                "source_promoted_regression_queue_row_id": queue_row.get("source_promoted_regression_queue_row_id"),
                "adapter_id": queue_row.get("adapter_id"),
                "source_kind": queue_row.get("source_kind"),
                "fixture_pack_id": queue_row.get("fixture_pack_id"),
                "route_id": queue_row.get("route_id"),
                "provider_execution_adapter_id": queue_row.get("provider_execution_adapter_id"),
                "capability_id": queue_row.get("capability_id"),
                "execution_mode": DRY_RUN_MODE,
                "receipt_kind": "local_regression_acceptance_receipt",
                "receipt_status": "SOURCE_ADAPTER_LOCAL_REGRESSION_ACCEPTANCE_RECEIPT_READY" if ready else "SOURCE_ADAPTER_LOCAL_REGRESSION_ACCEPTANCE_RECEIPT_NEEDS_REVIEW",
                "accepted_for_closeout_audit": ready,
                "receipt_capture_metadata_only": True,
                "expected_receipt_fields": list(queue_row.get("expected_receipt_fields") or []),
                "field_presence": dict(queue_row.get("field_presence") or {}),
                "missing_receipt_fields": list(queue_row.get("missing_receipt_fields") or []),
                "source_payload_sha256": queue_row.get("payload_sha256"),
                "receipt_payload_sha256": hashlib.sha256(canonical_json(receipt_seed).encode("utf-8")).hexdigest(),
                "local_runner_acceptance_recorded": ready,
                "provider_call_performed": False,
                "controller_call_performed": False,
                "live_execution_allowed": False,
                "network_allowed": False,
                "archive_submission_performed": False,
                "release_upload_performed": False,
                "file_library_mutation_performed": False,
                "credential_storage_allowed": False,
                "credential_secret_material_present": False,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                "redacted_reference_hash_required": queue_row.get("provider_execution_adapter_id") == KEYS_ACCOUNTS_PROVIDER,
                "redacted_reference_hash_preserved": queue_row.get("redacted_reference_hash_preserved") is True,
            })
    ready_count = sum(1 for row in rows if row.get("receipt_status") == "SOURCE_ADAPTER_LOCAL_REGRESSION_ACCEPTANCE_RECEIPT_READY")
    return {
        "schema_version": ACCEPTANCE_RECEIPT_BATCH_SCHEMA_VERSION,
        "acceptance_receipt_batch_status": ACCEPTANCE_RECEIPT_BATCH_STATUS if rows and ready_count == len(rows) else "SOURCE_ADAPTER_LOCAL_REGRESSION_ACCEPTANCE_RECEIPTS_NEED_REVIEW",
        "execution_mode": DRY_RUN_MODE,
        "acceptance_receipt_row_count": len(rows),
        "ready_acceptance_receipt_row_count": ready_count,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "local_regression_acceptance_receipt_rows": rows,
    }


def _build_smoke_gate_carry_forward(promotion_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, row in enumerate(_promotion_smoke_gate_rows(promotion_package)):
            rows.append({
                "schema_version": "source_adapter_named_site_smoke_gate_carry_forward_row_v1",
                "row_index": index,
                "smoke_gate_carry_forward_row_id": stable_id("source_adapter.named_site_smoke_gate_carry_forward", {"source": row.get("named_site_smoke_gate_row_id"), "index": index}),
                "source_named_site_smoke_gate_row_id": row.get("named_site_smoke_gate_row_id"),
                "source_named_site_smoke_queue_row_id": row.get("source_named_site_smoke_queue_row_id"),
                "fixture_pack_id": row.get("fixture_pack_id"),
                "adapter_id": row.get("adapter_id"),
                "source_kind": row.get("source_kind"),
                "fixture_family": row.get("fixture_family"),
                "provider_execution_adapter_ids": list(row.get("provider_execution_adapter_ids") or []),
                "required_operator_inputs": list(row.get("required_operator_inputs") or []),
                "receipt_capture_requirements": list(row.get("receipt_capture_requirements") or []),
                "carry_forward_status": "CARRIED_FORWARD_AS_OPERATOR_APPROVAL_REQUIRED",
                "operator_approval_required": True,
                "operator_approved": False,
                "execution_mode": OPERATOR_APPROVED_MANUAL_SMOKE_MODE,
                "execution_performed": False,
                "smoke_executed": False,
                "live_execution_allowed": False,
                "network_allowed": False,
                "provider_call_performed": False,
                "credential_storage_allowed": False,
                "receipt_capture_required": True,
                "redacted_credential_reference_required": True,
                "block_reason": "explicit_operator_approval_and_named_site_inputs_required",
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            })
    carried_count = sum(1 for row in rows if row.get("carry_forward_status") == "CARRIED_FORWARD_AS_OPERATOR_APPROVAL_REQUIRED")
    return {
        "schema_version": SMOKE_GATE_CARRY_FORWARD_SCHEMA_VERSION,
        "smoke_gate_carry_forward_status": SMOKE_GATE_CARRY_FORWARD_STATUS if rows and carried_count == len(rows) else "SOURCE_ADAPTER_NAMED_SITE_SMOKE_GATE_CARRY_FORWARD_NEEDS_REVIEW",
        "named_site_smoke_gate_row_count": len(rows),
        "carried_forward_gate_row_count": carried_count,
        "operator_approval_required": True,
        "smoke_execution_performed": False,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "smoke_gate_carry_forward_rows": rows,
    }


def _build_handoff(wiring_id: str, local_runner_queue: Mapping[str, Any], expanded_binding_matrix: Mapping[str, Any], gui_wiring: Mapping[str, Any], acceptance_receipts: Mapping[str, Any], smoke_gate_carry_forward: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = (
        not issues
        and local_runner_queue.get("local_runner_queue_status") == LOCAL_RUNNER_QUEUE_STATUS
        and expanded_binding_matrix.get("expanded_binding_matrix_status") == EXPANDED_BINDING_STATUS
        and gui_wiring.get("gui_call_site_runtime_wiring_status") == GUI_CALL_SITE_WIRING_STATUS
        and acceptance_receipts.get("acceptance_receipt_batch_status") == ACCEPTANCE_RECEIPT_BATCH_STATUS
        and smoke_gate_carry_forward.get("smoke_gate_carry_forward_status") == SMOKE_GATE_CARRY_FORWARD_STATUS
    )
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_regression_queue_runtime_wiring_id": wiring_id,
        "local_regression_runner_queue_installed": ready,
        "expanded_controller_provider_bindings_ready": ready,
        "gui_controller_call_sites_wired_for_local_dry_run": ready,
        "local_regression_acceptance_receipts_ready": ready,
        "named_site_smoke_still_approval_gated": True,
        "credential_references_preserved_redacted": True,
        "required_next_stage": "source_adapter_closeout_audit_and_roadmap_state_update" if ready else "regression_queue_runtime_wiring_review",
        "local_runner_queue_row_count": local_runner_queue.get("local_runner_queue_row_count", 0),
        "expanded_binding_row_count": expanded_binding_matrix.get("expanded_binding_row_count", 0),
        "call_site_wiring_row_count": gui_wiring.get("call_site_wiring_row_count", 0),
        "acceptance_receipt_row_count": acceptance_receipts.get("acceptance_receipt_row_count", 0),
        "named_site_smoke_gate_row_count": smoke_gate_carry_forward.get("named_site_smoke_gate_row_count", 0),
    }


def build_source_adapter_regression_queue_runtime_wiring(
    priority_fixture_regression_promotion_package: Mapping[str, Any],
    runtime_gui_provider_implementation_package: Mapping[str, Any],
    *,
    operator_id: str = "operator",
    wiring_notes: Sequence[str] | None = None,
) -> SourceAdapterRegressionQueueRuntimeWiring:
    promotion_package = as_mapping(priority_fixture_regression_promotion_package, "priority_fixture_regression_promotion_package")
    runtime_package = as_mapping(runtime_gui_provider_implementation_package, "runtime_gui_provider_implementation_package")
    issues = _validate_inputs(promotion_package, runtime_package)
    local_runner_queue = _build_local_runner_queue(promotion_package, runtime_package, issues, wiring_notes or [])
    expanded_binding_matrix = _build_expanded_binding_matrix(local_runner_queue, runtime_package, issues)
    gui_wiring = _build_gui_call_site_wiring(promotion_package, runtime_package, expanded_binding_matrix, issues)
    acceptance_receipts = _build_acceptance_receipts(local_runner_queue, expanded_binding_matrix, operator_id, issues)
    smoke_gate_carry_forward = _build_smoke_gate_carry_forward(promotion_package, issues)
    wiring_id = stable_id("source_adapter.regression_queue_runtime_wiring", {
        "promotion_id": promotion_package.get("source_adapter_priority_fixture_regression_promotion_id"),
        "runtime_gui_provider_id": runtime_package.get("source_adapter_runtime_gui_provider_implementation_id"),
        "operator_id": operator_id,
        "local_runner_queue_row_count": local_runner_queue.get("local_runner_queue_row_count"),
    })
    handoff = _build_handoff(wiring_id, local_runner_queue, expanded_binding_matrix, gui_wiring, acceptance_receipts, smoke_gate_carry_forward, issues)
    ready = handoff.get("handoff_status") == HANDOFF_STATUS
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "local_runner_queue_row_count": local_runner_queue.get("local_runner_queue_row_count", 0),
        "expanded_binding_row_count": expanded_binding_matrix.get("expanded_binding_row_count", 0),
        "call_site_wiring_row_count": gui_wiring.get("call_site_wiring_row_count", 0),
        "acceptance_receipt_row_count": acceptance_receipts.get("acceptance_receipt_row_count", 0),
        "named_site_smoke_gate_row_count": smoke_gate_carry_forward.get("named_site_smoke_gate_row_count", 0),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Use the local regression runner queue and acceptance receipts for closeout audit.",
            "Keep GUI/controller call-site wiring as local dry-run registry wiring until UI mutation is separately approved.",
            "Keep named-site smoke blocked until explicit operator approval and named-site inputs are supplied.",
            "Prepare a roadmap/current-state closeout after the local regression queue wiring audit passes.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "regression_queue_runtime_wiring_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_regression_queue_runtime_wiring_id": wiring_id,
        "source_adapter_priority_fixture_regression_promotion_id": promotion_package.get("source_adapter_priority_fixture_regression_promotion_id"),
        "source_adapter_runtime_gui_provider_implementation_id": runtime_package.get("source_adapter_runtime_gui_provider_implementation_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": list(issues),
        "wiring_logic": {
            "input_sources": ["source_adapter_priority_fixture_regression_promotion", "source_adapter_runtime_gui_provider_implementation"],
            "local_regression_runner_queue_installed": True,
            "expanded_controller_provider_bindings_built": True,
            "gui_controller_call_sites_wired_for_local_dry_run": True,
            "local_acceptance_receipts_recorded": True,
            "named_site_smoke_approval_gate_carried_forward": True,
            "keys_accounts_references_preserved_redacted": True,
            "live_execution_blocked": True,
        },
        "source_adapter_local_regression_runner_queue_installation": local_runner_queue,
        "source_adapter_runtime_controller_provider_expanded_binding_matrix": expanded_binding_matrix,
        "source_adapter_gui_controller_call_site_runtime_wiring": gui_wiring,
        "source_adapter_local_regression_acceptance_receipt_batch": acceptance_receipts,
        "source_adapter_named_site_smoke_gate_carry_forward": smoke_gate_carry_forward,
        "source_adapter_regression_queue_runtime_wiring_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterRegressionQueueRuntimeWiring(package)


def example_regression_queue_runtime_wiring_package() -> dict[str, Any]:
    return build_source_adapter_regression_queue_runtime_wiring(
        example_priority_fixture_regression_promotion_package(),
        example_runtime_gui_provider_implementation_package(),
        operator_id="example_operator",
        wiring_notes=["deterministic local runtime wiring example"],
    ).as_dict()


def main() -> None:
    package = example_regression_queue_runtime_wiring_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["regression_queue_runtime_wiring_status"] == STATUS
    assert package["source_adapter_regression_queue_runtime_wiring_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_local_regression_runner_queue_installation"]["local_runner_queue_row_count"] == 20
    assert package["source_adapter_runtime_controller_provider_expanded_binding_matrix"]["expanded_binding_row_count"] == 20
    assert package["source_adapter_local_regression_acceptance_receipt_batch"]["acceptance_receipt_row_count"] == 20
    assert package["source_adapter_named_site_smoke_gate_carry_forward"]["named_site_smoke_gate_row_count"] == 5
    assert package["operator_summary"]["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
    print("Source Adapter Regression Queue Runtime Wiring self-test passed.")


if __name__ == "__main__":
    main()
