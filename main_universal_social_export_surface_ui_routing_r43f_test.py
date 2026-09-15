from pathlib import Path


def test_main_registers_universal_social_export_surface_router_r43f() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING" in source
    assert "universal_social_export_surface_router_r43f" in source
    assert "build_universal_social_export_surface_router_r43f" in source
    assert "universal_social_account_tracking_registry_r43e" in source
    assert "twitter_x_account_tracking_export_surface_r43d" in source
    assert "source-role checks" in source or "source_role" in source


def run_self_test() -> None:
    test_main_registers_universal_social_export_surface_router_r43f()
    print("main_universal_social_export_surface_ui_routing_r43f_test: PASS")


if __name__ == "__main__":
    run_self_test()
