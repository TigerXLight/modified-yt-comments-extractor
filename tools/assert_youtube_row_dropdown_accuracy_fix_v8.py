from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / "main.py").read_text(encoding="utf-8")
queue = (root / "youtube_gui_media_queue.py").read_text(encoding="utf-8")

assert "_open_youtube_source_quality_dropdown_menu" in main
assert "tk.Menu(" in main
assert "CTkOptionMenu(" not in main[main.index("if self._source_row_is_youtube(row):"):main.index("if self._source_row_is_twitter(row):")]
assert "button.place(x=100, y=4)" in main or "youtube_button.place(x=100, y=4)" in main
assert "quality_checkbox.place(x=3, y=3)" in main
assert "detail_text = self._short_source_url_for_row(row)" in main
assert "return (default_label,)" in main
assert "self._youtube_watch_html_quality_probe" in main
assert 'fallback: Sequence[str] = (),' in queue
assert "return tuple(result)" in queue
print("YOUTUBE_ROW_DROPDOWN_ACCURACY_FIX_V8_STATIC_CHECK_OK")
