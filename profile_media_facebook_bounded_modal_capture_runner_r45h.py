#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import profile_media_facebook_auto_expand_comments_runner_r45d as r45d
import profile_media_facebook_modal_hidden_replies_runner_r45g as r45g

MARKER = "YTCE_R45H_FACEBOOK_BOUNDED_MODAL_CAPTURE_RUNNER"
STATUS_PASS = "PASS_R45H_FACEBOOK_BOUNDED_MODAL_CAPTURE_RUNNER"
STATUS_NEEDS_MORE_EXPANSION = "NEEDS_MORE_EXPANSION_R45H_FACEBOOK_BOUNDED_MODAL_CAPTURE_RUNNER"
STATUS_BLOCKED = "BLOCKED_R45H_FACEBOOK_BOUNDED_MODAL_CAPTURE_RUNNER"
SCHEMA_VERSION = "facebook_bounded_modal_capture_runner.r45h.v1"

EXPAND_PATTERNS_R45H = list(r45g.EXPAND_PATTERNS_R45G) + [
    r'\bview\s+hidden\s+repl(?:y|ies)\b',
    r'\bview\s+hidden\s+comments?\b',
    r'\bview\s+(?:all|more)\s+\d+\s+repl(?:y|ies)\b',
    r'\bview\s+\d+\s+repl(?:y|ies)\b',
    r'\bview\s+(?:previous|more)\s+repl(?:y|ies)\b',
    r'\breplied\s*[·•\-–—]\s*\d+\s+repl(?:y|ies)\b',
]

