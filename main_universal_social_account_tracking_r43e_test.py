from __future__ import annotations

from pathlib import Path


def test_main_registers_universal_social_account_tracking_registry() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP" in source
    assert "universal_social_account_tracking_registry_r43e" in source
    assert "build_universal_social_account_tracking_registry_r43e" in source
    assert "twitter_x_account_tracking_export_surface_r43d" in source
    assert "platform adapter map" in source.lower()
    assert "not Twitter/X-specific architecture" in source


def run_self_test() -> None:
    test_main_registers_universal_social_account_tracking_registry()


if __name__ == "__main__":
    run_self_test()
    print("main_universal_social_account_tracking_r43e_test: PASS")
