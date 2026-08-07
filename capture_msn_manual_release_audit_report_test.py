from capture_msn_manual_release_audit_report import (
    AUDIT_STATUS_READY,
    AUDIT_STATUS_REVIEW_REQUIRED,
    _REQUIRED_STAGE_KEYS,
    build_msn_manual_release_audit_report,
    inspect_msn_manual_release_audit_report_safety,
)


def _pipeline_closeout():
    return {
        "schema_version": "msn_manual_release_pipeline_closeout_v1",
        "pipeline_status": "MSN_MANUAL_RELEASE_PIPELINE_CLOSED",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "pipeline_closeout_id": "msn.queue.release.1234.pipeline_closeout.abc123",
        "content_sha256": "b" * 64,
        "transition_map": {"to_status": "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL"},
        "stage_coverage": {key: True for key in _REQUIRED_STAGE_KEYS},
        "stored_files": [
            {
                "filename": "msn.queue.release.1234.pipeline_closeout.abc123.release_pipeline_closeout.json",
                "role": "msn_manual_release_pipeline_closeout",
                "sha256": "a" * 64,
                "byte_count": 100,
            }
        ],
    }


def test_build_audit_report_ready():
    packet = build_msn_manual_release_audit_report(
        _pipeline_closeout(),
        store_reports=[
            {
                "schema_version": "receipt_v1",
                "stored_files": [
                    {"filename": "release_export_bundle.json", "role": "bundle", "sha256": "c" * 64, "byte_count": 10}
                ],
            }
        ],
        operator_label="reviewer",
        audit_notes="ready",
    )
    assert packet["schema_version"] == "msn_manual_release_audit_report_v1"
    assert packet["audit_status"] == AUDIT_STATUS_READY
    assert packet["queue_item_id"] == "msn.queue"
    assert packet["stage_count"] == len(_REQUIRED_STAGE_KEYS)
    assert packet["artifact_quality"]["artifact_count"] == 2
    assert packet["artifact_quality"]["artifact_quality_passed"] is True
    assert packet["audit_report_id"].startswith("msn.queue.release.1234.audit.")
    assert inspect_msn_manual_release_audit_report_safety(packet)["safe"] is True


def test_audit_report_requires_review_for_missing_stage():
    source = _pipeline_closeout()
    source["stage_coverage"] = {key: (key != "release_export_bundle") for key in _REQUIRED_STAGE_KEYS}
    packet = build_msn_manual_release_audit_report(source)
    assert packet["audit_status"] == AUDIT_STATUS_REVIEW_REQUIRED
    assert "release_export_bundle" in packet["missing_stages"]
    assert "missing_stage_coverage" in packet["readiness_issues"]


if __name__ == "__main__":
    test_build_audit_report_ready()
    test_audit_report_requires_review_for_missing_stage()
    print("MSN manual release audit report self-test passed.")
