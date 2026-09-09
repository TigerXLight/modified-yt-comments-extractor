from __future__ import annotations
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path.home() / "Downloads" / "ytce_r42er_file_converter_convertit_handbrake_settings_polish_patch_20260909.zip"
stage = ROOT / "profile_media_live_captures" / "r42er_file_converter_convertit_handbrake_settings_patch_stage"
if stage.exists():
    shutil.rmtree(stage)
project = stage / "project"
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42ER_FILE_CONVERTER_CONVERTIT_HANDBRAKE_SETTINGS_POLISH_NOTES_20260909.md",
    "assets/Keep icon icons8-k-ios-27-filled.png",
    "assets/Compression icon icons8-c-ios-27-filled.png",
    "tools/profile_media_file_converter/smoke_r42er_file_converter_convertit_handbrake_settings.cmd",
    "tools/profile_media_file_converter/probe_r42er_file_converter_convertit_handbrake_settings_no_gui.py",
    "tools/profile_media_file_converter/probe_r42er_file_converter_convertit_handbrake_settings_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42er_file_converter_convertit_handbrake_settings_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42er_file_converter_convertit_handbrake_settings_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42er_file_converter_convertit_handbrake_settings_zip.py",
    "tools/profile_media_file_converter/build_r42er_file_converter_convertit_handbrake_settings_zip.cmd",
]
for rel in files:
    src = ROOT / rel
    if not src.exists():
        raise FileNotFoundError(rel)
    dst = project / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
if OUT.exists():
    OUT.unlink()
shutil.make_archive(str(OUT.with_suffix("")), "zip", stage)
print(f"CREATED R42ER PATCH ZIP: {OUT}")
