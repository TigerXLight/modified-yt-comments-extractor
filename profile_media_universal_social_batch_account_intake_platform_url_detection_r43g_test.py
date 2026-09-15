from __future__ import annotations

import json
from pathlib import Path

from profile_media_universal_social_batch_account_intake_platform_url_detection_r43g import (
    BATCH_INTAKE_OUTPUT_FILES_R43G,
    R43G_MARKER,
    R43G_PASS_STATUS,
    UniversalSocialBatchAccountIntakeRequestR43G,
    build_report,
    build_universal_social_batch_account_intake_router_r43g,
    detect_social_url_r43g,
    extract_urls_from_text_r43g,
)


def test_url_extraction_and_platform_detection() -> None:
    urls = extract_urls_from_text_r43g("[x](https://twitter.com/example/status/1?s=20) https://www.instagram.com/example/ bsky.app/profile/example.bsky.social")
    assert urls == (
        "https://twitter.com/example/status/1?s=20",
        "https://www.instagram.com/example/",
        "bsky.app/profile/example.bsky.social",
    )
    assert detect_social_url_r43g("https://twitter.com/example/status/1?s=20")[:4] == ("twitter_x", "post", "example", "1")
    assert detect_social_url_r43g("https://bsky.app/profile/example.bsky.social")[:3] == ("bluesky", "account", "example.bsky.social")
    assert detect_social_url_r43g("https://www.reddit.com/r/example/comments/abc123/title/")[:2] == ("reddit", "comment_thread")
    assert detect_social_url_r43g("https://news.example.test/story/comments#comments")[:2] == ("news_comments", "comment_thread")


def test_one_many_txt_and_mixed_platform_route_through_r43f(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    txt = tmp_path / "batch_urls.txt"
    txt.write_text("https://www.facebook.com/example/posts/12345\nhttps://www.tiktok.com/@example/video/7350000000000000000\n", encoding="utf-8")
    router = build_universal_social_batch_account_intake_router_r43g(output_root=tmp_path)
    result = router.route_batch(
        UniversalSocialBatchAccountIntakeRequestR43G(
            inputs=(
                "https://x.com/example",
                "https://x.com/example/status/1111111111111111111?s=20",
                "https://bsky.app/profile/example.bsky.social",
                "https://www.instagram.com/p/C-example/?igsh=test",
                "https://unknown.invalid/profile/example",
            ),
            txt_path=str(txt),
            capture_timestamp="20260915T070000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    assert result.status == R43G_PASS_STATUS
    assert result.total_inputs == 7
    assert result.route_result_count == 7
    assert result.platform_counts["twitter_x"] == 2
    assert result.platform_counts["bluesky"] == 1
    assert result.unsupported_count == 1
    assert result.account_url_count >= 2
    assert result.post_url_count >= 4
    for name in BATCH_INTAKE_OUTPUT_FILES_R43G:
        assert (Path(result.run_dir) / name).exists(), name
    routes = [json.loads(line) for line in Path(result.route_receipts_path).read_text(encoding="utf-8").splitlines()]
    assert all(route["marker"] == "YTCE_R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING" for route in routes)
    assert any(route["route_status"] == "dispatched_to_r43d_surface_via_r43e_adapter_map" for route in routes)
    assert any(route["route_status"] == "mapped_pending_adapter_receipt" for route in routes)
    assert any(route["route_status"] == "unsupported_platform_receipt" for route in routes)


def test_report_checks_and_boundaries(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    data = report.to_dict()
    assert data["marker"] == R43G_MARKER
    assert data["status"] == R43G_PASS_STATUS, [c for c in data["checks"] if c["status"] != "pass"]
    names = {check["name"] for check in data["checks"]}
    required = {
        "universal_social_batch_account_intake_router_invoked",
        "one_url_many_urls_and_txt_inputs_supported",
        "mixed_platform_urls_detected",
        "account_and_post_urls_classified",
        "routes_through_r43f_universal_surface",
        "routes_through_r43e_adapter_map_first",
        "twitter_x_account_url_dispatches_to_implemented_path",
        "pending_platforms_return_mapped_receipts",
        "unknown_urls_return_unsupported_receipts",
        "universal_contract_preserved",
        "no_browser_or_source_role_side_effects",
        "no_hidden_api_cookie_token_or_challenge_bypass",
        "no_remote_media_downloads",
        "plain_machine_urls",
    }
    assert required <= names
    flags = data["side_effect_flags"]
    assert flags["webview2_session_started_by_r43g"] is False
    assert flags["cefsharp_session_started_by_r43g"] is False
    assert flags["hidden_api_scraping_performed"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["captcha_or_challenge_bypass_performed"] is False
    assert flags["source_role_checks_performed"] is False
    assert flags["review_window_dependency_invoked"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert "](" not in json.dumps(data)


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43g_universal_social_batch_account_intake_platform_url_detection_test")
    root.mkdir(parents=True, exist_ok=True)
    test_url_extraction_and_platform_detection()
    test_one_many_txt_and_mixed_platform_route_through_r43f(root / "batch")
    test_report_checks_and_boundaries(root / "report")
    print("profile_media_universal_social_batch_account_intake_platform_url_detection_r43g_test: PASS")


if __name__ == "__main__":
    run_self_test()