from __future__ import annotations
import json, os, sys
from pathlib import Path
from datetime import datetime

TARGET='https://archive.ph/6mr3C'
ROOT=Path.cwd()

def read_text(p: Path) -> str:
    try: return p.read_text(encoding='utf-8-sig', errors='replace')
    except Exception as e: return f'<READ_ERROR {type(e).__name__}: {e}>'

def main() -> int:
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    out=Path.home()/'Downloads'/f'r42cp_archive_material_audit_{stamp}.txt'
    lines=[]
    lines.append('===== R42CP ARCHIVE MATERIAL AUDIT =====')
    lines.append(f'Root: {ROOT}')
    lines.append(f'Target: {TARGET}')
    lines.append(f'LOCALAPPDATA: {os.environ.get("LOCALAPPDATA","")}')
    check_dirs=[
        ROOT/'profile_media_live_captures'/'r42cp_archive_source_material',
        ROOT/'profile_media_live_captures'/'r42cm_alt_clean_localappdata'/'YTCE'/'profile_media_generic_website_live_captures',
        ROOT/'profile_media_live_captures'/'link_source_role_webview_overlay',
    ]
    for d in check_dirs:
        lines.append('')
        lines.append(f'--- DIR {d} exists={d.exists()}')
        if not d.exists(): continue
        files=list(d.rglob('*'))[:5000]
        hits=[]
        for p in files:
            if not p.is_file(): continue
            s=str(p).lower()
            if any(x in s for x in ['archive','6mr3c','source_role','capture_summary','article_text']):
                txt=''
                if p.suffix.lower() in ['.txt','.json','.log','.html','.htm'] and p.stat().st_size < 5_000_000:
                    t=read_text(p)
                    if 'archive.ph/6mr3c' in t.lower() or 'seagull eater' in t.lower() or 'browser_capture_failed' in t.lower() or 'archive_material' in t.lower():
                        txt=t[:1200].replace('\n',' ') 
                hits.append((p, p.stat().st_size, txt))
        lines.append(f'hit_file_count={len(hits)}')
        for p, size, txt in hits[:80]:
            lines.append(f'FILE {p} size={size}')
            if txt: lines.append(f'  SNIP {txt[:1000]}')
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote: {out}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
