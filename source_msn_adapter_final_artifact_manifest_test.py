#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_final_artifact_manifest import build_manifest, write_manifest


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        root.mkdir()
        (root / "source_msn_adapter_manifest.py").write_text("# manifest\n", encoding="utf-8")
        (root / "MSN_SOURCE_ADAPTER_COMPLETION_BOUNDARY_LOCK.md").write_text("lock\n", encoding="utf-8")
        out = Path(td) / "out"
        report = build_manifest(root)
        assert report.total_expected > 20
        assert report.present_count >= 2
        assert report.missing_count >= 1
        paths = write_manifest(report, out)
        for key in ("json", "markdown", "csv"):
            assert Path(paths[key]).exists(), key
        assert "positive manual/live evidence" in (out / "MSN_SOURCE_ADAPTER_FINAL_ARTIFACT_MANIFEST.md").read_text(encoding="utf-8")
    print("MSN final artifact manifest self-test passed.")


if __name__ == "__main__":
    main()
