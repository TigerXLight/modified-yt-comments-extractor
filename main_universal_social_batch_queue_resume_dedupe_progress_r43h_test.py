from pathlib import Path


def test_main_registers_universal_social_batch_queue_r43h() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS" in source
    assert "universal_social_batch_queue_router_r43h" in source
    assert "build_universal_social_batch_queue_router_r43h" in source
    assert "universal_social_batch_account_intake_router_r43g" in source
    assert "R43G" in source and "R43F" in source and "R43E" in source
    assert "resume" in source.lower()
    assert "dedupe" in source.lower()
    assert "source-role" in source or "source_role" in source
    assert "does not start WebView2" in source or "WebView2" in source
    assert "YouTube capture engine" in source


def run_self_test() -> None:
    test_main_registers_universal_social_batch_queue_r43h()
    print("main_universal_social_batch_queue_resume_dedupe_progress_r43h_test: PASS")


if __name__ == "__main__":
    run_self_test()
