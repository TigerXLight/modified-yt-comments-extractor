from capture_msn_manual_archive_handoff import build_msn_manual_archive_handoff


def _fixture_audit():
    return {
        "schema_version": "msn_manual_release_audit_report_v1",
        "audit_status": "MSN_MANUAL_RELEASE_AUDIT_READY",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "audit_report_id": "msn.queue.release.1234.audit.abcdef123456",
        "readiness_issues": [],
        "artifact_quality": {"artifact_quality_passed": True},
    }


def test_archive_handoff_builds_manual_tasks():
    handoff = build_msn_manual_archive_handoff(
        _fixture_audit(),
        source_url="https://www.msn.com/en-gb/news/example-article/ar-AA123456",
        providers=["archive.ph", "ghostarchive", "wayback"],
        operator_label="operator",
    )
    assert handoff["schema_version"] == "msn_manual_archive_handoff_v1"
    assert handoff["archive_handoff_status"] == "MSN_MANUAL_ARCHIVE_HANDOFF_READY"
    assert handoff["provider_count"] == 3
    assert handoff["providers"] == ["archive_today", "ghostarchive", "wayback_machine"]
    assert handoff["archive_handoff_id"].startswith("msn.queue.release.1234.archive_handoff.")
    for task in handoff["archive_tasks"]:
        assert task["task_status"] == "PENDING_OPERATOR_ARCHIVAL"
        assert task["execution_mode"] == "MANUAL_OPERATOR_ONLY"
        assert task["external_call_performed_by_code"] is False


def test_archive_handoff_requires_ready_audit_and_url():
    bad_audit = dict(_fixture_audit())
    bad_audit["audit_status"] = "MSN_MANUAL_RELEASE_AUDIT_REVIEW_REQUIRED"
    handoff = build_msn_manual_archive_handoff(bad_audit, source_url="not-a-url")
    assert handoff["archive_handoff_status"] == "MSN_MANUAL_ARCHIVE_HANDOFF_REVIEW_REQUIRED"
    assert "release_audit_not_ready" in handoff["readiness_issues"]
    assert "invalid_source_url" in handoff["readiness_issues"]


if __name__ == "__main__":
    test_archive_handoff_builds_manual_tasks()
    test_archive_handoff_requires_ready_audit_and_url()
    print("MSN manual archive handoff self-test passed.")
