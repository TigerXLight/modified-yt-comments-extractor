from __future__ import annotations

from source_release_index import build_source_release_index


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
        "content_summary": {"title": "Fixture Story", "body_character_count": 123},
        "comment_summary": {"comment_count": 2, "reply_count": 1},
        "artifact_count": 2,
        "artifact_roles": ["article_html_or_text", "comments_json_or_text"],
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_approved_release"},
            {"role": "comments_json_or_text", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 52, "source_stage": "source_approved_release"},
        ],
        "release_fingerprint": "f" * 16,
        "release_notes": ["Approved after review."],
    }


def _approved_release_manifest():
    return {
        "schema_version": "source_approved_release_manifest_v1",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "manifest_status": "READY_FOR_RELEASE_INDEX",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "artifact_count": 2,
        "artifact_roles": ["article_html_or_text", "comments_json_or_text"],
        "release_fingerprint": "f" * 16,
    }


def _release_index_handoff():
    return {
        "schema_version": "source_approved_release_index_handoff_v1",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "handoff_status": "READY_FOR_RELEASE_INDEX",
        "required_next_stage": "source_release_index",
        "release_index_inputs": [
            {"role": "source_approved_release_package", "id": "fixture_adapter.approved_release.1234", "filename_hint": "approved.json"},
        ],
    }


def test_source_release_index_builds_export_bundle_handoff() -> None:
    outputs = build_source_release_index(
        approved_release_package=_approved_release_package(),
        approved_release_manifest=_approved_release_manifest(),
        release_index_handoff=_release_index_handoff(),
        indexer_id="release_indexer",
        release_notes=["Ready for export bundle."],
    )
    record = outputs.release_index_record
    assert record["schema_version"] == "source_release_index_v1"
    assert record["release_index_status"] == "READY_FOR_RELEASE_EXPORT_BUNDLE"
    assert record["approved_release_id"] == "fixture_adapter.approved_release.1234"
    assert record["artifact_count"] == 2
    assert record["indexed_by"] == "release_indexer"
    assert outputs.release_inventory["release_count"] == 1
    assert outputs.export_bundle_handoff["required_next_stage"] == "source_release_export_bundle"
    assert outputs.operator_summary["manual_or_live_actions_started"] is False


def test_source_release_index_rejects_unapproved_status() -> None:
    package = _approved_release_package()
    package["release_status"] = "PENDING"
    try:
        build_source_release_index(approved_release_package=package)
    except ValueError as exc:
        assert "READY_FOR_RELEASE_INDEX" in str(exc)
    else:
        raise AssertionError("expected invalid release status to fail")


def test_source_release_index_rejects_path_artifacts() -> None:
    package = _approved_release_package()
    package["artifact_index"][0]["filename"] = r"C:\\tmp\\article.html"
    try:
        build_source_release_index(approved_release_package=package)
    except ValueError as exc:
        assert "safe basenames" in str(exc)
    else:
        raise AssertionError("expected path artifact to fail")


if __name__ == "__main__":
    test_source_release_index_builds_export_bundle_handoff()
    test_source_release_index_rejects_unapproved_status()
    test_source_release_index_rejects_path_artifacts()
    print("Source Release Index self-test passed.")
