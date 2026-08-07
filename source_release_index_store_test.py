from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path

from source_release_index import build_source_release_index
from source_release_index_store import store_source_release_index


def _approved_release_package():
    return {
        "schema_version": "source_approved_release_v1",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "release_status": "READY_FOR_RELEASE_INDEX",
        "approved_by_review_decision": True,
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_approved_release"},
        ],
        "release_fingerprint": "f" * 16,
    }


def test_source_release_index_store_writes_four_json_files() -> None:
    outputs = build_source_release_index(approved_release_package=_approved_release_package())
    with TemporaryDirectory() as tmp:
        receipt = store_source_release_index(outputs.as_dict(), Path(tmp))
        assert receipt["schema_version"] == "source_release_index_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 4
        assert receipt["verification"]["verified"] is True
        assert len(list(Path(tmp).glob("*.json"))) == 4
        for stored in receipt["stored_files"]:
            assert stored["byte_count"] > 0
            assert len(stored["sha256"]) == 64
            assert "/" not in stored["filename"] and "\\" not in stored["filename"]


if __name__ == "__main__":
    test_source_release_index_store_writes_four_json_files()
    print("Source Release Index store self-test passed.")
