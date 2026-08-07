from __future__ import annotations

import tempfile
from pathlib import Path

from source_archive_review import build_source_archive_review
from source_archive_review_store import store_source_archive_review


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
                "provider_id": "archive_today",
                "archive_url": "https://archive.ph/example",
                "archive_receipt_filename": "archive_today_receipt.json",
            }
        ],
    }


def test_store_source_archive_review() -> None:
    outputs = build_source_archive_review(archive_result_intake_record=_intake_record())
    with tempfile.TemporaryDirectory() as temp_dir:
        receipt = store_source_archive_review(outputs.as_dict(), Path(temp_dir))
        assert receipt["schema_version"] == "source_archive_review_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 5
        assert receipt["verification"]["verified"] is True
        for stored in receipt["stored_files"]:
            assert (Path(temp_dir) / stored["filename"]).exists()
            assert stored["byte_count"] > 0
            assert len(stored["sha256"]) == 64


if __name__ == "__main__":
    test_store_source_archive_review()
    print("Source Archive Review store self-test passed.")
