from __future__ import annotations

from source_archive_review import build_source_archive_review
from source_archive_review_verifier import verify_source_archive_review


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
                "provider_id": "perma_cc",
                "archive_url": "https://perma.cc/ABCD-1234",
                "archive_receipt_filename": "perma_receipt.json",
            }
        ],
    }


def test_verifier_accepts_review_outputs() -> None:
    outputs = build_source_archive_review(archive_result_intake_record=_intake_record())
    verification = verify_source_archive_review(
        outputs.archive_review_package,
        outputs.archive_review_checklist,
        outputs.archive_review_decision,
        outputs.archive_review_closeout,
    )
    assert verification["verified"] is True
    assert verification["issue_count"] == 0


def test_verifier_rejects_online_validation_claim() -> None:
    outputs = build_source_archive_review(archive_result_intake_record=_intake_record())
    package = dict(outputs.archive_review_package)
    package["online_validation_performed"] = True
    verification = verify_source_archive_review(package)
    assert verification["verified"] is False
    assert any("online validation" in issue for issue in verification["issues"])


if __name__ == "__main__":
    test_verifier_accepts_review_outputs()
    test_verifier_rejects_online_validation_claim()
    print("Source Archive Review verifier self-test passed.")
