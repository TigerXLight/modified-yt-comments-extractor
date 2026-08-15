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


def test_inspector_flags_markdown_url_leak() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72b_inspect_markdown_") as tmp:
        out = Path(tmp)
        (out / "browser_session_manifest.json").write_text(
            json.dumps(
                {
                    "status": "success",
                    "source_url": "[https://x.com/example/status/123](https://x.com/example/status/123)",
                    "canonical_url": "[https://x.com/example/status/123](https://x.com/example/status/123)",
                    "evidence_completion_claim": "completed",
                }
            ),
            encoding="utf-8",
        )
        inspection = inspect_twitter_browser_capture_output(out)
    assert inspection.diagnosis == "runner_url_not_normalized"
    assert inspection.evidence_completion_claim == "not_completed"
    assert inspection.safe_to_handoff_to_jd is False


def test_inspector_flags_http_404_zero_items_as_not_completed() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72b_inspect_404_") as tmp:
        out = Path(tmp)
        (out / "browser_session_manifest.json").write_text(
            json.dumps(
                {
                    "status": "success",
                    "source_url": "https://x.com/example/status/404",
                    "canonical_url": "https://x.com/example/status/404",
                    "api_page_count": 2,
                    "network_event_count": 420,
                    "media_item_count": 0,
                    "evidence_completion_claim": "completed",
                }
            ),
            encoding="utf-8",
        )
        (out / "api_pages.jsonl").write_text('{"query_name":"twitter_api"}\n', encoding="utf-8")
        (out / "network_events.jsonl").write_text('{"query_name":"twitter_api"}\n', encoding="utf-8")
        (out / "media_inventory.json").write_text("[]", encoding="utf-8")
        (out / "cursor_boundaries.json").write_text(
            json.dumps(
                [
                    {
                        "query_name": "twitter_api",
                        "http_status": 404,
                        "returned_items_count": 0,
                        "completeness_state": "complete_if_known_total_else_partial_boundary",
                    }
                ]
            ),
            encoding="utf-8",
        )
        inspection = inspect_twitter_browser_capture_output(out)
    assert inspection.status == "needs_review"
    assert inspection.diagnosis == "twitter_api_http_404_no_items"
    assert inspection.evidence_completion_claim == "not_completed"
    assert inspection.safe_to_handoff_to_jd is False




def test_inspector_reports_rendered_dom_fallback_when_api_404_has_dom_media() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72d_inspect_dom_fallback_") as tmp:
        out = Path(tmp)
        (out / "browser_session_manifest.json").write_text(
            json.dumps(
                {
                    "status": "needs_review",
                    "source_url": "https://x.com/DuvalMagic/status/2085760210359267524",
                    "canonical_url": "https://x.com/DuvalMagic/status/2085760210359267524",
                    "api_page_count": 1,
                    "network_event_count": 409,
                    "media_item_count": 1,
                    "api_completion_state": "needs_review_http_404_no_items",
                    "rendered_dom_status_available": True,
                    "rendered_dom_media_item_count": 1,
                    "rendered_dom_fallback_used": True,
                    "evidence_completion_claim": "rendered_status_media_metadata_captured",
                }
            ),
            encoding="utf-8",
        )
        (out / "api_pages.jsonl").write_text('{"query_name":"twitter_api"}\n', encoding="utf-8")
        (out / "network_events.jsonl").write_text('{"query_name":"twitter_api"}\n', encoding="utf-8")
        (out / "media_inventory.json").write_text(
            json.dumps(
                [
                    {
                        "media_url": "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large",
                        "from_query_name": "rendered_dom",
                        "source_kind": "rendered_dom_og_image",
                        "provenance": "rendered_dom_status_metadata",
                    }
                ]
            ),
            encoding="utf-8",
        )
        (out / "cursor_boundaries.json").write_text(
            json.dumps(
                [
                    {
                        "query_name": "twitter_api",
                        "http_status": 404,
                        "returned_items_count": 0,
                        "completeness_state": "complete_if_known_total_else_partial_boundary",
                    }
                ]
            ),
            encoding="utf-8",
        )
        (out / "rendered_dom_snapshot.html").write_text("<html></html>", encoding="utf-8")
        inspection = inspect_twitter_browser_capture_output(out)
    assert inspection.diagnosis == "rendered_dom_status_available_api_404"
    assert inspection.safe_to_handoff_to_jd is True
    assert inspection.rendered_dom_status_available is True
    assert inspection.rendered_dom_fallback_used is True
    assert inspection.rendered_dom_media_item_count == 1
    assert inspection.evidence_completion_claim == "rendered_status_media_metadata_captured"


def test_inspector_keeps_rendered_dom_metadata_claim_conservative_without_download() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72e_inspect_dom_metadata_") as tmp:
        out = Path(tmp)
        (out / "browser_session_manifest.json").write_text(
            json.dumps(
                {
                    "status": "needs_review",
                    "source_url": "https://x.com/DuvalMagic/status/2085760210359267524",
                    "canonical_url": "https://x.com/DuvalMagic/status/2085760210359267524",
                    "api_page_count": 1,
                    "network_event_count": 413,
                    "media_item_count": 1,
                    "api_completion_state": "captured_with_boundaries",
                    "rendered_dom_status_available": True,
                    "rendered_dom_media_item_count": 1,
                    "rendered_dom_fallback_used": False,
                    "evidence_completion_claim": "rendered_status_media_metadata_captured",
                    "media_backend_result_paths": [],
                }
            ),
            encoding="utf-8",
        )
        (out / "api_pages.jsonl").write_text('{"query_name":"twitter_api"}\n', encoding="utf-8")
        (out / "network_events.jsonl").write_text('{"query_name":"twitter_api"}\n', encoding="utf-8")
        (out / "media_inventory.json").write_text(
            json.dumps(
                [
                    {
                        "media_url": "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large",
                        "from_query_name": "rendered_dom",
                        "source_kind": "rendered_dom_og_image",
                        "provenance": "rendered_dom_status_metadata",
                    }
                ]
            ),
            encoding="utf-8",
        )
        (out / "cursor_boundaries.json").write_text(
            json.dumps(
                [
                    {
                        "query_name": "twitter_api",
                        "http_status": 200,
                        "returned_items_count": 0,
                        "completeness_state": "partial_api_boundary",
                    }
                ]
            ),
            encoding="utf-8",
        )
        (out / "rendered_dom_snapshot.html").write_text("<html></html>", encoding="utf-8")
        inspection = inspect_twitter_browser_capture_output(out)
    assert inspection.diagnosis == "rendered_dom_media_metadata_captured"
    assert inspection.safe_to_handoff_to_jd is True
    assert inspection.status == "needs_review"
    assert inspection.evidence_completion_claim == "rendered_status_media_metadata_captured"

def main() -> None:
    test_inspector_detects_playwright_missing()
    test_inspector_detects_media_discovered()
    test_write_inspection_json()
    test_inspector_flags_markdown_url_leak()
    test_inspector_flags_http_404_zero_items_as_not_completed()
    test_inspector_reports_rendered_dom_fallback_when_api_404_has_dom_media()
    test_inspector_keeps_rendered_dom_metadata_claim_conservative_without_download()
    print("twitter_browser_capture_inspector_test OK")


if __name__ == "__main__":
    main()
