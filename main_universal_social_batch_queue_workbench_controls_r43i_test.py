from pathlib import Path


def test_main_registers_universal_social_batch_queue_workbench_r43i() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS" in source
    assert "universal_social_batch_queue_workbench_r43i" in source
    assert "build_universal_social_batch_queue_workbench_r43i" in source
    assert "universal_social_batch_queue_router_r43h" in source
    assert "R43H" in source and "R43G" in source and "R43F" in source
    assert "preview" in source.lower()
    assert "resume" in source.lower()
    assert "retry" in source.lower()
    assert "source-role" in source or "source_role" in source
    assert "WebView2" in source
    assert "YouTube capture engine" in source


def run_self_test() -> None:
    test_main_registers_universal_social_batch_queue_workbench_r43i()
    print("main_universal_social_batch_queue_workbench_controls_r43i_test: PASS")


if __name__ == "__main__":
    run_self_test()
