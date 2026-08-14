from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import App


def test_youtube_button_does_not_use_twitter_variables() -> None:
    source = inspect.getsource(App._refresh_source_resource_rows)
    youtube_inline = re.search(
        r"youtube_button = ctk\.CTkButton\(\n\s*youtube_control,.*?command=_open_youtube_settings,.*?\)",
        source,
        flags=re.S,
    )
    assert youtube_inline is not None
    block = youtube_inline.group(0)
    assert "width=16" in block
    assert "height=16" in block
    assert "twitter_button_width" not in block
    assert "twitter_button_height" not in block


def test_twitter_mode_change_rebuilds_row() -> None:
    source = inspect.getsource(App._open_twitter_source_mode_dropdown_menu)
    assert "update_widget.configure(text=value)" not in source
    assert "self.after(1, self._refresh_source_resource_rows)" in source
    assert "self.after(1, self._refresh_discussion_source_controls)" in source


def main() -> None:
    test_youtube_button_does_not_use_twitter_variables()
    test_twitter_mode_change_rebuilds_row()
    print("assert_source_row_regression_repair_v86 OK")


if __name__ == "__main__":
    main()
