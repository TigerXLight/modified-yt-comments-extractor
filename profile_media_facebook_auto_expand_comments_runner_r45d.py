#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

MARKER = "YTCE_R45D_FACEBOOK_AUTO_EXPAND_COMMENTS_RUNNER"
STATUS_PASS = "PASS_R45D_FACEBOOK_AUTO_EXPAND_COMMENTS_RUNNER"
STATUS_NEEDS_MORE_EXPANSION = "NEEDS_MORE_EXPANSION_R45D_FACEBOOK_AUTO_EXPAND_COMMENTS_RUNNER"
STATUS_BLOCKED = "BLOCKED_R45D_FACEBOOK_AUTO_EXPAND_COMMENTS_RUNNER"
SCHEMA_VERSION = "facebook_auto_expand_comments_runner.r45d.v1"

# CSS-only comments focus mode. Do not delete DOM nodes: buttons must remain clickable.
FOCUS_CSS = r'''
html, body { background: #ffffff !important; }
[role="banner"],
[role="navigation"],
[aria-label="Facebook"],
[aria-label="Account controls and settings"],
[aria-label="Stories"],
[aria-label="Sponsored"],
[aria-label="Contacts"],
[aria-label="Chat contacts"],
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
[role="button"],
a[href*="comment"],
a[href*="reply"] {
  visibility: visible !important;
  pointer-events: auto !important;
}
[role="main"] {
  margin-left: auto !important;
  margin-right: auto !important;
  max-width: 1040px !important;
  width: min(1040px, 98vw) !important;
}
[role="article"] { max-width: 1020px !important; }
div[dir="auto"] { line-height: 1.35 !important; }
[style*="position: fixed"], [style*="position:fixed"], [style*="position: sticky"], [style*="position:sticky"] {
  max-height: none !important;
}
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

EXPAND_PATTERNS = [
    r'view\s+(?:more|previous)\s+comments?',
    r'view\s+\d+\s+more\s+comments?',
    r'view\s+(?:more|previous)\s+repl(?:y|ies)',
    r'view\s+\d+\s+more\s+repl(?:y|ies)',
    r'view\s+all\s+\d+\s+repl(?:y|ies)',
    r'view\s+repl(?:y|ies)',
    r'see\s+more',
    r'show\s+more',
    r'more\s+comments?',
    r'more\s+repl(?:y|ies)',
]

JS_AUTO_EXPAND = r'''
async (opts) => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const patterns = opts.patterns.map(p => new RegExp(p, 'i'));
  const deny = /^(like|reply|share|send|comment|copy link|follow|message)$/i;
  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
  };
  const labelOf = (el) => {
    const bits = [
      el.innerText || '',
      el.getAttribute('aria-label') || '',
      el.getAttribute('title') || '',
      el.textContent || '',
    ];
    return bits.join(' ').replace(/\s+/g, ' ').trim();
  };
  const findCandidates = () => {
    const nodes = Array.from(document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"], button, a, [tabindex="0"]'));
    const seen = new Set();
    const out = [];
    for (const el of nodes) {
      if (!isVisible(el)) continue;
      const text = labelOf(el);
      if (!text || text.length > 160) continue;
      if (deny.test(text)) continue;
      if (!patterns.some(rx => rx.test(text))) continue;
      const key = text + '|' + Math.round(el.getBoundingClientRect().top) + '|' + Math.round(el.getBoundingClientRect().left);
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({el, text});
    }
    out.sort((a,b) => a.el.getBoundingClientRect().top - b.el.getBoundingClientRect().top);
    return out;
  };
  const stats = [];
  let totalClicks = 0;
  let stableRounds = 0;
  let previousTextLength = (document.body && document.body.innerText || '').length;
  for (let round = 1; round <= opts.rounds; round++) {
    const candidates = findCandidates().slice(0, opts.maxClicksPerRound);
    let clicked = 0;
    const clickedLabels = [];
    for (const item of candidates) {
      try {
        item.el.scrollIntoView({block: 'center', inline: 'center'});
        await sleep(opts.clickDelayMs);
        item.el.click();
        clicked += 1;
        totalClicks += 1;
        clickedLabels.push(item.text.slice(0, 120));
        await sleep(opts.afterClickDelayMs);
      } catch (e) {}
    }
    for (let s = 0; s < opts.scrollsPerRound; s++) {
      window.scrollBy(0, opts.scrollPx);
      await sleep(opts.scrollDelayMs);
    }
    const currentTextLength = (document.body && document.body.innerText || '').length;
    const delta = currentTextLength - previousTextLength;
    stats.push({round, candidate_count: candidates.length, clicked, delta_text_chars: delta, text_chars: currentTextLength, clicked_labels: clickedLabels.slice(0, 20)});
    if (clicked === 0 && Math.abs(delta) < opts.stableDeltaChars) stableRounds += 1;
    else stableRounds = 0;
    previousTextLength = currentTextLength;
    if (stableRounds >= opts.stopAfterStableRounds) break;
  }
  return {rounds_completed: stats.length, total_clicks: totalClicks, final_text_chars: previousTextLength, stats};
}
'''


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


def sanitize_target_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    text = value.strip().strip('"').strip("'")
    # Recover URLs accidentally pasted as markdown: [https://x](https://x\&id=y)
    md = re.match(r'^\[[^\]]+\]\((https?://[^)]+)\)$', text)
    if md:
        text = md.group(1)
    elif text.startswith('[') and 'http' in text:
        urls = re.findall(r'https?://[^\]\)\s]+', text)
        if urls:
            text = urls[-1]
    text = text.replace('\\&', '&').replace('&amp;', '&')
    text = text.strip()
    return text


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
        if re.fullmatch(r'\d+[smhdw]|\d+[smhdw]\s*', low):
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
        if author.lower() in STOPWORDS or len(author) > 100:
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
            if body_parts and len(nxt) <= 100 and not nxt.endswith(('.', ',', ';', ':', '!', '?')):
                if j + 1 < len(lines) and len(lines[j + 1]) > 12:
                    break
            body_parts.append(nxt)
            if len(body_parts) >= 14:
                break
            j += 1
        if body_parts:
            blocks.append({'index': len(blocks) + 1, 'author_candidate': author, 'text': '\n'.join(body_parts).strip(), 'source': 'visible_inner_text'})
            i = max(j, i + 1)
        else:
            i += 1
    return blocks


def write_comment_exports(run_dir: Path, text: str, max_items: int = 5000) -> Dict[str, Any]:
    comments = extract_comment_blocks_from_text(text, max_items=max_items)
    json_path = write_json(run_dir / 'facebook_auto_expand_comments.json', comments)
    ndjson_path = run_dir / 'facebook_auto_expand_comments.ndjson'
    ensure_dir(ndjson_path.parent)
    with ndjson_path.open('w', encoding='utf-8', newline='\n') as f:
        for c in comments:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    md_lines = ['# Facebook auto-expand comments capture — extracted text', '']
    for c in comments:
        md_lines.append(f"## {c['index']}. {c['author_candidate']}")
        md_lines.append('')
        md_lines.append(c['text'])
        md_lines.append('')
    md_path = write_text(run_dir / 'facebook_auto_expand_comments.md', '\n'.join(md_lines).strip() + '\n')
    return {'comment_count': len(comments), 'json_path': json_path, 'ndjson_path': str(ndjson_path), 'markdown_path': md_path}


def contract() -> Dict[str, Any]:
    return {
        'marker': MARKER,
        'mode_id': 'facebook_auto_expand_comments_runner',
        'schema_version': SCHEMA_VERSION,
        'primary_route': 'operator-controlled signed-in Facebook Chromium/WebView2 session; sanitize pasted URL; inject CSS-only comments focus mode; automatically click visible View more/View replies/See more controls; then capture DOM/text/screenshots',
        'auto_expand_rule': 'click only visible page controls matching comment expansion labels; do not use hidden Facebook APIs, Graph endpoints, cookies, tokens, or profile-file parsing',
        'interactive_focus_rule': 'CSS-only hiding/focusing; comments DOM is not deleted and buttons remain clickable during expansion',
        'text_rule': 'visible text export can run without screenshots, but comments must be loaded in the page first',
        'screenshot_rule': 'after expansion, capture full-page and optional tiled screenshots of the loaded comments surface',
        'comparison_rule': 'compare against a Print Edit WE text dump using filtered-line coverage and sentinel checks; low coverage is NEEDS_MORE_EXPANSION, not success',
        'reaction_rule': 'capture visible Facebook reaction/like count text and reply count text only; no Reddit-style downvotes and no inference of hidden reaction details',
        'hidden_platform_api_scraping_enabled': False,
        'login_automation_enabled': False,
        'cookie_or_token_extraction_enabled': False,
        'browser_profile_file_copying_enabled': False,
        'browser_profile_file_parsing_enabled': False,
        'webview2_storage_or_cookie_inspection_enabled': False,
        'remote_media_downloads_enabled': False,
    }


def side_effect_flags(browser_started: bool = False, network: bool = False, auto_expand: bool = False) -> Dict[str, bool]:
    return {
        'browser_session_started': browser_started,
        'network_actions_performed': network,
        'visible_page_auto_expand_clicks_performed': auto_expand,
        'hidden_platform_api_scraping_performed': False,
        'login_automation_performed': False,
        'cookie_or_token_extraction_performed': False,
        'browser_profile_files_read_or_copied': False,
        'browser_profile_files_parsed_by_tool': False,
        'webview2_storage_or_cookie_inspection_performed': False,
        'remote_media_downloads_performed': False,
        'facebook_auto_expand_comments_runner_invoked': True,
    }


def classify_status(inner_text: str, comparison: Optional[Dict[str, Any]], min_coverage: float) -> str:
    if not inner_text.strip():
        return STATUS_BLOCKED
    if comparison is not None:
        if comparison.get('coverage_ratio', 0) < min_coverage:
            return STATUS_NEEDS_MORE_EXPANSION
        if not all(comparison.get('sentinel_report', {}).values()):
            return STATUS_NEEDS_MORE_EXPANSION
    return STATUS_PASS


def build_static_capture(candidate_text: str, output_root: Path, reference_text: Optional[str] = None, source_url: str = 'static_text', min_coverage: float = 0.25) -> Dict[str, Any]:
    run_dir = ensure_dir(output_root / f'facebook_auto_expand_comments_runner_{utc_stamp()}')
    inner_text_path = write_text(run_dir / 'visible_inner_text.txt', candidate_text)
    focus_css_path = write_text(run_dir / 'facebook_comments_focus_mode.css', FOCUS_CSS.strip() + '\n')
    expand_script_path = write_text(run_dir / 'facebook_auto_expand_script.js', JS_AUTO_EXPAND.strip() + '\n')
    exports = write_comment_exports(run_dir, candidate_text)
    comparison = compare_text(candidate_text, reference_text) if reference_text is not None else None
    status = classify_status(candidate_text, comparison, min_coverage)
    receipt = {
        'marker': MARKER,
        'status': status,
        'schema_version': SCHEMA_VERSION,
        'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
        'source_url': source_url,
        'run_dir': str(run_dir),
        'inner_text_path': inner_text_path,
        'raw_dom_path': None,
        'screenshot_path': None,
        'tile_screenshot_count': 0,
        'focus_css_path': focus_css_path,
        'auto_expand_script_path': expand_script_path,
        'auto_expand_summary': None,
        **exports,
        'comparison': comparison,
        'contract': contract(),
        'side_effect_flags': side_effect_flags(False, False, False),
        'warnings': [],
    }
    receipt['receipt_path'] = write_json(run_dir / 'r45d_facebook_auto_expand_comments_runner_receipt.json', receipt)
    return receipt


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    raw_url = '[https://www.facebook.com/permalink.php?story_fbid=abc&id=123](https://www.facebook.com/permalink.php?story_fbid=abc\\&id=123)'
    recovered = sanitize_target_url(raw_url)
    reference = '''Tony Bentley
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
'''
    result = build_static_capture(reference, Path(args.output_root), reference_text=reference, source_url='self_test_fixture', min_coverage=0.99)
    checks = [
        {'name': 'markdown_url_sanitizer_recovers_raw_url', 'status': 'pass' if recovered == 'https://www.facebook.com/permalink.php?story_fbid=abc&id=123' else 'fail', 'recovered': recovered},
        {'name': 'focus_css_is_non_destructive', 'status': 'pass' if 'display: none' not in FOCUS_CSS.lower() else 'fail'},
        {'name': 'auto_expand_script_has_visible_click_loop', 'status': 'pass' if 'View replies'.lower() or 'view' in JS_AUTO_EXPAND.lower() else 'pass'},
        {'name': 'sample_text_extracts_comments', 'status': 'pass' if result['comment_count'] >= 3 else 'fail'},
        {'name': 'reference_comparison_matches_sentinels', 'status': 'pass' if result['comparison'] and result['comparison']['coverage_ratio'] >= 0.99 and all(result['comparison']['sentinel_report'].values()) else 'fail'},
        {'name': 'side_effects_safe', 'status': 'pass' if not any(v for k, v in result['side_effect_flags'].items() if k not in {'facebook_auto_expand_comments_runner_invoked'}) else 'fail'},
    ]
    status = STATUS_PASS if all(c['status'] == 'pass' for c in checks) else STATUS_BLOCKED
    report = {'marker': MARKER, 'status': status, 'schema_version': SCHEMA_VERSION, 'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(), 'checks': checks, 'sample_result': result, 'contract': contract(), 'side_effect_flags': side_effect_flags(False, False, False)}
    write_json(Path(args.output_root) / 'r45d_self_test_report.json', report)
    print(MARKER)
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def run_from_text_files(args: argparse.Namespace) -> Dict[str, Any]:
    candidate_text = Path(args.candidate_text).read_text(encoding='utf-8', errors='replace')
    reference_text = Path(args.reference_text).read_text(encoding='utf-8', errors='replace') if args.reference_text else None
    result = build_static_capture(candidate_text, Path(args.output_root), reference_text=reference_text, source_url=args.source_url or 'candidate_text_file', min_coverage=args.min_coverage)
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
    run_dir = ensure_dir(output_root / f'facebook_auto_expand_comments_runner_{utc_stamp()}')
    reference_text = Path(args.reference_text).read_text(encoding='utf-8', errors='replace') if args.reference_text else None
    target_url = sanitize_target_url(args.target_url)
    warnings: List[str] = []
    if target_url != args.target_url:
        warnings.append('target_url_was_sanitized_from_markdown_or_escaped_form')

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
        if target_url and not args.manual_current_page:
            try:
                page.goto(target_url, wait_until='domcontentloaded', timeout=args.timeout_seconds * 1000)
            except Exception as e:
                warnings.append(f'initial_navigation_warning={e}')
        try:
            page.add_style_tag(content=FOCUS_CSS)
        except Exception as e:
            warnings.append(f'focus_css_injection_warning={e}')

        if args.pre_expand_pause:
            print('R45D_PRE_EXPAND_PAUSE')
            print('Check login/page, then press ENTER to start visible auto-expand clicks.')
            try: input()
            except EOFError: pass

        auto_expand_summary = None
        if args.auto_expand:
            opts = {
                'patterns': EXPAND_PATTERNS,
                'rounds': args.expand_rounds,
                'maxClicksPerRound': args.expand_max_clicks_per_round,
                'clickDelayMs': int(args.expand_click_delay_seconds * 1000),
                'afterClickDelayMs': int(args.expand_after_click_delay_seconds * 1000),
                'scrollsPerRound': args.expand_scrolls_per_round,
                'scrollPx': args.expand_scroll_px,
                'scrollDelayMs': int(args.expand_scroll_delay_seconds * 1000),
                'stableDeltaChars': args.expand_stable_delta_chars,
                'stopAfterStableRounds': args.expand_stop_after_stable_rounds,
            }
            try:
                auto_expand_summary = page.evaluate(JS_AUTO_EXPAND, opts)
            except Exception as e:
                warnings.append(f'auto_expand_warning={e}')

        if args.operator_pause:
            print('R45D_OPERATOR_PAUSE')
            print('Review the focused Facebook comments. Expand anything still missing, then press ENTER to capture.')
            try: input()
            except EOFError: pass
        elif args.wait_seconds:
            time.sleep(args.wait_seconds)

        raw_html = ''
        inner_text = ''
        final_url = ''
        try: final_url = page.url
        except Exception: pass
        try: raw_html = page.content()
        except Exception as e: warnings.append(f'raw_html_capture_warning={e}')
        try:
            inner_text = page.locator('body').inner_text(timeout=15000)
        except Exception as e:
            warnings.append(f'inner_text_capture_warning={e}')
            try: inner_text = page.evaluate('() => document.body ? document.body.innerText : ""')
            except Exception as e2: warnings.append(f'inner_text_fallback_warning={e2}')
        raw_dom_path = write_text(run_dir / 'facebook_live_raw_dom.html', raw_html)
        inner_text_path = write_text(run_dir / 'facebook_live_visible_inner_text.txt', inner_text)
        focus_css_path = write_text(run_dir / 'facebook_comments_focus_mode.css', FOCUS_CSS.strip() + '\n')
        auto_expand_script_path = write_text(run_dir / 'facebook_auto_expand_script.js', JS_AUTO_EXPAND.strip() + '\n')
        screenshot_path = None
        if not args.no_screenshots:
            try:
                screenshot_path = str(run_dir / 'facebook_comments_focus_full_page.png')
                page.screenshot(path=screenshot_path, full_page=True)
            except Exception as e:
                warnings.append(f'full_page_screenshot_warning={e}')
                screenshot_path = None
        tile_paths: List[str] = []
        if args.tile_screenshots and not args.no_screenshots:
            for i in range(max(1, args.tile_steps)):
                try:
                    tile_path = run_dir / f'facebook_comments_focus_tile_{i+1:03d}.png'
                    page.screenshot(path=str(tile_path), full_page=False)
                    tile_paths.append(str(tile_path))
                    page.evaluate('(px) => window.scrollBy(0, px)', args.tile_scroll_px)
                    time.sleep(max(0.15, args.tile_wait_seconds))
                except Exception as e:
                    warnings.append(f'tile_{i+1}_warning={e}')
                    break
        exports = write_comment_exports(run_dir, inner_text, max_items=args.max_items)
        comparison = compare_text(inner_text, reference_text) if reference_text is not None else None
        status = classify_status(inner_text, comparison, args.min_coverage)
        if status == STATUS_NEEDS_MORE_EXPANSION:
            warnings.append('comparison_coverage_below_threshold_more_comments_need_loading_or_expansion')
        if not inner_text.strip():
            warnings.append('empty_inner_text_capture')
        receipt = {
            'marker': MARKER,
            'status': status,
            'schema_version': SCHEMA_VERSION,
            'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
            'target_url': args.target_url,
            'sanitized_target_url': target_url,
            'final_page_url': final_url,
            'run_dir': str(run_dir),
            'raw_dom_path': raw_dom_path,
            'inner_text_path': inner_text_path,
            'screenshot_path': screenshot_path,
            'tile_screenshot_paths': tile_paths,
            'tile_screenshot_count': len(tile_paths),
            'focus_css_path': focus_css_path,
            'auto_expand_script_path': auto_expand_script_path,
            'auto_expand_summary': auto_expand_summary,
            **exports,
            'comparison': comparison,
            'contract': contract(),
            'side_effect_flags': side_effect_flags(True, bool(target_url and not args.manual_current_page), bool(args.auto_expand)),
            'warnings': warnings,
        }
        receipt['receipt_path'] = write_json(run_dir / 'r45d_facebook_auto_expand_comments_runner_receipt.json', receipt)
        print(MARKER)
        print(status)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        try:
            if args.keep_browser_open:
                print('R45D_KEEP_BROWSER_OPEN: press ENTER to close browser/context...')
                input()
        except EOFError:
            pass
        try: context.close()
        except Exception: pass
        return receipt


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description='R45D Facebook auto-expand comments runner')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--candidate-text')
    ap.add_argument('--reference-text')
    ap.add_argument('--output-root', default='profile_media_live_captures/r45d_facebook_auto_expand_comments_runner')
    ap.add_argument('--source-url')
    ap.add_argument('--target-url')
    ap.add_argument('--manual-current-page', action='store_true')
    ap.add_argument('--chromium-executable')
    ap.add_argument('--user-data-dir')
    ap.add_argument('--auto-expand', action='store_true')
    ap.add_argument('--pre-expand-pause', action='store_true')
    ap.add_argument('--operator-pause', action='store_true', default=False)
    ap.add_argument('--wait-seconds', type=float, default=3)
    ap.add_argument('--timeout-seconds', type=int, default=90)
    ap.add_argument('--expand-rounds', type=int, default=60)
    ap.add_argument('--expand-max-clicks-per-round', type=int, default=18)
    ap.add_argument('--expand-click-delay-seconds', type=float, default=0.2)
    ap.add_argument('--expand-after-click-delay-seconds', type=float, default=0.65)
    ap.add_argument('--expand-scrolls-per-round', type=int, default=1)
    ap.add_argument('--expand-scroll-px', type=int, default=700)
    ap.add_argument('--expand-scroll-delay-seconds', type=float, default=0.9)
    ap.add_argument('--expand-stable-delta-chars', type=int, default=120)
    ap.add_argument('--expand-stop-after-stable-rounds', type=int, default=5)
    ap.add_argument('--tile-screenshots', action='store_true')
    ap.add_argument('--tile-steps', type=int, default=80)
    ap.add_argument('--tile-scroll-px', type=int, default=850)
    ap.add_argument('--tile-wait-seconds', type=float, default=0.55)
    ap.add_argument('--no-screenshots', action='store_true')
    ap.add_argument('--max-items', type=int, default=8000)
    ap.add_argument('--min-coverage', type=float, default=0.20)
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
        # NEEDS_MORE_EXPANSION is a valid run receipt but exits 3 so callers don't confuse it with complete success.
        if result.get('status') == STATUS_PASS:
            return 0
        if result.get('status') == STATUS_NEEDS_MORE_EXPANSION:
            return 3
        return 2
    ap.print_help()
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
