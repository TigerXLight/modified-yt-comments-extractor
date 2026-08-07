from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from capture_msn_manual_approved_release_package_cli import main
from capture_msn_manual_approved_release_package_test import _handoff, _package_store


def test_cli_writes_release_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff_path = root / "handoff.json"
        store_path = root / "store.json"
        out_dir = root / "out"
        handoff_path.write_text(json.dumps(_handoff()), encoding="utf-8")
        store_path.write_text(json.dumps(_package_store()), encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "--approved-handoff-json",
                str(handoff_path),
                "--package-store-json",
                str(store_path),
                "--output-dir",
                str(out_dir),
                "--release-label",
                "operator release",
            ])
        assert exit_code == 0
        payload = json.loads(output.getvalue())
        assert payload["schema_version"] == "msn_manual_approved_release_package_store_v1"
        assert payload["output_file_count"] == 3
        assert len(list(out_dir.glob("*.json"))) == 3


if __name__ == "__main__":
    test_cli_writes_release_package()
    print("MSN manual approved release package CLI self-test passed.")
