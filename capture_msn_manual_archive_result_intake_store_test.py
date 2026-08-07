import tempfile
from pathlib import Path

from capture_msn_manual_archive_result_intake import build_msn_manual_archive_result_intake
from capture_msn_manual_archive_result_intake_store import store_msn_manual_archive_result_intake
from capture_msn_manual_archive_result_intake_test import _fixture_handoff


def test_archive_result_intake_store_writes_expected_files():
    intake = build_msn_manual_archive_result_intake(
        _fixture_handoff(),
        [
            {"provider": "archive_today", "task_id": "task.archive_today", "result_status": "archived", "archive_url_or_artifact_id": "https://archive.ph/example123"},
            {"provider": "ghostarchive", "task_id": "task.ghostarchive", "result_status": "skipped", "failure_reason": "not needed"},
        ],
    )
    with tempfile.TemporaryDirectory() as tmp:
        stored = store_msn_manual_archive_result_intake(intake, tmp)
        assert stored["schema_version"] == "msn_manual_archive_result_intake_store_v1"
        assert stored["store_status"] == "STORED"
        assert stored["output_file_count"] == 4
        assert len(list(Path(tmp).glob("*.json"))) == 4
        assert all(file["sha256"] for file in stored["stored_files"])


if __name__ == "__main__":
    test_archive_result_intake_store_writes_expected_files()
    print("MSN manual archive result intake store self-test passed.")
