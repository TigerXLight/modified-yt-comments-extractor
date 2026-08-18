from __future__ import annotations

from webpage_image_downloader_backend import (
    discover_webpage_images,
    discover_webpage_images_for_row,
    discover_webpage_images_rendered,
    close_rendered_browser_discovery_worker,
    prewarm_rendered_browser_discovery_worker,
    start_internal_browser_image_discovery_service,
)
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
    assert result.network_actions_performed == "one page static HTML fetch only"
    assert callable(discover_webpage_images_rendered)
    assert callable(discover_webpage_images_for_row)
    assert callable(close_rendered_browser_discovery_worker)
    assert callable(prewarm_rendered_browser_discovery_worker)
    assert callable(start_internal_browser_image_discovery_service)
    backend_source = __import__("inspect").getsource(__import__("webpage_image_downloader_backend"))
    assert "_create_rendered_discovery_context" in backend_source
    assert "_rendered_browser_candidate_dicts_with_context" in backend_source
    print("webpage_image_downloader_backend_test OK")


if __name__ == "__main__":
    run_self_test()
