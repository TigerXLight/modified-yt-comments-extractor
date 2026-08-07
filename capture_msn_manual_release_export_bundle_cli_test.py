from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_release_export_bundle_cli import main
from capture_msn_manual_release_export_bundle_test import _release_index


def test_release_export_bundle_cli() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        index_path = root / "release_index.json"
        out_dir = root / "out"
        index_path.write_text(json.dumps(_release_index()), encoding="utf-8")
        code = main(["--release-index", str(index_path), "--output-dir", str(out_dir)])
        assert code == 0
        assert len(list(out_dir.glob("*.json"))) == 3


if __name__ == "__main__":
    test_release_export_bundle_cli()
    print("MSN manual release export bundle CLI self-test passed.")
