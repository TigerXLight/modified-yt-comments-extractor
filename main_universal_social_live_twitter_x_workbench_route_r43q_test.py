from __future__ import annotations

from pathlib import Path


def test_main_keeps_r43q_on_existing_registered_route_chain() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "universal_social_batch_workbench_app_shell_commands_r43l" in source
    assert "universal_social_batch_queue_workbench_panel_r43j" in source
    assert "universal_social_batch_queue_workbench_r43i" in source
    assert "universal_social_batch_queue_router_r43h" in source
    assert "universal_social_batch_account_intake_router_r43g" in source
    assert "universal_social_export_surface_router_r43f" in source
    assert "universal_social_account_tracking_registry_r43e" in source
    assert "live_twitter_x_single_account_smoke_harness_r43n" in source
    assert "live_twitter_x_visible_session_binding_r43o" in source
    assert "live_twitter_x_runner_output_promotion_r43p" in source


def test_r43l_does_not_directly_import_r43n_smoke_harness() -> None:
    source = Path("profile_media_universal_social_batch_workbench_app_shell_commands_r43l.py").read_text(encoding="utf-8")
    assert "profile_media_live_twitter_x_single_account_smoke_harness_r43n" not in source
    assert "build_live_twitter_x_single_account_smoke_harness_r43n" not in source


if __name__ == "__main__":
    test_main_keeps_r43q_on_existing_registered_route_chain()
    test_r43l_does_not_directly_import_r43n_smoke_harness()
    print("main R43Q tests passed")
