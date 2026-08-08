from __future__ import annotations

import contextlib
import io
import json
import tempfile

from source_adapter_operator_approved_execution_runtime_cli import main as cli_main


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cli_main(["--output-dir", tmpdir, "--use-example-inputs", "--operator-id", "cli_tester", "--execution-note", "cli local execution"])
        assert exit_code == 0
        payload = json.loads(buffer.getvalue())
    assert payload["store_status"] == "STORED"
    assert payload["verification"]["verified"] is True
    assert payload["approval_packet_row_count"] == 5
    assert payload["execution_queue_row_count"] == 5
    assert payload["executed_row_count"] == 5
    assert payload["provider_receipt_row_count"] == 25
    package = payload["package"]
    assert package["operator_summary"]["operator_id"] == "cli_tester"
    assert package["source_adapter_provider_execution_receipt_batch"]["provider_receipt_row_count"] == 25
    print("Source Adapter Operator Approved Execution Runtime CLI self-test passed.")


if __name__ == "__main__":
    main()
