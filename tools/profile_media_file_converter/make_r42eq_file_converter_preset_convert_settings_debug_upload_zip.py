from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42eq_file_converter_preset_convert_settings_polish"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"r42eq_file_converter_preset_convert_settings_polish_debug_{stamp}.zip"

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
            zf.write(path, rel)
    for command, name in [
        (["git", "--no-pager", "log", "-8", "--oneline", "--decorate"], "git_log_8.txt"),
        (["git", "status", "--short"], "git_status_short.txt"),
        (["git", "--no-pager", "diff", "--stat", "--", *files], "git_diff_stat.txt"),
    ]:
        try:
            proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
            zf.writestr(name, (proc.stdout or "") + (proc.stderr or ""))
        except Exception as exc:
            zf.writestr(name, f"failed: {exc}\n")

print(f"[R42EQ] Debug upload ZIP: {out}")
