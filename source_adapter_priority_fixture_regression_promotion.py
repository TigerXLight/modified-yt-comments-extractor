from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_priority_fixture_pack_implementation import (
    HANDOFF_STATUS as PRIORITY_FIXTURE_PACK_HANDOFF_STATUS,
    SCHEMA_VERSION as PRIORITY_FIXTURE_PACK_SCHEMA_VERSION,
    STATUS as PRIORITY_FIXTURE_PACK_STATUS,
    example_priority_fixture_pack_implementation_package,
)

SCHEMA_VERSION = "source_adapter_priority_fixture_regression_promotion_v1"
REGRESSION_QUEUE_SCHEMA_VERSION = "source_adapter_priority_fixture_regression_queue_v1"
GUI_CALL_SITE_PLAN_SCHEMA_VERSION = "source_adapter_gui_controller_call_site_installation_plan_v1"
SMOKE_APPROVAL_GATE_SCHEMA_VERSION = "source_adapter_named_site_smoke_operator_approval_gate_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_priority_fixture_regression_promotion_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_priority_fixture_regression_promotion_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_PROMOTION_BUILT"
REGRESSION_QUEUE_STATUS = "SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_QUEUE_READY"
GUI_CALL_SITE_PLAN_STATUS = "SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITE_INSTALLATION_PLAN_READY"
NAMED_SITE_SMOKE_GATE_STATUS = "SOURCE_ADAPTER_NAMED_SITE_SMOKE_REMAINS_OPERATOR_APPROVAL_REQUIRED"
HANDOFF_STATUS = "SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_PROMOTION_READY_FOR_REGRESSION_QUEUE_INSTALLATION"
BLOCKED_STATUS = "SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_PROMOTION_NEEDS_REVIEW"

DRY_RUN_MODE = "dry_run"
LOCAL_PLAN_ONLY_MODE = "local_plan_only"
OPERATOR_APPROVED_MANUAL_SMOKE_MODE = "operator_approved_manual_smoke"
KEYS_ACCOUNTS_LABEL = "KEYS/ACCOUNTS"
KEYS_ACCOUNTS_SURFACE = "keys_accounts.ui.credential_reference_selector"


@dataclass(frozen=True)
class SourceAdapterPriorityFixtureRegressionPromotion:
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


def _validate_priority_fixture_pack_package(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != PRIORITY_FIXTURE_PACK_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_priority_fixture_pack_schema", "severity": "error", "message": "priority fixture pack implementation schema was not recognised"})
    if package.get("priority_fixture_pack_implementation_status") != PRIORITY_FIXTURE_PACK_STATUS:
        issues.append({"issue_id": "priority_fixture_pack_not_built", "severity": "error", "message": "priority fixture pack implementation is not built"})
    if int(package.get("issue_count", 0) or 0) != 0:
        issues.append({"issue_id": "upstream_priority_fixture_pack_issues", "severity": "error", "message": "priority fixture pack implementation contains upstream issues"})
    handoff = package.get("source_adapter_priority_fixture_pack_implementation_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != PRIORITY_FIXTURE_PACK_HANDOFF_STATUS:
        issues.append({"issue_id": "priority_fixture_pack_handoff_not_ready", "severity": "error", "message": "priority fixture pack implementation handoff is not ready"})
    if package.get("operator_summary", {}).get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_not_preserved", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved upstream"})
    catalog = package.get("source_adapter_priority_fixture_pack_catalog") or {}
    dispatch_receipts = package.get("source_adapter_priority_fixture_pack_dispatch_receipt_batch") or {}
    gui_checklist = package.get("source_adapter_priority_fixture_pack_gui_installation_checklist") or {}
    smoke_queue = package.get("source_adapter_priority_fixture_pack_named_site_smoke_queue") or {}
    if not isinstance(catalog, Mapping) or len(_rows(catalog, "fixture_pack_rows")) != 5:
        issues.append({"issue_id": "fixture_pack_catalog_missing", "severity": "error", "message": "expected five priority fixture pack catalog rows"})
    if not isinstance(dispatch_receipts, Mapping) or len(_rows(dispatch_receipts, "dispatch_receipt_rows")) != 20:
        issues.append({"issue_id": "dispatch_receipt_batch_missing", "severity": "error", "message": "expected twenty accepted priority dispatch receipts"})
    if not isinstance(gui_checklist, Mapping) or not _rows(gui_checklist, "gui_installation_rows"):
        issues.append({"issue_id": "gui_installation_checklist_missing", "severity": "error", "message": "GUI installation checklist is missing"})
    if not isinstance(smoke_queue, Mapping) or len(_rows(smoke_queue, "named_site_smoke_queue_rows")) != 5:
        issues.append({"issue_id": "named_site_smoke_queue_missing", "severity": "error", "message": "expected five named-site smoke queue rows"})
    return issues