JS_BOUNDED_MODAL_AUTO_EXPAND = r'''
async (opts) => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const startedAt = Date.now();
  const maxMillis = Math.max(15000, (opts.maxSeconds || 180) * 1000);
  const progressiveTopDown = !!opts.progressiveTopDown;
  const viewportMarginPx = Number(opts.viewportMarginPx || 90);
  // R45Q/R45R: keep the fast single downward frontier. maxTopDownSweeps
  // is retained for CLI compatibility only; it must not trigger a global
  // scroll-to-top rescan and must not limit local viewport exhaustion.
  // R45R locally exhausts the current visible area even when the operator
  // passes --progressive-top-down-sweeps 1, so newly exposed View all /
  // View hidden replies controls are opened before the frontier moves down.
  const requestedLocalPasses = Number(opts.localExhaustPasses || 0);
  // R45S: strict first-visible-click mode needs a high local pass ceiling,
  // because each pass intentionally clicks exactly one topmost visible control.
  const localExhaustPasses = Math.max(500, requestedLocalPasses || Math.max(500, Number(opts.maxTopDownSweeps || 1) * 500));
  const patterns = opts.patterns.map(p => new RegExp(p, 'i'));
  const deny = /^(like|reply|share|send|comment|copy link|follow|message|all|most relevant|newest|top comments|edited)$/i;
  const log = (obj) => { try { console.log('R45H_PROGRESS ' + JSON.stringify(obj)); } catch(e) {} };
  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0' && style.pointerEvents !== 'none';
  };
  const labelOf = (el) => {
    const bits = [el.innerText || '', el.getAttribute('aria-label') || '', el.getAttribute('title') || '', el.textContent || ''];
    return bits.join(' ').replace(/\s+/g, ' ').trim();
  };
  const clickTargetFor = (el) => {
    let n = el;
    for (let i = 0; n && i < 7; i++, n = n.parentElement) {
      const role = (n.getAttribute('role') || '').toLowerCase();
      const tag = (n.tagName || '').toLowerCase();
      const style = window.getComputedStyle(n);
      if (role === 'button' || tag === 'a' || tag === 'button' || tag === 'summary' || style.cursor === 'pointer') return n;
    }
    return el;
  };
  const pageText = () => (document.body && document.body.innerText || '');
  const pageTextLength = () => pageText().length;
  const parseProgress = () => {
    const m = pageText().match(/\b(\d{1,5})\s+of\s+(\d{1,5})\b/);
    if (!m) return null;
    return {current: Number(m[1]), total: Number(m[2]), text: m[0]};
  };
  const targetKeyFor = (target) => {
    const r = target.getBoundingClientRect();
    return [Math.round((r.top + window.scrollY) / 3), Math.round(r.left / 3), Math.round(r.width / 3), Math.round(r.height / 3)].join(':');
  };
  const canonicalLabel = (text) => {
    const m = text.match(/\b(View\s+(?:hidden\s+(?:comments?|repl(?:y|ies))|all\s+\d+\s+repl(?:y|ies)|more\s+\d+\s+repl(?:y|ies)|\d+\s+repl(?:y|ies)|previous\s+repl(?:y|ies)|more\s+repl(?:y|ies)))\b/i);
    if (m) return m[1].toLowerCase().replace(/\s+/g, ' ');
    const r = text.match(/\breplied\s*[·•\-–—]\s*\d+\s+repl(?:y|ies)\b/i);
    return (r ? r[0] : text.slice(0, 80)).toLowerCase().replace(/\s+/g, ' ');
  };
  const expansionMatchText = (text) => {
    const m = text.match(/\b(View\s+(?:hidden\s+(?:comments?|repl(?:y|ies))|all\s+\d+\s+repl(?:y|ies)|more\s+\d+\s+repl(?:y|ies)|\d+\s+repl(?:y|ies)|previous\s+repl(?:y|ies)|more\s+repl(?:y|ies)))\b/i);
    if (m) return m[1].replace(/\s+/g, ' ').trim();
    const r = text.match(/\b[\p{L}\p{M}' .-]{1,80}\s+replied\s*[·•\-–—]\s*\d+\s+repl(?:y|ies)\b/iu);
    return r ? r[0].replace(/\s+/g, ' ').trim() : '';
  };
  const looksLikeBloatedCommentContainer = (text) => {
    if (text.length <= 140) return false;
    if (/^\s*(view|see)\b/i.test(text)) return false;
    if (/\breplied\s*[·•\-–—]\s*\d+\s+repl/i.test(text) && text.length < 180) return false;
    return /\bLike\b.*\bReply\b/i.test(text) || text.length > 220;
  };
  const visibleUnresolvedLabels = () => {
    const out = [];
    const nodes = Array.from(document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"], button, a, [tabindex="0"], span, div'));
    for (const el of nodes) {
      if (!isVisible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.bottom <= 0 || r.top > window.innerHeight + viewportMarginPx) continue;
      const text = labelOf(el);
      const m = expansionMatchText(text);
      if (m) out.push(m);
      if (out.length >= 12) break;
    }
    return Array.from(new Set(out));
  };
  const findCandidates = () => {
    // R45Q: top-to-bottom, downward-only frontier. We click controls visible in
    // the current viewport and locally exhaust newly exposed controls before
    // scrolling down. We do not perform a global scroll-back-to-top rescan.
    const nodes = Array.from(document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"], button, a, [tabindex="0"], span, div'));
    const byTarget = new Map();
    for (const el of nodes) {
      if (!isVisible(el)) continue;
      const text = labelOf(el);
      if (!text || text.length > 320) continue;
      if (deny.test(text)) continue;
      const matched = expansionMatchText(text);
      if (!matched && !patterns.some(rx => rx.test(text))) continue;
      // R45S: avoid treating a whole comment bubble containing "Like Reply ... View all"
      // as the clickable control. Prefer the actual first visible expansion label.
      if (looksLikeBloatedCommentContainer(text)) continue;
      const target = clickTargetFor(el);
      if (!target || !isVisible(target)) continue;
      const rect = target.getBoundingClientRect();
      if (progressiveTopDown) {
        // Strict forward sweep: do not reach back above the viewport for a
        // missed button. Anything missed above is intentionally not revisited.
        if (rect.bottom <= 0 || rect.top > window.innerHeight + viewportMarginPx) continue;
      }
      const directRect = el.getBoundingClientRect();
      const key = canonicalLabel(text) + '|' + Math.round((directRect.top + window.scrollY) / 8) + ':' + Math.round(directRect.left / 8);
      let priority = 0;
      if (/hidden\s+(?:comments?|repl(?:y|ies))/i.test(text)) priority += 20000;
      if (/view\s+(?:all|more)\s+\d+\s+repl/i.test(text)) priority += 12000;
      if (/view\s+\d+\s+repl/i.test(text)) priority += 9000;
      if (/replied\s*[·•\-–—]\s*\d+\s+repl/i.test(text)) priority += 8000;
      if (/view all|view more|see more/i.test(text)) priority += 4000;
      const item = {el: target, text, top: rect.top, left: rect.left, priority};
      const old = byTarget.get(key);
      if (!old || text.length < old.text.length || priority > old.priority) byTarget.set(key, item);
    }
    const out = Array.from(byTarget.values());
    // R45S: strict user-requested order is first visible clickable, then next.
    // Priority is only a tie-breaker for overlapping elements on the same row.
    if (progressiveTopDown) out.sort((a,b) => a.top - b.top || a.left - b.left || b.priority - a.priority);
    else out.sort((a,b) => b.priority - a.priority || a.top - b.top || a.left - b.left);
    return out;
  };
  const findScrollTargets = () => {
    const els = Array.from(document.querySelectorAll('[role="dialog"], div, section, main, article'));
    const out = [];
    for (const el of els) {
      if (!isVisible(el)) continue;
      const scrollable = el.scrollHeight - el.clientHeight;
      if (scrollable < 120) continue;
      const rect = el.getBoundingClientRect();
      if (rect.height < 140 || rect.width < 260) continue;
      const style = window.getComputedStyle(el);
      const overflow = ((style.overflowY || '') + ' ' + (style.overflow || '')).toLowerCase();
      const role = (el.getAttribute('role') || '').toLowerCase();
      const aria = (el.getAttribute('aria-label') || '').toLowerCase();
      const text = (el.innerText || '').slice(0, 1800).toLowerCase();
      let score = scrollable + rect.height;
      if (role === 'dialog') score += 20000;
      if (/restore britain|comment|reply|view hidden|write a comment|of\s+\d+/.test(text + ' ' + aria)) score += 8000;
      if (/auto|scroll/.test(overflow)) score += 1000;
      out.push({el, score, role, aria: aria.slice(0, 80), scrollable, height: Math.round(rect.height), width: Math.round(rect.width)});
    }
    out.sort((a,b) => b.score - a.score);
    return out.slice(0, 10);
  };
  const scrollLoad = async (px) => {
    let changed = 0;
    const targets = findScrollTargets();
    for (const item of targets) {
      try {
        const before = item.el.scrollTop;
        item.el.scrollTop = Math.min(item.el.scrollTop + px, item.el.scrollHeight);
        item.el.dispatchEvent(new WheelEvent('wheel', {deltaY: px, bubbles: true, cancelable: true}));
        if (Math.abs(item.el.scrollTop - before) > 2) changed += 1;
      } catch(e) {}
    }
    const beforeY = window.scrollY;
    window.scrollBy(0, px);
    window.dispatchEvent(new WheelEvent('wheel', {deltaY: px, bubbles: true, cancelable: true}));
    if (Math.abs(window.scrollY - beforeY) > 2) changed += 1;
    await sleep(opts.scrollDelayMs);
    return {changed, targets: targets.map(t => ({role: t.role, aria: t.aria, scrollable: t.scrollable, height: t.height, width: t.width})).slice(0, 4)};
  };
  const clickOne = async (item) => {
    try {
      const before = item.el.getBoundingClientRect();
      if (before.top < 0 || before.bottom > window.innerHeight) item.el.scrollIntoView({block: 'nearest', inline: 'nearest'});
      await sleep(opts.clickDelayMs);
      const after = item.el.getBoundingClientRect();
      if (progressiveTopDown && after.bottom <= 0) return false;
      item.el.click();
      await sleep(opts.afterClickDelayMs);
      return true;
    } catch(e) { return false; }
  };
  const clickVisibleUntilExhausted = async () => {
    let candidateCount = 0;
    let clicked = 0;
    const labels = [];
    let idleVisibleChecks = 0;
    for (let pass = 0; pass < localExhaustPasses; pass++) {
      if (Date.now() - startedAt > maxMillis) break;
      const candidates = findCandidates();
      candidateCount += candidates.length;
      if (!candidates.length) {
        const unresolved = visibleUnresolvedLabels();
        if (unresolved.length && idleVisibleChecks < 3) {
          idleVisibleChecks += 1;
          await sleep(Math.max(80, opts.afterClickDelayMs));
          continue;
        }
        break;
      }
      idleVisibleChecks = 0;
      // R45S: click exactly one first visible expansion control, then rescan.
      // Do not batch-click the 100+ collected candidates; Facebook mutates the
      // thread after each click and batching skips newly exposed controls.
      const item = candidates[0];
      const beforeText = pageTextLength();
      const beforeHeight = Math.max(document.body ? document.body.scrollHeight : 0, ...findScrollTargets().map(t => t.el.scrollHeight || 0));
      const ok = await clickOne(item);
      if (ok) {
        clicked += 1;
        labels.push(item.text.slice(0, 160));
        await sleep(Math.max(80, opts.afterClickDelayMs));
        const afterText = pageTextLength();
        const afterHeight = Math.max(document.body ? document.body.scrollHeight : 0, ...findScrollTargets().map(t => t.el.scrollHeight || 0));
        if (afterText === beforeText && afterHeight === beforeHeight) {
          // A no-op click can still be Facebook latency. Give it one short
          // breath, then the next loop rescans rather than assuming success.
          await sleep(Math.max(120, opts.afterClickDelayMs));
        }
      } else {
        await sleep(Math.max(80, opts.clickDelayMs));
      }
    }
    return {candidate_count: candidateCount, clicked, clicked_labels: labels.slice(0, 40), visible_unresolved_labels: visibleUnresolvedLabels().slice(0, 12)};
  };
  const stats = [];
  let totalClicks = 0;
  let totalScrollEvents = 0;
  let stableRounds = 0;
  let previousTextLength = pageTextLength();
  let previousProgress = parseProgress();
  let timedOut = false;
  const topDownSweep = 1;
  if (progressiveTopDown) {
    // R45R: a downward-only frontier must start from the earliest loaded
    // position. Otherwise a reused/manual browser state can begin mid-thread
    // and permanently skip controls above the initial viewport. This is not a
    // later global rescan; it is the initial frontier placement.
    try {
      for (const item of findScrollTargets()) item.el.scrollTop = 0;
      window.scrollTo(0, 0);
      window.dispatchEvent(new WheelEvent('wheel', {deltaY: -1200, bubbles: true, cancelable: true}));
      await sleep(opts.scrollDelayMs);
    } catch(e) {}
  }
  for (let round = 1; round <= opts.rounds; round++) {
    if (Date.now() - startedAt > maxMillis) { timedOut = true; break; }
    const c = await clickVisibleUntilExhausted();
    totalClicks += c.clicked;
    let scrollChanged = 0;
    let lastTargets = [];
    for (let s = 0; s < opts.scrollsPerRound; s++) {
      if (Date.now() - startedAt > maxMillis) { timedOut = true; break; }
      const sc = await scrollLoad(opts.scrollPx);
      scrollChanged += sc.changed;
      totalScrollEvents += 1;
      lastTargets = sc.targets;
      const c2 = await clickVisibleUntilExhausted();
      c.candidate_count += c2.candidate_count;
      c.clicked += c2.clicked;
      totalClicks += c2.clicked;
      c.clicked_labels.push(...c2.clicked_labels);
    }
    const currentTextLength = pageTextLength();
    const delta = currentTextLength - previousTextLength;
    const progress = parseProgress();
    const progressChanged = JSON.stringify(progress) !== JSON.stringify(previousProgress);
    const remainingVisibleCandidates = findCandidates().length;
    const visibleUnresolved = visibleUnresolvedLabels();
    const row = {round, top_down_sweep: topDownSweep, downward_only: true, first_visible_click_mode: true, candidate_count: c.candidate_count, clicked: c.clicked, remaining_visible_candidates: remainingVisibleCandidates, visible_unresolved_labels: visibleUnresolved.slice(0, 12), delta_text_chars: delta, text_chars: currentTextLength, scroll_changed: scrollChanged, progress, progress_changed: progressChanged, elapsed_seconds: Math.round((Date.now()-startedAt)/1000), scroll_targets: lastTargets, clicked_labels: c.clicked_labels.slice(0, 25)};
    stats.push(row);
    log(row);
    const progressIncomplete = progress && progress.total && progress.current < progress.total;
    if (c.clicked === 0 && remainingVisibleCandidates === 0 && visibleUnresolved.length === 0 && !progressIncomplete && Math.abs(delta) < opts.stableDeltaChars && scrollChanged === 0 && !progressChanged) stableRounds += 1;
    else stableRounds = 0;
    previousTextLength = currentTextLength;
    previousProgress = progress;
    if (stableRounds >= opts.stopAfterStableRounds) break;
  }
  const remainingVisibleCandidates = findCandidates().length;
  const finalVisibleUnresolved = visibleUnresolvedLabels();
  const mainProgressIncomplete = previousProgress && previousProgress.total && previousProgress.current < previousProgress.total;
  return {rounds_completed: stats.length, total_clicks: totalClicks, total_scroll_events: totalScrollEvents, final_text_chars: previousTextLength, final_progress: previousProgress, timed_out: timedOut, downward_only: true, global_rescan_used: false, first_visible_click_mode: true, remaining_visible_candidates: remainingVisibleCandidates, visible_unresolved_labels: finalVisibleUnresolved.slice(0, 12), main_progress_incomplete: !!mainProgressIncomplete, top_down_sweeps_completed: topDownSweep, elapsed_seconds: Math.round((Date.now()-startedAt)/1000), stats};
}
'''



