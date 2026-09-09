from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
downloads = Path.home() / "Downloads"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out = downloads / f"ytce_r42eq_file_converter_preset_convert_settings_polish_patch_{stamp}.zip"

files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42EQ_FILE_CONVERTER_PRESET_AND_CONVERT_SETTINGS_POLISH_NOTES_20260909.md",
    "tools/profile_media_file_converter/smoke_r42eq_file_converter_preset_convert_settings.cmd",
    "tools/profile_media_file_converter/probe_r42eq_file_converter_preset_convert_settings_no_gui.py",
    "tools/profile_media_file_converter/probe_r42eq_file_converter_preset_convert_settings_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42eq_file_converter_preset_convert_settings_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42eq_file_converter_preset_convert_settings_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42eq_file_converter_preset_convert_settings_zip.py",
    "tools/profile_media_file_converter/build_r42eq_file_converter_preset_convert_settings_zip.cmd",
]

with ZipFile(out, "w", ZIP_DEFLATED) as zf:
    for rel in files:
        path = ROOT / rel
        if path.exists():
            zf.write(path, "project/" + rel)
print(f"[R42EQ] Patch ZIP: {out}")
