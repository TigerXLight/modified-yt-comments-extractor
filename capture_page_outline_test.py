from capture_article import extract_article_text_from_html
from capture_page_outline import build_page_outline_from_html, format_page_outline_text


HTML = """<!doctype html>
<html>
<head><title>Example Fixture</title></head>
<body>
<header><nav><p>Navigation should be sampled as page chrome</p></nav></header>
<main>
  <article>
    <h1>Main Heading</h1>
    <p>Visible page text.</p>
    <h2>Section Heading</h2>
  </article>
  <a href="/one">One</a>
  <img src="/image.jpg" alt="Image alt">
  <video src="/clip.mp4"></video>
  <section id="comments"><p>Visible comment text.</p></section>
</main>
</body>
</html>
"""


def test_page_outline_extracts_title_headings_and_media_counts() -> None:
    outline = build_page_outline_from_html(HTML, source_url="http://127.0.0.1/article/static")

    assert outline.title == "Example Fixture"
    assert [heading.to_dict() for heading in outline.headings] == [
        {"level": 1, "text": "Main Heading"},
        {"level": 2, "text": "Section Heading"},
    ]
    assert outline.link_count == 1
    assert outline.image_count == 1
    assert outline.video_count == 1
    assert outline.media_references[0].source == "/image.jpg"
    assert outline.media_references[0].alt_text == "Image alt"
    assert "Visible page text" in outline.text_sample
    assert outline.outline_lines[:5] == (
        "[Header]",
        "  [Navigation]",
        "    Navigation should be sampled as page chrome",
        "[Main]",
        "  [Article]",
    )
    assert "  [Comments]" in outline.outline_lines
    assert "    Visible comment text." in outline.outline_lines


def test_page_outline_reports_reviewable_missing_structure() -> None:
    outline = build_page_outline_from_html("<html><body><p>Loose text</p></body></html>")

    assert outline.title == ""
    assert outline.headings == ()
    assert "No page title found." in outline.warnings
    assert "No heading structure found." in outline.warnings


def test_page_outline_text_is_distinct_from_article_semantic_text() -> None:
    outline = build_page_outline_from_html(HTML)
    article = extract_article_text_from_html(HTML)
    outline_text = format_page_outline_text(outline)

    assert "[Navigation]" in outline_text
    assert "[Comments]" in outline_text
    assert "Visible comment text" in outline_text
    assert "Visible comment text" not in article.text
    assert outline_text != article.text


def run_self_test() -> None:
    test_page_outline_extracts_title_headings_and_media_counts()
    test_page_outline_reports_reviewable_missing_structure()
    test_page_outline_text_is_distinct_from_article_semantic_text()


if __name__ == "__main__":
    run_self_test()
    print("Capture page outline self-test passed.")
