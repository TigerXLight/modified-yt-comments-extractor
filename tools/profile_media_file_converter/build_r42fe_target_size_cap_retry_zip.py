from __future__ import annotations
import zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / "ytce_r42fe_target_size_cap_retry_patch_20260910.zip"
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42FE_TARGET_SIZE_CAP_RETRY_NOTES_20260910.md",
    "tools/profile_media_file_converter/smoke_r42fe_target_size_cap_retry.cmd",
    "tools/profile_media_file_converter/probe_r42fe_target_size_cap_retry_no_gui.py",
    "tools/profile_media_file_converter/probe_r42fe_target_size_cap_retry_no_gui.cmd",
    "tools/profile_media_file_converter/audit_r42fe_target_size_cap_retry_no_gui.py",
    "tools/profile_media_file_converter/audit_r42fe_target_size_cap_retry_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42fe_target_size_cap_retry_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42fe_target_size_cap_retry_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42fe_target_size_cap_retry_zip.py",
    "tools/profile_media_file_converter/build_r42fe_target_size_cap_retry_zip.cmd",
]
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        z.write(ROOT / rel, f"project/{rel}")
print(OUT)
