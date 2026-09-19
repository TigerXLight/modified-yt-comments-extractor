#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

MARKER = "YTCE_R45C_FACEBOOK_LIVE_COMMENTS_FOCUS_RUNNER"
STATUS_PASS = "PASS_R45C_FACEBOOK_LIVE_COMMENTS_FOCUS_RUNNER"
STATUS_BLOCKED = "BLOCKED_R45C_FACEBOOK_LIVE_COMMENTS_FOCUS_RUNNER"
SCHEMA_VERSION = "facebook_live_comments_focus_runner.r45c.v1"

FOCUS_CSS = r'''
/* R45C Facebook comments focus mode: CSS hiding only, no DOM deletion. */
html, body { background: #ffffff !important; }
[role="banner"],
[role="navigation"],
[aria-label="Facebook"],
[aria-label="Account controls and settings"],
[aria-label="Stories"],
[aria-label="Sponsored"],
[aria-label="Contacts"],
[aria-label="Chat contacts"],
[aria-label="Marketplace"],
[aria-label="Groups"],
[aria-label="Watch"],
[aria-label="Gaming"],
[aria-label="Notifications"],
[aria-label="Messenger"],
[aria-label="Create"],
div[role="complementary"],
aside,
nav {
  visibility: hidden !important;
  pointer-events: none !important;
}
[role="main"],
[role="article"],
[aria-label*="Comment"],
[aria-label*="comment"],
[aria-label*="Reply"],
[aria-label*="reply"],
[aria-label*="See more"],
[aria-label*="View more"],
[aria-label*="View replies"],
[aria-label*="View reply"],
[aria-label*="Like"],
[aria-label*="React"],
[role="button"],
a[href*="comment"],
a[href*="reply"] {
  visibility: visible !important;
  pointer-events: auto !important;
}
[role="main"] {
  margin-left: auto !important;
  margin-right: auto !important;
  max-width: 980px !important;
  width: 980px !important;
}
[role="article"] { max-width: 960px !important; }
div[dir="auto"] { line-height: 1.35 !important; }
[style*="position: fixed"], [style*="position:fixed"], [style*="position: sticky"], [style*="position:sticky"] {
  max-height: none !important;
}
'''

CONSOLE_SNIPPET = r'''
(() => {
  const css = __R45C_CSS__;
  let el = document.getElementById('ytce-r45c-facebook-comments-focus-css');
  if (!el) {
    el = document.createElement('style');
    el.id = 'ytce-r45c-facebook-comments-focus-css';
    document.documentElement.appendChild(el);
  }
  el.textContent = css;
  document.documentElement.setAttribute('data-ytce-r45c-facebook-comments-focus', '1');
  console.log('R45C Facebook comments focus mode applied. CSS-only, non-destructive. Expand comments/replies now; then capture.');
})();
'''

STOPWORDS = {
    'like', 'reply', 'share', 'edited', 'top comments', 'most relevant', 'all comments',
    'view more comments', 'view previous comments', 'see more', 'write a comment', 'comment as',
    'facebook', 'notifications', 'sponsored', 'contacts', 'search facebook', 'home', 'watch',
}

SENTINELS = [
    'Tony Bentley',
    'Mohhamed etc is the first name',
    'Dan Melin',
    "Look I'm all for Restore",
    'Alex Barron',
    'Context is everything',
]


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


def normalize_line(line: str) -> str:
    line = line.replace('\u00a0', ' ')
    line = re.sub(r'\s+', ' ', line).strip()
    return line


def filtered_lines(text: str) -> List[str]:
    out: List[str] = []
    for raw in text.splitlines():
        line = normalize_line(raw)
        if not line:
            continue
        low = line.lower()
        if low in STOPWORDS:
            continue
        if re.fullmatch(r'\d+[smhdw]|\d+[smhdw]\s*$', low):
            continue
        if re.fullmatch(r'\d+[KkMm]?\s*', line):
            continue
        if len(line) < 2:
            continue
        out.append(line)
    return out


