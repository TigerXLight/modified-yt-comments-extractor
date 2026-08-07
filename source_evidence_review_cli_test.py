from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_evidence_review_cli import main as cli_main
from source_evidence_review_test import _queue_item


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        queue_path = root / "queue_item.json"
        queue_path.write_text(json.dumps(_queue_item(), sort_keys=True), encoding="utf-8")
        output_dir = root / "out"
        rc = cli_main([
            "--evidence-queue-item-json",
            str(queue_path),
            "--decision",
            "APPROVED",
            "--completed-action",
            "verify_source_identity",
            "--completed-action",
            "review_content_text",
            "--completed-action",
            "review_comments",
            "--completed-action",
            "decide_evidence_status",
            "--review-note",
            "cli fixture",
            "--output-dir",
            str(output_dir),
        ])
        assert rc == 0
        assert len(list(output_dir.glob("*.json"))) == 5
    print("Source Evidence Review CLI self-test passed.")


if __name__ == "__main__":
    main()
