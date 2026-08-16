from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_case_batch import write_demo_case_batch_json
from profile_media_database_review_report import build_review_report_from_session, render_review_report_text
from profile_media_database_session import ProfileMediaDatabaseSessionConfig, build_database_session_snapshot


def test_review_report_counts_source_gaps_and_disputes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        batch_path = root / "case_batch.json"
        write_demo_case_batch_json(batch_path, database_root=str(root / "db"), case_title="Example Case")
        snapshot = build_database_session_snapshot(
            ProfileMediaDatabaseSessionConfig(
                database_root=str(root / "db"),
                batch_json_files=(str(batch_path),),
                mode="DATABASE",
                text="Example",
            )
        )
        report = build_review_report_from_session(snapshot)
        payload = report.to_dict()
        assert payload["status"] == "success"
        assert payload["source_chain_gap_count"] == 1
        assert payload["disputed_framing_count"] == 1
        assert payload["folder_scan_performed"] is False
        assert payload["folder_move_performed"] is False
        assert payload["folder_rename_performed"] is False
        assert payload["file_copy_performed"] is False
        assert payload["media_download_performed"] is False
        assert payload["automatic_classification_performed"] is False
        assert payload["sensitive_identifier_inference_performed"] is False
        text = render_review_report_text(report)
        assert "source_chain_gap" in text
        assert "disputed_framing" in text


def test_review_report_handles_files_mode_warning_without_reading_batches() -> None:
    snapshot = build_database_session_snapshot(ProfileMediaDatabaseSessionConfig(mode="FILES", batch_json_files=("not-read.json",)))
    report = build_review_report_from_session(snapshot)
    assert report.status == "files_mode_passthrough"
    assert report.warning_count == 1
    assert report.items[0].item_type == "session_warning"


def main() -> int:
    test_review_report_counts_source_gaps_and_disputes()
    test_review_report_handles_files_mode_warning_without_reading_batches()
    print("profile_media_database_review_report v75z OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
