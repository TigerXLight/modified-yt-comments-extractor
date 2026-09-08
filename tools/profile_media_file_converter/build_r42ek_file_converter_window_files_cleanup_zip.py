from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / "ytce_r42ek_file_converter_window_files_cleanup_patch_20260908.zip"
include = [
    "main.py",
    "R42EK_FILE_CONVERTER_WINDOW_AND_FILES_CLEANUP_NOTES_20260908.md",
    "tools/profile_media_file_converter/smoke_r42ek_file_converter_window_files_cleanup.cmd",
    "tools/profile_media_file_converter/probe_r42ek_file_converter_window_files_cleanup_no_gui.py",
    "tools/profile_media_file_converter/probe_r42ek_file_converter_window_files_cleanup_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42ek_file_converter_window_files_cleanup_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42ek_file_converter_window_files_cleanup_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42ek_file_converter_window_files_cleanup_zip.py",
    "tools/profile_media_file_converter/build_r42ek_file_converter_window_files_cleanup_zip.cmd",
]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in include:
        zf.write(ROOT / rel, f"project/{rel}")
print(out)
