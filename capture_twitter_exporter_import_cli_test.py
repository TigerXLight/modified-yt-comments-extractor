from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import tempfile
import zipfile
from pathlib import Path

from capture_twitter_exporter_import_cli import (
    build_twitter_exporter_import_cli_result,
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


def test_single_file_preview_cli_outputs_safe_summary_without_full_content() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(
            Path(tmp) / "tweet.txt",
            "Text: Do not dump this complete tweet text in preview\n"
            "URL: https://x.com/example/status/123\n"
            "Handle: @example\n",
        )

        exit_code, output = _run_cli(["--input", str(source), "--preview"])

        assert exit_code == 0
        assert "Twitter/X exporter local import preview" in output
        assert "Importer: Twitter Exporter" in output
        assert "Review status: USER_REVIEW_REQUIRED" in output
        assert "Provenance: USER_SUPPLIED_LOCAL_EXPORT" in output
        assert "tweet.txt: ok" in output
        assert "Parsed records: 1" in output
        assert "Network actions performed: none" in output
        assert "API capture claimed: no" in output
        assert "Browser automation claimed: no" in output
        assert "Extension automation claimed: no" in output
        assert "Do not dump this complete tweet text" not in output


def test_json_output_mode_is_deterministic_and_summary_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(
            Path(tmp) / "tweets.json",
            json.dumps({"tweets": [{"tweet_id": "234", "text": "JSON tweet", "username": "user"}]}),
        )

        first_code, first_output = _run_cli(["--input", str(source), "--json"])
        second_code, second_output = _run_cli(["--input", str(source), "--json"])
        first = json.loads(first_output)

        assert first_code == 0
        assert second_code == 0
        assert first_output == second_output
        assert first["total_parsed_record_count"] == 1
        assert first["results"][0]["input_name"] == "tweets.json"
        assert first["results"][0]["review_status"] == "USER_REVIEW_REQUIRED"
        assert first["results"][0]["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert "records" not in first["results"][0]
        assert first["api_capture_claimed"] is False
        assert first["browser_automation_claimed"] is False
        assert first["extension_automation_claimed"] is False
        assert first["live_verification_claimed"] is False


def test_multiple_explicit_inputs_preserve_per_file_identity_and_aggregate_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        first = _write(Path(tmp) / "tweet.txt", "Text: first\nURL: https://x.com/a/status/1\n")
        second = _write(Path(tmp) / "tweet 2.csv", "tweet_id,text,username\n2,second,user\n")

        exit_code, output = _run_cli(["--input", str(first), "--input", str(second), "--json"])
        data = json.loads(output)

        assert exit_code == 0
        assert data["file_count"] == 2
        assert data["input_order"] == "input_order_preserved"
        assert data["total_parsed_record_count"] == 2
        assert [item["input_name"] for item in data["results"]] == ["tweet.txt", "tweet 2.csv"]
        assert all(item["status"] == "ok" for item in data["results"])


def test_zip_input_via_cli_reports_archive_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "1.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("a/tweets.jsonl", json.dumps({"id": "10", "text": "zip tweet"}) + "\n")
            archive.writestr("b/tweets.csv", "tweet_id,text\n11,zip csv\n")

        exit_code, output = _run_cli(["--input", str(zip_path), "--json"])
        data = json.loads(output)

        assert exit_code == 0
        assert data["results"][0]["input_name"] == "1.zip"
        assert data["results"][0]["archive_member_count"] == 2
        assert data["results"][0]["parsed_record_count"] == 2


def test_zip_traversal_is_rejected_through_entry_point() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "unsafe.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("../evil.txt", "Text: unsafe")

        exit_code, output = _run_cli(["--input", str(zip_path), "--json"])
        data = json.loads(output)

        assert exit_code == 1
        assert data["total_error_count"] == 1
        assert data["results"][0]["status"] == "error"
        assert "Unsafe zip member path rejected" in data["results"][0]["validation_errors"][0]
        assert data["total_parsed_record_count"] == 0


def test_size_and_count_limits_are_exposed_through_cli() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "limits.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("one.txt", "Text: one")
            archive.writestr("two.txt", "Text: two")

        exit_code, output = _run_cli(["--input", str(zip_path), "--json", "--max-zip-entries", "1"])
        data = json.loads(output)

        assert exit_code == 1
        assert data["results"][0]["status"] == "error"
        assert "max_zip_entries" in data["results"][0]["validation_errors"][0]


def test_queue_metadata_mode_returns_safe_review_items() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.txt", "Text: queue\nURL: https://x.com/a/status/99\n")

        exit_code, output = _run_cli(["--input", str(source), "--json", "--as-queue-metadata"])
        data = json.loads(output)
        review = data["queue_review_items"][0]
        queue = data["queue_items"][0]

        assert exit_code == 0
        assert data["queue_metadata_requested"] is True
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
        assert queue["item_role"] == "MANUAL_EVIDENCE_NOTE"
        assert queue["item_status"] == "NEEDS_REVIEW"
        assert queue["local_path"] == ""


def test_missing_and_unsupported_inputs_return_clear_validation_results() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        missing = root / "missing.txt"
        unsupported = _write(root / "export.exe", "not supported")

        missing_code, missing_output = _run_cli(["--input", str(missing), "--json"])
        unsupported_code, unsupported_output = _run_cli(["--input", str(unsupported), "--json"])

        assert missing_code == 1
        assert unsupported_code == 1
        assert "does not exist" in json.loads(missing_output)["results"][0]["validation_errors"][0]
        assert "Unsupported Twitter exporter import file type" in json.loads(unsupported_output)["results"][0]["validation_errors"][0]


def test_no_input_uses_argparse_error() -> None:
    code, error = _run_cli_error(["--json"])

    assert code == 2
    assert "At least one --input file is required." in error


def test_helper_result_matches_cli_safety_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.tsv", "tweet_id\ttext\n321\thelper\n")

        result = build_twitter_exporter_import_cli_result(
            input_paths=(str(source),),
            as_queue_metadata=True,
        )

        assert result["total_parsed_record_count"] == 1
        assert result["review_status"] == "USER_REVIEW_REQUIRED"
        assert result["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert result["queue_review_items"]
        assert result["network_actions_performed"] == "none"
        assert result["automatic_classification"] is False


def run_self_test() -> None:
    test_single_file_preview_cli_outputs_safe_summary_without_full_content()
    test_json_output_mode_is_deterministic_and_summary_only()
    test_multiple_explicit_inputs_preserve_per_file_identity_and_aggregate_counts()
    test_zip_input_via_cli_reports_archive_counts()
    test_zip_traversal_is_rejected_through_entry_point()
    test_size_and_count_limits_are_exposed_through_cli()
    test_queue_metadata_mode_returns_safe_review_items()
    test_missing_and_unsupported_inputs_return_clear_validation_results()
    test_no_input_uses_argparse_error()
    test_helper_result_matches_cli_safety_contract()


if __name__ == "__main__":
    run_self_test()
    print("Capture Twitter exporter import CLI self-test passed.")
