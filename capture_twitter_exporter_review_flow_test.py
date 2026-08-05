import json
import tempfile
from pathlib import Path

from capture_twitter_exporter_review_flow import (
    build_twitter_exporter_local_review_flow,
    build_twitter_exporter_review_flow_summary,
    twitter_exporter_review_flow_to_json,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _flow_for_paths(*paths: Path, timestamp: str = "2026-08-06T13:00:00Z"):
    return build_twitter_exporter_local_review_flow(
        tuple(str(path) for path in paths),
        session_id="session-twitter-exporter-flow",
        timestamp_utc=timestamp,
        previous_event_hash="previous_flow_hash",
        actor_id="app",
        app_version="test",
    )


def test_single_synthetic_local_export_runs_end_to_end_summary_flow() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = _write(
            root / "tweet.json",
            json.dumps([{"id": "8101", "text": "DO NOT INCLUDE THIS TWEET TEXT"}]),
        )

        flow = _flow_for_paths(source)
        data = flow.to_dict()
        rendered = twitter_exporter_review_flow_to_json(flow)
        summary = build_twitter_exporter_review_flow_summary(flow)
        file_summary = data["file_summaries"][0]

        assert data["status"] == "USER_REVIEW_REQUIRED"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert data["source_review_summary"]["total_parsed_record_count"] == 1
        assert data["queue_draft_summary"]["eligible_input_count"] == 1
        assert data["manifest_report_summary"]["entry_count"] == 1
        assert data["action_receipt_summary"]["result"] == "USER_REVIEW_REQUIRED"
        assert file_summary["input_file_name"] == "tweet.json"
        assert file_summary["input_file_sha256"]
        assert file_summary["input_file_size_bytes"] == source.stat().st_size
        assert file_summary["queue_draft_item_id"]
        assert file_summary["manifest_entry_id"]
        assert file_summary["receipt_queue_draft_item_id"] == file_summary["queue_draft_item_id"]
        assert "DO NOT INCLUDE THIS TWEET TEXT" not in rendered
        assert "DO NOT INCLUDE THIS TWEET TEXT" not in summary
        assert str(root) not in rendered
        assert str(root) not in summary
        assert '"records"' not in rendered


def test_batch_review_flow_ordering_and_serialization_are_deterministic() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = _write(root / "first.csv", "tweet_id,text\n1,first\n")
        second = _write(root / "second.jsonl", json.dumps({"id": "2", "text": "second"}) + "\n")

        first_flow = _flow_for_paths(first, second)
        second_flow = _flow_for_paths(first, second)
        first_json = twitter_exporter_review_flow_to_json(first_flow)
        second_json = twitter_exporter_review_flow_to_json(second_flow)
        data = json.loads(first_json)

        assert first_json == second_json
        assert [item["input_file_name"] for item in data["file_summaries"]] == [
            "first.csv",
            "second.jsonl",
        ]
        assert data["source_review_summary"]["total_parsed_record_count"] == 2
        assert data["queue_draft_summary"]["eligible_input_count"] == 2
        assert data["manifest_report_summary"]["entry_count"] == 2
        assert data["action_receipt_summary"]["queue_draft_count"] == 2


def test_review_flow_is_summary_only_without_payloads_paths_or_unsupported_content() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = _write(
            root / "tweet.txt",
            "Text: DISTINCTIVE FLOW BODY MUST STAY OUT\nURL: https://x.com/example/status/812\n",
        )
        unsupported = _write(root / "bad.exe", "RAW UNSUPPORTED EXPORT CONTENT")

        flow = _flow_for_paths(source, unsupported)
        rendered = twitter_exporter_review_flow_to_json(flow)
        summary = build_twitter_exporter_review_flow_summary(flow)

        assert flow.status == "USER_REVIEW_REQUIRED"
        assert flow.queue_draft.eligible_input_count == 1
        assert flow.queue_draft.rejected_input_count == 1
        assert "DISTINCTIVE FLOW BODY" not in rendered
        assert "DISTINCTIVE FLOW BODY" not in summary
        assert "RAW UNSUPPORTED EXPORT CONTENT" not in rendered
        assert "RAW UNSUPPORTED EXPORT CONTENT" not in summary
        assert str(root) not in rendered
        assert str(root) not in summary
        assert '"records"' not in rendered
        assert "Summary/counts only: yes" in summary


def test_review_flow_has_no_false_completion_or_capture_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.csv", "tweet_id,text\n40,claim check\n")

        data = _flow_for_paths(source).to_dict()
        rendered = json.dumps(data, sort_keys=True)

        assert data["live_verification_claimed"] is False
        assert data["api_capture_claimed"] is False
        assert data["browser_automation_claimed"] is False
        assert data["extension_automation_claimed"] is False
        assert data["archive_claimed"] is False
        assert data["archive_provider_result_claimed"] is False
        assert data["downloaded_media_claimed"] is False
        assert data["screenshot_ocr_claimed"] is False
        assert data["screenshot_claimed"] is False
        assert data["ocr_claimed"] is False
        assert data["warc_wacz_claimed"] is False
        assert data["completed_evidence_claimed"] is False
        assert data["evidence_file_move_claimed"] is False
        assert data["automatic_classification_claimed"] is False
        assert data["automatic_classification"] is False
        assert data["network_actions_performed"] == "none"
        assert "completed_evidence\": true" not in rendered
        assert "live_verified\": true" not in rendered
        assert "api_capture_claimed\": true" not in rendered
        assert "browser_automation_claimed\": true" not in rendered
        assert "downloaded_media_claimed\": true" not in rendered


def test_error_only_missing_file_flow_is_review_error_without_successful_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        missing = root / "missing.txt"

        flow = _flow_for_paths(missing)
        data = flow.to_dict()
        rendered = twitter_exporter_review_flow_to_json(flow)
        summary = build_twitter_exporter_review_flow_summary(flow)

        assert data["status"] == "REVIEW_ERROR"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert data["queue_draft_summary"]["draft_status"] == "NO_QUEUE_DRAFT_CREATED"
        assert data["queue_draft_summary"]["eligible_input_count"] == 0
        assert data["manifest_report_summary"]["entry_count"] == 0
        assert data["manifest_report_summary"]["no_entries_reason"] == "NO_QUEUE_DRAFT_CREATED"
        assert data["action_receipt_summary"]["result"] == "REVIEW_ERROR"
        assert data["file_summaries"][0]["input_file_name"] == "missing.txt"
        assert data["file_summaries"][0]["validation_error_count"] == 1
        assert data["completed_evidence_claimed"] is False
        assert str(root) not in rendered
        assert str(root) not in summary


def run_self_test() -> None:
    test_single_synthetic_local_export_runs_end_to_end_summary_flow()
    test_batch_review_flow_ordering_and_serialization_are_deterministic()
    test_review_flow_is_summary_only_without_payloads_paths_or_unsupported_content()
    test_review_flow_has_no_false_completion_or_capture_claims()
    test_error_only_missing_file_flow_is_review_error_without_successful_claims()


if __name__ == "__main__":
    run_self_test()
    print("Capture Twitter exporter review flow self-test passed.")
