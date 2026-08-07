from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_evidence_queue_bridge import build_source_adapter_evidence_queue_bridge
from source_adapter_evidence_queue_bridge_test import fixture_total_export_bridge
from source_adapter_evidence_review_bridge_cli import main as cli_main


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        queue_bridge = build_source_adapter_evidence_queue_bridge(fixture_total_export_bridge())
        input_path = root / "evidence_queue_bridge.json"
        input_path.write_text(json.dumps(queue_bridge, sort_keys=True), encoding="utf-8")
        output_dir = root / "out"
        rc = cli_main([
            "--evidence-queue-bridge-json",
            str(input_path),
            "--decision",
            "APPROVED",
            "--reviewer-id",
            "cli_reviewer",
            "--review-note",
            "cli fixture",
            "--output-dir",
            str(output_dir),
        ])
        assert rc == 0
        assert len(list(output_dir.glob("*.json"))) == 5
    print("Source Adapter Evidence Review Bridge CLI self-test passed.")


if __name__ == "__main__":
    main()
