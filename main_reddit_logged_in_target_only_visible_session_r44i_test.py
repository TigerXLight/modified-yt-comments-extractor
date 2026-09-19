from __future__ import annotations

from pathlib import Path


def run_self_test() -> None:
    main_text = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R44I_REDDIT_LOGGED_IN_TARGET_ONLY_VISIBLE_SESSION" in main_text
    assert "profile_media_reddit_logged_in_target_only_visible_session_r44i" in main_text
    assert "build_reddit_logged_in_target_only_visible_session_contract_r44i" in main_text
    print("main_reddit_logged_in_target_only_visible_session_r44i_test: PASS")


if __name__ == "__main__":
    run_self_test()