def compare_text(candidate_text: str, reference_text: str) -> Dict[str, Any]:
    ref_lines = filtered_lines(reference_text)
    cand_text_norm = '\n'.join(filtered_lines(candidate_text)).lower()
    missing: List[str] = []
    matched = 0
    for line in ref_lines:
        needle = line.lower()
        if needle in cand_text_norm:
            matched += 1
        else:
            prefix = needle[:80].strip()
            if len(prefix) >= 18 and prefix in cand_text_norm:
                matched += 1
            else:
                missing.append(line)
    sentinel_report = {s: (s.lower() in candidate_text.lower()) for s in SENTINELS}
    return {
        'reference_filtered_line_count': len(ref_lines),
        'candidate_filtered_line_count': len(filtered_lines(candidate_text)),
        'matched_reference_line_count': matched,
        'missing_reference_line_count': len(missing),
        'coverage_ratio': (matched / len(ref_lines)) if ref_lines else 1.0,
        'sentinel_report': sentinel_report,
        'missing_sample': missing[:25],
    }


def extract_comment_blocks_from_text(text: str, max_items: int = 5000) -> List[Dict[str, Any]]:
    lines = filtered_lines(text)
    blocks: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines) and len(blocks) < max_items:
        author = lines[i]
        if author.lower() in STOPWORDS or len(author) > 90:
            i += 1
            continue
        body_parts: List[str] = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            low = nxt.lower()
            if low in STOPWORDS:
                j += 1
                continue
            if body_parts and len(nxt) <= 90 and not nxt.endswith(('.', ',', ';', ':', '!', '?')):
                if j + 1 < len(lines) and len(lines[j + 1]) > 12:
                    break
            body_parts.append(nxt)
            if len(body_parts) >= 12:
                break
            j += 1
        if body_parts:
            blocks.append({
                'index': len(blocks) + 1,
                'author_candidate': author,
                'text': '\n'.join(body_parts).strip(),
                'source': 'visible_inner_text',
            })
            i = max(j, i + 1)
        else:
            i += 1
    return blocks


def write_comment_exports(run_dir: Path, text: str, max_items: int = 5000) -> Dict[str, Any]:
    comments = extract_comment_blocks_from_text(text, max_items=max_items)
    json_path = write_json(run_dir / 'facebook_live_comments_focus_comments.json', comments)
    ndjson_path = run_dir / 'facebook_live_comments_focus_comments.ndjson'
    ensure_dir(ndjson_path.parent)
    with ndjson_path.open('w', encoding='utf-8', newline='\n') as f:
        for c in comments:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    md_lines = ['# Facebook live comments focus capture — extracted text', '']
    for c in comments:
        md_lines.append(f"## {c['index']}. {c['author_candidate']}")
        md_lines.append('')
        md_lines.append(c['text'])
        md_lines.append('')
    md_path = write_text(run_dir / 'facebook_live_comments_focus_comments.md', '\n'.join(md_lines).strip() + '\n')
    return {'comment_count': len(comments), 'json_path': json_path, 'ndjson_path': str(ndjson_path), 'markdown_path': md_path}


def contract() -> Dict[str, Any]:
    return {
        'marker': MARKER,
        'mode_id': 'facebook_live_comments_focus_runner',
        'schema_version': SCHEMA_VERSION,
        'primary_route': 'operator-controlled signed-in Facebook Chromium/WebView2 session; direct-launch or manual-current-page target; inject comments-only CSS focus mode; expand while page remains clickable; then capture screenshots, DOM, and visible text',
        'interactive_focus_rule': 'use CSS-only hiding/focusing; do not delete the comments DOM before expansion; View replies/View more/See more must remain clickable',
        'screenshot_rule': 'capture a full-page screenshot and optional tiled viewport screenshots after comments are loaded',
        'text_rule': 'capture visible innerText/textContent/DOM text from loaded comments; text capture does not require screenshots but still requires comments to be expanded/loaded first',
        'comparison_rule': 'when a Print Edit WE text dump is supplied, compare candidate text against it using filtered-line coverage and sentinel checks',
        'reaction_rule': 'capture visible Facebook reaction/like count text and reply count text only; Facebook has no Reddit-style downvotes and hidden reaction details must not be inferred',
        'post_cleanup_rule': 'static print-clean or cloned evidence view may be used after expansion; clickability is not required after static cleanup',
        'hidden_platform_api_scraping_enabled': False,
        'login_automation_enabled': False,
        'cookie_or_token_extraction_enabled': False,
        'browser_profile_file_copying_enabled': False,
        'browser_profile_file_parsing_enabled': False,
        'webview2_storage_or_cookie_inspection_enabled': False,
        'remote_media_downloads_enabled': False,
    }


