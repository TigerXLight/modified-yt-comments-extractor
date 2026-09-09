from __future__ import annotations
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ytce_r42ev_converter_runtime_testing_and_cog_default_fix_patch_20260909.zip'
stage = ROOT / 'profile_media_live_captures' / 'r42ev_build_stage'
if stage.exists(): shutil.rmtree(stage)
proj = stage / 'project'
files = ['main.py','profile_media_file_converter_r42eh.py','R42EV_CONVERTER_RUNTIME_TESTING_AND_COG_DEFAULT_FIX_NOTES_20260909.md','tools/profile_media_file_converter/smoke_r42ev_converter_runtime_testing_and_cog_default_fix.cmd','tools/profile_media_file_converter/probe_r42ev_converter_runtime_testing_and_cog_default_fix_no_gui.py','tools/profile_media_file_converter/probe_r42ev_converter_runtime_testing_and_cog_default_fix_no_gui.cmd','tools/profile_media_file_converter/audit_r42ev_converter_processes_efficiency_no_gui.py','tools/profile_media_file_converter/audit_r42ev_converter_processes_efficiency_no_gui.cmd','tools/profile_media_file_converter/make_r42ev_converter_runtime_testing_and_cog_default_fix_debug_upload_zip.py','tools/profile_media_file_converter/make_r42ev_converter_runtime_testing_and_cog_default_fix_debug_upload_zip.cmd','tools/profile_media_file_converter/build_r42ev_converter_runtime_testing_and_cog_default_fix_zip.py','tools/profile_media_file_converter/build_r42ev_converter_runtime_testing_and_cog_default_fix_zip.cmd']
for rel in files:
    src=ROOT/rel
    if src.exists():
        dst=proj/rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst)
if OUT.exists(): OUT.unlink()
shutil.make_archive(str(OUT.with_suffix('')), 'zip', stage)
print(OUT)
