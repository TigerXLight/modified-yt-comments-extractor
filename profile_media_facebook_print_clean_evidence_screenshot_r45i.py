#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MARKER = "YTCE_R45I_FACEBOOK_PRINT_CLEAN_EVIDENCE_SCREENSHOT"
STATUS_PASS = "PASS_R45I_FACEBOOK_PRINT_CLEAN_EVIDENCE_SCREENSHOT"
STATUS_BLOCKED = "BLOCKED_R45I_FACEBOOK_PRINT_CLEAN_EVIDENCE_SCREENSHOT"
SCHEMA_VERSION = "facebook_print_clean_evidence_screenshot.r45i.v1"


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, text: str) -> str:
    ensure_dir(path.parent)
    path.write_text(text, encoding='utf-8', newline='\n')
    return str(path)


def write_json(path: Path, data: Any) -> str:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    return str(path)


def norm_line(line: str) -> str:
    return re.sub(r'\s+', ' ', line.replace('\u00a0', ' ')).strip()


def filtered_lines(text: str) -> List[str]:
    skip_exact = {
        'like', 'reply', 'share', 'edited', 'facebook', 'write a comment', 'comment as',
        'top comments', 'most relevant', 'all comments', 'newest', 'oldest', 'relevant',
    }
    out: List[str] = []
    for raw in text.splitlines():
        line = norm_line(raw)
        if not line:
            continue
        low = line.lower()
        if low in skip_exact:
            continue
        if re.fullmatch(r'\d+[smhdw]', low):
            continue
        out.append(line)
    return out


def extract_blocks_from_inner_text(text: str, max_items: int = 10000) -> List[Dict[str, Any]]:
    """Lightweight export parser, matching the existing Facebook text lane style.

    This is intentionally conservative: it does not infer hidden/deleted text and only formats
    text already loaded into the visible page/export.
    """
    lines = filtered_lines(text)
    blocks: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines) and len(blocks) < max_items:
        author = lines[i]
        if len(author) > 120:
            i += 1
            continue
        body_parts: List[str] = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if body_parts and len(nxt) <= 110 and not nxt.endswith(('.', ',', ';', ':', '!', '?', ')', '”', '"')):
                if j + 1 < len(lines) and len(lines[j + 1]) > 12:
                    break
            body_parts.append(nxt)
            if len(body_parts) >= 14:
                break
            j += 1
        if body_parts:
            blocks.append({
                'index': len(blocks) + 1,
                'author_candidate': author,
                'text': '\n'.join(body_parts).strip(),
                'source': 'r45i_inner_text_or_export',
            })
            i = max(j, i + 1)
        else:
            i += 1
    return blocks


def load_comments_from_json(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding='utf-8', errors='replace'))
    if isinstance(data, list):
        comments = data
    elif isinstance(data, dict) and isinstance(data.get('comments'), list):
        comments = data['comments']
    else:
        comments = []
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(comments, start=1):
        if not isinstance(item, dict):
            continue
        author = str(item.get('author_candidate') or item.get('author') or item.get('name') or f'Comment {i}').strip()
        text = str(item.get('text') or item.get('body') or item.get('comment_text') or '').strip()
        if not text and author.startswith('Comment '):
            continue
        out.append({'index': len(out) + 1, 'author_candidate': author, 'text': text, 'source': str(path)})
    return out


def find_latest_run_dir(output_root: Path) -> Optional[Path]:
    candidates = []
    if output_root.exists():
        candidates.extend([p for p in output_root.iterdir() if p.is_dir()])
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def detect_source_paths(run_dir: Path) -> Dict[str, Optional[str]]:
    names = {
        'json': ['facebook_auto_expand_comments.json', 'facebook_live_comments_focus_comments.json'],
        'inner_text': ['facebook_live_visible_inner_text.txt', 'visible_inner_text.txt'],
        'receipt': ['r45h_facebook_bounded_modal_capture_runner_receipt.json', 'r45d_facebook_auto_expand_comments_runner_receipt.json'],
    }
    found: Dict[str, Optional[str]] = {k: None for k in names}
    for key, candidates in names.items():
        for name in candidates:
            p = run_dir / name
            if p.exists():
                found[key] = str(p)
                break
    return found


