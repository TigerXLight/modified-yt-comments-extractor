import json
import tempfile
from pathlib import Path

from capture_twitter_exporter_manifest_report import (
    build_twitter_exporter_manifest_report,
    build_twitter_exporter_manifest_report_text,
    build_twitter_exporter_total_export_manifest,
    twitter_exporter_manifest_report_to_json,
)
from capture_twitter_exporter_source_import import (
    build_twitter_exporter_queue_review_draft,
    preview_twitter_exporter_local_import_source,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _draft_for_paths(*paths: Path):
    return build_twitter_exporter_queue_review_draft(
        preview_twitter_exporter_local_import_source(tuple(str(path) for path in paths))
    )


def test_single_queue_draft_projects_to_manifest_report_metadata_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = _write(
            root / "tweet.json",
            json.dumps([{"id": "701", "text": "DO NOT EXPORT THIS TWEET BODY"}]),
        )

        draft = _draft_for_paths(source)
        report = build_twitter_exporter_manifest_report(draft)
        data = report.to_dict()
        entry = data["entries"][0]
        manifest = build_twitter_exporter_total_export_manifest(draft).to_dict()
        rendered = json.dumps({"manifest": manifest, "report": data}, sort_keys=True)

        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert entry["entry_kind"] == "twitter_x_local_exporter_review_draft"
        assert entry["input_file_name"] == "tweet.json"
        assert entry["input_file_sha256"]
        assert entry["input_file_size_bytes"] == source.stat().st_size
        assert entry["parsed_record_count"] == 1
        assert entry["skipped_record_count"] == 0
        assert entry["warning_count"] == 0
        assert entry["archive_member_count"] == 0
        assert manifest["assets"] == []
        assert manifest["source_urls"] == []
        assert manifest["created_at_utc"] == ""
        assert manifest["archive_results"][0]["review_status"] == "USER_REVIEW_REQUIRED"
        assert "DO NOT EXPORT THIS TWEET BODY" not in rendered
        assert str(root) not in rendered
        assert '"records"' not in rendered


def test_batch_manifest_report_ordering_and_serialization_are_deterministic() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        later = _write(root / "z-later.jsonl", json.dumps({"id": "2", "text": "later"}) + "\n")
        earlier = _write(root / "a-earlier.csv", "tweet_id,text\n1,earlier\n")

        first_report = build_twitter_exporter_manifest_report(_draft_for_paths(later, earlier))
        second_report = build_twitter_exporter_manifest_report(_draft_for_paths(later, earlier))
        first_json = twitter_exporter_manifest_report_to_json(first_report)
        second_json = twitter_exporter_manifest_report_to_json(second_report)

        assert first_json == second_json
        assert [entry.input_file_name for entry in first_report.entries] == [
            "a-earlier.csv",
            "z-later.jsonl",
        ]
        assert first_report.total_parsed_record_count == 2
        assert first_report.total_skipped_record_count == 0


def test_manifest_report_summary_text_is_counts_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = _write(
            root / "tweet.txt",
            "Text: DISTINCTIVE REPORT BODY MUST STAY OUT\nURL: https://x.com/a/status/901\n",
        )

        text = build_twitter_exporter_manifest_report_text(_draft_for_paths(source))

        assert "Twitter/X exporter export manifest review metadata" in text
        assert "Review status: USER_REVIEW_REQUIRED" in text
        assert "Provenance: USER_SUPPLIED_LOCAL_EXPORT" in text
        assert "tweet.txt: 1 parsed" in text
        assert "Summary/counts only: yes" in text
        assert "DISTINCTIVE REPORT BODY" not in text
        assert str(root) not in text


def test_manifest_report_has_no_false_completion_or_capture_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.csv", "tweet_id,text\n404,claim check\n")

        data = build_twitter_exporter_manifest_report(_draft_for_paths(source)).to_dict()
        manifest = build_twitter_exporter_total_export_manifest(_draft_for_paths(source)).to_dict()
        rendered = json.dumps({"manifest": manifest, "report": data}, sort_keys=True)
        entry = data["entries"][0]

        assert entry["live_verification_claimed"] is False
        assert entry["api_capture_claimed"] is False
        assert entry["browser_automation_claimed"] is False
        assert entry["extension_automation_claimed"] is False
        assert entry["archive_claimed"] is False
        assert entry["archive_provider_result_claimed"] is False
        assert entry["downloaded_media_claimed"] is False
        assert entry["screenshot_ocr_claimed"] is False
        assert entry["warc_wacz_claimed"] is False
        assert entry["completed_evidence_claimed"] is False
        assert entry["evidence_file_move_claimed"] is False
        assert entry["automatic_classification_claimed"] is False
        assert "completed_evidence\": true" not in rendered
        assert "live_verified\": true" not in rendered
        assert "api_capture_claimed\": true" not in rendered
        assert "browser_automation_claimed\": true" not in rendered


def test_error_only_draft_creates_review_error_manifest_without_evidence_entries() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        unsupported = _write(Path(tmp) / "bad.exe", "unsupported")

        draft = _draft_for_paths(unsupported)
        report = build_twitter_exporter_manifest_report(draft)
        manifest = build_twitter_exporter_total_export_manifest(draft).to_dict()
        data = report.to_dict()

        assert data["entries"] == []
        assert data["no_entries_reason"] == "NO_QUEUE_DRAFT_CREATED"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert manifest["assets"] == []
        assert manifest["archive_results"] == []
        assert "NO_QUEUE_DRAFT_CREATED" in manifest["notes"]


def run_self_test() -> None:
    test_single_queue_draft_projects_to_manifest_report_metadata_only()
    test_batch_manifest_report_ordering_and_serialization_are_deterministic()
    test_manifest_report_summary_text_is_counts_only()
    test_manifest_report_has_no_false_completion_or_capture_claims()
    test_error_only_draft_creates_review_error_manifest_without_evidence_entries()


if __name__ == "__main__":
    run_self_test()
    print("Capture Twitter exporter manifest report self-test passed.")
