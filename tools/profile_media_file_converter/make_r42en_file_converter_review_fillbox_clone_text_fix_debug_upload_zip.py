from __future__ import annotations

import os
import subprocess
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42en_file_converter_review_fillbox_clone_text_fix"
out_dir.mkdir(parents=True, exist_ok=True)
out_zip = out_dir / f"r42en_file_converter_review_fillbox_clone_text_fix_debug_{stamp}.zip"
files = [
    "main.py",
    "R42EN_FILE_CONVERTER_REVIEW_FILLBOX_CLONE_AND_TEXT_FIX_NOTES_20260908.md",
    "profile_media_file_converter_r42eh.py",
    "profile_media_file_converter_r42eg.py",
    "profile_media_file_converter_r42eh_test.py",
    "tools/profile_media_file_converter/smoke_r42en_file_converter_review_fillbox_clone_text_fix.cmd",
    "tools/profile_media_file_converter/probe_r42en_file_converter_review_fillbox_clone_text_fix_no_gui.py",
    "tools/profile_media_file_converter/probe_r42en_file_converter_review_fillbox_clone_text_fix_no_gui.cmd",
]

def _cmd(args: list[str]) -> str:
    try:
        return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, errors="replace", timeout=45).stdout
    except Exception as exc:
        return f"COMMAND FAILED: {args}: {exc}\n"

extras = {
    "git_status_short.txt": _cmd(["git", "status", "--short"]),
    "git_diff_stat.txt": _cmd(["git", "--no-pager", "diff", "--stat"]),
    "git_diff_r42en.txt": _cmd(["git", "--no-pager", "diff", "--", "main.py", "R42EN_FILE_CONVERTER_REVIEW_FILLBOX_CLONE_AND_TEXT_FIX_NOTES_20260908.md", "tools/profile_media_file_converter"]),
}
with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        path = ROOT / rel
        if path.exists():
            zf.write(path, rel)
    for name, content in extras.items():
        zf.writestr(name, content)
print(f"[R42EN] Debug upload ZIP: {out_zip}")
