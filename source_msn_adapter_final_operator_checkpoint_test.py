from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_final_operator_checkpoint import (
    REQUIRED_DOC_ARTIFACTS,
    REQUIRED_REPO_ARTIFACTS,
    build_checkpoint,
    write_checkpoint,
)


def test_checkpoint_ready_when_all_files_exist() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        for name in REQUIRED_REPO_ARTIFACTS + REQUIRED_DOC_ARTIFACTS:
            (repo / name).write_text("x", encoding="utf-8")
        report = build_checkpoint(repo)
        assert report.status == "CHECKPOINT_READY_FOR_LIVE_EVIDENCE"
        assert report.missing == 0
        out = Path(tmp) / "out"
        write_checkpoint(report, out)
        assert (out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_CHECKPOINT.json").exists()
        assert (out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_CHECKPOINT.md").exists()
        assert (out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_CHECKPOINT.csv").exists()


def test_checkpoint_partial_when_missing_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / REQUIRED_REPO_ARTIFACTS[0]).write_text("x", encoding="utf-8")
        report = build_checkpoint(repo)
        assert report.status == "CHECKPOINT_PARTIAL_TOOLING"
        assert report.missing > 0


if __name__ == "__main__":
    test_checkpoint_ready_when_all_files_exist()
    test_checkpoint_partial_when_missing_files()
    print("MSN final operator checkpoint self-test passed.")
