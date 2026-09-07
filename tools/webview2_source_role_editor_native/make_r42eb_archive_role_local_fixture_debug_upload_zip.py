from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT_BASE = ROOT / "profile_media_live_captures" / "r42eb_archive_role_local_fixture"
OUT_BASE.mkdir(parents=True, exist_ok=True)

INCLUDE_FILES = [
    "main.py",
    "profile_media_archive_role_local_fixture_r42eb.py",
    "profile_media_archive_role_local_fixture_r42eb_test.py",
    "profile_media_archive_role_payload_r42dw.py",
    "profile_media_archive_role_refresh_live_spool_r42ea.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "R42EB_ARCHIVE_ROLE_LOCAL_FIXTURE_URL_GUARD_NOTES_20260907.md",
    "tools/webview2_source_role_editor_native/Program.cs",
    "tools/webview2_source_role_editor_native/YTCE.NativeSourceRoleEditor.csproj",
    "tools/webview2_source_role_editor_native/_r42eb_python.cmd",
    "tools/webview2_source_role_editor_native/reset_r42eb_stuck_app_native_helper.cmd",
    "tools/webview2_source_role_editor_native/smoke_r42eb_archive_role_local_fixture_url_guard.cmd",
    "tools/webview2_source_role_editor_native/probe_r42eb_archive_role_local_fixture_no_gui.cmd",
    "tools/webview2_source_role_editor_native/probe_r42eb_archive_role_local_fixture_no_gui_recolor.cmd",
    "tools/webview2_source_role_editor_native/launch_r42eb_cached_archive_role_fixture_native.cmd",
    "tools/webview2_source_role_editor_native/launch_r42eb_cached_archive_role_fixture_native_recolor.cmd",
    "tools/webview2_source_role_editor_native/probe_r42eb_native_log_after_local_fixture.cmd",
    "tools/webview2_source_role_editor_native/make_r42eb_archive_role_local_fixture_debug_upload_zip.py",
    "tools/webview2_source_role_editor_native/make_r42eb_archive_role_local_fixture_debug_upload_zip.cmd",
]

def add_if_exists(zf: zipfile.ZipFile, path: Path, arc: str, added: set[str]) -> None:
    if not path.exists() or arc in added:
        return
    zf.write(path, arc)
    added.add(arc)

def main() -> int:
    # Build a fresh no-GUI probe first, but do not fail the upload if no cached surface exists.
    try:
        import sys
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from profile_media_archive_role_local_fixture_r42eb import build_no_gui_probe
        print(json.dumps(build_no_gui_probe(project_root=ROOT, source_url="https://archive.ph/6mr3C"), ensure_ascii=False, indent=2))
    except Exception as exc:
        print("[WARN] R42EB no-GUI probe before upload failed:", repr(exc))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUT_BASE / f"r42eb_archive_role_local_fixture_debug_upload_{stamp}.zip"
    added: set[str] = set()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE_FILES:
            add_if_exists(zf, ROOT / rel, rel, added)

        # bounded runtime materials
        runtime_roots = [
            ROOT / "profile_media_live_captures" / "r42eb_archive_role_local_fixture",
            ROOT / "profile_media_live_captures" / "r42ea_archive_role_refresh_live_spool",
            ROOT / "profile_media_live_captures" / "r42dz_archive_role_refresh_dispatch_no_gui",
            ROOT / "profile_media_live_captures" / "r42dy_archive_role_paint_no_gui",
            ROOT / "profile_media_live_captures" / "r42dx_cmdline_archive_role_payload",
        ]
        allowed_suffixes = {".json", ".jsonl", ".md", ".txt", ".html", ".log", ".cmd", ".py"}
        for base in runtime_roots:
            if not base.exists():
                continue
            files = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in allowed_suffixes]
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for p in files[:80]:
                rel = "_runtime/" + p.relative_to(ROOT).as_posix()
                add_if_exists(zf, p, rel, added)

        log = ROOT / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_native_webview2_launch.log"
        if log.exists():
            # Include a bounded tail copy rather than the whole growing log.
            tail_dir = OUT_BASE / "_upload_log_tail"
            tail_dir.mkdir(exist_ok=True)
            tail = tail_dir / "selected_link_source_role_native_webview2_launch_tail.log"
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-800:]
            tail.write_text("\n".join(lines) + "\n", encoding="utf-8")
            add_if_exists(zf, tail, "_runtime/selected_link_source_role_native_webview2_launch_tail.log", added)

        manifest = {"created_at_local": datetime.now().isoformat(timespec="seconds"), "files_included": len(added), "zip_path": str(zip_path)}
        manifest_path = OUT_BASE / "r42eb_debug_upload_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        add_if_exists(zf, manifest_path, "r42eb_debug_upload_manifest.json", added)

    downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads" / zip_path.name
    try:
        downloads.write_bytes(zip_path.read_bytes())
        print("[DONE] Copied ZIP to Downloads:", downloads)
    except Exception as exc:
        print("[WARN] Could not copy to Downloads:", repr(exc))
    print("[DONE] Created ZIP:", zip_path)
    print("[DONE] Files included:", len(added))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
