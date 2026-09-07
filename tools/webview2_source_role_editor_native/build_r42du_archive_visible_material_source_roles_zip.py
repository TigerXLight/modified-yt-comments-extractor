from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json, os, shutil, zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42du_archive_visible_material_source_roles"
OUTROOT.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
stage = OUTROOT / ("bundle_" + stamp)
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True)
files = [
    "profile_media_archive_source_role_surface_r42ds.py",
    "profile_media_link_source_real_webview_overlay_v83d.py",
    "profile_media_archive_material_chain_r42ct.py",
    "profile_media_archive_material_visible_roles_r42du_test.py",
    "R42DU_ARCHIVE_VISIBLE_MATERIAL_SOURCE_ROLES_NOTES_20260907.md",
    r"tools\webview2_source_role_editor_native\Program.cs",
    r"tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj",
    r"tools\webview2_source_role_editor_native\_r42du_python.cmd",
    r"tools\webview2_source_role_editor_native\smoke_r42du_archive_visible_material_source_roles.cmd",
    r"tools\webview2_source_role_editor_native\probe_r42du_archive_visible_material_source_roles.cmd",
    r"tools\webview2_source_role_editor_native\probe_r42du_archive_visible_material_source_roles.py",
    r"tools\webview2_source_role_editor_native\launch_r42du_archive_only_app_test.cmd",
    r"tools\webview2_source_role_editor_native\launch_r42du_archive_only_app_test_recolor.cmd",
    r"tools\webview2_source_role_editor_native\build_r42du_archive_visible_material_source_roles_zip.cmd",
    r"tools\webview2_source_role_editor_native\build_r42du_archive_visible_material_source_roles_zip.py",
    r"tools\webview2_source_role_editor_native\make_r42du_active_archive_material_debug_upload_zip.cmd",
    r"tools\webview2_source_role_editor_native\make_r42du_active_archive_material_debug_upload_zip.py",
]
manifest=[]
for rel in files:
    src=ROOT/rel
    if not src.is_file():
        continue
    dst=stage/rel.replace("\\","/")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src,dst)
    manifest.append({"path":rel.replace("\\","/"),"bytes":src.stat().st_size})
for p in OUTROOT.glob("probe_*/*"):
    if p.is_file() and p.stat().st_size <= 2_000_000:
        dst=stage/"_r42du_probe_outputs"/p.parent.name/p.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p,dst)
        manifest.append({"path":str(dst.relative_to(stage)).replace("\\","/"),"bytes":p.stat().st_size})
(stage/"r42du_bundle_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
zip_path=OUTROOT/f"r42du_archive_visible_material_source_roles_{stamp}.zip"
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
