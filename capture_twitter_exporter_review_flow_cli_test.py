from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import tempfile
from pathlib import Path

from capture_twitter_exporter_review_flow_cli import (
    build_twitter_exporter_review_flow_cli_result,
    main,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _run_cli(argv: list[str]) -> tuple[int, str]:
    output = StringIO()
    with redirect_stdout(output):
        exit_code = main(argv)
    return exit_code, output.getvalue()


def _run_cli_error(argv: list[str]) -> tuple[int, str]:
    output = StringIO()
    try:
        with redirect_stderr(output):
            main(argv)
    except SystemExit as exc:
        return int(exc.code), output.getvalue()
    raise AssertionError("Expected argparse SystemExit.")


def test_plain_text_single_input_outputs_safe_full_flow_summary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = _write(
            root / "tweet.txt",
            "Text: DO NOT PRINT THIS CLI TWEET BODY\nURL: https://x.com/a/status/1\n",
        )

        exit_code, output = _run_cli(
            [
                "--input",
                str(source),
                "--show-receipt-id",
                "--show-queue-summary",
                "--show-manifest-summary",
            ]
        )

        assert exit_code == 0
        assert "Twitter/X exporter end-to-end local review flow" in output
        assert "Status: USER_REVIEW_REQUIRED" in output
        assert "Review status: USER_REVIEW_REQUIRED" in output
        assert "Provenance: USER_SUPPLIED_LOCAL_EXPORT" in output
        assert "Queue draft items: 1" in output
        assert "Manifest/report entries: 1" in output
        assert "Action receipt result: USER_REVIEW_REQUIRED" in output
        assert "Receipt ID: twitter_exporter_action_receipt_" in output
        assert "tweet.txt: ok" in output
        assert "Summary/counts only: yes" in output
        assert "Not live verified; not completed evidence." in output
        assert "DO NOT PRINT THIS CLI TWEET BODY" not in output
        assert str(root) not in output


def test_json_single_input_is_deterministic_and_summary_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = _write(
            root / "tweet.json",
            json.dumps([{"id": "20", "text": "JSON CLI BODY MUST STAY OUT"}]),
        )

        first_code, first_output = _run_cli(["--input", str(source), "--json"])
        second_code, second_output = _run_cli(["--input", str(source), "--json"])
        data = json.loads(first_output)

        assert first_code == 0
        assert second_code == 0
        assert first_output == second_output
        assert data["source_review_summary"]["total_parsed_record_count"] == 1
        assert data["queue_draft_summary"]["eligible_input_count"] == 1
        assert data["manifest_report_summary"]["entry_count"] == 1
        assert data["action_receipt_summary"]["result"] == "USER_REVIEW_REQUIRED"
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert "records" not in first_output
        assert "JSON CLI BODY MUST STAY OUT" not in first_output
        assert str(root) not in first_output


def test_batch_input_preserves_order_and_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = _write(root / "first.csv", "tweet_id,text\n1,first\n")
        second = _write(root / "second.jsonl", json.dumps({"id": "2", "text": "second"}) + "\n")

        exit_code, output = _run_cli(["--input", str(first), "--input", str(second), "--json"])
        data = json.loads(output)

        assert exit_code == 0
        assert data["input_count"] == 2
        assert [item["input_file_name"] for item in data["file_summaries"]] == [
            "first.csv",
            "second.jsonl",
        ]
        assert data["source_review_summary"]["total_parsed_record_count"] == 2
        assert data["queue_draft_summary"]["eligible_input_count"] == 2
        assert data["manifest_report_summary"]["entry_count"] == 2


def test_no_input_fails_without_running_scan() -> None:
    code, error = _run_cli_error(["--json"])

    assert code == 2
    assert "At least one --input file is required." in error


def test_missing_file_reports_basename_only_and_fail_on_error_is_nonzero() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        missing = root / "missing.txt"

        default_code, default_output = _run_cli(["--input", str(missing), "--json"])
        fail_code, fail_output = _run_cli(["--input", str(missing), "--json", "--fail-on-error"])
        data = json.loads(default_output)

        assert default_code == 1
        assert fail_code == 1
        assert default_output == fail_output
        assert data["status"] == "REVIEW_ERROR"
        assert data["queue_draft_summary"]["eligible_input_count"] == 0
        assert data["manifest_report_summary"]["entry_count"] == 0
        assert data["action_receipt_summary"]["result"] == "REVIEW_ERROR"
        assert data["file_summaries"][0]["input_file_name"] == "missing.txt"
        assert str(root) not in default_output
        assert "completed_evidence" in default_output
        assert data["completed_evidence_claimed"] is False


def test_mixed_error_batch_is_success_by_default_but_fail_on_error_nonzero() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        valid = _write(root / "valid.tsv", "tweet_id\ttext\n7\tvalid\n")
        invalid = _write(root / "invalid.exe", "UNSUPPORTED CLI RAW BODY")

        default_code, default_output = _run_cli(["--input", str(valid), "--input", str(invalid), "--json"])
        fail_code, fail_output = _run_cli(
            ["--input", str(valid), "--input", str(invalid), "--json", "--fail-on-error"]
        )
        data = json.loads(default_output)

        assert default_code == 0
        assert fail_code == 1
        assert default_output == fail_output
        assert data["status"] == "USER_REVIEW_REQUIRED"
        assert data["queue_draft_summary"]["eligible_input_count"] == 1
        assert data["queue_draft_summary"]["rejected_input_count"] == 1
        assert "UNSUPPORTED CLI RAW BODY" not in default_output
        assert str(root) not in default_output


def test_false_claim_guard_in_plain_text_and_json_output() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.csv", "tweet_id,text\n9,claim guard\n")

        _, text_output = _run_cli(["--input", str(source)])
        _, json_output = _run_cli(["--input", str(source), "--json", "--pretty"])
        data = json.loads(json_output)

        assert "Live/API/browser/extension/archive/download/OCR/WARC/WACZ/classification/completed-evidence claims: none" in text_output
        assert data["live_verification_claimed"] is False
        assert data["api_capture_claimed"] is False
        assert data["browser_automation_claimed"] is False
        assert data["extension_automation_claimed"] is False
        assert data["archive_claimed"] is False
        assert data["downloaded_media_claimed"] is False
        assert data["screenshot_ocr_claimed"] is False
        assert data["warc_wacz_claimed"] is False
        assert data["completed_evidence_claimed"] is False
        assert data["automatic_classification_claimed"] is False
        assert "live_verified\": true" not in json_output
        assert "api_capture_claimed\": true" not in json_output
        assert "browser_automation_claimed\": true" not in json_output


def test_helper_result_matches_cli_safety_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.tsv", "tweet_id\ttext\n321\thelper\n")

        result = build_twitter_exporter_review_flow_cli_result(input_paths=(str(source),))

        assert result["status"] == "USER_REVIEW_REQUIRED"
        assert result["review_status"] == "USER_REVIEW_REQUIRED"
        assert result["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert result["cli_scope"]
        assert result["network_actions_performed"] == "none"
        assert result["source_review_summary"]["total_parsed_record_count"] == 1
        assert result["queue_draft_summary"]["eligible_input_count"] == 1
        assert result["manifest_report_summary"]["entry_count"] == 1
        assert result["action_receipt_summary"]["result"] == "USER_REVIEW_REQUIRED"


def run_self_test() -> None:
    test_plain_text_single_input_outputs_safe_full_flow_summary()
    test_json_single_input_is_deterministic_and_summary_only()
    test_batch_input_preserves_order_and_counts()
    test_no_input_fails_without_running_scan()
    test_missing_file_reports_basename_only_and_fail_on_error_is_nonzero()
    test_mixed_error_batch_is_success_by_default_but_fail_on_error_nonzero()
    test_false_claim_guard_in_plain_text_and_json_output()
    test_helper_result_matches_cli_safety_contract()


if __name__ == "__main__":
    run_self_test()
    print("Capture Twitter exporter review flow CLI self-test passed.")
