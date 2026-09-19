#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import profile_media_facebook_auto_expand_comments_runner_r45d as r45d

_ORIGINAL_R45D_SIDE_EFFECT_FLAGS = r45d.side_effect_flags

MARKER = "YTCE_R45F_FACEBOOK_MODAL_PROGRESS_HIDDEN_COMMENTS_RUNNER"
STATUS_PASS = "PASS_R45F_FACEBOOK_MODAL_PROGRESS_HIDDEN_COMMENTS_RUNNER"
STATUS_NEEDS_MORE_EXPANSION = "NEEDS_MORE_EXPANSION_R45F_FACEBOOK_MODAL_PROGRESS_HIDDEN_COMMENTS_RUNNER"
STATUS_BLOCKED = "BLOCKED_R45F_FACEBOOK_MODAL_PROGRESS_HIDDEN_COMMENTS_RUNNER"
SCHEMA_VERSION = "facebook_modal_progress_hidden_comments_runner.r45f.v1"

JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND = r'''
async (opts) => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const patterns = opts.patterns.map(p => new RegExp(p, 'i'));
  const deny = /^(like|reply|share|send|comment|copy link|follow|message|all|most relevant|newest|top comments)$/i;
  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
  };
  const labelOf = (el) => {
    const bits = [el.innerText || '', el.getAttribute('aria-label') || '', el.getAttribute('title') || '', el.textContent || ''];
    return bits.join(' ').replace(/\s+/g, ' ').trim();
  };
  const bodyText = () => (document.body && document.body.innerText || '');
  const pageTextLength = () => bodyText().length;
  const parseProgress = () => {
    const text = bodyText();
    const matches = Array.from(text.matchAll(/\b(\d{1,5})\s+of\s+(\d{1,5})\b/g));
    let best = null;
    for (const m of matches) {
      const current = parseInt(m[1], 10);
      const total = parseInt(m[2], 10);
      if (!Number.isFinite(current) || !Number.isFinite(total) || total <= 0) continue;
      if (current > total) continue;
      if (!best || total > best.total || (total === best.total && current > best.current)) {
        best = {current, total, ratio: current / total, text: `${current} of ${total}`};
      }
    }
    return best;
  };
  const visibleDialogs = () => Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"]')).filter(isVisible);
  const findDialog = () => {
    const dialogs = visibleDialogs();
    if (!dialogs.length) return null;
    const scored = dialogs.map(el => {
      const rect = el.getBoundingClientRect();
      const text = (el.innerText || '').toLowerCase();
      let score = rect.height * rect.width;
      if (/restore britain|post|comment|reply|view hidden comments|\d+\s+of\s+\d+/.test(text)) score += 2000000;
      return {el, score};
    }).sort((a,b)=>b.score-a.score);
    return scored[0].el;
  };
  const findScrollTargets = () => {
    const dialog = findDialog();
    const base = dialog ? [dialog, ...Array.from(dialog.querySelectorAll('div, section, main, article'))] : Array.from(document.querySelectorAll('div, section, main, article, [role="main"]'));
    const out = [];
    for (const el of base) {
      if (!isVisible(el)) continue;
      const rect = el.getBoundingClientRect();
      if (rect.height < 120 || rect.width < 260) continue;
      const scrollable = el.scrollHeight - el.clientHeight;
      const style = window.getComputedStyle(el);
      const overflow = ((style.overflowY || '') + ' ' + (style.overflow || '')).toLowerCase();
      const text = (el.innerText || '').slice(0, 1800).toLowerCase();
      const label = (el.getAttribute('aria-label') || el.getAttribute('role') || '').toLowerCase();
      let score = Math.max(0, scrollable) + rect.height;
      if (el === dialog) score += 4000000;
      if (/auto|scroll/.test(overflow)) score += 100000;
      if (/comment|reply/.test(label) || /view hidden comments|view all .* replies|view \d+ repl|write a comment|\d+\s+of\s+\d+/.test(text)) score += 250000;
      if (scrollable < 40 && el !== dialog) continue;
      out.push({el, score, scrollable, label: label.slice(0,80), height: Math.round(rect.height), width: Math.round(rect.width), top: Math.round(rect.top), left: Math.round(rect.left)});
    }
    out.sort((a,b) => b.score - a.score);
    return out.slice(0, 10);
  };
  const findCandidates = () => {
    const root = findDialog() || document;
    const selector = 'div[role="button"], span[role="button"], a[role="button"], button, a, [tabindex="0"]';
    const nodes = Array.from(root.querySelectorAll ? root.querySelectorAll(selector) : document.querySelectorAll(selector));
    const seen = new Set();
    const out = [];
    for (const el of nodes) {
      if (!isVisible(el)) continue;
      const text = labelOf(el);
      if (!text || text.length > 220) continue;
      if (deny.test(text)) continue;
      if (!patterns.some(rx => rx.test(text))) continue;
      const rect = el.getBoundingClientRect();
      const key = text + '|' + Math.round(rect.top) + '|' + Math.round(rect.left);
      if (seen.has(key)) continue;
      seen.add(key);
      let priority = 0;
      if (/hidden comments?/i.test(text)) priority += 10000;
      if (/view\s+\d+\s+repl/i.test(text)) priority += 5000;
      if (/view all\s+\d+\s+repl/i.test(text)) priority += 4000;
      if (/view more comments?|view previous comments?/i.test(text)) priority += 3000;
      if (/see more|show more/i.test(text)) priority += 1000;
      out.push({el, text, top: rect.top, left: rect.left, priority});
    }
    out.sort((a,b) => b.priority - a.priority || a.top - b.top || a.left - b.left);
    return out;
  };
  const clickCandidates = async () => {
    const candidates = findCandidates().slice(0, opts.maxClicksPerRound);
    let clicked = 0;
    const labels = [];
    for (const item of candidates) {
      try {
        item.el.scrollIntoView({block: 'center', inline: 'center'});
        await sleep(opts.clickDelayMs);
        item.el.click();
        clicked += 1;
        labels.push(item.text.slice(0, 160));
        await sleep(opts.afterClickDelayMs);
      } catch(e) {}
    }
    return {candidate_count: candidates.length, clicked, clicked_labels: labels};
  };
  const scrollLoad = async (px) => {
    let changed = 0;
    const targets = findScrollTargets();
    for (const item of targets.slice(0, 6)) {
      try {
        const el = item.el;
        const rect = el.getBoundingClientRect();
        if (typeof el.focus === 'function') { try { el.focus({preventScroll:true}); } catch(e) { try { el.focus(); } catch(e2) {} } }
        const before = el.scrollTop;
        if (typeof el.scrollBy === 'function') el.scrollBy({top: px, left: 0, behavior: 'instant'});
        else el.scrollTop = Math.min(el.scrollTop + px, el.scrollHeight);
        el.dispatchEvent(new WheelEvent('wheel', {deltaY: px, bubbles: true, cancelable: true, clientX: rect.left + Math.min(rect.width/2, 400), clientY: rect.top + Math.min(rect.height/2, 400)}));
        el.dispatchEvent(new Event('scroll', {bubbles: true}));
        if (Math.abs(el.scrollTop - before) > 2) changed += 1;
      } catch(e) {}
    }
    try {
      const beforeY = window.scrollY;
      window.scrollBy(0, px);
      window.dispatchEvent(new WheelEvent('wheel', {deltaY: px, bubbles: true, cancelable: true}));
      if (Math.abs(window.scrollY - beforeY) > 2) changed += 1;
    } catch(e) {}
    await sleep(opts.scrollDelayMs);
    return {changed, targets: targets.map(t => ({scrollable: t.scrollable, label: t.label, height: t.height, width: t.width, top: t.top})).slice(0, 5)};
  };
  const stats = [];
  let totalClicks = 0;
  let totalScrollEvents = 0;
  let stableRounds = 0;
  let previousTextLength = pageTextLength();
  let previousProgress = parseProgress();
  for (let round = 1; round <= opts.rounds; round++) {
    let progressBefore = parseProgress();
    const c1 = await clickCandidates();
    totalClicks += c1.clicked;
    let scrollChanged = 0;
    let lastTargets = [];
    for (let s = 0; s < opts.scrollsPerRound; s++) {
      const sc = await scrollLoad(opts.scrollPx);
      scrollChanged += sc.changed;
      totalScrollEvents += 1;
      lastTargets = sc.targets;
      const c2 = await clickCandidates();
      c1.candidate_count += c2.candidate_count;
      c1.clicked += c2.clicked;
      totalClicks += c2.clicked;
      c1.clicked_labels.push(...c2.clicked_labels);
    }
    if (round % 6 === 0) {
      for (const item of findScrollTargets().slice(0, 3)) {
        try { item.el.scrollTop = item.el.scrollHeight; item.el.dispatchEvent(new Event('scroll', {bubbles:true})); } catch(e) {}
      }
      await sleep(opts.scrollDelayMs);
    }
    const currentTextLength = pageTextLength();
    const delta = currentTextLength - previousTextLength;
    const progressAfter = parseProgress();
    const progressDelta = progressAfter && previousProgress ? (progressAfter.current - previousProgress.current) : (progressAfter && !previousProgress ? progressAfter.current : 0);
    stats.push({round, candidate_count: c1.candidate_count, clicked: c1.clicked, delta_text_chars: delta, text_chars: currentTextLength, scroll_changed: scrollChanged, progress_before: progressBefore, progress_after: progressAfter, progress_delta: progressDelta, scroll_targets: lastTargets, clicked_labels: c1.clicked_labels.slice(0, 35)});
    const progressComplete = progressAfter && progressAfter.total > 0 && progressAfter.current >= progressAfter.total;
    if (c1.clicked === 0 && Math.abs(delta) < opts.stableDeltaChars && scrollChanged === 0 && progressDelta <= 0) stableRounds += 1;
    else stableRounds = 0;
    previousTextLength = currentTextLength;
    previousProgress = progressAfter || previousProgress;
    if (progressComplete && stableRounds >= Math.min(4, opts.stopAfterStableRounds)) break;
    if (!progressComplete && progressAfter && progressAfter.total > 0 && progressAfter.current < progressAfter.total) {
      if (stableRounds >= Math.max(opts.stopAfterStableRounds, 20)) break;
    } else if (stableRounds >= opts.stopAfterStableRounds) break;
  }
  return {rounds_completed: stats.length, total_clicks: totalClicks, total_scroll_events: totalScrollEvents, final_text_chars: previousTextLength, final_progress: parseProgress(), stats};
}
'''


