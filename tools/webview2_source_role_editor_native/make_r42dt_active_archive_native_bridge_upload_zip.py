from __future__ import annotations

import json
import os
import shutil
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "profile_media_live_captures" / "r42dt_archive_native_webview2_bridge"
STAMP = time.strftime("%Y%m%d_%H%M%S")
STAGE = OUT_ROOT / ("active_source_stage_" + STAMP)
ZIP_PATH = OUT_ROOT / ("r42dt_active_archive_native_webview2_bridge_source_upload_" + STAMP + ".zip")

INCLUDE = [
    "main.py",
    "source_adapters.py",
    "source_resource_state.py",
    "profile_media_archive_material_chain_r42ct.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "profile_media_archive_source_role_surface_r42ds.py",
    "profile_media_normal_access_feature_receipts_r42dr.py",
    "profile_media_normal_access_provider_layer_r42dq.py",
    "profile_media_universal_worker_source_router_r42do.py",
    "profile_media_access_backend_router_r42ct.py",
    "profile_media_tor_camoufox_material_backend_r42ct.py",
    "profile_media_archive_native_webview2_bridge_r42dt_test.py",
    "R42DT_ARCHIVE_NATIVE_WEBVIEW2_BRIDGE_NOTES_20260907.md",
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
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True, exist_ok=True)
    for rel in INCLUDE:
        copy_rel(rel)
    for cap in [
        ROOT / "profile_media_live_captures" / "r42ct_archive_source_material",
        ROOT / "profile_media_live_captures" / "r42ds_archive_source_roles_webview2",
        ROOT / "profile_media_live_captures" / "r42dt_archive_native_webview2_bridge",
    ]:
        if cap.is_dir():
            latest = sorted([p for p in cap.iterdir() if p.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)[:3]
            for folder in latest:
                dstroot = STAGE / "_latest_runtime_state" / cap.name / folder.name
                for item in folder.rglob("*"):
                    if item.is_file() and item.stat().st_size <= 5_000_000:
                        target = dstroot / item.relative_to(folder)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target)
    manifest = {
        "schema": "ytce.r42dt.active_archive_native_webview2_bridge_source_upload.v1",
        "created_at_local": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "single_source_for_app_test": "https://archive.ph/6mr3C",
        "included_files": INCLUDE,
    }
    (STAGE / "r42dt_active_upload_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
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
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
