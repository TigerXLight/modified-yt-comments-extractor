from __future__ import annotations

import json
import shutil
from pathlib import Path

from profile_media_universal_social_account_ledger_contract_r43u import (
    R43U_MARKER,
    R43U_PASS_STATUS,
    UNIVERSAL_SOCIAL_LEDGER_FILES_R43U,
    build_fake_bluesky_fixture_records_r43u,
    build_fake_twitter_x_fixture_records_r43u,
    build_report,
    build_universal_social_account_ledger_contract_r43u,
    write_universal_social_account_ledger_r43u,
)


def test_contract_freezes_r43t_method_without_twitter_x_internals() -> None:
    contract = build_universal_social_account_ledger_contract_r43u()
    assert contract["marker"] == R43U_MARKER
    assert contract["twitter_x_output_must_remain_backwards_compatible"] is True
    assert contract["platform_adapters_must_not_copy_twitter_x_internals"] is True
    assert contract["method_is_reusable_across_twitter_like_platforms"] is True
    assert contract["folder_contract"]["account_capture"] == "source_exports/<platform_id>/<account_handle>/account_capture_<timestamp>"
    assert "platform_specific" in contract["record_fields"]
    assert "platform_specific" in contract["media_fields"]
    assert "app.bsky.embed.images" in contract["bluesky_mapping_baseline"]["embed_types"]
    assert "atproto/lexicons/app/bsky/feed/post.json" in contract["bluesky_mapping_baseline"]["repo_reference_paths"]
    assert contract["side_effect_policy"]["remote_media_download_performed_by_r43u"] is False
    assert contract["side_effect_policy"]["cookie_or_token_extraction_performed"] is False


def test_universal_writer_writes_twitter_x_baseline_shape(tmp_path: Path) -> None:
    records = build_fake_twitter_x_fixture_records_r43u(tmp_path / "fixture")
    result = write_universal_social_account_ledger_r43u(records, output_root=tmp_path / "out", platform_id="twitter_x", account_handle="example", capture_timestamp="20260918T050000Z")
    assert result.status == R43U_PASS_STATUS
    capture = Path(result.account_capture_dir)
    assert capture.parts[-4:] == ("source_exports", "twitter_x", "example", "account_capture_20260918T050000Z")
    assert (capture / "dates" / "2026-09-18" / "post_1111111111111111111" / "post.md").is_file()
    assert (capture / "dates" / "2026-09-18" / "post_1111111111111111111" / "media" / "images" / "r43u_twitter_x_fixture.jpg").is_file()
    for name in UNIVERSAL_SOCIAL_LEDGER_FILES_R43U:
        assert (capture / name).is_file(), name
    timeline = (capture / "account_timeline.ndjson").read_text(encoding="utf-8")
    assert '"platform_id": "twitter_x"' in timeline
    assert '"marker": "' + R43U_MARKER + '"' in timeline


def test_universal_writer_writes_bluesky_with_platform_specific_identity(tmp_path: Path) -> None:
    records = build_fake_bluesky_fixture_records_r43u(tmp_path / "fixture")
    result = write_universal_social_account_ledger_r43u(records, output_root=tmp_path / "out", platform_id="bluesky", account_handle="example.bsky.social", capture_timestamp="20260918T050500Z")
    assert result.status == R43U_PASS_STATUS
    capture = Path(result.account_capture_dir)
    assert capture.parts[-4:] == ("source_exports", "bluesky", "example.bsky.social", "account_capture_20260918T050500Z")
    post_json_path = capture / "dates" / "2026-09-18" / "post_3lrtestfixture" / "post.json"
    assert post_json_path.is_file()
    post = json.loads(post_json_path.read_text(encoding="utf-8"))
    assert post["platform_id"] == "bluesky"
    assert post["platform_specific"]["bluesky"]["did"].startswith("did:plc:")
    assert post["platform_specific"]["bluesky"]["at_uri"].startswith("at://")
    assert post["platform_specific"]["bluesky"]["cid"]
    media_index = json.loads(Path(result.media_index_path).read_text(encoding="utf-8"))
    assert len(media_index) == 2
    assert {row["media_class"] for row in media_index} == {"image", "external"}
    assert all(row["platform_specific"]["bluesky"]["embed_type"].startswith("app.bsky.embed.") for row in media_index)
    assert any(str(row["local_export_path"]).endswith(".url.txt") for row in media_index)
    assert result.side_effect_flags["remote_media_download_performed_by_r43u"] is False


