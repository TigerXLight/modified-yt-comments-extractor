import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _fixture_audit():
    return {
        "schema_version": "msn_manual_release_audit_report_v1",
        "audit_status": "MSN_MANUAL_RELEASE_AUDIT_READY",
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "audit_report_id": "msn.queue.release.1234.audit.abcdef123456",
        "readiness_issues": [],
    }


def test_archive_handoff_cli_writes_store_summary():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        audit_path = root / "audit.json"
        out_dir = root / "out"
        audit_path.write_text(json.dumps(_fixture_audit()), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "capture_msn_manual_archive_handoff_cli.py",
                "--audit-report-json",
                str(audit_path),
                "--source-url",
                "https://www.msn.com/en-gb/news/example-article/ar-AA123456",
                "--output-dir",
                str(out_dir),
                "--provider",
                "archive_today",
                "--provider",
                "ghostarchive",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        assert payload["schema_version"] == "msn_manual_archive_handoff_store_v1"
        assert payload["verification"]["verified"] is True
        assert payload["output_file_count"] == 3
        assert len(list(out_dir.glob("*.json"))) == 3


if __name__ == "__main__":
    test_archive_handoff_cli_writes_store_summary()
    print("MSN manual archive handoff CLI self-test passed.")
