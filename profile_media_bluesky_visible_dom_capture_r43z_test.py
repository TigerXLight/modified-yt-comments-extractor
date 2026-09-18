from __future__ import annotations

import json
from pathlib import Path

from profile_media_bluesky_visible_dom_capture_r43z import (
    R43Z_PASS_STATUS,
    BlueskyVisibleDomCaptureRequestR43Z,
    build_bluesky_visible_dom_capture_contract_r43z,
    build_bluesky_visible_dom_capture_r43z,
    build_fake_bluesky_visible_dom_html_r43z,
    build_report,
    extract_visible_dom_records_r43z,
)


def test_extract_visible_dom_records_binds_media_by_article_proximity(tmp_path: Path) -> None:
    html = build_fake_bluesky_visible_dom_html_r43z("example.bsky.social")
    records, bound, unbound = extract_visible_dom_records_r43z(
        html,
        account_handle="example.bsky.social",
        account_url="https://bsky.app/profile/example.bsky.social",
        capture_timestamp="20260918T080000Z",
        html_receipt_path=str(tmp_path / "visible_dom.html"),
        screenshot_path=str(tmp_path / "screen.png"),
        max_items=5,
    )
    assert len(records) == 2
    assert {row["record_id"] for row in records} == {"3lxyzdomimagepost", "3lxyzdomvideopost"}
    assert len(bound) >= 3
    assert any(item["media_class"] == "manifest" for item in bound)
    assert len(unbound) >= 1
    assert all(item["binding_status"] == "bound_to_post" for item in bound)


def test_visible_dom_capture_writes_ledger_and_screenshot_receipts(tmp_path: Path) -> None:
    result = build_bluesky_visible_dom_capture_r43z(tmp_path / "out").run_account_export(
        BlueskyVisibleDomCaptureRequestR43Z(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T080000Z",
            output_root=str(tmp_path / "out"),
            fixture_mode=True,
            explicit_live_mode=True,
            run_visible_live=True,
            max_items=5,
        )
    )
    assert result.status == R43Z_PASS_STATUS, result.warnings
    assert result.visible_record_count == 2
    assert result.record_count == 2
    assert result.bound_media_count >= 3
    assert result.unbound_media_count >= 1
    assert result.media_count >= 3
    assert result.screenshot_count >= 2
    assert Path(result.visible_dom_html_path).is_file()
    assert Path(result.copied_screenshot_path).is_file()
    assert Path(result.account_record_path).is_file()
    media_index = json.loads(Path(result.media_index_path).read_text(encoding="utf-8"))
    assert any(row.get("media_class") == "manifest" for row in media_index)
    assert all(row.get("metadata_only_remote_media_not_downloaded") is True for row in media_index)
    assert all(row.get("remote_download_performed_by_r43u") is False for row in media_index)
    flags = result.side_effect_flags
    assert flags["browser_session_started"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert flags["browser_profile_files_read_or_copied"] is False


def test_contract_records_visible_browser_boundaries() -> None:
    contract = build_bluesky_visible_dom_capture_contract_r43z()
    assert contract["browser_session_started_by_r43z"] is False
    assert contract["network_requests_performed_by_r43z"] is False
    assert contract["remote_media_downloads_performed_by_r43z"] is False
    assert "social-app/src/view/com/posts/PostFeedItem.tsx" in contract["repo_reference_paths"]


def test_report_passes(tmp_path: Path) -> None:
    report = build_report(tmp_path / "report")
    assert report.status == R43Z_PASS_STATUS
    assert all(check["status"] == "pass" for check in report.checks), report.to_dict()["checks"]


def run_self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        test_extract_visible_dom_records_binds_media_by_article_proximity(root / "extract")
        test_visible_dom_capture_writes_ledger_and_screenshot_receipts(root / "capture")
        test_contract_records_visible_browser_boundaries()
        test_report_passes(root / "report")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_bluesky_visible_dom_capture_r43z_test: PASS")
