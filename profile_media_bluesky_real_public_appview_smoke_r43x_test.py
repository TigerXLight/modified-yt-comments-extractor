from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from profile_media_bluesky_public_appview_import_r43w import build_fake_bluesky_public_appview_feed_response_r43w
from profile_media_bluesky_real_public_appview_smoke_r43x import (
    BLUESKY_PUBLIC_APPVIEW_BASE_R43W,
    R43X_BLOCKED_STATUS,
    R43X_MARKER,
    R43X_PASS_STATUS,
    BlueskyRealPublicAppviewSmokeRequestR43X,
    build_bluesky_real_public_appview_smoke_contract_r43x,
    build_report,
    run_bluesky_real_public_appview_smoke_r43x,
)


class CountingFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str) -> Mapping[str, Any]:
        self.urls.append(url)
        return {
            "ok": True,
            "status": "injected_test_fetcher_ok",
            "status_code": 200,
            "url": url,
            "json": build_fake_bluesky_public_appview_feed_response_r43w(actor="bsky.app", limit=3),
        }


def test_r43x_blocks_without_explicit_public_network_flag(tmp_path: Path) -> None:
    fetcher = CountingFetcher()
    result = run_bluesky_real_public_appview_smoke_r43x(
        BlueskyRealPublicAppviewSmokeRequestR43X(
            actor="bsky.app",
            account_handle="bsky.app",
            account_url="https://bsky.app/profile/bsky.app",
            output_root=str(tmp_path),
            capture_timestamp="20260918T071500Z",
            max_items=2,
        ),
        fetcher=fetcher,
    )
    assert result.status == R43X_BLOCKED_STATUS
    assert result.public_network_requested is False
    assert result.network_actions_performed is False
    assert result.request_urls == ()
    assert fetcher.urls == []
    assert Path(result.receipt_path).is_file()


def test_r43x_injected_fetcher_exercises_public_appview_lane(tmp_path: Path) -> None:
    fetcher = CountingFetcher()
    result = run_bluesky_real_public_appview_smoke_r43x(
        BlueskyRealPublicAppviewSmokeRequestR43X(
            actor="bsky.app",
            account_handle="bsky.app",
            account_url="https://bsky.app/profile/bsky.app",
            output_root=str(tmp_path),
            capture_timestamp="20260918T071600Z",
            public_network_enabled=True,
            explicit_live_mode=True,
            max_items=2,
            timeout_seconds=5.0,
            injected_fetcher_label="unit_test_no_external_network",
        ),
        fetcher=fetcher,
    )
    assert result.status == R43X_PASS_STATUS
    assert result.marker == R43X_MARKER
    assert result.public_network_requested is True
    assert result.network_actions_performed is True
    assert result.injected_fetcher_used is True
    assert fetcher.urls and fetcher.urls[0].startswith(BLUESKY_PUBLIC_APPVIEW_BASE_R43W + "/app.bsky.feed.getAuthorFeed?")
    assert result.r43w_status.startswith("PASS_R43W_")
    assert result.adapter_status.startswith("PASS_R43V_")
    assert result.ledger_status.startswith("PASS_R43U_")
    assert result.post_view_count >= 1
    assert result.record_count >= 1
    assert result.post_folder_count >= 1
    assert all(Path(path).is_file() for path in result.appview_payload_paths)
    assert not result.side_effect_flags["browser_session_started"]
    assert not result.side_effect_flags["cookie_or_token_extraction_performed"]
    assert not result.side_effect_flags["remote_media_downloads_performed"]


def test_r43x_contract_and_report_are_plain_and_green(tmp_path: Path) -> None:
    contract = build_bluesky_real_public_appview_smoke_contract_r43x()
    assert contract["explicit_public_network_gate_required"] is True
    assert contract["public_endpoint_base"] == BLUESKY_PUBLIC_APPVIEW_BASE_R43W
    assert "](" not in json.dumps(contract)
    report = build_report(tmp_path / "report")
    assert report.status == R43X_PASS_STATUS
    assert report.sample_result["status"] == R43X_PASS_STATUS
    assert report.blocked_gate_result["status"] == R43X_BLOCKED_STATUS
    assert Path(tmp_path / "report" / "R43X_BLUESKY_REAL_PUBLIC_APPVIEW_SMOKE_REPORT.json").is_file()


def run_self_test() -> None:
    tmp = Path("profile_media_live_captures/r43x_bluesky_real_public_appview_smoke/selftest")
    if tmp.exists():
        import shutil

        shutil.rmtree(tmp)
    test_r43x_blocks_without_explicit_public_network_flag(tmp / "blocked")
    test_r43x_injected_fetcher_exercises_public_appview_lane(tmp / "injected")
    test_r43x_contract_and_report_are_plain_and_green(tmp / "report")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_bluesky_real_public_appview_smoke_r43x_test: PASS")
