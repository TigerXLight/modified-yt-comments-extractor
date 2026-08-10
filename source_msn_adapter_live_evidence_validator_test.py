from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_live_evidence_validator import (
    validate_live_evidence,
    write_live_evidence_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_no_live_evidence_is_not_complete() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = validate_live_evidence(root)
        assert report.status == "NO_LIVE_EVIDENCE"
        assert "No real MSN COMPLETE" in report.warnings[0]


def test_positive_live_evidence_is_accepted() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "02_MSN_LIVE_ACCEPTANCE_RESULT_filled.json", {
            "operator_decision": "ACCEPTED",
            "target_url": "https://www.msn.com/en-gb/news/example/ar-AA123#comments",
            "observed_at": "2026-08-10T19:00:00Z",
            "checks": {
                "article_extraction": "PASS",
                "comments_profile_extraction": "PASS",
                "offline_viewer_archive": "PASS",
                "media_registration": "PASS",
                "source_chain_review": "PASS",
                "video_stream_status": "NOT_APPLICABLE",
            },
        })
        report = validate_live_evidence(root)
        assert report.status == "LIVE_EVIDENCE_ACCEPTED"
        assert report.accepted_file.endswith("02_MSN_LIVE_ACCEPTANCE_RESULT_filled.json")
        assert report.required_checks["article_extraction"] == "PASS"


def test_failed_required_check_blocks_acceptance() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "MSN_MANUAL_VALIDATION_RESULT.json", {
            "decision": "ACCEPTED",
            "checks": {
                "article_extraction": "PASS",
                "comments_profile_extraction": "FAIL",
                "offline_viewer_archive": "PASS",
                "media_registration": "PASS",
                "source_chain_review": "PASS",
            },
        })
        report = validate_live_evidence(root)
        assert report.status in {"LIVE_EVIDENCE_REJECTED", "LIVE_EVIDENCE_INCOMPLETE"}
        assert "comments_profile_extraction" in report.missing_required_checks


def test_writes_json_and_markdown() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = root / "reports"
        report = validate_live_evidence(root)
        json_path, md_path = write_live_evidence_report(report, out)
        assert json_path.exists()
        assert md_path.exists()
        assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "NO_LIVE_EVIDENCE"


if __name__ == "__main__":
    test_no_live_evidence_is_not_complete()
    test_positive_live_evidence_is_accepted()
    test_failed_required_check_blocks_acceptance()
    test_writes_json_and_markdown()
    print("MSN live evidence validator self-test passed.")
