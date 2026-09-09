from pathlib import Path
import shutil, time, zipfile
root=Path(__file__).resolve().parents[2]
stamp=time.strftime('%Y%m%d_%H%M%S')
out=root/'profile_media_live_captures'/'r42ex_real_capability_process_and_cog'/f'ytce_r42ex_real_capability_process_and_cog_debug_{stamp}.zip'
out.parent.mkdir(parents=True, exist_ok=True)
files=['main.py','profile_media_file_converter_r42eh.py','R42EX_REAL_CAPABILITY_PROCESS_AND_COG_FIX_NOTES_20260909.md','tools/profile_media_file_converter/audit_r42ex_converter_real_capability_and_process_no_gui.py','tools/profile_media_file_converter/probe_r42ex_real_capability_alignment_no_gui.py']
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        p=root/rel
        if p.exists(): z.write(p, rel)
print(out)
