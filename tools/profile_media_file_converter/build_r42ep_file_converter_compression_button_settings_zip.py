from __future__ import annotations

import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42ep_file_converter_compression_button_settings_polish"
out_dir.mkdir(parents=True, exist_ok=True)
out_zip = out_dir / f"ytce_r42ep_file_converter_compression_button_settings_polish_patch_{stamp}.zip"
files = [
    "main.py",
    "R42EP_FILE_CONVERTER_COMPRESSION_BUTTON_AND_SETTINGS_POLISH_NOTES_20260909.md",
    "tools/profile_media_file_converter/smoke_r42ep_file_converter_compression_button_settings.cmd",
    "tools/profile_media_file_converter/probe_r42ep_file_converter_compression_button_settings_no_gui.py",
    "tools/profile_media_file_converter/probe_r42ep_file_converter_compression_button_settings_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42ep_file_converter_compression_button_settings_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42ep_file_converter_compression_button_settings_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42ep_file_converter_compression_button_settings_zip.py",
    "tools/profile_media_file_converter/build_r42ep_file_converter_compression_button_settings_zip.cmd",
]
with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        path = ROOT / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        zf.write(path, "project/" + rel)
print(f"[R42EP] Patch ZIP: {out_zip}")
