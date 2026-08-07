from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from capture_msn_manual_evidence_queue_item_test import _pipeline_payload


def test_cli_builds_and_stores_queue_item_from_explicit_pipeline_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pipeline_file = root / "pipeline.json"
        output_dir = root / "queue_out"
        pipeline_file.write_text(json.dumps({"pipeline_result": _pipeline_payload()}), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "capture_msn_manual_evidence_queue_cli.py",
                "--pipeline-json",
                str(pipeline_file),
                "--output-dir",
                str(output_dir),
                "--queue-id",
                "source_evidence_review_queue",
                "--file-prefix",
                "msn_queue",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["evidence_queue_item"]["ready_for_evidence_queue_review"] is True
        assert payload["evidence_queue_verifier"]["issue_count"] == 0
        assert payload["evidence_queue_store_result"]["file_count"] == 2
        assert str(root) not in completed.stdout


if __name__ == "__main__":
    test_cli_builds_and_stores_queue_item_from_explicit_pipeline_json()
    print("MSN manual Evidence Queue CLI self-test passed.")
