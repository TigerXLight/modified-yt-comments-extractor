from __future__ import annotations

import json
import tempfile
from pathlib import Path
from urllib.parse import urlencode

from twitter_capture_live_output_closeout_v77c import (
    WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C,
    build_repaired_next_cursor_url,
    build_twitter_live_output_closeout,
    render_twitter_live_output_closeout_text,
    write_twitter_live_output_closeout,
)


SOURCE_URL = "https://x.com/examaddaorg"
CANONICAL_URL = "https://x.com/examaddaorg/with_replies"
CURSOR_1 = "DAABCgABHP4xEYS__-oKAAIc_ZV-bNpBOwgAAwAAAAIAAA"
CURSOR_2 = "DAABCgABHP4xEYS__9QKAAIc_YMy1lvQ0AgAAwAAAAIAAA"


def _request_url(cursor: str = "") -> str:
    variables = {"userId": "2010743683663220736", "count": 20, "includePromotedContent": True}
    if cursor:
        variables["cursor"] = cursor
    query = urlencode({"variables": json.dumps(variables, separators=(",", ":")), "features": "{}", "fieldToggles": "{}"})
    return f"https://x.com/i/api/graphql/dRUXRSlEIPlVmPgOQ8Z43g/UserRepliesTimeline?{query}"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _entry(index: int, *, media_limit: int, reply_limit: int) -> dict:
    status_id = str(2089000000000000000 + index)
    return {
        "schema_version": "twitter_browser_timeline_entry.v74",
        "status_id": status_id,
        "canonical_url": f"https://x.com/examaddaorg/status/{status_id}",
        "source_url": CANONICAL_URL,
        "source_query_name": "UserRepliesTimeline",
        "source_page_number": 1 if index <= 43 else 2,
        "author_name": "",
        "screen_name": "",
        "post_text": f"Fixture post {index}",
        "created_at": "Sun Aug 16 17:07:46 +0000 2026",
        "conversation_id": status_id if index > reply_limit else "2089000000000000000",
        "in_reply_to_status_id": "2089000000000000000" if index <= reply_limit else "",
        "in_reply_to_screen_name": "someone" if index <= reply_limit else "",
        "reply_count": 0,
        "retweet_count": 0,
        "quote_count": 0,
        "like_count": index,
        "bookmark_count": 0,
        "view_count": str(index * 10),
        "links": [],
        "media_urls": [f"https://pbs.twimg.com/media/example{index}.jpg"] if index <= media_limit else [],
        "provenance": "browser_session_graphql_timeline_entry_v74",
    }


