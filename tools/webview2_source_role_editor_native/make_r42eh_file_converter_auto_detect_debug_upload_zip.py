from __future__ import annotations
from pathlib import Path
import json
import os
import shutil
import zipfile
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = ROOT / "profile_media_live_captures" / "r42eh_file_converter_auto_detect"
OUT_DIR.mkdir(parents=True, exist_ok=True)
zip_path = OUT_DIR / f"r42eh_file_converter_auto_detect_debug_upload_{STAMP}.zip"
downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads" / zip_path.name
files = [
    ROOT / "main.py",
    ROOT / "profile_media_file_converter_r42eh.py",
    ROOT / "profile_media_file_converter_r42eg.py",
    ROOT / "profile_media_file_converter_r42eh_test.py",
    ROOT / "R42EH_FILE_CONVERTER_AUTO_DETECT_NOTES_20260907.md",
    ROOT / "assets" / "Keep icon icons8-kappa-100.png",
    ROOT / "tools" / "webview2_source_role_editor_native" / "smoke_r42eh_file_converter_auto_detect.cmd",
    ROOT / "tools" / "webview2_source_role_editor_native" / "probe_r42eh_file_converter_auto_detect_no_gui.py",
    ROOT / "tools" / "webview2_source_role_editor_native" / "probe_r42eh_file_converter_auto_detect_no_gui.cmd",
]
for p in sorted(OUT_DIR.glob("r42eh_file_converter_auto_detect_probe_summary.json"))[-2:]:
    files.append(p)
included = []
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for p in files:
        if p.exists() and p.is_file():
            try:
                arc = str(p.relative_to(ROOT))
            except Exception:
                arc = p.name
            zf.write(p, arc)
            included.append(arc)
try:
    shutil.copy2(zip_path, downloads)
except Exception:
    downloads = Path("")
summary = {
    "schema": "ytce.r42eh.file_converter_auto_detect.v1.debug_zip",
    "created_at_local": datetime.now().isoformat(timespec="seconds"),
    "zip_path": str(zip_path),
    "downloads_zip_path": str(downloads) if downloads else "",
    "included_files": len(included),
    "included": included,
    "side_effects": {"archive_ph_hit": False, "network_actions_performed": False, "native_webview2_started": False, "app_started": False},
    "verdict": {"zip_created": zip_path.exists(), "ready_for_upload": zip_path.exists()},
}
print(json.dumps(summary, indent=2, ensure_ascii=False))
print(f"[DONE] Created ZIP: {zip_path}")
if downloads:
    print(f"[DONE] Copied ZIP to Downloads: {downloads}")
print(f"[DONE] Files included: {len(included)}")
