from __future__ import annotations

from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
main = (root / "main.py").read_text(encoding="utf-8")

assert "row_height = 72 if self._source_row_is_youtube(row) else 98" in main
assert "width=76" in main
assert "quality_label = ctk.CTkLabel(" in main
assert re.search(r"quality_label\s*=\s*ctk\.CTkLabel\([\s\S]*?width=30,[\s\S]*?height=20,", main)
assert "quality_label.place(x=20, y=4)" in main
assert "checkbox_width=12" in main
assert "quality_checkbox.place(x=4, y=2)" in main
assert re.search(r"youtube_button\s*=\s*ctk\.CTkButton\([\s\S]*?width=16,[\s\S]*?height=16,[\s\S]*?font=ctk\.CTkFont\(size=7, weight=\"bold\"\),[\s\S]*?corner_radius=4,", main)
assert "youtube_button.place(x=56, y=2)" in main
assert "youtube_button.place(x=52, y=2)" not in main
assert "_quality_label_enter" in main and "_quality_label_leave" in main
assert 'text="Local archive settings"' in main
print("YOUTUBE_ICON_RIGHT_WRAP_BALANCE_FIX_V19_STATIC_CHECK_OK")
