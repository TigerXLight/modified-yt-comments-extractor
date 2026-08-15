from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "tools" else Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    runner = (ROOT / "twitter_browser_capture_runner.py").read_text(encoding="utf-8")
    inspector = (ROOT / "twitter_browser_capture_inspector.py").read_text(encoding="utf-8")
    runner_test = (ROOT / "twitter_browser_capture_runner_test.py").read_text(encoding="utf-8")
    inspector_test = (ROOT / "twitter_browser_capture_inspector_test.py").read_text(encoding="utf-8")

    assert "def extract_rendered_dom_media_inventory(" in runner
    assert "rendered_dom_status_metadata" in runner
    assert "rendered_dom_fallback_used" in runner
    assert "needs_review_http_404_no_items" in runner
    assert "source_url=clean_source_url" in runner

    assert "rendered_dom_status_available_api_404" in inspector
    assert "rendered_dom_media_metadata_captured" in inspector
    assert "safe_to_handoff = bool(media_items)" in inspector

    assert "test_extract_rendered_dom_media_inventory_from_status_dom" in runner_test
    assert "test_rendered_dom_fallback_does_not_activate_for_wrong_tweet_id" in runner_test
    assert "test_run_browser_capture_uses_rendered_dom_fallback_for_api_404" in runner_test
    assert "test_inspector_reports_rendered_dom_fallback_when_api_404_has_dom_media" in inspector_test
    print("assert_twitter_rendered_dom_fallback_v72d OK")


if __name__ == "__main__":
    main()
