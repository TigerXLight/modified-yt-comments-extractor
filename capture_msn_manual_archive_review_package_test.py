from capture_msn_manual_archive_review_package import (
    ARCHIVE_REVIEW_STATUS_READY,
    ARCHIVE_REVIEW_STATUS_REVIEW_REQUIRED,
    build_msn_manual_archive_review_package,
)
from capture_msn_manual_archive_review_package_cli import _fixture_intake


def test_archive_review_package_ready_from_successful_receipt():
    package = build_msn_manual_archive_review_package(_fixture_intake(), reviewer_label="reviewer")
    assert package["schema_version"] == "msn_manual_archive_review_package_v1"
    assert package["archive_review_status"] == ARCHIVE_REVIEW_STATUS_READY
    assert package["archive_review_package_id"].startswith("msn.queue.release.1234.archive_review.")
    assert package["archive_receipt_index"]["successful_receipt_count"] == 1
    assert package["archive_review_queue_update"]["ready_for_archive_review_decision"] is True
    assert package["next_boundary"] == "msn_manual_archive_review_decision"


def test_archive_review_requires_operator_success_and_no_code_fetch_claim():
    intake = _fixture_intake()
    intake["archive_result_receipts"][0]["external_call_performed_by_code"] = True
    package = build_msn_manual_archive_review_package(intake)
    assert package["archive_review_status"] == ARCHIVE_REVIEW_STATUS_REVIEW_REQUIRED
    assert any(issue.startswith("external_call_claim_detected") for issue in package["readiness_issues"])


def test_archive_review_rejects_absolute_path_artifact():
    intake = _fixture_intake()
    intake["archive_result_receipts"][0]["archive_url_or_artifact_id"] = r"C:\\Users\\fahad\\archive.html"
    package = build_msn_manual_archive_review_package(intake)
    assert package["archive_review_status"] == ARCHIVE_REVIEW_STATUS_REVIEW_REQUIRED
    assert any("unsafe_or_missing_successful_archive_artifact" in issue for issue in package["readiness_issues"])


if __name__ == "__main__":
    test_archive_review_package_ready_from_successful_receipt()
    test_archive_review_requires_operator_success_and_no_code_fetch_claim()
    test_archive_review_rejects_absolute_path_artifact()
    print("MSN manual archive review package self-test passed.")
