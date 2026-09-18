from __future__ import annotations

import ast
from pathlib import Path


def test_main_registers_r43y_bluesky_public_appview_universal_route() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "R43Y_BLUESKY_PUBLIC_APPVIEW_UNIVERSAL_ROUTE" in source
    assert "bluesky_public_appview_universal_route_r43y" in source
    assert "build_bluesky_public_appview_universal_route_r43y" in source
    ast.parse(source)


def run_self_test() -> None:
    test_main_registers_r43y_bluesky_public_appview_universal_route()


if __name__ == "__main__":
    run_self_test()
    print("main_bluesky_public_appview_universal_route_r43y_test: PASS")
