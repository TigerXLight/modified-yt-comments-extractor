from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_twitter_x_account_media_ledger_r43a import (
    R43A_MARKER,
    R43A_PASS_STATUS,
    TwitterXAccountMediaItemR43A,
    TwitterXAccountRecordR43A,
    build_report,
    build_r43a_folder_policy,
    write_twitter_x_account_media_ledger_r43a,
)


def test_account_ledger_writes_date_folders_and_links() -> None:
    with tempfile.TemporaryDirectory(prefix="r43a_account_ledger_") as tmp:
        root = Path(tmp)
        img = root / "fixtures" / "image.jpg"
        vid = root / "fixtures" / "video.mp4"
        screenshot = root / "fixtures" / "static.png"
        img.parent.mkdir(parents=True, exist_ok=True)
        img.write_bytes(b"img")
        vid.write_bytes(b"vid")
        screenshot.write_bytes(b"shot")
        result = write_twitter_x_account_media_ledger_r43a(
            (
                TwitterXAccountRecordR43A(account_handle="examaddaorg", author_handle="examaddaorg", record_id="1001", record_type="post", source_url="https://x.com/examaddaorg/status/1001", visible_text="Post with local image and video.", visible_timestamp="2026-09-14T10:00:00Z", static_screenshot_path=str(screenshot), media_items=(TwitterXAccountMediaItemR43A(media_id="i1", media_class="image", media_url="https://pbs.twimg.com/media/abc.jpg?format=jpg&name=large", local_path=str(img), filename="abc.jpg"), TwitterXAccountMediaItemR43A(media_id="v1", media_class="video", media_url="https://video.twimg.com/ext_tw_video/1001/pu/vid/720x720/v.mp4", local_path=str(vid), filename="v.mp4")), review_strings=("Post with local image and video.",), observed_order=1),
                TwitterXAccountRecordR43A(account_handle="examaddaorg", author_handle="someone_else", record_id="2002", record_type="repost", original_post_id="9009", reposted_by_handle="examaddaorg", source_url="https://x.com/someone_else/status/9009", visible_text="Repost with remote manifest receipt only.", visible_timestamp="2026-09-15 08:30", static_screenshot_path=str(screenshot), media_items=(TwitterXAccountMediaItemR43A(media_id="m1", media_class="manifest", media_url="https://video.twimg.com/ext_tw_video/9009/pu/pl/manifest.m3u8?tag=16", filename="manifest.m3u8"),), review_strings=("Repost with remote manifest receipt only.",), observed_order=2),
            ),
            output_root=root / "source_exports" / "twitter_x",
            account_handle="examaddaorg",
            capture_timestamp="20260914T000000Z",
        )
        capture = Path(result.account_capture_dir)
        assert result.status == R43A_PASS_STATUS
        assert (capture / "account_record.md").is_file()
        assert (capture / "manifest.json").is_file()
        assert (capture / "media_index.json").is_file()
        assert (capture / "account_timeline.ndjson").is_file()
        assert (capture / "progress_events.ndjson").is_file()
        assert (capture / "review_strings.txt").is_file()
        assert (capture / "dates" / "2026-09-14" / "post_1001" / "post.md").is_file()
        assert (capture / "dates" / "2026-09-15" / "repost_2002__original_9009" / "post.md").is_file()
        assert (capture / "dates" / "2026-09-14" / "post_1001" / "static_screenshot.png").is_file()
        assert (capture / "dates" / "2026-09-14" / "post_1001" / "media" / "images" / "abc.jpg").is_file()
        assert (capture / "dates" / "2026-09-14" / "post_1001" / "media" / "videos" / "v.mp4").is_file()
        assert list((capture / "dates" / "2026-09-15" / "repost_2002__original_9009" / "media" / "manifests").glob("*.url.txt"))
        account_record = (capture / "account_record.md").read_text(encoding="utf-8")
        assert "dates/2026-09-14/" in account_record
        assert "dates/2026-09-15/" in account_record
        assert "post_1001/post.md" in account_record
        assert "repost_2002__original_9009/post.md" in account_record
        assert "static_screenshot" in account_record
        assert "media/images" in account_record
        assert "media/videos" in account_record
        assert "media/manifests" in account_record
        manifest = json.loads((capture / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["marker"] == R43A_MARKER
        assert manifest["record_count"] == 2
        assert manifest["media_count"] == 3
        assert manifest["date_folders"] == ["2026-09-14", "2026-09-15"]
        media_index = json.loads((capture / "media_index.json").read_text(encoding="utf-8"))
        assert all(item["remote_download_performed_by_r43a"] is False for item in media_index)
        assert any(item["local_export_path"].endswith(".url.txt") for item in media_index)
        assert result.side_effect_flags["network_actions_performed"] is False
        assert result.side_effect_flags["source_role_checks_performed"] is False


def test_folder_policy_records_user_requested_structure() -> None:
    policy = build_r43a_folder_policy()
    assert policy["single_whole_record_document"] == "account_record.md"
    assert "visible post date first" in policy["date_folder_rule"]
    assert "repost_<repost_id>__original_<original_post_id>" in policy["post_folder_rule"]
    assert "media/images" in policy["media_folder_rule"]
    assert policy["remote_downloads_performed_by_ledger"] is False


def test_report_green() -> None:
    with tempfile.TemporaryDirectory(prefix="r43a_report_") as tmp:
        report = build_report(Path(tmp))
        failed = [dict(check) for check in report.checks if check.get("status") != "pass"]
        assert report.status == R43A_PASS_STATUS, failed
        assert report.passed, failed
        payload = report.to_dict()
        assert payload["marker"] == R43A_MARKER
        assert payload["ledger_result"]["record_count"] == 2
        assert payload["ledger_result"]["media_count"] == 3


def run_self_test() -> None:
    test_account_ledger_writes_date_folders_and_links()
    test_folder_policy_records_user_requested_structure()
    test_report_green()


if __name__ == "__main__":
    run_self_test()
    print("profile_media_twitter_x_account_media_ledger_r43a_test: PASS")
