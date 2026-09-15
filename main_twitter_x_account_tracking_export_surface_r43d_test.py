from __future__ import annotations
from pathlib import Path


def test_main_registers_twitter_x_account_tracking_export_surface_r43d() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43D_TWITTER_X_ACCOUNT_TRACKING_EXPORT_SURFACE" in source
    assert "twitter_x_account_tracking_export_surface_r43d" in source
    assert "build_twitter_x_account_tracking_export_surface_r43d" in source
    assert "tracking/dedupe/ledger/export local" in source
    assert "does not call source-role" in source
    assert "does not use the review/source-role WebView2 lane" in source


def run_self_test() -> None:
    test_main_registers_twitter_x_account_tracking_export_surface_r43d()


if __name__ == "__main__":
    run_self_test()
    print("main_twitter_x_account_tracking_export_surface_r43d_test: PASS")
