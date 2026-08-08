from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_regression_queue_runtime_wiring import (
    HANDOFF_STATUS as RUNTIME_WIRING_HANDOFF_STATUS,
    SCHEMA_VERSION as RUNTIME_WIRING_SCHEMA_VERSION,
    STATUS as RUNTIME_WIRING_STATUS,
    example_regression_queue_runtime_wiring_package,
)

SCHEMA_VERSION = "source_adapter_runtime_queue_closeout_audit_v1"
COVERAGE_MATRIX_SCHEMA_VERSION = "source_adapter_runtime_queue_closeout_coverage_matrix_v1"
ROADMAP_STATE_SCHEMA_VERSION = "source_adapter_runtime_queue_closeout_roadmap_state_v1"
RELEASE_GATE_SCHEMA_VERSION = "source_adapter_runtime_queue_closeout_release_gate_v1"
OPERATOR_HANDOFF_SCHEMA_VERSION = "source_adapter_runtime_queue_closeout_operator_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_runtime_queue_closeout_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_AUDIT_BUILT"
COVERAGE_MATRIX_STATUS = "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_COVERAGE_MATRIX_READY"
ROADMAP_STATE_STATUS = "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_ROADMAP_STATE_UPDATED"
RELEASE_GATE_STATUS = "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_RELEASE_GATE_READY"
OPERATOR_HANDOFF_STATUS = "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_READY_FOR_OPERATOR_APPROVED_NAMED_SITE_SELECTION"
BLOCKED_STATUS = "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_AUDIT_NEEDS_REVIEW"

KEYS_ACCOUNTS_LABEL = "KEYS/ACCOUNTS"
DRY_RUN_MODE = "dry_run"
OPERATOR_APPROVED_MANUAL_SMOKE_MODE = "operator_approved_manual_smoke"


