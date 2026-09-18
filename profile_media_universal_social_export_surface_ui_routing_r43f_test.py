from __future__ import annotations

import json
from pathlib import Path

from profile_media_universal_social_export_surface_ui_routing_r43f import (
    R43F_MARKER,
    R43F_PASS_STATUS,
    UNIVERSAL_EXPORT_FILES_R43F,
    UniversalSocialExportSurfaceRequestR43F,
    build_report,
    build_universal_social_export_surface_router_r43f,
)


def test_twitter_routes_through_r43e_to_r43d_surface(tmp_path: Path) -> None:
    router = build_universal_social_export_surface_router_r43f(output_root=tmp_path)
    result = router.route_account_tracking_export(
        UniversalSocialExportSurfaceRequestR43F(
            platform_id="twitter_x",
            account_url="https://twitter.com/example?s=20&utm_source=test",
            account_handle="example",
            capture_timestamp="20260915T050000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    assert result.status == R43F_PASS_STATUS
    assert result.route_status == "dispatched_to_r43d_surface_via_r43e_adapter_map"
    assert result.downstream_status.startswith("PASS_R43D_")
    assert result.universal_record_contract_preserved is True
    assert result.account_url == "https://x.com/example"
    for name in UNIVERSAL_EXPORT_FILES_R43F:
        assert (Path(result.run_dir) / name).exists(), name
    adapter_map = json.loads(Path(result.adapter_map_path).read_text(encoding="utf-8"))
    assert adapter_map["twitter_x"]["implementation_module"] == "profile_media_twitter_x_account_tracking_export_surface_r43d"


def test_bluesky_routes_through_r43e_to_r43v_adapter(tmp_path: Path) -> None:
    router = build_universal_social_export_surface_router_r43f(output_root=tmp_path)
    result = router.route_account_tracking_export(
        UniversalSocialExportSurfaceRequestR43F(
            platform_id="bluesky",
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260915T050010Z",
            output_root=str(tmp_path),
            fixture_mode=True,
            max_items=5,
        )
    )
    assert result.status == R43F_PASS_STATUS
    assert result.route_status == "dispatched_to_r43v_adapter_via_r43e_adapter_map"
    assert result.downstream_status.startswith("PASS_R43V_")
    assert result.universal_record_contract_preserved is True
    assert result.downstream_result["record_count"] == 2
    assert result.downstream_result["media_count"] == 3


def test_pending_platforms_return_mapped_receipts_not_crashes(tmp_path: Path) -> None:
    router = build_universal_social_export_surface_router_r43f(output_root=tmp_path)
    for platform in ("instagram", "facebook", "threads", "mastodon", "tiktok", "reddit", "youtube", "news_comments"):
        result = router.route_account_tracking_export(
            UniversalSocialExportSurfaceRequestR43F(
                platform_id=platform,
                account_handle="example",
                capture_timestamp=f"20260915T0501{len(platform):02d}Z",
                output_root=str(tmp_path),
            )
        )
        assert result.status == R43F_PASS_STATUS
        assert result.route_status == "mapped_pending_adapter_receipt"
        assert result.downstream_status == "contract_only_adapter_pending"
        assert result.universal_record_contract_preserved is True
        receipt = json.loads(Path(result.surface_receipt_path).read_text(encoding="utf-8"))
        assert receipt["adapter_status"] == "mapped_contract_adapter_pending"
        assert receipt["no_remote_media_downloads"] is True


def test_unknown_platform_returns_unsupported_receipt(tmp_path: Path) -> None:
    router = build_universal_social_export_surface_router_r43f(output_root=tmp_path)
    result = router.route_account_tracking_export(
        UniversalSocialExportSurfaceRequestR43F(
            platform_id="unknown_social",
            account_url="https://example.invalid/profile",
            account_handle="example",
            capture_timestamp="20260915T050200Z",
            output_root=str(tmp_path),
        )
    )
    assert result.status == R43F_PASS_STATUS
    assert result.route_status == "unsupported_platform_receipt"
    assert result.downstream_status == "unsupported_platform"
    assert result.universal_record_contract_preserved is True


def test_browser_source_role_review_window_and_download_boundaries(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    data = report.to_dict()
    assert data["status"] == R43F_PASS_STATUS, [c for c in data["checks"] if c["status"] != "pass"]
    flags = data["side_effect_flags"]
    assert flags["browser_engine_observation_only"] is True
    assert flags["webview2_internals_copied"] is False
    assert flags["webview2_session_started_by_r43f"] is False
    assert flags["hidden_x_api_scraping_performed"] is False
    assert flags["cookie_or_token_extraction_performed"] is False
    assert flags["captcha_or_challenge_bypass_performed"] is False
    assert flags["source_role_checks_performed"] is False
    assert flags["review_window_dependency_invoked"] is False
    assert flags["remote_media_downloads_performed"] is False
    assert "](" not in json.dumps(data)


def test_cli_report_files_are_written(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.marker == R43F_MARKER
    assert report.status == R43F_PASS_STATUS
    assert (tmp_path / "R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING_REPORT.json").is_file()
    assert (tmp_path / "R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING_REPORT.md").is_file()
    names = {check["name"] for check in report.checks}
    assert "universal_social_export_surface_router_invoked" in names
    assert "routes_through_r43e_adapter_map_first" in names
    assert "twitter_x_dispatches_to_r43d_surface" in names
    assert "bluesky_dispatches_to_r43v_adapter" in names
    assert "pending_platforms_return_mapped_receipts_not_crashes" in names
    assert "unknown_platform_returns_unsupported_receipt" in names


def run_self_test() -> None:
    root = Path("profile_media_live_captures/r43f_universal_social_export_surface_ui_routing_test")
    root.mkdir(parents=True, exist_ok=True)
    test_twitter_routes_through_r43e_to_r43d_surface(root / "twitter")
    test_bluesky_routes_through_r43e_to_r43v_adapter(root / "bluesky")
    test_pending_platforms_return_mapped_receipts_not_crashes(root / "pending")
    test_unknown_platform_returns_unsupported_receipt(root / "unknown")
    test_browser_source_role_review_window_and_download_boundaries(root / "boundaries")
    test_cli_report_files_are_written(root / "report")
    print("profile_media_universal_social_export_surface_ui_routing_r43f_test: PASS")


if __name__ == "__main__":
    run_self_test()
