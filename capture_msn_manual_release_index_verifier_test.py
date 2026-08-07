from __future__ import annotations

import json

from capture_msn_manual_release_index import build_msn_manual_release_index, msn_manual_release_index_to_json
from capture_msn_manual_release_index_test import _approved_release, _store_report
from capture_msn_manual_release_index_verifier import (
    MSN_MANUAL_RELEASE_INDEX_VERDICT_NEEDS_REVIEW,
    MSN_MANUAL_RELEASE_INDEX_VERDICT_READY,
    verify_msn_manual_release_index,
)


def test_verifier_accepts_ready_release_index() -> None:
    report = build_msn_manual_release_index(_approved_release(), release_package_store_report=_store_report())
    payload = json.loads(msn_manual_release_index_to_json(report))
    verification = verify_msn_manual_release_index(payload)
    assert verification.verdict == MSN_MANUAL_RELEASE_INDEX_VERDICT_READY
    assert verification.issue_count == 0
    assert verification.index_id == report.index_id


def test_verifier_flags_not_ready_index() -> None:
    report = build_msn_manual_release_index(_approved_release(), release_package_store_report=_store_report())
    payload = json.loads(msn_manual_release_index_to_json(report))
    payload["release_index_status"] = "MSN_MANUAL_RELEASE_INDEX_NEEDS_REVIEW"
    verification = verify_msn_manual_release_index(payload)
    assert verification.verdict == MSN_MANUAL_RELEASE_INDEX_VERDICT_NEEDS_REVIEW
    assert verification.issue_count >= 1


if __name__ == "__main__":
    test_verifier_accepts_ready_release_index()
    test_verifier_flags_not_ready_index()
    print("MSN manual release index verifier self-test passed.")
