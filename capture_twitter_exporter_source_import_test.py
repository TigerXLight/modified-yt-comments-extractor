import json
import tempfile
import zipfile
from pathlib import Path

from capture_twitter_exporter_source_import import (
    TWITTER_EXPORTER_SOURCE_ROW_KIND,
    build_twitter_exporter_source_review_state,
    build_twitter_exporter_source_row_summary,
    import_twitter_exporter_local_paths_for_review,
    preview_twitter_exporter_local_import_source,
    twitter_exporter_source_review_state_to_json,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_source_hook_previews_single_local_export_without_live_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(
            Path(tmp) / "tweet.txt",
            "Text: Source hook tweet\nURL: https://x.com/example/status/123\n",
        )

        state = preview_twitter_exporter_local_import_source((str(source),))
        data = state.to_dict()

        assert data["source_platform"] == "twitter_x"
        assert data["source_kind"] == "local_export"
        assert data["source_row_kind"] == TWITTER_EXPORTER_SOURCE_ROW_KIND
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert data["input_count"] == 1
        assert data["total_parsed_record_count"] == 1
        assert data["file_summaries"][0]["input_file_name"] == "tweet.txt"
        assert data["file_summaries"][0]["input_file_sha256"]
        assert data["file_summaries"][0]["input_file_size_bytes"] == source.stat().st_size
        assert data["live_verification_claimed"] is False
        assert data["api_capture_claimed"] is False
        assert data["browser_capture_claimed"] is False
        assert data["browser_automation_claimed"] is False
        assert data["extension_automation_claimed"] is False
        assert data["archive_claimed"] is False
        assert data["media_download_claimed"] is False
        assert data["screenshot_ocr_claimed"] is False
        assert data["automatic_classification_claimed"] is False
        assert data["network_actions_performed"] == "none"


def test_batch_preview_preserves_input_order_and_independent_errors() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = _write(root / "first.json", json.dumps([{"id": "1", "text": "first"}]))
        second = _write(root / "second.csv", "tweet_id,text\n2,second\n")
        unsupported = _write(root / "third.exe", "not supported")

        state = import_twitter_exporter_local_paths_for_review(
            (str(first), str(unsupported), str(second)),
        )
        data = state.to_dict()

        assert data["input_order"] == "input_order_preserved"
        assert data["input_count"] == 3
        assert data["total_parsed_record_count"] == 2
        assert data["total_error_count"] == 1
        assert [item["input_file_name"] for item in data["file_summaries"]] == [
            "first.json",
            "third.exe",
            "second.csv",
        ]
        assert data["file_summaries"][1]["status"] == "error"
        assert "Unsupported Twitter exporter import file type" in data["file_summaries"][1]["validation_errors"][0]


def test_source_row_summary_is_summary_only_and_does_not_dump_tweet_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(
            Path(tmp) / "tweet.txt",
            "Text: DISTINCTIVE FULL TWEET TEXT MUST NOT APPEAR IN ROW SUMMARY\n"
            "URL: https://x.com/example/status/321\n",
        )

        state = build_twitter_exporter_source_review_state(input_paths=(str(source),))
        summary = build_twitter_exporter_source_row_summary(state)

        assert "Twitter/X exporter local import" in summary
        assert "USER_REVIEW_REQUIRED" in summary
        assert "USER_SUPPLIED_LOCAL_EXPORT" in summary
        assert "Parsed records: 1" in summary
        assert "DISTINCTIVE FULL TWEET TEXT" not in summary
        assert "Live/API/browser/extension/archive/download/OCR/classification claims: none" in summary


def test_queue_metadata_compatibility_remains_review_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.tsv", "tweet_id\ttext\n77\tqueue\n")

        state = preview_twitter_exporter_local_import_source(
            (str(source),),
            as_queue_metadata=True,
        )
        data = state.to_dict()
        review = data["queue_review_items"][0]
        queue = data["queue_items"][0]

        assert data["queue_metadata_requested"] is True
        assert data["queue_metadata_available"] is True
        assert data["file_summaries"][0]["queue_metadata_available"] is True
        assert review["review_status"] == "USER_REVIEW_REQUIRED"
        assert review["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert review["api_capture_claimed"] is False
        assert review["browser_automation_claimed"] is False
        assert review["extension_automation_claimed"] is False
        assert review["archive_provider_result_claimed"] is False
        assert review["downloaded_media_claimed"] is False
        assert review["screenshot_claimed"] is False
        assert review["ocr_claimed"] is False
        assert review["automatic_classification"] is False
        assert queue["item_status"] == "NEEDS_REVIEW"
        assert queue["local_path"] == ""


def test_missing_directory_unsafe_zip_and_unsupported_inputs_report_validation_errors() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        missing = root / "missing.txt"
        unsupported = _write(root / "export.exe", "unsupported")
        unsafe_zip = root / "unsafe.zip"
        with zipfile.ZipFile(unsafe_zip, "w") as archive:
            archive.writestr("../evil.txt", "Text: unsafe")

        state = preview_twitter_exporter_local_import_source(
            (str(missing), str(root), str(unsupported), str(unsafe_zip)),
        )
        data = state.to_dict()

        assert data["total_error_count"] == 4
        errors = [
            item["validation_errors"][0]
            for item in data["file_summaries"]
            if item["validation_errors"]
        ]
        assert any("does not exist" in error for error in errors)
        assert any("requires a file path" in error for error in errors)
        assert any("Unsupported Twitter exporter import file type" in error for error in errors)
        assert any("Unsafe zip member path rejected" in error for error in errors)
        assert all(item["parsed_record_count"] == 0 for item in data["file_summaries"])


def test_empty_batch_is_rejected_by_source_hook() -> None:
    try:
        preview_twitter_exporter_local_import_source(())
    except ValueError as exc:
        assert "At least one --input file is required." in str(exc)
    else:
        raise AssertionError("empty source import batch should fail")


def test_source_review_json_is_deterministic_and_omits_record_payloads() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweets.jsonl", json.dumps({"id": "500", "text": "jsonl text"}) + "\n")

        first = twitter_exporter_source_review_state_to_json(
            build_twitter_exporter_source_review_state(input_paths=(str(source),))
        )
        second = twitter_exporter_source_review_state_to_json(
            build_twitter_exporter_source_review_state(input_paths=(str(source),))
        )
        data = json.loads(first)

        assert first == second
        assert "records" not in data["file_summaries"][0]
        assert "jsonl text" not in first


def run_self_test() -> None:
    test_source_hook_previews_single_local_export_without_live_claims()
    test_batch_preview_preserves_input_order_and_independent_errors()
    test_source_row_summary_is_summary_only_and_does_not_dump_tweet_text()
    test_queue_metadata_compatibility_remains_review_only()
    test_missing_directory_unsafe_zip_and_unsupported_inputs_report_validation_errors()
    test_empty_batch_is_rejected_by_source_hook()
    test_source_review_json_is_deterministic_and_omits_record_payloads()


if __name__ == "__main__":
    run_self_test()
    print("Capture Twitter exporter source import self-test passed.")