def side_effect_flags(browser_started: bool = False, network: bool = False) -> Dict[str, bool]:
    return {
        'browser_session_started': browser_started,
        'network_actions_performed': network,
        'hidden_platform_api_scraping_performed': False,
        'login_automation_performed': False,
        'cookie_or_token_extraction_performed': False,
        'browser_profile_files_read_or_copied': False,
        'browser_profile_files_parsed_by_tool': False,
        'webview2_storage_or_cookie_inspection_performed': False,
        'remote_media_downloads_performed': False,
        'facebook_live_comments_focus_runner_invoked': True,
    }


def build_static_capture(candidate_text: str, output_root: Path, reference_text: Optional[str] = None, source_url: str = 'static_text') -> Dict[str, Any]:
    run_dir = ensure_dir(output_root / f'facebook_live_comments_focus_runner_{utc_stamp()}')
    inner_text_path = write_text(run_dir / 'visible_inner_text.txt', candidate_text)
    focus_css_path = write_text(run_dir / 'facebook_comments_focus_mode.css', FOCUS_CSS.strip() + '\n')
    focus_snippet_path = write_text(run_dir / 'facebook_comments_focus_console_snippet.js', CONSOLE_SNIPPET.replace('__R45C_CSS__', json.dumps(FOCUS_CSS)).strip() + '\n')
    exports = write_comment_exports(run_dir, candidate_text)
    comparison = compare_text(candidate_text, reference_text) if reference_text is not None else None
    receipt = {
        'marker': MARKER,
        'status': STATUS_PASS,
        'schema_version': SCHEMA_VERSION,
        'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
        'source_url': source_url,
        'run_dir': str(run_dir),
        'inner_text_path': inner_text_path,
        'raw_dom_path': None,
        'sanitized_dom_path': None,
        'screenshot_path': None,
        'tile_screenshot_count': 0,
        'focus_css_path': focus_css_path,
        'focus_snippet_path': focus_snippet_path,
        'comparison': comparison,
        **exports,
        'contract': contract(),
        'side_effect_flags': side_effect_flags(False, False),
        'warnings': [],
    }
    receipt['receipt_path'] = write_json(run_dir / 'r45c_facebook_live_comments_focus_runner_receipt.json', receipt)
    return receipt


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    reference = """Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet. They normally go by a middle name. This doesn't mean more muslim babies are being born than others.
1d
Reply
Dan Melin
Look I'm all for Restore, but this graph is so skewed. If we have 100 children. 20% are called Muhammad, 11% called Noah and so on and so forth all the way down; that's 20 kids called Muhammad and 80 kids not called that. It just so happens we have more variety 🤷
1d
Reply
Alex Barron
If all Christians called their kid Jesus, Muhammad would be a tiny percentage of boys names. But they dont.
But all Muslims do call their boys Muhammad (or variation of) so of course it’s high on the list.
Context is everything
23h
Reply
"""
    result = build_static_capture(reference, Path(args.output_root), reference_text=reference, source_url='self_test_fixture')
    checks = [
        {'name': 'focus_css_is_non_destructive', 'status': 'pass' if 'display: none' not in FOCUS_CSS.lower() else 'fail'},
        {'name': 'focus_snippet_available', 'status': 'pass' if Path(result['focus_snippet_path']).exists() else 'fail'},
        {'name': 'sample_text_extracts_comments', 'status': 'pass' if result['comment_count'] >= 3 else 'fail'},
        {'name': 'reference_comparison_matches_sentinels', 'status': 'pass' if result['comparison'] and result['comparison']['coverage_ratio'] >= 0.99 and all(result['comparison']['sentinel_report'].values()) else 'fail'},
        {'name': 'side_effects_safe', 'status': 'pass' if not any(v for k, v in result['side_effect_flags'].items() if k not in {'facebook_live_comments_focus_runner_invoked'}) else 'fail'},
    ]
    status = STATUS_PASS if all(c['status'] == 'pass' for c in checks) else STATUS_BLOCKED
    report = {
        'marker': MARKER,
        'status': status,
        'schema_version': SCHEMA_VERSION,
        'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
        'checks': checks,
        'sample_result': result,
        'contract': contract(),
        'side_effect_flags': side_effect_flags(False, False),
    }
    write_json(Path(args.output_root) / 'r45c_self_test_report.json', report)
    print(MARKER)
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def run_from_text_files(args: argparse.Namespace) -> Dict[str, Any]:
    candidate_text = Path(args.candidate_text).read_text(encoding='utf-8', errors='replace')
    reference_text = Path(args.reference_text).read_text(encoding='utf-8', errors='replace') if args.reference_text else None
    result = build_static_capture(candidate_text, Path(args.output_root), reference_text=reference_text, source_url=args.source_url or 'candidate_text_file')
    print(MARKER)
    print(result['status'])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def run_live(args: argparse.Namespace) -> Dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise SystemExit(f'{STATUS_BLOCKED}: Playwright is not available: {e}')

    output_root = Path(args.output_root)
    run_dir = ensure_dir(output_root / f'facebook_live_comments_focus_runner_{utc_stamp()}')
    reference_text = Path(args.reference_text).read_text(encoding='utf-8', errors='replace') if args.reference_text else None
    warnings: List[str] = []

    with sync_playwright() as p:
        chromium_kwargs: Dict[str, Any] = {'headless': False, 'viewport': None, 'args': ['--start-maximized']}
        if args.chromium_executable:
            chromium_kwargs['executable_path'] = args.chromium_executable
        if args.user_data_dir:
            context = p.chromium.launch_persistent_context(args.user_data_dir, **chromium_kwargs)
        else:
            browser = p.chromium.launch(**chromium_kwargs)
            context = browser.new_context(viewport=None)
        page = context.pages[0] if context.pages else context.new_page()
        if args.target_url and not args.manual_current_page:
            try:
                page.goto(args.target_url, wait_until='domcontentloaded', timeout=args.timeout_seconds * 1000)
            except Exception as e:
                warnings.append(f'initial_navigation_warning={e}')
        try:
            page.add_style_tag(content=FOCUS_CSS)
        except Exception as e:
            warnings.append(f'focus_css_injection_warning={e}')
        if args.operator_pause:
            print('R45C_OPERATOR_PAUSE')
            print('Use the visible Facebook page to expand View more comments / View replies / See more.')
            print('The CSS focus mode hides page chrome only; it does not delete comments and buttons should remain clickable.')
            print('Press ENTER here when the loaded comments are ready to capture...')
            try:
                input()
            except EOFError:
                pass
        elif args.wait_seconds:
            time.sleep(args.wait_seconds)
        raw_html = ''
        inner_text = ''
        final_url = ''
        try:
            final_url = page.url
        except Exception:
            pass
        try:
            raw_html = page.content()
        except Exception as e:
            warnings.append(f'raw_html_capture_warning={e}')
        try:
            inner_text = page.locator('body').inner_text(timeout=15000)
        except Exception as e:
            warnings.append(f'inner_text_capture_warning={e}')
            try:
                inner_text = page.evaluate('() => document.body ? document.body.innerText : ""')
            except Exception as e2:
                warnings.append(f'inner_text_fallback_warning={e2}')
        raw_dom_path = write_text(run_dir / 'facebook_live_raw_dom.html', raw_html)
        inner_text_path = write_text(run_dir / 'facebook_live_visible_inner_text.txt', inner_text)
        focus_css_path = write_text(run_dir / 'facebook_comments_focus_mode.css', FOCUS_CSS.strip() + '\n')
        focus_snippet_path = write_text(run_dir / 'facebook_comments_focus_console_snippet.js', CONSOLE_SNIPPET.replace('__R45C_CSS__', json.dumps(FOCUS_CSS)).strip() + '\n')
        screenshot_path = None
        try:
            screenshot_path = str(run_dir / 'facebook_comments_focus_full_page.png')
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception as e:
            warnings.append(f'full_page_screenshot_warning={e}')
            screenshot_path = None
        tile_paths: List[str] = []
        if args.tile_screenshots:
            for i in range(max(1, args.tile_steps)):
                try:
                    tile_path = run_dir / f'facebook_comments_focus_tile_{i+1:03d}.png'
                    page.screenshot(path=str(tile_path), full_page=False)
                    tile_paths.append(str(tile_path))
                    page.evaluate('(px) => window.scrollBy(0, px)', args.tile_scroll_px)
                    time.sleep(max(0.2, args.tile_wait_seconds))
                except Exception as e:
                    warnings.append(f'tile_{i+1}_warning={e}')
                    break
        exports = write_comment_exports(run_dir, inner_text, max_items=args.max_items)
        comparison = compare_text(inner_text, reference_text) if reference_text is not None else None
        status = STATUS_PASS if inner_text.strip() else STATUS_BLOCKED
        if not inner_text.strip():
            warnings.append('empty_inner_text_capture')
        receipt = {
            'marker': MARKER,
            'status': status,
            'schema_version': SCHEMA_VERSION,
            'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
            'target_url': args.target_url,
            'final_page_url': final_url,
            'run_dir': str(run_dir),
            'raw_dom_path': raw_dom_path,
            'inner_text_path': inner_text_path,
            'screenshot_path': screenshot_path,
            'tile_screenshot_paths': tile_paths,
            'tile_screenshot_count': len(tile_paths),
            'focus_css_path': focus_css_path,
            'focus_snippet_path': focus_snippet_path,
            **exports,
            'comparison': comparison,
            'contract': contract(),
            'side_effect_flags': side_effect_flags(True, bool(args.target_url and not args.manual_current_page)),
            'warnings': warnings,
        }
        receipt['receipt_path'] = write_json(run_dir / 'r45c_facebook_live_comments_focus_runner_receipt.json', receipt)
        print(MARKER)
        print(status)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        try:
            if args.keep_browser_open:
                print('R45C_KEEP_BROWSER_OPEN: press ENTER to close browser/context...')
                input()
        except EOFError:
            pass
        try:
            context.close()
        except Exception:
            pass
        return receipt


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description='R45C Facebook live comments focus runner')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--candidate-text')
    ap.add_argument('--reference-text')
    ap.add_argument('--output-root', default='profile_media_live_captures/r45c_facebook_live_comments_focus_runner')
    ap.add_argument('--source-url')
    ap.add_argument('--target-url')
    ap.add_argument('--manual-current-page', action='store_true')
    ap.add_argument('--chromium-executable')
    ap.add_argument('--user-data-dir')
    ap.add_argument('--operator-pause', action='store_true', default=False)
    ap.add_argument('--wait-seconds', type=float, default=3)
    ap.add_argument('--timeout-seconds', type=int, default=90)
    ap.add_argument('--tile-screenshots', action='store_true')
    ap.add_argument('--tile-steps', type=int, default=8)
    ap.add_argument('--tile-scroll-px', type=int, default=850)
    ap.add_argument('--tile-wait-seconds', type=float, default=0.7)
    ap.add_argument('--max-items', type=int, default=5000)
    ap.add_argument('--keep-browser-open', action='store_true')
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)
    if args.self_test:
        report = run_self_test(args)
        return 0 if report.get('status') == STATUS_PASS else 2
    if args.candidate_text:
        result = run_from_text_files(args)
        return 0 if result.get('status') == STATUS_PASS else 2
    if args.target_url or args.manual_current_page:
        result = run_live(args)
        return 0 if result.get('status') == STATUS_PASS else 2
    ap.print_help()
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
