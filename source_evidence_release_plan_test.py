from source_evidence_release_plan import (
    build_source_evidence_release_action_plan,
    source_evidence_release_action_plan_to_json,
    validate_source_evidence_release_action_plan,
)
from source_evidence_release_readiness import build_source_evidence_release_readiness


def _readiness():
    return build_source_evidence_release_readiness(
        source_row_id="source_row_1",
        adapter_id="msn",
        selected_modes=("webpage", "comments"),
        execution_gate_status="APPROVAL_REQUIRED",
        execution_gate_action_kinds=("LIVE_SITE_CAPTURE", "BROWSER_AUTOMATION"),
        queue_item_count=3,
        total_export_asset_count=4,
        review_manifest_package_id="source_review",
        queue_review_store_id="evidence_queue_review_store_123",
        created_at_utc="2026-08-08T12:00:00Z",
    )


def test_release_action_plan_records_approval_required_receipts_only() -> None:
    plan = build_source_evidence_release_action_plan(_readiness())
    data = plan.to_dict()

    assert plan.release_status == "RELEASE_APPROVAL_REQUIRED"
    assert plan.operator_signoff_required is True
    assert plan.receipt_count == 4
    assert plan.command_count == 0
    assert plan.release_upload_performed is False
    assert plan.file_library_publish_performed is False
    assert plan.operator_signoff_performed is False
    assert plan.completed_release_claimed is False
    assert plan.file_existence_claimed is False
    assert plan.raw_payload_included is False
    assert data["receipts"][0]["action_status"] == "RELEASE_APPROVAL_REQUIRED"
    assert all(receipt["command_emitted"] is False for receipt in data["receipts"])
    assert {
        receipt["target_kind"] for receipt in data["receipts"]
    } == {
        "total_export_release_manifest",
        "release_upload_target_receipt",
        "file_library_publish_receipt",
        "operator_signoff_receipt",
    }
    validate_source_evidence_release_action_plan(data)

    rendered = source_evidence_release_action_plan_to_json(plan)
    assert rendered == source_evidence_release_action_plan_to_json(plan)
    assert "completed evidence" not in rendered.lower()
    assert "C:\\Users\\fahad" not in rendered


def test_release_action_plan_validation_rejects_completed_release_claims() -> None:
    data = build_source_evidence_release_action_plan(_readiness()).to_dict()
    data["completed_release_claimed"] = True
    try:
        validate_source_evidence_release_action_plan(data)
    except ValueError as error:
        assert "completed_release_claimed" in str(error)
    else:
        raise AssertionError("Completed release claim should be rejected")


def run_self_test() -> None:
    test_release_action_plan_records_approval_required_receipts_only()
    test_release_action_plan_validation_rejects_completed_release_claims()


if __name__ == "__main__":
    run_self_test()
    print("Source evidence release action plan self-test passed.")
