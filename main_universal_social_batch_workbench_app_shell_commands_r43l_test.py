from pathlib import Path


def test_main_registers_universal_social_batch_workbench_app_shell_commands_r43l() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS" in source
    assert "universal_social_batch_workbench_app_shell_commands_r43l" in source
    assert "build_universal_social_batch_workbench_app_shell_commands_r43l" in source
    assert "universal_social_batch_queue_workbench_panel_r43j" in source
    assert "universal_social_batch_workbench_gui_state_bridge_r43k" in source
    assert "opening the" in source
    assert "pasting/loading inputs" in source
    assert "saving/restoring state" in source
    assert "run" in source.lower() and "retry" in source.lower() and "skip" in source.lower()
    assert "Commands delegate to R43J/R43K" in source
    assert "R43H/R43G/R43F/R43E/R43D directly" in source
    assert "source-role" in source or "source_role" in source
    assert "review-window" in source or "review window" in source
    assert "WebView2" in source
    assert "YouTube capture engine" in source


def run_self_test() -> None:
    test_main_registers_universal_social_batch_workbench_app_shell_commands_r43l()
    print("main_universal_social_batch_workbench_app_shell_commands_r43l_test: PASS")


if __name__ == "__main__":
    run_self_test()
