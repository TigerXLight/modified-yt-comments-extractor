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

FILES = [
    "profile_media_archive_role_local_fixture_r42eb.py",
    "profile_media_archive_role_local_fixture_r42eb_test.py",
    "profile_media_archive_role_closeout_r42ec.py",
    "profile_media_archive_role_closeout_r42ec_test.py",
    "R42EC_ARCHIVE_ROLE_CLOSEOUT_NO_GUI_NOTES_20260907.md",
    "tools/webview2_source_role_editor_native/Program.cs",
    "tools/webview2_source_role_editor_native/YTCE.NativeSourceRoleEditor.csproj",
    "tools/webview2_source_role_editor_native/_r42ec_python.cmd",
    "tools/webview2_source_role_editor_native/reset_r42ec_stuck_app_native_helper.cmd",
    "tools/webview2_source_role_editor_native/smoke_r42ec_archive_role_closeout_no_gui.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ec_archive_role_closeout_no_gui.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ec_archive_role_closeout_no_gui_recolor.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ec_native_log_after_local_fixture.cmd",
    "tools/webview2_source_role_editor_native/launch_r42ec_cached_archive_role_fixture_native.cmd",
    "tools/webview2_source_role_editor_native/launch_r42ec_cached_archive_role_fixture_native_recolor.cmd",
    "tools/webview2_source_role_editor_native/build_r42ec_archive_role_closeout_no_gui_zip.cmd",
    "tools/webview2_source_role_editor_native/build_r42ec_archive_role_closeout_no_gui_zip.py",
    "tools/webview2_source_role_editor_native/make_r42ec_archive_role_closeout_debug_upload_zip.cmd",
    "tools/webview2_source_role_editor_native/make_r42ec_archive_role_closeout_debug_upload_zip.py",
]

def add_file(zf: zipfile.ZipFile, path: Path, arc: str) -> None:
    if path.is_file():
        zf.write(path, arc)

def main() -> int:
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Generate a fresh no-GUI probe summary for reference.
    subprocess.run([sys.executable, "profile_media_archive_role_closeout_r42ec.py"], cwd=ROOT, check=False)
    zip_path = OUT_BASE / f"r42ec_archive_role_closeout_no_gui_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in FILES:
            add_file(zf, ROOT / rel, rel)
        # Bounded recent summaries only.
        for base_rel in [
            "profile_media_live_captures/r42ec_archive_role_closeout_no_gui",
            "profile_media_live_captures/r42eb_archive_role_local_fixture",
        ]:
            base = ROOT / base_rel
            if not base.exists():
                continue
            recent = sorted([p for p in base.rglob("*") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)[:80]
            for p in recent:
                if p.suffix.lower() in {".json", ".jsonl", ".html", ".log", ".txt"}:
                    zf.write(p, "_runtime/" + p.relative_to(ROOT).as_posix())
        log = ROOT / "profile_media_live_captures/link_source_role_webview_overlay/selected_link_source_role_native_webview2_launch.log"
        if log.is_file():
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-1000:]
            tmp = OUT_BASE / "_r42ec_native_launch_tail.log"
            tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
            zf.write(tmp, "_runtime/selected_link_source_role_native_webview2_launch_tail.log")
    downloads = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
    if downloads.exists():
        dest = downloads / zip_path.name
        shutil.copy2(zip_path, dest)
        print("[DONE] Copied ZIP to Downloads:", dest)
    print("[DONE] Created ZIP:", zip_path)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
