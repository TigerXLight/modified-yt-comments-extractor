import json
import tempfile
from pathlib import Path

from capture_msn_manual_release_audit_report import _REQUIRED_STAGE_KEYS
from capture_msn_manual_release_audit_report_cli import main


def test_cli_writes_audit_report():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        pipeline_path = base / "pipeline_closeout.json"
        receipt_path = base / "receipt.json"
        output_dir = base / "out"
        pipeline_path.write_text(
            json.dumps(
                {
                    "schema_version": "msn_manual_release_pipeline_closeout_v1",
                    "pipeline_status": "MSN_MANUAL_RELEASE_PIPELINE_CLOSED",
                    "queue_item_id": "msn.queue",
                    "release_id": "msn.queue.release.1234",
                    "pipeline_closeout_id": "msn.queue.release.1234.pipeline_closeout.abc123",
                    "transition_map": {"to_status": "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL"},
                    "stage_coverage": {key: True for key in _REQUIRED_STAGE_KEYS},
                    "stored_files": [
                        {"filename": "artifact.json", "role": "artifact", "sha256": "f" * 64, "byte_count": 10}
                    ],
                }
            ),
            encoding="utf-8",
        )
        receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": "receipt_v1",
                    "stored_files": [{"filename": "receipt.json", "role": "receipt", "sha256": "1" * 64, "byte_count": 11}],
                }
            ),
            encoding="utf-8",
        )
        code = main(
            [
                "--pipeline-closeout-json",
                str(pipeline_path),
                "--store-report-json",
                str(receipt_path),
                "--operator-label",
                "reviewer",
                "--output-dir",
                str(output_dir),
                "--json",
            ]
        )
        assert code == 0
        assert len(list(output_dir.glob("*.json"))) == 4


if __name__ == "__main__":
    test_cli_writes_audit_report()
    print("MSN manual release audit report CLI self-test passed.")
