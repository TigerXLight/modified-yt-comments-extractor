from __future__ import annotations
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT.parent/'ytce_r42fa_file_converter_cog_seam_repair_patch_20260909.zip'
include=['main.py','R42FA_FILE_CONVERTER_COG_SEAM_REPAIR_NOTES_20260909.md']
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for rel in include:
        p=ROOT/rel
        if p.exists(): z.write(p, f'project/{rel}')
    for p in (ROOT/'tools'/'profile_media_file_converter').glob('*r42fa*'):
        z.write(p, 'project/'+str(p.relative_to(ROOT)).replace('\\','/'))
print(out)
