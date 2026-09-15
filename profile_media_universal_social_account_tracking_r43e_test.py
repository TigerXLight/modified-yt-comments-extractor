from __future__ import annotations

import json
import shutil
from pathlib import Path

from profile_media_universal_social_account_tracking_r43e import (
    R43E_MARKER,
    R43E_PASS_STATUS,
    UniversalSocialAccountTrackingRequestR43E,
    build_default_platform_adapter_map_r43e,
    build_report,
    build_universal_social_account_tracking_contract_r43e,
    build_universal_social_account_tracking_registry_r43e,
)


def test_contract_is_platform_neutral_not_twitter_locked() -> None:
    contract = build_universal_social_account_tracking_contract_r43e()
    assert contract["marker"] == R43E_MARKER
    assert contract["twitter_x_is_first_adapter_not_architecture"] is True
    assert contract["future_platforms_use_same_contract"] is True
    assert "bluesky" in contract["platforms"]
    assert "instagram" in contract["platforms"]
    assert "facebook" in contract["platforms"]
    assert "repost_or_reshare" in contract["universal_record_types"]
    assert "screenshot_receipt" in contract["universal_record_types"]
    assert contract["review_window_dependency"] is False
    assert contract["source_role_checks_enabled"] is False
    assert contract["webview2_internals_copied"] is False


def test_adapter_map_contains_major_platforms_and_twitter_x_first_adapter() -> None:
    adapters = build_default_platform_adapter_map_r43e()
    for platform_id in ("twitter_x", "bluesky", "instagram", "facebook", "threads", "mastodon", "tiktok", "reddit"):
        assert platform_id in adapters
        assert "account_record_md" in adapters[platform_id].capabilities
        assert "static_screenshot_receipt_gate" in adapters[platform_id].capabilities
    assert adapters["twitter_x"].implementation_module == "profile_media_twitter_x_account_tracking_export_surface_r43d"
    assert adapters["twitter_x"].planned_from_twitter_x_contract is False
    assert adapters["bluesky"].planned_from_twitter_x_contract is True
    assert adapters["instagram"].record_type_map["reel"] == "post"
    assert adapters["facebook"].record_type_map["share"] == "repost_or_reshare"


def test_registry_detects_platform_and_routes_twitter_x_to_r43d(tmp_path: Path) -> None:
    registry = build_universal_social_account_tracking_registry_r43e(output_root=tmp_path)
    assert registry.detect_platform_id("https://x.com/example") == "twitter_x"
    assert registry.detect_platform_id("https://bsky.app/profile/example.bsky.social") == "bluesky"
    assert registry.detect_platform_id("https://www.instagram.com/example/") == "instagram"
    result = registry.run_account_export(
        UniversalSocialAccountTrackingRequestR43E(
            platform_id="twitter_x",
            account_url="https://x.com/example",
            account_handle="example",
            capture_timestamp="20260915T040000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    assert result.status == R43E_PASS_STATUS
    assert result.platform_id == "twitter_x"
    assert result.downstream_status.startswith("PASS_R43D_")
    assert result.record_count >= 2
    assert result.media_count >= 1
    assert Path(result.request_path).is_file()
    assert Path(result.runbook_path).is_file()
    assert Path(result.adapter_map_path).is_file()
    assert Path(result.receipt_path).is_file()
    adapter_map = json.loads(Path(result.adapter_map_path).read_text(encoding="utf-8"))
    assert "bluesky" in adapter_map
    assert "instagram" in adapter_map
    assert "facebook" in adapter_map
    runbook = Path(result.runbook_path).read_text(encoding="utf-8")
    assert "Twitter/X is the first adapter implementation" in runbook
    assert "WebView2 or any later browser engine is only a rendering/observation input" in runbook


def test_non_twitter_platform_is_mapped_but_not_claimed_implemented(tmp_path: Path) -> None:
    registry = build_universal_social_account_tracking_registry_r43e(output_root=tmp_path)
    result = registry.run_account_export(
        UniversalSocialAccountTrackingRequestR43E(
            platform_id="bluesky",
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260915T040000Z",
            output_root=str(tmp_path),
            fixture_mode=True,
        )
    )
    assert result.status != R43E_PASS_STATUS
    assert result.adapter_status == "mapped_contract_adapter_pending"
    assert result.downstream_status == "contract_only_adapter_pending"
    assert result.warnings
    assert Path(result.adapter_map_path).is_file()


def test_report_green(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.status == R43E_PASS_STATUS, [c for c in report.checks if c.get("status") != "pass"]
    assert report.passed
    data = report.to_dict()
    assert data["adapter_map"]["twitter_x"]["planned_from_twitter_x_contract"] is False
    assert "bluesky" in data["adapter_map"]
    assert data["sample_result"]["status"] == R43E_PASS_STATUS
    assert all(c["status"] == "pass" for c in data["checks"])


def run_self_test() -> None:
    test_contract_is_platform_neutral_not_twitter_locked()
    test_adapter_map_contains_major_platforms_and_twitter_x_first_adapter()
    root = Path("profile_media_live_captures/r43e_universal_social_account_tracking_contract_adapter_map_test")
    shutil.rmtree(root, ignore_errors=True)
    test_registry_detects_platform_and_routes_twitter_x_to_r43d(root / "registry")
    test_non_twitter_platform_is_mapped_but_not_claimed_implemented(root / "contract_only")
    test_report_green(root / "report")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_universal_social_account_tracking_r43e_test: PASS")
