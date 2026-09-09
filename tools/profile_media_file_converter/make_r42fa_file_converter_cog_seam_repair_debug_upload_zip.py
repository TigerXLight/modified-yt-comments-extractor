from __future__ import annotations
import zipfile, datetime, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out=ROOT/'profile_media_live_captures'/f'ytce_r42fa_file_converter_cog_seam_debug_upload_{stamp}.zip'
out.parent.mkdir(parents=True, exist_ok=True)
files=['main.py','profile_media_file_converter_r42eh.py','R42FA_FILE_CONVERTER_COG_SEAM_REPAIR_NOTES_20260909.md']
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        p=ROOT/rel
        if p.exists(): z.write(p, rel)
    for p in (ROOT/'tools'/'profile_media_file_converter').glob('*r42fa*'):
        z.write(p, str(p.relative_to(ROOT)))
    try:
        status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True,stderr=subprocess.STDOUT)
    except Exception as exc:
        status=repr(exc)
    z.writestr('git_status_short.txt', status)
print(out)
