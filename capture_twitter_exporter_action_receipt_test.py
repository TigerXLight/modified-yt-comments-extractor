import json
import tempfile
from pathlib import Path

from capture_action_log import compute_action_event_hash
from capture_twitter_exporter_action_receipt import (
    TWITTER_EXPORTER_ACTION_TYPE,
    build_twitter_exporter_action_receipt_summary,
    build_twitter_exporter_import_action_receipt,
    twitter_exporter_action_receipt_to_json,
)
from capture_twitter_exporter_source_import import preview_twitter_exporter_local_import_source


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _receipt_for_paths(*paths: Path, timestamp: str = "2026-08-06T12:00:00Z"):
    state = preview_twitter_exporter_local_import_source(tuple(str(path) for path in paths))
    return build_twitter_exporter_import_action_receipt(
        state,
        session_id="session-twitter-exporter",
        timestamp_utc=timestamp,
        previous_event_hash="previous_hash",
        actor_id="app",
        app_version="test",
    )


def test_single_local_export_review_builds_summary_only_action_receipt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = _write(
            root / "tweet.json",
            json.dumps([{"id": "1201", "text": "DO NOT LOG THIS TWEET BODY"}]),
        )

        receipt = _receipt_for_paths(source)
        data = receipt.to_dict()
        entry = data["file_entries"][0]
        rendered = twitter_exporter_action_receipt_to_json(receipt)
        summary = build_twitter_exporter_action_receipt_summary(receipt)
        event = data["action_log_event"]

        assert data["action_type"] == TWITTER_EXPORTER_ACTION_TYPE
        assert data["result"] == "USER_REVIEW_REQUIRED"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert entry["input_file_name"] == "tweet.json"
        assert entry["input_file_sha256"]
        assert entry["input_file_size_bytes"] == source.stat().st_size
        assert entry["parsed_record_count"] == 1
        assert data["queue_draft_count"] == 1
        assert data["manifest_report_entry_count"] == 1
        assert event["action_type"] == TWITTER_EXPORTER_ACTION_TYPE
        assert event["result"] == "USER_REVIEW_REQUIRED"
        assert event["previous_event_hash"] == "previous_hash"
        assert event["event_hash"] == compute_action_event_hash(
            {key: value for key, value in event.items() if key != "event_hash"}
        )
        assert "DO NOT LOG THIS TWEET BODY" not in rendered
        assert "DO NOT LOG THIS TWEET BODY" not in summary
        assert str(root) not in rendered
        assert '"records"' not in rendered


def test_batch_action_receipt_ordering_and_serialization_are_deterministic() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = _write(root / "first.csv", "tweet_id,text\n1,first\n")
        second = _write(root / "second.jsonl", json.dumps({"id": "2", "text": "second"}) + "\n")

        first_receipt = _receipt_for_paths(first, second)
        second_receipt = _receipt_for_paths(first, second)

        assert twitter_exporter_action_receipt_to_json(first_receipt) == twitter_exporter_action_receipt_to_json(
            second_receipt
        )
        assert [entry.input_file_name for entry in first_receipt.file_entries] == [
            "first.csv",
            "second.jsonl",
        ]
        assert first_receipt.total_parsed_record_count == 2
        assert first_receipt.queue_draft_count == 2
        assert first_receipt.manifest_report_entry_count == 2


def test_receipt_has_no_false_completion_or_capture_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.txt", "Text: claim check\nURL: https://x.com/a/status/70\n")

        data = _receipt_for_paths(source).to_dict()
        rendered = json.dumps(data, sort_keys=True)

        assert data["live_verification_claimed"] is False
        assert data["api_capture_claimed"] is False
        assert data["browser_automation_claimed"] is False
        assert data["extension_automation_claimed"] is False
        assert data["archive_claimed"] is False
        assert data["archive_provider_result_claimed"] is False
        assert data["downloaded_media_claimed"] is False
        assert data["screenshot_ocr_claimed"] is False
        assert data["warc_wacz_claimed"] is False
        assert data["completed_evidence_claimed"] is False
        assert data["evidence_file_move_claimed"] is False
        assert data["automatic_classification_claimed"] is False
        assert "completed_evidence\": true" not in rendered
        assert "live_verified\": true" not in rendered
        assert "api_capture_claimed\": true" not in rendered
        assert "browser_automation_claimed\": true" not in rendered


def test_error_only_receipt_is_review_error_without_full_path_or_evidence_claim() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        unsupported = _write(root / "bad.exe", "unsupported")

        receipt = _receipt_for_paths(unsupported)
        data = receipt.to_dict()
        rendered = twitter_exporter_action_receipt_to_json(receipt)
        summary = build_twitter_exporter_action_receipt_summary(receipt)

        assert data["result"] == "REVIEW_ERROR"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert data["queue_draft_count"] == 0
        assert data["manifest_report_entry_count"] == 0
        assert data["file_entries"][0]["input_file_name"] == "bad.exe"
        assert data["file_entries"][0]["validation_error_count"] == 1
        assert data["completed_evidence_claimed"] is False
        assert str(root) not in rendered
        assert str(root) not in summary
        assert "unsupported" not in rendered
        assert "unsupported" not in summary


def test_receipt_requires_explicit_timestamp_for_stability() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.csv", "tweet_id,text\n33,stable\n")
        state = preview_twitter_exporter_local_import_source((str(source),))

        try:
            build_twitter_exporter_import_action_receipt(
                state,
                session_id="session-twitter-exporter",
                timestamp_utc="",
            )
        except ValueError as exc:
            assert "timestamp_utc" in str(exc)
        else:
            raise AssertionError("timestamp_utc should be explicit")


def run_self_test() -> None:
    test_single_local_export_review_builds_summary_only_action_receipt()
    test_batch_action_receipt_ordering_and_serialization_are_deterministic()
    test_receipt_has_no_false_completion_or_capture_claims()
    test_error_only_receipt_is_review_error_without_full_path_or_evidence_claim()
    test_receipt_requires_explicit_timestamp_for_stability()


if __name__ == "__main__":
    run_self_test()
    print("Capture Twitter exporter action receipt self-test passed.")
