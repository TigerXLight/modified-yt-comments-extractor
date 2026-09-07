from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import os
import zipfile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42dz_archive_role_refresh_dispatch_no_gui"


def _run_probe() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (";" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    subprocess.run([
        sys.executable,
        str(ROOT / "profile_media_archive_role_refresh_dispatch_r42dz.py"),
        "https://archive.ph/6mr3C",
        "--root",
        str(ROOT),
    ], cwd=str(ROOT), env=env, check=False)


def _add(zf: zipfile.ZipFile, path: Path, arc: str) -> None:
    if path.is_file():
        zf.write(path, arc)


def main() -> int:
    OUTROOT.mkdir(parents=True, exist_ok=True)
    _run_probe()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUTROOT / ("r42dz_archive_role_refresh_dispatch_no_gui_" + stamp + ".zip")
    included = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        rels = [
            "profile_media_archive_role_refresh_dispatch_r42dz.py",
            "profile_media_archive_role_refresh_dispatch_r42dz_test.py",
            "profile_media_archive_role_payload_r42dw.py",
            "profile_media_archive_role_payload_cmd_replay_r42dy.py",
            "R42DZ_CMDLINE_ARCHIVE_ROLE_REFRESH_DISPATCH_NO_GUI_NOTES_20260907.md",
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
        ]
        for rel in rels:
            p = ROOT / rel
            if p.is_file():
                zf.write(p, rel)
                included.append(rel)
        latest = []
        for base_rel in [
            "profile_media_live_captures/r42dz_archive_role_refresh_dispatch_no_gui",
            "profile_media_live_captures/r42dy_archive_role_paint_no_gui",
        ]:
            base = ROOT / base_rel
            if base.exists():
                files = [p for p in base.rglob("*") if p.is_file() and p.stat().st_size <= 2_000_000]
                files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                latest.extend(files[:40])
        for p in latest:
            try:
                arc = "_runtime/" + str(p.relative_to(ROOT)).replace("\\", "/")
                zf.write(p, arc)
                included.append(arc)
            except Exception:
                pass
        manifest = {
            "schema": "ytce.r42dz.reference_zip_manifest.v1",
            "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
            "zip_path": str(zip_path),
            "files_included": len(included),
            "no_gui": True,
            "no_network": True,
            "source_url": "https://archive.ph/6mr3C",
        }
        zf.writestr("r42dz_reference_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
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
