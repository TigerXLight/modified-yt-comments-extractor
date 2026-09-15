from __future__ import annotations
from pathlib import Path


def test_main_registers_twitter_x_account_timeline_runner_r43b() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY" in source
    assert "twitter_x_account_timeline_runner_r43b" in source
    assert "build_twitter_x_account_timeline_runner_r43b" in source
    assert "independent fast Media WebView2 lane" in source
    assert "does not call source-role" in source
    assert "review/source-role WebView2" in source


def run_self_test() -> None:
    test_main_registers_twitter_x_account_timeline_runner_r43b()


if __name__ == "__main__":
    run_self_test()
    print("main_twitter_x_account_timeline_runner_r43b_test: PASS")
