from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_release_promotion import build_release_promotion, write_release_promotion_report


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _positive_live_payload() -> dict:
    return {
        "operator_decision": "ACCEPTED",
        "target_url": "https://www.msn.com/en-gb/news/example/ar-AA123#comments",
        "observed_at": "2026-08-10T19:00:00Z",
        "checks": {
            "article_extraction": "PASS",
            "comments_profile_extraction": "PASS",
            "offline_viewer_archive": "PASS",
            "media_registration": "PASS",
            "source_chain_review": "PASS",
        },
    }


def test_pending_without_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_json(root / "reports" / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.json", {
            "lock_state": "RC_LOCKED_PENDING_LIVE_EVIDENCE"
        })
        report = build_release_promotion(root)
        assert report.promotion_status == "RC_LOCKED_PENDING_LIVE_EVIDENCE"


def test_complete_with_positive_live_evidence_and_non_failing_reports() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_json(root / "reports" / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.json", {
            "lock_state": "RC_LOCKED_PENDING_LIVE_EVIDENCE"
        })
        _write_json(root / "reports" / "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.json", {
            "status": "CONFIDENT_WITH_MANUAL_REVIEW"
        })
        _write_json(root / "02_MSN_LIVE_ACCEPTANCE_RESULT_filled.json", _positive_live_payload())
        report = build_release_promotion(root)
        assert report.promotion_status == "COMPLETE"
        assert report.input_summary.live_evidence_status == "LIVE_EVIDENCE_ACCEPTED"


def test_blocked_when_no_network_report_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_json(root / "reports" / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json", {"status": "FAIL"})
        _write_json(root / "02_MSN_LIVE_ACCEPTANCE_RESULT_filled.json", _positive_live_payload())
        report = build_release_promotion(root)
        assert report.promotion_status == "BLOCKED"


def test_writes_promotion_report() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_release_promotion(root)
        json_path, md_path = write_release_promotion_report(report, root / "reports")
        assert json_path.exists()
        assert md_path.exists()
        assert json.loads(json_path.read_text(encoding="utf-8"))["promotion_status"] == "RC_LOCKED_PENDING_LIVE_EVIDENCE"


if __name__ == "__main__":
    test_pending_without_live_evidence()
    test_complete_with_positive_live_evidence_and_non_failing_reports()
    test_blocked_when_no_network_report_fails()
    test_writes_promotion_report()
    print("MSN release promotion self-test passed.")
