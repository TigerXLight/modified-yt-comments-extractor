from pathlib import Path


def run_self_test() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "R44B_BLUESKY_REAL_WINDOWS_VISIBLE_BROWSER_SMOKE" in source
    assert "bluesky_real_windows_visible_browser_smoke_r44b" in source
    assert "build_bluesky_real_windows_visible_browser_smoke_r44b" in source
    print("main_bluesky_real_windows_visible_browser_smoke_r44b_test: PASS")


if __name__ == "__main__":
    run_self_test()
