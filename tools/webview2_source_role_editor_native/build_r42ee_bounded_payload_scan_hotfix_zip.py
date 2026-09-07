from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "profile_media_live_captures" / "r42ee_bounded_payload_scan_hotfix"
DOWNLOADS = Path.home() / "Downloads"
INCLUDE = [
    "profile_media_semantic_media_logic_matrix_r42ed.py",
    "profile_media_semantic_media_logic_matrix_r42ed_test.py",
    "profile_media_semantic_media_logic_matrix_r42ee_test.py",
    "profile_media_archive_role_payload_r42dw.py",
    "R42EE_BOUNDED_PAYLOAD_SCAN_HOTFIX_NOTES_20260907.md",
    "tools/webview2_source_role_editor_native/_r42ee_python.cmd",
    "tools/webview2_source_role_editor_native/reset_r42ee_stuck_app_native_helper.cmd",
    "tools/webview2_source_role_editor_native/smoke_r42ee_bounded_payload_scan_hotfix.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ee_bounded_payload_scan_hotfix_no_gui.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ee_bounded_payload_scan_hotfix_no_gui_recolor.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ee_bounded_payload_scan_hotfix_no_gui.py",
    "tools/webview2_source_role_editor_native/build_r42ee_bounded_payload_scan_hotfix_zip.cmd",
    "tools/webview2_source_role_editor_native/build_r42ee_bounded_payload_scan_hotfix_zip.py",
    "tools/webview2_source_role_editor_native/make_r42ee_bounded_payload_scan_hotfix_debug_upload_zip.cmd",
    "tools/webview2_source_role_editor_native/make_r42ee_bounded_payload_scan_hotfix_debug_upload_zip.py",
]

def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUT_ROOT / f"r42ee_bounded_payload_scan_hotfix_{stamp}.zip"
    manifest = {"schema":"ytce.r42ee.reference_zip_manifest.v1","created_at_local":datetime.now().replace(microsecond=0).isoformat(),"included":[]}
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE:
            p = ROOT / rel
            if p.is_file():
                zf.write(p, rel.replace("\\", "/")); manifest["included"].append(rel.replace("\\", "/"))
        zf.writestr("r42ee_reference_zip_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    dst = DOWNLOADS / zip_path.name
    shutil.copy2(zip_path, dst)
    print(f"[DONE] Created ZIP: {zip_path}")
    print(f"[DONE] Copied ZIP to Downloads: {dst}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
