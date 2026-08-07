from __future__ import annotations

import json

from capture_msn_manual_approved_release_package import build_msn_manual_approved_release_package, msn_manual_approved_release_package_to_json
from capture_msn_manual_approved_release_package_test import _handoff, _package_store
from capture_msn_manual_approved_release_package_verifier import (
    MSN_MANUAL_APPROVED_RELEASE_PACKAGE_VERDICT_NEEDS_REVIEW,
    MSN_MANUAL_APPROVED_RELEASE_PACKAGE_VERDICT_READY,
    verify_msn_manual_approved_release_package,
)


def test_verifier_ready() -> None:
    report = build_msn_manual_approved_release_package(_handoff(), package_store_report=_package_store())
    payload = json.loads(msn_manual_approved_release_package_to_json(report))
    verification = verify_msn_manual_approved_release_package(payload)
    assert verification.verdict == MSN_MANUAL_APPROVED_RELEASE_PACKAGE_VERDICT_READY
    assert verification.issue_count == 0


def test_verifier_catches_bad_status() -> None:
    report = build_msn_manual_approved_release_package(_handoff(), package_store_report=_package_store())
    payload = json.loads(msn_manual_approved_release_package_to_json(report))
    payload["release_status"] = "BROKEN"
    verification = verify_msn_manual_approved_release_package(payload)
    assert verification.verdict == MSN_MANUAL_APPROVED_RELEASE_PACKAGE_VERDICT_NEEDS_REVIEW
    assert verification.issue_count >= 1


if __name__ == "__main__":
    test_verifier_ready()
    test_verifier_catches_bad_status()
    print("MSN manual approved release package verifier self-test passed.")
