from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42el_file_converter_review_style_held_rows"
out_dir.mkdir(parents=True, exist_ok=True)
zip_path = out_dir / f"r42el_file_converter_review_style_held_rows_debug_upload_{stamp}.zip"
downloads = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
downloads_zip_path = downloads / zip_path.name if downloads.exists() else None

include = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "profile_media_file_converter_r42eg.py",
    "profile_media_file_converter_r42eh_test.py",
    "R42EL_FILE_CONVERTER_REVIEW_STYLE_HELD_ROWS_NOTES_20260908.md",
    "R42EK_FILE_CONVERTER_WINDOW_AND_FILES_CLEANUP_NOTES_20260908.md",
    "assets/Keep icon icons8-kappa-100.png",
    "assets/Open folder icon icons8-opened-folder-ios-27-outlined.png",
    "tools/profile_media_file_converter/smoke_r42el_file_converter_review_style_held_rows.cmd",
    "tools/profile_media_file_converter/probe_r42el_file_converter_review_style_held_rows_no_gui.py",
    "tools/profile_media_file_converter/probe_r42el_file_converter_review_style_held_rows_no_gui.cmd",
    "profile_media_live_captures/r42el_file_converter_review_style_held_rows/r42el_file_converter_review_style_held_rows_probe_summary.json",
]
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for rel in include:
        path = ROOT / rel
        if path.exists():
            z.write(path, rel)
    try:
        status = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True, timeout=20)
        z.writestr("git_status_short.txt", status.stdout + status.stderr)
    except Exception as exc:
        z.writestr("git_status_short_error.txt", str(exc))
    try:
        diff = subprocess.run(["git", "--no-pager", "diff", "--stat"], cwd=ROOT, capture_output=True, text=True, timeout=20)
        z.writestr("git_diff_stat.txt", diff.stdout + diff.stderr)
    except Exception as exc:
        z.writestr("git_diff_stat_error.txt", str(exc))

copied = False
if downloads_zip_path is not None:
    shutil.copy2(zip_path, downloads_zip_path)
    copied = downloads_zip_path.exists()

payload = {
    "schema": "ytce.r42el.file_converter_review_style_held_rows.v1.debug_zip",
    "zip_path": str(zip_path),
    "downloads_zip_path": str(downloads_zip_path) if downloads_zip_path is not None else "",
    "included_files": len(include),
    "side_effects": {
        "archive_ph_hit": False,
        "network_actions_performed": False,
        "native_webview2_started": False,
        "app_started": False,
    },
    "verdict": {
        "zip_created": zip_path.exists(),
        "copied_to_downloads": copied,
        "ready_for_upload": zip_path.exists(),
    },
}
print(json.dumps(payload, indent=2))
print(f"[DONE] Created ZIP: {zip_path}")
if downloads_zip_path is not None:
    print(f"[DONE] Copied ZIP to Downloads: {downloads_zip_path}")
