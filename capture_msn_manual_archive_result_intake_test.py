from capture_msn_manual_archive_result_intake import build_msn_manual_archive_result_intake


def _fixture_handoff():
    return {
        "schema_version": "msn_manual_archive_handoff_v1",
        "archive_handoff_status": "MSN_MANUAL_ARCHIVE_HANDOFF_READY",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "archive_handoff_id": "msn.queue.release.1234.archive_handoff.abc123",
        "source_url": "https://www.msn.com/en-gb/news/example-article/ar-AA123456",
        "source_url_sha256": "sourcehash",
        "readiness_issues": [],
        "archive_tasks": [
            {"task_id": "task.archive_today", "provider": "archive_today"},
            {"task_id": "task.ghostarchive", "provider": "ghostarchive"},
        ],
    }


def test_archive_result_intake_accepts_manual_results():
    intake = build_msn_manual_archive_result_intake(
        _fixture_handoff(),
        [
            {
                "provider": "archive.ph",
                "task_id": "task.archive_today",
                "result_status": "archived",
                "archive_url_or_artifact_id": "https://archive.ph/example123",
                "captured_at_utc": "2026-08-07T17:30:00Z",
                "operator_label": "operator",
            },
            {
                "provider": "ghostarchive",
                "task_id": "task.ghostarchive",
                "result_status": "failed",
                "failure_reason": "service unavailable",
                "operator_label": "operator",
            },
        ],
    )
    assert intake["schema_version"] == "msn_manual_archive_result_intake_v1"
    assert intake["archive_result_status"] == "MSN_MANUAL_ARCHIVE_RESULTS_READY"
    assert intake["archive_result_summary"]["successful_result_count"] == 1
    assert intake["archive_result_queue_update"]["ready_for_post_archive_review"] is True
    assert intake["archive_result_receipts"][0]["archive_url_or_artifact_sha256"]


def test_archive_result_intake_flags_missing_and_unsafe_results():
    intake = build_msn_manual_archive_result_intake(
        _fixture_handoff(),
        [
            {
                "provider": "archive_today",
                "task_id": "task.archive_today",
                "result_status": "archived",
                "archive_url_or_artifact_id": "C:/Users/fahad/Desktop/archive.html",
                "external_call_performed_by_code": True,
            }
        ],
    )
    assert intake["archive_result_status"] == "MSN_MANUAL_ARCHIVE_RESULTS_REVIEW_REQUIRED"
    assert "absolute_path_detected" in intake["readiness_issues"]
    assert "missing_results_for_handoff_tasks" in intake["readiness_issues"]
    assert any(issue.startswith("external_call_claim_detected") for issue in intake["readiness_issues"])


if __name__ == "__main__":
    test_archive_result_intake_accepts_manual_results()
    test_archive_result_intake_flags_missing_and_unsafe_results()
    print("MSN manual archive result intake self-test passed.")
