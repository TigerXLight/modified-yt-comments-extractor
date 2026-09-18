from __future__ import annotations

import ast
from pathlib import Path


def test_main_registers_r43z_bluesky_visible_dom_capture_lane() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "R43Z_BLUESKY_VISIBLE_DOM_CAPTURE_LANE" in source
    assert "bluesky_visible_dom_capture_r43z" in source
    assert "build_bluesky_visible_dom_capture_r43z" in source
    ast.parse(source)


def run_self_test() -> None:
    test_main_registers_r43z_bluesky_visible_dom_capture_lane()


if __name__ == "__main__":
    run_self_test()
    print("main_bluesky_visible_dom_capture_r43z_test: PASS")
