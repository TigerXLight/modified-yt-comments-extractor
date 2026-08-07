from __future__ import annotations

from source_total_export_package import build_source_total_export_package
from source_total_export_package_verifier import verify_source_total_export_package


def _fixture_capture_bundle() -> dict:
    return {
        "schema_version": "source_capture_bundle_v1",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "input_stage_ids": {
            "content_extraction_id": "fixture.content.1",
            "comment_extraction_id": "fixture.comments.1",
        },
        "content": {
            "title": "Fixture title",
            "body_text": "Fixture article body.",
            "content_extraction_id": "fixture.content.1",
        },
        "comments": {
            "available": True,
            "comment_count": 2,
            "comment_extraction_id": "fixture.comments.1",
        },
        "artifact_index": [
            {
                "filename": "article.html",
                "role": "article_html_or_text",
                "input_stage": "artifact_collection",
                "byte_count": 20,
                "sha256": "a" * 64,
            },
            {
                "filename": "comments.json",
                "role": "comments_json_or_text",
                "input_stage": "artifact_collection",
                "byte_count": 30,
                "sha256": "b" * 64,
            },
        ],
        "total_export_handoff": {
            "schema_version": "source_capture_total_export_handoff_v1",
            "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
            "handoff_status": "READY_FOR_TOTAL_EXPORT_PACKAGE",
        },
    }


def test_build_source_total_export_package() -> None:
    outputs = build_source_total_export_package(
        capture_bundle=_fixture_capture_bundle(),
        package_notes=["Fixture package."],
    )
    package = outputs.total_export_package
    assert package["schema_version"] == "source_total_export_package_v1"
    assert package["export_status"] == "READY_FOR_EVIDENCE_QUEUE"
    assert package["adapter_id"] == "fixture_adapter"
    assert package["comments"]["comment_count"] == 2
    assert package["total_export_manifest"]["artifact_count"] == 2
    assert outputs.evidence_queue_handoff["required_next_stage"] == "source_evidence_queue"
    assert verify_source_total_export_package(package)["verified"] is True


def test_rejects_full_path_artifact() -> None:
    bundle = _fixture_capture_bundle()
    bundle["artifact_index"][0]["filename"] = r"C:\\tmp\\article.html"
    try:
        build_source_total_export_package(capture_bundle=bundle)
    except ValueError as exc:
        assert "basename" in str(exc)
    else:
        raise AssertionError("full path artifact should be rejected")


if __name__ == "__main__":
    test_build_source_total_export_package()
    test_rejects_full_path_artifact()
    print("Source Total Export package self-test passed.")
