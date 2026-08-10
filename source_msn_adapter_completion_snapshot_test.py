from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_completion_snapshot import EXPECTED_DOCS, EXPECTED_FILES, build_completion_snapshot


def test_completion_snapshot_passes_when_expected_files_exist() -> None:
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        for name in EXPECTED_FILES:
            (repo / name).write_text("# placeholder\n", encoding="utf-8")
        for name in EXPECTED_DOCS:
            (repo / name).write_text("placeholder\n", encoding="utf-8")
        snapshot = build_completion_snapshot(repo, repo / "out")
        assert snapshot.status == "PASS"
        assert snapshot.present_count == snapshot.expected_count
        assert not snapshot.missing
        assert (repo / "out" / "MSN_SOURCE_ADAPTER_COMPLETION_SNAPSHOT.json").exists()
        assert (repo / "out" / "MSN_SOURCE_ADAPTER_COMPLETION_SNAPSHOT.md").exists()


def test_completion_snapshot_reports_missing_files() -> None:
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        (repo / EXPECTED_FILES[0]).write_text("# placeholder\n", encoding="utf-8")
        snapshot = build_completion_snapshot(repo, repo / "out")
        assert snapshot.status == "PARTIAL"
        assert snapshot.missing


def run_self_test() -> None:
    test_completion_snapshot_passes_when_expected_files_exist()
    test_completion_snapshot_reports_missing_files()
    print("MSN completion snapshot self-test passed.")


if __name__ == "__main__":
    run_self_test()
