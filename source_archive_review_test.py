from __future__ import annotations

from source_archive_review import build_source_archive_review


def _intake_record() -> dict[str, object]:
    return {
        "schema_version": "source_archive_result_intake_v1",
        "intake_status": "READY_FOR_ARCHIVE_REVIEW",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "release_index_id": "fixture_adapter.release_index.1234",
        "release_audit_id": "fixture_adapter.release_audit.1234",
        "archive_handoff_id": "fixture_adapter.archive_handoff.1234",
        "archive_result_intake_id": "fixture_adapter.archive_result_intake.1234",
        "operator_supplied_results_received": True,
        "online_validation_performed": False,
        "archive_submission_performed_by_app": False,
        "manual_or_live_actions_started_by_app": False,
        "operator_archive_results": [
            {
                "schema_version": "source_archive_operator_result_v1",
                "provider_id": "ghostarchive",
                "archive_url": "https://ghostarchive.org/archive/example",
                "archive_receipt_filename": "ghostarchive_receipt.json",
                "archive_screenshot_filename": "ghostarchive.png",
                "operator_result_supplied": True,
                "online_validation_performed": False,
                "archive_submission_performed_by_app": False,
            }
        ],
    }


def _receipt_index() -> dict[str, object]:
    return {
        "schema_version": "source_archive_receipt_index_v1",
        "archive_result_intake_id": "fixture_adapter.archive_result_intake.1234",
        "receipt_status": "RECEIVED_PENDING_ARCHIVE_REVIEW",
        "online_validation_performed": False,
        "receipt_entries": [
            {
                "archive_receipt_id": "ghostarchive.receipt.1234",
                "provider_id": "ghostarchive",
                "archive_url": "https://ghostarchive.org/archive/example",
                "archive_receipt_filename": "ghostarchive_receipt.json",
                "archive_screenshot_filename": "ghostarchive.png",
                "receipt_status": "RECEIVED_PENDING_ARCHIVE_REVIEW",
            }
        ],
    }


def _review_handoff() -> dict[str, object]:
    return {
        "schema_version": "source_archive_review_handoff_v1",
        "archive_result_intake_id": "fixture_adapter.archive_result_intake.1234",
        "handoff_status": "READY_FOR_ARCHIVE_REVIEW",
        "required_next_stage": "source_archive_review",
        "online_validation_performed": False,
    }


def test_build_approved_archive_review() -> None:
    outputs = build_source_archive_review(
        archive_result_intake_record=_intake_record(),
        archive_receipt_index=_receipt_index(),
        archive_review_handoff=_review_handoff(),
        decision="APPROVED",
        review_notes=["Receipt screenshot visually checked by operator."],
    )
    package = outputs.archive_review_package
    assert package["schema_version"] == "source_archive_review_v1"
    assert package["decision"] == "APPROVED"
    assert package["approved_receipt_count"] == 1
    assert package["online_validation_performed"] is False
    assert package["archive_submission_performed_by_app"] is False
    assert outputs.archive_review_closeout["closeout_status"] == "ARCHIVE_COMPLETE"
    assert outputs.archive_review_closeout["required_next_stage"] == "NONE"


def test_revision_request_keeps_followup_open() -> None:
    outputs = build_source_archive_review(
        archive_result_intake_record=_intake_record(),
        decision="REVISION_REQUESTED",
        review_notes=["Archive receipt did not show the expected page title."],
    )
    assert outputs.archive_review_decision["requires_revision"] is True
    assert outputs.archive_review_closeout["source_pipeline_status"] == "NEEDS_OPERATOR_FOLLOWUP"
    assert outputs.operator_summary["needs_operator_followup"] is True


def test_rejects_local_path_fields() -> None:
    intake = _intake_record()
    results = list(intake["operator_archive_results"])  # type: ignore[index]
    bad = dict(results[0])  # type: ignore[index]
    bad["local_path"] = "C:/secret/receipt.json"
    intake["operator_archive_results"] = [bad]
    try:
        build_source_archive_review(archive_result_intake_record=intake)
    except ValueError as exc:
        assert "local path" in str(exc)
    else:
        raise AssertionError("expected local path rejection")


if __name__ == "__main__":
    test_build_approved_archive_review()
    test_revision_request_keeps_followup_open()
    test_rejects_local_path_fields()
    print("Source Archive Review self-test passed.")
