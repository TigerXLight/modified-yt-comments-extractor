from __future__ import annotations

import json
import shutil
from pathlib import Path

from profile_media_bluesky_visible_account_adapter_r43v import (
    R43V_MARKER,
    R43V_PASS_STATUS,
    BlueskyVisibleAccountAdapterRequestR43V,
    build_bluesky_visible_account_adapter_r43v,
    build_fake_bluesky_post_views_r43v,
    build_report,
    build_bluesky_post_url_r43v,
    normalize_bluesky_post_view_to_universal_record_r43v,
    parse_bluesky_app_url_r43v,
    parse_bluesky_at_uri_r43v,
)


def test_bluesky_url_and_at_uri_parsing() -> None:
    parsed = parse_bluesky_app_url_r43v("https://bsky.app/profile/example.bsky.social/post/3lxyzimagepost?utm_source=x")
    assert parsed["handle"] == "example.bsky.social"
    assert parsed["rkey"] == "3lxyzimagepost"
    assert parsed["url_kind"] == "post"
    at = parse_bluesky_at_uri_r43v("at://did:plc:r43vexample/app.bsky.feed.post/3lxyzimagepost")
    assert at == {"did": "did:plc:r43vexample", "collection": "app.bsky.feed.post", "rkey": "3lxyzimagepost"}
    assert build_bluesky_post_url_r43v("example.bsky.social", "3lxyzimagepost") == "https://bsky.app/profile/example.bsky.social/post/3lxyzimagepost"


def test_normalizer_maps_post_view_to_universal_record() -> None:
    record = normalize_bluesky_post_view_to_universal_record_r43v(
        build_fake_bluesky_post_views_r43v("example.bsky.social")[0],
        account_handle="example.bsky.social",
        capture_timestamp="20260918T061000Z",
        observed_order=1,
    )
    data = record.to_dict()
    assert data["platform_id"] == "bluesky"
    assert data["record_id"] == "3lxyzimagepost"
    assert data["source_url"] == "https://bsky.app/profile/example.bsky.social/post/3lxyzimagepost"
    assert "did" not in data
    assert data["platform_specific"]["bluesky"]["did"] == "did:plc:r43vexample"
    assert data["platform_specific"]["bluesky"]["at_uri"].startswith("at://did:plc:r43vexample/")
    assert len(data["media_items"]) == 1
    assert data["media_items"][0]["media_class"] == "image"
    assert data["media_items"][0]["platform_specific"]["bluesky"]["alt"] == "fixture image alt text"


def test_adapter_writes_r43u_ledger_for_bluesky_fixture(tmp_path: Path) -> None:
    adapter = build_bluesky_visible_account_adapter_r43v(tmp_path)
    result = adapter.run_account_export(
        BlueskyVisibleAccountAdapterRequestR43V(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T061000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
            max_items=5,
        )
    )
    assert result.status == R43V_PASS_STATUS
    assert result.record_count == 2
    assert result.media_count == 3
    assert result.post_folder_count == 2
    assert Path(result.account_record_path).is_file()
    assert Path(result.account_timeline_path).is_file()
    media_index = json.loads(Path(result.media_index_path).read_text(encoding="utf-8"))
    assert {row["media_class"] for row in media_index} == {"image", "manifest"}
    assert any(row.get("playlist_manifest_url", "").endswith("playlist.m3u8") for row in media_index)
    assert all(row["platform_id"] == "bluesky" for row in media_index)
    assert all(row["metadata_only_remote_media_not_downloaded"] is True for row in media_index)
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert manifest["platform_id"] == "bluesky"
    assert manifest["record_count"] == 2


def test_adapter_blocks_without_source_records_or_fixture(tmp_path: Path) -> None:
    adapter = build_bluesky_visible_account_adapter_r43v(tmp_path)
    result = adapter.run_account_export(
        BlueskyVisibleAccountAdapterRequestR43V(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T061500Z",
            output_root=str(tmp_path),
            fixture_mode=False,
        )
    )
    assert result.status != R43V_PASS_STATUS
    assert result.ledger_status == "not_written_no_source_records"
    assert result.warnings
    assert Path(result.receipt_path).is_file()


def test_report_green(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.marker == R43V_MARKER
    assert report.status == R43V_PASS_STATUS, [c for c in report.checks if c["status"] != "pass"]
    assert report.passed
    data = report.to_dict()
    assert data["contract"]["twitter_x_internals_reused"] is False
    assert data["contract"]["live_browser_capture_added"] is False
    assert data["side_effect_flags"]["network_actions_performed"] is False
    assert data["sample_result"]["record_count"] == 2
    assert data["sample_result"]["media_count"] == 3
    assert "](" not in json.dumps(data)


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43v_bluesky_visible_account_adapter_test")
    shutil.rmtree(root, ignore_errors=True)
    test_bluesky_url_and_at_uri_parsing()
    test_normalizer_maps_post_view_to_universal_record()
    test_adapter_writes_r43u_ledger_for_bluesky_fixture(root / "ledger")
    test_adapter_blocks_without_source_records_or_fixture(root / "blocked")
    test_report_green(root / "report")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_bluesky_visible_account_adapter_r43v_test: PASS")
