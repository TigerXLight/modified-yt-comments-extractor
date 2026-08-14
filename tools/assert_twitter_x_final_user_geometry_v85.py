# V85 assertion: user-accepted Twitter/X compact row geometry.

from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import App
from source_resource_state import build_source_resource_row
from source_twitter_compact_row import build_twitter_compact_row_state


def test_v85_final_geometry_and_refresh() -> None:
    source = inspect.getsource(App._refresh_source_resource_rows)
    assert "twitter_control_width = 97 if twitter_is_thread else 95" in source
    assert "twitter_button_x = twitter_control_width - twitter_button_width - twitter_button_right_pad" in source
    assert "twitter_settings_button.place(x=twitter_button_x, y=2)" in source

    menu_source = inspect.getsource(App._open_twitter_source_mode_dropdown_menu)
    assert "update_widget.configure(text=value)" not in menu_source
    assert "self.after(1, self._refresh_source_resource_rows)" in menu_source
    assert "self.after(1, self._refresh_discussion_source_controls)" in menu_source


def test_v85_metadata() -> None:
    row = build_source_resource_row("https://x.com/example/status/1234567890")
    state = build_twitter_compact_row_state(row)
    assert state.compact_control_width == 95
    assert state.icon_position == "final_user_selected_post_w95_thread_w97_refresh_rebuild"


def main() -> None:
    test_v85_final_geometry_and_refresh()
    test_v85_metadata()
    print("assert_twitter_x_final_user_geometry_v85 OK")


if __name__ == "__main__":
    main()
