from __future__ import annotations

import tempfile

from capture_msn_manual_release_section_closeout import build_msn_manual_release_section_closeout, msn_manual_release_section_closeout_to_json
from capture_msn_manual_release_section_closeout_store import msn_manual_release_section_closeout_store_report_to_json, store_msn_manual_release_section_closeout
from capture_msn_manual_release_section_closeout_test import _bundle, _store
from capture_msn_manual_release_section_closeout_verifier import verify_msn_manual_release_section_closeout


def test_verifier_accepts_ready_closeout() -> None:
    report = build_msn_manual_release_section_closeout(_bundle(), release_export_bundle_store_report=_store())
    with tempfile.TemporaryDirectory() as temp_dir:
        store_report = store_msn_manual_release_section_closeout(report, temp_dir)
        verifier = verify_msn_manual_release_section_closeout(
            msn_manual_release_section_closeout_to_json(report),
            msn_manual_release_section_closeout_store_report_to_json(store_report),
        )
        assert verifier.verifier_status == "MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_VERIFIED"
        assert verifier.issue_count == 0


if __name__ == "__main__":
    test_verifier_accepts_ready_closeout()
    print("MSN manual release section closeout verifier self-test passed.")
