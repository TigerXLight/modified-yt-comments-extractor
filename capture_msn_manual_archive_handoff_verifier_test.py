from capture_msn_manual_archive_handoff import build_msn_manual_archive_handoff
from capture_msn_manual_archive_handoff_verifier import verify_msn_manual_archive_handoff


def _fixture_audit():
    return {
        "schema_version": "msn_manual_release_audit_report_v1",
        "audit_status": "MSN_MANUAL_RELEASE_AUDIT_READY",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "audit_report_id": "msn.queue.release.1234.audit.abcdef123456",
        "readiness_issues": [],
    }


def test_verifier_accepts_ready_manual_handoff():
    handoff = build_msn_manual_archive_handoff(
        _fixture_audit(),
        source_url="https://www.msn.com/en-gb/news/example-article/ar-AA123456",
    )
    verification = verify_msn_manual_archive_handoff(handoff)
    assert verification["verified"] is True
    assert verification["issue_count"] == 0


def test_verifier_rejects_completed_template_results():
    handoff = build_msn_manual_archive_handoff(
        _fixture_audit(),
        source_url="https://www.msn.com/en-gb/news/example-article/ar-AA123456",
    )
    handoff["archive_result_template"][0]["archive_url_or_artifact_id"] = "https://archive.ph/example"
    handoff["archive_result_template"][0]["result_status"] = "CAPTURED"
    verification = verify_msn_manual_archive_handoff(handoff)
    assert verification["verified"] is False
    assert "result_template_already_contains_archive_result" in verification["issues"]
    assert "result_template_not_pending" in verification["issues"]


if __name__ == "__main__":
    test_verifier_accepts_ready_manual_handoff()
    test_verifier_rejects_completed_template_results()
    print("MSN manual archive handoff verifier self-test passed.")
