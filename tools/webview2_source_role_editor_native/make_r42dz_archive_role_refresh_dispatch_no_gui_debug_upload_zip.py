from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import zipfile
import subprocess
import sys
import os

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42dz_archive_role_refresh_dispatch_no_gui"

EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", "bin", "obj", ".venv", "venv", "env", "build", "dist"}
INCLUDE_SUFFIXES = {".py", ".cmd", ".cs", ".csproj", ".json", ".jsonl", ".md", ".txt", ".log", ".csv"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    if path.suffix.lower() not in INCLUDE_SUFFIXES:
        return False
    try:
        if path.stat().st_size > 2_500_000:
            return False
    except OSError:
        return False
    return True


def main() -> int:
    OUTROOT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (";" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    subprocess.run([sys.executable, str(ROOT / "profile_media_archive_role_refresh_dispatch_r42dz.py"), "https://archive.ph/6mr3C", "--root", str(ROOT)], cwd=str(ROOT), env=env, check=False)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUTROOT / ("r42dz_archive_role_refresh_dispatch_no_gui_debug_upload_" + stamp + ".zip")
    included: list[str] = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        root_files = [
            "profile_media_archive_role_refresh_dispatch_r42dz.py",
            "profile_media_archive_role_refresh_dispatch_r42dz_test.py",
            "profile_media_archive_role_payload_r42dw.py",
            "profile_media_archive_role_payload_cmd_replay_r42dy.py",
            "profile_media_archive_source_role_surface_r42ds.py",
            "profile_media_archive_material_chain_r42ct.py",
            "profile_media_link_source_real_webview_overlay_v83d.py",
            "main.py",
            "R42DZ_CMDLINE_ARCHIVE_ROLE_REFRESH_DISPATCH_NO_GUI_NOTES_20260907.md",
        ]
        for rel in root_files:
            p = ROOT / rel
            if should_include(p):
                zf.write(p, rel)
                included.append(rel)
        for rel in [
            "tools/webview2_source_role_editor_native/Program.cs",
            "tools/webview2_source_role_editor_native/YTCE.NativeSourceRoleEditor.csproj",
            "tools/webview2_source_role_editor_native/_r42dz_python.cmd",
            "tools/webview2_source_role_editor_native/reset_r42dz_stuck_app_native_helper.cmd",
            "tools/webview2_source_role_editor_native/smoke_r42dz_archive_role_refresh_dispatch_no_gui.cmd",
            "tools/webview2_source_role_editor_native/probe_r42dz_archive_role_refresh_dispatch_no_gui.cmd",
            "tools/webview2_source_role_editor_native/probe_r42dz_archive_role_refresh_dispatch_no_gui_recolor.cmd",
            "tools/webview2_source_role_editor_native/build_r42dz_archive_role_refresh_dispatch_no_gui_zip.cmd",
            "tools/webview2_source_role_editor_native/build_r42dz_archive_role_refresh_dispatch_no_gui_zip.py",
            "tools/webview2_source_role_editor_native/make_r42dz_archive_role_refresh_dispatch_no_gui_debug_upload_zip.cmd",
            "tools/webview2_source_role_editor_native/make_r42dz_archive_role_refresh_dispatch_no_gui_debug_upload_zip.py",
        ]:
            p = ROOT / rel
            if should_include(p):
                zf.write(p, rel)
                included.append(rel)
        # Bounded latest runtime outputs only.
        for base_rel in [
            "profile_media_live_captures/r42dz_archive_role_refresh_dispatch_no_gui",
            "profile_media_live_captures/r42dy_archive_role_paint_no_gui",
            "profile_media_live_captures/r42dw_archive_role_payload",
            "profile_media_live_captures/r42ds_archive_source_roles_webview2",
            "profile_media_live_captures/r42ct_archive_source_material",
            "profile_media_live_captures/link_source_role_webview_overlay",
        ]:
            base = ROOT / base_rel
            if not base.exists():
                continue
            files = [p for p in base.rglob("*") if p.is_file() and should_include(p)]
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for p in files[:45]:
                try:
                    arc = "_runtime/" + str(p.relative_to(ROOT)).replace("\\", "/")
                    zf.write(p, arc)
                    included.append(arc)
                except Exception:
                    pass
        manifest = {
            "schema": "ytce.r42dz.debug_upload_manifest.v1",
            "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
            "zip_path": str(zip_path),
            "files_included": len(included),
            "no_gui": True,
            "no_network": True,
            "source_url": "https://archive.ph/6mr3C",
        }
        zf.writestr("r42dz_debug_upload_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    downloads = Path.home() / "Downloads" / zip_path.name
    try:
        downloads.write_bytes(zip_path.read_bytes())
        print("[DONE] Created ZIP:", zip_path)
        print("[DONE] Copied ZIP to Downloads:", downloads)
    except Exception as exc:
        print("[DONE] Created ZIP:", zip_path)
        print("[WARN] Could not copy to Downloads:", exc)
    print("[DONE] Files included:", len(included))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
