from pathlib import Path


def test_main_registers_universal_social_batch_workbench_gui_state_bridge_r43k() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE" in source
    assert "universal_social_batch_workbench_gui_state_bridge_r43k" in source
    assert "build_universal_social_batch_workbench_gui_state_bridge_r43k" in source
    assert "universal_social_batch_queue_workbench_panel_r43j" in source
    assert "recent universal-social" in source
    assert "panel rows" in source
    assert "selections" in source
    assert "receipt paths" in source
    assert "run/resume/retry remain" in source
    assert "R43J/R43I/R43H" in source
    assert "source-role" in source or "source_role" in source
    assert "review-window" in source or "review window" in source
    assert "WebView2" in source
    assert "YouTube capture engine" in source


def run_self_test() -> None:
    test_main_registers_universal_social_batch_workbench_gui_state_bridge_r43k()
    print("main_universal_social_batch_workbench_gui_state_bridge_r43k_test: PASS")


if __name__ == "__main__":
    run_self_test()