def contract() -> Dict[str, Any]:
    base = r45g.contract()
    base.update({
        'marker': MARKER,
        'mode_id': 'facebook_bounded_modal_capture_runner',
        'schema_version': SCHEMA_VERSION,
        'r45g_gap_fixed': 'R45G could appear stuck because auto-expand ran silently inside page.evaluate for many modal-scroll stability rounds. R45H adds bounded runtime, browser-console progress heartbeats, shorter defaults, and capture-after-timeout receipts.',
        'bounded_runtime_rule': 'auto-expand stops after --expand-max-seconds and still captures DOM/text/screenshots rather than appearing frozen indefinitely.',
        'progress_rule': 'emit R45H_PROGRESS browser console messages for each completed expansion round.',
        'r45o_progressive_top_down_rule': 'When requested by R45J, expansion clicks visible controls in viewport top-to-bottom order before continuing downward, reducing jump-back behaviour on long Facebook modal threads.',
        'r45p_progressive_rescan_rule': 'R45P previously allowed a bounded top-to-bottom rescan, but this could jump back upward on long threads.',
        'r45q_downward_frontier_rule': 'R45Q keeps a single downward frontier: locally exhaust visible View hidden replies / View all N replies controls before scrolling further down, and never performs a global scroll-back-to-top rescan.',
        'r45r_local_exhaust_rule': 'R45R decouples local viewport exhaustion from global sweep count: even with --progressive-top-down-sweeps 1, newly exposed View all N replies / View hidden replies controls in the current area are exhausted before the frontier moves downward.',
        'r45s_first_visible_click_rule': 'R45S clicks exactly one first visible expansion control, rescans the same viewport, and only then moves to the next visible control or scrolls downward; it does not batch-click collected candidates.',
    })
    return base


