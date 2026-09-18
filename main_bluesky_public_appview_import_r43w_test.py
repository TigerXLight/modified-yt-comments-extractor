from __future__ import annotations

import ast
from pathlib import Path


def test_main_registers_r43w_bluesky_public_appview_import() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT" in source
    assert "bluesky_public_appview_import_r43w" in source
    assert "build_bluesky_public_appview_import_r43w" in source
    ast.parse(source)


def run_self_test() -> None:
    test_main_registers_r43w_bluesky_public_appview_import()


if __name__ == "__main__":
    run_self_test()
    print("main_bluesky_public_appview_import_r43w_test: PASS")
