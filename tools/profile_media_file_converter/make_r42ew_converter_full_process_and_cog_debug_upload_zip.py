from __future__ import annotations
import zipfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
outdir=ROOT/'profile_media_live_captures'/'r42ew_converter_full_process_and_cog'
outdir.mkdir(parents=True, exist_ok=True)
out=outdir/('ytce_r42ew_converter_full_process_and_cog_debug_'+time.strftime('%Y%m%d_%H%M%S')+'.zip')
include=['main.py','profile_media_file_converter_r42eh.py','R42EW_CONVERTER_FULL_PROCESS_CAPABILITY_AND_COG_FIX_NOTES_20260909.md']
include += [str(p.relative_to(ROOT)) for p in (ROOT/'tools/profile_media_file_converter').glob('*r42ew*')]
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for rel in include:
        p=ROOT/rel
        if p.exists(): z.write(p, rel)
    for p in sorted((ROOT/'profile_media_live_captures').glob('r42ew_converter_full_process_audit_*.json'))[-3:]:
        z.write(p, 'audits/'+p.name)
print(out)
