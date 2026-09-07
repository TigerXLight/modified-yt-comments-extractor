from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sqlite3
import sys
import zipfile
from datetime import datetime, timedelta

TARGET_ARCHIVE = 'https://archive.ph/6mr3C'
TARGET_ARCHIVE_LOWER = TARGET_ARCHIVE.lower()
NEEDLES = [
    'archive.ph/6mr3c',
    'https://archive.ph/6mr3c',
    'browser_capture_failed',
    'playwright browser capture failed',
    'generic website live capture did not complete',
    'people shout "seagull eater"',
    'seagull eater',
    'muslim woman who far right painted',
]
TEXT_EXTS = {'.txt', '.json', '.jsonl', '.log', '.html', '.htm', '.md', '.csv', '.tsv', '.xml', '.yml', '.yaml'}


def read_text(path: pathlib.Path, limit: int = 80_000_000) -> str | None:
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > limit:
            return None
        return path.read_text(encoding='utf-8-sig', errors='replace')
    except Exception:
        try:
            return path.read_text(encoding='utf-16', errors='replace')
        except Exception:
            return None


def parse_dt(s: str) -> datetime:
    if not s:
        return datetime.now().astimezone() - timedelta(hours=4)
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone()
    except Exception:
        return datetime.now().astimezone() - timedelta(hours=4)


def safe_json(path: pathlib.Path) -> dict:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def rel(root: pathlib.Path, p: pathlib.Path) -> str:
    try:
        return str(p.relative_to(root))
    except Exception:
        return str(p)


def interesting_recent_files(base: pathlib.Path, since: datetime):
    if not base.exists():
        return
    for p in sorted(base.rglob('*')):
        try:
            if not p.is_file():
                continue
            st = p.stat()
            mtime = datetime.fromtimestamp(st.st_mtime).astimezone()
            if mtime < since:
                continue
            if p.suffix.lower() and p.suffix.lower() not in TEXT_EXTS:
                continue
            if st.st_size > 80_000_000:
                continue
            yield p, st, mtime
        except Exception:
            continue


