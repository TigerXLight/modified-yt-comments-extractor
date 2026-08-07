from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from source_pipeline_closeout_store import store_source_pipeline_closeout


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


def test_store_source_pipeline_closeout() -> None:
    with TemporaryDirectory() as tmp:
        result = store_source_pipeline_closeout(_package(), out_dir=tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 4
        assert result["verification"]["verified"] is True
        for stored in result["stored_files"]:
            path = Path(tmp) / stored["filename"]
            assert path.exists()
            assert path.stat().st_size == stored["byte_count"]
            assert len(stored["sha256"]) == 64


if __name__ == "__main__":
    test_store_source_pipeline_closeout()
    print("Source Pipeline Closeout store self-test passed.")
