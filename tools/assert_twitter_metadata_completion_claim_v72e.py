from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "tools" else Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    runner = (ROOT / "twitter_browser_capture_runner.py").read_text(encoding="utf-8")
    runner_test = (ROOT / "twitter_browser_capture_runner_test.py").read_text(encoding="utf-8")
    inspector_test = (ROOT / "twitter_browser_capture_inspector_test.py").read_text(encoding="utf-8")

    assert 'elif rendered_dom_media_items:' in runner
    assert 'claim = "completed" if payload.events else "rendered_status_media_metadata_captured"' not in runner
    assert 'status = "success" if payload.events else "needs_review"' not in runner
    assert 'claim = "rendered_status_media_metadata_captured"' in runner

    assert "test_run_browser_capture_with_rendered_dom_metadata_only_is_not_completed" in runner_test
    assert "test_inspector_keeps_rendered_dom_metadata_claim_conservative_without_download" in inspector_test
    assert 'assert result.evidence_completion_claim == "rendered_status_media_metadata_captured"' in runner_test
    print("assert_twitter_metadata_completion_claim_v72e OK")


if __name__ == "__main__":
    main()
