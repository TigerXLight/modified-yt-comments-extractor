from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT_BASE = ROOT / "profile_media_live_captures" / "r42ec_archive_role_closeout_no_gui"

SOURCE_FILES = [
    "main.py",
    "profile_media_archive_role_local_fixture_r42eb.py",
    "profile_media_archive_role_local_fixture_r42eb_test.py",
    "profile_media_archive_role_payload_r42dw.py",
    "profile_media_archive_role_refresh_live_spool_r42ea.py",
    "profile_media_archive_role_refresh_dispatch_r42dz.py",
    "profile_media_archive_role_payload_cmd_replay_r42dy.py",
    "profile_media_archive_role_closeout_r42ec.py",
    "profile_media_archive_role_closeout_r42ec_test.py",
    "profile_media_archive_source_role_surface_r42ds.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "R42EC_ARCHIVE_ROLE_CLOSEOUT_NO_GUI_NOTES_20260907.md",
    "tools/webview2_source_role_editor_native/Program.cs",
    "tools/webview2_source_role_editor_native/YTCE.NativeSourceRoleEditor.csproj",
]
SCRIPT_GLOBS = [
    "tools/webview2_source_role_editor_native/*r42eb*.cmd",
    "tools/webview2_source_role_editor_native/*r42eb*.py",
    "tools/webview2_source_role_editor_native/*r42ec*.cmd",
    "tools/webview2_source_role_editor_native/*r42ec*.py",
]

def add_if_file(zf: zipfile.ZipFile, path: Path, arc: str) -> int:
    if path.is_file():
        zf.write(path, arc)
        return 1
    return 0

def recent_files(base: Path, limit: int) -> list[Path]:
    if not base.exists():
        return []
    files = [p for p in base.rglob("*") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]

def main() -> int:
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    # Fresh no-GUI probe; safe, no app/browser/archive hit.
    subprocess.run([sys.executable, "profile_media_archive_role_closeout_r42ec.py"], cwd=ROOT, check=False)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUT_BASE / f"r42ec_archive_role_closeout_debug_upload_{stamp}.zip"
    included = 0
    manifest: dict[str, object] = {"created_at_local": datetime.now().replace(microsecond=0).isoformat(), "files": []}
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in SOURCE_FILES:
            p = ROOT / rel
            if add_if_file(zf, p, rel):
                included += 1
                manifest["files"].append(rel)  # type: ignore[index]
        for pattern in SCRIPT_GLOBS:
            for p in ROOT.glob(pattern):
                if p.is_file() and "__pycache__" not in p.parts:
                    arc = p.relative_to(ROOT).as_posix()
                    if add_if_file(zf, p, arc):
                        included += 1
        for base_rel, limit in [
            ("profile_media_live_captures/r42ec_archive_role_closeout_no_gui", 120),
            ("profile_media_live_captures/r42eb_archive_role_local_fixture", 120),
            ("profile_media_live_captures/r42ea_archive_role_refresh_live_spool", 50),
            ("profile_media_live_captures/r42dz_archive_role_refresh_dispatch_no_gui", 50),
            ("profile_media_live_captures/r42dy_archive_role_paint_no_gui", 50),
            ("profile_media_live_captures/r42dx_cmdline_archive_role_payload", 50),
        ]:
            for p in recent_files(ROOT / base_rel, limit):
                if p.suffix.lower() not in {".json", ".jsonl", ".html", ".log", ".txt", ".md"}:
                    continue
                arc = "_runtime/" + p.relative_to(ROOT).as_posix()
                zf.write(p, arc)
                included += 1
        log = ROOT / "profile_media_live_captures/link_source_role_webview_overlay/selected_link_source_role_native_webview2_launch.log"
        if log.is_file():
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-1200:]
            tmp = OUT_BASE / "_r42ec_native_launch_tail.log"
            tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
            zf.write(tmp, "_runtime/selected_link_source_role_native_webview2_launch_tail.log")
            included += 1
        manifest["included_count"] = included
        manifest_path = OUT_BASE / "r42ec_debug_upload_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        zf.write(manifest_path, "r42ec_debug_upload_manifest.json")
        included += 1
    downloads = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
    if downloads.exists():
        dest = downloads / zip_path.name
        shutil.copy2(zip_path, dest)
        print("[DONE] Copied ZIP to Downloads:", dest)
    print("[DONE] Created ZIP:", zip_path)
    print("[DONE] Files included:", included)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
