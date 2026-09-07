from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42dw_archive_role_payload"
OUTROOT.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
stage = OUTROOT / ("active_debug_" + stamp)
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True)
manifest=[]

def copy_file(src: Path, rel: str, reason: str, max_bytes: int = 12_000_000) -> None:
    try:
        if not src.is_file() or src.stat().st_size > max_bytes:
            return
        dst = stage / rel.replace("\\", "/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest.append({"reason": reason, "path": rel.replace("\\", "/"), "bytes": src.stat().st_size})
    except OSError:
        return

include_files = [
    "main.py",
    "profile_media_archive_role_payload_r42dw.py",
    "profile_media_archive_source_role_surface_r42ds.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "profile_media_archive_material_chain_r42ct.py",
    "R42DW_ARCHIVE_ROLE_PAYLOAD_AFTER_MATERIAL_NOTES_20260907.md",
    r"tools\webview2_source_role_editor_native\Program.cs",
    r"tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj",
    r"tools\webview2_source_role_editor_native\probe_r42dw_archive_role_payload_from_latest.py",
    r"tools\webview2_source_role_editor_native\launch_r42dw_native_overlay_from_latest.py",
    r"tools\webview2_source_role_editor_native\probe_r42dw_native_role_overlay_log.py",
]
for rel in include_files:
    copy_file(ROOT / rel, rel, "source")

runtime_roots = [
    r"profile_media_live_captures\link_source_role_webview_overlay",
    r"profile_media_live_captures\r42ct_archive_source_material",
    r"profile_media_live_captures\r42ds_archive_source_roles_webview2",
    r"profile_media_live_captures\r42du_archive_visible_material_source_roles",
    r"profile_media_live_captures\r42dv_native_role_paint_js_fix",
    r"profile_media_live_captures\r42dw_archive_role_payload",
]
allowed_ext = {".json",".jsonl",".txt",".log",".csv",".md",".html"}
for relroot in runtime_roots:
    base = ROOT / relroot
    if not base.exists():
        continue
    candidates=[]
    for parent, dirs, fnames in os.walk(base):
        path=Path(parent)
        try:
            depth=len(path.relative_to(base).parts)
        except ValueError:
            depth=0
        if depth > 4:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in {".git","node_modules","__pycache__","webview2_user_data","Cache","Code Cache","GPUCache"} and not d.startswith("bundle_") and not d.startswith("active_debug_")]
        for name in fnames:
            p=path/name
            try:
                if p.suffix.lower() in allowed_ext and p.stat().st_size <= 5_000_000:
                    candidates.append(p)
            except OSError:
                pass
    candidates.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for p in candidates[:180]:
        copy_file(p, "_runtime/" + p.relative_to(ROOT).as_posix(), "runtime-latest", max_bytes=5_000_000)

(stage / "r42dw_active_debug_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
zip_path = OUTROOT / f"r42dw_active_archive_role_payload_debug_upload_{stamp}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for p in stage.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(stage).as_posix())
downloads = Path.home() / "Downloads"
downloads.mkdir(parents=True, exist_ok=True)
copy_to = downloads / zip_path.name
shutil.copy2(zip_path, copy_to)
print("[DONE] Created ZIP:", zip_path)
print("[DONE] Copied ZIP to Downloads:", copy_to)
print("[DONE] Files included:", len(manifest))
