from __future__ import annotations

import ast
from pathlib import Path


def test_main_registers_r43x_bluesky_real_public_appview_smoke() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "R43X_BLUESKY_REAL_PUBLIC_APPVIEW_SMOKE" in source
    assert "bluesky_real_public_appview_smoke_r43x" in source
    assert "build_bluesky_real_public_appview_smoke_r43x" in source
    ast.parse(source)


def run_self_test() -> None:
    test_main_registers_r43x_bluesky_real_public_appview_smoke()


if __name__ == "__main__":
    run_self_test()
    print("main_bluesky_real_public_appview_smoke_r43x_test: PASS")
