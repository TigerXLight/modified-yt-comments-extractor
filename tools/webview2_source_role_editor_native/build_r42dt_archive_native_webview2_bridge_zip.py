from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "profile_media_live_captures" / "r42dt_archive_native_webview2_bridge"
STAMP = time.strftime("%Y%m%d_%H%M%S")
STAGE = OUT_ROOT / ("zip_stage_" + STAMP)
ZIP_PATH = OUT_ROOT / ("r42dt_archive_native_webview2_bridge_" + STAMP + ".zip")

INCLUDE = [
    "profile_media_archive_material_chain_r42ct.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "profile_media_archive_native_webview2_bridge_r42dt_test.py",
    "R42DT_ARCHIVE_NATIVE_WEBVIEW2_BRIDGE_NOTES_20260907.md",
    "tools/webview2_source_role_editor_native/_r42dt_python.cmd",
    "tools/webview2_source_role_editor_native/smoke_r42dt_archive_native_webview2_bridge.cmd",
    "tools/webview2_source_role_editor_native/probe_r42dt_archive_native_webview2_bridge.cmd",
    "tools/webview2_source_role_editor_native/probe_r42dt_archive_native_webview2_bridge.py",
    "tools/webview2_source_role_editor_native/launch_r42dt_archive_only_app_test.cmd",
    "tools/webview2_source_role_editor_native/build_r42dt_archive_native_webview2_bridge_zip.cmd",
    "tools/webview2_source_role_editor_native/build_r42dt_archive_native_webview2_bridge_zip.py",
    "tools/webview2_source_role_editor_native/make_r42dt_active_archive_native_bridge_upload_zip.cmd",
    "tools/webview2_source_role_editor_native/make_r42dt_active_archive_native_bridge_upload_zip.py",
]

def copy_rel(rel: str) -> None:
    src = ROOT / rel
    if not src.is_file():
        return
    dst = STAGE / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        [str(ROOT / "tools" / "webview2_source_role_editor_native" / "_r42dt_python.cmd"),
         str(ROOT / "tools" / "webview2_source_role_editor_native" / "probe_r42dt_archive_native_webview2_bridge.py")],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True, exist_ok=True)
    for rel in INCLUDE:
        copy_rel(rel)
    (STAGE / "_r42dt_build_probe_stdout.txt").write_text(probe.stdout or "", encoding="utf-8", errors="replace")
    latest_probe = None
    for p in sorted(OUT_ROOT.glob("probe_*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_dir():
            latest_probe = p
            break
    if latest_probe:
        dstroot = STAGE / "_latest_probe_output" / latest_probe.name
        for item in latest_probe.rglob("*"):
            if item.is_file() and item.stat().st_size <= 2_000_000:
                rel = item.relative_to(latest_probe)
                target = dstroot / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
    manifest = {
        "schema": "ytce.r42dt.archive_native_webview2_bridge_zip_manifest.v1",
        "created_at_local": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "single_source_for_app_test": "https://archive.ph/6mr3C",
        "probe_returncode": probe.returncode,
        "included_files": INCLUDE,
    }
    (STAGE / "r42dt_archive_native_webview2_bridge_zip_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(STAGE.rglob("*")):
            if item.is_file():
                zf.write(item, item.relative_to(STAGE).as_posix())
    downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads" / ZIP_PATH.name
    try:
        shutil.copy2(ZIP_PATH, downloads)
        print("[DONE] Copied ZIP to Downloads:", downloads)
    except Exception as exc:
        print("[WARN] Could not copy ZIP to Downloads:", exc)
    print("[DONE] Created ZIP:", ZIP_PATH)
    return probe.returncode

if __name__ == "__main__":
    raise SystemExit(main())
