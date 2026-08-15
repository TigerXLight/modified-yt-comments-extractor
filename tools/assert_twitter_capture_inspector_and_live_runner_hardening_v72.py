from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    for rel in (
        "twitter_browser_capture_inspector.py",
        "twitter_browser_capture_inspector_test.py",
        "tools/inspect_twitter_browser_capture_v72.py",
        "tools/check_twitter_browser_capture_environment_v72.py",
    ):
        assert (ROOT / rel).exists(), rel
    runner = (ROOT / "twitter_browser_capture_runner.py").read_text(encoding="utf-8")
    assert "canonicalize_browser_capture_url" in runner
    assert "browser_user_data_dir" in runner
    assert "reuse_existing_profile" in runner
    assert "by_query.setdefault(page.query_name, []).append(page)" in runner
    assert "by_query.setdefault(page.query_name, []).append(page)\n        by_query.setdefault(page.query_name, []).append(page)" not in runner
    cli = (ROOT / "tools" / "run_twitter_browser_capture_v71.py").read_text(encoding="utf-8")
    assert "--browser-user-data-dir" in cli
    assert "--reuse-existing-profile" in cli
    from twitter_browser_capture_inspector import inspect_twitter_browser_capture_output
    assert callable(inspect_twitter_browser_capture_output)
    print("assert_twitter_capture_inspector_and_live_runner_hardening_v72 OK")


if __name__ == "__main__":
    main()
