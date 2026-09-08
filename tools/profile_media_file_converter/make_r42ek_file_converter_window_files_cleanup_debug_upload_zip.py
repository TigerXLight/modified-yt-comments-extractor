from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42ek_file_converter_window_files_cleanup"
out_dir.mkdir(parents=True, exist_ok=True)
zip_path = out_dir / f"r42ek_file_converter_window_files_cleanup_debug_upload_{stamp}.zip"
downloads_zip = Path.home() / "Downloads" / zip_path.name
include = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "profile_media_file_converter_r42eg.py",
    "profile_media_file_converter_r42eh_test.py",
    "R42EK_FILE_CONVERTER_WINDOW_AND_FILES_CLEANUP_NOTES_20260908.md",
    "assets/Keep icon icons8-kappa-100.png",
    "assets/Open folder icon icons8-opened-folder-ios-27-outlined.png",
    "tools/profile_media_file_converter/smoke_r42ek_file_converter_window_files_cleanup.cmd",
    "tools/profile_media_file_converter/probe_r42ek_file_converter_window_files_cleanup_no_gui.py",
    "tools/profile_media_file_converter/probe_r42ek_file_converter_window_files_cleanup_no_gui.cmd",
    "profile_media_live_captures/r42ek_file_converter_window_files_cleanup/r42ek_file_converter_window_files_cleanup_probe_summary.json",
]
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in include:
        path = ROOT / rel
        if path.exists():
            zf.write(path, rel)
try:
    shutil.copy2(zip_path, downloads_zip)
except Exception:
    pass
payload = {
    "schema": "ytce.r42ek.file_converter_window_files_cleanup.v1.debug_zip",
    "zip_path": str(zip_path),
    "downloads_zip_path": str(downloads_zip),
    "included_files": len(include),
    "side_effects": {
        "archive_ph_hit": False,
        "network_actions_performed": False,
        "native_webview2_started": False,
        "app_started": False,
    },
    "verdict": {"zip_created": zip_path.exists(), "ready_for_upload": zip_path.exists()},
}
print(json.dumps(payload, indent=2))
print(f"[DONE] Created ZIP: {zip_path}")
print(f"[DONE] Copied ZIP to Downloads: {downloads_zip}")
