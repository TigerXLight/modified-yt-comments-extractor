from __future__ import annotations

import subprocess
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42ep_file_converter_compression_button_settings_polish"
out_dir.mkdir(parents=True, exist_ok=True)
out_zip = out_dir / f"r42ep_file_converter_compression_button_settings_polish_debug_{stamp}.zip"
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "profile_media_file_converter_r42eg.py",
    "profile_media_file_converter_r42eh_test.py",
    "R42EP_FILE_CONVERTER_COMPRESSION_BUTTON_AND_SETTINGS_POLISH_NOTES_20260909.md",
    "tools/profile_media_file_converter/smoke_r42ep_file_converter_compression_button_settings.cmd",
    "tools/profile_media_file_converter/probe_r42ep_file_converter_compression_button_settings_no_gui.py",
    "tools/profile_media_file_converter/probe_r42ep_file_converter_compression_button_settings_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42ep_file_converter_compression_button_settings_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42ep_file_converter_compression_button_settings_debug_upload_zip.cmd",
]

def _cmd(args: list[str]) -> str:
    try:
        proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, errors="replace", timeout=45)
        return proc.stdout + proc.stderr
    except Exception as exc:
        return f"COMMAND FAILED: {args}: {exc}\n"

extras = {
    "git_status_short.txt": _cmd(["git", "status", "--short"]),
    "git_diff_stat.txt": _cmd(["git", "--no-pager", "diff", "--stat"]),
    "git_diff_r42ep.txt": _cmd(["git", "--no-pager", "diff", "--", "main.py", "R42EP_FILE_CONVERTER_COMPRESSION_BUTTON_AND_SETTINGS_POLISH_NOTES_20260909.md", "tools/profile_media_file_converter"]),
}
with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        path = ROOT / rel
        if path.exists():
            zf.write(path, rel)
    for name, content in extras.items():
        zf.writestr(name, content)
print(f"[R42EP] Debug upload ZIP: {out_zip}")