@dataclass(frozen=True)
class SourceAdapterRuntimeQueueCloseoutAudit:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def short_hash(value: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def as_list(value: Any, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{label} must be a list")
    return list(value)


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in as_list(container.get(key), key) if isinstance(row, Mapping)]


def _strings(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in output:
            output.append(text)
    return output


def _validate_wiring_package(runtime_wiring_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if runtime_wiring_package.get("schema_version") != RUNTIME_WIRING_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_runtime_wiring_schema", "severity": "error", "message": "runtime queue wiring schema was not recognised"})
    if runtime_wiring_package.get("regression_queue_runtime_wiring_status") != RUNTIME_WIRING_STATUS:
        issues.append({"issue_id": "runtime_wiring_not_built", "severity": "error", "message": "runtime queue wiring is not built"})
    handoff = runtime_wiring_package.get("source_adapter_regression_queue_runtime_wiring_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != RUNTIME_WIRING_HANDOFF_STATUS:
        issues.append({"issue_id": "runtime_wiring_handoff_not_ready", "severity": "error", "message": "runtime queue wiring handoff is not ready for closeout audit"})
    summary = runtime_wiring_package.get("operator_summary") or {}
    if not isinstance(summary, Mapping) or summary.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "runtime_wiring_keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved by runtime wiring"})
    local_queue = runtime_wiring_package.get("source_adapter_local_regression_runner_queue_installation") or {}
    bindings = runtime_wiring_package.get("source_adapter_runtime_controller_provider_expanded_binding_matrix") or {}
    gui_wiring = runtime_wiring_package.get("source_adapter_gui_controller_call_site_runtime_wiring") or {}
    receipts = runtime_wiring_package.get("source_adapter_local_regression_acceptance_receipt_batch") or {}
    smoke_gate = runtime_wiring_package.get("source_adapter_named_site_smoke_gate_carry_forward") or {}
    if not isinstance(local_queue, Mapping) or len(_rows(local_queue, "local_runner_queue_rows")) != 20:
        issues.append({"issue_id": "local_runner_queue_row_count_mismatch", "severity": "error", "message": "expected twenty local runner queue rows"})
    if not isinstance(bindings, Mapping) or len(_rows(bindings, "expanded_binding_rows")) != 20:
        issues.append({"issue_id": "expanded_binding_row_count_mismatch", "severity": "error", "message": "expected twenty expanded binding rows"})
    if not isinstance(gui_wiring, Mapping) or len(_rows(gui_wiring, "gui_call_site_wiring_rows")) < 4:
        issues.append({"issue_id": "gui_call_site_wiring_row_count_mismatch", "severity": "error", "message": "expected at least four GUI/controller call-site wiring rows"})
    if not isinstance(receipts, Mapping) or len(_rows(receipts, "local_regression_acceptance_receipt_rows")) != 20:
        issues.append({"issue_id": "acceptance_receipt_row_count_mismatch", "severity": "error", "message": "expected twenty local regression acceptance receipts"})
    if not isinstance(smoke_gate, Mapping) or len(_rows(smoke_gate, "smoke_gate_carry_forward_rows")) != 5:
        issues.append({"issue_id": "smoke_gate_row_count_mismatch", "severity": "error", "message": "expected five named-site smoke gate rows"})
    return issues


def _build_coverage_matrix(runtime_wiring_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    local_queue = runtime_wiring_package.get("source_adapter_local_regression_runner_queue_installation") or {}
    bindings = runtime_wiring_package.get("source_adapter_runtime_controller_provider_expanded_binding_matrix") or {}
    gui_wiring = runtime_wiring_package.get("source_adapter_gui_controller_call_site_runtime_wiring") or {}
    receipts = runtime_wiring_package.get("source_adapter_local_regression_acceptance_receipt_batch") or {}
    smoke_gate = runtime_wiring_package.get("source_adapter_named_site_smoke_gate_carry_forward") or {}
    handoff = runtime_wiring_package.get("source_adapter_regression_queue_runtime_wiring_handoff") or {}
    row_specs = [
        ("local_regression_runner_queue", local_queue, "local_runner_queue_row_count", 20, "SOURCE_ADAPTER_LOCAL_REGRESSION_RUNNER_QUEUE_INSTALLED"),
        ("expanded_controller_provider_bindings", bindings, "expanded_binding_row_count", 20, "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_EXPANDED_BINDINGS_READY"),
        ("gui_controller_call_site_wiring", gui_wiring, "call_site_wiring_row_count", 4, "SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITES_WIRED_FOR_LOCAL_DRY_RUN"),
        ("local_regression_acceptance_receipts", receipts, "acceptance_receipt_row_count", 20, "SOURCE_ADAPTER_LOCAL_REGRESSION_ACCEPTANCE_RECEIPTS_READY"),
        ("named_site_smoke_approval_gate", smoke_gate, "named_site_smoke_gate_row_count", 5, "SOURCE_ADAPTER_NAMED_SITE_SMOKE_APPROVAL_GATE_CARRIED_FORWARD_UNEXECUTED"),
        ("runtime_wiring_handoff", handoff, "local_runner_queue_row_count", 20, RUNTIME_WIRING_HANDOFF_STATUS),
    ]
    rows: list[dict[str, Any]] = []
    for index, (coverage_area, source, count_field, expected_count, expected_status) in enumerate(row_specs):
        source_mapping = source if isinstance(source, Mapping) else {}
        observed_count = int(source_mapping.get(count_field, 0) or 0)
        status_values = _strings(value for key, value in source_mapping.items() if key.endswith("status"))
        area_ready = observed_count >= expected_count and expected_status in status_values or source_mapping.get("handoff_status") == expected_status
        rows.append({
            "schema_version": "source_adapter_runtime_queue_closeout_coverage_matrix_row_v1",
            "row_index": index,
            "coverage_row_id": stable_id("source_adapter.runtime_queue_closeout_coverage_row", {"area": coverage_area, "count": observed_count}),
            "coverage_area": coverage_area,
            "source_artifact_schema_version": source_mapping.get("schema_version"),
            "expected_status": expected_status,
            "observed_status_values": status_values,
            "expected_row_count": expected_count,
            "observed_row_count": observed_count,
            "coverage_ready": bool(area_ready),
            "local_only": True,
            "dry_run_only": True,
            "live_execution_allowed": False,
            "network_allowed": False,
            "credential_storage_allowed": False,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    ready_count = sum(1 for row in rows if row["coverage_ready"])
    return {
        "schema_version": COVERAGE_MATRIX_SCHEMA_VERSION,
        "coverage_matrix_status": COVERAGE_MATRIX_STATUS if not issues and ready_count == len(rows) else "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_COVERAGE_MATRIX_NEEDS_REVIEW",
        "coverage_row_count": len(rows),
        "coverage_ready_row_count": ready_count,
        "local_runner_queue_row_count": int(local_queue.get("local_runner_queue_row_count", 0) or 0) if isinstance(local_queue, Mapping) else 0,
        "expanded_binding_row_count": int(bindings.get("expanded_binding_row_count", 0) or 0) if isinstance(bindings, Mapping) else 0,
        "call_site_wiring_row_count": int(gui_wiring.get("call_site_wiring_row_count", 0) or 0) if isinstance(gui_wiring, Mapping) else 0,
        "acceptance_receipt_row_count": int(receipts.get("acceptance_receipt_row_count", 0) or 0) if isinstance(receipts, Mapping) else 0,
        "named_site_smoke_gate_row_count": int(smoke_gate.get("named_site_smoke_gate_row_count", 0) or 0) if isinstance(smoke_gate, Mapping) else 0,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "coverage_rows": rows,
    }


def _build_roadmap_state(runtime_wiring_package: Mapping[str, Any], coverage_matrix: Mapping[str, Any], closeout_notes: Sequence[str]) -> dict[str, Any]:
    handoff = runtime_wiring_package.get("source_adapter_regression_queue_runtime_wiring_handoff") or {}
    return {
        "schema_version": ROADMAP_STATE_SCHEMA_VERSION,
        "roadmap_state_status": ROADMAP_STATE_STATUS,
        "source_adapter_runtime_queue_closeout_marker": "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_AUDIT_RECORDED",
        "source_runtime_wiring_handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
        "completed_local_sections": [
            "priority_fixture_pack_implementation",
            "priority_fixture_regression_promotion",
            "regression_queue_runtime_wiring",
            "runtime_queue_closeout_audit",
        ],
        "document_update_targets": [
            "SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md",
            "SOURCE_EVIDENCE_ROADMAP.md",
            "CURRENT_DEV_STATE.md",
            "PROJECT_CURRENT_STATE_HANDOFF.md",
        ],
        "roadmap_projection": {
            "local_regression_runner_queue_installed": coverage_matrix.get("local_runner_queue_row_count") == 20,
            "expanded_controller_provider_bindings_ready": coverage_matrix.get("expanded_binding_row_count") == 20,
            "gui_controller_call_site_wiring_ready": coverage_matrix.get("call_site_wiring_row_count", 0) >= 4,
            "local_acceptance_receipts_ready": coverage_matrix.get("acceptance_receipt_row_count") == 20,
            "named_site_smoke_still_operator_approval_gated": coverage_matrix.get("named_site_smoke_gate_row_count") == 5,
            "runtime_closeout_audit_recorded": True,
        },
        "remaining_operator_only_work": [
            "choose named priority sites for manual/live smoke",
            "supply explicit operator approval metadata and named-site inputs",
            "capture provider/archive/upload/file-library receipts only after approval",
            "review imported smoke receipts before any release/evidence completion claim",
        ],
        "blocked_automatic_work": [
            "live smoke execution",
            "browser automation",
            "network calls",
            "API calls",
            "archive provider submission",
            "release upload",
            "file-library mutation",
            "credential storage",
            "GUI mutation",
        ],
        "closeout_notes": _strings(closeout_notes),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def _build_release_gate(coverage_matrix: Mapping[str, Any], roadmap_state: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = not issues and coverage_matrix.get("coverage_matrix_status") == COVERAGE_MATRIX_STATUS and roadmap_state.get("roadmap_state_status") == ROADMAP_STATE_STATUS
    return {
        "schema_version": RELEASE_GATE_SCHEMA_VERSION,
        "release_gate_status": RELEASE_GATE_STATUS if ready else "SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_RELEASE_GATE_NEEDS_REVIEW",
        "ready_for_operator_named_site_selection": ready,
        "ready_for_live_smoke_execution": False,
        "ready_for_browser_automation": False,
        "ready_for_network_or_provider_calls": False,
        "ready_for_archive_submission": False,
        "ready_for_release_upload": False,
        "ready_for_file_library_mutation": False,
        "ready_for_credential_storage": False,
        "requires_explicit_operator_approval_before_smoke": True,
        "requires_named_site_inputs_before_smoke": True,
        "requires_receipt_review_after_smoke": True,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "gate_notes": [
            "Local dry-run regression queue closeout is ready for audit review.",
            "The next operational step is selecting named priority sites and supplying explicit operator approval metadata.",
            "This checkpoint did not execute live/provider work yet; those capabilities remain implementation scope and move through operator-approved runtime wiring with receipts.",
        ],
    }


def _build_operator_handoff(coverage_matrix: Mapping[str, Any], roadmap_state: Mapping[str, Any], release_gate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": OPERATOR_HANDOFF_SCHEMA_VERSION,
        "handoff_status": OPERATOR_HANDOFF_STATUS,
        "coverage_matrix_ready": coverage_matrix.get("coverage_matrix_status") == COVERAGE_MATRIX_STATUS,
        "roadmap_state_updated": roadmap_state.get("roadmap_state_status") == ROADMAP_STATE_STATUS,
        "release_gate_ready": release_gate.get("release_gate_status") == RELEASE_GATE_STATUS,
        "local_runner_queue_row_count": coverage_matrix.get("local_runner_queue_row_count"),
        "expanded_binding_row_count": coverage_matrix.get("expanded_binding_row_count"),
        "call_site_wiring_row_count": coverage_matrix.get("call_site_wiring_row_count"),
        "acceptance_receipt_row_count": coverage_matrix.get("acceptance_receipt_row_count"),
        "named_site_smoke_gate_row_count": coverage_matrix.get("named_site_smoke_gate_row_count"),
        "runtime_closeout_complete": True,
        "named_site_smoke_still_approval_gated": True,
        "required_next_stage": "operator_named_site_selection_and_approval_packet_capture",
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def build_source_adapter_runtime_queue_closeout_audit(
    runtime_wiring_package: Mapping[str, Any] | None = None,
    *,
    operator_id: str = "operator",
    closeout_notes: Sequence[str] | None = None,
) -> SourceAdapterRuntimeQueueCloseoutAudit:
    runtime_wiring_package = runtime_wiring_package or example_regression_queue_runtime_wiring_package()
    issues = _validate_wiring_package(runtime_wiring_package)
    coverage_matrix = _build_coverage_matrix(runtime_wiring_package, issues)
    roadmap_state = _build_roadmap_state(runtime_wiring_package, coverage_matrix, closeout_notes or [])
    release_gate = _build_release_gate(coverage_matrix, roadmap_state, issues)
    operator_handoff = _build_operator_handoff(coverage_matrix, roadmap_state, release_gate)
    ready = not issues and release_gate.get("release_gate_status") == RELEASE_GATE_STATUS
    closeout_id = stable_id("source_adapter.runtime_queue_closeout_audit", {
        "runtime_wiring": runtime_wiring_package.get("source_adapter_regression_queue_runtime_wiring_id"),
        "operator": operator_id,
        "coverage": coverage_matrix.get("coverage_ready_row_count"),
    })
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "operator_id": str(operator_id),
        "local_runner_queue_row_count": coverage_matrix.get("local_runner_queue_row_count"),
        "expanded_binding_row_count": coverage_matrix.get("expanded_binding_row_count"),
        "call_site_wiring_row_count": coverage_matrix.get("call_site_wiring_row_count"),
        "acceptance_receipt_row_count": coverage_matrix.get("acceptance_receipt_row_count"),
        "named_site_smoke_gate_row_count": coverage_matrix.get("named_site_smoke_gate_row_count"),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Use the closeout audit as the current roadmap checkpoint.",
            "Choose named priority sites only through an explicit operator approval packet.",
            "Keep named-site smoke unexecuted until named-site inputs and approval metadata are supplied.",
            "Preserve KEYS/ACCOUNTS credential references and redacted reference hashes in future receipts.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "runtime_queue_closeout_audit_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_runtime_queue_closeout_audit_id": closeout_id,
        "source_adapter_regression_queue_runtime_wiring_id": runtime_wiring_package.get("source_adapter_regression_queue_runtime_wiring_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": issues,
        "closeout_logic": {
            "input_source": "source_adapter_regression_queue_runtime_wiring",
            "coverage_matrix_built": True,
            "roadmap_state_update_projected": True,
            "release_gate_built": True,
            "operator_handoff_built": True,
            "local_runner_queue_closeout_complete": True,
            "named_site_smoke_approval_gate_preserved": True,
            "keys_accounts_references_preserved_redacted": True,
            "live_execution_not_executed_in_this_checkpoint": True,
            "all_provider_capabilities_remain_implementation_scope": True,
        },
        "source_adapter_runtime_queue_closeout_coverage_matrix": coverage_matrix,
        "source_adapter_runtime_queue_closeout_roadmap_state": roadmap_state,
        "source_adapter_runtime_queue_closeout_release_gate": release_gate,
        "source_adapter_runtime_queue_closeout_operator_handoff": operator_handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterRuntimeQueueCloseoutAudit(package)


def example_runtime_queue_closeout_audit_package() -> dict[str, Any]:
    return build_source_adapter_runtime_queue_closeout_audit(
        example_regression_queue_runtime_wiring_package(),
        operator_id="example_operator",
        closeout_notes=["deterministic closeout audit example"],
    ).as_dict()


def main() -> None:
    package = example_runtime_queue_closeout_audit_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["runtime_queue_closeout_audit_status"] == STATUS
    assert package["source_adapter_runtime_queue_closeout_coverage_matrix"]["coverage_matrix_status"] == COVERAGE_MATRIX_STATUS
    assert package["source_adapter_runtime_queue_closeout_roadmap_state"]["roadmap_state_status"] == ROADMAP_STATE_STATUS
    assert package["source_adapter_runtime_queue_closeout_release_gate"]["release_gate_status"] == RELEASE_GATE_STATUS
    assert package["source_adapter_runtime_queue_closeout_operator_handoff"]["handoff_status"] == OPERATOR_HANDOFF_STATUS
    assert package["operator_summary"]["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
    print("Source Adapter Runtime Queue Closeout Audit self-test passed.")


if __name__ == "__main__":
    main()
