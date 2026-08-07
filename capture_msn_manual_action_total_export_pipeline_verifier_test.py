from __future__ import annotations

from capture_msn_manual_action_total_export_pipeline_verifier import verify_msn_manual_action_total_export_pipeline_payload


def test_verifier_accepts_pipeline_payload_shape() -> None:
    report = verify_msn_manual_action_total_export_pipeline_payload(
        {
            "package_id": "msn_pkg",
            "pipeline_implemented": True,
            "generated_operator_action_kits": True,
            "explicit_operator_artifact_files_read": True,
            "total_export_package_written": True,
            "action_kit_file_count": 8,
            "total_export_file_count": 5,
            "comment_count": 2,
            "completed_capture_claimed": False,
            "verified_capture_claimed": False,
            "total_export_verification_report": {"ready_for_total_export_review": True},
        }
    )
    assert report.ready_for_total_export_review is True
    assert report.verdict.endswith("READY_FOR_REVIEW")


def test_verifier_rejects_path_and_completion_claim() -> None:
    report = verify_msn_manual_action_total_export_pipeline_payload(
        {
            "package_id": "msn_pkg",
            "pipeline_implemented": True,
            "generated_operator_action_kits": True,
            "explicit_operator_artifact_files_read": True,
            "total_export_package_written": True,
            "action_kit_file_count": 8,
            "total_export_file_count": 5,
            "completed_capture_claimed": True,
            "debug": r"C:\Users\fahad\secret\file.json",
            "total_export_verification_report": {"ready_for_total_export_review": True},
        }
    )
    assert report.ready_for_total_export_review is False
    assert {issue.code for issue in report.issues} >= {"unsafe_capture_claim", "full_path_serialized"}


if __name__ == "__main__":
    test_verifier_accepts_pipeline_payload_shape()
    test_verifier_rejects_path_and_completion_claim()
    print("MSN manual action Total Export pipeline verifier self-test passed.")
