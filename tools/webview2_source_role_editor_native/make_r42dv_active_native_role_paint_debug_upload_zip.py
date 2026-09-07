from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json, os, shutil, zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42dv_native_role_paint_js_fix"
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
        dst = stage / rel.replace("\\","/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest.append({"reason": reason, "path": rel.replace("\\","/"), "bytes": src.stat().st_size})
    except OSError:
        return

include_files = [
    "main.py",
    "profile_media_archive_source_role_surface_r42ds.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "profile_media_archive_material_chain_r42ct.py",
    "profile_media_native_role_paint_js_r42dv_test.py",
    "R42DV_NATIVE_ROLE_PAINT_JS_FIX_NOTES_20260907.md",
    r"tools\webview2_source_role_editor_native\Program.cs",
    r"tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj",
    r"tools\webview2_source_role_editor_native\probe_r42dv_native_role_paint_js_fix.py",
]
for rel in include_files:
    copy_file(ROOT/rel, rel, "source")

runtime_roots = [
    r"profile_media_live_captures\link_source_role_webview_overlay",
    r"profile_media_live_captures\r42ct_archive_source_material",
    r"profile_media_live_captures\r42ds_archive_source_roles_webview2",
    r"profile_media_live_captures\r42du_archive_visible_material_source_roles",
    r"profile_media_live_captures\r42dv_native_role_paint_js_fix",
]
allowed_ext = {".json",".jsonl",".txt",".log",".csv",".md",".html"}
for relroot in runtime_roots:
    base = ROOT / relroot
    if not base.exists():
        continue
    candidates = []
    for parent, dirs, fnames in os.walk(base):
        path = Path(parent)
        try:
            depth = len(path.relative_to(base).parts)
        except ValueError:
            depth = 0
        if depth > 4:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in {".git","node_modules","__pycache__","webview2_user_data","Cache","Code Cache","GPUCache"} and not d.startswith("bundle_") and not d.startswith("active_debug_")]
        for name in fnames:
            p = path / name
            try:
                if p.suffix.lower() in allowed_ext and p.stat().st_size <= 5_000_000:
                    candidates.append(p)
            except OSError:
                pass
    candidates.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for p in candidates[:140]:
        copy_file(p, "_runtime/" + p.relative_to(ROOT).as_posix(), "runtime-latest", max_bytes=5_000_000)

(stage/"r42dv_active_debug_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
zip_path = OUTROOT / f"r42dv_active_native_role_paint_debug_upload_{stamp}.zip"
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for p in stage.rglob("*"):
        if p.is_file():
            zf.write(p, p.relative_to(stage).as_posix())
downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads" / zip_path.name
shutil.copy2(zip_path, downloads)
print("[DONE] Created ZIP:", zip_path)
print("[DONE] Copied ZIP to Downloads:", downloads)
print("[DONE] Files included:", len(manifest))
