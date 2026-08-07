from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_store_mode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        action_kit = root / "action_kit.json"
        receipts = root / "receipts.json"
        out = root / "out"
        action_kit.write_text(
            json.dumps(
                {
                    "source_adapter_capture_action_kit_id": "source_adapter_capture_action_kit.example",
                    "adapters": [{"adapter_id": "article", "artifact_roles": ["article_html_or_text"]}],
                    "artifact_intake_templates": {
                        "templates": [{"adapter_id": "article", "artifact_role": "article_html_or_text"}]
                    },
                }
            ),
            encoding="utf-8",
        )
        receipts.write_text(
            json.dumps(
                [
                    {
                        "adapter_id": "article",
                        "artifact_role": "article_html_or_text",
                        "artifact_basename": "article.html",
                        "byte_count": 12,
                        "sha256": "a" * 64,
                    }
                ]
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                "source_adapter_capture_session_cli.py",
                "--action-kit-json",
                str(action_kit),
                "--artifact-receipts-json",
                str(receipts),
                "--output-dir",
                str(out),
                "--operator-approval-id",
                "approval.example",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
    assert payload["store_status"] == "STORED"
    assert payload["verification"]["verified"] is True


if __name__ == "__main__":
    test_cli_store_mode()
    print("Source Adapter Capture Session CLI self-test passed.")
