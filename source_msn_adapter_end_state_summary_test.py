
from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_end_state_summary import REQUIRED_ARTIFACTS, build_end_state_summary, write_end_state_outputs

def test_end_state_summary_detects_missing_and_present() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        out = Path(td) / "out"
        root.mkdir()
        for name in REQUIRED_ARTIFACTS[:3]:
            (root / name).write_text("# placeholder\n", encoding="utf-8")
        summary = build_end_state_summary(root)
        assert summary.status == "CHAIN_PARTIAL"
        assert summary.present_count == 3
        assert summary.missing_count == len(REQUIRED_ARTIFACTS) - 3
        paths = write_end_state_outputs(summary, out)
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()
        assert Path(paths["csv"]).exists()

def test_end_state_summary_chain_present() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        root.mkdir()
        for name in REQUIRED_ARTIFACTS:
            (root / name).write_text("# placeholder\n", encoding="utf-8")
        summary = build_end_state_summary(root)
        assert summary.status == "CHAIN_PRESENT"
        assert summary.missing_count == 0

if __name__ == "__main__":
    test_end_state_summary_detects_missing_and_present()
    test_end_state_summary_chain_present()
    print("MSN end-state summary self-test passed.")
