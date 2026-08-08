from __future__ import annotations

import contextlib
import io
import json
import tempfile

from source_adapter_provider_backend_interfaces_cli import main as cli_main


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cli_main(["--output-dir", tmpdir, "--operator-id", "cli_tester", "--execution-note", "cli provider backend interfaces"])
        assert exit_code == 0
        payload = json.loads(buffer.getvalue())
    assert payload["store_status"] == "STORED"
    assert payload["verification"]["verified"] is True
    assert payload["provider_backend_request_row_count"] == 25
    assert payload["provider_backend_execution_receipt_row_count"] == 25
    assert payload["package"]["operator_summary"]["operator_id"] == "cli_tester"
    print("Source Adapter Provider Backend Interfaces CLI self-test passed.")


if __name__ == "__main__":
    main()
