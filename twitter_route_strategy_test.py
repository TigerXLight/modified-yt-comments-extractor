from __future__ import annotations
import tempfile
from pathlib import Path
from twitter_route_strategy import *

def test_classify_common_twitter_routes():
    assert classify_twitter_route("https://x.com/user/status/123") == "single_status_media"
    assert classify_twitter_route("https://twitter.com/user") == "user_timeline_strict_limited"
    assert classify_twitter_route("https://x.com/i/lists/123") == "list_timeline_workaround"
    assert classify_twitter_route("https://x.com/i/article/123") == "article_export_render"

def test_single_status_strategy_uses_shared_media_backend():
    s = build_twitter_route_strategy("https://x.com/user/status/123", output_dir="out")
    assert s.primary_route == "twitter_x_media_shared_backend"
    assert "browser_network_media_capture" in s.fallback_routes
    assert any(a.component == "shared_media_backend" for a in s.actions)

def test_user_timeline_constraints():
    s = build_twitter_route_strategy("https://x.com/example")
    assert LIST_WORKAROUND_NOT_GUARANTEED in s.constraints
    assert STOP_WHEN_NO_NEXT_PAGE in s.constraints
    assert "partial" in s.completion_policy

def test_pagination_boundary_no_next_page():
    b = record_twitter_pagination_boundary(route_kind="user_timeline_strict_limited", source_url="https://x.com/example", page_number=3, returned_items_count=20, next_cursor="abc", api_returned_next_page_data=False)
    assert b.stopped_reason == "next_cursor_present_but_no_next_page_data_returned"
    assert b.completeness_state == "partial_api_boundary"

def test_write_json():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "route.json"
        write_twitter_route_strategy(p, build_twitter_route_strategy("https://x.com/user/status/123", output_dir=tmp))
        assert '"single_status_media"' in p.read_text(encoding="utf-8")

def main():
    test_classify_common_twitter_routes()
    test_single_status_strategy_uses_shared_media_backend()
    test_user_timeline_constraints()
    test_pagination_boundary_no_next_page()
    test_write_json()
    print("twitter_route_strategy_test OK")

if __name__ == "__main__":
    main()
