from pathlib import Path


def test_main_registers_universal_social_batch_account_intake_r43g() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION" in source
    assert "universal_social_batch_account_intake_router_r43g" in source
    assert "build_universal_social_batch_account_intake_router_r43g" in source
    assert "universal_social_export_surface_router_r43f" in source
    assert "Twitter/X is the first adapter" in source or "first adapter" in source
    assert "source-role" in source or "source_role" in source


def run_self_test() -> None:
    test_main_registers_universal_social_batch_account_intake_r43g()
    print("main_universal_social_batch_account_intake_platform_url_detection_r43g_test: PASS")


if __name__ == "__main__":
    run_self_test()