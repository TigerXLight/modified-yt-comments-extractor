from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_release_candidate_ledger import build_completion_ledger, main, write_completion_ledger


def test_completion_ledger_contains_required_layers() -> None:
    ledger = build_completion_ledger()
    layers = {entry.layer for entry in ledger.entries}
    assert "release-candidate-lock" in layers
    assert "media-download" in layers
    assert "live-reconciler" in layers
    assert any("Do not call live MSN COMPLETE" in rule for rule in ledger.non_negotiable_rules)


def test_write_completion_ledger() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_completion_ledger(Path(tmp))
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()


def test_cli() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert main(["--output-dir", tmp]) == 0


if __name__ == "__main__":
    test_completion_ledger_contains_required_layers()
    test_write_completion_ledger()
    test_cli()
    print("MSN completion ledger self-test passed.")
