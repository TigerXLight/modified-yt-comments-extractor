from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_runtime_fixture_smoke_final_closeout_verifier_v1"
EXPECTED_STATUS = "SOURCE_ADAPTER_RUNTIME_FIXTURE_SMOKE_FINAL_CLOSEOUT_BUILT"
EXPECTED_HANDOFF = "SOURCE_ADAPTER_RUNTIME_SHARED_SYSTEM_READY_FOR_PRIORITY_SITE_PACKS_AND_OPERATOR_APPROVED_SMOKE"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_runtime_fixture_smoke_final_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = _mapping(package)
    if pkg.get("schema_version") != "source_adapter_runtime_fixture_smoke_final_closeout_v1":
        _issue(issues, "package schema_version mismatch")
    if pkg.get("runtime_fixture_smoke_final_closeout_status") != EXPECTED_STATUS:
        _issue(issues, "runtime fixture/smoke final closeout status mismatch")
    closeout_id = str(pkg.get("source_adapter_runtime_fixture_smoke_final_closeout_id") or "")
    if not closeout_id:
        _issue(issues, "source_adapter_runtime_fixture_smoke_final_closeout_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero")

    receipts = _mapping(pkg.get("source_adapter_runtime_dry_run_receipt_batch"))
    receipt_caps: set[str] = set()
    receipt_rows = _list(receipts.get("dry_run_receipt_rows"))
    if receipts.get("schema_version") != "source_adapter_runtime_dry_run_receipt_batch_v1":
        _issue(issues, "dry-run receipt batch schema_version mismatch")
    if receipts.get("dry_run_receipt_count") != len(receipt_rows):
        _issue(issues, "dry-run receipt count mismatch")
    for index, row in enumerate(receipt_rows):
        row_map = _mapping(row)
        cap = str(row_map.get("capability_id") or "")
        receipt_caps.add(cap)
        if row_map.get("receipt_status") != "DRY_RUN_RECEIPT_RECORDED":
            _issue(issues, f"dry-run receipt row {index} status mismatch")
        if _list(row_map.get("missing_payload_fields")):
            _issue(issues, f"dry-run receipt row {index} has missing payload fields")
        if row_map.get("receipt_review_status") != "ACCEPTED_FOR_LOCAL_FIXTURE_EXECUTION":
            _issue(issues, f"dry-run receipt row {index} review status mismatch")

    priority = _mapping(pkg.get("source_adapter_priority_fixture_execution_matrix"))
    priority_rows = _list(priority.get("priority_fixture_execution_rows"))
    if priority.get("schema_version") != "source_adapter_priority_fixture_execution_matrix_v1":
        _issue(issues, "priority fixture execution matrix schema_version mismatch")
    if priority.get("priority_fixture_execution_count") != len(priority_rows):
        _issue(issues, "priority fixture execution count mismatch")
    if len(priority_rows) < 5:
        _issue(issues, "priority fixture execution matrix should cover at least five adapter families")
    for index, row in enumerate(priority_rows):
        row_map = _mapping(row)
        if row_map.get("fixture_execution_status") != "READY_FOR_SHARED_PIPELINE_FIXTURE_EXECUTION":
            _issue(issues, f"priority fixture row {index} status mismatch")
        if not _list(row_map.get("fixture_types")):
            _issue(issues, f"priority fixture row {index} missing fixture types")

    smoke = _mapping(pkg.get("source_adapter_manual_live_smoke_runbook"))
    smoke_rows = _list(smoke.get("manual_live_smoke_runbook_rows"))
    smoke_caps = {str(_mapping(row).get("capability_id") or "") for row in smoke_rows}
    if smoke.get("schema_version") != "source_adapter_manual_live_smoke_runbook_v1":
        _issue(issues, "manual/live smoke runbook schema_version mismatch")
    if smoke.get("manual_live_smoke_runbook_count") != len(smoke_rows):
        _issue(issues, "manual/live smoke runbook count mismatch")
    if smoke_caps != receipt_caps:
        _issue(issues, "manual/live smoke capability set must match dry-run receipt capability set")
    for index, row in enumerate(smoke_rows):
        row_map = _mapping(row)
        if row_map.get("runbook_status") != "READY_FOR_OPERATOR_NAMED_SITE_INPUT_AND_APPROVAL":
            _issue(issues, f"manual/live smoke row {index} runbook status mismatch")
        if row_map.get("receipt_capture_required") is not True:
            _issue(issues, f"manual/live smoke row {index} must require receipt capture")

    acceptance = _mapping(pkg.get("source_adapter_runtime_final_acceptance_index"))
    if acceptance.get("schema_version") != "source_adapter_runtime_final_acceptance_index_v1":
        _issue(issues, "final acceptance index schema_version mismatch")
    if set(acceptance.get("capability_ids") or []) != receipt_caps:
        _issue(issues, "final acceptance capability set mismatch")
    if acceptance.get("accepted_local_receipt_count") != len(receipt_rows):
        _issue(issues, "accepted local receipt count mismatch")

    audit = _mapping(pkg.get("source_adapter_runtime_roadmap_coverage_closeout"))
    if audit.get("schema_version") != "source_adapter_runtime_roadmap_coverage_closeout_v1":
        _issue(issues, "roadmap coverage closeout schema_version mismatch")
    closed = set(audit.get("closed_sections") or [])
    for required in {"runtime_controller_provider_installation", "runtime_dispatch_dry_run_receipts", "priority_fixture_execution_matrix", "manual_live_smoke_runbook"}:
        if required not in closed:
            _issue(issues, f"roadmap coverage closeout missing section: {required}")
    if audit.get("keys_accounts_lookup_surface") != "keys_accounts.ui.credential_reference_selector":
        _issue(issues, "KEYS/ACCOUNTS lookup surface mismatch")

    handoff = _mapping(pkg.get("source_adapter_runtime_fixture_smoke_final_handoff"))
    if handoff.get("schema_version") != "source_adapter_runtime_fixture_smoke_final_handoff_v1":
        _issue(issues, "final handoff schema_version mismatch")
    if handoff.get("handoff_status") != EXPECTED_HANDOFF:
        _issue(issues, "final handoff status mismatch")
    if handoff.get("ready_for_named_priority_site_fixture_authoring") is not True:
        _issue(issues, "final handoff must be ready for named priority site fixture authoring")
    if handoff.get("ready_for_operator_approved_manual_live_smoke") is not True:
        _issue(issues, "final handoff must be ready for operator-approved manual/live smoke")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_fixture_smoke_final_closeout_id": closeout_id,
        "capability_count": len(receipt_caps),
        "dry_run_receipt_count": len(receipt_rows),
        "priority_fixture_execution_count": len(priority_rows),
        "manual_live_smoke_runbook_count": len(smoke_rows),
        "handoff_status": handoff.get("handoff_status", ""),
    }


def main() -> None:
    from source_adapter_runtime_fixture_smoke_final_closeout import build_source_adapter_runtime_fixture_smoke_final_closeout
    from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
    from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout

    controller = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(controller)
    verification = verify_source_adapter_runtime_fixture_smoke_final_closeout(package)
    if not verification["verified"]:
        raise SystemExit(verification)
    print("Source Adapter Runtime Fixture Smoke Final Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
