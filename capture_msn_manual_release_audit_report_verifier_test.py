from capture_msn_manual_release_audit_report import _REQUIRED_STAGE_KEYS, build_msn_manual_release_audit_report
from capture_msn_manual_release_audit_report_verifier import verify_msn_manual_release_audit_report


def _packet():
    return build_msn_manual_release_audit_report(
        {
            "schema_version": "msn_manual_release_pipeline_closeout_v1",
            "pipeline_status": "MSN_MANUAL_RELEASE_PIPELINE_CLOSED",
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "pipeline_closeout_id": "msn.queue.release.1234.pipeline_closeout.abc123",
            "transition_map": {"to_status": "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL"},
            "stage_coverage": {key: True for key in _REQUIRED_STAGE_KEYS},
            "stored_files": [{"filename": "artifact.json", "role": "artifact", "sha256": "e" * 64, "byte_count": 9}],
        }
    )


def test_verify_audit_report():
    packet = _packet()
    result = verify_msn_manual_release_audit_report(packet)
    assert result["schema_version"] == "msn_manual_release_audit_report_verifier_v1"
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verify_audit_report_rejects_not_ready():
    packet = _packet()
    packet["audit_status"] = "MSN_MANUAL_RELEASE_AUDIT_REVIEW_REQUIRED"
    result = verify_msn_manual_release_audit_report(packet)
    assert result["verified"] is False
    assert "audit_not_ready" in result["issues"]


if __name__ == "__main__":
    test_verify_audit_report()
    test_verify_audit_report_rejects_not_ready()
    print("MSN manual release audit report verifier self-test passed.")
