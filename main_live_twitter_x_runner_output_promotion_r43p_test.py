from __future__ import annotations

from pathlib import Path


def test_main_registers_r43p_runner_output_promotion() -> None:
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")

    assert "R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION" in text
    assert "promote_twitter_x_runner_outputs_r43p" in text
    assert "live_twitter_x_runner_output_promotion_r43p" in text
    assert "R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING" in text
    assert "R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT" in text


def test_r43p_module_documents_promotion_and_no_side_effects() -> None:
    text = Path("profile_media_live_twitter_x_runner_output_promotion_r43p.py").read_text(
        encoding="utf-8",
        errors="replace",
    )

    assert "screenshot.png" in text
    assert "rendered_dom_snapshot.html" in text
    assert "visible_browser_media_observations" in text
    assert "media_index.json" in text
    assert "network_events_recorded_but_not_pass_alone" in text
    assert "no_browser_started_during_automated_tests" in text
    assert "no_network_access_during_automated_tests" in text
    assert "no_remote_media_downloads_during_automated_tests" in text


if __name__ == "__main__":
    test_main_registers_r43p_runner_output_promotion()
    test_r43p_module_documents_promotion_and_no_side_effects()
    print("PASS main_live_twitter_x_runner_output_promotion_r43p_test")