def test_mapping_coercion_accepts_bluesky_like_dicts(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")
    result = write_universal_social_account_ledger_r43u(
        [
            {
                "platform": "bluesky",
                "account_handle": "example.bsky.social",
                "uri": "at://did:plc:example/app.bsky.feed.post/3lrcoerce",
                "record_type": "post",
                "url": "https://bsky.app/profile/example.bsky.social/post/3lrcoerce",
                "text": "coerced bluesky-like record",
                "indexed_at": "2026-09-18T06:00:00Z",
                "platform_specific": {"bluesky": {"did": "did:plc:example", "at_uri": "at://did:plc:example/app.bsky.feed.post/3lrcoerce", "cid": "bafycoerce"}},
                "media_items": [
                    {
                        "media_class": "image",
                        "media_url": "https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:example/bafkcoerce@jpeg",
                        "local_session_path": str(image),
                        "filename": "coerced.jpg",
                        "platform_specific": {"bluesky": {"embed_type": "app.bsky.embed.images", "blob_ref": "bafkcoerce"}},
                    }
                ],
            }
        ],
        output_root=tmp_path / "out",
        platform_id="bluesky",
        account_handle="example.bsky.social",
        capture_timestamp="20260918T060000Z",
    )
    capture = Path(result.account_capture_dir)
    assert (capture / "dates" / "2026-09-18" / "post_3lrcoerce" / "media" / "images" / "coerced.jpg").is_file()
    post = json.loads((capture / "dates" / "2026-09-18" / "post_3lrcoerce" / "post.json").read_text(encoding="utf-8"))
    assert post["record_id"] == "3lrcoerce"
    assert post["media_items"][0]["copied_local_bytes"] is True


def test_r43u_report_green(tmp_path: Path) -> None:
    report = build_report(tmp_path / "report")
    assert report.status == R43U_PASS_STATUS, [c for c in report.checks if c.get("status") != "pass"]
    data = report.to_dict()
    assert data["twitter_x_fixture_result"]["platform_id"] == "twitter_x"
    assert data["bluesky_fixture_result"]["platform_id"] == "bluesky"
    assert all(c["status"] == "pass" for c in data["checks"])


def test_existing_twitter_x_r43a_baseline_constants_are_not_replaced() -> None:
    from profile_media_twitter_x_account_media_ledger_r43a import R43A_DEFAULT_OUTPUT_ROOT, R43A_SCHEMA_VERSION

    assert R43A_DEFAULT_OUTPUT_ROOT == "source_exports/twitter_x"
    assert R43A_SCHEMA_VERSION == "twitter_x_account_media_ledger_date_folder_export_map.r43a.v1"


def run_self_test() -> None:
    test_contract_freezes_r43t_method_without_twitter_x_internals()
    root = Path("profile_media_live_captures/r43u_universal_social_account_ledger_contract_baseline_test")
    shutil.rmtree(root, ignore_errors=True)
    test_universal_writer_writes_twitter_x_baseline_shape(root / "twitter")
    test_universal_writer_writes_bluesky_with_platform_specific_identity(root / "bluesky")
    test_mapping_coercion_accepts_bluesky_like_dicts(root / "coercion")
    test_r43u_report_green(root / "report")
    test_existing_twitter_x_r43a_baseline_constants_are_not_replaced()


if __name__ == "__main__":
    run_self_test()
    print("profile_media_universal_social_account_ledger_contract_r43u_test: PASS")
