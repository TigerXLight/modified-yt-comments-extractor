
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_final_readiness_badge import build_final_readiness_badge, write_badge_outputs

def test_pending_without_positive_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "root"
        out = Path(td) / "out"
        root.mkdir()
        (root / "promotion.json").write_text(json.dumps({"state": "RC_LOCKED_PENDING_LIVE_EVIDENCE"}), encoding="utf-8")
        report = build_final_readiness_badge(root)
        assert report.badge == "RC_LOCKED_PENDING_LIVE_EVIDENCE"
        assert report.complete_allowed is False
        paths = write_badge_outputs(report, out)
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()
        assert Path(paths["csv"]).exists()

def test_positive_live_evidence_promotes() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "root"
        root.mkdir()
        (root / "promotion.json").write_text(json.dumps({"final_state": "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"}), encoding="utf-8")
        report = build_final_readiness_badge(root)
        assert report.badge == "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
        assert report.complete_allowed is True
        assert report.positive_live_evidence_found is True

if __name__ == "__main__":
    test_pending_without_positive_live_evidence()
    test_positive_live_evidence_promotes()
    print("MSN final readiness badge self-test passed.")
