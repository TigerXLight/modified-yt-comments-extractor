from __future__ import annotations

from capture_msn_manual_article_extraction import extract_msn_manual_article
from capture_msn_manual_capture_bundle import build_msn_manual_capture_bundle, msn_manual_capture_bundle_to_json
from capture_msn_manual_comments_extraction import extract_msn_manual_comments


def test_bundle_contains_article_and_comments_data_for_review() -> None:
    article = extract_msn_manual_article(
        source_url="https://www.msn.com/en-gb/news/example/story-id",
        artifact_text="Article title\nThis is the article body copied from the approved operator artifact.",
        artifact_file_name="article.txt",
    )
    comments = extract_msn_manual_comments(
        source_url="https://www.msn.com/en-gb/news/example/story-id",
        artifact_text="Alice: A visible comment from the operator artifact.",
        artifact_file_name="comments.txt",
    )
    bundle = build_msn_manual_capture_bundle(article=article, comments=comments)
    assert bundle.ready_for_total_export_review is True
    assert bundle.completed_capture_claimed is False
    assert bundle.comment_count == 1
    payload = msn_manual_capture_bundle_to_json(bundle)
    assert "This is the article body" in payload
    assert "A visible comment" in payload
    assert "article.txt" in payload


def test_bundle_requires_matching_source_url() -> None:
    article = extract_msn_manual_article(source_url="https://www.msn.com/a", artifact_text="T\nThis is a body long enough.")
    comments = extract_msn_manual_comments(source_url="https://www.msn.com/b", artifact_text="A: text")
    try:
        build_msn_manual_capture_bundle(article=article, comments=comments)
    except ValueError as exc:
        assert "source_url" in str(exc)
    else:
        raise AssertionError("expected source URL mismatch rejection")


if __name__ == "__main__":
    test_bundle_contains_article_and_comments_data_for_review()
    test_bundle_requires_matching_source_url()
    print("MSN manual capture bundle self-test passed.")
