from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_release_index_cli import main
from capture_msn_manual_release_index_test import _approved_release, _store_report


def test_cli_builds_and_stores_release_index() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        release_path = base / "approved_release.json"
        store_path = base / "approved_release_store.json"
        output_dir = base / "out"
        release_path.write_text(json.dumps(_approved_release()), encoding="utf-8")
        store_path.write_text(json.dumps(_store_report()), encoding="utf-8")
        code = main([
            "--approved-release-json",
            str(release_path),
            "--release-package-store-json",
            str(store_path),
            "--output-dir",
            str(output_dir),
            "--index-label",
            "cli index",
        ])
        assert code == 0
        assert list(output_dir.glob("*.release_index.json"))
        assert list(output_dir.glob("*.release_inventory.json"))
        assert list(output_dir.glob("*.release_queue_update.json"))


if __name__ == "__main__":
    test_cli_builds_and_stores_release_index()
    print("MSN manual release index CLI self-test passed.")
