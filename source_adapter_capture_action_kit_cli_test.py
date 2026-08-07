from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_store_mode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        setup = root / "setup.json"
        out = root / "out"
        setup.write_text(
            json.dumps(
                {
                    "source_adapter_capture_setup_id": "source_adapter_capture_setup.example",
                    "adapters": [{"adapter_id": "article", "artifact_roles": ["article_html_or_text"]}],
                }
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, "source_adapter_capture_action_kit_cli.py", "--capture-setup-json", str(setup), "--output-dir", str(out)],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
    assert payload["store_status"] == "STORED"
    assert payload["verification"]["verified"] is True


if __name__ == "__main__":
    test_cli_store_mode()
    print("Source Adapter Capture Action Kit CLI self-test passed.")
