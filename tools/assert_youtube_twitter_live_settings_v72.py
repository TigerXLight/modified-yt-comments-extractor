# Assertions for V72 live source settings and X/Twitter preview probing.

from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import App


def test_youtube_settings_apply_live() -> None:
    source = inspect.getsource(App._open_youtube_source_settings)
    assert "def apply_preferences()" in source
    assert "command=apply_preferences" in source
    assert "command=lambda _choice: apply_preferences()" in source
    assert "Settings apply immediately" in source
    assert 'text="Save"' not in source
    assert 'text="Cancel"' not in source


def test_twitter_preview_probe_is_wired_to_source_intake() -> None:
    enter_source = inspect.getsource(App._on_source_url_enter)
    probe_source = inspect.getsource(App._twitter_oembed_text_probe)
    start_source = inspect.getsource(App._start_twitter_source_row_metadata_probe)
    apply_source = inspect.getsource(App._apply_twitter_source_row_preview)
    assert "_start_twitter_source_row_metadata_probe(intake.rows)" in enter_source
    assert "publish.twitter.com/oembed" in probe_source
    assert "html.unescape" in probe_source
    assert "threading.Thread" in start_source
    assert "preview_text=preview" in apply_source
    assert "display_title=preview" in apply_source
    assert "title=preview" in apply_source


def main() -> None:
    tests = [
        test_youtube_settings_apply_live,
        test_twitter_preview_probe_is_wired_to_source_intake,
    ]
    for test in tests:
        test()
    print("assert_youtube_twitter_live_settings_v72 OK")


if __name__ == "__main__":
    main()
