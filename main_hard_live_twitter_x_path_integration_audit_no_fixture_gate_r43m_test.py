from __future__ import annotations

from pathlib import Path


def test_main_registers_r43l_app_shell_for_r43m_source_proof() -> None:
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")

    assert "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS" in text
    assert "build_universal_social_batch_workbench_app_shell_commands_r43l" in text
    assert "universal_social_batch_workbench_app_shell_commands_r43l" in text
    assert "universal_social_batch_queue_workbench_panel_r43j" in text
    assert "universal_social_batch_workbench_gui_state_bridge_r43k" in text


def test_r43m_audit_uses_robust_main_registration_and_negative_safety_sweep() -> None:
    text = Path("profile_media_hard_live_twitter_x_path_integration_audit_no_fixture_gate_r43m.py").read_text(
        encoding="utf-8",
        errors="replace",
    )

    assert "def _main_registers_r43l" in text
    assert "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS" in text
    assert "def _no_positive_forbidden_behaviour" in text
    assert "document\\.cookie" in text
    assert "no cookie extraction" not in text.lower()
    assert "live_capture_enabled" in Path("profile_media_twitter_x_account_tracking_export_surface_r43d.py").read_text(
        encoding="utf-8",
        errors="replace",
    )


if __name__ == "__main__":
    test_main_registers_r43l_app_shell_for_r43m_source_proof()
    test_r43m_audit_uses_robust_main_registration_and_negative_safety_sweep()
    print("PASS main_hard_live_twitter_x_path_integration_audit_no_fixture_gate_r43m_test")
