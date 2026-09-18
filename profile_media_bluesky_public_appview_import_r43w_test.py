from __future__ import annotations

import json
import shutil
from pathlib import Path

from profile_media_bluesky_public_appview_import_r43w import (
    BLUESKY_PUBLIC_APPVIEW_BASE_R43W,
    R43W_MARKER,
    R43W_PASS_STATUS,
    BlueskyPublicAppviewImportRequestR43W,
    build_bluesky_get_author_feed_url_r43w,
    build_bluesky_public_appview_import_contract_r43w,
    build_bluesky_public_appview_import_r43w,
    build_fake_bluesky_public_appview_feed_response_r43w,
    build_report,
    extract_post_views_from_author_feed_r43w,
    run_bluesky_public_appview_import_r43w,
)


def test_get_author_feed_url_is_public_appview_plain_url() -> None:
    url = build_bluesky_get_author_feed_url_r43w(actor="example.bsky.social", limit=12)
    assert url.startswith(BLUESKY_PUBLIC_APPVIEW_BASE_R43W + "/app.bsky.feed.getAuthorFeed?")
    assert "actor=example.bsky.social" in url
    assert "limit=12" in url
    assert "includePins=true" in url
    assert "](" not in url


def test_extract_post_views_from_author_feed_fixture() -> None:
    feed = build_fake_bluesky_public_appview_feed_response_r43w(actor="example.bsky.social", limit=5)
    post_views = extract_post_views_from_author_feed_r43w(feed, max_items=5)
    assert len(post_views) == 2
    assert post_views[0]["uri"].startswith("at://did:plc:r43vexample/")
    assert post_views[0]["author"]["handle"] == "example.bsky.social"


def test_fixture_import_uses_r43v_and_r43u_without_network(tmp_path: Path) -> None:
    result = run_bluesky_public_appview_import_r43w(
        BlueskyPublicAppviewImportRequestR43W(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            actor="example.bsky.social",
            capture_timestamp="20260918T064000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
            max_items=5,
        )
    )
    assert result.status == R43W_PASS_STATUS
    assert result.post_view_count == 2
    assert result.record_count == 2
    assert result.media_count == 3
    assert result.adapter_status.startswith("PASS_R43V_")
    assert result.ledger_status.startswith("PASS_R43U_")
    assert result.side_effect_flags["network_actions_performed"] is False
    assert result.side_effect_flags["remote_media_downloads_performed"] is False
    assert Path(result.account_record_path).is_file()
    assert Path(result.media_index_path).is_file()
    assert all(Path(path).is_file() for path in result.appview_payload_paths)
    media_index = json.loads(Path(result.media_index_path).read_text(encoding="utf-8"))
    assert all(row["platform_id"] == "bluesky" for row in media_index)
    assert all(row["metadata_only_remote_media_not_downloaded"] is True for row in media_index)


def test_public_network_mode_uses_injected_fetcher_not_real_network(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_fetcher(url: str):
        calls.append(url)
        return {
            "ok": True,
            "status": "fake_http_200",
            "status_code": 200,
            "url": url,
            "json": build_fake_bluesky_public_appview_feed_response_r43w(actor="example.bsky.social", limit=5),
        }

    adapter = build_bluesky_public_appview_import_r43w(tmp_path, fetcher=fake_fetcher)
    result = adapter.run_account_export(
        BlueskyPublicAppviewImportRequestR43W(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            actor="example.bsky.social",
            capture_timestamp="20260918T064100Z",
            output_root=str(tmp_path),
            public_network_enabled=True,
            max_items=5,
        )
    )
    assert result.status == R43W_PASS_STATUS
    assert calls and "app.bsky.feed.getAuthorFeed" in calls[0]
    assert result.request_urls == (calls[0],)
    assert result.appview_statuses == ("fake_http_200",)
    assert result.side_effect_flags["network_actions_performed"] is True
    assert result.side_effect_flags["cookie_or_token_extraction_performed"] is False
    assert result.side_effect_flags["login_automation_performed"] is False


def test_blocks_without_fixture_import_or_explicit_network(tmp_path: Path) -> None:
    result = run_bluesky_public_appview_import_r43w(
        BlueskyPublicAppviewImportRequestR43W(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T064200Z",
            output_root=str(tmp_path),
            fixture_mode=False,
            public_network_enabled=False,
        )
    )
    assert result.status != R43W_PASS_STATUS
    assert result.post_view_count == 0
    assert result.warnings
    assert Path(result.receipt_path).is_file()


def test_report_green(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.marker == R43W_MARKER
    assert report.status == R43W_PASS_STATUS, [c for c in report.checks if c["status"] != "pass"]
    assert report.passed
    data = report.to_dict()
    assert data["sample_result"]["record_count"] == 2
    assert data["sample_result"]["media_count"] == 3
    assert data["side_effect_flags"]["network_actions_performed"] is False
    assert data["contract"]["remote_media_downloads_performed_by_r43w"] is False
    assert "](" not in json.dumps(data)


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43w_bluesky_public_appview_import_test")
    shutil.rmtree(root, ignore_errors=True)
    test_get_author_feed_url_is_public_appview_plain_url()
    test_extract_post_views_from_author_feed_fixture()
    test_fixture_import_uses_r43v_and_r43u_without_network(root / "fixture")
    test_public_network_mode_uses_injected_fetcher_not_real_network(root / "fake_live")
    test_blocks_without_fixture_import_or_explicit_network(root / "blocked")
    test_report_green(root / "report")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_bluesky_public_appview_import_r43w_test: PASS")
