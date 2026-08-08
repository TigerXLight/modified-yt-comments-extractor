from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from source_local_browser_execution import (
    LocalBrowserExecutionStatus,
    LocalScreenshotLabel,
    build_protected_black_output_result,
    run_local_fixture_browser_execution,
)


FIXTURE_HTML = """
<html>
  <head><title>Fixture Story</title></head>
  <body>
    <main>
      <article><h1>Fixture Headline</h1><p>Article body text for extraction.</p></article>
      <section data-scroll-container="true">
        <div data-comment-id="c1" data-author="A" data-source-order="1">First comment</div>
        <div data-comment-id="c1" data-author="A" data-source-order="2">Duplicate comment</div>
        <div data-comment-id="c2" data-state="deleted">Deleted comment</div>
      </section>
      <section>
        <div data-event-id="l1" data-author="Chat">Live message</div>
        <div data-event-id="l2" data-event-type="removed" data-removed="true">Removed</div>
      </section>
      <video src="/media/video.mp4" poster="/media/poster.jpg"></video>
      <audio src="/media/audio.mp3"></audio>
    </main>
  </body>
</html>
"""


class SourceLocalBrowserExecutionTest(unittest.TestCase):
    def test_local_fixture_execution_writes_artifacts_and_runs_extractors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_local_fixture_browser_execution(
                html=FIXTURE_HTML,
                output_directory=temp_dir,
                source_url="local-fixture://article",
                element_selector="article",
            )
            self.assertEqual(result.status, LocalBrowserExecutionStatus.COMPLETED)
            self.assertTrue(result.browser_automation_implemented)
            self.assertFalse(result.external_network_performed)
            self.assertTrue((Path(temp_dir) / "rendered_dom.html").is_file())
            self.assertTrue((Path(temp_dir) / "faithful_full_page.png").is_file())
            self.assertTrue((Path(temp_dir) / "selected_element.png").is_file())
            self.assertEqual(result.screenshots[0].label, LocalScreenshotLabel.FAITHFUL_PAGE)
            self.assertEqual(result.screenshots[0].width, 1)
            self.assertIn("Article body text", result.article.text)
            self.assertGreaterEqual(len(result.page_outline.outline_lines), 1)
            self.assertEqual(len(result.comments.comments), 2)
            self.assertIn("c1", result.comments.duplicate_comment_ids)
            self.assertEqual(len(result.livechat.events), 2)
            self.assertGreaterEqual(len(result.media_discovery.resources), 3)

    def test_external_url_is_blocked_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_local_fixture_browser_execution(
                html=FIXTURE_HTML,
                output_directory=temp_dir,
                source_url="https://example.com/live",
            )
            self.assertEqual(result.status, LocalBrowserExecutionStatus.BLOCKED_EXTERNAL_URL)
            self.assertFalse((Path(temp_dir) / "rendered_dom.html").exists())
            self.assertFalse(result.external_network_performed)

    def test_protected_black_output_writes_blocked_screenshot_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = build_protected_black_output_result(
                source_url="local-fixture://protected",
                output_directory=temp_dir,
            )
            self.assertEqual(result.status, LocalBrowserExecutionStatus.FAILED)
            self.assertEqual(result.screenshots[0].label, LocalScreenshotLabel.PROTECTED_BLACK_OUTPUT)
            self.assertTrue(result.screenshots[0].protected_or_black_output)
            self.assertTrue((Path(temp_dir) / "protected_black_output.png").is_file())


if __name__ == "__main__":
    unittest.main()

