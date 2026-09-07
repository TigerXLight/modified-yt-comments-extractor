from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import sys
import zipfile
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "profile_media_live_captures" / "r42ea_archive_role_refresh_live_spool"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

def add(zf, p: Path, arc: str, manifest: list[dict[str, object]]) -> None:
    if p.is_file() and p.stat().st_size <= 5_000_000:
        zf.write(p, arc)
        manifest.append({"arc": arc, "bytes": p.stat().st_size})

def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "tools/webview2_source_role_editor_native/probe_r42ea_archive_role_refresh_live_spool_no_gui.py")], cwd=str(ROOT), check=False)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUT_ROOT / f"r42ea_archive_role_refresh_live_spool_debug_upload_{stamp}.zip"
    roots = [
        OUT_ROOT,
        ROOT / "profile_media_live_captures/r42dz_archive_role_refresh_dispatch_no_gui",
        ROOT / "profile_media_live_captures/r42dy_archive_role_paint_no_gui",
        ROOT / "profile_media_live_captures/r42dx_cmdline_archive_role_payload",
    ]
    project_files = [
        "main.py",
        "profile_media_archive_role_refresh_live_spool_r42ea.py",
        "profile_media_archive_role_refresh_live_spool_r42ea_test.py",
        "profile_media_archive_role_payload_r42dw.py",
        "profile_media_archive_source_role_surface_r42ds.py",
        "profile_media_link_source_real_webview_overlay_v83d.py",
        "R42EA_ARCHIVE_ROLE_REFRESH_LIVE_SPOOL_NO_GUI_NOTES_20260907.md",
        "tools/webview2_source_role_editor_native/Program.cs",
        "tools/webview2_source_role_editor_native/_r42ea_python.cmd",
        "tools/webview2_source_role_editor_native/smoke_r42ea_archive_role_refresh_live_spool_no_gui.cmd",
        "tools/webview2_source_role_editor_native/probe_r42ea_archive_role_refresh_live_spool_no_gui.cmd",
        "tools/webview2_source_role_editor_native/probe_r42ea_archive_role_refresh_live_spool_no_gui.py",
        "tools/webview2_source_role_editor_native/queue_r42ea_role_refresh_if_native_server_already_loaded.cmd",
        "tools/webview2_source_role_editor_native/queue_r42ea_role_refresh_if_native_server_already_loaded.py",
    ]
    manifest: list[dict[str, object]] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in project_files:
            add(zf, ROOT / rel, rel, manifest)
        for folder in roots:
            if not folder.exists():
                continue
            files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".txt", ".md", ".log"} and p.stat().st_size <= 2_000_000]
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for p in files[:60]:
                add(zf, p, "_runtime/" + str(p.relative_to(ROOT)).replace("\\", "/"), manifest)
        zf.writestr("r42ea_debug_upload_manifest.json", json.dumps({
            "schema": "ytce.r42ea.debug_upload_manifest.v1",
            "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
            "files_included": len(manifest),
            "no_gui": True,
            "no_network": True,
            "source_url": "https://archive.ph/6mr3C",
        }, ensure_ascii=False, indent=2))
    downloads = Path.home() / "Downloads" / zip_path.name
    try:
        shutil.copy2(zip_path, downloads)
        print("[DONE] Copied ZIP to Downloads:", downloads)
    except Exception as exc:
        print("[WARN] Could not copy to Downloads:", exc)
    print("[DONE] Created ZIP:", zip_path)
    print("[DONE] Files included:", len(manifest))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
