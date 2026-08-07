from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_release_section_closeout_cli import main
from capture_msn_manual_release_section_closeout_test import _bundle, _store


def test_cli_builds_closeout_store() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        bundle_path = base / "bundle.json"
        store_path = base / "store.json"
        output_dir = base / "out"
        bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
        store_path.write_text(json.dumps(_store()), encoding="utf-8")
        code = main([
            "--release-export-bundle",
            str(bundle_path),
            "--release-export-bundle-store",
            str(store_path),
            "--output-dir",
            str(output_dir),
        ])
        assert code == 0
        assert len(list(output_dir.glob("*.json"))) == 4


if __name__ == "__main__":
    test_cli_builds_closeout_store()
    print("MSN manual release section closeout CLI self-test passed.")
