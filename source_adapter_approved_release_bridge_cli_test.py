from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from source_adapter_evidence_review_bridge import build_source_adapter_evidence_review_bridge
from source_adapter_evidence_review_bridge_test import fixture_evidence_queue_bridge


def main() -> None:
    review_bridge = build_source_adapter_evidence_review_bridge(
        fixture_evidence_queue_bridge(),
        reviewer_decision={"decision": "APPROVED"},
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        review_bridge_path = tmp_path / "evidence_review_bridge.json"
        review_bridge_path.write_text(json.dumps(review_bridge, indent=2, sort_keys=True), encoding="utf-8")
        output_dir = tmp_path / "out"
        completed = subprocess.run(
            [
                sys.executable,
                "source_adapter_approved_release_bridge_cli.py",
                "--evidence-review-bridge-json",
                str(review_bridge_path),
                "--output-dir",
                str(output_dir),
                "--releaser-id",
                "cli_releaser",
                "--release-note",
                "cli release",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        result = json.loads(completed.stdout)
        assert result["store_status"] == "STORED"
        assert result["approved_release_count"] == 1
        assert result["verification"]["verified"] is True
        assert len(list(output_dir.glob("*.json"))) == 5


if __name__ == "__main__":
    main()
    print("Source Adapter Approved Release Bridge CLI self-test passed.")
