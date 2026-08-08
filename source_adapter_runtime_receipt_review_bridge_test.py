from __future__ import annotations

from copy import deepcopy

from source_adapter_runtime_receipt_review_bridge import build_source_adapter_runtime_receipt_review_bridge
from source_adapter_runtime_receipt_review_bridge_verifier import verify_source_adapter_runtime_receipt_review_bridge
from source_adapter_runtime_wiring_bridge import build_source_adapter_runtime_wiring_bridge
from source_adapter_runtime_wiring_bridge_test import fixture_pipeline_closeout_bridge


def fixture_runtime_wiring_bridge() -> dict:
    return build_source_adapter_runtime_wiring_bridge(
        fixture_pipeline_closeout_bridge(),
        operator_approval_id="approval.runtime.fixture",
        runtime_inputs={
            "fixture_adapter": {
                "artifact_folder": "T:/fixture/artifacts",
                "credential_ref": "keys://archive_today/default",
                "archive_provider_task": {"provider_id": "archive_today"},
                "release_artifact": "release/source.zip",
                "library_destination": "/SourceEvidence/fixture.json",
            }
        },
        operator_notes=["fixture runtime receipts"],
    )


def test_build_runtime_receipt_review_bridge() -> None:
    package = build_source_adapter_runtime_receipt_review_bridge(
        fixture_runtime_wiring_bridge(),
        reviewer_id="operator.fixture",
        review_notes=["accept dry-run receipts"],
    )
    assert package["runtime_receipt_review_status"] == "SOURCE_ADAPTER_RUNTIME_RECEIPTS_REVIEWED"
    assert package["runtime_receipt_review_count"] == 8
    assert package["accepted_review_count"] == 8
    assert package["source_adapter_runtime_acceptance_handoff"]["handoff_status"] == "SOURCE_ADAPTER_RUNTIME_READY_FOR_UI_OR_PROVIDER_INTEGRATION"
    assert verify_source_adapter_runtime_receipt_review_bridge(package)["verified"] is True


def test_accepts_required_capability_subset() -> None:
    wiring = build_source_adapter_runtime_wiring_bridge(
        fixture_pipeline_closeout_bridge(),
        enabled_capabilities=["archive_submit", "release_upload"],
        operator_approval_id="approval.subset.fixture",
    )
    package = build_source_adapter_runtime_receipt_review_bridge(
        wiring,
        required_capabilities=["archive_submit", "release_upload"],
        acceptance_decision="ACCEPTED_WITH_NOTES",
    )
    assert package["accepted_review_count"] == 2
    assert set(package["source_adapter_runtime_acceptance_index"]["accepted_capability_ids"]) == {"archive_submit", "release_upload"}
    assert verify_source_adapter_runtime_receipt_review_bridge(package)["verified"] is True


def test_missing_receipts_are_review_issues() -> None:
    wiring = build_source_adapter_runtime_wiring_bridge(
        fixture_pipeline_closeout_bridge(),
        enabled_capabilities=["operator_url_fetch"],
        execution_mode="plan_only",
    )
    package = build_source_adapter_runtime_receipt_review_bridge(
        wiring,
        required_capabilities=["operator_url_fetch"],
    )
    assert package["runtime_receipt_review_status"] == "SOURCE_ADAPTER_RUNTIME_RECEIPT_REVIEW_HAS_ISSUES"
    assert package["issue_count"] >= 1
    assert verify_source_adapter_runtime_receipt_review_bridge(package)["verified"] is False


def test_rejects_wrong_handoff_stage() -> None:
    wiring = deepcopy(fixture_runtime_wiring_bridge())
    wiring["source_adapter_runtime_execution_handoff"]["required_next_stage"] = "different_stage"
    try:
        build_source_adapter_runtime_receipt_review_bridge(wiring)
    except ValueError as exc:
        assert "source_adapter_runtime_receipt_review" in str(exc)
    else:
        raise AssertionError("expected wrong handoff stage rejection")


if __name__ == "__main__":
    test_build_runtime_receipt_review_bridge()
    test_accepts_required_capability_subset()
    test_missing_receipts_are_review_issues()
    test_rejects_wrong_handoff_stage()
    print("Source Adapter Runtime Receipt Review Bridge self-test passed.")
