from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout
from source_adapter_runtime_fixture_smoke_final_closeout import (
    build_source_adapter_runtime_fixture_smoke_final_closeout,
    runtime_fixture_smoke_capabilities,
)
from source_adapter_runtime_fixture_smoke_final_closeout_verifier import verify_source_adapter_runtime_fixture_smoke_final_closeout


def fixture_runtime_controller_provider_closeout() -> dict:
    return build_source_adapter_runtime_controller_provider_closeout(
        fixture_runtime_operator_acceptance_closeout(),
        operator_id="operator.fixture",
        closeout_notes=["fixture controller/provider closeout ready for dry-run receipts and smoke runbook"],
    )


def test_build_fixture_smoke_final_closeout() -> None:
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(
        fixture_runtime_controller_provider_closeout(),
        operator_id="operator.fixture",
        closeout_notes=["final fixture smoke closeout"],
    )
    assert package["runtime_fixture_smoke_final_closeout_status"] == "SOURCE_ADAPTER_RUNTIME_FIXTURE_SMOKE_FINAL_CLOSEOUT_BUILT"
    assert package["capability_count"] == 8
    assert package["source_adapter_runtime_final_acceptance_index"]["accepted_local_receipt_count"] == 8
    assert package["source_adapter_runtime_fixture_smoke_final_handoff"]["ready_for_operator_approved_manual_live_smoke"] is True
    assert verify_source_adapter_runtime_fixture_smoke_final_closeout(package)["verified"] is True


def test_all_dry_run_receipts_are_complete() -> None:
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(fixture_runtime_controller_provider_closeout())
    rows = package["source_adapter_runtime_dry_run_receipt_batch"]["dry_run_receipt_rows"]
    assert len(rows) == 8
    assert {row["receipt_status"] for row in rows} == {"DRY_RUN_RECEIPT_RECORDED"}
    assert all(not row["missing_payload_fields"] for row in rows)


def test_capability_subset() -> None:
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(
        fixture_runtime_controller_provider_closeout(),
        enabled_capabilities=["archive_submit", "credential_lookup"],
    )
    assert set(runtime_fixture_smoke_capabilities(package)) == {"archive_submit", "credential_lookup"}
    assert package["source_adapter_manual_live_smoke_runbook"]["manual_live_smoke_runbook_count"] == 2
    assert verify_source_adapter_runtime_fixture_smoke_final_closeout(package)["verified"] is True


def test_rejects_wrong_handoff() -> None:
    controller = deepcopy(fixture_runtime_controller_provider_closeout())
    controller["source_adapter_runtime_controller_provider_final_handoff"]["handoff_status"] = "different"
    try:
        build_source_adapter_runtime_fixture_smoke_final_closeout(controller)
    except ValueError as exc:
        assert "SOURCE_ADAPTER_RUNTIME_READY_FOR_PRIORITY_FIXTURES_AND_MANUAL_LIVE_SMOKE" in str(exc)
    else:
        raise AssertionError("expected wrong handoff rejection")


def test_priority_fixture_and_runbook_coverage() -> None:
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(fixture_runtime_controller_provider_closeout())
    priority_rows = package["source_adapter_priority_fixture_execution_matrix"]["priority_fixture_execution_rows"]
    runbook_rows = package["source_adapter_manual_live_smoke_runbook"]["manual_live_smoke_runbook_rows"]
    assert len(priority_rows) >= 5
    assert len(runbook_rows) == 8
    assert all(row["operator_named_site_required"] is True for row in runbook_rows)


if __name__ == "__main__":
    test_build_fixture_smoke_final_closeout()
    test_all_dry_run_receipts_are_complete()
    test_capability_subset()
    test_rejects_wrong_handoff()
    test_priority_fixture_and_runbook_coverage()
    print("Source Adapter Runtime Fixture Smoke Final Closeout self-test passed.")
