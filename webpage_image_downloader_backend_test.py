from __future__ import annotations

from webpage_image_downloader_backend import discover_webpage_images
from source_resource_state import RESOURCE_KIND_IMAGE


def run_self_test() -> None:
    html = """
    <html>
      <head>
        <meta property="og:image" content="/og.jpg">
        <meta name="twitter:image" content="https://img.example.net/twitter.webp">
        <style>.hero{background-image:url('/hero.png')}</style>
      </head>
      <body>
        <picture><source srcset="/wide-800.jpg 800w, /wide-1600.jpg 1600w"></picture>
        <a href="/linked.gif">linked image</a>
        <img src="/photo.jpg" width="640" height="480" alt="Photo">
        <img srcset="/small.jpg 1x, /large.jpg 2x">
      </body>
    </html>
    """
    result = discover_webpage_images(
        "https://example.com/article",
        row_id="source:example",
        html_text=html,
    )
    assert result.deduplicated_count >= 8, result.to_dict()
    assert all(item.resource_kind == RESOURCE_KIND_IMAGE for item in result.resources)
    assert any(item.from_link for item in result.resources)
    assert any(item.width == 640 and item.height == 480 for item in result.resources)
    assert result.downloads_performed == "none"
    assert result.safety_flags["captcha_solver_used"] is False
    print("webpage_image_downloader_backend_test OK")


if __name__ == "__main__":
    run_self_test()
