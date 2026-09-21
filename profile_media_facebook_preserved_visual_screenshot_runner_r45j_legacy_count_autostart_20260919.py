#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import profile_media_facebook_auto_expand_comments_runner_r45d as r45d
import profile_media_facebook_bounded_modal_capture_runner_r45h_legacy_failfast_v2_20260919 as r45h

MARKER = "YTCE_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
STATUS_PASS = "PASS_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
STATUS_NEEDS_MORE_EXPANSION = "NEEDS_MORE_EXPANSION_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
STATUS_BLOCKED = "BLOCKED_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
SCHEMA_VERSION = "facebook_preserved_visual_screenshot_runner.r45j.v1"


R45AL_VISIBLE_EXPAND_PREFLIGHT_JS = r"""
() => {
  const rx = [
    /view\s+all\s+\d+\s+repl/i,
    /view\s+\d+\s+repl/i,
    /view\s+\d+\s+more\s+repl/i,
    /view\s+hidden\s+repl/i,
    /view\s+more\s+repl/i,
    /view\s+hidden\s+comments?/i,
    /view\s+(all\s+)?\d+\s+comments?/i,
    /replied\s*[·•.-]\s*\d+\s+repl/i
  ];
  const deny = /^(like|reply|share|send|comment|copy link|follow|message|all|most relevant|newest|top comments|edited)$/i;
  const norm = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const isVisible = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const s = window.getComputedStyle(el);
    return r.width > 0 && r.height > 0 &&
           r.bottom > 0 && r.top < window.innerHeight &&
           r.right > 0 && r.left < window.innerWidth &&
           s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  const labelOf = (el) => norm([
    el.innerText || '',
    el.getAttribute('aria-label') || '',
    el.getAttribute('title') || '',
    el.textContent || ''
  ].join(' '));
  const nodes = Array.from(document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"], button, a, [tabindex="0"]'));
  const rows = [];
  const seen = new Set();
  for (const el of nodes) {
    if (!isVisible(el)) continue;
    const text = labelOf(el);
    if (!text || text.length > 220 || deny.test(text)) continue;
    if (!rx.some(r => r.test(text))) continue;
    const r = el.getBoundingClientRect();
    const key = text + '|' + Math.round(r.top) + '|' + Math.round(r.left);
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push({
      text,
      top: Math.round(r.top),
      left: Math.round(r.left),
      bottom: Math.round(r.bottom),
      role: el.getAttribute('role') || '',
      tag: el.tagName || ''
    });
  }
  rows.sort((a,b) => a.top - b.top || a.left - b.left || a.text.localeCompare(b.text));
  return {
    count: rows.length,
    labels: rows.slice(0, 40).map(r => r.text),
    items: rows.slice(0, 20),
    url: location.href,
    active_tag: document.activeElement ? document.activeElement.tagName : null,
    active_role: document.activeElement ? (document.activeElement.getAttribute('role') || '') : null,
    body_text_chars: document.body && document.body.innerText ? document.body.innerText.length : 0
  };
}
"""


