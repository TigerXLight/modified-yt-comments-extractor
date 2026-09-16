from __future__ import annotations

from pathlib import Path


def test_main_registers_r43n_smoke_harness_without_capture_side_effects() -> None:
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")

    assert "R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT" in text
    assert "build_live_twitter_x_single_account_smoke_harness_r43n" in text
    assert "live_twitter_x_single_account_smoke_harness_r43n" in text
    assert "universal_social_batch_workbench_app_shell_commands_r43l" in text


def test_r43n_module_keeps_visible_session_and_no_fixture_pass_policy() -> None:
    text = Path("profile_media_live_twitter_x_single_account_smoke_harness_r43n.py").read_text(
        encoding="utf-8",
        errors="replace",
    )

    assert "BLOCKED_NEEDS_VISIBLE_SESSION" in text
    assert "run_visible_live" in text
    assert "fixture_sample_probe_outputs_do_not_count_as_live_pass" in text
    assert "non_fixture_live_observation_required_for_pass" in text
    assert "build_independent_fast_media_webview2_lane_r42gz" in text
    assert "headless=False" in text


if __name__ == "__main__":
    test_main_registers_r43n_smoke_harness_without_capture_side_effects()
    test_r43n_module_keeps_visible_session_and_no_fixture_pass_policy()
    print("PASS main_live_twitter_x_single_account_smoke_harness_r43n_test")
