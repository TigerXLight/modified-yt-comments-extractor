import tempfile
from pathlib import Path

from capture_msn_manual_archive_handoff import build_msn_manual_archive_handoff
from capture_msn_manual_archive_handoff_store import store_msn_manual_archive_handoff


def _fixture_audit():
    return {
        "schema_version": "msn_manual_release_audit_report_v1",
        "audit_status": "MSN_MANUAL_RELEASE_AUDIT_READY",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "audit_report_id": "msn.queue.release.1234.audit.abcdef123456",
        "readiness_issues": [],
    }


def test_store_archive_handoff_writes_three_files():
    handoff = build_msn_manual_archive_handoff(
        _fixture_audit(),
        source_url="https://www.msn.com/en-gb/news/example-article/ar-AA123456",
        providers=["archive_today", "manual_local_mirror"],
    )
    with tempfile.TemporaryDirectory() as tmp:
        summary = store_msn_manual_archive_handoff(handoff, tmp)
        assert summary["schema_version"] == "msn_manual_archive_handoff_store_v1"
        assert summary["store_status"] == "STORED"
        assert summary["output_file_count"] == 3
        for item in summary["stored_files"]:
            assert Path(tmp, item["filename"]).exists()
            assert item["byte_count"] > 0
            assert len(item["sha256"]) == 64
            assert "\\" not in item["filename"]
            assert "/" not in item["filename"]


if __name__ == "__main__":
    test_store_archive_handoff_writes_three_files()
    print("MSN manual archive handoff store self-test passed.")