R45AM_VISIBLE_TEXT_EXPAND_COUNT_JS = r"""
() => {
  const patterns = [
    {key: 'view_all_replies', rx: /^view all\s+\d+\s+repl/i},
    {key: 'view_hidden', rx: /^view hidden\s+(repl|comments?)/i},
    {key: 'view_more_replies', rx: /^view more repl/i},
    {key: 'view_more_replies', rx: /^view\s+\d+\s+more\s+repl/i},
    {key: 'view_number_replies', rx: /^view\s+\d+\s+repl/i},
    {key: 'replied_buckets', rx: /replied\s*[·•.-]\s*\d+\s+repl/i}
  ];
  const norm = (s) => String(s || '').replace(/\s+/g, ' ').trim();
  const classify = (text) => {
    const t = norm(text);
    if (!t || t.length > 180) return null;
    const lower = t.toLowerCase();
    if (/^(like|reply|share|send|comment|edited|follow|message|copy link)$/i.test(t)) return null;
    for (const p of patterns) {
      if (p.rx.test(lower)) return {category: p.key, label: t};
    }
    return null;
  };
  const styleVisible = (el) => {
    if (!el || el.nodeType !== 1) return false;
    const s = window.getComputedStyle(el);
    return s && s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
  };
  const rectVisible = (r) => r && r.width > 0 && r.height > 0 &&
    r.bottom > 0 && r.top < window.innerHeight &&
    r.right > 0 && r.left < window.innerWidth;
  const addRow = (rows, seen, category, label, r, source) => {
    const key = category + '|' + label + '|' + Math.round(r.top / 3) + '|' + Math.round(r.left / 3);
    if (seen.has(key)) return;
    seen.add(key);
    rows.push({
      category, label,
      top: Math.round(r.top),
      left: Math.round(r.left),
      bottom: Math.round(r.bottom),
      source
    });
  };

  const rows = [];
  const seen = new Set();

  // 1) Text-node pass: catches Facebook labels that are visible text but not exposed
  // as clean role=button labels.
  const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const t = norm(node.nodeValue);
      if (!t) return NodeFilter.FILTER_REJECT;
      const c = classify(t);
      return c ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }
  });
  let node;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    if (!styleVisible(parent)) continue;
    let rects = [];
    try {
      const range = document.createRange();
      range.selectNodeContents(node);
      rects = Array.from(range.getClientRects());
      range.detach && range.detach();
    } catch (e) {
      rects = [];
    }
    const c = classify(node.nodeValue);
    if (!c) continue;
    for (const r of rects) {
      if (rectVisible(r)) {
        addRow(rows, seen, c.category, c.label, r, 'text_node');
        break;
      }
    }
  }

  // 2) Clickable element pass: catches aria-label/button cases.
  const els = Array.from(document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"], button, a, [tabindex="0"]'));
  for (const el of els) {
    if (!styleVisible(el)) continue;
    const raw = norm(el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '');
    const c = classify(raw);
    if (!c) continue;
    const r = el.getBoundingClientRect();
    if (!rectVisible(r)) continue;
    addRow(rows, seen, c.category, c.label, r, 'clickable_element');
  }

  rows.sort((a,b) => a.top - b.top || a.left - b.left || a.label.localeCompare(b.label));
  const counts = {};
  for (const p of ['view_all_replies','view_hidden','view_more_replies','view_number_replies','replied_buckets']) counts[p] = 0;
  for (const r of rows) counts[r.category] = (counts[r.category] || 0) + 1;
  return {
    total_count: rows.length,
    counts,
    labels: rows.slice(0, 80).map(r => r.label),
    items: rows.slice(0, 40),
    url: location.href,
    viewport: {width: window.innerWidth, height: window.innerHeight},
    body_text_chars: document.body && document.body.innerText ? document.body.innerText.length : 0
  };
}
"""

VISUAL_CLEAN_CSS = r'''
html, body {
  background: #ffffff !important;
  color-scheme: light !important;
  overflow: visible !important;
}
body {
  margin: 0 !important;
  padding: 24px 0 !important;
}
/* R45J blank-page fix: keep the live Facebook-rendered comments DOM in place.
   Do not clone the dialog or replace document.body; that can collapse/blank the visual page. */
[data-r45j-visual-keep-path="true"] {
  position: static !important;
  inset: auto !important;
  transform: none !important;
  overflow: visible !important;
  max-height: none !important;
  min-height: 0 !important;
  height: auto !important;
  background: transparent !important;
}
[data-r45j-preserved-comments-root="true"] {
  position: static !important;
  inset: auto !important;
  transform: none !important;
  width: min(720px, 96vw) !important;
  min-width: 0 !important;
  max-width: 720px !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  margin: 0 auto !important;
  padding: 0 !important;
  background: #fff !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}
[data-r45j-preserved-comments-root="true"] * {
  max-height: none !important;
}
[data-r45j-preserved-comments-root="true"] [style*="position: sticky"],
[data-r45j-preserved-comments-root="true"] [style*="position:sticky"],
[data-r45j-preserved-comments-root="true"] [style*="position: fixed"],
[data-r45j-preserved-comments-root="true"] [style*="position:fixed"] {
  position: static !important;
}
[data-r45j-visual-hide="true"],
[data-r45j-remove="true"] {
  display: none !important;
  visibility: hidden !important;
}
/* Remove editor/composer surfaces after expansion; keep visible Like/Reply/reaction metadata. */
[role="textbox"], textarea, input, form,
[contenteditable="true"],
[aria-label^="Reply to"], [aria-label*="Reply to"],
[aria-label^="Write a comment"], [aria-label*="Write a comment"],
[aria-label^="Comment as"], [aria-label*="Comment as"] {
  display: none !important;
  visibility: hidden !important;
}
'''

