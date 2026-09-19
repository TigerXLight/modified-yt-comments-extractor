#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from profile_media_reddit_normal_site_link_queue_r44l import (
    EXPECTED_BRANCH_LABEL_ORDER,
    PASS_STATUS_R44L,
    build_default_normal_site_queue_items_r44l,
    normalize_to_current_reddit_url_r44l,
    run_self_test,
)


def test_url_normalization() -> None:
    url = "https://en.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/?force-legacy-sct=1&limit=500"
    normalized = normalize_to_current_reddit_url_r44l(url)
    parsed = urlparse(normalized)
    assert parsed.netloc == "www.reddit.com"
    assert "limit=500" not in normalized
    assert "force-legacy-sct=1" in normalized


def test_queue_order_and_resumable_statuses() -> None:
    items = build_default_normal_site_queue_items_r44l()
    assert len(items) == 28
    assert items[0].order_label == "main"
    branch_labels = [item.order_label for item in items[1:]]
    assert branch_labels == EXPECTED_BRANCH_LABEL_ORDER
    assert branch_labels[2] == "2.1"
    assert items[3].parent_order_label == "2"
    assert all(item.status == "pending" for item in items)
    assert all(urlparse(item.capture_url).netloc == "www.reddit.com" for item in items)


def test_self_test_writes_reports() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        payload = run_self_test(Path(tmp))
        assert payload["status"] == PASS_STATUS_R44L
        result = payload["sample_result"]
        assert result["queue_item_count"] == 28
        assert result["branch_url_count"] == 27
        queue_path = Path(result["queue_path"])
        assert queue_path.exists()
        queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
        assert len(queue_payload["items"]) == 28
        assert queue_payload["items"][0]["url_kind"] == "main_thread"
        assert payload["checks"][-1]["status"] == "pass"


def run_self_tests() -> None:
    test_url_normalization()
    test_queue_order_and_resumable_statuses()
    test_self_test_writes_reports()
    print("profile_media_reddit_normal_site_link_queue_r44l_test: PASS")


if __name__ == "__main__":
    run_self_tests()
