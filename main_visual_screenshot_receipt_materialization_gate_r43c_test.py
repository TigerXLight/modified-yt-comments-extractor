from __future__ import annotations
from pathlib import Path


def test_main_registers_visual_screenshot_receipt_gate_r43c() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE" in source
    assert "visual_screenshot_receipt_materialization_gate_r43c" in source
    assert "Edge R18 screenshot-safe baseline" in source
    assert "does not call source-role" in source
    assert "does not use the review-window WebView2 lane" in source


def run_self_test() -> None:
    test_main_registers_visual_screenshot_receipt_gate_r43c()


if __name__ == "__main__":
    run_self_test()
    print("main_visual_screenshot_receipt_materialization_gate_r43c_test: PASS")
