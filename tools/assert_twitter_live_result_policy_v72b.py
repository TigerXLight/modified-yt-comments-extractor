from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    runner = (ROOT / "twitter_browser_capture_runner.py").read_text(encoding="utf-8")
    inspector = (ROOT / "twitter_browser_capture_inspector.py").read_text(encoding="utf-8")
    runner_test = (ROOT / "twitter_browser_capture_runner_test.py").read_text(encoding="utf-8")
    inspector_test = (ROOT / "twitter_browser_capture_inspector_test.py").read_text(encoding="utf-8")

    assert "def _run_twitter_browser_capture_impl(" in runner
    assert "def run_twitter_browser_capture(source_url: str, *args: Any, **kwargs: Any)" in runner
    assert "twitter_live_capture_http_404_zero_items_not_completed" in runner
    assert "twitter_live_capture_markdown_url_unwrapped" in runner

    assert "def _inspect_twitter_browser_capture_output_impl(" in inspector
    assert "def inspect_twitter_browser_capture_output(output_dir: str | Path)" in inspector
    assert "twitter_api_http_404_no_items" in inspector
    assert "runner_url_not_normalized" in inspector

    assert "test_runner_marks_http_404_zero_item_capture_not_completed" in runner_test
    assert "test_inspector_flags_http_404_zero_items_as_not_completed" in inspector_test
    print("assert_twitter_live_result_policy_v72b OK")


if __name__ == "__main__":
    main()
