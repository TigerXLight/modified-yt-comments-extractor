from __future__ import annotations

import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime("%Y%m%d_%H%M%S")
out = ROOT / "profile_media_live_captures" / "r42en_file_converter_review_fillbox_clone_text_fix" / f"ytce_r42en_file_converter_review_fillbox_clone_text_fix_patch_{stamp}.zip"
out.parent.mkdir(parents=True, exist_ok=True)
files = [
    "main.py",
    "R42EN_FILE_CONVERTER_REVIEW_FILLBOX_CLONE_AND_TEXT_FIX_NOTES_20260908.md",
    "tools/profile_media_file_converter/smoke_r42en_file_converter_review_fillbox_clone_text_fix.cmd",
    "tools/profile_media_file_converter/probe_r42en_file_converter_review_fillbox_clone_text_fix_no_gui.py",
    "tools/profile_media_file_converter/probe_r42en_file_converter_review_fillbox_clone_text_fix_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42en_file_converter_review_fillbox_clone_text_fix_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42en_file_converter_review_fillbox_clone_text_fix_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42en_file_converter_review_fillbox_clone_text_fix_zip.py",
    "tools/profile_media_file_converter/build_r42en_file_converter_review_fillbox_clone_text_fix_zip.cmd",
]
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        path = ROOT / rel
        if path.exists():
            zf.write(path, "project/" + rel)
print(out)