def sanitize_target_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    text = value.strip().strip('"').strip("'")
    urls = re.findall(r'https?://[^\]\)\s]+', text)
    if urls:
        text = urls[-1]
    text = text.replace('\\&', '&').replace('&amp;', '&').rstrip(').,;')
    return text.strip()


def contract() -> Dict[str, Any]:
    return {
        'marker': MARKER,
        'mode_id': 'facebook_modal_progress_hidden_comments_runner',
        'schema_version': SCHEMA_VERSION,
        'primary_route': 'operator-controlled signed-in Facebook Chromium/WebView2 session; sanitize pasted URL; target the Facebook post modal/dialog; click hidden-comments/reply/see-more controls; scroll modal/comment containers until modal progress is stable; then capture DOM/text/screenshots',
        'r45e_gap_fixed': 'R45E scroll-loaded page/comment containers, but the live page showed a Facebook post modal with progress like 438 of 715 and controls such as View hidden comments / View 1 reply. R45F prefers the modal/dialog scroller and uses modal progress as a completeness signal.',
        'modal_progress_rule': 'detect visible progress text like 438 of 715; do not report success from stability alone while current is below total unless coverage threshold is met or the operator accepts the run manually',
        'hidden_comments_rule': 'click visible View hidden comments controls plus View 1 reply/View all replies/View more replies/See more controls',
        'auto_expand_rule': 'click only visible page controls; do not use hidden Facebook APIs, Graph endpoints, cookies, tokens, or profile-file parsing',
        'scroll_load_rule': 'scroll the modal/dialog and large visible scrollable comment containers before and after expansion clicks',
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


def side_effect_flags(browser: bool, network: bool, auto_clicks: bool) -> Dict[str, Any]:
    flags = _ORIGINAL_R45D_SIDE_EFFECT_FLAGS(browser, network, auto_clicks)
    flags['scroll_load_sweeps_performed'] = bool(auto_clicks)
    flags['modal_progress_detection_performed'] = bool(auto_clicks)
    flags['visible_hidden_comments_clicks_supported'] = True
    flags['facebook_modal_progress_hidden_comments_runner_invoked'] = True
    flags.pop('facebook_auto_expand_comments_runner_invoked', None)
    return flags


def patch_r45d_globals() -> None:
    r45d.MARKER = MARKER
    r45d.STATUS_PASS = STATUS_PASS
    r45d.STATUS_NEEDS_MORE_EXPANSION = STATUS_NEEDS_MORE_EXPANSION
    r45d.STATUS_BLOCKED = STATUS_BLOCKED
    r45d.SCHEMA_VERSION = SCHEMA_VERSION
    r45d.EXPAND_PATTERNS = [
        r'view\s+hidden\s+comments?',
        r'view\s+\d+\s+hidden\s+comments?',
        r'hidden\s+comments?',
        r'view\s+(?:more|previous)\s+comments?',
        r'view\s+\d+\s+more\s+comments?',
        r'view\s+(?:more|previous)\s+repl(?:y|ies)',
        r'view\s+\d+\s+more\s+repl(?:y|ies)',
        r'view\s+all\s+\d+\s+repl(?:y|ies)',
        r'view\s+\d+\s+repl(?:y|ies)',
        r'view\s+repl(?:y|ies)',
        r'see\s+more',
        r'show\s+more',
        r'more\s+comments?',
        r'more\s+repl(?:y|ies)',
    ]
    r45d.JS_AUTO_EXPAND = JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND
    r45d.sanitize_target_url = sanitize_target_url
    r45d.contract = contract
    r45d.side_effect_flags = side_effect_flags


def build_static_capture(candidate_text: str, output_root: Path, reference_text: Optional[str] = None, source_url: str = 'static_text', min_coverage: float = 0.25) -> Dict[str, Any]:
    patch_r45d_globals()
    return r45d.build_static_capture(candidate_text, output_root, reference_text=reference_text, source_url=source_url, min_coverage=min_coverage)


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    patch_r45d_globals()
    raw_url = '[https://www.facebook.com/permalink.php?story_fbid=abc&id=123](https://www.facebook.com/permalink.php?story_fbid=abc\\&id=123)'
    recovered = sanitize_target_url(raw_url)
    reference = '''Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore, but this graph is so skewed.
Alex Barron
Context is everything
'''
    result = build_static_capture(reference, Path(args.output_root), reference_text=reference, source_url='self_test_fixture', min_coverage=0.99)
    joined_patterns = '\n'.join(r45d.EXPAND_PATTERNS).lower()
    checks = [
        {'name': 'markdown_url_sanitizer_recovers_raw_url', 'status': 'pass' if recovered == 'https://www.facebook.com/permalink.php?story_fbid=abc&id=123' else 'fail', 'recovered': recovered},
        {'name': 'modal_progress_parser_present', 'status': 'pass' if 'parseProgress' in JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND and r'of\s+' in JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND else 'fail'},
        {'name': 'view_hidden_comments_pattern_supported', 'status': 'pass' if 'view\\s+hidden' in joined_patterns and 'hidden comments' in JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND.lower() else 'fail'},
        {'name': 'modal_dialog_scroller_preferred', 'status': 'pass' if 'findDialog' in JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND and '[role="dialog"]' in JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND else 'fail'},
        {'name': 'view_one_reply_pattern_supported', 'status': 'pass' if 'view\\s+\\d+\\s+repl' in joined_patterns else 'fail'},
        {'name': 'reference_comparison_matches_sentinels', 'status': 'pass' if result['comparison'] and result['comparison']['coverage_ratio'] >= 0.99 and all(result['comparison']['sentinel_report'].values()) else 'fail'},
        {'name': 'side_effects_safe', 'status': 'pass' if not any(v for k, v in result['side_effect_flags'].items() if k not in {'facebook_modal_progress_hidden_comments_runner_invoked','visible_hidden_comments_clicks_supported'}) else 'fail'},
    ]
    status = STATUS_PASS if all(c['status'] == 'pass' for c in checks) else STATUS_BLOCKED
    report = {'marker': MARKER, 'status': status, 'schema_version': SCHEMA_VERSION, 'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(), 'checks': checks, 'sample_result': result, 'contract': contract(), 'side_effect_flags': side_effect_flags(False, False, False)}
    r45d.write_json(Path(args.output_root) / 'r45f_self_test_report.json', report)
    print(MARKER)
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    patch_r45d_globals()
    ap = r45d.build_arg_parser()
    ap.description = 'R45F Facebook modal progress + hidden-comments runner'
    ap.set_defaults(output_root='profile_media_live_captures/r45f_facebook_modal_progress_hidden_comments_runner')
    ap.set_defaults(expand_rounds=420)
    ap.set_defaults(expand_max_clicks_per_round=32)
    ap.set_defaults(expand_scrolls_per_round=9)
    ap.set_defaults(expand_scroll_px=950)
    ap.set_defaults(expand_stop_after_stable_rounds=24)
    ap.set_defaults(tile_steps=260)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    patch_r45d_globals()
    ap = build_arg_parser()
    args = ap.parse_args(argv)
    if args.self_test:
        report = run_self_test(args)
        return 0 if report.get('status') == STATUS_PASS else 2
    if args.candidate_text:
        result = r45d.run_from_text_files(args)
        return 0 if result.get('status') == STATUS_PASS else 2
    if args.target_url or args.manual_current_page:
        result = r45d.run_live(args)
        if result.get('status') == STATUS_PASS:
            return 0
        if result.get('status') == STATUS_NEEDS_MORE_EXPANSION:
            return 3
        return 2
    ap.print_help()
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