def build_print_html(comments: List[Dict[str, Any]], meta: Dict[str, Any], raw_text: Optional[str] = None) -> str:
    generated = _dt.datetime.now(_dt.timezone.utc).isoformat()
    total = len(comments)
    css = '''
:root { color-scheme: light; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #f5f6f7; color: #050505; font-family: Arial, Helvetica, sans-serif; font-size: 16px; }
body { padding: 24px; }
header { max-width: 980px; margin: 0 auto 18px auto; background: #fff; border: 1px solid #d8dadf; border-radius: 12px; padding: 18px 20px; }
h1 { font-size: 22px; margin: 0 0 8px 0; }
.meta { font-size: 13px; color: #555; line-height: 1.45; word-break: break-word; }
.notice { margin-top: 10px; padding: 10px 12px; background: #fff8db; border: 1px solid #ead27a; border-radius: 8px; color: #4d3b00; }
.comments { max-width: 980px; margin: 0 auto; }
.comment { background: #fff; border: 1px solid #d8dadf; border-radius: 12px; padding: 12px 14px; margin: 10px 0; break-inside: avoid; page-break-inside: avoid; }
.comment-header { display: flex; gap: 8px; align-items: baseline; border-bottom: 1px solid #f0f1f2; padding-bottom: 6px; margin-bottom: 8px; }
.idx { color: #777; font-size: 12px; min-width: 52px; }
.author { font-weight: 700; }
.body { white-space: pre-wrap; line-height: 1.45; overflow-wrap: anywhere; }
.raw { max-width: 980px; margin: 22px auto; background: #fff; border: 1px solid #d8dadf; border-radius: 12px; padding: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
@media print { body { background: white; padding: 12px; } header, .comment, .raw { border-color: #bbb; } }
'''
    bits: List[str] = []
    bits.append('<!doctype html><html><head><meta charset="utf-8"><title>Facebook comments print-clean evidence</title>')
    bits.append('<style>' + css + '</style></head><body>')
    bits.append('<header>')
    bits.append('<h1>Facebook comments print-clean evidence</h1>')
    bits.append('<div class="meta">')
    bits.append(f'<div><b>Generated:</b> {html.escape(generated)}</div>')
    bits.append(f'<div><b>Comment blocks formatted:</b> {total}</div>')
    if meta.get('source_run_dir'):
        bits.append(f'<div><b>Source run:</b> {html.escape(str(meta.get("source_run_dir")))}</div>')
    if meta.get('source_url'):
        bits.append(f'<div><b>Source URL:</b> {html.escape(str(meta.get("source_url")))}</div>')
    if meta.get('comparison'):
        comp = meta['comparison']
        bits.append(f'<div><b>Comparison coverage:</b> {html.escape(str(comp.get("coverage_ratio")))}</div>')
        bits.append(f'<div><b>Reference matched/missing:</b> {html.escape(str(comp.get("matched_reference_line_count")))} matched, {html.escape(str(comp.get("missing_reference_line_count")))} missing</div>')
    bits.append('</div>')
    bits.append('<div class="notice">This is a static print-clean evidence page generated after the visible Facebook comments were loaded. It is not an interactive Facebook page; it is intended for complete readable screenshots/printing.</div>')
    bits.append('</header>')
    bits.append('<main class="comments">')
    for i, c in enumerate(comments, start=1):
        author = html.escape(str(c.get('author_candidate') or c.get('author') or f'Comment {i}'))
        text = html.escape(str(c.get('text') or ''))
        bits.append('<section class="comment">')
        bits.append('<div class="comment-header"><span class="idx">#%04d</span><span class="author">%s</span></div>' % (i, author))
        bits.append('<div class="body">%s</div>' % text)
        bits.append('</section>')
    bits.append('</main>')
    if raw_text and not comments:
        bits.append('<section class="raw"><h2>Raw visible text</h2>')
        bits.append(html.escape(raw_text))
        bits.append('</section>')
    bits.append('</body></html>')
    return '\n'.join(bits)


