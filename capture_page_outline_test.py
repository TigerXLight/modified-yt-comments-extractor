from capture_page_outline import build_page_outline_from_html


HTML = """<!doctype html>
<html>
<head><title>Example Fixture</title></head>
<body>
<nav>Navigation should be sampled as page chrome</nav>
<main>
  <h1>Main Heading</h1>
  <p>Visible page text.</p>
  <h2>Section Heading</h2>
  <a href="/one">One</a>
  <img src="/image.jpg" alt="Image alt">
  <video src="/clip.mp4"></video>
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


def test_page_outline_reports_reviewable_missing_structure() -> None:
    outline = build_page_outline_from_html("<html><body><p>Loose text</p></body></html>")

    assert outline.title == ""
    assert outline.headings == ()
    assert "No page title found." in outline.warnings
    assert "No heading structure found." in outline.warnings


def run_self_test() -> None:
    test_page_outline_extracts_title_headings_and_media_counts()
    test_page_outline_reports_reviewable_missing_structure()


if __name__ == "__main__":
    run_self_test()
    print("Capture page outline self-test passed.")