JS_MARK_AND_CLEAN_PRESERVED_COMMENTS = r'''
() => {
  const textOf = (el) => ((el && (el.innerText || el.textContent)) || '').replace(/\s+/g, ' ').trim();
  const labelOf = (el) => [el.getAttribute('aria-label') || '', el.getAttribute('title') || '', textOf(el)].join(' ').replace(/\s+/g, ' ').trim();
  const visible = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };

  for (const el of Array.from(document.querySelectorAll('[data-r45j-preserved-comments-root], [data-r45j-visual-keep-path], [data-r45j-visual-hide], [data-r45j-remove]'))) {
    el.removeAttribute('data-r45j-preserved-comments-root');
    el.removeAttribute('data-r45j-visual-keep-path');
    el.removeAttribute('data-r45j-visual-hide');
    el.removeAttribute('data-r45j-remove');
  }

  const candidates = Array.from(document.querySelectorAll('[role="dialog"], [role="main"], [role="article"], main, article'))
    .filter(visible)
    .map(el => {
      const t = textOf(el);
      const r = el.getBoundingClientRect();
      let score = t.length + Math.max(0, el.scrollHeight - el.clientHeight);
      if ((el.getAttribute('role') || '').toLowerCase() === 'dialog') score += 50000;
      if (/Restore Britain's post|View all|View hidden|Like Reply|Comment as/i.test(t)) score += 20000;
      if (/Tony Bentley|Dan Melin|Alex Barron/i.test(t)) score += 20000;
      if (r.width > 500 && r.width < 1000) score += 2000;
      return {el, score, textLength: t.length, scrollHeight: el.scrollHeight, role: el.getAttribute('role') || '', width: Math.round(r.width), height: Math.round(r.height)};
    })
    .sort((a,b) => b.score - a.score);
  const chosen = candidates.length ? candidates[0].el : document.body;
  const chosenInfo = candidates.length ? {...candidates[0], el: null} : {role: 'body', textLength: textOf(document.body).length, scrollHeight: document.body.scrollHeight};

  // R45J blank-page fix: keep the original live Facebook DOM in place. The prior
  // clone-and-replace method preserved text but could render as a blank white page.
  chosen.setAttribute('data-r45j-preserved-comments-root', 'true');
  chosen.setAttribute('data-r45j-source-role', chosen.getAttribute('role') || '');

  const keepPath = [];
  let n = chosen;
  while (n && n !== document.documentElement) {
    keepPath.push(n);
    n.setAttribute('data-r45j-visual-keep-path', 'true');
    if (n === document.body) break;
    n = n.parentElement;
  }

  // Hide siblings outside the path to the selected comments surface, but do not
  // rewrite body.innerHTML and do not hide descendants merely because their text
  // contains composer phrases.
  let childOnPath = chosen;
  for (let ancestor = chosen.parentElement; ancestor && ancestor !== document.documentElement; ancestor = ancestor.parentElement) {
    for (const child of Array.from(ancestor.children || [])) {
      if (child !== childOnPath && !child.contains(chosen)) {
        child.setAttribute('data-r45j-visual-hide', 'true');
      }
    }
    childOnPath = ancestor;
    if (ancestor === document.body) break;
  }

  // Make the kept ancestor chain behave like a normal printable page.
  for (const el of keepPath) {
    try {
      el.style.position = 'static';
      el.style.inset = 'auto';
      el.style.left = 'auto';
      el.style.right = 'auto';
      el.style.top = 'auto';
      el.style.bottom = 'auto';
      el.style.transform = 'none';
      el.style.overflow = 'visible';
      el.style.overflowY = 'visible';
      el.style.maxHeight = 'none';
      el.style.minHeight = '0';
      el.style.height = 'auto';
      el.style.background = el === chosen ? '#fff' : 'transparent';
    } catch (e) {}
  }

  try {
    chosen.style.width = 'min(720px, 96vw)';
    chosen.style.maxWidth = '720px';
    chosen.style.margin = '0 auto';
    chosen.style.boxShadow = 'none';
    chosen.style.borderRadius = '0';
  } catch (e) {}

  let hidden = 0;
  const smallAndVisible = (el, maxW = 420, maxH = 120) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.width <= maxW && r.height <= maxH;
  };
  for (const el of Array.from(chosen.querySelectorAll('*'))) {
    const txt = textOf(el);
    const lab = labelOf(el);
    const role = (el.getAttribute('role') || '').toLowerCase();
    const tag = el.tagName;
    if (role === 'textbox' || tag === 'TEXTAREA' || tag === 'INPUT' || tag === 'FORM' || el.isContentEditable) {
      el.setAttribute('data-r45j-remove', 'true'); hidden++; continue;
    }
    if (/^(close|search|notifications|messenger)$/i.test(lab) && smallAndVisible(el, 140, 140)) {
      el.setAttribute('data-r45j-remove', 'true'); hidden++; continue;
    }
    if (/^(Reply to .+|Comment as .+|Write a comment\.?\.?\.)$/i.test(lab) && smallAndVisible(el, 700, 120)) {
      el.setAttribute('data-r45j-remove', 'true'); hidden++; continue;
    }
    if (/^Restore Britain's post$/i.test(txt) && smallAndVisible(el, 800, 140)) {
      el.setAttribute('data-r45j-remove', 'true'); hidden++; continue;
    }
  }

  // Flatten real scrollers in the selected comments surface without forcing every
  // child node to height:auto, which can collapse Facebook's nested layout.
  for (const el of Array.from(chosen.querySelectorAll('*'))) {
    try {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const scrollGap = el.scrollHeight - el.clientHeight;
      const isScroller = scrollGap > 100 || /(auto|scroll)/i.test(cs.overflowY || cs.overflow || '');
      if (isScroller && r.height > 0) {
        el.style.maxHeight = 'none';
        el.style.overflow = 'visible';
        el.style.overflowY = 'visible';
        if (el.clientHeight && el.scrollHeight > el.clientHeight + 100) {
          el.style.height = 'auto';
        }
      }
    } catch (e) {}
  }

  try { document.documentElement.style.overflow = 'visible'; } catch (e) {}
  try { document.body.style.overflow = 'visible'; } catch (e) {}
  window.scrollTo(0, 0);
  return {
    chosen: chosenInfo,
    in_place_dom_preserved: true,
    clone_body_replacement_used: false,
    hidden_nodes: hidden,
    body_text_chars: (document.body.innerText || '').length,
    scroll_height: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)
  };
}
'''


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def contract() -> Dict[str, Any]:
    base = r45h.contract()
    base.update({
        'marker': MARKER,
        'mode_id': 'facebook_preserved_visual_screenshot_runner',
        'schema_version': SCHEMA_VERSION,
        'r45i_gap_fixed': 'R45I intentionally generated a static simplified comment-card evidence page. R45J instead screenshots the already-expanded live Facebook-rendered comments DOM after visual cleanup, preserving the bubble/avatar/reaction layout similar to the Print Edit WE view.',
        'primary_route': 'Open operator-controlled signed-in Facebook page, run R45H bounded expansion, then remove surrounding chrome/composer surfaces and screenshot the preserved Facebook-rendered comments DOM.',
        'preserved_visual_rule': 'Do not re-render comments into custom cards for screenshot evidence; preserve Facebook-rendered comment bubbles, avatars, nesting, visible reactions, and Like/Reply metadata after expansion.',
        'visual_clean_rule': 'After expansion only, remove/hide Facebook chrome, modal header, close buttons, and comment composer/reply boxes so the screenshot contains comments only.',
        'r45j_blank_page_fix': 'Preserved visual cleanup is now in-place: it marks and crops the live Facebook comments surface rather than cloning/replacing document.body, because clone-and-replace could produce a blank white screenshot while text still existed.',
        'text_comparison_rule': 'Use the same R45H visible-text comparison before visual cleanup so the run still gates on reference coverage.',
        'hidden_platform_api_scraping_enabled': False,
        'login_automation_enabled': False,
        'cookie_or_token_extraction_enabled': False,
        'browser_profile_file_copying_enabled': False,
        'browser_profile_file_parsing_enabled': False,
        'webview2_storage_or_cookie_inspection_enabled': False,
        'remote_media_downloads_enabled': False,
    })
    return base