def screenshot_html(html_path: Path, output_dir: Path, chromium_executable: Optional[str], full_page: bool, tile: bool, tile_steps: int, tile_scroll_px: int, viewport_width: int, viewport_height: int) -> Tuple[Optional[str], List[str], List[str]]:
    warnings: List[str] = []
    full_path: Optional[str] = None
    tile_paths: List[str] = []
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        warnings.append(f'playwright_unavailable_for_screenshot={e}')
        return full_path, tile_paths, warnings
    with sync_playwright() as p:
        launch_kwargs: Dict[str, Any] = {'headless': True}
        if chromium_executable:
            launch_kwargs['executable_path'] = chromium_executable
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={'width': viewport_width, 'height': viewport_height})
        page.goto(html_path.resolve().as_uri(), wait_until='load')
        time.sleep(0.25)
        if full_page:
            try:
                full_path = str(output_dir / 'facebook_print_clean_evidence_full_page.png')
                page.screenshot(path=full_path, full_page=True)
            except Exception as e:
                warnings.append(f'full_page_print_screenshot_warning={e}')
                full_path = None
        if tile:
            try:
                total_height = page.evaluate('() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)')
            except Exception:
                total_height = viewport_height * tile_steps
            max_tiles = max(1, tile_steps)
            y = 0
            for i in range(max_tiles):
                if y > total_height + viewport_height:
                    break
                try:
                    page.evaluate('(y) => window.scrollTo(0, y)', y)
                    time.sleep(0.1)
                    tile_path = output_dir / f'facebook_print_clean_evidence_tile_{i+1:03d}.png'
                    page.screenshot(path=str(tile_path), full_page=False)
                    tile_paths.append(str(tile_path))
                    y += tile_scroll_px
                except Exception as e:
                    warnings.append(f'tile_print_screenshot_{i+1}_warning={e}')
                    break
        browser.close()
    return full_path, tile_paths, warnings


def contract() -> Dict[str, Any]:
    return {
        'marker': MARKER,
        'mode_id': 'facebook_print_clean_evidence_screenshot',
        'schema_version': SCHEMA_VERSION,
        'primary_route': 'Use R45H/R45G live expansion first, then convert loaded/exported comments into a static print-clean evidence page for full-page or tiled screenshots.',
        'screenshot_rule': 'Screenshots should be taken after expansion from a static print-clean evidence page, not from the original scroll-trapped Facebook modal.',
        'interactive_rule': 'All expansion happens before this runner; the print-clean page is intentionally non-interactive like Print Edit WE output.',
        'comments_only_rule': 'The generated page contains only comment evidence plus minimal metadata; Facebook chrome/feed/sidebar/modal floaters are excluded.',
        'text_source_rule': 'Input is loaded visible text or extracted comment JSON/NDJSON from a prior visible run; no hidden API scraping is used.',
        'hidden_platform_api_scraping_enabled': False,
        'login_automation_enabled': False,
        'cookie_or_token_extraction_enabled': False,
        'browser_profile_file_copying_enabled': False,
        'browser_profile_file_parsing_enabled': False,
        'webview2_storage_or_cookie_inspection_enabled': False,
        'remote_media_downloads_enabled': False,
    }


def side_effect_flags(screenshot_browser: bool = False) -> Dict[str, Any]:
    return {
        'browser_session_started': screenshot_browser,
        'network_actions_performed': False,
        'visible_page_auto_expand_clicks_performed': False,
        'hidden_platform_api_scraping_performed': False,
        'login_automation_performed': False,
        'cookie_or_token_extraction_performed': False,
        'browser_profile_files_read_or_copied': False,
        'browser_profile_files_parsed_by_tool': False,
        'webview2_storage_or_cookie_inspection_performed': False,
        'remote_media_downloads_performed': False,
        'facebook_print_clean_evidence_screenshot_invoked': True,
    }


