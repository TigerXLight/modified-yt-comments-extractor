from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source_resource_state import build_source_resource_row
from source_twitter_compact_row import build_twitter_compact_row_state


def main() -> None:
    row = build_source_resource_row("https://x.com/example/status/12345")
    state = build_twitter_compact_row_state(row)
    assert state.dropdown_options == ("Post", "Thread")
    assert state.media_download_inside_settings is True
    assert state.visible_capture_options == ("article_screenshot",)
    assert state.local_export_button_visible is False
    assert state.add_review_draft_button_visible is False
    assert state.review_flow_summary_button_visible is False
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "Twitter/X Local Export" not in main_text
    assert "Add Review Draft" not in main_text
    assert "Review Flow Summary" not in main_text
    assert "row media controls" not in main_text
    assert "Media download stays inside X settings" in main_text
    print("assert_twitter_compact_row_v27 OK")


if __name__ == "__main__":
    main()
