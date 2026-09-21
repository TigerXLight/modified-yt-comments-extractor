#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

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

  // R45P: the modal is often scrolled near the bottom after expansion. Reset the
  // selected live scrollers before flattening, otherwise the preserved comments
  // root can have a negative visual top and screenshot clipping only captures a
  // viewport-sized tail instead of the full comment column.
  try { chosen.scrollTop = 0; } catch (e) {}
  for (const el of Array.from(chosen.querySelectorAll('*'))) {
    try { if (el.scrollTop && el.scrollTop > 0) el.scrollTop = 0; } catch (e) {}
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
async (opts) => {
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
  const progressiveTopDown = opts.progressiveTopDown !== false;
  const viewportMarginPx = Number(opts.viewportMarginPx || 90);
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
    // R45P: do not treat the text span itself as clickable merely because it
    // contains "replied · N replies". Walk to the actual button/link/cursor
    // ancestor first; the R45O version could be clicking inert text and log success
    // with zero text growth.
    let n = el;
    for (let i = 0; n && i < 8; i++, n = n.parentElement) {
      const role = (n.getAttribute('role') || '').toLowerCase();
      const tag = (n.tagName || '').toLowerCase();
      const s = getComputedStyle(n);
      if (role === 'button' || tag === 'a' || tag === 'button' || tag === 'summary' || s.cursor === 'pointer') return n;
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
      const r = target.getBoundingClientRect();
      if (progressiveTopDown && (r.bottom < -viewportMarginPx || r.top > window.innerHeight + viewportMarginPx)) continue;
      const key = combined.slice(0, 160) + '|' + rectKey(target);
      if (clickedKeys.has(key)) continue;
      if (out.some(item => item.label === combined && (item.target === target || item.target.contains(target) || target.contains(item.target)))) continue;
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
        'r45o_screenshot_band_rule': 'Very tall Facebook comment columns are captured as maximum-height screenshot bands, starting with facebook_preserved_visual_comments_column.png and continuing with numbered parts, instead of hundreds of small viewport tiles.',
        'r45o_replied_bucket_async_fix': 'The R45N replied-reply-bucket pass is async and logs R45N progress so labels such as Name replied · 14 replies can be clicked before the final visual cleanup.',
        'r45o_progressive_top_down_rule': 'R45J asks the R45H expansion pass to click visible controls top-to-bottom while moving downward through the modal, reducing repeated jump-back behaviour on long threads.',
        'r45p_replied_bucket_click_target_fix': 'R45P clicks the nearest real clickable ancestor for Name replied · N replies buckets instead of clicking a non-interactive text span.',
        'r45p_max_band_viewport_clip_fix': 'R45P captures comments-column screenshot bands with viewport-relative clipping after resizing the viewport, avoiding empty/out-of-range clips on very tall Facebook pages.',
        'r45p_top_down_rescan_rule': 'R45P allowed a bounded second top-to-bottom sweep, but that could jump back upward and waste time on long Facebook threads.',
        'r45q_downward_frontier_rule': 'R45Q uses a single downward frontier: locally exhaust visible View hidden replies, View all N replies, View 1 reply, and View more replies controls before scrolling further down; it does not go back up for a global rescan.',
        'r45r_local_exhaust_rule': 'R45R fixes the R45Q regression where --progressive-top-down-sweeps 1 limited local exhaustion: each visible area is repeatedly exhausted for newly exposed View all N replies / View hidden replies controls before scrolling downward.',
        'r45s_first_visible_click_rule': 'R45S clicks exactly one first visible expansion control, rescans the same viewport, and does not start the replied-bucket follow-up while visible expansion controls or incomplete comment progress remain.',
        'r45t_visible_click_heartbeat_rule': 'R45T keeps the operator-requested downward frontier but emits a heartbeat for each single first-visible click and uses a human-like pointer/mouse click sequence for visible Facebook expand controls.',
        'r45u_target_page_guard_rule': 'R45U refuses to expand a generic Facebook home/feed page when a specific target URL was requested; after the pre-expand pause it reopens the target URL and blocks if the browser is still not on that target.',
        'r45v_playwright_mouse_downward_rule': 'R45V uses Playwright-side mouse clicks for the first visible Facebook expand control, then rescans the same viewport before scrolling downward; it avoids synthetic in-page click dispatch for Comet role=button controls.',
        'r45w_no_file_chooser_rule': 'R45W restricts mouse-click coordinates to the exact visible expansion text and excludes comment composer/upload/photo/GIF/sticker controls so the run cannot open a native file chooser while expanding comments.',
        'r45x_expansion_only_rule': 'R45X treats the pass as expand-comments only: click the next explicit visible View all/View hidden/View more/Name replied control, rescan that local area, then continue downward without broad comment/feed scanning.',
        'r45y_pre_pause_target_rule': 'R45Y opens a fresh target tab for a requested permalink and runs the target-page guard before the operator pre-expand pause, so a restored facebook.com feed tab is not shown/expanded as the working page.',
        'r45z_active_target_tab_rule': 'R45Z closes restored/crashed non-target tabs after opening the requested permalink and keeps the target page in front before expansion; it also waits for large expansion clicks to settle before scrolling downward.',
        'r45aa_large_bucket_settle_rule': 'R45AA enforces a real minimum hold after large reply openers such as View all 302 replies; the runner must not scroll away until the opened bucket has had time to stream newly inserted replies and expose their expansion controls.',
        'r45ab_target_surface_lock_rule': 'R45AB locks expansion and downward scrolling to the active Facebook comments dialog; if the dialog disappears, the runner stops instead of scrolling the outer facebook.com feed.',
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


def _axis_positions(total: int, viewport: int, overlap_px: int) -> List[int]:
    total = max(1, int(total))
    viewport = max(1, int(viewport))
    overlap = max(0, min(int(overlap_px), viewport - 1))
    if total <= viewport:
        return [0]
    step = max(1, viewport - overlap)
    last = max(0, total - viewport)
    positions: List[int] = []
    pos = 0
    while pos < last:
        positions.append(pos)
        pos += step
    positions.append(last)
    out: List[int] = []
    seen = set()
    for item in positions:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _page_dimensions(page: Any) -> Dict[str, int]:
    try:
        dims = page.evaluate("""() => ({
          width: Math.ceil(Math.max(document.body.scrollWidth || 0, document.documentElement.scrollWidth || 0, window.innerWidth || 0)),
          height: Math.ceil(Math.max(document.body.scrollHeight || 0, document.documentElement.scrollHeight || 0, window.innerHeight || 0)),
          innerWidth: Math.ceil(window.innerWidth || 0),
          innerHeight: Math.ceil(window.innerHeight || 0)
        })""")
        return {k: max(1, int(dims.get(k) or 1)) for k in ('width', 'height', 'innerWidth', 'innerHeight')}
    except Exception:
        return {'width': 1280, 'height': 720, 'innerWidth': 1280, 'innerHeight': 720}


def _prepare_preserved_visual_screenshot_surface(page: Any) -> Dict[str, Any]:
    return page.evaluate("""() => {
      const root = document.querySelector('[data-r45j-preserved-comments-root="true"]');
      if (!root) return {root_found: false};
      const rect = root.getBoundingClientRect();
      const rootHeight = Math.ceil(Math.max(root.scrollHeight || 0, rect.height || 0));
      const rootWidth = Math.ceil(Math.max(root.scrollWidth || 0, rect.width || 0));
      const minHeight = Math.max(rootHeight + 96, window.innerHeight || 0, document.body.scrollHeight || 0, document.documentElement.scrollHeight || 0);
      try { document.documentElement.style.minHeight = minHeight + 'px'; } catch (e) {}
      try { document.body.style.minHeight = minHeight + 'px'; } catch (e) {}
      try { document.documentElement.style.overflow = 'visible'; document.body.style.overflow = 'visible'; } catch (e) {}
      return {root_found: true, root_height: rootHeight, root_width: rootWidth, min_height: Math.ceil(minHeight)};
    }""")


def _capture_locator_bands(
    page: Any,
    run_dir: Path,
    selector: str,
    *,
    first_filename: Optional[str],
    prefix: str,
    max_band_height: int,
    overlap_px: int,
    wait_s: float,
) -> List[str]:
    """Capture a tall comments column as maximum-height viewport-relative bands.

    R45O used page-coordinate clips with full_page=False. On tall Facebook pages,
    Playwright treats that clip against the viewport image, so high-y bands fail
    as "outside the resulting image" after the first/early band. R45P resizes the
    viewport to the band height, scrolls to each page y, and clips at viewport
    y=0, which matches the main-project maximum-band behaviour.
    """
    paths: List[str] = []
    max_band_height = max(600, int(max_band_height))
    overlap_px = max(0, min(int(overlap_px), max_band_height - 1))
    surface = _prepare_preserved_visual_screenshot_surface(page)
    locator = page.locator(selector).first
    box = locator.bounding_box(timeout=15000)
    if not box:
        raise RuntimeError(f'locator not available for screenshot bands: {selector}')
    dims = _page_dimensions(page)
    x = max(0, int(math.floor(box.get('x', 0))))
    y0 = max(0, int(math.floor(box.get('y', 0))))
    raw_width = max(1, int(math.ceil(box.get('width', 1))))
    surface_height = 0
    if isinstance(surface, dict):
        try:
            surface_height = int(surface.get('root_height') or 0)
        except Exception:
            surface_height = 0
    raw_height = max(1, int(math.ceil(max(box.get('height', 1), surface_height))))
    page_width = max(dims.get('width', 1), dims.get('innerWidth', 1), x + raw_width + 16)
    width = max(1, min(raw_width, max(1, page_width - x)))
    total_height = raw_height
    positions = _axis_positions(total_height, max_band_height, overlap_px)
    # Ensure the viewport is tall enough for the largest band; this is the
    # critical difference from the broken page-coordinate clip approach.
    viewport_width = max(int(page_width), x + width + 16, 900)
    for idx, offset in enumerate(positions, start=1):
        band_doc_y = y0 + offset
        band_h = min(max_band_height, max(1, total_height - offset))
        name = first_filename if idx == 1 and first_filename else f'{prefix}_{idx:03d}.png'
        path = run_dir / name
        try:
            page.set_viewport_size({'width': int(viewport_width), 'height': int(max(600, band_h))})
        except Exception:
            pass
        try:
            page.evaluate('(y) => window.scrollTo(0, y)', max(0, band_doc_y))
        except Exception:
            pass
        time.sleep(max(0.05, wait_s))
        try:
            # full_page=False clip is viewport-relative, so y is zero after scroll.
            page.screenshot(path=str(path), full_page=False, clip={'x': x, 'y': 0, 'width': width, 'height': band_h})
            paths.append(str(path))
        except Exception:
            if not paths:
                raise
            break
    try:
        page.evaluate('() => window.scrollTo(0, 0)')
    except Exception:
        pass
    return paths

def _capture_tiles(page: Any, run_dir: Path, prefix: str, steps: int, scroll_px: int, wait_s: float, *, max_band_height: int = 14000, overlap_px: int = 160) -> List[str]:
    # R45O: keep the old receipt field name for compatibility, but use maximum-height
    # screenshot bands rather than hundreds of 900px viewport tiles.
    return _capture_locator_bands(
        page,
        run_dir,
        '[data-r45j-preserved-comments-root="true"]',
        first_filename=None,
        prefix=prefix,
        max_band_height=max_band_height,
        overlap_px=overlap_px,
        wait_s=wait_s,
    )



def _sanitize_facebook_target_url_r45ab(raw: str) -> str:
    import re
    raw_s = str(raw or '').strip().replace('\\&', '&')
    try:
        cleaned = r45d.sanitize_target_url(raw_s)
    except Exception:
        cleaned = raw_s
    if cleaned and cleaned.startswith(('http://', 'https://')) and '[' not in cleaned and '](' not in cleaned:
        return cleaned
    m = re.search(r'https?://[^\]\)\s"\']+', raw_s)
    if m:
        return m.group(0).replace('\\&', '&')
    return cleaned


def _target_url_identity(target_url: str) -> Dict[str, str]:
    try:
        parsed = urlparse(target_url or '')
        qs = parse_qs(parsed.query or '')
        return {
            'netloc': (parsed.netloc or '').lower(),
            'path': parsed.path or '',
            'story_fbid': (qs.get('story_fbid') or [''])[0],
            'id': (qs.get('id') or [''])[0],
        }
    except Exception:
        return {'netloc': '', 'path': '', 'story_fbid': '', 'id': ''}


def _target_url_looks_loaded(current_url: str, target_url: str) -> bool:
    if not target_url:
        return True
    current = (current_url or '').lower()
    target = (target_url or '').lower()
    if not current:
        return False
    if target and target in current:
        return True
    ident = _target_url_identity(target_url)
    story = (ident.get('story_fbid') or '').lower()
    page_id = (ident.get('id') or '').lower()
    path = (ident.get('path') or '').lower()
    if story and story in current:
        return True
    if 'permalink.php' in current and page_id and page_id in current:
        return True
    # Facebook may rewrite some direct post URLs to /posts/... or /videos/...
    if path and path not in {'/', ''} and path in current:
        return True
    # Root facebook.com/feed is never a safe match for a specific target URL.
    return False


def _guard_or_reopen_target_page(page: Any, target_url: str, *, timeout_ms: int, warnings: List[str], stage: str) -> Dict[str, Any]:
    if not target_url:
        return {'ok': True, 'stage': stage, 'reason': 'no_target_url'}
    try:
        current = page.url
    except Exception:
        current = ''
    if _target_url_looks_loaded(current, target_url):
        print(f'R45J_TARGET_PAGE_GUARD_PASS stage={stage} url={current}')
        return {'ok': True, 'stage': stage, 'url': current, 'reopened': False}
    print(f'R45J_TARGET_PAGE_GUARD_REOPEN stage={stage} current_url={current} target_url={target_url}')
    warnings.append(f'r45u_target_page_guard_reopen_stage={stage}_from={current}')
    try:
        page.goto(target_url, wait_until='domcontentloaded', timeout=timeout_ms)
        try:
            page.wait_for_load_state('networkidle', timeout=min(timeout_ms, 8000))
        except Exception:
            pass
    except Exception as e:
        warnings.append(f'r45u_target_page_guard_navigation_warning_stage={stage}={e}')
    try:
        final = page.url
    except Exception:
        final = ''
    ok = _target_url_looks_loaded(final, target_url)
    print(('R45J_TARGET_PAGE_GUARD_PASS' if ok else 'R45J_TARGET_PAGE_GUARD_BLOCKED') + f' stage={stage} url={final}')
    return {'ok': ok, 'stage': stage, 'url': final, 'reopened': True, 'target_url': target_url}



JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V = r"""
(opts) => {
  const viewportMarginPx = Number((opts && opts.viewportMarginPx) || 90);
  const clickGuardTopPx = Number((opts && opts.clickGuardTopPx) || 72);
  const clickGuardBottomPx = Number((opts && opts.clickGuardBottomPx) || 16);
  const skipKeys = new Set((opts && opts.skipKeys) || []);
  const normalize = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const composerOrUploadDeny = /\b(comment as|write a comment|comment composer|add photo|photo\/video|photo or video|camera|gif|sticker|avatar|open sticker|choose file|upload|attach|send|emoji|emoticon)\b/i;
  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0' && style.pointerEvents !== 'none';
  };
  const textOf = (el) => normalize((el && (el.innerText || el.textContent)) || '');
  const ariaOf = (el) => normalize([el && el.getAttribute && el.getAttribute('aria-label'), el && el.getAttribute && el.getAttribute('title')].join(' '));
  const pageText = () => (document.body && document.body.innerText || '');
  const parseProgress = () => {
    const m = pageText().match(/\b(\d{1,5})\s+of\s+(\d{1,5})\b/);
    if (!m) return null;
    return {current: Number(m[1]), total: Number(m[2]), text: m[0]};
  };
  const isComposerOrUploadSurface = (el) => {
    let n = el;
    for (let i = 0; n && i < 10; i++, n = n.parentElement) {
      const tag = (n.tagName || '').toLowerCase();
      const role = (n.getAttribute('role') || '').toLowerCase();
      const type = n.getAttribute('type') || '';
      const txt = normalize([ariaOf(n), (n.innerText || n.textContent || '').slice(0, 220)].join(' '));
      if (tag === 'input' && /file/i.test(type)) return true;
      if (tag === 'textarea' || role === 'textbox' || n.isContentEditable) return true;
      if (tag === 'form' && /comment|photo|video|upload|file/i.test(txt)) return true;
      if (composerOrUploadDeny.test(txt)) return true;
      try { if (n.querySelector && n.querySelector('input[type="file"]') && /comment|photo|video|upload|camera|gif|sticker/i.test(txt)) return true; } catch(e) {}
    }
    return false;
  };
  const expansionLabel = (text) => {
    text = normalize(text);
    if (!text) return '';
    let m = text.match(/^(View\s+hidden\s+(?:comments?|repl(?:y|ies)))$/i); if (m) return normalize(m[1]);
    m = text.match(/^(View\s+all\s+\d+\s+repl(?:y|ies))$/i); if (m) return normalize(m[1]);
    m = text.match(/^(View\s+\d+\s+repl(?:y|ies))$/i); if (m) return normalize(m[1]);
    m = text.match(/^(View\s+more\s+(?:\d+\s+)?repl(?:y|ies))$/i); if (m) return normalize(m[1]);
    m = text.match(/^(View\s+previous\s+repl(?:y|ies))$/i); if (m) return normalize(m[1]);
    m = text.match(/^([\p{L}\p{M}' .-]{1,80}\s+replied\s*[·•\-–—]\s*\d+\s+repl(?:y|ies))$/iu); if (m) return normalize(m[1]);
    m = text.match(/\b(View\s+(?:hidden\s+(?:comments?|repl(?:y|ies))|all\s+\d+\s+repl(?:y|ies)|\d+\s+repl(?:y|ies)|more\s+(?:\d+\s+)?repl(?:y|ies)|previous\s+repl(?:y|ies)))\b/i);
    if (m && text.length <= 180) return normalize(m[1]);
    m = text.match(/\b([\p{L}\p{M}' .-]{1,80}\s+replied\s*[·•\-–—]\s*\d+\s+repl(?:y|ies))\b/iu);
    if (m && text.length <= 220) return normalize(m[1]);
    return '';
  };
  const findDialogSurface = () => {
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"]')).filter(isVisible);
    const scored = [];
    for (const el of dialogs) {
      const rect = el.getBoundingClientRect();
      if (rect.width < 280 || rect.height < 180) continue;
      const txt = textOf(el).slice(0, 6000).toLowerCase();
      let score = rect.width * rect.height;
      if (/post|comment|reply|view hidden|view all|comment as|write a comment|like reply/.test(txt)) score += 1000000;
      if (/restore britain/.test(txt)) score += 1000000;
      scored.push({el, score, width: Math.round(rect.width), height: Math.round(rect.height), text_sample: txt.slice(0, 220)});
    }
    scored.sort((a,b) => b.score - a.score);
    return scored[0] || null;
  };
  const surfaceInfo = findDialogSurface();
  if (!surfaceInfo) {
    return {
      marker: 'R45AB_SURFACE_LOCKED_PROBE',
  // R45X_EXPAND_ONLY_PROBE compatibility marker retained for older static tests; R45AB now locks expansion to the target surface.
      candidate: null,
      visible_count: 0,
      visible_labels: [],
      text_chars: pageText().length,
      progress: parseProgress(),
      expansion_only: true,
      broad_scan_used: false,
      surface_required: true,
      surface_found: false,
      dialog_surface_required: true,
      stop_reason: 'target_comments_dialog_missing',
      current_url: location.href,
    };
  }
  const surface = surfaceInfo.el;
  const clickableAncestor = (el) => {
    let n = el;
    for (let i = 0; n && i < 8 && surface.contains(n); i++, n = n.parentElement) {
      if (isComposerOrUploadSurface(n)) return null;
      const role = (n.getAttribute('role') || '').toLowerCase();
      const tag = (n.tagName || '').toLowerCase();
      const style = window.getComputedStyle(n);
      if (role === 'button' || tag === 'button' || tag === 'a' || tag === 'summary' || style.cursor === 'pointer') return n;
    }
    return null;
  };
  const visibleTextRect = (textNode, label) => {
    const raw = textNode.nodeValue || '';
    const idx = raw.toLowerCase().indexOf(label.toLowerCase());
    try {
      const range = document.createRange();
      if (idx >= 0) { range.setStart(textNode, idx); range.setEnd(textNode, Math.min(raw.length, idx + label.length)); }
      else { range.selectNodeContents(textNode); }
      const rects = Array.from(range.getClientRects()).filter(r => r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight + viewportMarginPx && r.right > 0 && r.left < window.innerWidth);
      if (rects.length) return rects[0];
    } catch(e) {}
    const parent = textNode.parentElement;
    if (!parent) return null;
    const r = parent.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight + viewportMarginPx) return r;
    return null;
  };
  const keyFor = (label, rect) => [label.toLowerCase(), Math.round((rect.top + window.scrollY) / 8), Math.round(rect.left / 8)].join('|');
  const walker = document.createTreeWalker(surface, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || !surface.contains(parent) || !isVisible(parent) || isComposerOrUploadSurface(parent)) return NodeFilter.FILTER_REJECT;
      const val = normalize(node.nodeValue || '');
      if (!val || val.length > 220) return NodeFilter.FILTER_REJECT;
      return expansionLabel(val) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }
  });
  const controls = [];
  let node;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    const label = expansionLabel(node.nodeValue || '') || expansionLabel(textOf(parent)) || expansionLabel(ariaOf(parent));
    if (!label) continue;
    let rect = visibleTextRect(node, label);
    if (!rect) continue;
    const target = clickableAncestor(parent);
    if (!target || !isVisible(target) || isComposerOrUploadSurface(target)) continue;
    if (rect.top < clickGuardTopPx || rect.bottom > (window.innerHeight - clickGuardBottomPx)) {
      try { target.scrollIntoView({block: 'center', inline: 'nearest'}); } catch(e) {}
      rect = visibleTextRect(node, label) || rect;
    }
    if (rect.top < 8 || rect.bottom <= 0 || rect.top >= window.innerHeight) continue;
    const key = keyFor(label, rect);
    if (skipKeys.has(key)) continue;
    const x = Math.min(Math.max(rect.left + rect.width / 2, 3), Math.max(3, window.innerWidth - 3));
    const y = Math.min(Math.max(rect.top + rect.height / 2, 3), Math.max(3, window.innerHeight - 3));
    const hit = document.elementFromPoint(x, y);
    if (!hit || !surface.contains(hit) || isComposerOrUploadSurface(hit)) continue;
    controls.push({label, key, x, y, top: rect.top, left: rect.left, width: rect.width, height: rect.height, targetRole: target.getAttribute('role') || '', targetTag: (target.tagName || '').toLowerCase()});
  }
  controls.sort((a,b) => (a.top - b.top) || (a.left - b.left));
  const first = controls[0] || null;
  return {
    marker: 'R45AB_SURFACE_LOCKED_PROBE',
    candidate: first,
    visible_count: controls.length,
    visible_labels: controls.slice(0, 12).map(c => c.label),
    text_chars: pageText().length,
    progress: parseProgress(),
    expansion_only: true,
    broad_scan_used: false,
    composer_upload_controls_excluded: true,
    surface_required: true,
    surface_found: true,
    dialog_surface_required: true,
    surface_width: surfaceInfo.width,
    surface_height: surfaceInfo.height,
  };
}
"""

JS_SCROLL_DOWNWARD_FRONTIER_R45V = r"""
(opts) => {
  const px = Number((opts && opts.scrollPx) || 650);
  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const textOf = (el) => (el.innerText || '').slice(0, 2600).toLowerCase();
  const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"]')).filter(isVisible).map(el => {
    const rect = el.getBoundingClientRect();
    const text = textOf(el);
    let score = rect.width * rect.height;
    if (/post|comment|reply|view hidden|view all|comment as|write a comment|like reply/.test(text)) score += 1000000;
    if (/restore britain/.test(text)) score += 1000000;
    return {el, score, width: Math.round(rect.width), height: Math.round(rect.height)};
  }).filter(item => item.width >= 280 && item.height >= 180).sort((a,b) => b.score - a.score);
  const surfaceInfo = dialogs[0] || null;
  if (!surfaceInfo) {
    return {changed: 0, targets: [], surface_required: true, surface_found: false, stop_reason: 'target_comments_dialog_missing', window_before: window.scrollY, window_after: window.scrollY};
  }
  const surface = surfaceInfo.el;
  const targets = [];
  const candidates = [surface, ...Array.from(surface.querySelectorAll('div, section, main, article'))];
  for (const el of candidates) {
    if (!isVisible(el) || !surface.contains(el)) continue;
    const scrollable = (el.scrollHeight || 0) - (el.clientHeight || 0);
    if (scrollable < 120) continue;
    const rect = el.getBoundingClientRect();
    if (rect.height < 140 || rect.width < 260) continue;
    const role = (el.getAttribute('role') || '').toLowerCase();
    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
    const text = textOf(el);
    let score = scrollable + rect.height;
    if (el === surface) score += 5000;
    if (/comment|reply|view hidden|view all|view more|like reply|of\s+\d+/.test(text + ' ' + aria)) score += 10000;
    targets.push({el, score, role, aria: aria.slice(0,80), scrollable, height: Math.round(rect.height), width: Math.round(rect.width)});
  }
  targets.sort((a,b) => b.score - a.score);
  let changed = 0;
  const summaries = [];
  const item = targets[0] || null;
  if (item) {
    try {
      const before = item.el.scrollTop;
      item.el.scrollTop = Math.min(item.el.scrollTop + px, Math.max(0, item.el.scrollHeight - item.el.clientHeight));
      item.el.dispatchEvent(new Event('scroll', {bubbles:true}));
      if (item.el.scrollTop !== before) changed += 1;
      summaries.push({role: item.role, aria: item.aria, scrollable: item.scrollable, height: item.height, width: item.width, before, after: item.el.scrollTop});
    } catch(e) {}
  }
  return {changed, targets: summaries, surface_required: true, surface_found: true, surface_width: surfaceInfo.width, surface_height: surfaceInfo.height, window_before: window.scrollY, window_after: window.scrollY};
}
"""

def _close_non_working_pages_r45z(context: Any, page: Any, warnings: List[str], stage: str) -> None:
    """R45Z: keep the operator-visible browser on the requested target tab.

    Persistent Chromium can restore a crashed facebook.com/feed tab in front of the
    fresh permalink tab. That makes the visible browser look broken even while the
    Playwright Page object points at the target URL. For a specific --target-url,
    close every non-working tab after opening the target page. This only closes
    browser tabs in the current Playwright-controlled session; it does not inspect
    or parse browser profile files.
    """
    closed: List[str] = []
    try:
        pages = list(context.pages)
    except Exception as e:
        warnings.append(f'r45z_list_pages_warning_stage={stage}={e}')
        return
    for other in pages:
        if other is page:
            continue
        try:
            url = other.url
        except Exception:
            url = ''
        try:
            other.close(run_before_unload=False)
            closed.append(url or 'about:blank')
        except Exception as e:
            warnings.append(f'r45z_close_non_target_tab_warning_stage={stage}_url={url}={e}')
    if closed:
        warnings.append(f'r45z_closed_non_target_tabs_stage={stage}_count={len(closed)}')
        print('R45Z_CLOSED_NON_TARGET_TABS ' + json.dumps({'stage': stage, 'count': len(closed), 'urls': closed[:8]}, ensure_ascii=False))
    try:
        page.bring_to_front()
    except Exception as e:
        warnings.append(f'r45z_bring_target_to_front_warning_stage={stage}={e}')


def _playwright_mouse_downward_expand(page: Any, args: argparse.Namespace, patterns: List[str]) -> Dict[str, Any]:
    """R45V: click the first visible Facebook expand control with Playwright mouse.

    This avoids in-page synthetic PointerEvent/MouseEvent dispatch on Facebook
    Comet role=button controls. It clicks one visible control, waits, rescans the
    same viewport, then scrolls downward only when no visible expand control remains.
    """
    started = time.monotonic()
    max_seconds = max(15.0, float(getattr(args, 'expand_max_seconds', 180) or 180))
    scroll_px = int(getattr(args, 'expand_scroll_px', 650) or 650)
    scroll_delay = float(getattr(args, 'expand_scroll_delay_seconds', 0.8) or 0.8)
    after_click_delay = float(getattr(args, 'expand_after_click_delay_seconds', 0.45) or 0.45)
    click_delay = float(getattr(args, 'expand_click_delay_seconds', 0.08) or 0.08)
    viewport_margin = int(getattr(args, 'expand_viewport_margin_px', 90) or 90)
    rounds_limit = int(getattr(args, 'expand_rounds', 2000) or 2000)
    skip_counts: Dict[str, int] = {}
    clicked_total = 0
    scroll_events = 0
    stable_no_candidate_rounds = 0
    last_probe: Dict[str, Any] = {}

    def elapsed() -> int:
        return int(round(time.monotonic() - started))

    def _probe(skip_keys_local: List[str]) -> Dict[str, Any]:
        try:
            return page.evaluate(JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V, {
                'patterns': patterns,
                'viewportMarginPx': viewport_margin,
                'skipKeys': skip_keys_local,
            }) or {}
        except Exception:
            return {}

    def _reply_count_from_label(label: str) -> int:
        parts = []
        for raw in str(label or '').replace(',', ' ').replace('·', ' ').split():
            try:
                parts.append(int(raw))
            except Exception:
                pass
        return max(parts or [0])

    def _extra_settle_seconds_for_label(label: str) -> float:
        # R45AA: max settle window. Large buckets need real time to stream
        # replies after Facebook removes the clicked "View all N replies" text.
        n = _reply_count_from_label(label)
        if n >= 250:
            return 16.0
        if n >= 100:
            return 12.0
        if n >= 25:
            return 7.0
        if n >= 5:
            return 3.5
        return 1.4

    def _minimum_settle_seconds_for_label(label: str) -> float:
        # R45AA: do not let the old "text changed and looks stable" shortcut
        # exit after ~1-2s for huge reply buckets. That was why the runner
        # clicked "View all 302 replies" and immediately scrolled away.
        n = _reply_count_from_label(label)
        if n >= 250:
            return 9.0
        if n >= 100:
            return 7.0
        if n >= 25:
            return 4.0
        if n >= 5:
            return 2.0
        return 0.6

    def _wait_for_click_settle(label: str, before_chars: int, before_progress: Any) -> Dict[str, Any]:
        # R45AA: clicking a large opener such as "View all 302 replies" can
        # remove that visible label immediately while Facebook streams the 302
        # replies in later. Enforce a minimum local hold before any scroll.
        max_secs = _extra_settle_seconds_for_label(label)
        min_secs = _minimum_settle_seconds_for_label(label)
        started_settle = time.monotonic()
        deadline = started_settle + max_secs
        min_deadline = started_settle + min_secs
        best: Dict[str, Any] = {}
        last_sig = None
        stable = 0
        while time.monotonic() < deadline:
            time.sleep(0.25)
            p = _probe([k for k, v in skip_counts.items() if v >= 5])
            if p:
                best = p
            visible_count = int((p or {}).get('visible_count') or 0)
            text_chars = int((p or {}).get('text_chars') or before_chars)
            sig = (
                text_chars,
                visible_count,
                json.dumps((p or {}).get('progress'), sort_keys=True, ensure_ascii=False),
                '|'.join(((p or {}).get('visible_labels') or [])[:4]),
            )
            if sig == last_sig:
                stable += 1
            else:
                stable = 0
                last_sig = sig

            past_min = time.monotonic() >= min_deadline

            # It is safe to continue only after the minimum wait has elapsed.
            # If new expansion labels are visible, the next main loop will click
            # the first one in the same local area.
            if past_min and visible_count > 0 and stable >= 1:
                break

            # Old R45Z exited here too early after text changed. R45AA permits
            # this only after the minimum hold, and only with a stronger stable
            # signal, so large buckets do not get abandoned.
            if past_min and text_chars != before_chars and stable >= 6:
                break

        if best:
            try:
                best['r45aa_settle_elapsed_seconds'] = round(time.monotonic() - started_settle, 2)
                best['r45aa_minimum_settle_seconds'] = min_secs
                best['r45aa_max_settle_seconds'] = max_secs
            except Exception:
                pass
        return best

    for step in range(1, rounds_limit + 1):
        if time.monotonic() - started > max_seconds:
            break
        skip_keys = [k for k, v in skip_counts.items() if v >= 5]
        try:
            probe = _probe(skip_keys)
        except Exception as e:
            print('R45H_PROGRESS ' + json.dumps({'event': 'R45V_PROBE_FAILED', 'step': step, 'error': str(e)[:180], 'elapsed_seconds': elapsed()}, ensure_ascii=False))
            break
        last_probe = probe
        candidate = probe.get('candidate') if isinstance(probe, dict) else None
        if candidate:
            label = str(candidate.get('label') or '')
            key = str(candidate.get('key') or f'{label}:{step}')
            before_chars = int(probe.get('text_chars') or 0)
            before_progress = probe.get('progress')
            x = float(candidate.get('x') or 0)
            y = float(candidate.get('y') or 0)
            time.sleep(max(0.0, click_delay))
            click_error = ''
            try:
                page.mouse.move(x, y)
                page.mouse.down()
                time.sleep(0.03)
                page.mouse.up()
            except Exception as e:
                click_error = str(e)[:180]
            time.sleep(max(0.05, after_click_delay))
            after_probe = _wait_for_click_settle(label, before_chars, before_progress)
            if not after_probe:
                after_probe = _probe([k for k, v in skip_counts.items() if v >= 5])
            after_chars = int(after_probe.get('text_chars') or before_chars)
            after_progress = after_probe.get('progress')
            remaining_visible = int(after_probe.get('visible_count') or 0)
            no_op = bool(click_error) or (after_chars == before_chars and after_progress == before_progress and remaining_visible == int(probe.get('visible_count') or 0))
            if no_op:
                skip_counts[key] = skip_counts.get(key, 0) + 1
            else:
                skip_counts.pop(key, None)
            clicked_total += 0 if click_error else 1
            print('R45H_PROGRESS ' + json.dumps({
                'event': 'R45X_EXPAND_CLICK',
                'step': step,
                'label': label,
                'x': round(x, 1),
                'y': round(y, 1),
                'click_error': click_error,
                'no_op': no_op,
                'no_op_count': skip_counts.get(key, 0),
                'delta_text_chars': after_chars - before_chars,
                'before_progress': before_progress,
                'after_progress': after_progress,
                'remaining_visible_candidates': remaining_visible,
                'visible_labels': (after_probe.get('visible_labels') or [])[:8],
                'settle_seconds': _extra_settle_seconds_for_label(label),
                'minimum_settle_seconds': _minimum_settle_seconds_for_label(label),
                'actual_settle_elapsed_seconds': after_probe.get('r45aa_settle_elapsed_seconds'),
                'elapsed_seconds': elapsed(),
            }, ensure_ascii=False))
            continue

        if isinstance(probe, dict) and probe.get('surface_required') and not probe.get('surface_found'):
            print('R45H_PROGRESS ' + json.dumps({
                'event': 'R45AB_TARGET_SURFACE_MISSING_STOP',
                'step': step,
                'stop_reason': probe.get('stop_reason') or 'target_comments_dialog_missing',
                'current_url': probe.get('current_url'),
                'elapsed_seconds': elapsed(),
            }, ensure_ascii=False))
            stable_no_candidate_rounds = int(getattr(args, 'expand_stop_after_stable_rounds', 4) or 4)
            break

        try:
            scroll_result = page.evaluate(JS_SCROLL_DOWNWARD_FRONTIER_R45V, {'scrollPx': scroll_px}) or {}
        except Exception as e:
            scroll_result = {'changed': 0, 'error': str(e)[:180]}
        changed = int(scroll_result.get('changed') or 0)
        if changed:
            scroll_events += changed
            stable_no_candidate_rounds = 0
        else:
            stable_no_candidate_rounds += 1
        print('R45H_PROGRESS ' + json.dumps({
            'event': 'R45V_DOWNWARD_SCROLL',
            'step': step,
            'changed': changed,
            'visible_labels_before_scroll': (probe.get('visible_labels') or [])[:8],
            'progress': probe.get('progress'),
            'scroll_targets': scroll_result.get('targets') or [],
            'elapsed_seconds': elapsed(),
        }, ensure_ascii=False))
        time.sleep(max(0.05, scroll_delay))
        if stable_no_candidate_rounds >= int(getattr(args, 'expand_stop_after_stable_rounds', 4) or 4):
            break

    final_probe = last_probe
    try:
        final_probe = _probe([k for k, v in skip_counts.items() if v >= 5]) or last_probe
    except Exception:
        pass
    final_progress = final_probe.get('progress') if isinstance(final_probe, dict) else None
    main_progress_incomplete = False
    if isinstance(final_progress, dict):
        try:
            main_progress_incomplete = int(final_progress.get('current') or 0) < int(final_progress.get('total') or 0)
        except Exception:
            main_progress_incomplete = False
    timed_out = (time.monotonic() - started) > max_seconds
    return {
        'marker': 'YTCE_R45V_PLAYWRIGHT_MOUSE_DOWNWARD_EXPAND',
        'status': 'NEEDS_MORE_EXPANSION_R45V_PLAYWRIGHT_MOUSE_DOWNWARD_EXPAND' if timed_out or main_progress_incomplete else 'PASS_R45V_PLAYWRIGHT_MOUSE_DOWNWARD_EXPAND',
        'clicked_total': clicked_total,
        'scroll_events': scroll_events,
        'timed_out': timed_out,
        'elapsed_seconds': elapsed(),
        'final_text_chars': int((final_probe or {}).get('text_chars') or 0) if isinstance(final_probe, dict) else 0,
        'remaining_visible_candidates': int((final_probe or {}).get('visible_count') or 0) if isinstance(final_probe, dict) else 0,
        'visible_unresolved_labels': ((final_probe or {}).get('visible_labels') or [])[:12] if isinstance(final_probe, dict) else [],
        'final_progress': final_progress,
        'main_progress_incomplete': main_progress_incomplete,
        'downward_only': True,
        'playwright_mouse_clicks': True,
        'synthetic_in_page_click_dispatch': False,
        'expansion_only': True,
        'broad_scan_used': False,
        'r45x_expand_comments_only': True,
        'r45ab_surface_lock': True,
        'surface_found': bool((final_probe or {}).get('surface_found')) if isinstance(final_probe, dict) else False,
    }

def _main_expand_still_incomplete(summary: Optional[Dict[str, Any]]) -> bool:
    if not summary:
        return False
    if summary.get('timed_out'):
        return True
    if int(summary.get('remaining_visible_candidates') or 0) > 0:
        return True
    if summary.get('visible_unresolved_labels'):
        return True
    progress = summary.get('final_progress')
    if isinstance(progress, dict):
        try:
            current = int(progress.get('current') or 0)
            total = int(progress.get('total') or 0)
        except Exception:
            current = total = 0
        if total and current < total:
            return True
    if summary.get('main_progress_incomplete'):
        return True
    return False

def run_live(args: argparse.Namespace) -> Dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise SystemExit(f'{STATUS_BLOCKED}: Playwright is not available: {e}')

    r45h.patch_r45d_globals()
    output_root = Path(args.output_root)
    run_dir = r45d.ensure_dir(output_root / f'facebook_preserved_visual_screenshot_runner_{utc_stamp()}')
    reference_text = _safe_read(args.reference_text)
    target_url = _sanitize_facebook_target_url_r45ab(args.target_url)
    warnings: List[str] = []
    if target_url != args.target_url:
        warnings.append('target_url_was_sanitized_from_markdown_or_escaped_form')

    with sync_playwright() as p:
        # R45M: BrowserType.launch() does not accept viewport. Keep viewport
        # on contexts only, while preserving maximized operator-controlled browser UI.
        launch_kwargs: Dict[str, Any] = {
            'headless': False,
            'args': [
                '--start-maximized',
                '--disable-session-crashed-bubble',
                '--hide-crash-restore-bubble',
                '--no-first-run',
                '--no-default-browser-check',
            ],
        }
        context_kwargs: Dict[str, Any] = {'viewport': None}
        if args.chromium_executable:
            launch_kwargs['executable_path'] = args.chromium_executable
        if args.user_data_dir:
            context = p.chromium.launch_persistent_context(args.user_data_dir, **launch_kwargs, **context_kwargs)
        else:
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(**context_kwargs)
        # R45Y: do not reuse a restored/crashed facebook.com feed tab as the
        # working page for a specific permalink. Open a fresh tab for the target
        # and bring it to front; old restored tabs are left alone but ignored.
        if target_url and not args.manual_current_page:
            page = context.new_page()
        else:
            page = context.pages[0] if context.pages else context.new_page()
        try:
            page.bring_to_front()
        except Exception:
            pass
        page.on('console', lambda msg: print(msg.text) if (msg.text.startswith('R45H_PROGRESS') or msg.text.startswith('R45N_REPLIED_REPLY_BUCKET_PROGRESS')) else None)
        def _r45w_block_filechooser(chooser: Any) -> None:
            try:
                print('R45W_FILE_CHOOSER_BLOCKED')
                chooser.set_files([])
            except Exception as e:
                warnings.append(f'r45w_filechooser_block_warning={e}')
        try:
            page.on('filechooser', _r45w_block_filechooser)
        except Exception as e:
            warnings.append(f'r45w_filechooser_handler_warning={e}')
        if target_url and not args.manual_current_page:
            try:
                page.goto(target_url, wait_until='domcontentloaded', timeout=args.timeout_seconds * 1000)
            except Exception as e:
                warnings.append(f'initial_navigation_warning={e}')
        try:
            page.add_style_tag(content=r45d.FOCUS_CSS)
        except Exception as e:
            warnings.append(f'focus_css_injection_warning={e}')

        # R45Y: run the target guard before the operator pause. Previously the
        # pause could show a restored facebook.com feed tab even though a specific
        # permalink was requested, which made the run look broken before expansion.
        target_page_guard = None
        if target_url and not args.manual_current_page:
            target_page_guard = _guard_or_reopen_target_page(
                page,
                target_url,
                timeout_ms=args.timeout_seconds * 1000,
                warnings=warnings,
                stage='before_pre_expand_pause',
            )
            if not target_page_guard.get('ok'):
                warnings.append('r45y_blocked_before_pre_expand_pause_browser_not_on_requested_target')
                receipt = {
                    'marker': MARKER,
                    'status': STATUS_BLOCKED,
                    'schema_version': SCHEMA_VERSION,
                    'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
                    'run_dir': str(run_dir),
                    'target_url': args.target_url,
                    'sanitized_target_url': target_url,
                    'target_page_guard': target_page_guard,
                    'warnings': warnings,
                    'contract': contract(),
                    'side_effect_flags': side_effect_flags(True, True, False),
                }
                r45d.write_json(run_dir / 'r45j_facebook_preserved_visual_screenshot_receipt.json', receipt)
                print('R45J_TARGET_PAGE_GUARD_STOPPED_BEFORE_PRE_EXPAND_PAUSE')
                return receipt
            _close_non_working_pages_r45z(context, page, warnings, 'before_pre_expand_pause')
        if args.pre_expand_pause:
            print('R45J_PRE_EXPAND_PAUSE')
            print('Check login/page, then press ENTER in this CMD window to start expansion.')
            try: input()
            except EOFError: pass

        # R45U/R45Y: re-check after the operator pause in case the operator or a
        # restore-session prompt changed the active target page before expansion.
        if target_url and not args.manual_current_page:
            target_page_guard = _guard_or_reopen_target_page(
                page,
                target_url,
                timeout_ms=args.timeout_seconds * 1000,
                warnings=warnings,
                stage='before_auto_expand',
            )
            if not target_page_guard.get('ok'):
                warnings.append('r45u_blocked_before_auto_expand_browser_not_on_requested_target')
                receipt = {
                    'marker': MARKER,
                    'status': STATUS_BLOCKED,
                    'schema_version': SCHEMA_VERSION,
                    'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
                    'run_dir': str(run_dir),
                    'target_url': args.target_url,
                    'sanitized_target_url': target_url,
                    'target_page_guard': target_page_guard,
                    'warnings': warnings,
                    'contract': contract(),
                    'side_effect_flags': side_effect_flags(True, True, False),
                }
                r45d.write_json(run_dir / 'r45j_facebook_preserved_visual_screenshot_receipt.json', receipt)
                print('R45J_TARGET_PAGE_GUARD_STOPPED_BEFORE_EXPANSION')
                return receipt
            _close_non_working_pages_r45z(context, page, warnings, 'before_auto_expand')

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
                'progressiveTopDown': not args.no_progressive_top_down_expansion,
                'viewportMarginPx': args.expand_viewport_margin_px,
                'maxTopDownSweeps': args.progressive_top_down_sweeps,
                'localExhaustPasses': args.local_exhaust_passes,
            }
            try:
                print(f'R45J_AUTO_EXPAND_START max_seconds={args.expand_max_seconds}')
                print('R45V_PLAYWRIGHT_MOUSE_DOWNWARD_EXPAND_START')
                print('R45X_EXPAND_COMMENTS_ONLY_START')
                auto_expand_summary = _playwright_mouse_downward_expand(page, args, r45h.EXPAND_PATTERNS_R45H)
                print('R45X_EXPAND_COMMENTS_ONLY_DONE')
                print('R45V_PLAYWRIGHT_MOUSE_DOWNWARD_EXPAND_DONE')
                print('R45J_AUTO_EXPAND_DONE')
            except Exception as e:
                warnings.append(f'auto_expand_warning={e}')

            if not args.no_replied_reply_bucket_expand and _main_expand_still_incomplete(auto_expand_summary):
                warnings.append('r45s_replied_bucket_followup_deferred_until_main_downward_expansion_complete')
            elif not args.no_replied_reply_bucket_expand:
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
                        'progressiveTopDown': not args.no_progressive_top_down_expansion,
                        'viewportMarginPx': args.expand_viewport_margin_px,
                        'maxTopDownSweeps': args.progressive_top_down_sweeps,
                'localExhaustPasses': args.local_exhaust_passes,
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
            try:
                surface_summary = _prepare_preserved_visual_screenshot_surface(page)
                if isinstance(visual_clean_summary, dict):
                    visual_clean_summary['screenshot_surface'] = surface_summary
            except Exception as e:
                warnings.append(f'visual_screenshot_surface_prepare_warning={e}')
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

        column_screenshot_paths: List[str] = []
        if not args.no_screenshots:
            try:
                column_screenshot_paths = _capture_locator_bands(
                    page,
                    run_dir,
                    '[data-r45j-preserved-comments-root="true"]',
                    first_filename='facebook_preserved_visual_comments_column.png',
                    prefix='facebook_preserved_visual_comments_column_part',
                    max_band_height=args.max_screenshot_band_height,
                    overlap_px=getattr(args, 'screenshot_band_overlap_px', 160),
                    wait_s=args.tile_wait_seconds,
                )
                column_screenshot_path = column_screenshot_paths[0] if column_screenshot_paths else None
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
                    # R45O: keep tile receipt compatibility but capture maximum-size bands.
                    # If the column bands were already captured, reuse their paths instead
                    # of creating hundreds of small viewport captures.
                    tile_paths = list(column_screenshot_paths)
                    if not tile_paths:
                        tile_paths = _capture_tiles(
                            page,
                            run_dir,
                            'facebook_preserved_visual_tile',
                            args.tile_steps,
                            args.tile_scroll_px,
                            args.tile_wait_seconds,
                            max_band_height=args.max_screenshot_band_height,
                            overlap_px=getattr(args, 'screenshot_band_overlap_px', 160),
                        )
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
            'target_page_guard': target_page_guard,
            'final_page_url': final_url,
            'run_dir': str(run_dir),
            'pre_clean_raw_dom_path': raw_dom_path,
            'pre_clean_inner_text_path': inner_text_path,
            'preserved_visual_clean_dom_path': clean_html_path,
            'preserved_visual_clean_text_path': clean_text_path,
            'preserved_visual_comments_column_screenshot_path': column_screenshot_path,
            'preserved_visual_comments_column_screenshot_paths': column_screenshot_paths,
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
        {'name': 'r45o_replied_reply_bucket_async_present', 'status': 'pass' if 'async (opts) =>' in JS_CLICK_REPLIED_REPLY_BUCKETS_R45N and 'R45N_REPLIED_REPLY_BUCKET_PROGRESS' in JS_CLICK_REPLIED_REPLY_BUCKETS_R45N else 'fail'},
        {'name': 'r45o_max_height_screenshot_bands_present', 'status': 'pass' if '_capture_locator_bands' in open(__file__, encoding='utf-8').read() and 'max_screenshot_band_height' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45p_clickable_replied_bucket_target_present', 'status': 'pass' if 'clicking inert text' in JS_CLICK_REPLIED_REPLY_BUCKETS_R45N and "tag === 'summary'" in JS_CLICK_REPLIED_REPLY_BUCKETS_R45N else 'fail'},
        {'name': 'r45p_viewport_relative_bands_present', 'status': 'pass' if 'viewport-relative' in open(__file__, encoding='utf-8').read() and "'y': 0" in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45q_downward_frontier_present', 'status': 'pass' if 'r45q_downward_frontier_rule' in contract() and 'clickVisibleUntilExhausted' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND and 'scrollTopForRescan' not in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND else 'fail'},
        {'name': 'r45r_local_exhaust_present', 'status': 'pass' if 'r45r_local_exhaust_rule' in contract() and 'requestedLocalPasses' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND and ('Math.max(12' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND or 'Math.max(500' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND) else 'fail'},
        {'name': 'r45u_target_page_guard_present', 'status': 'pass' if '_guard_or_reopen_target_page' in open(__file__, encoding='utf-8').read() and 'R45J_TARGET_PAGE_GUARD_BLOCKED' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45v_playwright_mouse_downward_expand_present', 'status': 'pass' if '_playwright_mouse_downward_expand' in open(__file__, encoding='utf-8').read() and ('R45V_MOUSE_CLICK' in open(__file__, encoding='utf-8').read() or 'R45X_EXPAND_CLICK' in open(__file__, encoding='utf-8').read()) and 'page.mouse.down()' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45w_no_file_chooser_guard_present', 'status': 'pass' if 'r45w_no_file_chooser_rule' in contract() and 'isComposerOrUploadSurface' in JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V and "page.on('filechooser'" in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45x_expand_comments_only_present', 'status': 'pass' if 'r45x_expansion_only_rule' in contract() and 'R45X_EXPAND_ONLY_PROBE' in JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V and 'broad_scan_used' in JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V and 'expansion_only: true' in JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V else 'fail'},
        {'name': 'r45y_pre_pause_target_guard_present', 'status': 'pass' if 'r45y_pre_pause_target_rule' in contract() and 'before_pre_expand_pause' in open(__file__, encoding='utf-8').read() and 'context.new_page()' in open(__file__, encoding='utf-8').read() and '--disable-session-crashed-bubble' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45z_active_target_tab_and_settle_present', 'status': 'pass' if 'r45z_active_target_tab_rule' in contract() and '_close_non_working_pages_r45z' in open(__file__, encoding='utf-8').read() and 'R45Z_CLOSED_NON_TARGET_TABS' in open(__file__, encoding='utf-8').read() and '_wait_for_click_settle' in open(__file__, encoding='utf-8').read() and '--hide-crash-restore-bubble' in open(__file__, encoding='utf-8').read() else 'fail'},
        {'name': 'r45aa_large_bucket_settle_hold_present', 'status': 'pass' if 'r45aa_large_bucket_settle_rule' in contract() and '_minimum_settle_seconds_for_label' in open(__file__, encoding='utf-8').read() and 'past_min' in open(__file__, encoding='utf-8').read() and 'actual_settle_elapsed_seconds' in open(__file__, encoding='utf-8').read() else 'fail'},
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
    ap.add_argument('--no-progressive-top-down-expansion', action='store_true', help='Disable R45O viewport top-to-bottom expansion order and use legacy priority sorting.')
    ap.add_argument('--expand-viewport-margin-px', type=int, default=90, help='Viewport margin for R45O top-to-bottom visible-control expansion.')
    ap.add_argument('--progressive-top-down-sweeps', type=int, default=3, help='R45Q local visible-control exhaustion passes per downward viewport; retained under the old name for CLI compatibility and does not trigger a scroll-back-to-top rescan.')
    ap.add_argument('--local-exhaust-passes', type=int, default=500, help='R45S maximum first-visible single-click rescans before scrolling down from one visible area.')
    ap.add_argument('--max-screenshot-band-height', type=int, default=14000, help='Maximum height of each R45O comments-column screenshot band.')
    ap.add_argument('--screenshot-band-overlap-px', type=int, default=160, help='Overlap between R45O maximum-height screenshot bands.')
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
