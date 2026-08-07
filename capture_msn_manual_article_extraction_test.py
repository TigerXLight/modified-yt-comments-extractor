from __future__ import annotations

from capture_msn_manual_article_extraction import extract_msn_manual_article, msn_manual_article_extraction_to_json


def test_extracts_msn_article_text_from_html_without_raw_html() -> None:
    html = """
    <html><head><title>Browser title</title><meta property="og:title" content="Main MSN title">
    <meta name="author" content="Reporter Name"></head><body><h1>Main MSN title</h1>
    <p>First paragraph of the article with enough information.</p>
    <p>Second paragraph continuing the story for capture.</p></body></html>
    """
    extraction = extract_msn_manual_article(
        source_url="https://www.msn.com/en-gb/news/example/story-id",
        artifact_text=html,
        artifact_file_name="article.html",
    )
    assert extraction.title == "Main MSN title"
    assert "First paragraph" in extraction.article_text
    assert extraction.artifact_file_name == "article.html"
    assert extraction.raw_html_payload_included is False
    assert extraction.full_local_path_serialized is False
    assert extraction.data_extraction_implemented is True
    payload = msn_manual_article_extraction_to_json(extraction)
    assert "<html>" not in payload
    assert "Main MSN title" in payload


def test_full_path_artifact_file_name_is_reduced_to_safe_name() -> None:
    extraction = extract_msn_manual_article(
        source_url="https://www.msn.com/en-gb/news/example/story-id",
        artifact_text="Title\nThis is enough body text for extraction to pass.",
        artifact_file_name=r"T:\\private\\article.html",
    )
    assert extraction.artifact_file_name == "article.html"
    assert extraction.full_local_path_serialized is False


if __name__ == "__main__":
    test_extracts_msn_article_text_from_html_without_raw_html()
    test_full_path_artifact_file_name_is_reduced_to_safe_name()
    print("MSN manual article extraction self-test passed.")
