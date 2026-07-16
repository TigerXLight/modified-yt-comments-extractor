from capture_article import (
    ARTICLE_STATUS_EMPTY,
    ARTICLE_STATUS_EXTRACTED,
    ARTICLE_STATUS_LOW_CONFIDENCE,
    extract_article_text_from_html,
)
from capture_fixture_server import CaptureFixtureServer
from urllib.request import urlopen


def test_article_extraction_prefers_article_element() -> None:
    result = extract_article_text_from_html(
        """
        <html><head><title>Fixture Title</title></head>
        <body>
        <nav>Navigation</nav>
        <article><h1>Article headline</h1><p>First paragraph.</p><p>Second paragraph.</p></article>
        <aside>Advertisement</aside>
        <section id="comments"><p>A reader comment should stay out.</p></section>
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
    assert "reader comment" not in result.text
    assert "excluded_comments_region" in result.contamination_signals
    assert result.excluded_region_counts["comments"] == 1
    assert any("Comment/discussion regions" in warning for warning in result.warnings)


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


def test_article_extraction_excludes_nested_ad_like_regions_inside_article() -> None:
    result = extract_article_text_from_html(
        """
        <html><body>
        <article>
          <h1>Story</h1>
          <p>Article text before advert.</p>
          <div class="sponsored advert"><p>Sponsored text must not appear.</p></div>
          <p>Article text after advert.</p>
        </article>
        </body></html>
        """
    )

    assert result.status == ARTICLE_STATUS_EXTRACTED
    assert "Article text before advert." in result.text
    assert "Article text after advert." in result.text
    assert "Sponsored text" not in result.text
    assert result.excluded_region_counts["advertising"] == 1
    assert "excluded_advertising_region" in result.contamination_signals


def test_article_extraction_excludes_chrome_heavy_localhost_fixture_sections() -> None:
    with CaptureFixtureServer() as server:
        source_url = server.url_for_fixture("article_chrome_heavy")
        with urlopen(source_url, timeout=5) as response:
            html = response.read().decode("utf-8")

    result = extract_article_text_from_html(html, source_url=source_url)

    assert result.status == ARTICLE_STATUS_EXTRACTED
    assert "Primary story." in result.text
    assert "Navigation" not in result.text
    assert "Advertisement" not in result.text
    assert "Fixture comment" not in result.text
    assert result.excluded_region_counts["comments"] == 1
    assert result.excluded_region_counts["advertising"] == 1


def run_self_test() -> None:
    test_article_extraction_prefers_article_element()
    test_article_extraction_uses_main_fallback_with_warning()
    test_article_extraction_marks_body_fallback_low_confidence()
    test_article_extraction_marks_empty_html()
    test_article_extraction_excludes_nested_ad_like_regions_inside_article()
    test_article_extraction_excludes_chrome_heavy_localhost_fixture_sections()


if __name__ == "__main__":
    run_self_test()
    print("Capture article self-test passed.")
