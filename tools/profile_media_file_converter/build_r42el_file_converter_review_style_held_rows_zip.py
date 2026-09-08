from __future__ import annotations

import os
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out = ROOT / f"ytce_r42el_file_converter_review_style_held_rows_patch_{stamp}.zip"
include = [
    "main.py",
    "R42EL_FILE_CONVERTER_REVIEW_STYLE_HELD_ROWS_NOTES_20260908.md",
    "tools/profile_media_file_converter/smoke_r42el_file_converter_review_style_held_rows.cmd",
    "tools/profile_media_file_converter/probe_r42el_file_converter_review_style_held_rows_no_gui.py",
    "tools/profile_media_file_converter/probe_r42el_file_converter_review_style_held_rows_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42el_file_converter_review_style_held_rows_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42el_file_converter_review_style_held_rows_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42el_file_converter_review_style_held_rows_zip.py",
    "tools/profile_media_file_converter/build_r42el_file_converter_review_style_held_rows_zip.cmd",
]
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for rel in include:
        path = ROOT / rel
        if path.exists():
            z.write(path, "project/" + rel)
print(f"[DONE] Created {out}")
