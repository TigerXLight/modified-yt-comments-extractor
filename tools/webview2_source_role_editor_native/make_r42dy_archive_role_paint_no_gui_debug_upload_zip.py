from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import zipfile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42dy_archive_role_paint_no_gui"
OUTROOT.mkdir(parents=True, exist_ok=True)


def add_file(zf: zipfile.ZipFile, path: Path, arc: str, seen: set[str]) -> None:
    if not path.is_file():
        return
    arc = arc.replace("\\", "/").lstrip("/")
    if arc in seen:
        return
    seen.add(arc)
    zf.write(path, arc)


def add_latest_named(zf: zipfile.ZipFile, base: Path, filename: str, prefix: str, seen: set[str], limit: int = 20) -> None:
    if not base.exists():
        return
    files = [p for p in base.rglob(filename) if p.is_file() and p.stat().st_size <= 6_000_000]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[:limit]:
        rel = p.relative_to(base).as_posix()
        add_file(zf, p, f"{prefix}/{rel}", seen)


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUTROOT / f"r42dy_archive_role_paint_no_gui_debug_upload_{stamp}.zip"
    downloads = Path.home() / "Downloads" / zip_path.name
    seen: set[str] = set()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in [
            "profile_media_archive_role_payload_cmd_replay_r42dy.py",
            "profile_media_archive_role_payload_cmd_replay_r42dy_test.py",
            "profile_media_archive_role_payload_r42dw.py",
            "profile_media_archive_source_role_surface_r42ds.py",
            "profile_media_archive_material_chain_r42ct.py",
            "profile_media_link_source_real_webview_overlay_v83d.py",
            "main.py",
            "R42DY_CMDLINE_ARCHIVE_ROLE_PAINT_NO_GUI_NOTES_20260907.md",
            "tools/webview2_source_role_editor_native/Program.cs",
            "tools/webview2_source_role_editor_native/YTCE.NativeSourceRoleEditor.csproj",
            "tools/webview2_source_role_editor_native/_r42dy_python.cmd",
            "tools/webview2_source_role_editor_native/smoke_r42dy_no_gui_archive_role_paint.cmd",
            "tools/webview2_source_role_editor_native/probe_r42dy_archive_role_paint_no_gui.cmd",
            "tools/webview2_source_role_editor_native/probe_r42dy_archive_role_paint_no_gui_recolor.cmd",
            "tools/webview2_source_role_editor_native/probe_r42dw_archive_role_payload_from_latest.py",
            "tools/webview2_source_role_editor_native/launch_r42dw_native_overlay_from_latest.py",
            "tools/webview2_source_role_editor_native/build_r42dy_archive_role_paint_no_gui_zip.cmd",
            "tools/webview2_source_role_editor_native/build_r42dy_archive_role_paint_no_gui_zip.py",
            "tools/webview2_source_role_editor_native/make_r42dy_archive_role_paint_no_gui_debug_upload_zip.cmd",
            "tools/webview2_source_role_editor_native/make_r42dy_archive_role_paint_no_gui_debug_upload_zip.py",
        ]:
            add_file(zf, ROOT / rel, rel, seen)

        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42ct_archive_source_material", "native_webview2_material_capture.json", "_runtime/r42ct_archive_source_material", seen, limit=30)
        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42ct_archive_source_material", "native_webview2_material_payload.json", "_runtime/r42ct_archive_source_material", seen, limit=30)
        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42ct_archive_source_material", "article_text.txt", "_runtime/r42ct_archive_source_material", seen, limit=10)
        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42ct_archive_source_material", "archive_page.html", "_runtime/r42ct_archive_source_material", seen, limit=5)
        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42ds_archive_source_roles_webview2", "archive_source_role_surface_r42ds.json", "_runtime/r42ds_archive_source_roles_webview2", seen, limit=30)
        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42ds_archive_source_roles_webview2", "archive_source_role_spans_r42ds.jsonl", "_runtime/r42ds_archive_source_roles_webview2", seen, limit=30)
        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42dw_archive_role_payload", "archive_role_overlay_payload_r42dw.json", "_runtime/r42dw_archive_role_payload", seen, limit=30)
        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42dy_archive_role_paint_no_gui", "r42dy_no_gui_archive_role_paint_replay_summary.json", "_runtime/r42dy_archive_role_paint_no_gui", seen, limit=20)
        add_latest_named(zf, ROOT / "profile_media_live_captures" / "r42dy_archive_role_paint_no_gui", "r42dy_archive_role_paint_plan_no_gui.json", "_runtime/r42dy_archive_role_paint_no_gui", seen, limit=20)

        manifest = {
            "schema": "ytce.r42dy.archive_role_paint_no_gui_debug_upload_manifest.v1",
            "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
            "zip_path": str(zip_path),
            "files_included": len(seen),
            "no_gui": True,
            "no_network": True,
            "source_url": "https://archive.ph/6mr3C",
        }
        zf.writestr("r42dy_debug_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    shutil.copy2(zip_path, downloads)
    print(f"[DONE] Created ZIP: {zip_path}")
    print(f"[DONE] Copied ZIP to Downloads: {downloads}")
    print(f"[DONE] Files included: {len(seen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
