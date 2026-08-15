from __future__ import annotations

import tempfile
from pathlib import Path

from twitter_browser_capture_strategy import (
    LIST_QUERY_CANDIDATES,
    build_twitter_browser_capture_plan,
    record_browser_network_page_boundary,
    should_continue_paging,
    unwrap_source_url,
    write_twitter_browser_capture_plan,
)
from twitter_media_backend import normalize_twitter_media_source_url
from twitter_route_strategy import canonicalize_twitter_url


def test_unwrap_markdown_url() -> None:
    assert unwrap_source_url("[https://x.com/example](https://x.com/example)") == "https://x.com/example"
    assert canonicalize_twitter_url("[https://x.com/example/status/123](https://x.com/example/status/123)") == "https://x.com/example/status/123"
    assert normalize_twitter_media_source_url("[https://x.com/example/status/123](https://x.com/example/status/123)") == "https://x.com/example/status/123"


def test_status_plan_uses_browser_and_shared_backend() -> None:
    plan = build_twitter_browser_capture_plan("[https://x.com/user/status/123](https://x.com/user/status/123)")
    assert plan.canonical_url == "https://x.com/user/status/123"
    assert plan.route_kind == "single_status_media"
    assert any(step.capture_medium == "shared_media_backend" for step in plan.steps)
    assert any("TweetDetail" in step.query_candidates for step in plan.steps)


def test_user_timeline_plan_encodes_list_workaround_without_guarantee() -> None:
    plan = build_twitter_browser_capture_plan(
        "https://x.com/example",
        list_workaround_url="https://x.com/i/lists/123",
    )
    assert plan.route_kind == "user_timeline_strict_limited"
    assert plan.list_workaround_url == "https://x.com/i/lists/123"
    assert plan.list_workaround_guarantees_full_export is False
    assert "list_workaround_not_guaranteed_complete" in plan.constraints
    assert any(step.query_candidates == LIST_QUERY_CANDIDATES for step in plan.steps)


def test_page_boundary_stops_on_no_next_page_data() -> None:
    boundary = record_browser_network_page_boundary(
        query_name="UserTweets",
        source_url="https://x.com/example",
        page_number=2,
        returned_items_count=20,
        cursor_in="one",
        cursor_out="two",
        next_page_requested=True,
        next_page_returned_data=False,
    )
    assert boundary.stop_reason == "next_page_requested_but_no_data_returned"
    assert boundary.completeness_state == "partial_api_boundary"
    assert should_continue_paging(boundary) is False


def test_page_boundary_continues_when_next_data_exists() -> None:
    boundary = record_browser_network_page_boundary(
        query_name="UserTweets",
        source_url="https://x.com/example",
        page_number=1,
        returned_items_count=20,
        cursor_out="two",
        next_page_returned_data=True,
    )
    assert should_continue_paging(boundary) is True


def test_write_plan_json() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v70_browser_plan_") as tmp:
        output = Path(tmp) / "browser-plan.json"
        write_twitter_browser_capture_plan(output, build_twitter_browser_capture_plan("https://x.com/user/status/123"))
        text = output.read_text(encoding="utf-8")
    assert '"schema_version": "twitter_browser_capture_strategy.v70"' in text
    assert '"single_status_media"' in text

def test_assertion_matches_imported_constant_runtime_plan() -> None:
    plan = build_twitter_browser_capture_plan(
        "https://x.com/example",
        list_workaround_url="https://x.com/i/lists/1234567890",
    )
    assert "list_workaround_not_guaranteed_complete" in plan.constraints
    assert plan.list_workaround_guarantees_full_export is False


def main() -> None:
    test_unwrap_markdown_url()
    test_status_plan_uses_browser_and_shared_backend()
    test_user_timeline_plan_encodes_list_workaround_without_guarantee()
    test_page_boundary_stops_on_no_next_page_data()
    test_page_boundary_continues_when_next_data_exists()
    test_write_plan_json()
    print("twitter_browser_capture_strategy_test OK")


if __name__ == "__main__":
    main()
