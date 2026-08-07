from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def _package() -> dict:
    return {
        "archive_review_package_id": "fixture_adapter.archive_review.1234",
        "archive_result_intake_id": "fixture_adapter.archive_result_intake.1234",
        "archive_handoff_id": "fixture_adapter.archive_handoff.1234",
        "release_audit_id": "fixture_adapter.release_audit.1234",
        "release_index_id": "fixture_adapter.release_index.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "decision": "APPROVED",
        "closeout_status": "ARCHIVE_COMPLETE",
        "reviewed_receipts": [{"provider_id": "archive_today", "archive_url": "https://archive.today/example"}],
    }


def test_cli_store_and_verify() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = root / "archive_review_package.json"
        package_path.write_text(json.dumps(_package()), encoding="utf-8")
        out_dir = root / "out"
        completed = subprocess.run(
            [
                sys.executable,
                "source_pipeline_closeout_cli.py",
                "--archive-review-package",
                str(package_path),
                "--out-dir",
                str(out_dir),
                "--store",
                "--verify",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(completed.stdout)
        assert data["store_status"] == "STORED"
        assert data["verification"]["verified"] is True
        assert len(list(out_dir.glob("*.json"))) == 4


def test_cli_print_and_verify() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_path = root / "archive_review_package.json"
        package_path.write_text(json.dumps(_package()), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "source_pipeline_closeout_cli.py", "--archive-review-package", str(package_path), "--verify"],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(completed.stdout)
        assert data["verification"]["verified"] is True
        assert data["closeout_report"]["final_status"] == "SOURCE_PIPELINE_COMPLETE"


if __name__ == "__main__":
    test_cli_store_and_verify()
    test_cli_print_and_verify()
    print("Source Pipeline Closeout CLI self-test passed.")
