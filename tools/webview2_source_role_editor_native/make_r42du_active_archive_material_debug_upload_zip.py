from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json, os, shutil, zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42du_archive_visible_material_source_roles"
OUTROOT.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
stage = OUTROOT / ("active_debug_" + stamp)
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True)
include_files = [
    "main.py",
    "profile_media_archive_source_role_surface_r42ds.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "profile_media_archive_material_chain_r42ct.py",
    "profile_media_access_backend_router_r42ct.py",
    "profile_media_tor_camoufox_material_backend_r42ct.py",
    "profile_media_normal_access_feature_receipts_r42dr.py",
    "profile_media_normal_access_provider_layer_r42dq.py",
    "profile_media_universal_worker_source_router_r42do.py",
    "profile_media_account_channel_worker_adapter_r42dp.py",
    "profile_media_normal_access_layer_r42dn.py",
    "profile_media_access_escalation_policy_r42dm.py",
    "source_adapters.py",
    "source_resource_state.py",
    "R42DU_ARCHIVE_VISIBLE_MATERIAL_SOURCE_ROLES_NOTES_20260907.md",
    r"tools\webview2_source_role_editor_native\Program.cs",
    r"tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj",
    r"tools\webview2_source_role_editor_native\probe_r42du_archive_visible_material_source_roles.py",
]
manifest=[]
def copy_file(src:Path, rel:str, reason:str):
    try:
        if not src.is_file() or src.stat().st_size > 12_000_000:
            return
        dst=stage/rel.replace("\\","/")
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        manifest.append({"reason":reason,"path":rel.replace("\\","/"),"bytes":src.stat().st_size})
    except OSError:
        return
for rel in include_files:
    copy_file(ROOT/rel, rel, "source")
for relroot in [
    r"profile_media_live_captures\link_source_role_webview_overlay",
    r"profile_media_live_captures\r42ct_archive_source_material",
    r"profile_media_live_captures\r42ds_archive_source_roles_webview2",
    r"profile_media_live_captures\r42dt_archive_native_webview2_bridge",
    r"profile_media_live_captures\r42du_archive_visible_material_source_roles",
]:
    base=ROOT/relroot
    if not base.exists():
        continue
    files=[]
    for parent, dirs, fnames in os.walk(base):
        path=Path(parent)
        try:
            depth=len(path.relative_to(base).parts)
        except ValueError:
            depth=0
        if depth>4:
            dirs[:]=[]
            continue
        dirs[:]=[d for d in dirs if d not in {".git","node_modules","__pycache__","webview2_user_data","Cache","Code Cache","GPUCache","r42du_archive_visible_material_source_roles"}]
        for name in fnames:
            p=path/name
            try:
                if p.stat().st_size<=5_000_000 and p.suffix.lower() in {".json",".jsonl",".txt",".log",".csv",".md",".html"}:
                    files.append(p)
            except OSError:
                pass
    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for p in files[:120]:
        copy_file(p, "_runtime/"+p.relative_to(ROOT).as_posix(), "runtime-latest")
(stage/"r42du_active_debug_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
zip_path=OUTROOT/f"r42du_active_archive_material_debug_upload_{stamp}.zip"
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as zf:
    for p in stage.rglob("*"):
        if p.is_file():
            zf.write(p,p.relative_to(stage).as_posix())
downloads=Path(os.environ.get("USERPROFILE",str(Path.home())))/"Downloads"/zip_path.name
shutil.copy2(zip_path,downloads)
print("[DONE] Created ZIP:", zip_path)
print("[DONE] Copied ZIP to Downloads:", downloads)
print("[DONE] Files included:", len(manifest))
