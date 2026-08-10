from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_release_promotion import _scan_no_network_reports


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_generated_strict_and_recheck_reports_do_not_block_current_root() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_json(
            root
            / "final_msn_live_evidence_STRICT_20260810_205724"
            / "operator_final"
            / "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json",
            {"overall_status": "BLOCKED"},
        )
        _write_json(
            root
            / "final_msn_live_evidence_STRICT_AFTER_ARTICLE_FIX_20260810_211418"
            / "live_reconciliation"
            / "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json",
            {"final_status": "BLOCKED"},
        )
        _write_json(
            root
            / "live_reconciliation_recheck_after_scope_fix"
            / "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json",
            {"final_status": "BLOCKED"},
        )
        _write_json(
            root
            / "acceptance_recheck_after_article_fix_FIXEDCLI"
            / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json",
            {"acceptance_status": "BLOCKED"},
        )
        _write_json(
            root
            / "final_msn_live_evidence_20260810_205533"
            / "certification_archive"
            / "evidence_files"
            / "final_msn_live_evidence_20260810_205533"
            / "live_reconciliation"
            / "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json",
            {"final_status": "BLOCKED"},
        )

        found, failing = _scan_no_network_reports(root)
        assert found == 0
        assert failing == []


def test_canonical_no_network_failures_still_block() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_json(
            root / "reports" / "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json",
            {"overall_status": "BLOCKED"},
        )
        found, failing = _scan_no_network_reports(root)
        assert found == 1
        assert failing
        assert "BLOCKED" in failing[0]


def test_canonical_non_failing_statuses_do_not_block() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_json(
            root / "reports" / "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json",
            {"overall_status": "CONFIDENT_WITH_MANUAL_REVIEW"},
        )
        _write_json(
            root / "reports" / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.json",
            {"lock_state": "RC_LOCKED_PENDING_LIVE_EVIDENCE"},
        )
        found, failing = _scan_no_network_reports(root)
        assert found == 2
        assert failing == []


if __name__ == "__main__":
    test_generated_strict_and_recheck_reports_do_not_block_current_root()
    test_canonical_no_network_failures_still_block()
    test_canonical_non_failing_statuses_do_not_block()
    print("MSN release promotion scope self-test passed.")
