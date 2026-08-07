from __future__ import annotations

import json

from capture_msn_manual_evidence_queue_item import build_msn_manual_evidence_queue_item, msn_manual_evidence_queue_item_to_json
from capture_msn_manual_evidence_queue_item_test import _pipeline_payload
from capture_msn_manual_evidence_queue_verifier import verify_msn_manual_evidence_queue_item_payload


def test_verifier_accepts_safe_queue_item() -> None:
    item = build_msn_manual_evidence_queue_item(_pipeline_payload())
    report = verify_msn_manual_evidence_queue_item_payload(json.loads(msn_manual_evidence_queue_item_to_json(item)))
    assert report.ready_for_evidence_queue_review is True
    assert report.issue_count == 0


def test_verifier_rejects_missing_manifest_role() -> None:
    item = build_msn_manual_evidence_queue_item(_pipeline_payload())
    payload = json.loads(msn_manual_evidence_queue_item_to_json(item))
    payload["asset_roles"].remove("total_export_manifest_json")
    report = verify_msn_manual_evidence_queue_item_payload(payload)
    assert report.ready_for_evidence_queue_review is False
    assert "total_export_manifest_json" in report.issues[0]


if __name__ == "__main__":
    test_verifier_accepts_safe_queue_item()
    test_verifier_rejects_missing_manifest_role()
    print("MSN manual Evidence Queue verifier self-test passed.")
