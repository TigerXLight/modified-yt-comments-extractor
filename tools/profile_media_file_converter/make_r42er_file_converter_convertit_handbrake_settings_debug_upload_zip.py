from __future__ import annotations
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime("%Y%m%d_%H%M%S")
out = Path.home() / "Downloads" / f"ytce_r42er_file_converter_convertit_handbrake_settings_debug_{stamp}.zip"
stage = Path.home() / "AppData" / "Local" / "Temp" / f"ytce_r42er_debug_{stamp}"
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True, exist_ok=True)
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42ER_FILE_CONVERTER_CONVERTIT_HANDBRAKE_SETTINGS_POLISH_NOTES_20260909.md",
    "tools/profile_media_file_converter/probe_r42er_file_converter_convertit_handbrake_settings_no_gui.py",
    "tools/profile_media_file_converter/smoke_r42er_file_converter_convertit_handbrake_settings.cmd",
    "assets/Keep icon icons8-k-ios-27-filled.png",
    "assets/Compression icon icons8-c-ios-27-filled.png",
]
for rel in files:
    src = ROOT / rel
    if src.exists():
        dst = stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
(stage / "git_status_short.txt").write_text(subprocess.run(["git", "status", "--short"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout, encoding="utf-8")
(stage / "git_diff_stat.txt").write_text(subprocess.run(["git", "--no-pager", "diff", "--stat"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout, encoding="utf-8")
shutil.make_archive(str(out.with_suffix("")), "zip", stage)
print(f"CREATED R42ER DEBUG ZIP: {out}")
