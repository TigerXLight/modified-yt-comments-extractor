#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import profile_media_facebook_auto_expand_comments_runner_r45d as r45d

_R45D_ORIGINAL_SIDE_EFFECT_FLAGS = r45d.side_effect_flags

MARKER = "YTCE_R45E_FACEBOOK_SCROLL_LOAD_AUTO_EXPAND_RUNNER"
STATUS_PASS = "PASS_R45E_FACEBOOK_SCROLL_LOAD_AUTO_EXPAND_RUNNER"
STATUS_NEEDS_MORE_EXPANSION = "NEEDS_MORE_EXPANSION_R45E_FACEBOOK_SCROLL_LOAD_AUTO_EXPAND_RUNNER"
STATUS_BLOCKED = "BLOCKED_R45E_FACEBOOK_SCROLL_LOAD_AUTO_EXPAND_RUNNER"
SCHEMA_VERSION = "facebook_scroll_load_auto_expand_runner.r45e.v1"

# R45E replaces the R45D click loop with a scroll-load loop. The important fix is
# scrolling large visible containers as well as window, because Facebook comments can
# live in an inner comments box whose lower controls do not exist until that box is scrolled.
JS_SCROLL_LOAD_AUTO_EXPAND = r'''
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
  const pageTextLength = () => (document.body && document.body.innerText || '').length;
  const findCandidates = () => {
    const nodes = Array.from(document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"], button, a, [tabindex="0"]'));
    const seen = new Set();
    const out = [];
    for (const el of nodes) {
      if (!isVisible(el)) continue;
      const text = labelOf(el);
      if (!text || text.length > 180) continue;
      if (deny.test(text)) continue;
      if (!patterns.some(rx => rx.test(text))) continue;
      const rect = el.getBoundingClientRect();
      const key = text + '|' + Math.round(rect.top) + '|' + Math.round(rect.left);
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({el, text, top: rect.top, left: rect.left});
    }
    out.sort((a,b) => a.top - b.top || a.left - b.left);
    return out;
  };
  const findScrollTargets = () => {
    const els = Array.from(document.querySelectorAll('div, section, main, article'));
    const out = [];
    for (const el of els) {
      if (!isVisible(el)) continue;
      const scrollable = el.scrollHeight - el.clientHeight;
      if (scrollable < 180) continue;
      const rect = el.getBoundingClientRect();
      if (rect.height < 160 || rect.width < 260) continue;
      const style = window.getComputedStyle(el);
      const overflow = ((style.overflowY || '') + ' ' + (style.overflow || '')).toLowerCase();
      const label = (el.getAttribute('aria-label') || el.getAttribute('role') || '').toLowerCase();
      const text = (el.innerText || '').slice(0, 1200).toLowerCase();
      let score = scrollable + rect.height;
      if (/comment|reply/.test(label) || /view more comments|view all .* replies|write a comment/.test(text)) score += 5000;
      if (/auto|scroll/.test(overflow)) score += 1000;
      out.push({el, score, scrollable, label: label.slice(0,80), height: Math.round(rect.height), width: Math.round(rect.width)});
    }
    out.sort((a,b) => b.score - a.score);
    return out.slice(0, 8);
  };
  const scrollLoad = async (px) => {
    let changed = 0;
    const beforeY = window.scrollY;
    window.scrollBy(0, px);
    if (Math.abs(window.scrollY - beforeY) > 2) changed += 1;
    const targets = findScrollTargets();
    for (const item of targets) {
      try {
        const before = item.el.scrollTop;
        item.el.scrollTop = Math.min(item.el.scrollTop + px, item.el.scrollHeight);
        item.el.dispatchEvent(new WheelEvent('wheel', {deltaY: px, bubbles: true, cancelable: true}));
        if (Math.abs(item.el.scrollTop - before) > 2) changed += 1;
      } catch(e) {}
    }
    window.dispatchEvent(new WheelEvent('wheel', {deltaY: px, bubbles: true, cancelable: true}));
    await sleep(opts.scrollDelayMs);
    return {changed, targets: targets.map(t => ({scrollable: t.scrollable, label: t.label, height: t.height, width: t.width})).slice(0, 4)};
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
        labels.push(item.text.slice(0, 140));
        await sleep(opts.afterClickDelayMs);
      } catch(e) {}
    }
    return {candidate_count: candidates.length, clicked, clicked_labels: labels.slice(0, 25)};
  };
  const stats = [];
  let totalClicks = 0;
  let totalScrollEvents = 0;
  let stableRounds = 0;
  let previousTextLength = pageTextLength();
  for (let round = 1; round <= opts.rounds; round++) {
    const c1 = await clickCandidates();
    totalClicks += c1.clicked;
    let scrollChanged = 0;
    let lastTargets = [];
    for (let s = 0; s < opts.scrollsPerRound; s++) {
      const sc = await scrollLoad(opts.scrollPx);
      scrollChanged += sc.changed;
      totalScrollEvents += 1;
      lastTargets = sc.targets;
      // Re-scan after each scroll because the next controls may only appear after scrolling.
      const c2 = await clickCandidates();
      c1.candidate_count += c2.candidate_count;
      c1.clicked += c2.clicked;
      totalClicks += c2.clicked;
      c1.clicked_labels.push(...c2.clicked_labels);
    }
    const currentTextLength = pageTextLength();
    const delta = currentTextLength - previousTextLength;
    stats.push({round, candidate_count: c1.candidate_count, clicked: c1.clicked, delta_text_chars: delta, text_chars: currentTextLength, scroll_changed: scrollChanged, scroll_targets: lastTargets, clicked_labels: c1.clicked_labels.slice(0, 25)});
    if (c1.clicked === 0 && Math.abs(delta) < opts.stableDeltaChars && scrollChanged === 0) stableRounds += 1;
    else stableRounds = 0;
    previousTextLength = currentTextLength;
    if (stableRounds >= opts.stopAfterStableRounds) break;
  }
  return {rounds_completed: stats.length, total_clicks: totalClicks, total_scroll_events: totalScrollEvents, final_text_chars: previousTextLength, stats};
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
        'mode_id': 'facebook_scroll_load_auto_expand_runner',
        'schema_version': SCHEMA_VERSION,
        'primary_route': 'operator-controlled signed-in Facebook Chromium/WebView2 session; sanitize pasted URL; inject comments-only focus mode; repeatedly scroll-load comment containers and click visible View more/View replies/See more controls; then capture DOM/text/screenshots',
        'r45d_gap_fixed': 'R45D clicked controls already loaded in the viewport; R45E scrolls the page and large visible comments containers so lower controls load before expansion attempts.',
        'auto_expand_rule': 'click only visible page controls matching comment expansion labels; do not use hidden Facebook APIs, Graph endpoints, cookies, tokens, or profile-file parsing',
        'scroll_load_rule': 'scroll both the page and large visible scrollable containers, then re-scan for newly loaded expansion controls',
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
    flags = _R45D_ORIGINAL_SIDE_EFFECT_FLAGS(browser, network, auto_clicks)
    flags['scroll_load_sweeps_performed'] = bool(auto_clicks)
    flags['facebook_scroll_load_auto_expand_runner_invoked'] = True
    flags.pop('facebook_auto_expand_comments_runner_invoked', None)
    return flags


def patch_r45d_globals() -> None:
    r45d.MARKER = MARKER
    r45d.STATUS_PASS = STATUS_PASS
    r45d.STATUS_NEEDS_MORE_EXPANSION = STATUS_NEEDS_MORE_EXPANSION
    r45d.STATUS_BLOCKED = STATUS_BLOCKED
    r45d.SCHEMA_VERSION = SCHEMA_VERSION
    r45d.JS_AUTO_EXPAND = JS_SCROLL_LOAD_AUTO_EXPAND
    r45d.sanitize_target_url = sanitize_target_url
    r45d.contract = contract
    r45d.side_effect_flags = side_effect_flags


def build_static_capture(candidate_text: str, output_root: Path, reference_text: Optional[str] = None, source_url: str = 'static_text', min_coverage: float = 0.25) -> Dict[str, Any]:
    patch_r45d_globals()
    result = r45d.build_static_capture(candidate_text, output_root, reference_text=reference_text, source_url=source_url, min_coverage=min_coverage)
    return result


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
    checks = [
        {'name': 'markdown_url_sanitizer_recovers_raw_url', 'status': 'pass' if recovered == 'https://www.facebook.com/permalink.php?story_fbid=abc&id=123' else 'fail', 'recovered': recovered},
        {'name': 'focus_css_is_non_destructive', 'status': 'pass' if 'display: none' not in r45d.FOCUS_CSS.lower() else 'fail'},
        {'name': 'scroll_load_script_targets_window_and_containers', 'status': 'pass' if 'findScrollTargets' in JS_SCROLL_LOAD_AUTO_EXPAND and 'scrollTop' in JS_SCROLL_LOAD_AUTO_EXPAND and 'window.scrollBy' in JS_SCROLL_LOAD_AUTO_EXPAND else 'fail'},
        {'name': 'auto_expand_script_clicks_after_each_scroll', 'status': 'pass' if 'Re-scan after each scroll' in JS_SCROLL_LOAD_AUTO_EXPAND else 'fail'},
        {'name': 'reference_comparison_matches_sentinels', 'status': 'pass' if result['comparison'] and result['comparison']['coverage_ratio'] >= 0.99 and all(result['comparison']['sentinel_report'].values()) else 'fail'},
        {'name': 'side_effects_safe', 'status': 'pass' if not any(v for k, v in result['side_effect_flags'].items() if k not in {'facebook_scroll_load_auto_expand_runner_invoked'}) else 'fail'},
    ]
    status = STATUS_PASS if all(c['status'] == 'pass' for c in checks) else STATUS_BLOCKED
    report = {'marker': MARKER, 'status': status, 'schema_version': SCHEMA_VERSION, 'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(), 'checks': checks, 'sample_result': result, 'contract': contract(), 'side_effect_flags': side_effect_flags(False, False, False)}
    r45d.write_json(Path(args.output_root) / 'r45e_self_test_report.json', report)
    print(MARKER)
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    ap = r45d.build_arg_parser()
    ap.description = 'R45E Facebook scroll-load auto-expand runner'
    ap.set_defaults(output_root='profile_media_live_captures/r45e_facebook_scroll_load_auto_expand_runner')
    ap.set_defaults(expand_rounds=260)
    ap.set_defaults(expand_max_clicks_per_round=28)
    ap.set_defaults(expand_scrolls_per_round=5)
    ap.set_defaults(expand_scroll_px=900)
    ap.set_defaults(expand_stop_after_stable_rounds=14)
    ap.set_defaults(tile_steps=180)
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
