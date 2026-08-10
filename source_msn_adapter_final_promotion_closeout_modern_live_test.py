from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_final_promotion_closeout import build_closeout


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_modern_filled_acceptance_result_promotes_closeout() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_json(root / "02_MSN_LIVE_ACCEPTANCE_RESULT_FILLED_20260810.json", {
            "operator_decision": "ACCEPTED",
            "checks": {
                "article_extraction": "PASS",
                "comments_profile_extraction": "PASS",
                "offline_viewer_archive": "PASS",
                "media_registration": "PASS",
                "source_chain_review": "PASS",
                "warc_wacz_status": "PARTIAL",
            },
        })
        _write_json(root / "release_promotion" / "MSN_SOURCE_ADAPTER_RELEASE_PROMOTION_REPORT.json", {
            "promotion_status": "COMPLETE",
            "input_summary": {"live_evidence_status": "LIVE_EVIDENCE_ACCEPTED"},
        })
        report = build_closeout(root)
        assert report.live_evidence_status == "POSITIVE"
        assert report.required_live_checks_passed == report.required_live_checks_total
        assert report.decision == "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"


def test_modern_validation_report_promotes_closeout() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_json(root / "release_promotion" / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_VALIDATION.json", {
            "status": "LIVE_EVIDENCE_ACCEPTED",
            "required_checks": {
                "article_extraction": "PASS",
                "comments_profile_extraction": "PASS",
                "offline_viewer_archive": "PASS",
                "media_registration": "PASS",
                "source_chain_review": "PASS",
            },
            "optional_checks": {"warc_wacz_status": "PARTIAL"},
        })
        report = build_closeout(root)
        assert report.live_evidence_status == "POSITIVE"
        assert report.required_live_checks_passed == report.required_live_checks_total
        assert report.decision == "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"


def test_unfilled_templates_do_not_promote_closeout() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_json(root / "operator_final" / "live_acceptance_pack" / "02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json", {
            "comments_exported": "UNKNOWN",
        })
        report = build_closeout(root)
        assert report.decision == "RC_LOCKED_PENDING_LIVE_EVIDENCE"
        assert report.live_evidence_status == "INCOMPLETE"


if __name__ == "__main__":
    test_modern_filled_acceptance_result_promotes_closeout()
    test_modern_validation_report_promotes_closeout()
    test_unfilled_templates_do_not_promote_closeout()
    print("MSN final promotion closeout modern live evidence self-test passed.")
