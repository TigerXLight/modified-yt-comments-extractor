import contextlib
import io
import json
import tempfile

from source_adapter_archive_polling_outcome_receipt_runtime_cli import main


def test_cli_json_output():
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(["--runtime-id", "cli-case", "--json"])
    payload = json.loads(buffer.getvalue())
    assert code == 0
    assert payload["issue_count"] == 0
    assert payload["record"]["runtime_id"] == "cli-case"


def test_cli_write_and_read():
    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/records.jsonl"
        assert main(["--runtime-id", "stored", "--write", path]) == 0
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["--read", path])
    payload = json.loads(buffer.getvalue())
    assert code == 0
    assert payload["records"][0]["runtime_id"] == "stored"


if __name__ == "__main__":
    test_cli_json_output()
    test_cli_write_and_read()
    print("Source Adapter Archive Polling Outcome Receipt Runtime CLI self-test passed.")