def side_effect_flags(browser: bool, network: bool, auto_clicks: bool) -> Dict[str, Any]:
    flags = r45g.side_effect_flags(browser, network, auto_clicks)
    flags['bounded_auto_expand_supported'] = True
    flags['facebook_bounded_modal_capture_runner_invoked'] = True
    flags.pop('facebook_modal_hidden_replies_runner_invoked', None)
    return flags


def patch_r45d_globals() -> None:
    r45g.patch_r45d_globals()
    r45d.MARKER = MARKER
    r45d.STATUS_PASS = STATUS_PASS
    r45d.STATUS_NEEDS_MORE_EXPANSION = STATUS_NEEDS_MORE_EXPANSION
    r45d.STATUS_BLOCKED = STATUS_BLOCKED
    r45d.SCHEMA_VERSION = SCHEMA_VERSION
    r45d.EXPAND_PATTERNS = list(EXPAND_PATTERNS_R45H)
    r45d.JS_AUTO_EXPAND = JS_BOUNDED_MODAL_AUTO_EXPAND
    r45d.contract = contract
    r45d.side_effect_flags = side_effect_flags


def _safe_read_text(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return Path(path).read_text(encoding='utf-8', errors='replace')


def run_live(args: argparse.Namespace) -> Dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise SystemExit(f'{STATUS_BLOCKED}: Playwright is not available: {e}')

    patch_r45d_globals()
    output_root = Path(args.output_root)
    run_dir = r45d.ensure_dir(output_root / f'facebook_bounded_modal_capture_runner_{r45d.utc_stamp()}')
    reference_text = _safe_read_text(args.reference_text)
    target_url = r45d.sanitize_target_url(args.target_url)
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
        page.on('console', lambda msg: print(msg.text) if msg.text.startswith('R45H_PROGRESS') else None)
        if target_url and not args.manual_current_page:
            try:
                page.goto(target_url, wait_until='domcontentloaded', timeout=args.timeout_seconds * 1000)
            except Exception as e:
                warnings.append(f'initial_navigation_warning={e}')
        try:
            page.add_style_tag(content=r45d.FOCUS_CSS)
        except Exception as e:
            warnings.append(f'focus_css_injection_warning={e}')
        if args.pre_expand_pause:
            print('R45H_PRE_EXPAND_PAUSE')
            print('Check login/page, then press ENTER in this CMD window to start bounded auto-expand.')
            try: input()
            except EOFError: pass
        auto_expand_summary = None
        if args.auto_expand:
            opts = {
                'patterns': EXPAND_PATTERNS_R45H,
                'rounds': args.expand_rounds,
                'maxSeconds': args.expand_max_seconds,
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
                print(f'R45H_AUTO_EXPAND_START max_seconds={args.expand_max_seconds}')
                auto_expand_summary = page.evaluate(JS_BOUNDED_MODAL_AUTO_EXPAND, opts)
                print('R45H_AUTO_EXPAND_DONE')
            except Exception as e:
                warnings.append(f'auto_expand_warning={e}')
        if args.operator_pause:
            print('R45H_OPERATOR_PAUSE')
            print('Review comments. Press ENTER in this CMD window to capture.')
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
        raw_dom_path = r45d.write_text(run_dir / 'facebook_live_raw_dom.html', raw_html)
        inner_text_path = r45d.write_text(run_dir / 'facebook_live_visible_inner_text.txt', inner_text)
        focus_css_path = r45d.write_text(run_dir / 'facebook_comments_focus_mode.css', r45d.FOCUS_CSS.strip() + '\n')
        auto_expand_script_path = r45d.write_text(run_dir / 'facebook_bounded_auto_expand_script.js', JS_BOUNDED_MODAL_AUTO_EXPAND.strip() + '\n')
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
                    page.evaluate('(px) => { const d=document.querySelector("[role=dialog]"); if(d) d.scrollTop += px; window.scrollBy(0, px); }', args.tile_scroll_px)
                    time.sleep(max(0.15, args.tile_wait_seconds))
                except Exception as e:
                    warnings.append(f'tile_{i+1}_warning={e}')
                    break
        exports = r45d.write_comment_exports(run_dir, inner_text, max_items=args.max_items)
        comparison = r45d.compare_text(inner_text, reference_text) if reference_text is not None else None
        status = r45d.classify_status(inner_text, comparison, args.min_coverage)
        if status == STATUS_NEEDS_MORE_EXPANSION:
            warnings.append('comparison_coverage_below_threshold_more_comments_need_loading_or_expansion')
        if auto_expand_summary and auto_expand_summary.get('timed_out'):
            warnings.append('auto_expand_reached_max_seconds_captured_current_loaded_state')
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
        receipt['receipt_path'] = r45d.write_json(run_dir / 'r45h_facebook_bounded_modal_capture_runner_receipt.json', receipt)
        print(MARKER)
        print(status)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        try: context.close()
        except Exception: pass
        return receipt


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    patch_r45d_globals()
    reference = '''Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore, but this graph is so skewed.
Alex Barron
Context is everything
'''
    result = r45d.build_static_capture(reference, Path(args.output_root), reference_text=reference, source_url='self_test_fixture', min_coverage=0.99)
    joined_patterns = '\n'.join(EXPAND_PATTERNS_R45H).lower()
    checks = [
        {'name': 'bounded_timeout_supported', 'status': 'pass' if 'maxSeconds' in JS_BOUNDED_MODAL_AUTO_EXPAND and 'timedOut' in JS_BOUNDED_MODAL_AUTO_EXPAND else 'fail'},
        {'name': 'progress_console_supported', 'status': 'pass' if 'R45H_PROGRESS' in JS_BOUNDED_MODAL_AUTO_EXPAND else 'fail'},
        {'name': 'view_hidden_replies_pattern_supported', 'status': 'pass' if 'view\\s+hidden\\s+repl' in joined_patterns else 'fail'},
        {'name': 'modal_progress_parser_present', 'status': 'pass' if 'parseProgress' in JS_BOUNDED_MODAL_AUTO_EXPAND and 'of' in JS_BOUNDED_MODAL_AUTO_EXPAND else 'fail'},
        {'name': 'r45r_local_exhaust_not_limited_by_global_sweeps', 'status': 'pass' if 'requestedLocalPasses' in JS_BOUNDED_MODAL_AUTO_EXPAND and 'Math.max(12' in JS_BOUNDED_MODAL_AUTO_EXPAND else 'fail'},
        {'name': 'reference_comparison_matches_sentinels', 'status': 'pass' if result.get('comparison') and result['comparison']['coverage_ratio'] >= 0.99 and all(result['comparison']['sentinel_report'].values()) else 'fail'},
        {'name': 'side_effects_safe', 'status': 'pass' if not any(v for k, v in result['side_effect_flags'].items() if k not in {'facebook_bounded_modal_capture_runner_invoked','bounded_auto_expand_supported','visible_hidden_comments_clicks_supported','visible_hidden_replies_clicks_supported'}) else 'fail'},
    ]
    status = STATUS_PASS if all(c['status'] == 'pass' for c in checks) else STATUS_BLOCKED
    report = {'marker': MARKER, 'status': status, 'schema_version': SCHEMA_VERSION, 'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(), 'checks': checks, 'sample_result': result, 'contract': contract(), 'side_effect_flags': side_effect_flags(False, False, False)}
    r45d.write_json(Path(args.output_root) / 'r45h_self_test_report.json', report)
    print(MARKER)
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    patch_r45d_globals()
    ap = r45d.build_arg_parser()
    ap.description = 'R45H Facebook bounded modal capture runner'
    ap.set_defaults(output_root='profile_media_live_captures/r45h_facebook_bounded_modal_capture_runner')
    ap.set_defaults(expand_rounds=160)
    ap.set_defaults(expand_max_clicks_per_round=30)
    ap.set_defaults(expand_scrolls_per_round=5)
    ap.set_defaults(expand_scroll_px=950)
    ap.set_defaults(expand_stop_after_stable_rounds=6)
    ap.set_defaults(tile_steps=160)
    ap.add_argument('--expand-max-seconds', type=int, default=180)
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
        result = run_live(args)
        if result.get('status') == STATUS_PASS:
            return 0
        if result.get('status') == STATUS_NEEDS_MORE_EXPANSION:
            return 3
        return 2
    ap.print_help()
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