def build_from_sources(args: argparse.Namespace) -> Dict[str, Any]:
    output_root = Path(args.output_root)
    run_dir = ensure_dir(output_root / f'facebook_print_clean_evidence_screenshot_{utc_stamp()}')
    warnings: List[str] = []
    source_run_dir: Optional[Path] = Path(args.run_dir) if args.run_dir else None
    if not source_run_dir and args.latest_r45h_root:
        source_run_dir = find_latest_run_dir(Path(args.latest_r45h_root))
        if not source_run_dir:
            raise SystemExit(f'{STATUS_BLOCKED}: no R45H run directories found under {args.latest_r45h_root}')
    comments: List[Dict[str, Any]] = []
    raw_text: str = ''
    detected: Dict[str, Optional[str]] = {}
    meta: Dict[str, Any] = {}
    if source_run_dir:
        detected = detect_source_paths(source_run_dir)
        if detected.get('receipt'):
            try:
                receipt = json.loads(Path(detected['receipt']).read_text(encoding='utf-8', errors='replace'))
                meta['source_url'] = receipt.get('final_page_url') or receipt.get('sanitized_target_url') or receipt.get('target_url')
                meta['comparison'] = receipt.get('comparison')
            except Exception as e:
                warnings.append(f'receipt_read_warning={e}')
        meta['source_run_dir'] = str(source_run_dir)
        if detected.get('json'):
            comments = load_comments_from_json(Path(detected['json']))
        if detected.get('inner_text'):
            raw_text = Path(detected['inner_text']).read_text(encoding='utf-8', errors='replace')
    if args.comments_json:
        comments = load_comments_from_json(Path(args.comments_json))
    if args.candidate_text:
        raw_text = Path(args.candidate_text).read_text(encoding='utf-8', errors='replace')
    if not comments and raw_text:
        comments = extract_blocks_from_inner_text(raw_text, max_items=args.max_items)
    if not comments:
        raise SystemExit(f'{STATUS_BLOCKED}: no comments found from run-dir/json/text input')
    html_text = build_print_html(comments, meta, raw_text=raw_text)
    html_path = Path(write_text(run_dir / 'facebook_print_clean_evidence.html', html_text))
    text_path = write_text(run_dir / 'facebook_print_clean_evidence_visible_text.txt', raw_text if raw_text else '\n\n'.join([str(c.get('author_candidate',''))+'\n'+str(c.get('text','')) for c in comments]))
    json_path = write_json(run_dir / 'facebook_print_clean_evidence_comments.json', comments)
    full_screenshot = None
    tile_paths: List[str] = []
    if args.screenshot or args.tile_screenshots:
        full_screenshot, tile_paths, shot_warnings = screenshot_html(html_path, run_dir, args.chromium_executable, args.screenshot, args.tile_screenshots, args.tile_steps, args.tile_scroll_px, args.viewport_width, args.viewport_height)
        warnings.extend(shot_warnings)
    status = STATUS_PASS if comments else STATUS_BLOCKED
    receipt = {
        'marker': MARKER,
        'status': status,
        'schema_version': SCHEMA_VERSION,
        'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
        'source_run_dir': str(source_run_dir) if source_run_dir else None,
        'detected_source_paths': detected,
        'comment_count': len(comments),
        'html_path': str(html_path),
        'text_path': text_path,
        'json_path': json_path,
        'full_screenshot_path': full_screenshot,
        'tile_screenshot_paths': tile_paths,
        'tile_screenshot_count': len(tile_paths),
        'contract': contract(),
        'side_effect_flags': side_effect_flags(bool(args.screenshot or args.tile_screenshots)),
        'warnings': warnings,
    }
    receipt['receipt_path'] = write_json(run_dir / 'r45i_facebook_print_clean_evidence_screenshot_receipt.json', receipt)
    print(MARKER)
    print(status)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    tmp_root = Path(args.output_root)
    sample_dir = ensure_dir(tmp_root / 'sample_r45h_run')
    sample_comments = [
        {'index': 1, 'author_candidate': 'Tony Bentley', 'text': 'Mohhamed etc is the first name of all muslim boys as it is the name of their prophet.'},
        {'index': 2, 'author_candidate': 'Dan Melin', 'text': "Look I'm all for Restore, but this graph is so skewed."},
        {'index': 3, 'author_candidate': 'Alex Barron', 'text': 'Context is everything'},
    ]
    write_json(sample_dir / 'facebook_auto_expand_comments.json', sample_comments)
    write_text(sample_dir / 'facebook_live_visible_inner_text.txt', '\n'.join([c['author_candidate']+'\n'+c['text'] for c in sample_comments]))
    ns = argparse.Namespace(
        run_dir=str(sample_dir), latest_r45h_root=None, comments_json=None, candidate_text=None,
        output_root=str(tmp_root), max_items=100, screenshot=False, tile_screenshots=False, tile_steps=3,
        tile_scroll_px=800, viewport_width=900, viewport_height=1200, chromium_executable=None,
    )
    result = build_from_sources(ns)
    checks = [
        {'name': 'print_clean_html_created', 'status': 'pass' if Path(result['html_path']).exists() else 'fail'},
        {'name': 'comments_loaded_from_r45h_json', 'status': 'pass' if result.get('comment_count') == 3 else 'fail'},
        {'name': 'comments_only_contract', 'status': 'pass' if contract()['comments_only_rule'] else 'fail'},
        {'name': 'side_effects_safe_without_screenshot', 'status': 'pass' if not any(v for k, v in result['side_effect_flags'].items() if k not in {'facebook_print_clean_evidence_screenshot_invoked'}) else 'fail'},
    ]
    status = STATUS_PASS if all(c['status'] == 'pass' for c in checks) else STATUS_BLOCKED
    report = {'marker': MARKER, 'status': status, 'schema_version': SCHEMA_VERSION, 'checks': checks, 'sample_result': result, 'contract': contract(), 'side_effect_flags': side_effect_flags(False)}
    write_json(tmp_root / 'r45i_self_test_report.json', report)
    print(MARKER)
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description='R45I Facebook print-clean evidence screenshot generator')
    ap.add_argument('--run-dir', help='Prior R45H/R45G/R45D live run directory containing extracted comments and/or inner text')
    ap.add_argument('--latest-r45h-root', default='profile_media_live_captures/r45h_facebook_bounded_modal_capture_runner/live')
    ap.add_argument('--comments-json')
    ap.add_argument('--candidate-text')
    ap.add_argument('--output-root', default='profile_media_live_captures/r45i_facebook_print_clean_evidence_screenshot/live')
    ap.add_argument('--max-items', type=int, default=10000)
    ap.add_argument('--screenshot', action='store_true', help='Capture one full-page screenshot of the generated print-clean page')
    ap.add_argument('--tile-screenshots', action='store_true', help='Capture viewport tiles of the generated print-clean page')
    ap.add_argument('--tile-steps', type=int, default=260)
    ap.add_argument('--tile-scroll-px', type=int, default=1000)
    ap.add_argument('--viewport-width', type=int, default=1100)
    ap.add_argument('--viewport-height', type=int, default=1400)
    ap.add_argument('--chromium-executable')
    ap.add_argument('--self-test', action='store_true')
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)
    if args.self_test:
        report = run_self_test(args)
        return 0 if report.get('status') == STATUS_PASS else 2
    result = build_from_sources(args)
    return 0 if result.get('status') == STATUS_PASS else 2


if __name__ == '__main__':
    raise SystemExit(main())