def _fixture_pack_rows(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(package.get("source_adapter_priority_fixture_pack_catalog") or {}, "fixture_pack_rows")


def _dispatch_receipt_rows(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(package.get("source_adapter_priority_fixture_pack_dispatch_receipt_batch") or {}, "dispatch_receipt_rows")


def _gui_installation_rows(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(package.get("source_adapter_priority_fixture_pack_gui_installation_checklist") or {}, "gui_installation_rows")


def _named_site_smoke_rows(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(package.get("source_adapter_priority_fixture_pack_named_site_smoke_queue") or {}, "named_site_smoke_queue_rows")


def _build_promoted_regression_queue(package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]], promotion_notes: Sequence[str]) -> dict[str, Any]:
    dispatch_rows = _dispatch_receipt_rows(package)
    fixture_pack_ids = _strings(row.get("fixture_pack_id") for row in dispatch_rows)
    provider_ids = _strings(row.get("provider_execution_adapter_id") for row in dispatch_rows)
    adapter_ids = _strings(row.get("adapter_id") for row in dispatch_rows)
    source_kinds = _strings(row.get("source_kind") for row in dispatch_rows)
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, receipt in enumerate(dispatch_rows):
            payload = dict(receipt.get("receipt_payload") or {}) if isinstance(receipt.get("receipt_payload"), Mapping) else {}
            redacted_hash = str(payload.get("redacted_reference_hash") or "").strip()
            rows.append({
                "schema_version": "source_adapter_priority_fixture_regression_queue_row_v1",
                "row_index": index,
                "promoted_regression_queue_row_id": stable_id("source_adapter.priority_fixture_regression_queue_row", {"receipt": receipt.get("fixture_pack_dispatch_receipt_row_id"), "index": index}),
                "source_priority_dispatch_receipt_row_id": receipt.get("fixture_pack_dispatch_receipt_row_id"),
                "source_runtime_dispatch_receipt_id": receipt.get("runtime_dispatch_receipt_id"),
                "fixture_pack_execution_row_id": receipt.get("fixture_pack_execution_row_id"),
                "fixture_pack_id": receipt.get("fixture_pack_id"),
                "adapter_id": receipt.get("adapter_id"),
                "source_kind": receipt.get("source_kind"),
                "fixture_family": receipt.get("fixture_family"),
                "local_fixture_dir": receipt.get("local_fixture_dir"),
                "route_id": receipt.get("route_id"),
                "surface_id": receipt.get("surface_id"),
                "controller_entrypoint": receipt.get("controller_entrypoint"),
                "provider_execution_adapter_id": receipt.get("provider_execution_adapter_id"),
                "capability_id": receipt.get("capability_id"),
                "receipt_role": receipt.get("receipt_role"),
                "expected_receipt_fields": _strings(receipt.get("expected_receipt_fields") or []),
                "field_presence": dict(receipt.get("field_presence") or {}),
                "missing_receipt_fields": list(receipt.get("missing_receipt_fields") or []),
                "payload_sha256": receipt.get("payload_sha256"),
                "source_dispatch_acceptance_status": receipt.get("dispatch_acceptance_status"),
                "regular_regression_acceptance_status": "ACCEPTED_FOR_REGULAR_SOURCE_ADAPTER_REGRESSION",
                "regression_queue_row_status": "READY_FOR_LOCAL_REGRESSION_QUEUE",
                "execution_mode": DRY_RUN_MODE,
                "execution_performed": False,
                "live_execution_allowed": False,
                "network_allowed": False,
                "provider_call_allowed": False,
                "archive_submission_allowed": False,
                "release_upload_allowed": False,
                "file_library_mutation_allowed": False,
                "credential_storage_allowed": False,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                "keys_accounts_surface_preserved": KEYS_ACCOUNTS_SURFACE in (str(receipt.get("surface_id")), str(receipt.get("route_id"))) or receipt.get("provider_execution_adapter_id") == "keys_accounts.provider.credential_reference_lookup",
                "redacted_reference_hash_preserved": bool(redacted_hash) if receipt.get("provider_execution_adapter_id") == "keys_accounts.provider.credential_reference_lookup" else True,
            })
    return {
        "schema_version": REGRESSION_QUEUE_SCHEMA_VERSION,
        "regression_queue_status": REGRESSION_QUEUE_STATUS if rows and not issues else "SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_QUEUE_NEEDS_REVIEW",
        "promotion_mode": DRY_RUN_MODE,
        "promotion_notes": _strings(promotion_notes),
        "fixture_pack_count": len(fixture_pack_ids),
        "provider_count": len(provider_ids),
        "adapter_count": len(adapter_ids),
        "source_kind_count": len(source_kinds),
        "source_dispatch_receipt_count": len(dispatch_rows),
        "promoted_regression_queue_row_count": len(rows),
        "adapter_ids": adapter_ids,
        "source_kinds": source_kinds,
        "provider_execution_adapter_ids": provider_ids,
        "fixture_pack_ids": fixture_pack_ids,
        "promoted_regression_queue_rows": rows,
    }


def _provider_ids_for_route(route_id: str, queue_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    providers = [str(row.get("provider_execution_adapter_id") or "") for row in queue_rows if row.get("route_id") == route_id]
    if route_id == "source_adapter.gui.runtime.action_palette" and not providers:
        providers = [str(row.get("provider_execution_adapter_id") or "") for row in queue_rows if row.get("provider_execution_adapter_id") != "keys_accounts.provider.credential_reference_lookup"]
    return _strings(providers)


def _capability_ids_for_route(route_id: str, queue_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    capabilities = [str(row.get("capability_id") or "") for row in queue_rows if row.get("route_id") == route_id]
    if route_id == "source_adapter.gui.runtime.action_palette" and not capabilities:
        capabilities = [str(row.get("capability_id") or "") for row in queue_rows if row.get("provider_execution_adapter_id") != "keys_accounts.provider.credential_reference_lookup"]
    return _strings(capabilities)


def _build_gui_controller_call_site_plan(package: Mapping[str, Any], regression_queue: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    queue_rows = _rows(regression_queue, "promoted_regression_queue_rows")
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, checklist_row in enumerate(_gui_installation_rows(package)):
            route_id = str(checklist_row.get("route_id") or "")
            is_keys_accounts = route_id == "keys_accounts.gui.credential_reference_selector" or checklist_row.get("surface_id") == KEYS_ACCOUNTS_SURFACE
            rows.append({
                "schema_version": "source_adapter_gui_controller_call_site_installation_plan_row_v1",
                "row_index": index,
                "call_site_installation_row_id": stable_id("source_adapter.gui_controller_call_site_installation", {"route": route_id, "index": index}),
                "source_gui_installation_row_id": checklist_row.get("gui_installation_row_id"),
                "route_id": route_id,
                "surface_id": checklist_row.get("surface_id"),
                "controller_entrypoint": checklist_row.get("controller_entrypoint"),
                "install_target": checklist_row.get("install_target"),
                "provider_execution_adapter_ids": _provider_ids_for_route(route_id, queue_rows),
                "capability_ids": _capability_ids_for_route(route_id, queue_rows),
                "installation_mode": LOCAL_PLAN_ONLY_MODE,
                "call_site_installation_status": "PLANNED_FOR_LOCAL_GUI_CONTROLLER_INSTALLATION",
                "gui_mutation_performed": False,
                "runtime_route_mutation_performed": False,
                "controller_call_performed": False,
                "network_allowed": False,
                "credential_storage_allowed": False,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                "keys_accounts_surface_preserved": is_keys_accounts or checklist_row.get("keys_accounts_label") == KEYS_ACCOUNTS_LABEL,
            })
    return {
        "schema_version": GUI_CALL_SITE_PLAN_SCHEMA_VERSION,
        "gui_controller_call_site_installation_plan_status": GUI_CALL_SITE_PLAN_STATUS if rows and not issues else "SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITE_INSTALLATION_PLAN_NEEDS_REVIEW",
        "installation_mode": LOCAL_PLAN_ONLY_MODE,
        "call_site_installation_row_count": len(rows),
        "route_count": len(_strings(row.get("route_id") for row in rows)),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "call_site_installation_rows": rows,
    }


def _build_named_site_smoke_approval_gate(package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, smoke_row in enumerate(_named_site_smoke_rows(package)):
            rows.append({
                "schema_version": "source_adapter_named_site_smoke_operator_approval_gate_row_v1",
                "row_index": index,
                "named_site_smoke_gate_row_id": stable_id("source_adapter.named_site_smoke_operator_approval_gate", {"source_row": smoke_row.get("named_site_smoke_queue_row_id"), "index": index}),
                "source_named_site_smoke_queue_row_id": smoke_row.get("named_site_smoke_queue_row_id"),
                "fixture_pack_id": smoke_row.get("fixture_pack_id"),
                "adapter_id": smoke_row.get("adapter_id"),
                "source_kind": smoke_row.get("source_kind"),
                "fixture_family": smoke_row.get("fixture_family"),
                "provider_execution_adapter_ids": _strings(smoke_row.get("provider_execution_adapter_ids") or []),
                "required_operator_inputs": _strings(smoke_row.get("required_operator_inputs") or []),
                "future_operator_input_reference_required": True,
                "future_operator_approval_id_required": True,
                "operator_approval_required": True,
                "operator_approved": False,
                "execution_performed": False,
                "smoke_executed": False,
                "live_execution_allowed": False,
                "execution_mode": OPERATOR_APPROVED_MANUAL_SMOKE_MODE,
                "receipt_capture_required": True,
                "receipt_capture_requirements": [
                    "operator_approval_id",
                    "named_site_id",
                    "source_url_or_local_fixture_ref",
                    "receipt_output_dir",
                    "redacted_credential_reference_hash",
                ],
                "credential_storage_allowed": False,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                "redacted_credential_reference_required": True,
                "approval_gate_status": "WAITING_FOR_OPERATOR_APPROVAL_AND_NAMED_SITE_INPUT",
            })
    return {
        "schema_version": SMOKE_APPROVAL_GATE_SCHEMA_VERSION,
        "named_site_smoke_approval_gate_status": NAMED_SITE_SMOKE_GATE_STATUS if rows and not issues else "SOURCE_ADAPTER_NAMED_SITE_SMOKE_APPROVAL_GATE_NEEDS_REVIEW",
        "named_site_smoke_gate_row_count": len(rows),
        "operator_approval_required": True,
        "smoke_execution_performed": False,
        "receipt_capture_required": True,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "named_site_smoke_gate_rows": rows,
    }


def _build_handoff(promotion_id: str, regression_queue: Mapping[str, Any], gui_plan: Mapping[str, Any], smoke_gate: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = (
        not issues
        and regression_queue.get("regression_queue_status") == REGRESSION_QUEUE_STATUS
        and gui_plan.get("gui_controller_call_site_installation_plan_status") == GUI_CALL_SITE_PLAN_STATUS
        and smoke_gate.get("named_site_smoke_approval_gate_status") == NAMED_SITE_SMOKE_GATE_STATUS
    )
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_priority_fixture_regression_promotion_id": promotion_id,
        "priority_dispatch_receipts_promoted": ready,
        "regular_regression_queue_ready": ready,
        "gui_controller_call_site_installation_plan_ready": ready,
        "named_site_smoke_still_approval_gated": True,
        "credential_references_preserved_redacted": True,
        "required_next_stage": "regular_regression_queue_installation_and_gui_controller_call_site_wiring" if ready else "priority_fixture_regression_promotion_review",
        "fixture_pack_count": regression_queue.get("fixture_pack_count", 0),
        "promoted_regression_queue_row_count": regression_queue.get("promoted_regression_queue_row_count", 0),
        "call_site_installation_row_count": gui_plan.get("call_site_installation_row_count", 0),
        "named_site_smoke_gate_row_count": smoke_gate.get("named_site_smoke_gate_row_count", 0),
    }


def build_source_adapter_priority_fixture_regression_promotion(
    priority_fixture_pack_implementation_package: Mapping[str, Any],
    *,
    operator_id: str = "operator",
    promotion_notes: Sequence[str] | None = None,
) -> SourceAdapterPriorityFixtureRegressionPromotion:
    priority_package = as_mapping(priority_fixture_pack_implementation_package, "priority_fixture_pack_implementation_package")
    issues = _validate_priority_fixture_pack_package(priority_package)
    regression_queue = _build_promoted_regression_queue(priority_package, issues, promotion_notes or [])
    gui_plan = _build_gui_controller_call_site_plan(priority_package, regression_queue, issues)
    smoke_gate = _build_named_site_smoke_approval_gate(priority_package, issues)
    promotion_id = stable_id("source_adapter.priority_fixture_regression_promotion", {
        "priority_fixture_pack_implementation_id": priority_package.get("source_adapter_priority_fixture_pack_implementation_id"),
        "operator_id": operator_id,
        "promoted_regression_queue_row_count": regression_queue.get("promoted_regression_queue_row_count"),
        "named_site_smoke_gate_row_count": smoke_gate.get("named_site_smoke_gate_row_count"),
    })
    handoff = _build_handoff(promotion_id, regression_queue, gui_plan, smoke_gate, issues)
    ready = handoff.get("handoff_status") == HANDOFF_STATUS
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "fixture_pack_count": regression_queue.get("fixture_pack_count", 0),
        "source_dispatch_receipt_count": regression_queue.get("source_dispatch_receipt_count", 0),
        "promoted_regression_queue_row_count": regression_queue.get("promoted_regression_queue_row_count", 0),
        "call_site_installation_row_count": gui_plan.get("call_site_installation_row_count", 0),
        "named_site_smoke_gate_row_count": smoke_gate.get("named_site_smoke_gate_row_count", 0),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Install the promoted regular regression queue in the local regression runner.",
            "Wire GUI/controller call sites from the local installation plan only.",
            "Keep named-site smoke rows blocked until explicit operator approval and named-site inputs are supplied.",
            "Preserve KEYS/ACCOUNTS credential references and redacted reference hashes in every future receipt.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "priority_fixture_regression_promotion_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_priority_fixture_regression_promotion_id": promotion_id,
        "source_adapter_priority_fixture_pack_implementation_id": priority_package.get("source_adapter_priority_fixture_pack_implementation_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": list(issues),
        "promotion_logic": {
            "input_source": "source_adapter_priority_fixture_pack_implementation",
            "priority_dispatch_receipts_promoted_to_regular_regression_queue": True,
            "gui_controller_call_site_installation_plan_built": True,
            "named_site_smoke_approval_gate_preserved": True,
            "keys_accounts_references_preserved_redacted": True,
            "live_execution_blocked": True,
        },
        "source_adapter_priority_fixture_regression_queue": regression_queue,
        "source_adapter_gui_controller_call_site_installation_plan": gui_plan,
        "source_adapter_named_site_smoke_operator_approval_gate": smoke_gate,
        "source_adapter_priority_fixture_regression_promotion_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterPriorityFixtureRegressionPromotion(package)


def example_priority_fixture_regression_promotion_package() -> dict[str, Any]:
    return build_source_adapter_priority_fixture_regression_promotion(
        example_priority_fixture_pack_implementation_package(),
        operator_id="example_operator",
        promotion_notes=["deterministic local regression promotion example"],
    ).as_dict()


def main() -> None:
    package = example_priority_fixture_regression_promotion_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["priority_fixture_regression_promotion_status"] == STATUS
    assert package["source_adapter_priority_fixture_regression_queue"]["regression_queue_status"] == REGRESSION_QUEUE_STATUS
    assert package["source_adapter_priority_fixture_regression_queue"]["promoted_regression_queue_row_count"] == 20
    assert package["source_adapter_named_site_smoke_operator_approval_gate"]["named_site_smoke_gate_row_count"] == 5
    assert package["operator_summary"]["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
    print("Source Adapter Priority Fixture Regression Promotion self-test passed.")


if __name__ == "__main__":
    main()
