from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

from source_adapter_runtime_controller_provider_closeout import execute_source_adapter_runtime_action

SCHEMA_VERSION = "source_adapter_runtime_fixture_smoke_final_closeout_v1"
DRY_RUN_RECEIPT_BATCH_SCHEMA_VERSION = "source_adapter_runtime_dry_run_receipt_batch_v1"
PRIORITY_FIXTURE_EXECUTION_MATRIX_SCHEMA_VERSION = "source_adapter_priority_fixture_execution_matrix_v1"
MANUAL_LIVE_SMOKE_RUNBOOK_SCHEMA_VERSION = "source_adapter_manual_live_smoke_runbook_v1"
FINAL_ACCEPTANCE_INDEX_SCHEMA_VERSION = "source_adapter_runtime_final_acceptance_index_v1"
ROADMAP_COVERAGE_CLOSEOUT_SCHEMA_VERSION = "source_adapter_runtime_roadmap_coverage_closeout_v1"
FINAL_HANDOFF_SCHEMA_VERSION = "source_adapter_runtime_fixture_smoke_final_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_runtime_fixture_smoke_final_closeout_operator_summary_v1"

FIXTURE_SMOKE_FINAL_CLOSEOUT_STATUS = "SOURCE_ADAPTER_RUNTIME_FIXTURE_SMOKE_FINAL_CLOSEOUT_BUILT"
EXPECTED_INPUT_STATUS = "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_CLOSEOUT_BUILT"
EXPECTED_INPUT_HANDOFF = "SOURCE_ADAPTER_RUNTIME_READY_FOR_PRIORITY_FIXTURES_AND_MANUAL_LIVE_SMOKE"
FINAL_HANDOFF_STATUS = "SOURCE_ADAPTER_RUNTIME_SHARED_SYSTEM_READY_FOR_PRIORITY_SITE_PACKS_AND_OPERATOR_APPROVED_SMOKE"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


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


