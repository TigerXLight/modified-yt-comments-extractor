from __future__ import annotations

from source_archive_result_intake import build_source_archive_result_intake


def _handoff_package() -> dict:
    return {
        "schema_version": "source_archive_handoff_v1",
        "handoff_status": "READY_FOR_MANUAL_ARCHIVE_SUBMISSION",
        "archive_handoff_id": "fixture_adapter.archive_handoff.1234",
        "release_audit_id": "fixture_adapter.release_audit.1234",
        "release_index_id": "fixture_adapter.release_index.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "archive_providers": ["archive_today", "ghostarchive"],
        "archive_submission_started": False,
        "manual_or_live_actions_started": False,
    }


def _operator_result(provider_id: str = "archive_today") -> dict:
    return {
        "schema_version": "source_archive_operator_result_v1",
        "provider_id": provider_id,
        "archive_url": "https://archive.example/fixture-story",
        "archive_receipt_filename": "archive_today_receipt.json",
        "archive_screenshot_filename": "archive_today_screenshot.png",
        "operator_notes": ["Operator pasted a manual archive result."],
    }


def test_build_result_intake_ready_for_review() -> None:
    outputs = build_source_archive_result_intake(
        archive_handoff_package=_handoff_package(),
        operator_archive_results=[_operator_result()],
        operator_id="reviewer_one",
        intake_notes=["Ready for archive review."],
    )
    record = outputs.archive_result_intake_record
    assert record["schema_version"] == "source_archive_result_intake_v1"
    assert record["intake_status"] == "READY_FOR_ARCHIVE_REVIEW"
    assert record["archive_result_intake_id"].startswith("fixture_adapter.archive_result_intake.")
    assert record["received_provider_ids"] == ["archive_today"]
    assert record["missing_provider_ids"] == ["ghostarchive"]
    assert record["online_validation_performed"] is False
    assert record["archive_submission_performed_by_app"] is False
    assert record["manual_or_live_actions_started_by_app"] is False
    assert outputs.archive_receipt_index["receipt_count"] == 1
    assert outputs.archive_review_handoff["required_next_stage"] == "source_archive_review"
    assert outputs.operator_summary["status"] == "READY_FOR_ARCHIVE_REVIEW"


def test_rejects_unknown_provider_result() -> None:
    try:
        build_source_archive_result_intake(
            archive_handoff_package=_handoff_package(),
            operator_archive_results=[_operator_result("wayback_machine")],
        )
    except ValueError as exc:
        assert "provider ids not present" in str(exc)
    else:
        raise AssertionError("expected unknown provider result to be rejected")


def test_rejects_path_fields() -> None:
    result = _operator_result()
    result["local_path"] = "C:/secret/receipt.json"
    try:
        build_source_archive_result_intake(
            archive_handoff_package=_handoff_package(),
            operator_archive_results=[result],
        )
    except ValueError as exc:
        assert "must not include local path" in str(exc)
    else:
        raise AssertionError("expected local path field to be rejected")


if __name__ == "__main__":
    test_build_result_intake_ready_for_review()
    test_rejects_unknown_provider_result()
    test_rejects_path_fields()
    print("Source Archive Result Intake self-test passed.")
