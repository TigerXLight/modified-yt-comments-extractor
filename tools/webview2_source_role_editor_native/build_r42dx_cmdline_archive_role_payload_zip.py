from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42dx_cmdline_archive_role_payload"
OUTROOT.mkdir(parents=True, exist_ok=True)

INCLUDE_FILES = [
    "profile_media_archive_role_payload_r42dw.py",
    "profile_media_archive_role_payload_r42dw_test.py",
    "R42DX_CMDLINE_ARCHIVE_ROLE_PAYLOAD_NO_GUI_NOTES_20260907.md",
    "tools/webview2_source_role_editor_native/_r42dx_python.cmd",
    "tools/webview2_source_role_editor_native/_r42dw_python.cmd",
    "tools/webview2_source_role_editor_native/reset_r42dx_stuck_app_and_native_helper.cmd",
    "tools/webview2_source_role_editor_native/probe_r42dx_archive_role_payload_no_gui.cmd",
    "tools/webview2_source_role_editor_native/probe_r42dx_archive_role_payload_no_gui.py",
    "tools/webview2_source_role_editor_native/probe_r42dw_archive_role_payload_from_latest.py",
    "tools/webview2_source_role_editor_native/launch_r42dw_native_overlay_from_latest.py",
    "tools/webview2_source_role_editor_native/build_r42dx_cmdline_archive_role_payload_zip.cmd",
    "tools/webview2_source_role_editor_native/build_r42dx_cmdline_archive_role_payload_zip.py",
    "tools/webview2_source_role_editor_native/make_r42dx_cmdline_archive_role_payload_debug_upload_zip.cmd",
    "tools/webview2_source_role_editor_native/make_r42dx_cmdline_archive_role_payload_debug_upload_zip.py",
]


def add_file(zf: zipfile.ZipFile, src: Path, arc: str, manifest: list[dict]) -> None:
    if src.is_file():
        zf.write(src, arc)
        manifest.append({"path": arc, "bytes": src.stat().st_size})


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUTROOT / f"r42dx_cmdline_archive_role_payload_no_gui_{stamp}.zip"
    manifest: list[dict] = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE_FILES:
            add_file(zf, ROOT / rel, rel, manifest)
        # include latest command-line probe summaries, if present
        for p in sorted(OUTROOT.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            add_file(zf, p, "_r42dx_probe_outputs/" + p.name, manifest)
        zf.writestr("r42dx_bundle_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads" / zip_path.name
    try:
        shutil.copy2(zip_path, downloads)
        print("[DONE] Created ZIP:", zip_path)
        print("[DONE] Copied ZIP to Downloads:", downloads)
        print("[DONE] Files included:", len(manifest))
    except Exception as exc:
        print("[DONE] Created ZIP:", zip_path)
        print("[WARN] Could not copy to Downloads:", repr(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
