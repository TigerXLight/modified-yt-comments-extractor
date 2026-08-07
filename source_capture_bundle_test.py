from __future__ import annotations

from source_capture_bundle import build_source_capture_bundle


def _content_fixture() -> dict:
    return {
        "schema_version": "source_content_extraction_v1",
        "content_extraction_id": "article.content.1",
        "adapter_id": "example_news",
        "source_url": "https://example.test/news/story",
        "title": "Example story",
        "body_text": "A body paragraph. Another body paragraph.",
        "artifacts": [
            {"filename": "article.html", "role": "article_html_or_text", "sha256": "a" * 64, "byte_count": 123}
        ],
    }


def _comments_fixture() -> dict:
    return {
        "schema_version": "source_comment_extraction_v1",
        "comment_extraction_id": "article.comments.1",
        "adapter_id": "example_news",
        "comment_count": 2,
        "artifacts": [
            {"filename": "comments.json", "role": "comments_json_or_text", "sha256": "b" * 64, "byte_count": 55}
        ],
    }


def test_build_source_capture_bundle() -> None:
    outputs = build_source_capture_bundle(
        content_extraction=_content_fixture(),
        comment_extraction=_comments_fixture(),
        artifact_collection={
            "artifact_collection_id": "article.artifacts.1",
            "stored_files": [
                {"filename": "screenshot.png", "role": "screenshot", "sha256": "c" * 64, "byte_count": 99}
            ],
        },
        operator_notes=["fixture only"],
    )
    bundle = outputs.capture_bundle
    assert bundle["schema_version"] == "source_capture_bundle_v1"
    assert bundle["adapter_id"] == "example_news"
    assert bundle["source_url"] == "https://example.test/news/story"
    assert bundle["content"]["title"] == "Example story"
    assert bundle["comments"]["comment_count"] == 2
    assert len(bundle["artifact_index"]) == 3
    assert outputs.total_export_handoff["handoff_status"] == "READY_FOR_TOTAL_EXPORT_PACKAGE"
    assert outputs.operator_summary["manual_or_live_actions_started"] is False


def test_rejects_missing_content() -> None:
    try:
        build_source_capture_bundle(content_extraction={"adapter_id": "empty"})
    except ValueError as exc:
        assert "title/headline or body/article text" in str(exc)
    else:
        raise AssertionError("missing content should fail")


def test_rejects_path_artifact_names() -> None:
    try:
        build_source_capture_bundle(
            content_extraction={
                "title": "Bad path",
                "artifacts": [{"filename": "C:/temp/article.html", "role": "article"}],
            }
        )
    except ValueError as exc:
        assert "basename" in str(exc)
    else:
        raise AssertionError("path artifact name should fail")


if __name__ == "__main__":
    test_build_source_capture_bundle()
    test_rejects_missing_content()
    test_rejects_path_artifact_names()
    print("Source capture bundle self-test passed.")
