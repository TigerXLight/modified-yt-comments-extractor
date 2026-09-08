from __future__ import annotations

import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42eo_file_converter_compression_ui_media_windows"
out_dir.mkdir(parents=True, exist_ok=True)
out_zip = out_dir / f"ytce_r42eo_file_converter_compression_ui_media_windows_patch_{stamp}.zip"
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42EO_FILE_CONVERTER_COMPRESSION_UI_AND_MEDIA_WINDOWS_NOTES_20260909.md",
    "assets/Keep icon icons8-k-ios-27-filled.png",
    "assets/Compression icon icons8-c-ios-27-filled.png",
    "tools/profile_media_file_converter/smoke_r42eo_file_converter_compression_ui.cmd",
    "tools/profile_media_file_converter/probe_r42eo_file_converter_compression_ui_no_gui.py",
    "tools/profile_media_file_converter/probe_r42eo_file_converter_compression_ui_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42eo_file_converter_compression_ui_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42eo_file_converter_compression_ui_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42eo_file_converter_compression_ui_zip.py",
    "tools/profile_media_file_converter/build_r42eo_file_converter_compression_ui_zip.cmd",
]
with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        path = ROOT / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        zf.write(path, "project/" + rel)
print(f"[R42EO] Patch ZIP: {out_zip}")