def _dispatch_rows(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    table = _mapping(package.get("source_adapter_runtime_dispatch_table"), "runtime_dispatch_table")
    rows = [_mapping(row, "runtime_dispatch_row") for row in _list(table.get("runtime_dispatch_rows"))]
    if not rows:
        raise ValueError("runtime dispatch rows are required")
    return rows


def _fixture_seed_rows(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    batch = _mapping(package.get("source_adapter_runtime_fixture_receipt_seed_batch"), "fixture_receipt_seed_batch")
    rows = [_mapping(row, "fixture_receipt_seed") for row in _list(batch.get("fixture_receipt_seed_rows"))]
    if not rows:
        raise ValueError("fixture receipt seed rows are required")
    return rows


def _priority_fixture_seeds(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    bundle = _mapping(package.get("source_adapter_priority_adapter_fixture_seed_bundle"), "priority_fixture_seed_bundle")
    rows = [_mapping(row, "priority_adapter_fixture_seed") for row in _list(bundle.get("priority_adapter_fixture_seeds"))]
    if not rows:
        raise ValueError("priority adapter fixture seeds are required")
    return rows


def _manual_smoke_rows(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    matrix = _mapping(package.get("source_adapter_runtime_manual_live_smoke_execution_matrix"), "manual_live_smoke_execution_matrix")
    rows = [_mapping(row, "manual_live_smoke_execution_row") for row in _list(matrix.get("manual_live_smoke_execution_rows"))]
    if not rows:
        raise ValueError("manual/live smoke execution rows are required")
    return rows


def _approval_rows(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    ledger = _mapping(package.get("source_adapter_runtime_operator_approval_ledger"), "operator_approval_ledger")
    rows = [_mapping(row, "approval_ledger_row") for row in _list(ledger.get("approval_ledger_rows"))]
    if not rows:
        raise ValueError("operator approval ledger rows are required")
    return rows


def _receipt_row(receipt: Mapping[str, Any], seed: Mapping[str, Any], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_runtime_dry_run_receipt_row_v1",
        "capability_id": receipt.get("capability_id"),
        "fixture_receipt_seed_id": seed.get("fixture_receipt_seed_id"),
        "runtime_action_execution_receipt_id": receipt.get("runtime_action_execution_receipt_id"),
        "runtime_dispatch_row_id": receipt.get("runtime_dispatch_row_id"),
        "provider_execution_adapter_id": receipt.get("provider_execution_adapter_id"),
        "controller_route_id": receipt.get("controller_route_id"),
        "execution_mode": receipt.get("execution_mode"),
        "receipt_status": receipt.get("receipt_status"),
        "missing_payload_fields": list(receipt.get("missing_payload_fields") or []),
        "payload_sha256": receipt.get("payload_sha256"),
        "receipt_field_count": len(receipt.get("receipt_body") or {}),
        "receipt_review_status": "ACCEPTED_FOR_LOCAL_FIXTURE_EXECUTION" if not receipt.get("missing_payload_fields") else "PAYLOAD_FIELDS_NEED_FIXTURE_COMPLETION",
        "row_index": index,
    }
    return dict(unsigned, dry_run_receipt_row_id=f"source_adapter.dry_run_receipt.{_stable_hash(unsigned)}")


def _priority_execution_row(seed: Mapping[str, Any], dispatch_rows: list[Mapping[str, Any]], index: int) -> dict[str, Any]:
    dispatch_ids = set(seed.get("runtime_dispatch_row_ids") or [])
    linked_dispatch = [row for row in dispatch_rows if row.get("runtime_dispatch_row_id") in dispatch_ids]
    unsigned = {
        "schema_version": "source_adapter_priority_fixture_execution_row_v1",
        "adapter_id": seed.get("adapter_id"),
        "display_name": seed.get("display_name"),
        "source_kind": seed.get("source_kind"),
        "priority_adapter_fixture_seed_id": seed.get("priority_adapter_fixture_seed_id"),
        "fixture_types": list(seed.get("fixture_types") or []),
        "artifact_roles": list(seed.get("artifact_roles") or []),
        "runtime_dispatch_row_ids": [row.get("runtime_dispatch_row_id") for row in linked_dispatch],
        "capability_ids": [row.get("capability_id") for row in linked_dispatch],
        "expected_pipeline_outputs": list(seed.get("expected_pipeline_outputs") or []),
        "fixture_execution_status": "READY_FOR_SHARED_PIPELINE_FIXTURE_EXECUTION",
        "row_index": index,
    }
    return dict(unsigned, priority_fixture_execution_row_id=f"source_adapter.priority_fixture_execution.{_stable_hash(unsigned)}")


def _manual_runbook_row(smoke: Mapping[str, Any], approval: Mapping[str, Any], dispatch: Mapping[str, Any], index: int) -> dict[str, Any]:
    unsigned = {
        "schema_version": "source_adapter_manual_live_smoke_runbook_row_v1",
        "capability_id": smoke.get("capability_id"),
        "manual_smoke_execution_row_id": smoke.get("manual_smoke_execution_row_id"),
        "manual_smoke_scenario_id": smoke.get("manual_smoke_scenario_id"),
        "runtime_dispatch_row_id": smoke.get("runtime_dispatch_row_id") or dispatch.get("runtime_dispatch_row_id"),
        "controller_route_id": smoke.get("controller_route_id") or dispatch.get("controller_route_id"),
        "provider_execution_adapter_id": smoke.get("provider_execution_adapter_id") or dispatch.get("provider_execution_adapter_id"),
        "operator_approval_id": smoke.get("operator_approval_id") or approval.get("operator_approval_id"),
        "required_operator_inputs": list(smoke.get("required_operator_inputs") or []),
        "expected_receipt_fields": list(smoke.get("expected_receipt_fields") or []),
        "manual_smoke_goal": smoke.get("manual_smoke_goal"),
        "execution_mode": "operator_approved_manual_smoke",
        "operator_named_site_required": True,
        "receipt_capture_required": True,
        "runbook_status": "READY_FOR_OPERATOR_NAMED_SITE_INPUT_AND_APPROVAL",
        "row_index": index,
    }
    return dict(unsigned, manual_live_smoke_runbook_row_id=f"source_adapter.manual_live_smoke_runbook.{_stable_hash(unsigned)}")


def build_source_adapter_runtime_fixture_smoke_final_closeout(
    controller_provider_closeout_package: Mapping[str, Any],
    *,
    enabled_capabilities: Iterable[str] | None = None,
    operator_id: str = "operator",
    closeout_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build the priority fixture, dry-run receipt, manual/live smoke, and roadmap closeout package."""

    package = _mapping(controller_provider_closeout_package, "controller_provider_closeout_package")
    if package.get("runtime_controller_provider_closeout_status") != EXPECTED_INPUT_STATUS:
        raise ValueError("controller/provider closeout package must be SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_CLOSEOUT_BUILT")
    handoff = _mapping(package.get("source_adapter_runtime_controller_provider_final_handoff"), "controller_provider_final_handoff")
    if handoff.get("handoff_status") != EXPECTED_INPUT_HANDOFF:
        raise ValueError("controller/provider final handoff must be SOURCE_ADAPTER_RUNTIME_READY_FOR_PRIORITY_FIXTURES_AND_MANUAL_LIVE_SMOKE")
    if handoff.get("ready_for_priority_fixture_execution") is not True or handoff.get("ready_for_operator_approved_manual_live_smoke") is not True:
        raise ValueError("controller/provider handoff must be ready for priority fixture execution and manual/live smoke")

    selected = _capability_filter(enabled_capabilities)
    operator_id = _safe_id(operator_id, label="operator_id")
    notes = _notes(closeout_notes)

    dispatch_all = _dispatch_rows(package)
    dispatch_rows = [row for row in dispatch_all if selected is None or row.get("capability_id") in selected]
    if not dispatch_rows:
        raise ValueError("at least one runtime dispatch row is required")
    capability_ids = [str(row.get("capability_id") or "") for row in dispatch_rows]
    dispatch_by_capability = _index_by(dispatch_rows, "capability_id")

    fixture_seeds = [row for row in _fixture_seed_rows(package) if row.get("capability_id") in dispatch_by_capability]
    if len(fixture_seeds) != len(dispatch_rows):
        raise ValueError("fixture receipt seed coverage must match selected dispatch capability coverage")

    approval_by_capability = _index_by(_approval_rows(package), "capability_id")
    smoke_by_capability = _index_by(_manual_smoke_rows(package), "capability_id")
    dry_receipts: list[dict[str, Any]] = []
    for index, seed in enumerate(fixture_seeds):
        capability_id = _safe_id(seed.get("capability_id"), label="capability_id")
        payload = deepcopy(_mapping(seed.get("fixture_payload"), "fixture_payload"))
        receipt = execute_source_adapter_runtime_action(
            package,
            capability_id=capability_id,
            payload=payload,
            execution_mode="dry_run",
            operator_id=operator_id,
        )
        dry_receipts.append(_receipt_row(receipt, seed, index))

    priority_execution_rows = [_priority_execution_row(seed, dispatch_rows, index) for index, seed in enumerate(_priority_fixture_seeds(package))]
    smoke_runbook_rows: list[dict[str, Any]] = []
    for index, capability_id in enumerate(capability_ids):
        if capability_id not in smoke_by_capability:
            raise ValueError(f"manual/live smoke row is required for capability: {capability_id}")
        if capability_id not in approval_by_capability:
            raise ValueError(f"operator approval ledger row is required for capability: {capability_id}")
        smoke_runbook_rows.append(
            _manual_runbook_row(smoke_by_capability[capability_id], approval_by_capability[capability_id], dispatch_by_capability[capability_id], index)
        )

    dry_receipt_batch = {
        "schema_version": DRY_RUN_RECEIPT_BATCH_SCHEMA_VERSION,
        "dry_run_receipt_batch_status": "SOURCE_ADAPTER_RUNTIME_DRY_RUN_RECEIPTS_ACCEPTED",
        "dry_run_receipt_count": len(dry_receipts),
        "capability_ids": capability_ids,
        "dry_run_receipt_rows": dry_receipts,
    }
    priority_fixture_matrix = {
        "schema_version": PRIORITY_FIXTURE_EXECUTION_MATRIX_SCHEMA_VERSION,
        "priority_fixture_execution_status": "SOURCE_ADAPTER_PRIORITY_FIXTURE_EXECUTION_MATRIX_READY",
        "priority_fixture_execution_count": len(priority_execution_rows),
        "priority_fixture_execution_rows": priority_execution_rows,
    }
    manual_live_smoke_runbook = {
        "schema_version": MANUAL_LIVE_SMOKE_RUNBOOK_SCHEMA_VERSION,
        "manual_live_smoke_runbook_status": "SOURCE_ADAPTER_MANUAL_LIVE_SMOKE_RUNBOOK_READY",
        "manual_live_smoke_runbook_count": len(smoke_runbook_rows),
        "execution_mode": "operator_approved_manual_smoke",
        "capability_ids": capability_ids,
        "manual_live_smoke_runbook_rows": smoke_runbook_rows,
    }
    final_acceptance_index = {
        "schema_version": FINAL_ACCEPTANCE_INDEX_SCHEMA_VERSION,
        "final_acceptance_status": "SOURCE_ADAPTER_RUNTIME_LOCAL_FIXTURE_AND_SMOKE_PLAN_ACCEPTED",
        "capability_count": len(capability_ids),
        "dry_run_receipt_count": len(dry_receipts),
        "priority_fixture_execution_count": len(priority_execution_rows),
        "manual_live_smoke_runbook_count": len(smoke_runbook_rows),
        "accepted_local_receipt_count": sum(1 for row in dry_receipts if row.get("receipt_review_status") == "ACCEPTED_FOR_LOCAL_FIXTURE_EXECUTION"),
        "capability_ids": capability_ids,
        "operator_id": operator_id,
    }
    roadmap_coverage_closeout = {
        "schema_version": ROADMAP_COVERAGE_CLOSEOUT_SCHEMA_VERSION,
        "roadmap_coverage_status": "SOURCE_ADAPTER_SHARED_RUNTIME_AND_FIXTURE_SMOKE_CLOSEOUT_READY",
        "closed_sections": [
            "shared_adapter_pipeline_end_to_end",
            "runtime_wiring",
            "runtime_receipt_review",
            "runtime_ui_provider_integration",
            "runtime_operator_acceptance",
            "runtime_controller_provider_installation",
            "runtime_dispatch_dry_run_receipts",
            "priority_fixture_execution_matrix",
            "manual_live_smoke_runbook",
        ],
        "capability_count": len(capability_ids),
        "priority_fixture_family_count": len(priority_execution_rows),
        "manual_smoke_scenario_count": len(smoke_runbook_rows),
        "runtime_receipt_coverage_complete": len(dry_receipts) == len(capability_ids),
        "keys_accounts_lookup_surface": "keys_accounts.ui.credential_reference_selector",
        "remaining_operator_actions": [
            "choose named priority sites for manual/live smoke",
            "enter operator-approved inputs for each smoke row",
            "capture provider receipts for operator-approved executions",
        ],
    }
    final_handoff = {
        "schema_version": FINAL_HANDOFF_SCHEMA_VERSION,
        "handoff_status": FINAL_HANDOFF_STATUS,
        "required_next_stage": "operator_named_priority_sites_and_live_smoke_execution",
        "ready_for_named_priority_site_fixture_authoring": True,
        "ready_for_operator_approved_manual_live_smoke": True,
        "ready_for_runtime_dispatch_receipt_capture": True,
        "capability_ids": capability_ids,
        "manual_live_smoke_runbook_row_ids": [row["manual_live_smoke_runbook_row_id"] for row in smoke_runbook_rows],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": FIXTURE_SMOKE_FINAL_CLOSEOUT_STATUS,
        "capability_count": len(capability_ids),
        "dry_run_receipt_count": len(dry_receipts),
        "priority_fixture_execution_count": len(priority_execution_rows),
        "manual_live_smoke_runbook_count": len(smoke_runbook_rows),
        "next_actions": [
            "Author the named priority site fixture packs against the priority fixture execution matrix.",
            "Run local fixture packs through the runtime dispatch receipt checks.",
            "Run manual/live smoke only from named operator-approved rows and preserve receipts.",
            "Use KEYS/ACCOUNTS credential references rather than raw credential values in receipts.",
        ],
    }

    unsigned_package = {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_runtime_controller_provider_closeout_id": package.get("source_adapter_runtime_controller_provider_closeout_id", ""),
        "runtime_fixture_smoke_final_closeout_status": FIXTURE_SMOKE_FINAL_CLOSEOUT_STATUS,
        "capability_count": len(capability_ids),
        "issue_count": 0,
        "issues": [],
        "source_adapter_runtime_dry_run_receipt_batch": dry_receipt_batch,
        "source_adapter_priority_fixture_execution_matrix": priority_fixture_matrix,
        "source_adapter_manual_live_smoke_runbook": manual_live_smoke_runbook,
        "source_adapter_runtime_final_acceptance_index": final_acceptance_index,
        "source_adapter_runtime_roadmap_coverage_closeout": roadmap_coverage_closeout,
        "source_adapter_runtime_fixture_smoke_final_handoff": final_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "input_source": "source_adapter_runtime_controller_provider_closeout",
            "dry_run_dispatch_executed_for_each_capability": True,
            "priority_fixture_execution_matrix_built": True,
            "manual_live_smoke_runbook_built": True,
            "keys_accounts_surface_preserved": True,
            "multi_capability_batch_supported": True,
        },
        "closeout_notes": notes,
    }
    return dict(
        unsigned_package,
        source_adapter_runtime_fixture_smoke_final_closeout_id=f"source_adapter_runtime_fixture_smoke_final_closeout.{_stable_hash(unsigned_package)}",
    )


def runtime_fixture_smoke_capabilities(package: Mapping[str, Any]) -> list[str]:
    built = _mapping(package, "fixture_smoke_final_closeout_package")
    index = _mapping(built.get("source_adapter_runtime_final_acceptance_index"), "final_acceptance_index")
    return [str(value) for value in _list(index.get("capability_ids"))]


def main() -> None:
    from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout
    from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
    from source_adapter_runtime_fixture_smoke_final_closeout_verifier import verify_source_adapter_runtime_fixture_smoke_final_closeout

    controller = build_source_adapter_runtime_controller_provider_closeout(
        fixture_runtime_operator_acceptance_closeout(), operator_id="operator.fixture"
    )
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(controller, operator_id="operator.fixture")
    verification = verify_source_adapter_runtime_fixture_smoke_final_closeout(package)
    if not verification["verified"]:
        raise SystemExit(verification)
    print("Source Adapter Runtime Fixture Smoke Final Closeout self-test passed.")


if __name__ == "__main__":
    main()
