from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from lightweight_in_app_browser_capture_cli import main


def test_cli_builds_package() -> None:
    adapter = {"adapter_id": "single", "display_name": "Single", "domains": ["single.example"]}
    with tempfile.TemporaryDirectory() as tmp:
        adapter_path = Path(tmp) / "adapter.json"
        out_dir = Path(tmp) / "out"
        adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            rc = main([
                "--adapter-json", str(adapter_path),
                "--source-url", "https://single.example/story",
                "--output-dir", str(out_dir),
                "--artifact", "dom_snapshot",
            ])
        assert rc == 0
        receipt = json.loads(stream.getvalue())
        assert receipt["store_status"] == "STORED"
        assert receipt["adapter_id"] == "single"
        assert any(item["role"] == "lightweight_browser_launch_script" for item in receipt["stored_files"])


if __name__ == "__main__":
    test_cli_builds_package()
    print("Lightweight in-app browser capture CLI self-test passed.")
