import tempfile
from pathlib import Path

from capture_msn_manual_release_audit_report import _REQUIRED_STAGE_KEYS, build_msn_manual_release_audit_report
from capture_msn_manual_release_audit_report_store import store_msn_manual_release_audit_report


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
            "stored_files": [{"filename": "artifact.json", "role": "artifact", "sha256": "d" * 64, "byte_count": 5}],
        }
    )


def test_store_audit_report():
    packet = _packet()
    with tempfile.TemporaryDirectory() as tmp:
        result = store_msn_manual_release_audit_report(packet, tmp)
        assert result["schema_version"] == "msn_manual_release_audit_report_store_v1"
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 4
        assert {item["role"] for item in result["stored_files"]} == {
            "msn_manual_release_audit_report",
            "msn_manual_release_audit_artifact_ledger",
            "msn_manual_release_audit_traceability_map",
            "msn_manual_release_audit_operator_receipt",
        }
        for item in result["stored_files"]:
            assert (Path(tmp) / item["filename"]).exists()
            assert item["byte_count"] > 0


if __name__ == "__main__":
    test_store_audit_report()
    print("MSN manual release audit report store self-test passed.")
