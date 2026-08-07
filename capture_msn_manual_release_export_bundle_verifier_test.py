from __future__ import annotations

import tempfile

from capture_msn_manual_release_export_bundle import build_msn_manual_release_export_bundle, msn_manual_release_export_bundle_to_json
from capture_msn_manual_release_export_bundle_store import msn_manual_release_export_bundle_store_report_to_json, store_msn_manual_release_export_bundle
from capture_msn_manual_release_export_bundle_test import _release_index
from capture_msn_manual_release_export_bundle_verifier import verify_msn_manual_release_export_bundle


def test_verifier_accepts_ready_bundle_and_store() -> None:
    report = build_msn_manual_release_export_bundle(_release_index())
    with tempfile.TemporaryDirectory() as tmp:
        store = store_msn_manual_release_export_bundle(report, tmp)
        verification = verify_msn_manual_release_export_bundle(
            msn_manual_release_export_bundle_to_json(report),
            msn_manual_release_export_bundle_store_report_to_json(store),
        )
    assert verification.verifier_status == "MSN_MANUAL_RELEASE_EXPORT_BUNDLE_VERIFIED"
    assert verification.issue_count == 0


if __name__ == "__main__":
    test_verifier_accepts_ready_bundle_and_store()
    print("MSN manual release export bundle verifier self-test passed.")
