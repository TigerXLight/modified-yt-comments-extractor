from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[2]
out=root/'ytce_r42ex_real_capability_process_and_cog_fix_patch_20260909.zip'
files=['main.py','profile_media_file_converter_r42eh.py','R42EX_REAL_CAPABILITY_PROCESS_AND_COG_FIX_NOTES_20260909.md','tools/profile_media_file_converter/smoke_r42ex_real_capability_process_and_cog.cmd','tools/profile_media_file_converter/probe_r42ex_real_capability_alignment_no_gui.py','tools/profile_media_file_converter/probe_r42ex_real_capability_alignment_no_gui.cmd','tools/profile_media_file_converter/audit_r42ex_converter_real_capability_and_process_no_gui.py','tools/profile_media_file_converter/audit_r42ex_converter_real_capability_and_process_no_gui.cmd','tools/profile_media_file_converter/make_r42ex_real_capability_process_and_cog_debug_upload_zip.py','tools/profile_media_file_converter/make_r42ex_real_capability_process_and_cog_debug_upload_zip.cmd','tools/profile_media_file_converter/build_r42ex_real_capability_process_and_cog_zip.py','tools/profile_media_file_converter/build_r42ex_real_capability_process_and_cog_zip.cmd']
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        p=root/rel
        if p.exists(): z.write(p,'project/'+rel)
print(out)
