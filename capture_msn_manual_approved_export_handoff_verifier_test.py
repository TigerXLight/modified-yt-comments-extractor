from __future__ import annotations

import json

from capture_msn_manual_approved_export_handoff import build_msn_manual_approved_export_handoff, msn_manual_approved_export_handoff_to_json
from capture_msn_manual_approved_export_handoff_test import _decision
from capture_msn_manual_approved_export_handoff_verifier import (
    MSN_MANUAL_APPROVED_EXPORT_HANDOFF_VERDICT_READY,
    verify_msn_manual_approved_export_handoff,
)


def main() -> None:
    handoff = build_msn_manual_approved_export_handoff(_decision())
    payload = json.loads(msn_manual_approved_export_handoff_to_json(handoff))
    report = verify_msn_manual_approved_export_handoff(payload)
    assert report.verdict == MSN_MANUAL_APPROVED_EXPORT_HANDOFF_VERDICT_READY
    assert report.issue_count == 0
    payload["source_url"] = "T:/References/leak.html"
    bad = verify_msn_manual_approved_export_handoff(payload)
    assert bad.issue_count > 0
    print("MSN manual approved export handoff verifier self-test passed.")


if __name__ == "__main__":
    main()
