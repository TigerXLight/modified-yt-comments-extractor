from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_controller_provider_closeout import (
    build_source_adapter_runtime_controller_provider_closeout,
    execute_source_adapter_runtime_action,
    runtime_controller_provider_capabilities,
)
from source_adapter_runtime_controller_provider_closeout_verifier import verify_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_operator_acceptance_closeout import build_source_adapter_runtime_operator_acceptance_closeout
from source_adapter_runtime_operator_acceptance_closeout_test import fixture_runtime_ui_provider_integration_bridge


def fixture_runtime_operator_acceptance_closeout() -> dict:
    return build_source_adapter_runtime_operator_acceptance_closeout(
        fixture_runtime_ui_provider_integration_bridge(),
        operator_id="operator.fixture",
        acceptance_notes=["operator accepted runtime routes for controller/provider installation"],
    )


def test_build_controller_provider_closeout() -> None:
    package = build_source_adapter_runtime_controller_provider_closeout(
        fixture_runtime_operator_acceptance_closeout(),
        operator_id="operator.fixture",
        closeout_notes=["install dispatch table and smoke matrix"],
    )
    assert package["runtime_controller_provider_closeout_status"] == "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_CLOSEOUT_BUILT"
    assert package["capability_count"] == 8
    assert package["source_adapter_runtime_controller_install_manifest"]["keys_accounts_surface_id"] == "keys_accounts.ui.credential_reference_selector"
    assert package["source_adapter_runtime_controller_provider_final_handoff"]["ready_for_operator_approved_manual_live_smoke"] is True
    assert verify_source_adapter_runtime_controller_provider_closeout(package)["verified"] is True


def test_dispatch_dry_run_receipt_and_redaction() -> None:
    package = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    receipt = execute_source_adapter_runtime_action(
        package,
        capability_id="credential_lookup",
        payload={
            "credential_reference_id": "fixture-ref",
            "provider_id": "archivebox",
            "adapter_id": "article",
            "purpose": "manual_smoke",
            "api_key": "secret-value",
        },
        execution_mode="dry_run",
    )
    assert receipt["receipt_status"] == "DRY_RUN_RECEIPT_RECORDED"
    assert receipt["provider_execution_adapter_id"] == "keys_accounts.provider.credential_reference_lookup"
    assert receipt["payload_sha256"]


def test_dispatch_operator_approved_live_requires_matching_approval() -> None:
    package = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    ledger = package["source_adapter_runtime_operator_approval_ledger"]["approval_ledger_rows"]
    approval = next(row["operator_approval_id"] for row in ledger if row["capability_id"] == "archive_submit")
    receipt = execute_source_adapter_runtime_action(
        package,
        capability_id="archive_submit",
        payload={"archive_provider_id": "manual", "source_url": "https://fixture.test/story", "artifact_refs": [], "submit_profile": "fixture"},
        execution_mode="operator_approved_live",
        operator_approval_id=approval,
    )
    assert receipt["receipt_status"] == "OPERATOR_APPROVED_RECEIPT_RECORDED"
    try:
        execute_source_adapter_runtime_action(
            package,
            capability_id="archive_submit",
            payload={"archive_provider_id": "manual"},
            execution_mode="operator_approved_live",
            operator_approval_id="wrong.approval",
        )
    except ValueError as exc:
        assert "operator_approval_id" in str(exc)
    else:
        raise AssertionError("expected approval mismatch rejection")


def test_capability_subset_and_catalog() -> None:
    package = build_source_adapter_runtime_controller_provider_closeout(
        fixture_runtime_operator_acceptance_closeout(),
        enabled_capabilities=["folder_scan", "file_library_publication"],
    )
    assert set(runtime_controller_provider_capabilities(package)) == {"folder_scan", "file_library_publication"}
    assert verify_source_adapter_runtime_controller_provider_closeout(package)["verified"] is True


def test_rejects_wrong_handoff() -> None:
    accepted = deepcopy(fixture_runtime_operator_acceptance_closeout())
    accepted["source_adapter_runtime_final_closeout_handoff"]["required_next_stage"] = "different"
    try:
        build_source_adapter_runtime_controller_provider_closeout(accepted)
    except ValueError as exc:
        assert "source_adapter_runtime_controller_install_and_manual_live_smoke" in str(exc)
    else:
        raise AssertionError("expected wrong next stage rejection")


if __name__ == "__main__":
    test_build_controller_provider_closeout()
    test_dispatch_dry_run_receipt_and_redaction()
    test_dispatch_operator_approved_live_requires_matching_approval()
    test_capability_subset_and_catalog()
    test_rejects_wrong_handoff()
    print("Source Adapter Runtime Controller Provider Closeout self-test passed.")
