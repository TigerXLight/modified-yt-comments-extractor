from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def _intake_record() -> dict[str, object]:
    return {
        "schema_version": "source_archive_result_intake_v1",
        "intake_status": "READY_FOR_ARCHIVE_REVIEW",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "release_index_id": "fixture_adapter.release_index.1234",
        "release_audit_id": "fixture_adapter.release_audit.1234",
        "archive_handoff_id": "fixture_adapter.archive_handoff.1234",
        "archive_result_intake_id": "fixture_adapter.archive_result_intake.1234",
        "operator_supplied_results_received": True,
        "online_validation_performed": False,
        "archive_submission_performed_by_app": False,
        "manual_or_live_actions_started_by_app": False,
        "operator_archive_results": [
            {
                "provider_id": "wayback",
                "archive_url": "https://web.archive.org/web/20260101000000/https://fixture.test/story",
                "archive_receipt_filename": "wayback_receipt.json",
            }
        ],
    }


def test_cli_builds_archive_review_store() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        intake_path = base / "intake.json"
        out_dir = base / "out"
        _write_json(intake_path, _intake_record())
        completed = subprocess.run(
            [
                sys.executable,
                "source_archive_review_cli.py",
                "--archive-result-intake-json",
                str(intake_path),
                "--decision",
                "APPROVED",
                "--review-note",
                "Operator reviewed saved receipt evidence.",
                "--output-dir",
                str(out_dir),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        receipt = json.loads(completed.stdout)
        assert receipt["schema_version"] == "source_archive_review_store_v1"
        assert receipt["verification"]["verified"] is True
        assert receipt["decision"] == "APPROVED"
        assert len(list(out_dir.glob("*.json"))) == 5


if __name__ == "__main__":
    test_cli_builds_archive_review_store()
    print("Source Archive Review CLI self-test passed.")
