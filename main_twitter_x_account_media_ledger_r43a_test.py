from __future__ import annotations
from pathlib import Path

def test_main_registers_twitter_x_account_media_ledger_exporter() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43A_TWITTER_X_ACCOUNT_MEDIA_LEDGER_DATE_FOLDER_EXPORT_MAP" in source
    assert "twitter_x_account_media_ledger_exporter" in source
    assert "build_twitter_x_account_media_ledger_exporter_r43a" in source
    assert "does not run WebView2" in source
    assert "does not call the source-role" in source

def run_self_test() -> None:
    test_main_registers_twitter_x_account_media_ledger_exporter()

if __name__ == "__main__":
    run_self_test()
    print("main_twitter_x_account_media_ledger_r43a_test: PASS")
