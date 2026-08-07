from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from source_adapter_fixture_pipeline_closeout import write_json_file
from source_adapter_fixture_pipeline_closeout_cli import main
from source_adapter_fixture_pipeline_closeout_test import _passed_pipeline


def test_cli_writes_json_record() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        pipeline_path = base / "pipeline.json"
        out_dir = base / "out"
        write_json_file(pipeline_path, _passed_pipeline())
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--fixture-pipeline-json", str(pipeline_path), "--output-dir", str(out_dir), "--json"])
        assert code == 0
        payload = json.loads(stdout.getvalue())
        assert payload["store_status"] == "STORED"
        assert payload["closeout_status"] == "FIXTURE_PIPELINE_CLOSED"
        assert payload["verification"]["verified"] is True


if __name__ == "__main__":
    test_cli_writes_json_record()
    print("Source Adapter Fixture Pipeline Closeout CLI self-test passed.")
