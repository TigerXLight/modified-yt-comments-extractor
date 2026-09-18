from __future__ import annotations

from pathlib import Path


def test_main_registers_r44a_visible_live_workbench_capture() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE" in source
    assert "bluesky_visible_live_workbench_capture_r44a" in source
    assert "build_bluesky_visible_live_workbench_capture_r44a" in source


def run_self_test() -> None:
    test_main_registers_r44a_visible_live_workbench_capture()
    print("main_bluesky_visible_live_workbench_capture_r44a_test: PASS")


if __name__ == "__main__":
    run_self_test()
