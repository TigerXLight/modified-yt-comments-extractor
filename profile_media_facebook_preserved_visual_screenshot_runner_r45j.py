#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import profile_media_facebook_auto_expand_comments_runner_r45d as r45d
import profile_media_facebook_bounded_modal_capture_runner_r45h as r45h

MARKER = "YTCE_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
STATUS_PASS = "PASS_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
STATUS_NEEDS_MORE_EXPANSION = "NEEDS_MORE_EXPANSION_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
STATUS_BLOCKED = "BLOCKED_R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER"
SCHEMA_VERSION = "facebook_preserved_visual_screenshot_runner.r45j.v1"

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
[data-r45j-pre-comment-hide="true"],
[data-r45j-remove="true"] {
  display: none !important;
  visibility: hidden !important;
}
/* R45L: cut the preserved visual surface down to the Facebook-rendered
   comments column, like the manual original-view -> Print Edit WE crop. */
[data-r45j-comment-column-crop="true"] {
  width: min(720px, 96vw) !important;
  max-width: 720px !important;
  margin-left: auto !important;
  margin-right: auto !important;
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

  for (const el of Array.from(document.querySelectorAll('[data-r45j-preserved-comments-root], [data-r45j-comment-column-crop], [data-r45j-visual-keep-path], [data-r45j-visual-hide], [data-r45j-pre-comment-hide], [data-r45j-remove]'))) {
    el.removeAttribute('data-r45j-preserved-comments-root');
    el.removeAttribute('data-r45j-comment-column-crop');
    el.removeAttribute('data-r45j-visual-keep-path');
    el.removeAttribute('data-r45j-visual-hide');
    el.removeAttribute('data-r45j-pre-comment-hide');
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
  chosen.setAttribute('data-r45j-comment-column-crop', 'true');
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
  let preCommentHidden = 0;

  // R45L: keep the original Facebook-rendered comments, but crop away the
  // post header/body/media/reaction bar above the first visible comment/reply.
  // This matches the operator expectation: use the original Facebook view as
  // the visual source, then cut it down to the comment column rather than
  // screenshotting the full post modal.
  const commentish = Array.from(chosen.querySelectorAll('*')).filter(visible).map(el => {
    const r = el.getBoundingClientRect();
    const t = textOf(el);
    const lab = labelOf(el);
    const role = (el.getAttribute('role') || '').toLowerCase();
    return {el, r, t, lab, role};
  }).filter(x => {
    if (!x.t || x.role === 'textbox' || x.el.isContentEditable) return false;
    if (/Reply to |Comment as |Write a comment/i.test(x.lab + ' ' + x.t)) return false;
    if (/\bLike\s+Reply\b/i.test(x.t)) return true;
    if (/\bView\s+(?:all|more)\s+\d*\s*repl/i.test(x.t)) return true;
    if (/\bView\s+hidden\s+(?:comments|replies)\b/i.test(x.t)) return true;
    return false;
  }).sort((a,b) => (a.r.top - b.r.top) || (a.r.left - b.r.left));
  const firstCommentish = commentish.length ? commentish[0] : null;
  const firstCommentTop = firstCommentish ? firstCommentish.r.top : null;
  if (firstCommentish && Number.isFinite(firstCommentTop)) {
    chosen.setAttribute('data-r45j-first-comment-top', String(Math.round(firstCommentTop)));
    for (const el of Array.from(chosen.querySelectorAll('*'))) {
      if (el === firstCommentish.el || el.contains(firstCommentish.el) || firstCommentish.el.contains(el)) continue;
      try {
        const r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) continue;
        const lab = labelOf(el);
        const t = textOf(el);
        const role = (el.getAttribute('role') || '').toLowerCase();
        if (role === 'textbox' || el.isContentEditable || /Reply to |Comment as |Write a comment/i.test(lab + ' ' + t)) continue;
        if (r.bottom <= firstCommentTop - 6) {
          el.setAttribute('data-r45j-pre-comment-hide', 'true');
          preCommentHidden++;
        }
      } catch (e) {}
    }
  }

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
    r45l_comment_column_crop_used: true,
    first_comment_top: firstCommentTop === null ? null : Math.round(firstCommentTop),
    pre_comment_hidden_nodes: preCommentHidden,
    commentish_anchor_count: commentish.length,
    hidden_nodes: hidden,
    body_text_chars: (document.body.innerText || '').length,
    scroll_height: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)
  };
}
'''


JS_CLICK_REPLIED_REPLY_BUCKETS_R45N = r'''
(opts) => {
  const started = Date.now();
  const maxSeconds = Number(opts.maxSeconds || 240);
  const rounds = Number(opts.rounds || 80);
  const maxClicksPerRound = Number(opts.maxClicksPerRound || 25);
  const clickDelayMs = Number(opts.clickDelayMs || 80);
  const afterClickDelayMs = Number(opts.afterClickDelayMs || 250);
  const scrollsPerRound = Number(opts.scrollsPerRound || 4);
  const scrollPx = Number(opts.scrollPx || 950);
  const scrollDelayMs = Number(opts.scrollDelayMs || 80);
  const stopAfterStableRounds = Number(opts.stopAfterStableRounds || 5);
  const repliedRe = /\breplied\s*[·•\-–—]\s*\d+\s+repl(?:y|ies)\b/i;
  const clickedKeys = new Set();
  const clickedLabels = [];
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const textOf = (el) => ((el && (el.innerText || el.textContent)) || '').replace(/\s+/g, ' ').trim();
  const labelOf = (el) => [el.getAttribute('aria-label') || '', el.getAttribute('title') || '', textOf(el)].join(' ').replace(/\s+/g, ' ').trim();
  const styleVisible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && s.pointerEvents !== 'none';
  };
  const rectKey = (el) => {
    const r = el.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.top + window.scrollY), Math.round(r.width), Math.round(r.height)].join(':');
  };
  const clickTargetFor = (el) => {
    let n = el;
    for (let i = 0; n && i < 5; i++, n = n.parentElement) {
      const role = (n.getAttribute('role') || '').toLowerCase();
      const tag = (n.tagName || '').toLowerCase();
      const s = getComputedStyle(n);
      const lab = labelOf(n);
      if (role === 'button' || tag === 'a' || tag === 'button' || s.cursor === 'pointer' || repliedRe.test(lab)) return n;
    }
    return el;
  };
  const findReplyBuckets = () => {
    const nodes = Array.from(document.querySelectorAll('[role="button"], a, button, span, div'));
    const out = [];
    for (const el of nodes) {
      if (!styleVisible(el)) continue;
      const own = textOf(el);
      const lab = labelOf(el);
      const combined = (lab + ' ' + own).replace(/\s+/g, ' ').trim();
      if (!combined || combined.length > 220) continue;
      if (!repliedRe.test(combined)) continue;
      const target = clickTargetFor(el);
      if (!target || !styleVisible(target)) continue;
      const key = combined.slice(0, 160) + '|' + rectKey(target);
      if (clickedKeys.has(key)) continue;
      out.push({el, target, label: combined, key});
    }
    out.sort((a, b) => {
      const ar = a.target.getBoundingClientRect();
      const br = b.target.getBoundingClientRect();
      return (ar.top - br.top) || (ar.left - br.left);
    });
    return out;
  };
  const scrollables = () => {
    const arr = [];
    if (document.scrollingElement) arr.push(document.scrollingElement);
    for (const el of Array.from(document.querySelectorAll('*'))) {
      try {
        const r = el.getBoundingClientRect();
        const gap = el.scrollHeight - el.clientHeight;
        if (gap > 120 && r.width > 200 && r.height > 180) arr.push(el);
      } catch (e) {}
    }
    const seen = new Set();
    return arr.filter(el => {
      if (!el || seen.has(el)) return false;
      seen.add(el);
      return true;
    }).sort((a,b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight)).slice(0, 6);
  };
  let stable = 0;
  let clickedTotal = 0;
  let lastTextLen = (document.body && document.body.innerText || '').length;
  for (let round = 1; round <= rounds; round++) {
    if ((Date.now() - started) / 1000 > maxSeconds) break;
    let clicked = 0;
    const candidates = findReplyBuckets();
    for (const item of candidates.slice(0, maxClicksPerRound)) {
      try {
        item.target.scrollIntoView({block: 'center', inline: 'center'});
        await sleep(scrollDelayMs);
        item.target.click();
        clickedKeys.add(item.key);
        clickedLabels.push(item.label);
        clicked++;
        clickedTotal++;
        await sleep(clickDelayMs + afterClickDelayMs);
      } catch (e) {}
    }
    let scrollChanged = 0;
    for (const sc of scrollables().slice(0, scrollsPerRound)) {
      try {
        const before = sc.scrollTop;
        sc.scrollTop = before + scrollPx;
        if (sc.scrollTop !== before) scrollChanged++;
      } catch (e) {}
      await sleep(scrollDelayMs);
    }
    const textLen = (document.body && document.body.innerText || '').length;
    const deltaTextChars = textLen - lastTextLen;
    if (clicked === 0 && scrollChanged === 0 && Math.abs(deltaTextChars) < 20) stable++;
    else stable = 0;
    lastTextLen = textLen;
    const payload = {round, candidate_count: candidates.length, clicked, clicked_total: clickedTotal, delta_text_chars: deltaTextChars, text_chars: textLen, scroll_changed: scrollChanged, elapsed_seconds: Math.round((Date.now() - started) / 1000), clicked_labels: clickedLabels.slice(-20)};
    try { console.log('R45N_REPLIED_REPLY_BUCKET_PROGRESS ' + JSON.stringify(payload)); } catch (e) {}
    if (stable >= stopAfterStableRounds) break;
  }
  return {
    marker: 'YTCE_R45N_FACEBOOK_REPLIED_REPLY_BUCKET_EXPAND',
    status: 'PASS_R45N_FACEBOOK_REPLIED_REPLY_BUCKET_EXPAND',
    clicked_total: clickedTotal,
    clicked_labels: clickedLabels,
    elapsed_seconds: Math.round((Date.now() - started) / 1000),
    body_text_chars: (document.body && document.body.innerText || '').length
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
        'r45l_comment_column_crop_fix': 'After the blank-page fix, real screenshots could still show the full original post modal/post media instead of the desired Print Edit WE-like comments column. R45L crops away pre-comment post/header/media surfaces while preserving the Facebook-rendered comment bubbles/replies.',
        'comments_column_screenshot_rule': 'When screenshots are enabled, also capture facebook_preserved_visual_comments_column.png from the marked comments root so the operator gets the cropped original-view comments column rather than the full modal shell.',
        'r45n_replied_reply_bucket_expand_fix': 'After the standard R45H/R45J expansion pass, R45N performs an additional visible-page click pass for collapsed Facebook labels such as Name replied · 14 replies, then reruns the normal bounded expansion to load controls exposed by those buckets.',
        'r45m_playwright_viewport_launch_fix': 'Playwright viewport=None is now passed to browser contexts only, not BrowserType.launch(), fixing the manual live-run TypeError while preserving maximized operator-controlled browser UI.',
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
        # R45M: BrowserType.launch() does not accept viewport. Keep viewport
        # on contexts only, while preserving maximized operator-controlled browser UI.
        launch_kwargs: Dict[str, Any] = {'headless': False, 'args': ['--start-maximized']}
        context_kwargs: Dict[str, Any] = {'viewport': None}
        if args.chromium_executable:
            launch_kwargs['executable_path'] = args.chromium_executable
        if args.user_data_dir:
            context = p.chromium.launch_persistent_context(args.user_data_dir, **launch_kwargs, **context_kwargs)
        else:
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(**context_kwargs)
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
            print('R45J_PRE_EXPAND_PAUSE')
            print('Check login/page, then press ENTER in this CMD window to start expansion.')
            try: input()
            except EOFError: pass

        auto_expand_summary = None
        replied_reply_bucket_summary = None
        post_replied_auto_expand_summary = None
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
            try:
                print(f'R45J_AUTO_EXPAND_START max_seconds={args.expand_max_seconds}')
                auto_expand_summary = page.evaluate(r45h.JS_BOUNDED_MODAL_AUTO_EXPAND, opts)
                print('R45J_AUTO_EXPAND_DONE')
            except Exception as e:
                warnings.append(f'auto_expand_warning={e}')

            if not args.no_replied_reply_bucket_expand:
                try:
                    replied_opts = {
                        'rounds': args.replied_bucket_rounds,
                        'maxSeconds': args.replied_bucket_max_seconds,
                        'maxClicksPerRound': args.expand_max_clicks_per_round,
                        'clickDelayMs': int(args.expand_click_delay_seconds * 1000),
                        'afterClickDelayMs': int(args.expand_after_click_delay_seconds * 1000),
                        'scrollsPerRound': args.expand_scrolls_per_round,
                        'scrollPx': args.expand_scroll_px,
                        'scrollDelayMs': int(args.expand_scroll_delay_seconds * 1000),
                        'stopAfterStableRounds': args.expand_stop_after_stable_rounds,
                    }
                    print(f'R45N_REPLIED_REPLY_BUCKET_EXPAND_START max_seconds={args.replied_bucket_max_seconds}')
                    replied_reply_bucket_summary = page.evaluate(JS_CLICK_REPLIED_REPLY_BUCKETS_R45N, replied_opts)
                    print('R45N_REPLIED_REPLY_BUCKET_EXPAND_DONE')
                    if (replied_reply_bucket_summary or {}).get('clicked_total'):
                        print(f'R45N_POST_REPLIED_AUTO_EXPAND_START max_seconds={args.expand_max_seconds}')
                        post_replied_auto_expand_summary = page.evaluate(r45h.JS_BOUNDED_MODAL_AUTO_EXPAND, opts)
                        print('R45N_POST_REPLIED_AUTO_EXPAND_DONE')
                except Exception as e:
                    warnings.append(f'replied_reply_bucket_expand_warning={e}')

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
        column_screenshot_path = None
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
                column_screenshot_path = str(run_dir / 'facebook_preserved_visual_comments_column.png')
                page.locator('[data-r45j-preserved-comments-root=\"true\"]').first.screenshot(path=column_screenshot_path)
            except Exception as e:
                warnings.append(f'preserved_visual_comments_column_screenshot_warning={e}')
                column_screenshot_path = None
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
            'preserved_visual_comments_column_screenshot_path': column_screenshot_path,
            'preserved_visual_full_screenshot_path': full_screenshot_path,
            'preserved_visual_tile_screenshot_paths': tile_paths,
            'preserved_visual_tile_screenshot_count': len(tile_paths),
            'focus_css_path': focus_css_path,
            'preserved_visual_css_path': visual_css_path,
            'auto_expand_script_path': auto_expand_script_path,
            'auto_expand_summary': auto_expand_summary,
            'replied_reply_bucket_summary': replied_reply_bucket_summary,
            'post_replied_auto_expand_summary': post_replied_auto_expand_summary,
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
        {'name': 'r45l_comment_column_crop_present', 'status': 'pass' if 'data-r45j-pre-comment-hide' in VISUAL_CLEAN_CSS and 'r45l_comment_column_crop_used' in JS_MARK_AND_CLEAN_PRESERVED_COMMENTS else 'fail'},
        {'name': 'comments_column_screenshot_path_present', 'status': 'pass' if 'facebook_preserved_visual_comments_column.png' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45n_replied_reply_bucket_expand_present', 'status': 'pass' if 'JS_CLICK_REPLIED_REPLY_BUCKETS_R45N' in open(__file__, encoding='utf-8').read() and 'replied_reply_bucket_summary' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45m_launch_viewport_context_only', 'status': 'pass' if 'p.chromium.launch(**launch_kwargs)' in open(__file__, encoding='utf-8').read() and 'browser.new_context(**context_kwargs)' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45h_expansion_reused', 'status': 'pass' if 'JS_BOUNDED_MODAL_AUTO_EXPAND' in dir(r45h) else 'fail'},
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
    ap.description = 'R45J Facebook preserved visual screenshot runner'
    ap.set_defaults(output_root='profile_media_live_captures/r45j_facebook_preserved_visual_screenshot_runner')
    ap.set_defaults(expand_rounds=260)
    ap.set_defaults(expand_max_clicks_per_round=30)
    ap.set_defaults(expand_scrolls_per_round=5)
    ap.set_defaults(expand_scroll_px=950)
    ap.set_defaults(expand_stop_after_stable_rounds=6)
    ap.set_defaults(tile_steps=220)
    ap.set_defaults(tile_scroll_px=900)
    ap.add_argument('--expand-max-seconds', type=int, default=900)
    ap.add_argument('--visual-clean-wait-seconds', type=float, default=0.5)
    ap.add_argument('--no-replied-reply-bucket-expand', action='store_true', help='Disable the R45N visible-page follow-up pass for labels like "Name replied · 14 replies".')
    ap.add_argument('--replied-bucket-max-seconds', type=int, default=240, help='Maximum seconds for the R45N replied-reply-bucket follow-up pass.')
    ap.add_argument('--replied-bucket-rounds', type=int, default=80, help='Maximum rounds for the R45N replied-reply-bucket follow-up pass.')
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
