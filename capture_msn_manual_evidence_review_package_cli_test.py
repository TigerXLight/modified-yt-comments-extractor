from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        queue_path = tmp_path / "queue.json"
        queue_path.write_text(
            json.dumps(
                {
                    "queue_item": {
                        "queue_item_id": "msn-cli-review",
                        "source_url": "https://www.msn.com/example",
                        "article_title": "CLI example",
                        "assets": [
                            {"role": "comments_json", "filename": "comments.json", "sha256": "a" * 64, "byte_count": 3},
                            {"role": "total_export_manifest", "filename": "manifest.json", "sha256": "b" * 64, "byte_count": 4},
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        out_dir = tmp_path / "out"
        proc = subprocess.run(
            [
                sys.executable,
                "capture_msn_manual_evidence_review_package_cli.py",
                "--queue-json",
                str(queue_path),
                "--output-dir",
                str(out_dir),
                "--reviewer-id",
                "reviewer",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        assert payload["queue_item_id"] == "msn-cli-review"
        assert payload["output_file_count"] == 2
        assert str(out_dir) not in proc.stdout
    print("MSN manual Evidence Review package CLI self-test passed.")


if __name__ == "__main__":
    main()
