from __future__ import annotations

import subprocess
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42eo_file_converter_compression_ui_media_windows"
out_dir.mkdir(parents=True, exist_ok=True)
out_zip = out_dir / f"r42eo_file_converter_compression_ui_media_windows_debug_{stamp}.zip"
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "profile_media_file_converter_r42eg.py",
    "profile_media_file_converter_r42eh_test.py",
    "R42EO_FILE_CONVERTER_COMPRESSION_UI_AND_MEDIA_WINDOWS_NOTES_20260909.md",
    "assets/Keep icon icons8-k-ios-27-filled.png",
    "assets/Compression icon icons8-c-ios-27-filled.png",
    "tools/profile_media_file_converter/smoke_r42eo_file_converter_compression_ui.cmd",
    "tools/profile_media_file_converter/probe_r42eo_file_converter_compression_ui_no_gui.py",
    "tools/profile_media_file_converter/probe_r42eo_file_converter_compression_ui_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42eo_file_converter_compression_ui_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42eo_file_converter_compression_ui_debug_upload_zip.cmd",
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
    "git_diff_r42eo.txt": _cmd(["git", "--no-pager", "diff", "--", "main.py", "profile_media_file_converter_r42eh.py", "R42EO_FILE_CONVERTER_COMPRESSION_UI_AND_MEDIA_WINDOWS_NOTES_20260909.md", "tools/profile_media_file_converter"]),
}
with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        path = ROOT / rel
        if path.exists():
            zf.write(path, rel)
    for name, content in extras.items():
        zf.writestr(name, content)
print(f"[R42EO] Debug upload ZIP: {out_zip}")
