from __future__ import annotations
import shutil, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime('%Y%m%d_%H%M%S')
outdir = ROOT / 'profile_media_live_captures' / 'r42ev_converter_runtime_testing_and_cog_default_fix'
outdir.mkdir(parents=True, exist_ok=True)
name = f'ytce_r42ev_converter_runtime_testing_and_cog_default_fix_debug_{stamp}'
stage = outdir / name
if stage.exists(): shutil.rmtree(stage)
stage.mkdir(parents=True)
for rel in ['main.py','profile_media_file_converter_r42eh.py','R42EV_CONVERTER_RUNTIME_TESTING_AND_COG_DEFAULT_FIX_NOTES_20260909.md','tools/profile_media_file_converter']:
    p = ROOT / rel
    if p.is_dir(): shutil.copytree(p, stage / rel, dirs_exist_ok=True)
    elif p.exists():
        (stage / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, stage / rel)
for cmd,name2 in [(['git','status','--short'],'git_status_short.txt'),(['git','--no-pager','log','-8','--oneline','--decorate'],'git_log_8.txt'),(['git','--no-pager','diff','--stat'],'git_diff_stat.txt')]:
    try:
        r=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
        (stage/name2).write_text(r.stdout,encoding='utf-8')
    except Exception as exc: (stage/name2).write_text(repr(exc),encoding='utf-8')
archive = shutil.make_archive(str(outdir / name), 'zip', stage)
print(archive)