def _make_fixture(root: Path) -> Path:
    output_root = root / "ytce_twitter_v77b_manual_probe"
    cycle1 = output_root / "examaddaorg_replies_v77b_probe_cycle_0001"
    cycle2 = output_root / "examaddaorg_replies_v77b_probe_cycle_0002"
    cycle3 = output_root / "examaddaorg_replies_v77b_probe_cycle_0003"
    for cycle in (cycle1, cycle2, cycle3):
        cycle.mkdir(parents=True, exist_ok=True)

    entries1 = [_entry(i, media_limit=7, reply_limit=21) for i in range(1, 44)]
    entries2 = [_entry(i, media_limit=13, reply_limit=41) for i in range(1, 81)]
    entries3 = [_entry(i, media_limit=13, reply_limit=41) for i in range(1, 81)]
    _write_jsonl(cycle1 / "cursor_entries.jsonl", entries1)
    _write_jsonl(cycle2 / "cursor_entries.jsonl", entries2)
    _write_jsonl(cycle3 / "cursor_entries.jsonl", entries3)
    _write_jsonl(
        cycle1 / "cursor_pages.jsonl",
        [
            {
                "page_number": 1,
                "cursor_out": CURSOR_1,
                "request_url": _request_url(),
                "response_status": 200,
                "rate_limit_remaining": 49,
                "cooldown_until_utc": "2026-08-17T01:38:51Z",
                "rate_limit_decision": "soft_page_budget_pause",
                "replay_mode": "live_initial_browser_response_v74d",
                "returned_items_count": 43,
            }
        ],
    )
    _write_jsonl(
        cycle2 / "cursor_pages.jsonl",
        [
            {"page_number": 1, "cursor_out": CURSOR_1, "request_url": _request_url(), "response_status": 200, "rate_limit_decision": "soft_page_budget_pause", "replay_mode": "live_initial_browser_response_v74d"},
            {"page_number": 2, "cursor_in": CURSOR_1, "cursor_out": CURSOR_2, "request_url": _request_url(CURSOR_1), "response_status": 200, "rate_limit_decision": "soft_page_budget_pause", "replay_mode": "browser_fetch_cursor_resume_v74g"},
        ],
    )
    _write_jsonl(
        cycle3 / "cursor_pages.jsonl",
        [
            {"page_number": 1, "cursor_out": CURSOR_1, "request_url": _request_url(), "response_status": 200, "rate_limit_decision": "soft_page_budget_pause", "replay_mode": "live_initial_browser_response_v74d"},
            {"page_number": 2, "cursor_in": CURSOR_1, "cursor_out": CURSOR_2, "request_url": _request_url(CURSOR_1), "response_status": 200, "rate_limit_decision": "soft_page_budget_pause", "replay_mode": "browser_fetch_cursor_resume_v74g"},
            {"page_number": 3, "cursor_in": CURSOR_2, "cursor_out": "", "request_url": _request_url(CURSOR_2), "response_status": 403, "rate_limit_decision": "stop_auth_or_access_boundary", "replay_mode": "browser_fetch_cursor_resume_v74g"},
        ],
    )
    _write_json(
        cycle1 / "cursor_scheduler_state.json",
        {"source_url": SOURCE_URL, "canonical_url": CANONICAL_URL, "pages_count": 1, "entries_count": 43, "unique_entries_count": 43, "last_cursor_out": "", "next_cursor_url": "", "stop_reason": "soft_page_budget_pause_boundary", "latest_rate_limit_decision": "soft_page_budget_pause"},
    )
    _write_json(
        cycle2 / "cursor_scheduler_state.json",
        {"source_url": SOURCE_URL, "canonical_url": CANONICAL_URL, "pages_count": 2, "entries_count": 80, "unique_entries_count": 80, "last_cursor_out": CURSOR_2, "next_cursor_url": _request_url(CURSOR_2), "stop_reason": "soft_page_budget_pause_boundary", "latest_rate_limit_decision": "soft_page_budget_pause"},
    )
    _write_json(
        cycle3 / "cursor_scheduler_state.json",
        {"source_url": SOURCE_URL, "canonical_url": CANONICAL_URL, "pages_count": 3, "entries_count": 80, "unique_entries_count": 80, "last_cursor_out": CURSOR_2, "next_cursor_url": _request_url(CURSOR_2), "stop_reason": "auth_or_access_boundary", "latest_rate_limit_decision": "stop_auth_or_access_boundary"},
    )
    for cycle, remaining, cooldown, decision, status in (
        (cycle1, 49, "2026-08-17T01:38:51Z", "soft_page_budget_pause", 200),
        (cycle2, 48, "2026-08-17T02:03:55Z", "soft_page_budget_pause", 200),
        (cycle3, None, "", "stop_auth_or_access_boundary", 403),
    ):
        _write_json(cycle / "cursor_rate_limit_state.json", {"response_status": status, "rate_limit_remaining": remaining, "cooldown_until_utc": cooldown, "latest_decision": decision})
    _write_json(cycle1 / "cursor_request_templates.json", {"next_cursor_url": "", "request_templates": []})
    _write_json(cycle2 / "cursor_request_templates.json", {"next_cursor_url": _request_url(CURSOR_2), "request_templates": [{"cursor_in": CURSOR_2}]})
    _write_json(cycle3 / "cursor_request_templates.json", {"next_cursor_url": _request_url(CURSOR_2), "request_templates": [{"cursor_in": CURSOR_2}]})
    for cycle in (cycle1, cycle2, cycle3):
        _write_json(cycle / "cursor_export_manifest.json", {"source_url": SOURCE_URL})
        (cycle / "cursor_errors.jsonl").write_text("", encoding="utf-8")
    return output_root


def test_repaired_next_cursor_url_inserts_cursor() -> None:
    repaired, reason = build_repaired_next_cursor_url(_request_url(), CURSOR_1)
    assert reason == ""
    assert "cursor" in repaired
    assert CURSOR_1 in repaired


