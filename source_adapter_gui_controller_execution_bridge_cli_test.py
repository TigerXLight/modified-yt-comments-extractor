from __future__ import annotations

import contextlib
import io
import json
import tempfile

from source_adapter_gui_controller_execution_bridge_cli import main as cli_main


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cli_main(["--output-dir", tmpdir, "--operator-id", "cli_tester", "--execution-note", "cli gui controller bridge"])
        assert exit_code == 0
        payload = json.loads(buffer.getvalue())
    assert payload["store_status"] == "STORED"
    assert payload["verification"]["verified"] is True
    assert payload["route_row_count"] == 4
    assert payload["dispatch_receipt_row_count"] == 5
    assert payload["package"]["operator_summary"]["operator_id"] == "cli_tester"
    print("Source Adapter GUI Controller Execution Bridge CLI self-test passed.")


if __name__ == "__main__":
    main()
