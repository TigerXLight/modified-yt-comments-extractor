from capture_article import (
    ARTICLE_STATUS_EMPTY,
    ARTICLE_STATUS_EXTRACTED,
    ARTICLE_STATUS_LOW_CONFIDENCE,
    extract_article_text_from_html,
    extract_article_text_from_rendered_text,
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


def test_article_extraction_filters_video_modal_newsletter_and_trending_chrome() -> None:
    html = """
    <html><head><title>'People shout seagull eater' | Metro</title></head><body>
      <article>
        <h1>'People shout seagull eater' | Metro</h1>
        <div class="vjs-modal-dialog">Play Video Play Mute Current Time 0:00 Duration -:- Fullscreen This is a modal window. Font Size 100% Done</div>
        <p>A Muslim woman has spoken out after a clip of her rescuing a baby seagull went viral.</p>
        <p>Nora Mubarak was secretly filmed as she tried to save an infant seagull.</p>
        <div class="newsletter-signup">Sign up for all of the latest stories Breaking News News Updates</div>
        <div class="trending-now"><p>Trending Now</p><p>Drunk Brit story</p></div>
        <p>She told Metro: ‘When I go out, people stare.’</p>
        <p>MORE: unrelated story link</p>
      </article>
    </body></html>
    """
    result = extract_article_text_from_html(html, source_url="https://metro.example/story")

    assert result.status == ARTICLE_STATUS_EXTRACTED
    assert "A Muslim woman has spoken out" in result.text
    assert "Nora Mubarak was secretly filmed" in result.text
    assert "She told Metro" in result.text
    assert "Play Video" not in result.text
    assert "Font Size" not in result.text
    assert "Breaking News" not in result.text
    assert "Trending Now" not in result.text
    assert "MORE:" not in result.text



def test_rendered_text_fallback_keeps_article_body_and_drops_video_rail() -> None:
    rendered = """
    HOME
    NEWS
    ‘People shout “seagull eater” at me in the street after far right lies’
    Barney Davis | Night News Editor
    Published July 17, 2026 6:00am Updated July 23, 2026 6:22pm
    Comments
    Muslim woman who far right painted as 'eating seagull' posts what really happened
    Video Player is loading.
    UP NEXT
    Teenage crash victim shared TikTok of police chase months before his death
    Reverend says Jews 'practice black magic' and 'r*tards turn to Islam' in online videos
    A Muslim woman has spoken out after a clip of her rescuing a baby seagull went viral with people accusing her of catching it for food.
    Nora Mubarak was secretly filmed as she tried to save an infant seagull which had fallen from its rooftop nest in Grimsby.
    She told Metro: ‘When I go out, people stare, and sometimes they say things.’
    TRENDING NOW
    Dad demands new trial after teenager who stabbed girl, 9, walks free
    """
    result = extract_article_text_from_rendered_text(
        rendered,
        source_url="https://metro.example/story",
        title="‘People shout “seagull eater” at me in the street after far right lies’ | Metro",
    )

    assert result.status == ARTICLE_STATUS_EXTRACTED
    assert result.method == "rendered_text_fallback_cleaned"
    assert "A Muslim woman has spoken out" in result.text
    assert "Nora Mubarak was secretly filmed" in result.text
    assert "She told Metro" in result.text
    assert "Video Player" not in result.text
    assert "UP NEXT" not in result.text
    assert "Reverend says" not in result.text
    assert "TRENDING NOW" not in result.text


def run_self_test() -> None:
    test_article_extraction_prefers_article_element()
    test_article_extraction_uses_main_fallback_with_warning()
    test_article_extraction_marks_body_fallback_low_confidence()
    test_article_extraction_marks_empty_html()
    test_article_extraction_excludes_nested_ad_like_regions_inside_article()
    test_article_extraction_excludes_chrome_heavy_localhost_fixture_sections()
    test_article_extraction_filters_video_modal_newsletter_and_trending_chrome()
    test_rendered_text_fallback_keeps_article_body_and_drops_video_rail()


if __name__ == "__main__":
    run_self_test()
    print("Capture article self-test passed.")