def test_closeout_summary_counts_and_boundaries() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_fixture(Path(tmp))
        closeout, records = build_twitter_live_output_closeout(output_root=root, source_url=SOURCE_URL, profile_tab="replies")
        payload = closeout.to_dict()
        assert payload["offline_closeout_only"] is True
        assert payload["canonical_url"] == CANONICAL_URL
        assert payload["cycle_count"] == 3
        assert payload["total_unique_status_ids"] == 80
        assert payload["cycles"][0]["entries_count"] == 43
        assert payload["cycles"][0]["cursor_template_repair"]["needed"] is True
        assert payload["cycles"][0]["cursor_template_repair"]["repaired_next_cursor_url_available"] is True
        assert payload["cycles"][1]["entries_count"] == 80
        assert payload["cycles"][1]["next_cursor_url_available"] is True
        assert payload["cycles"][2]["response_status"] == 403
        assert payload["auth_or_access_boundary"]["detected"] is True
        assert payload["auth_or_access_boundary"]["safe_to_continue_live"] is False
        assert payload["auth_or_access_boundary"]["live_rerun_recommended"] is False
        assert len(records) == 80


def test_profile_media_records_preserve_blank_identity_and_media_refs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_fixture(Path(tmp))
        closeout, records = build_twitter_live_output_closeout(output_root=root, source_url=SOURCE_URL, profile_tab="replies")
        bridge = closeout.to_dict()["profile_media_bridge"]
        assert bridge["record_count"] == 80
        assert bridge["account_context_candidate"] == "examaddaorg"
        assert bridge["account_context_inferred_from_profile_url"] is True
        assert bridge["author_row_identity_missing_count"] == 80
        assert bridge["screen_name_missing_count"] == 80
        assert bridge["media_reference_count"] == 13
        assert bridge["reply_count"] == 41
        assert bridge["final_source_role_decision"] is False
        media_records = [record for record in records if record["media_urls"]]
        assert len(media_records) == 13
        first = records[0]
        assert first["author_name"] == ""
        assert first["screen_name"] == ""
        assert first["account_context_candidate"] == "examaddaorg"
        assert first["author_row_identity_missing_review"] is True
        assert first["final_source_role_decision"] is False
        assert "twitter_x_author_identity_review" in first["review_lanes"]
        assert media_records[0]["media_references"][0]["media_download_performed"] is False


def test_safety_flags_and_text_summary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_fixture(Path(tmp))
        closeout, _records = build_twitter_live_output_closeout(output_root=root, source_url=SOURCE_URL, profile_tab="replies")
        flags = closeout.to_dict()["safety_flags"]
        for key in (
            "browser_launch_performed",
            "web_download_performed",
            "media_download_performed",
            "official_x_api_used",
            "write_actions_performed",
            "credential_automation_performed",
            "captcha_bypass_performed",
            "proxy_or_evasion_performed",
            "automatic_classification_performed",
            "sensitive_identifier_inference_performed",
        ):
            assert flags[key] is False
        text = render_twitter_live_output_closeout_text(closeout)
        assert "V77C TWITTER/X LIVE OUTPUT CLOSEOUT" in text
        assert "offline_closeout_only: True" in text
        assert "cycles: 3" in text
        assert "total_unique_status_ids: 80" in text
        assert "cycle 0001 entries: 43" in text
        assert "auth_or_access_boundary_detected: True" in text
        assert "official_x_api_used: False" in text


def test_write_gate_blocks_and_allows_json_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_fixture(Path(tmp) / "input")
        closeout, records = build_twitter_live_output_closeout(output_root=root, source_url=SOURCE_URL, profile_tab="replies")
        output_json = Path(tmp) / "closeout.json"
        records_jsonl = Path(tmp) / "records.jsonl"
        blocked = write_twitter_live_output_closeout(
            closeout=closeout,
            profile_media_records=records,
            output_json=output_json,
            profile_media_records_jsonl=records_jsonl,
            confirm_write="WRONG",
        )
        assert blocked["status"] == "blocked_confirmation_required"
        assert not output_json.exists()
        assert not records_jsonl.exists()
        written = write_twitter_live_output_closeout(
            closeout=closeout,
            profile_media_records=records,
            output_json=output_json,
            profile_media_records_jsonl=records_jsonl,
            confirm_write=WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C,
        )
        assert written["status"] == "twitter_capture_live_output_closeout_written"
        assert output_json.exists()
        assert len(records_jsonl.read_text(encoding="utf-8").splitlines()) == 80


if __name__ == "__main__":
    test_repaired_next_cursor_url_inserts_cursor()
    test_closeout_summary_counts_and_boundaries()
    test_profile_media_records_preserve_blank_identity_and_media_refs()
    test_safety_flags_and_text_summary()
    test_write_gate_blocks_and_allows_json_outputs()
    print("twitter_capture_live_output_closeout_v77c OK")
