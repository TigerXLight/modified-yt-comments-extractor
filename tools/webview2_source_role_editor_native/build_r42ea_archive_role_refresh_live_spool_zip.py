from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import os
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "profile_media_live_captures" / "r42ea_archive_role_refresh_live_spool"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

INCLUDE = [
    "main.py",
    "profile_media_archive_role_refresh_live_spool_r42ea.py",
    "profile_media_archive_role_refresh_live_spool_r42ea_test.py",
    "profile_media_archive_role_payload_r42dw.py",
    "profile_media_archive_role_refresh_dispatch_r42dz.py",
    "profile_media_archive_role_payload_cmd_replay_r42dy.py",
    "profile_media_archive_source_role_surface_r42ds.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "R42EA_ARCHIVE_ROLE_REFRESH_LIVE_SPOOL_NO_GUI_NOTES_20260907.md",
    "tools/webview2_source_role_editor_native/_r42ea_python.cmd",
    "tools/webview2_source_role_editor_native/reset_r42ea_stuck_app_native_helper.cmd",
    "tools/webview2_source_role_editor_native/smoke_r42ea_archive_role_refresh_live_spool_no_gui.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ea_archive_role_refresh_live_spool_no_gui.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ea_archive_role_refresh_live_spool_no_gui_recolor.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ea_archive_role_refresh_live_spool_no_gui.py",
    "tools/webview2_source_role_editor_native/queue_r42ea_role_refresh_if_native_server_already_loaded.cmd",
    "tools/webview2_source_role_editor_native/queue_r42ea_role_refresh_if_native_server_already_loaded.py",
    "tools/webview2_source_role_editor_native/build_r42ea_archive_role_refresh_live_spool_zip.cmd",
    "tools/webview2_source_role_editor_native/build_r42ea_archive_role_refresh_live_spool_zip.py",
    "tools/webview2_source_role_editor_native/make_r42ea_archive_role_refresh_live_spool_debug_upload_zip.cmd",
    "tools/webview2_source_role_editor_native/make_r42ea_archive_role_refresh_live_spool_debug_upload_zip.py",
]

def add_file(zf: zipfile.ZipFile, source: Path, arc: str, manifest: list[dict[str, object]]) -> None:
    if not source.is_file():
        return
    zf.write(source, arc)
    manifest.append({"arc": arc, "bytes": source.stat().st_size})

def main() -> int:
    # Make a fresh no-GUI probe first so the bundle proves the current local state.
    py = sys.executable
    subprocess.run([py, str(ROOT / "tools/webview2_source_role_editor_native/probe_r42ea_archive_role_refresh_live_spool_no_gui.py")], cwd=str(ROOT), check=False)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUT_ROOT / f"r42ea_archive_role_refresh_live_spool_no_gui_{stamp}.zip"
    manifest: list[dict[str, object]] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE:
            add_file(zf, ROOT / rel, rel, manifest)
        # Include recent no-GUI outputs only; bounded and no recursive backups.
        for base in [
            OUT_ROOT,
            ROOT / "profile_media_live_captures/r42dz_archive_role_refresh_dispatch_no_gui",
            ROOT / "profile_media_live_captures/r42dy_archive_role_paint_no_gui",
            ROOT / "profile_media_live_captures/r42dx_cmdline_archive_role_payload",
        ]:
            if not base.exists():
                continue
            files = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".txt", ".md"} and p.stat().st_size <= 2_000_000]
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for p in files[:40]:
                rel = "_runtime/" + str(p.relative_to(ROOT)).replace("\\", "/")
                add_file(zf, p, rel, manifest)
        zf.writestr("r42ea_bundle_manifest.json", json.dumps({
            "schema": "ytce.r42ea.bundle_manifest.v1",
            "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
            "files_included": len(manifest),
            "no_gui": True,
            "no_network": True,
            "source_url": "https://archive.ph/6mr3C",
            "manifest": manifest,
        }, ensure_ascii=False, indent=2))
    downloads = Path.home() / "Downloads" / zip_path.name
    try:
        import shutil
        shutil.copy2(zip_path, downloads)
        print("[DONE] Copied ZIP to Downloads:", downloads)
    except Exception as exc:
        print("[WARN] Could not copy to Downloads:", exc)
    print("[DONE] Created ZIP:", zip_path)
    print("[DONE] Files included:", len(manifest))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
