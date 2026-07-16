from capture_article import (
    ARTICLE_STATUS_EMPTY,
    ARTICLE_STATUS_EXTRACTED,
    ARTICLE_STATUS_LOW_CONFIDENCE,
    extract_article_text_from_html,
)


def test_article_extraction_prefers_article_element() -> None:
    result = extract_article_text_from_html(
        """
        <html><head><title>Fixture Title</title></head>
        <body>
        <nav>Navigation</nav>
        <article><h1>Article headline</h1><p>First paragraph.</p><p>Second paragraph.</p></article>
        <aside>Advertisement</aside>
        </body></html>
        """,
        source_url="http://127.0.0.1/article/static",
    )

    assert result.status == ARTICLE_STATUS_EXTRACTED
    assert result.title == "Fixture Title"
    assert result.method == "semantic_article"
    assert result.confidence == 0.9
    assert "Article headline" in result.text
    assert "Advertisement" not in result.text


def test_article_extraction_uses_main_fallback_with_warning() -> None:
    result = extract_article_text_from_html(
        "<html><body><main><h1>Main headline</h1><p>Main text.</p></main></body></html>"
    )

    assert result.status == ARTICLE_STATUS_EXTRACTED
    assert result.method == "semantic_main"
    assert result.confidence == 0.7
    assert "No article element found" in result.warnings[0]


def test_article_extraction_marks_body_fallback_low_confidence() -> None:
    result = extract_article_text_from_html("<html><body><p>Loose body text.</p></body></html>")

    assert result.status == ARTICLE_STATUS_LOW_CONFIDENCE
    assert result.method == "body_fallback"
    assert result.confidence == 0.35
    assert any("low-confidence body fallback" in warning for warning in result.warnings)


def test_article_extraction_marks_empty_html() -> None:
    result = extract_article_text_from_html("<html><body><script>var x = 1;</script></body></html>")

    assert result.status == ARTICLE_STATUS_EMPTY
    assert result.text == ""
    assert result.confidence == 0.0


def run_self_test() -> None:
    test_article_extraction_prefers_article_element()
    test_article_extraction_uses_main_fallback_with_warning()
    test_article_extraction_marks_body_fallback_low_confidence()
    test_article_extraction_marks_empty_html()


if __name__ == "__main__":
    run_self_test()
    print("Capture article self-test passed.")
