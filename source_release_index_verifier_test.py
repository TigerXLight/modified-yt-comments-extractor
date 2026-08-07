from __future__ import annotations

from source_release_index import build_source_release_index
from source_release_index_verifier import verify_source_release_index


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


def test_source_release_index_verifier_accepts_valid_package() -> None:
    outputs = build_source_release_index(approved_release_package=_approved_release_package())
    result = verify_source_release_index(outputs.release_index_record, outputs.release_inventory, outputs.export_bundle_handoff)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_source_release_index_verifier_rejects_path_artifact() -> None:
    outputs = build_source_release_index(approved_release_package=_approved_release_package())
    outputs.release_index_record["artifact_index"][0]["filename"] = "nested/article.html"
    result = verify_source_release_index(outputs.release_index_record, outputs.release_inventory, outputs.export_bundle_handoff)
    assert result["verified"] is False
    assert any("safe basename" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_source_release_index_verifier_accepts_valid_package()
    test_source_release_index_verifier_rejects_path_artifact()
    print("Source Release Index verifier self-test passed.")
