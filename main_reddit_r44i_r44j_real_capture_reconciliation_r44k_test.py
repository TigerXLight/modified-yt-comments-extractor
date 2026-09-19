from __future__ import annotations

from pathlib import Path

from profile_media_reddit_r44i_r44j_real_capture_reconciliation_r44k import (
    MARKER,
    build_reddit_r44i_r44j_real_capture_reconciliation_contract_r44k,
)


def run_self_test() -> None:
    contract = build_reddit_r44i_r44j_real_capture_reconciliation_contract_r44k()
    assert contract["marker"] == MARKER
    assert contract["mode_id"] == "reddit_r44i_r44j_real_capture_reconciliation"
    assert contract["network_actions_enabled"] is False
    assert contract["cookie_or_token_extraction_enabled"] is False
    assert contract["login_automation_enabled"] is False

    main_text = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R44K_REDDIT_R44I_R44J_REAL_CAPTURE_RECONCILIATION" in main_text
    assert "profile_media_reddit_r44i_r44j_real_capture_reconciliation_r44k" in main_text
    assert "build_reddit_r44i_r44j_real_capture_reconciliation_contract_r44k" in main_text
    print("main_reddit_r44i_r44j_real_capture_reconciliation_r44k_test: PASS")


if __name__ == "__main__":
    run_self_test()
