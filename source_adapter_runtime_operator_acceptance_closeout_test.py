from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_operator_acceptance_closeout import (
    build_source_adapter_runtime_operator_acceptance_closeout,
    priority_adapter_fixture_catalog,
    runtime_operator_execution_capability_catalog,
)
from source_adapter_runtime_operator_acceptance_closeout_verifier import verify_source_adapter_runtime_operator_acceptance_closeout
from source_adapter_runtime_ui_provider_integration_bridge import build_source_adapter_runtime_ui_provider_integration_bridge
from source_adapter_runtime_ui_provider_integration_bridge_test import fixture_runtime_receipt_review_bridge


def fixture_runtime_ui_provider_integration_bridge() -> dict:
    return build_source_adapter_runtime_ui_provider_integration_bridge(
        fixture_runtime_receipt_review_bridge(),
        operator_id="operator.fixture",
        integration_notes=["bind runtime UI/provider surfaces"],
    )


def test_build_runtime_operator_acceptance_closeout() -> None:
    package = build_source_adapter_runtime_operator_acceptance_closeout(
        fixture_runtime_ui_provider_integration_bridge(),
        operator_id="operator.fixture",
        acceptance_notes=["accept runtime surface for controller install and manual smoke"],
    )
    assert package["runtime_operator_acceptance_closeout_status"] == "SOURCE_ADAPTER_RUNTIME_OPERATOR_ACCEPTANCE_CLOSEOUT_BUILT"
    assert package["accepted_capability_count"] == 8
    assert package["source_adapter_runtime_final_closeout_handoff"]["ready_for_manual_live_smoke"] is True
    assert package["source_adapter_gui_controller_binding_manifest"]["keys_accounts_surface_id"] == "keys_accounts.ui.credential_reference_selector"
    assert package["source_adapter_priority_fixture_pack_plan"]["fixture_pack_count"] >= 5
    assert verify_source_adapter_runtime_operator_acceptance_closeout(package)["verified"] is True


def test_capability_subset_acceptance() -> None:
    package = build_source_adapter_runtime_operator_acceptance_closeout(
        fixture_runtime_ui_provider_integration_bridge(),
        enabled_capabilities=["archive_submit", "file_library_publication"],
        operator_id="operator.fixture",
    )
    assert package["accepted_capability_count"] == 2
    assert set(package["source_adapter_runtime_roadmap_closeout_index"]["integrated_capability_ids"]) == {
        "archive_submit",
        "file_library_publication",
    }
    assert verify_source_adapter_runtime_operator_acceptance_closeout(package)["verified"] is True


def test_catalogs_cover_runtime_and_priority_adapters() -> None:
    capability_catalog = runtime_operator_execution_capability_catalog()
    assert "credential_lookup" in capability_catalog
    assert capability_catalog["credential_lookup"]["controller_route_id"].startswith("keys_accounts.controller")
    fixture_catalog = priority_adapter_fixture_catalog()
    assert {row["adapter_id"] for row in fixture_catalog} >= {"article", "social_post", "archive_receipt"}


def test_rejects_wrong_handoff_stage() -> None:
    integration = deepcopy(fixture_runtime_ui_provider_integration_bridge())
    integration["source_adapter_runtime_operator_acceptance_handoff"]["required_next_stage"] = "different_stage"
    try:
        build_source_adapter_runtime_operator_acceptance_closeout(integration)
    except ValueError as exc:
        assert "source_adapter_runtime_operator_acceptance" in str(exc)
    else:
        raise AssertionError("expected wrong handoff rejection")


if __name__ == "__main__":
    test_build_runtime_operator_acceptance_closeout()
    test_capability_subset_acceptance()
    test_catalogs_cover_runtime_and_priority_adapters()
    test_rejects_wrong_handoff_stage()
    print("Source Adapter Runtime Operator Acceptance Closeout self-test passed.")
