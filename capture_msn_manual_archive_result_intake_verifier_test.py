from capture_msn_manual_archive_result_intake import build_msn_manual_archive_result_intake
from capture_msn_manual_archive_result_intake_test import _fixture_handoff
from capture_msn_manual_archive_result_intake_verifier import verify_msn_manual_archive_result_intake


def test_archive_result_intake_verifier_accepts_ready_intake():
    intake = build_msn_manual_archive_result_intake(
        _fixture_handoff(),
        [
            {"provider": "archive_today", "task_id": "task.archive_today", "result_status": "archived", "archive_url_or_artifact_id": "https://archive.ph/example123"},
            {"provider": "ghostarchive", "task_id": "task.ghostarchive", "result_status": "skipped", "failure_reason": "not needed"},
        ],
    )
    verification = verify_msn_manual_archive_result_intake(intake)
    assert verification["verified"] is True
    assert verification["issue_count"] == 0


def test_archive_result_intake_verifier_flags_review_required():
    intake = build_msn_manual_archive_result_intake(_fixture_handoff(), [])
    verification = verify_msn_manual_archive_result_intake(intake)
    assert verification["verified"] is False
    assert "archive_result_intake_not_ready" in verification["issues"]


if __name__ == "__main__":
    test_archive_result_intake_verifier_accepts_ready_intake()
    test_archive_result_intake_verifier_flags_review_required()
    print("MSN manual archive result intake verifier self-test passed.")
