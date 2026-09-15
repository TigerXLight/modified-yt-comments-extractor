from pathlib import Path


def test_main_registers_universal_social_batch_queue_workbench_panel_r43j() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING" in source
    assert "universal_social_batch_queue_workbench_panel_r43j" in source
    assert "build_universal_social_batch_queue_workbench_panel_r43j" in source
    assert "universal_social_batch_queue_workbench_r43i" in source
    assert "R43I" in source and "R43H" in source and "R43G" in source
    assert "paste" in source.lower()
    assert "preview" in source.lower()
    assert "selection" in source.lower() or "select" in source.lower()
    assert "source-role" in source or "source_role" in source
    assert "WebView2" in source
    assert "YouTube capture engine" in source


def run_self_test() -> None:
    test_main_registers_universal_social_batch_queue_workbench_panel_r43j()
    print("main_universal_social_batch_queue_workbench_panel_r43j_test: PASS")


if __name__ == "__main__":
    run_self_test()
