from __future__ import annotations

import json

from capture_msn_manual_evidence_review_decision import build_msn_manual_evidence_review_decision, msn_manual_evidence_review_decision_to_json
from capture_msn_manual_evidence_review_decision_test import _package
from capture_msn_manual_evidence_review_decision_verifier import (
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_VERDICT_READY,
    verify_msn_manual_evidence_review_decision,
)


def test_verifier_accepts_ready_decision() -> None:
    package = _package()
    decision = build_msn_manual_evidence_review_decision(
        package,
        review_decision="APPROVED",
        completed_action_ids=[action["action_id"] for action in package["review_actions"]],
    )
    payload = json.loads(msn_manual_evidence_review_decision_to_json(decision))
    report = verify_msn_manual_evidence_review_decision(payload)
    assert report.verdict == MSN_MANUAL_EVIDENCE_REVIEW_DECISION_VERDICT_READY
    assert report.issue_count == 0
    assert report.approved_for_total_export is True


if __name__ == "__main__":
    test_verifier_accepts_ready_decision()
    print("MSN manual Evidence Review decision verifier self-test passed.")
