from __future__ import annotations

import json
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from source_adapter_pipeline_closeout_bridge import build_source_adapter_pipeline_closeout_bridge
from source_adapter_pipeline_closeout_bridge_test import fixture_archive_review_bridge
from source_adapter_runtime_wiring_bridge_cli import main


def test_runtime_wiring_bridge_cli() -> None:
    closeout = build_source_adapter_pipeline_closeout_bridge(fixture_archive_review_bridge())
    with tempfile.TemporaryDirectory() as tmp:
        closeout_json = Path(tmp) / "pipeline_closeout.json"
        closeout_json.write_text(json.dumps(closeout, indent=2, sort_keys=True), encoding="utf-8")
        output_dir = Path(tmp) / "out"
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main([
                "--pipeline-closeout-bridge-json",
                str(closeout_json),
                "--output-dir",
                str(output_dir),
                "--operator-approval-id",
                "approval.cli.fixture",
                "--operator-note",
                "CLI runtime wiring fixture",
            ])
        assert code == 0
        result = json.loads(stdout.getvalue())
        assert result["store_status"] == "STORED"
        assert result["runtime_action_count"] == 8
        assert result["runtime_receipt_count"] == 8
        assert len(list(output_dir.glob("*.json"))) == 5


if __name__ == "__main__":
    test_runtime_wiring_bridge_cli()
    print("Source Adapter Runtime Wiring Bridge CLI self-test passed.")