def side_effect_flags(browser: bool, network: bool, auto_clicks: bool) -> Dict[str, Any]:
    flags = r45h.side_effect_flags(browser, network, auto_clicks)
    flags['facebook_preserved_visual_screenshot_runner_invoked'] = True
    flags['post_expansion_visual_dom_cleanup_performed'] = bool(browser)
    flags.pop('facebook_bounded_modal_capture_runner_invoked', None)
    return flags


def _safe_read(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return Path(path).read_text(encoding='utf-8', errors='replace')


def _capture_tiles(page: Any, run_dir: Path, prefix: str, steps: int, scroll_px: int, wait_s: float) -> List[str]:
    paths: List[str] = []
    try:
        total_height = int(page.evaluate('() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)'))
    except Exception:
        total_height = steps * scroll_px
    y = 0
    for i in range(max(1, steps)):
        if i > 0 and y > total_height + 1200:
            break
        tile_path = run_dir / f'{prefix}_{i+1:03d}.png'
        page.evaluate('(y) => window.scrollTo(0, y)', y)
        time.sleep(max(0.08, wait_s))
        page.screenshot(path=str(tile_path), full_page=False)
        paths.append(str(tile_path))
        y += scroll_px
    return paths


def run_live(args: argparse.Namespace) -> Dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise SystemExit(f'{STATUS_BLOCKED}: Playwright is not available: {e}')

    r45h.patch_r45d_globals()
    output_root = Path(args.output_root)
    run_dir = r45d.ensure_dir(output_root / f'facebook_preserved_visual_screenshot_runner_{utc_stamp()}')
    reference_text = _safe_read(args.reference_text)
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
        page.on('console', lambda msg: print(msg.text) if (msg.text.startswith('R45H_PROGRESS') or msg.text.startswith('R45AK') or msg.text.startswith('R45AL') or msg.text.startswith('R45AM')) else None)
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
            print('R45J_PRE_EXPAND_PAUSE')
            print('Check login/page, then press ENTER in this CMD window to start expansion.')
            try: input()
            except EOFError: pass
        else:
            # R45AM: no manual start gate. The user is already signed in; give the
            # Facebook permalink a tiny silent settle window, then start expansion.
            time.sleep(2.0)

        auto_expand_summary = None
        if args.auto_expand:
            opts = {
                'patterns': r45h.EXPAND_PATTERNS_R45H,
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
            preflight_report = {}
            pre_text_report = {}
            try:
                preflight_report = page.evaluate(R45AL_VISIBLE_EXPAND_PREFLIGHT_JS) or {}
            except Exception as e:
                preflight_report = {'preflight_error': str(e)[:1000]}
            try:
                pre_text_report = page.evaluate(R45AM_VISIBLE_TEXT_EXPAND_COUNT_JS) or {}
            except Exception as e:
                pre_text_report = {'visible_text_count_error': str(e)[:1000]}
            print('R45AL_PRE_EXPAND_VISIBLE_CONTROL_REPORT ' + json.dumps(preflight_report, ensure_ascii=False))
            print('R45AM_PRE_EXPAND_VISIBLE_TEXT_CONTROL_COUNT ' + json.dumps(pre_text_report, ensure_ascii=False))
            try:
                print(f'R45AL_FAILFAST_V2_AUTO_EXPAND_START max_seconds={args.expand_max_seconds}')
                auto_expand_summary = page.evaluate(r45h.JS_BOUNDED_MODAL_AUTO_EXPAND, opts)
                print('R45AL_FAILFAST_V2_AUTO_EXPAND_DONE ' + json.dumps({
                    'rounds_completed': (auto_expand_summary or {}).get('rounds_completed'),
                    'total_clicks': (auto_expand_summary or {}).get('total_clicks'),
                    'final_progress': (auto_expand_summary or {}).get('final_progress'),
                    'elapsed_seconds': (auto_expand_summary or {}).get('elapsed_seconds'),
                }, ensure_ascii=False))
                post_text_report = {}
                try:
                    post_text_report = page.evaluate(R45AM_VISIBLE_TEXT_EXPAND_COUNT_JS) or {}
                except Exception as e:
                    post_text_report = {'visible_text_count_error': str(e)[:1000]}
                print('R45AM_POST_EXPAND_VISIBLE_TEXT_CONTROL_COUNT ' + json.dumps(post_text_report, ensure_ascii=False))
                try:
                    post_total = int((post_text_report or {}).get('total_count') or 0)
                except Exception:
                    post_total = 0
                if post_total:
                    print('R45AM_VISIBLE_TEXT_MISSED_REPORT ' + json.dumps({
                        'status': 'NEEDS_MORE_EXPANSION',
                        'visible_text_missed_expand_count': post_total,
                        'counts': (post_text_report or {}).get('counts') or {},
                        'labels': list((post_text_report or {}).get('labels') or [])[:80],
                    }, ensure_ascii=False))
                    warnings.append(f'visible_text_expand_controls_remaining={post_total}')
                else:
                    print('R45AM_VISIBLE_TEXT_MISSED_REPORT ' + json.dumps({
                        'status': 'PASS_NO_VISIBLE_TEXT_EXPAND_CONTROLS',
                        'visible_text_missed_expand_count': 0,
                        'counts': (post_text_report or {}).get('counts') or {},
                        'labels': [],
                    }, ensure_ascii=False))
                if not auto_expand_summary or int((auto_expand_summary or {}).get('rounds_completed') or 0) <= 0:
                    post_zero = {}
                    try:
                        post_zero = page.evaluate(R45AL_VISIBLE_EXPAND_PREFLIGHT_JS) or {}
                    except Exception as e:
                        post_zero = {'post_zero_probe_error': str(e)[:1000]}
                    print('R45AL_AUTO_EXPAND_ZERO_ROUNDS ' + json.dumps({
                        'status': 'BLOCKED_AUTO_EXPAND_DID_NOT_RUN',
                        'preflight': preflight_report,
                    'pre_text_report': pre_text_report,
                        'pre_text_report': pre_text_report,
                        'post_zero_probe': post_zero,
                    }, ensure_ascii=False))
                    raise SystemExit('R45AL blocked: auto-expand returned zero rounds. See R45AL_AUTO_EXPAND_ZERO_ROUNDS above.')
                try:
                    visible_report = (auto_expand_summary or {}).get('final_visible_expand_report') or {}
                    visible_count = int(visible_report.get('count') or 0)
                    visible_labels = list(visible_report.get('labels') or [])[:30]
                    visible_status = 'NEEDS_MORE_EXPANSION' if visible_count else 'PASS_NO_VISIBLE_EXPAND_CONTROLS'
                    print('R45AL_VISIBLE_EXPAND_MISSED_REPORT ' + json.dumps({
                        'status': visible_status,
                        'visible_missed_expand_count': visible_count,
                        'visible_missed_expand_labels': visible_labels,
                    }, ensure_ascii=False))
                    if visible_count:
                        warnings.append(f'visible_expand_controls_remaining={visible_count}')
                except SystemExit:
                    raise
                except Exception as e:
                    warnings.append(f'visible_expand_report_warning={e}')
                    print('R45AL_VISIBLE_REPORT_FAILED ' + json.dumps({'error': str(e)[:1000]}, ensure_ascii=False))
            except SystemExit:
                raise
            except Exception as e:
                warnings.append(f'auto_expand_warning={e}')
                failed_report = {}
                try:
                    failed_report = page.evaluate(R45AL_VISIBLE_EXPAND_PREFLIGHT_JS) or {}
                except Exception as e2:
                    failed_report = {'failed_report_probe_error': str(e2)[:1000]}
                print('R45AL_AUTO_EXPAND_FAILED ' + json.dumps({
                    'status': 'BLOCKED_AUTO_EXPAND_EXCEPTION',
                    'error': str(e)[:2000],
                    'preflight': preflight_report,
                    'post_failure_probe': failed_report,
                }, ensure_ascii=False))
                raise SystemExit('R45AL blocked: auto-expand failed before opening controls. See R45AL_AUTO_EXPAND_FAILED above.')

        final_url = ''
        try: final_url = page.url
        except Exception: pass
        pre_clean_html = ''
        pre_clean_text = ''
        try: pre_clean_html = page.content()
        except Exception as e: warnings.append(f'pre_clean_raw_html_capture_warning={e}')
        try:
            pre_clean_text = page.locator('body').inner_text(timeout=15000)
        except Exception as e:
            warnings.append(f'pre_clean_inner_text_capture_warning={e}')
            try: pre_clean_text = page.evaluate('() => document.body ? document.body.innerText : ""')
            except Exception as e2: warnings.append(f'pre_clean_inner_text_fallback_warning={e2}')

        raw_dom_path = r45d.write_text(run_dir / 'facebook_live_pre_clean_raw_dom.html', pre_clean_html)
        inner_text_path = r45d.write_text(run_dir / 'facebook_live_pre_clean_visible_inner_text.txt', pre_clean_text)
        focus_css_path = r45d.write_text(run_dir / 'facebook_comments_focus_mode.css', r45d.FOCUS_CSS.strip() + '\n')
        visual_css_path = r45d.write_text(run_dir / 'facebook_preserved_visual_clean.css', VISUAL_CLEAN_CSS.strip() + '\n')
        auto_expand_script_path = r45d.write_text(run_dir / 'facebook_bounded_auto_expand_script.js', r45h.JS_BOUNDED_MODAL_AUTO_EXPAND.strip() + '\n')
        comparison = r45d.compare_text(pre_clean_text, reference_text) if reference_text is not None else None
        status = r45d.classify_status(pre_clean_text, comparison, args.min_coverage)
        if status == r45h.STATUS_PASS:
            status = STATUS_PASS
        elif status == r45h.STATUS_NEEDS_MORE_EXPANSION:
            status = STATUS_NEEDS_MORE_EXPANSION
        else:
            status = STATUS_BLOCKED if not pre_clean_text.strip() else status
        if status == STATUS_NEEDS_MORE_EXPANSION:
            warnings.append('comparison_coverage_below_threshold_more_comments_need_loading_or_expansion')
        if auto_expand_summary and auto_expand_summary.get('timed_out'):
            warnings.append('auto_expand_reached_max_seconds_captured_current_loaded_state')

        visual_clean_summary: Optional[Dict[str, Any]] = None
        clean_html_path = None
        clean_text_path = None
        full_screenshot_path = None
        tile_paths: List[str] = []
        try:
            visual_clean_summary = page.evaluate(JS_MARK_AND_CLEAN_PRESERVED_COMMENTS)
            page.add_style_tag(content=VISUAL_CLEAN_CSS)
            page.evaluate('() => window.scrollTo(0, 0)')
            time.sleep(max(0.2, args.visual_clean_wait_seconds))
            clean_html_path = r45d.write_text(run_dir / 'facebook_preserved_visual_clean_dom.html', page.content())
            clean_text_path = r45d.write_text(run_dir / 'facebook_preserved_visual_clean_visible_text.txt', page.locator('body').inner_text(timeout=15000))
        except Exception as e:
            warnings.append(f'visual_clean_warning={e}')

        if args.operator_pause:
            print('R45J_OPERATOR_PAUSE')
            print('Review the preserved Facebook-layout comments-only page. Press ENTER in this CMD window to screenshot.')
            try: input()
            except EOFError: pass
        elif args.wait_seconds:
            time.sleep(args.wait_seconds)

        if not args.no_screenshots:
            try:
                full_screenshot_path = str(run_dir / 'facebook_preserved_visual_full_page.png')
                page.screenshot(path=full_screenshot_path, full_page=True)
            except Exception as e:
                warnings.append(f'preserved_visual_full_page_screenshot_warning={e}')
                full_screenshot_path = None
            if args.tile_screenshots:
                try:
                    tile_paths = _capture_tiles(page, run_dir, 'facebook_preserved_visual_tile', args.tile_steps, args.tile_scroll_px, args.tile_wait_seconds)
                except Exception as e:
                    warnings.append(f'preserved_visual_tile_screenshot_warning={e}')

        exports = r45d.write_comment_exports(run_dir, pre_clean_text, max_items=args.max_items)
        receipt = {
            'marker': MARKER,
            'status': status,
            'schema_version': SCHEMA_VERSION,
            'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
            'target_url': args.target_url,
            'sanitized_target_url': target_url,
            'final_page_url': final_url,
            'run_dir': str(run_dir),
            'pre_clean_raw_dom_path': raw_dom_path,
            'pre_clean_inner_text_path': inner_text_path,
            'preserved_visual_clean_dom_path': clean_html_path,
            'preserved_visual_clean_text_path': clean_text_path,
            'preserved_visual_full_screenshot_path': full_screenshot_path,
            'preserved_visual_tile_screenshot_paths': tile_paths,
            'preserved_visual_tile_screenshot_count': len(tile_paths),
            'focus_css_path': focus_css_path,
            'preserved_visual_css_path': visual_css_path,
            'auto_expand_script_path': auto_expand_script_path,
            'auto_expand_summary': auto_expand_summary,
            'visual_clean_summary': visual_clean_summary,
            **exports,
            'comparison': comparison,
            'contract': contract(),
            'side_effect_flags': side_effect_flags(True, bool(target_url and not args.manual_current_page), bool(args.auto_expand)),
            'warnings': warnings,
        }
        receipt['receipt_path'] = r45d.write_json(run_dir / 'r45j_facebook_preserved_visual_screenshot_runner_receipt.json', receipt)
        print(MARKER)
        print(status)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        try: context.close()
        except Exception: pass
        return receipt


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    checks = [
        {'name': 'in_place_visual_clean_js_present', 'status': 'pass' if 'data-r45j-visual-keep-path' in JS_MARK_AND_CLEAN_PRESERVED_COMMENTS and 'document.body.innerHTML' not in JS_MARK_AND_CLEAN_PRESERVED_COMMENTS else 'fail'},
        {'name': 'preserved_visual_css_present', 'status': 'pass' if 'data-r45j-preserved-comments-root' in VISUAL_CLEAN_CSS and 'blank-page fix' in VISUAL_CLEAN_CSS else 'fail'},
        {'name': 'r45h_expansion_reused', 'status': 'pass' if 'JS_BOUNDED_MODAL_AUTO_EXPAND' in dir(r45h) else 'fail'},
        {'name': 'r45am_visible_text_count_present', 'status': 'pass' if 'R45AM_VISIBLE_TEXT_EXPAND_COUNT_JS' in globals() and 'R45AM_PRE_EXPAND_VISIBLE_TEXT_CONTROL_COUNT' in open(__file__, encoding='utf-8').read() and 'R45AM_POST_EXPAND_VISIBLE_TEXT_CONTROL_COUNT' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'hidden_platform_api_disabled', 'status': 'pass' if contract().get('hidden_platform_api_scraping_enabled') is False else 'fail'},
        {'name': 'login_automation_disabled', 'status': 'pass' if contract().get('login_automation_enabled') is False else 'fail'},
        {'name': 'no_browser_profile_parsing', 'status': 'pass' if contract().get('browser_profile_file_parsing_enabled') is False else 'fail'},
    ]
    status = STATUS_PASS if all(c['status'] == 'pass' for c in checks) else STATUS_BLOCKED
    report = {
        'marker': MARKER,
        'status': status,
        'schema_version': SCHEMA_VERSION,
        'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
        'checks': checks,
        'contract': contract(),
        'side_effect_flags': side_effect_flags(False, False, False),
    }
    r45d.write_json(Path(args.output_root) / 'r45j_self_test_report.json', report)
    print(MARKER)
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    r45h.patch_r45d_globals()
    ap = r45d.build_arg_parser()
    ap.description = 'R45AM Facebook preserved visual screenshot runner: legacy failfast v2 with visible text-control counts'
    ap.set_defaults(output_root='profile_media_live_captures/r45am_legacy_failfast_visible_count_20260919')
    ap.set_defaults(expand_rounds=220)
    ap.set_defaults(expand_max_clicks_per_round=80)
    ap.set_defaults(expand_scrolls_per_round=3)
    ap.set_defaults(expand_scroll_px=760)
    ap.set_defaults(expand_stop_after_stable_rounds=4)
    ap.set_defaults(expand_click_delay_seconds=0.03)
    ap.set_defaults(expand_after_click_delay_seconds=0.12)
    ap.set_defaults(expand_scroll_delay_seconds=0.18)
    ap.set_defaults(tile_steps=220)
    ap.set_defaults(tile_scroll_px=900)
    ap.add_argument('--expand-max-seconds', type=int, default=900)
    ap.add_argument('--visual-clean-wait-seconds', type=float, default=0.5)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)
    if args.self_test:
        report = run_self_test(args)
        return 0 if report.get('status') == STATUS_PASS else 2
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
