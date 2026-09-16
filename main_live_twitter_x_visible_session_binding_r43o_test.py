from __future__ import annotations

from pathlib import Path


def test_main_registers_r43o_visible_session_binding() -> None:
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")

    assert "R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING" in text
    assert "build_live_twitter_x_visible_session_binding_r43o" in text
    assert "live_twitter_x_visible_session_binding_r43o" in text
    assert "visible_session_binding=getattr" in text
    assert "live_twitter_x_single_account_smoke_harness_r43n" in text


def test_r43o_module_documents_existing_launcher_boundary_and_safety() -> None:
    text = Path("profile_media_live_twitter_x_visible_session_binding_r43o.py").read_text(
        encoding="utf-8",
        errors="replace",
    )

    assert "twitter_browser_capture_runner.run_twitter_browser_capture" in text
    assert "build_independent_fast_media_webview2_lane_r42gz" in text
    assert "headless=False" in text
    assert "no_hidden_api_cookie_token_or_challenge_bypass" in text
    assert "no_browser_started_during_automated_tests" in text
    assert "no_network_access_during_automated_tests" in text
    assert "no_remote_media_downloads_during_automated_tests" in text


if __name__ == "__main__":
    test_main_registers_r43o_visible_session_binding()
    test_r43o_module_documents_existing_launcher_boundary_and_safety()
    print("PASS main_live_twitter_x_visible_session_binding_r43o_test")
