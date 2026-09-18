from __future__ import annotations

from pathlib import Path


def test_main_registers_universal_social_account_ledger_contract_r43u() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE" in source
    assert "universal_social_account_ledger_contract_r43u" in source
    assert "build_universal_social_account_ledger_contract_r43u" in source
    assert "R43T/R43A" in source
    assert "Bluesky" in source
    assert "does not start browser" in source


def run_self_test() -> None:
    test_main_registers_universal_social_account_ledger_contract_r43u()


if __name__ == "__main__":
    run_self_test()
    print("main_universal_social_account_ledger_contract_r43u_test: PASS")
