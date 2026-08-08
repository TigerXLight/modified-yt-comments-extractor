from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_receipt_review_bridge import build_source_adapter_runtime_receipt_review_bridge
from source_adapter_runtime_receipt_review_bridge_test import fixture_runtime_wiring_bridge
from source_adapter_runtime_ui_provider_integration_bridge import (
    build_source_adapter_runtime_ui_provider_integration_bridge,
    runtime_ui_provider_surface_catalog,
)
from source_adapter_runtime_ui_provider_integration_bridge_verifier import verify_source_adapter_runtime_ui_provider_integration_bridge


def fixture_runtime_receipt_review_bridge() -> dict:
    return build_source_adapter_runtime_receipt_review_bridge(
        fixture_runtime_wiring_bridge(),
        reviewer_id="operator.fixture",
        review_notes=["accept runtime receipts for integration"],
    )


def test_build_runtime_ui_provider_integration_bridge() -> None:
    package = build_source_adapter_runtime_ui_provider_integration_bridge(
        fixture_runtime_receipt_review_bridge(),
        operator_id="operator.fixture",
        integration_notes=["bind shared UI/provider surfaces"],
    )
    assert package["runtime_ui_provider_integration_status"] == "SOURCE_ADAPTER_RUNTIME_UI_PROVIDER_INTEGRATIONS_BUILT"
    assert package["integrated_capability_count"] == 8
    assert package["source_adapter_runtime_operator_acceptance_handoff"]["handoff_status"] == "SOURCE_ADAPTER_RUNTIME_READY_FOR_OPERATOR_ACCEPTANCE"
    assert verify_source_adapter_runtime_ui_provider_integration_bridge(package)["verified"] is True


def test_capability_subset() -> None:
    package = build_source_adapter_runtime_ui_provider_integration_bridge(
        fixture_runtime_receipt_review_bridge(),
        enabled_capabilities=["archive_submit", "release_upload"],
    )
    assert package["integrated_capability_count"] == 2
    assert set(package["source_adapter_runtime_ui_provider_binding_index"]["integrated_capability_ids"]) == {"archive_submit", "release_upload"}
    assert verify_source_adapter_runtime_ui_provider_integration_bridge(package)["verified"] is True


def test_surface_catalog_names_keys_accounts() -> None:
    catalog = runtime_ui_provider_surface_catalog()
    assert catalog["credential_lookup"]["ui_surface_id"] == "keys_accounts.ui.credential_reference_selector"
    assert "archive_submit" in catalog


def test_rejects_wrong_handoff_stage() -> None:
    review = deepcopy(fixture_runtime_receipt_review_bridge())
    review["source_adapter_runtime_acceptance_handoff"]["required_next_stage"] = "different_stage"
    try:
        build_source_adapter_runtime_ui_provider_integration_bridge(review)
    except ValueError as exc:
        assert "source_adapter_runtime_ui_provider_integration" in str(exc)
    else:
        raise AssertionError("expected wrong handoff stage rejection")


if __name__ == "__main__":
    test_build_runtime_ui_provider_integration_bridge()
    test_capability_subset()
    test_surface_catalog_names_keys_accounts()
    test_rejects_wrong_handoff_stage()
    print("Source Adapter Runtime UI Provider Integration Bridge self-test passed.")