def main() -> int:
    ap = argparse.ArgumentParser(description='R42CN deep audit for archive.ph material test failure.')
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--make-zip', default='')
    ns = ap.parse_args()
    root = pathlib.Path(ns.root).resolve()
    out = pathlib.Path(ns.out)
    base = root / 'profile_media_live_captures'
    marker_paths = [
        base / 'r42cm_hard_clean_archive_material_test_start.json',
        base / 'r42cl_clean_archive_material_test_start.json',
    ]
    marker_used = None
    marker_data = {}
    for marker in marker_paths:
        if marker.exists():
            marker_used = marker
            marker_data = safe_json(marker)
            break
    since = parse_dt(str(marker_data.get('started_at', '') if marker_data else ''))
    if marker_used is None:
        since = datetime.now().astimezone() - timedelta(hours=4)

    lines: list[str] = []
    add = lines.append
    add('===== R42CN ARCHIVE MATERIAL FAILURE AUDIT =====')
    add(f'Root: {root}')
    add(f'Target archive URL: {TARGET_ARCHIVE}')
    add(f'Marker: {marker_used if marker_used else "MISSING - using last 4 hours"}')
    add(f'Since: {since.isoformat()}')
    add('')
    add('===== CLEAN PROFILE CHECK =====')
    udf = pathlib.Path(os.environ.get('LOCALAPPDATA', '')) / 'YTCE' / 'WebView2SourceRoleEditor'
    add(f'LOCALAPPDATA: {os.environ.get("LOCALAPPDATA", "")}')
    add(f'WebView2 UDF exists: {udf.exists()} :: {udf}')
    if marker_data:
        add('Marker JSON: ' + json.dumps(marker_data, ensure_ascii=False, sort_keys=True))
    add('')

    expected = [
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_overlay.json',
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_overlay_changes.jsonl',
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_roleplan.sqlite',
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_roleplan_summary.json',
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_native_webview2_launch.log',
    ]
    add('===== EXPECTED CURRENT SOURCE-ROLE / NATIVE DEBUG FILES =====')
    missing_expected = 0
    for p in expected:
        try:
            if p.exists():
                st = p.stat()
                add(f'PRESENT {rel(root,p)} size={st.st_size} mtime={datetime.fromtimestamp(st.st_mtime).astimezone().isoformat()}')
            else:
                missing_expected += 1
                add(f'MISSING {rel(root,p)}')
        except Exception as e:
            add(f'ERROR {rel(root,p)} :: {type(e).__name__}: {e}')
    add('')

    add('===== ACTIVITY / FAILURE NEEDLE HITS SINCE MARKER =====')
    hit_files: list[pathlib.Path] = []
    hit_count = 0
    for p, st, mtime in interesting_recent_files(base, since):
        txt = read_text(p)
        if not txt:
            continue
        low = txt.lower()
        hits = [n for n in NEEDLES if n in low]
        if not hits:
            continue
        hit_files.append(p)
        hit_count += 1
        add(f'--- FILE {rel(root,p)} size={st.st_size} mtime={mtime.isoformat()} hits={hits}')
        shown = 0
        for i, line in enumerate(txt.splitlines(), 1):
            ll = line.lower()
            if any(n in ll for n in NEEDLES):
                add(f'    L{i}: {line[:1000]}')
                shown += 1
                if shown >= 18:
                    break
    add(f'Hit files: {hit_count}')
    add('')

    add('===== LIVE CAPTURE DIRECTORIES SINCE MARKER =====')
    r40d = base / 'r40d_external_live_article'
    fresh_archive_dirs = []
    fresh_other_dirs = []
    if r40d.exists():
        for d in sorted(r40d.rglob('*')):
            try:
                if not d.is_dir():
                    continue
                st = d.stat()
                mtime = datetime.fromtimestamp(st.st_mtime).astimezone()
                if mtime < since:
                    continue
                name = str(d).lower()
                if 'archive' in name or 'seagull' in name or 'metro.co.uk' in name or 'web.archive.org' in name:
                    fresh_other_dirs.append(d)
                    if 'archive.ph' in name or 'archive.ph_6mr3c' in name or '6mr3c' in name:
                        fresh_archive_dirs.append(d)
            except Exception:
                continue
    add(f'Fresh matching live capture dirs: {len(fresh_other_dirs)}')
    add(f'Fresh archive.ph/6Mr3C dirs: {len(fresh_archive_dirs)}')
    for d in fresh_other_dirs[:80]:
        add(f'    DIR {rel(root,d)}')
    add('')

    add('===== SQLITE CURRENT ROLEPLAN CHECK =====')
    db = base / 'link_source_role_webview_overlay' / 'selected_link_source_role_roleplan.sqlite'
    if not db.exists():
        add('ROLEPLAN_DB_MISSING')
    else:
        try:
            con = sqlite3.connect(str(db))
            cur = con.cursor()
            tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name")]
            add('Tables: ' + ', '.join(tables))
            for table in tables:
                try:
                    cols = [r[1] for r in cur.execute(f'pragma table_info({table})')]
                    probe_cols = [c for c in cols if any(k in c.lower() for k in ('url', 'text', 'role', 'source', 'title'))]
                    if not probe_cols:
                        continue
                    where = []
                    params = []
                    for c in probe_cols:
                        where.append(f'lower(cast({c} as text)) like ?')
                        params.append('%archive.ph/6mr3c%')
                        where.append(f'lower(cast({c} as text)) like ?')
                        params.append('%seagull eater%')
                    select_cols = probe_cols[:8] or cols[:8]
                    q = f"select {', '.join(select_cols)} from {table} where {' or '.join(where)} limit 30"
                    rows = list(cur.execute(q, params))
                    if rows:
                        add(f'--- TABLE {table} matching rows={len(rows)} cols={select_cols}')
                        for row in rows[:12]:
                            add('    ' + repr(tuple((str(x)[:260] if x is not None else None) for x in row)))
                except Exception as e:
                    add(f'Query error table={table}: {type(e).__name__}: {e}')
            con.close()
        except Exception as e:
            add(f'SQLite error: {type(e).__name__}: {e}')
    add('')

    add('===== DIAGNOSIS RULES =====')
    if missing_expected >= 3:
        add('LIKELY_FAIL: source-role overlay/roleplan files are missing from current run, so the edit/native source-role worker did not produce current source-role artifacts.')
    if not fresh_archive_dirs:
        add('LIKELY_FAIL: no fresh archive.ph/6Mr3C live-capture directory exists after the clean marker.')
    add('PASS would require fresh post-marker archive.ph/6Mr3C material/artifacts, not only Metro/Wayback text or old moved captures.')
    add('If browser_capture_failed appears, the current Go path is still failing before it extracts archive.ph material.')

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Audit text written: {out}')
    for line in lines[:120]:
        print(line)
    if len(lines) > 120:
        print('... full audit written to file ...')

    if ns.make_zip:
        zip_path = pathlib.Path(ns.make_zip)
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.write(out, arcname=out.name)
            for p in expected:
                if p.exists() and p.is_file():
                    z.write(p, arcname=rel(root, p))
            for p in hit_files[:150]:
                try:
                    if p.exists() and p.is_file() and p.stat().st_size <= 80_000_000:
                        z.write(p, arcname=rel(root, p))
                except Exception:
                    pass
        print(f'Deep audit ZIP written: {zip_path}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
