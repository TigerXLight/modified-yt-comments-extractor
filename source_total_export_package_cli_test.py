from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_total_export_package_cli import main
from source_total_export_package_test import _fixture_capture_bundle


def test_cli_builds_package() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        capture_bundle_path = root / "capture_bundle.json"
        output_dir = root / "out"
        capture_bundle_path.write_text(json.dumps(_fixture_capture_bundle()), encoding="utf-8")
        code = main([
            "--capture-bundle-json",
            str(capture_bundle_path),
            "--package-note",
            "CLI fixture.",
            "--output-dir",
            str(output_dir),
        ])
        assert code == 0
        files = sorted(path.name for path in output_dir.iterdir())
        assert len(files) == 4
        assert any(name.endswith(".source_total_export_package.json") for name in files)


if __name__ == "__main__":
    test_cli_builds_package()
    print("Source Total Export package CLI self-test passed.")
