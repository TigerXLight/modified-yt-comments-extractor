from __future__ import annotations
import argparse, json, os, pathlib, sqlite3, sys
from datetime import datetime, timezone, timedelta

TARGETS = [
    'https://archive.ph/6mr3C',
    'archive.ph/6mr3C',
    'People shout "seagull eater"',
    'seagull eater',
    'Muslim woman who far right painted',
]
TEXT_SUFFIXES = {'.txt','.json','.jsonl','.html','.htm','.md','.log','.csv','.tsv','.xml'}


def parse_dt(s: str) -> datetime:
    if not s:
        return datetime.now().astimezone() - timedelta(hours=2)
    try:
        return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone()
    except Exception:
        return datetime.now().astimezone() - timedelta(hours=2)


def safe_read_text(path: pathlib.Path, limit: int = 20_000_000) -> str | None:
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    ns = ap.parse_args()
    root = pathlib.Path(ns.root)
    out = pathlib.Path(ns.out)
    base = root / 'profile_media_live_captures'
    marker = base / 'r42cm_hard_clean_archive_material_test_start.json'
    old_marker = base / 'r42cl_clean_archive_material_test_start.json'
    marker_data = {}
    if marker.exists():
        marker_data = json.loads(marker.read_text(encoding='utf-8', errors='replace'))
        since = parse_dt(str(marker_data.get('started_at','')))
        marker_used = str(marker)
    elif old_marker.exists():
        marker_data = json.loads(old_marker.read_text(encoding='utf-8', errors='replace'))
        since = parse_dt(str(marker_data.get('started_at','')))
        marker_used = str(old_marker) + ' (old R42CL marker)'
    else:
        since = datetime.now().astimezone() - timedelta(hours=2)
        marker_used = 'missing; default last 2 hours'

    lines: list[str] = []
    add = lines.append
    add('===== R42CM ARCHIVE MATERIAL CLEAN TEST AUDIT =====')
    add(f'Root: {root}')
    add(f'Marker: {marker_used}')
    add(f'Since: {since.isoformat()}')
    add('Target: https://archive.ph/6mr3C')
    add('')
    add('===== CLEANNESS CHECK =====')
    udf = pathlib.Path(os.environ.get('LOCALAPPDATA','')) / 'YTCE' / 'WebView2SourceRoleEditor'
    add(f'WebView2 UDF exists now: {udf.exists()} :: {udf}')
    if marker_data:
        add('Marker data: ' + json.dumps(marker_data, ensure_ascii=False, sort_keys=True))
    add('')

    wanted = [
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_overlay.json',
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_overlay_changes.jsonl',
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_roleplan.sqlite',
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_roleplan_summary.json',
        base / 'link_source_role_webview_overlay' / 'selected_link_source_role_native_webview2_launch.log',
    ]
    add('===== EXPECTED CURRENT DEBUG FILES =====')
    for p in wanted:
        if p.exists():
            st = p.stat()
            add(f'PRESENT {p} size={st.st_size} mtime={datetime.fromtimestamp(st.st_mtime).astimezone().isoformat()}')
        else:
            add(f'MISSING {p}')
    add('')

    add('===== RECENT FILES CONTAINING TARGET URL/TITLE =====')
    recent_hits = 0
    if base.exists():
        for p in sorted(base.rglob('*')):
            try:
                if not p.is_file():
                    continue
                st = p.stat()
                mtime = datetime.fromtimestamp(st.st_mtime).astimezone()
                if mtime < since:
                    continue
                if st.st_size > 50_000_000:
                    continue
                if p.suffix.lower() and p.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                txt = safe_read_text(p)
                if txt is None:
                    continue
                matches = []
                low = txt.lower()
                for t in TARGETS:
                    if t.lower() in low:
                        matches.append(t)
                if not matches:
                    continue
                recent_hits += 1
                add(f'--- FILE: {p}')
                add(f'    LastWriteTime: {mtime.isoformat()} Size: {st.st_size} Matches: {matches}')
                # First matching lines only.
                count = 0
                for i, line in enumerate(txt.splitlines(), 1):
                    if any(t.lower() in line.lower() for t in TARGETS):
                        add(f'    L{i}: {line[:800]}')
                        count += 1
                        if count >= 12:
                            break
            except Exception as e:
                continue
    add(f'Recent matching file count: {recent_hits}')
    add('')

    db = base / 'link_source_role_webview_overlay' / 'selected_link_source_role_roleplan.sqlite'
    add('===== SQLITE CHECK =====')
    if not db.exists():
        add(f'DB missing: {db}')
    else:
        add(f'DB: {db}')
        try:
            con = sqlite3.connect(str(db))
            cur = con.cursor()
            add('Tables:')
            tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name")]
            add(', '.join(tables))
            for table in tables:
                try:
                    cols = [r[1] for r in cur.execute(f'pragma table_info({table})')]
                except Exception:
                    continue
                url_cols = [c for c in cols if 'url' in c.lower()]
                text_cols = [c for c in cols if c.lower() in ('text','source_text','article_text','preview_text','normalized_text') or 'text' in c.lower()]
                role_cols = [c for c in cols if 'role' in c.lower()]
                if not (url_cols or text_cols or role_cols):
                    continue
                add(f'--- TABLE {table} cols={cols}')
                where_parts = []
                params = []
                for c in url_cols + text_cols:
                    where_parts.append(f'lower(cast({c} as text)) like ?')
                    params.append('%archive.ph/6mr3c%')
                    where_parts.append(f'lower(cast({c} as text)) like ?')
                    params.append('%seagull eater%')
                if not where_parts:
                    continue
                select_cols = (url_cols[:3] + role_cols[:3] + text_cols[:3])[:8]
                if not select_cols:
                    select_cols = cols[:5]
                try:
                    q = f"select {', '.join(select_cols)} from {table} where {' or '.join(where_parts)} limit 30"
                    rows = list(cur.execute(q, params))
                    add(f'Rows matching archive/title: {len(rows)}')
                    for row in rows[:15]:
                        add('    ' + repr(tuple((str(x)[:240] if x is not None else None) for x in row)))
                except Exception as e:
                    add(f'Query error: {e}')
            con.close()
        except Exception as e:
            add(f'SQLite open error: {e}')
    add('')

    add('===== RESULT HINT =====')
    add('PASS needs fresh post-marker material tied to https://archive.ph/6mr3C and current DB/source rows, not only old capture folders or Metro/Wayback duplicate text.')
    add('FAIL if selected overlay/roleplan files are missing, or recent matches only come from backups/old captures, or archive.ph rows are absent/currently copied without a fresh archive material load.')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Audit text written: {out}')
    # Print a compact tail to console too.
    for line in lines[:80]:
        print(line)
    if len(lines) > 80:
        print('... full audit written to file ...')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
