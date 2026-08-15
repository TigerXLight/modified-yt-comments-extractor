from __future__ import annotations

import json
import tempfile
from pathlib import Path

from twitter_browser_capture_inspector import inspect_twitter_browser_capture_output, write_twitter_browser_capture_inspection


def test_inspector_detects_playwright_missing() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72_inspect_missing_") as tmp:
        out = Path(tmp)
        (out / "browser_session_manifest.json").write_text(
            json.dumps({"status": "failed", "source_url": "https://x.com/example/status/123", "canonical_url": "https://x.com/example/status/123", "errors": ["playwright_unavailable:No module named 'playwright'"]}),
            encoding="utf-8",
        )
        (out / "network_events.jsonl").write_text("", encoding="utf-8")
        (out / "api_pages.jsonl").write_text("", encoding="utf-8")
        (out / "media_inventory.json").write_text("[]", encoding="utf-8")
        (out / "cursor_boundaries.json").write_text("[]", encoding="utf-8")
        inspection = inspect_twitter_browser_capture_output(out)
    assert inspection.diagnosis == "playwright_missing"
    assert inspection.safe_to_handoff_to_jd is False
    assert "install Playwright" in inspection.next_action


def test_inspector_detects_media_discovered() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72_inspect_media_") as tmp:
        out = Path(tmp)
        (out / "browser_session_manifest.json").write_text(
            json.dumps({"status": "success", "source_url": "https://x.com/example/status/123", "canonical_url": "https://x.com/example/status/123", "api_page_count": 1, "network_event_count": 1, "media_item_count": 1, "evidence_completion_claim": "completed"}),
            encoding="utf-8",
        )
        (out / "network_events.jsonl").write_text('{"query_name":"TweetDetail"}\n', encoding="utf-8")
        (out / "api_pages.jsonl").write_text('{"query_name":"TweetDetail"}\n', encoding="utf-8")
        (out / "media_inventory.json").write_text('[{"media_url":"https://video.twimg.com/example.mp4"}]', encoding="utf-8")
        (out / "cursor_boundaries.json").write_text('[{"completeness_state":"complete_if_known_total_else_partial_boundary"}]', encoding="utf-8")
        (out / "screenshot.png").write_bytes(b"png")
        (out / "rendered_dom_snapshot.html").write_text("<html></html>", encoding="utf-8")
        inspection = inspect_twitter_browser_capture_output(out)
    assert inspection.diagnosis == "media_discovered"
    assert inspection.safe_to_handoff_to_jd is True
    assert "TweetDetail" in inspection.matched_query_names
    assert inspection.screenshot_exists is True
    assert inspection.rendered_dom_exists is True


def test_write_inspection_json() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72_inspect_write_") as tmp:
        out = Path(tmp) / "capture"
        out.mkdir()
        (out / "browser_session_manifest.json").write_text('{"status":"planned"}', encoding="utf-8")
        inspection = inspect_twitter_browser_capture_output(out)
        dest = Path(tmp) / "inspection.json"
        write_twitter_browser_capture_inspection(dest, inspection)
        data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["schema_version"] == "twitter_browser_capture_inspector.v72"
    assert data["manifest_exists"] is True


def main() -> None:
    test_inspector_detects_playwright_missing()
    test_inspector_detects_media_discovered()
    test_write_inspection_json()
    print("twitter_browser_capture_inspector_test OK")


if __name__ == "__main__":
    main()
