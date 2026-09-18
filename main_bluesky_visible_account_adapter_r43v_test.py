from __future__ import annotations

import ast
from pathlib import Path


def test_main_registers_r43v_bluesky_adapter() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "R43V_BLUESKY_VISIBLE_ACCOUNT_ADAPTER" in source
    assert "bluesky_visible_account_adapter_r43v" in source
    assert "build_bluesky_visible_account_adapter_r43v" in source
    ast.parse(source)


def run_self_test() -> None:
    test_main_registers_r43v_bluesky_adapter()


if __name__ == "__main__":
    run_self_test()
    print("main_bluesky_visible_account_adapter_r43v_test: PASS")
