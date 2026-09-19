from pathlib import Path


def run_self_test() -> None:
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R44G_REDDIT_NO_LOGIN_FULL_THREAD_RELIABILITY" in text
    assert "build_reddit_no_login_full_thread_reliability_r44g" in text
    assert "reddit_no_login_full_thread_reliability_r44g" in text
    print("main_reddit_no_login_full_thread_reliability_r44g_test: PASS")


if __name__ == "__main__":
    run_self_test()
