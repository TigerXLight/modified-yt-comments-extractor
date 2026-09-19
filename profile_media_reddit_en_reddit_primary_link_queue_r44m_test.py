#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from profile_media_reddit_en_reddit_primary_link_queue_r44m import (
    EXPECTED_BRANCH_LABEL_ORDER,
    PASS_STATUS_R44M,
    build_default_en_reddit_primary_queue_items_r44m,
    build_reddit_en_reddit_primary_link_queue_contract_r44m,
    normalize_to_en_reddit_url_r44m,
    run_self_test,
)


def test_url_conversion_to_en_reddit() -> None:
    source = "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/?force-legacy-sct=1&limit=999"
    converted = normalize_to_en_reddit_url_r44m(source)
    parsed = urlparse(converted)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "en.reddit.com"
    assert query["force-legacy-sct"] == ["1"]
    assert query["sort"] == ["old"]
    assert query["limit"] == ["500"]
    assert query["ext-referrer"] == ["DIRECT"]


def test_primary_queue_order_login_requirement_and_host() -> None:
    items = build_default_en_reddit_primary_queue_items_r44m()
    assert len(items) == 28
    assert items[0].order_label == "main"
    branch_labels = [item.order_label for item in items[1:]]
    assert branch_labels == EXPECTED_BRANCH_LABEL_ORDER
    assert branch_labels[2] == "2.1"
    assert items[3].parent_order_label == "2"
    assert all(item.status == "pending" for item in items)
    assert all(item.logged_in_account_required is True for item in items)
    assert all(urlparse(item.capture_url).netloc == "en.reddit.com" for item in items)
    assert items[1].source_domain == "www.reddit.com"


def test_contract_makes_r44l_secondary() -> None:
    contract = build_reddit_en_reddit_primary_link_queue_contract_r44m()
    assert contract["logged_in_account_required"] is True
    assert contract["not_no_login_primary"] is True
    assert "en.reddit.com" in contract["primary_logged_in_route"]
    assert "secondary fallback" in contract["secondary_fallback_route"].lower()
    assert "R44L" in contract["secondary_fallback_route"]
    assert any("webview2" in f.lower() for f in contract["hierarchy_reference"]["webview2_related_files_noted"])


def test_self_test_writes_reports() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        payload = run_self_test(Path(tmp))
        assert payload["status"] == PASS_STATUS_R44M
        result = payload["sample_result"]
        assert result["queue_item_count"] == 28
        assert result["branch_url_count"] == 27
        assert result["all_capture_urls_are_en_reddit"] is True
        assert result["all_items_require_logged_in_account"] is True
        queue_path = Path(result["queue_path"])
        assert queue_path.exists()
        queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
        assert len(queue_payload["items"]) == 28
        assert queue_payload["items"][0]["url_kind"] == "main_thread"
        assert all(check["status"] == "pass" for check in payload["checks"])


def run_self_tests() -> None:
    test_url_conversion_to_en_reddit()
    test_primary_queue_order_login_requirement_and_host()
    test_contract_makes_r44l_secondary()
    test_self_test_writes_reports()
    print("profile_media_reddit_en_reddit_primary_link_queue_r44m_test: PASS")


if __name__ == "__main__":
    run_self_tests()
