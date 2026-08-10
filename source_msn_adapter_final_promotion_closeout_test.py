from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_final_promotion_closeout import EXPECTED_REPORT_NAMES, REQUIRED_LIVE_CHECKS, build_closeout, run


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _positive_live_evidence() -> dict:
    return {
        "schema_version": "test",
        "artifact_kind": "msn_source_adapter_live_evidence_result",
        "operator_signed": True,
        "checks": [{"check_id": check_id, "status": "PASS"} for check_id in REQUIRED_LIVE_CHECKS],
    }


def test_no_live_evidence_does_not_complete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build_closeout(root)
        assert report.decision == "RC_LOCKED_PENDING_LIVE_EVIDENCE"
        assert report.live_evidence_status == "MISSING"


def test_positive_live_evidence_can_complete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_json(root / "live" / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json", _positive_live_evidence())
        for name in EXPECTED_REPORT_NAMES:
            _write_json(root / "reports" / name, {"status": "PASS"})
        report = build_closeout(root)
        assert report.decision == "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
        assert report.required_live_checks_passed == len(REQUIRED_LIVE_CHECKS)


def test_write_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "root"
        out = Path(tmp) / "out"
        _write_json(root / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json", _positive_live_evidence())
        result = run(root, out)
        assert Path(result["json"]).exists()
        assert Path(result["markdown"]).exists()
        assert Path(result["csv"]).exists()
        assert result["decision"] == "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"


if __name__ == "__main__":
    test_no_live_evidence_does_not_complete()
    test_positive_live_evidence_can_complete()
    test_write_outputs()
    print("MSN final promotion closeout self-test passed.")
