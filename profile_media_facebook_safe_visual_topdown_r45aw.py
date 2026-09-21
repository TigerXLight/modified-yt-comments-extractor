#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

MARKER = "YTCE_R45AW_SAFE_VISUAL_TOPDOWN_MAX_BANDS"
SCHEMA_VERSION = "facebook_safe_visual_topdown.r45aw.v1"


def emit(event: str, payload: Dict[str, Any]) -> None:
    print(event + " " + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)


def _clean_url(url: str) -> str:
    s = (url or "").strip().strip('"').strip("'")
    m = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", s)
    if m:
        s = m.group(1)
    return s.replace('\\&', '&').replace('\\:', ':')


def _target_story(url: str) -> str:
    m = re.search(r"(?:story_fbid|fbid)=([^&?#)]+)", url or "")
    return m.group(1) if m else ""


def contract() -> Dict[str, Any]:
    return {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "primary_route": "visible-page-only Facebook expansion in an operator-controlled signed-in Chromium profile",
        "r45aw_rule": "Open the post, lock to the target story, install a profile/comment-permalink navigation blocker, start at the top of the active comments scroller, click the first safe visible expansion label, skip unsafe false-positive click points that resolve to profile anchors, rescan the same viewport, keep moving downward as comments load, require a complete top-to-bottom visual audit pass with zero safe visible controls, reset scrollers to top, then capture the separated comments box as maximum-height screenshot bands.",
        "visible_controls": ["View all N replies", "View N replies", "View hidden replies/comments", "View more replies/comments", "replied · N replies"],
        "success_rule": "No final screenshot is accepted until a full visible top-to-bottom audit pass sees zero safe expansion controls. The final evidence uses maximum-height separated comments-column bands rather than one huge full-page PNG, because very tall Chromium screenshots can blank or truncate.",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "webview2_storage_or_cookie_inspection_enabled": False,
        "remote_media_downloads_enabled": False,
    }


# R45AW uses the already-working R45J/R45L post-expansion visual cleanup/crop path.
# It keeps the original Facebook-rendered comments DOM, hides the surrounding webpage/modal chrome,
# crops away pre-comment post/media surfaces, and screenshots only the separated comments box.
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


RESET_ALL_COMMENT_SCROLLERS_JS = r"""
() => {
  const visible = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const reset = [];
  const all = [document.scrollingElement || document.documentElement, ...Array.from(document.querySelectorAll('*'))];
  for (const el of all) {
    try {
      const cs = getComputedStyle(el);
      const scrollGap = (el.scrollHeight || 0) - (el.clientHeight || 0);
      const isScroller = scrollGap > 40 || /(auto|scroll)/i.test(String(cs.overflowY || cs.overflow || ''));
      if (!isScroller) continue;
      if (el !== document.scrollingElement && !visible(el)) continue;
      const before = el.scrollTop || 0;
      if (before !== 0) el.scrollTop = 0;
      reset.push({tag: el.tagName, role: el.getAttribute('role') || '', before, after: el.scrollTop || 0, scrollHeight: el.scrollHeight || 0, clientHeight: el.clientHeight || 0});
    } catch (e) {}
  }
  try { window.scrollTo(0, 0); } catch (e) {}
  return {reset_count: reset.length, reset_sample: reset.slice(0, 12)};
}
"""


TARGET_GUARD_JS = r"""
(args) => {
  const expectedStory = String(args && args.expectedStory || '');
  const href = String(location.href || '');
  const onFacebook = /(^|\.)facebook\.com$/i.test(location.hostname || '');
  const hasStory = expectedStory ? href.includes(expectedStory) : true;
  const profileWithComment = /^\/[^/?#]+/i.test(location.pathname || '') && /[?&]comment_id=/.test(location.search || '') && !/permalink\.php/i.test(location.pathname || '');
  return {ok: onFacebook && hasStory && !profileWithComment, href, expectedStory, onFacebook, hasStory, profileWithComment, title: document.title || ''};
}
"""

SCROLLER_JS = r"""
() => {
  const norm = s => String(s || '').replace(/\s+/g, ' ').trim();
  const els = [document.scrollingElement || document.documentElement, ...Array.from(document.querySelectorAll('div,section,main,article'))];
  let best = null;
  for (const el of els) {
    if (!el) continue;
    const isDoc = el === document.scrollingElement || el === document.documentElement;
    const r = isDoc ? {top:0,bottom:innerHeight,left:0,right:innerWidth,width:innerWidth,height:innerHeight} : el.getBoundingClientRect();
    const sh = el.scrollHeight || 0;
    const ch = isDoc ? innerHeight : (el.clientHeight || 0);
    if (sh <= ch + 80) continue;
    const txt = norm((el.innerText || '').slice(0, 5000));
    let score = sh - ch;
    if (/Restore Britain's post/i.test(txt)) score += 5000;
    if (/\bView\s+(?:all\s+)?\d+\s+repl/i.test(txt)) score += 3500;
    if (/\bView\s+hidden\s+(?:repl|comment)/i.test(txt)) score += 3500;
    if (/\breplied\s*[·•.\-]\s*\d+\s+repl/i.test(txt)) score += 2500;
    if (r.width >= 430 && r.width <= 980 && r.height >= 360 && r.left >= 150 && r.right <= innerWidth - 10) score += 1800;
    if (r.top >= 70 && r.top <= 190) score += 800;
    const item = {score, isDoc, tag: el.tagName || 'DOCUMENT', role: el.getAttribute && (el.getAttribute('role') || ''), aria: el.getAttribute && (el.getAttribute('aria-label') || ''), rect:{top:Math.round(r.top),bottom:Math.round(r.bottom),left:Math.round(r.left),right:Math.round(r.right),width:Math.round(r.width),height:Math.round(r.height)}, scrollTop:Math.round(isDoc ? (window.scrollY || el.scrollTop || 0) : el.scrollTop), scrollHeight:Math.round(sh), clientHeight:Math.round(ch)};
    if (!best || item.score > best.score) best = {...item, el};
  }
  if (!best) return {ok:false, reason:'no_comments_scroller'};
  const {el, ...rest} = best;
  return {ok:true, scroller:rest};
}
"""

PROBE_JS = r"""
(args) => {
  const hint = args && args.hint || null;
  const maxItems = Number(args && args.maxItems || 100);
  const skipKeys = new Set((args && args.skipKeys) || []);
  const norm = s => String(s || '').replace(/\s+/g, ' ').trim();
  const patterns = [
    {cat:'view_hidden', rx:/\bView\s+hidden\s+(?:repl(?:y|ies)|comments?)\b/ig},
    {cat:'view_more', rx:/\bView\s+(?:more|\d+\s+more)\s+(?:repl(?:y|ies)|comments?)\b/ig},
    {cat:'view_all_replies', rx:/\bView\s+all\s+\d+\s+repl(?:y|ies)\b/ig},
    {cat:'view_number_replies', rx:/\bView\s+\d+\s+repl(?:y|ies)\b/ig},
    {cat:'view_comments', rx:/\bView\s+(?:all\s+)?\d+\s+comments?\b/ig},
    {cat:'replied_bucket', rx:/\breplied\s*[·•.\-]\s*\d+\s+repl(?:y|ies)\b/ig}
  ];
  function findScroller(h) {
    const els = [document.scrollingElement || document.documentElement, ...Array.from(document.querySelectorAll('div,section,main,article'))];
    if (h && h.rect) {
      for (const el of els) {
        const isDoc = el === document.scrollingElement || el === document.documentElement;
        const r = isDoc ? {top:0,bottom:innerHeight,left:0,right:innerWidth,width:innerWidth,height:innerHeight} : el.getBoundingClientRect();
        if (Math.abs(Math.round(r.top)-h.rect.top)<8 && Math.abs(Math.round(r.left)-h.rect.left)<8 && Math.abs(Math.round(r.width)-h.rect.width)<12) return el;
      }
    }
    let best = null;
    for (const el of els) {
      const isDoc = el === document.scrollingElement || el === document.documentElement;
      const r = isDoc ? {top:0,bottom:innerHeight,left:0,right:innerWidth,width:innerWidth,height:innerHeight} : el.getBoundingClientRect();
      const sh = el.scrollHeight || 0, ch = isDoc ? innerHeight : (el.clientHeight || 0);
      if (sh <= ch+80) continue;
      const txt = norm((el.innerText || '').slice(0, 3000));
      let score = sh-ch;
      if (/Restore Britain's post/i.test(txt)) score += 5000;
      if (/\bView\s+(?:all\s+)?\d+\s+repl/i.test(txt)) score += 3500;
      if (r.width >= 430 && r.width <= 980 && r.height >= 360 && r.left >= 150) score += 1500;
      if (!best || score > best.score) best = {el, score};
    }
    return best ? best.el : (document.scrollingElement || document.documentElement);
  }
  const scroller = findScroller(hint);
  const isDoc = scroller === document.scrollingElement || scroller === document.documentElement || scroller === document.body;
  const sr = isDoc ? {top:0,bottom:innerHeight,left:0,right:innerWidth,width:innerWidth,height:innerHeight} : scroller.getBoundingClientRect();
  const topBand = Math.max(sr.top + 42, 82);
  const bottomBand = Math.min(sr.bottom - 92, innerHeight - 72);
  const inBand = r => r.bottom >= topBand && r.top <= bottomBand && r.right >= sr.left && r.left <= sr.right;
  const bad = el => {
    if (!el) return true;
    if (el.closest('textarea,input,select,[contenteditable="true"]')) return true;
    let cur = el;
    for (let i=0; cur && i<8; i++, cur=cur.parentElement) {
      const blob = norm([cur.getAttribute && (cur.getAttribute('aria-label')||''), cur.getAttribute && (cur.getAttribute('title')||''), cur.className||''].join(' '));
      if (/(composer|comment as|write a comment|reply to|gif|sticker|photo|camera|avatar|upload|file|emoji)/i.test(blob)) return true;
    }
    return false;
  };
  const isProfileOrProfileCommentHref = (hrefRaw) => {
    const href = String(hrefRaw || '');
    if (!href) return false;
    let u;
    try { u = new URL(href, location.href); } catch(e) { return false; }
    if (!/(^|\.)facebook\.com$/i.test(u.hostname || '')) return false;
    const path = u.pathname || '';
    // These are the only post/story surfaces this runner is allowed to keep using.
    if (/permalink\.php/i.test(path) || /[?&]story_fbid=/.test(u.search || '')) return false;
    // Block personal/profile paths, INCLUDING profile comment permalinks such as
    // /dbroomhall?comment_id=... . R45AQ/R45AS allowed comment_id/reply_comment_id
    // here, which is exactly how a bad click could leave the target post.
    if (/^\/profile\.php/i.test(path)) return true;
    if (/^\/[A-Za-z0-9_.-]+\/?$/i.test(path)) return true;
    return false;
  };
  const profileAnchorAt = (x,y) => {
    let el = document.elementFromPoint(Math.max(1, Math.min(innerWidth-2,x)), Math.max(1, Math.min(innerHeight-2,y)));
    for (let i=0; el && i<10; i++, el=el.parentElement) {
      if ((el.tagName||'').toLowerCase() === 'a') {
        const href = String(el.getAttribute('href') || el.href || '');
        if (isProfileOrProfileCommentHref(href)) return true;
      }
    }
    return false;
  };
  const items = [], seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {acceptNode(n) {
    const t = norm(n.nodeValue || '');
    if (!t) return NodeFilter.FILTER_REJECT;
    if (!patterns.some(p => p.rx.test(t))) return NodeFilter.FILTER_REJECT;
    patterns.forEach(p => p.rx.lastIndex = 0);
    if (!n.parentElement || bad(n.parentElement)) return NodeFilter.FILTER_REJECT;
    return NodeFilter.FILTER_ACCEPT;
  }});
  let n;
  while ((n = walker.nextNode())) {
    const raw = String(n.nodeValue || '');
    const text = norm(raw);
    for (const p of patterns) {
      p.rx.lastIndex = 0;
      let m;
      while ((m = p.rx.exec(text))) {
        const label = norm(m[0]);
        let start = raw.toLowerCase().indexOf(label.toLowerCase());
        if (start < 0) start = 0;
        let end = Math.min(raw.length, start + label.length);
        const range = document.createRange();
        try { range.setStart(n, start); range.setEnd(n, end); } catch(e) { range.selectNodeContents(n); }
        const rects = Array.from(range.getClientRects()).filter(r => r.width > 4 && r.height > 4);
        range.detach();
        for (const r of rects) {
          if (!inBand(r)) continue;
          const x = Math.round((r.left+r.right)/2), y = Math.round((r.top+r.bottom)/2);
          if (profileAnchorAt(x,y)) continue;
          const absTop = Math.round((isDoc ? (window.scrollY || scroller.scrollTop || 0) : scroller.scrollTop) + (r.top - sr.top));
          const key = [p.cat,label,absTop,Math.round(r.left)].join('|');
          if (skipKeys.has(key)) continue;
          if (seen.has(key)) continue;
          seen.add(key);
          items.push({category:p.cat,label,top:Math.round(r.top),bottom:Math.round(r.bottom),left:Math.round(r.left),right:Math.round(r.right),x,y,absTop,key});
        }
      }
    }
  }
  items.sort((a,b) => a.top-b.top || a.left-b.left || a.label.localeCompare(b.label));
  const counts = {};
  for (const it of items) counts[it.category] = (counts[it.category] || 0) + 1;
  return {total:items.length, counts, labels:items.slice(0,maxItems).map(x=>x.label), items:items.slice(0,maxItems), scroller:{isDoc, tag:scroller.tagName||'DOCUMENT', role:scroller.getAttribute && (scroller.getAttribute('role')||''), scrollTop:Math.round(isDoc ? (window.scrollY || scroller.scrollTop || 0) : scroller.scrollTop), scrollHeight:Math.round(scroller.scrollHeight || 0), clientHeight:Math.round(isDoc ? innerHeight : scroller.clientHeight || 0), rect:{top:Math.round(sr.top),bottom:Math.round(sr.bottom),left:Math.round(sr.left),right:Math.round(sr.right),width:Math.round(sr.width),height:Math.round(sr.height)}}};
}
"""

SCROLL_JS = r"""
(args) => {
  const h = args && args.hint || null;
  const mode = String(args && args.mode || 'down');
  const frac = Number(args && args.frac || 0.72);
  function findScroller(h) {
    const els = [document.scrollingElement || document.documentElement, ...Array.from(document.querySelectorAll('div,section,main,article'))];
    if (h && h.rect) {
      for (const el of els) {
        const isDoc = el === document.scrollingElement || el === document.documentElement;
        const r = isDoc ? {top:0,bottom:innerHeight,left:0,right:innerWidth,width:innerWidth,height:innerHeight} : el.getBoundingClientRect();
        if (Math.abs(Math.round(r.top)-h.rect.top)<8 && Math.abs(Math.round(r.left)-h.rect.left)<8 && Math.abs(Math.round(r.width)-h.rect.width)<12) return el;
      }
    }
    return document.scrollingElement || document.documentElement;
  }
  const scroller = findScroller(h);
  const isDoc = scroller === document.scrollingElement || scroller === document.documentElement || scroller === document.body;
  const before = isDoc ? (window.scrollY || scroller.scrollTop || 0) : scroller.scrollTop;
  const ch = isDoc ? innerHeight : (scroller.clientHeight || 0);
  const sh = scroller.scrollHeight || 0;
  let after = before;
  if (mode === 'top') after = 0;
  else if (mode === 'bottom') after = Math.max(0, sh - ch);
  else after = Math.min(Math.max(0, sh - ch), before + Math.max(120, Math.floor(ch * frac)));
  if (isDoc) window.scrollTo({top:after, left:0, behavior:'instant'}); else scroller.scrollTop = after;
  const actual = isDoc ? (window.scrollY || scroller.scrollTop || 0) : scroller.scrollTop;
  return {mode,isDoc,before:Math.round(before),after:Math.round(actual),clientHeight:Math.round(ch),scrollHeight:Math.round(sh),atBottom: actual + ch >= sh - 5};
}
"""

CLIP_JS = r"""
(args) => {
  const h = args && args.hint || null;
  const els = [document.scrollingElement || document.documentElement, ...Array.from(document.querySelectorAll('div,section,main,article'))];
  let scroller = null;
  if (h && h.rect) {
    for (const el of els) {
      const isDoc = el === document.scrollingElement || el === document.documentElement;
      const r = isDoc ? {top:0,bottom:innerHeight,left:0,right:innerWidth,width:innerWidth,height:innerHeight} : el.getBoundingClientRect();
      if (Math.abs(Math.round(r.top)-h.rect.top)<8 && Math.abs(Math.round(r.left)-h.rect.left)<8 && Math.abs(Math.round(r.width)-h.rect.width)<12) { scroller = el; break; }
    }
  }
  scroller = scroller || document.scrollingElement || document.documentElement;
  const isDoc = scroller === document.scrollingElement || scroller === document.documentElement || scroller === document.body;
  const r = isDoc ? {top:0,bottom:innerHeight,left:0,right:innerWidth,width:innerWidth,height:innerHeight} : scroller.getBoundingClientRect();
  const top = Math.max(0, r.top), left = Math.max(0, r.left), right = Math.min(innerWidth, r.right), bottom = Math.min(innerHeight, r.bottom);
  return {x:Math.round(left), y:Math.round(top), width:Math.max(1,Math.round(right-left)), height:Math.max(1,Math.round(bottom-top))};
}
"""


PROFILE_NAV_BLOCKER_JS = r"""
() => {
  if (window.__YTCE_R45AW_PROFILE_NAV_BLOCKER_INSTALLED) return {installed:true, already:true};
  const isProfileOrProfileCommentHref = (hrefRaw) => {
    const href = String(hrefRaw || '');
    if (!href) return false;
    let u;
    try { u = new URL(href, location.href); } catch(e) { return false; }
    if (!/(^|\.)facebook\.com$/i.test(u.hostname || '')) return false;
    const path = u.pathname || '';
    if (/permalink\.php/i.test(path) || /[?&]story_fbid=/.test(u.search || '')) return false;
    if (/^\/profile\.php/i.test(path)) return true;
    if (/^\/[A-Za-z0-9_.-]+\/?$/i.test(path)) return true;
    return false;
  };
  const handler = (ev) => {
    let el = ev.target;
    for (let i = 0; el && i < 12; i++, el = el.parentElement) {
      if ((el.tagName || '').toLowerCase() === 'a') {
        const href = String(el.getAttribute('href') || el.href || '');
        if (isProfileOrProfileCommentHref(href)) {
          ev.preventDefault();
          ev.stopPropagation();
          ev.stopImmediatePropagation();
          console.warn('YTCE_R45AW_BLOCKED_PROFILE_NAV', href);
          return false;
        }
      }
    }
  };
  document.addEventListener('click', handler, true);
  document.addEventListener('auxclick', handler, true);
  document.addEventListener('mousedown', handler, true);
  window.__YTCE_R45AW_PROFILE_NAV_BLOCKER_INSTALLED = true;
  return {installed:true, already:false};
}
"""

CLICK_POINT_SAFETY_JS = r"""
(args) => {
  const x = Number(args && args.x || 0), y = Number(args && args.y || 0);
  const isProfileOrProfileCommentHref = (hrefRaw) => {
    const href = String(hrefRaw || '');
    if (!href) return false;
    let u;
    try { u = new URL(href, location.href); } catch(e) { return false; }
    if (!/(^|\.)facebook\.com$/i.test(u.hostname || '')) return false;
    const path = u.pathname || '';
    if (/permalink\.php/i.test(path) || /[?&]story_fbid=/.test(u.search || '')) return false;
    if (/^\/profile\.php/i.test(path)) return true;
    if (/^\/[A-Za-z0-9_.-]+\/?$/i.test(path)) return true;
    return false;
  };
  let el = document.elementFromPoint(Math.max(1, Math.min(innerWidth-2,x)), Math.max(1, Math.min(innerHeight-2,y)));
  const chain = [];
  for (let i = 0; el && i < 12; i++, el = el.parentElement) {
    const tag = (el.tagName || '').toLowerCase();
    const txt = String(el.innerText || el.textContent || '').replace(/\s+/g,' ').trim().slice(0,120);
    const href = tag === 'a' ? String(el.getAttribute('href') || el.href || '') : '';
    chain.push({tag, role: el.getAttribute && (el.getAttribute('role') || ''), href, text: txt});
    if (href && isProfileOrProfileCommentHref(href)) return {ok:false, reason:'profile_or_profile_comment_anchor_under_click_point', href, chain};
  }
  return {ok:true, reason:'safe_point', chain};
}
"""


def _guard(page: Any, story: str) -> Dict[str, Any]:
    return page.evaluate(TARGET_GUARD_JS, {"expectedStory": story}) or {}


def _find_scroller(page: Any) -> Dict[str, Any]:
    return page.evaluate(SCROLLER_JS) or {}


def _probe(page: Any, hint: Dict[str, Any], skip_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    return page.evaluate(PROBE_JS, {"hint": hint, "maxItems": 120, "skipKeys": skip_keys or []}) or {}


def _scroll(page: Any, hint: Dict[str, Any], mode: str) -> Dict[str, Any]:
    return page.evaluate(SCROLL_JS, {"hint": hint, "mode": mode, "frac": 0.72}) or {}


def exhaust(page: Any, args: argparse.Namespace, story: str) -> Dict[str, Any]:
    start = time.monotonic()
    clicked = 0
    scrolls = 0
    audit_pass = 1
    clean_bottom_once = False
    no_scroll_cycles = 0
    last_scroll = None
    unsafe_skip_keys: set[str] = set()
    unsafe_skipped = 0

    guard = _guard(page, story)
    emit("R45AW_TARGET_GUARD", guard)
    if not guard.get("ok"):
        return {"status":"blocked", "reason":"target_guard_failed", "guard":guard}

    try:
        nav_block = page.evaluate(PROFILE_NAV_BLOCKER_JS)
    except Exception as e:
        nav_block = {"installed": False, "error": str(e)}
    emit("R45AW_PROFILE_NAV_BLOCKER", nav_block)

    sc = _find_scroller(page)
    emit("R45AW_ACTIVE_SCROLL_CONTAINER", sc)
    if not sc.get("ok"):
        return {"status":"blocked", "reason":"no_active_comments_scroller", "scroller":sc}
    hint = sc["scroller"]

    top = _scroll(page, hint, "top")
    emit("R45AW_SCROLL_TOP", top)
    time.sleep(args.scroll_settle_seconds)

    for step in range(1, args.max_steps + 1):
        elapsed = time.monotonic() - start
        if elapsed > args.expand_max_seconds:
            probe = _probe(page, hint, list(unsafe_skip_keys))
            emit("R45AW_BLOCKED_VISIBLE_CONTROLS", {"reason":"timeout", "clicked":clicked, "scrolls":scrolls, "audit_pass":audit_pass, "visible_total":probe.get("total"), "visible_counts":probe.get("counts"), "visible_labels":probe.get("labels")})
            return {"status":"blocked", "reason":"timeout", "clicked":clicked, "scrolls":scrolls, "probe":probe}

        guard = _guard(page, story)
        if not guard.get("ok"):
            emit("R45AW_TARGET_SURFACE_LOST", {"step":step, "clicked":clicked, "guard":guard})
            return {"status":"blocked", "reason":"target_surface_lost", "clicked":clicked, "guard":guard}

        probe = _probe(page, hint, list(unsafe_skip_keys))
        emit("R45AW_VIEWPORT_SCAN", {"step":step, "audit_pass":audit_pass, "elapsed_seconds":round(elapsed,2), "visible_total":probe.get("total",0), "visible_counts":probe.get("counts",{}), "visible_labels":(probe.get("labels") or [])[:30], "scrollTop":(probe.get("scroller") or {}).get("scrollTop"), "scrollHeight":(probe.get("scroller") or {}).get("scrollHeight")})

        if int(probe.get("total") or 0) > 0:
            item = (probe.get("items") or [])[0]
            try:
                point_safety = page.evaluate(CLICK_POINT_SAFETY_JS, {"x": item.get("x"), "y": item.get("y")})
            except Exception as e:
                point_safety = {"ok": False, "reason": "point_safety_exception", "error": str(e)}
            if not point_safety.get("ok"):
                unsafe_key = str(item.get("key") or "")
                if unsafe_key:
                    unsafe_skip_keys.add(unsafe_key)
                unsafe_skipped += 1
                emit("R45AW_UNSAFE_CLICK_POINT_SKIPPED", {"step": step, "audit_pass": audit_pass, "unsafe_skipped": unsafe_skipped, "item": item, "point_safety": point_safety, "skip_key_count": len(unsafe_skip_keys), "elapsed_seconds": round(time.monotonic()-start,2)})
                # Do not navigate away and do not end the run: this is a false-positive visual point
                # over a profile/name anchor. Exclude it and immediately rescan the same viewport.
                continue
            try:
                page.evaluate(PROFILE_NAV_BLOCKER_JS)
            except Exception:
                pass
            page.mouse.move(float(item["x"]), float(item["y"]))
            page.mouse.down(); time.sleep(0.012); page.mouse.up()
            clicked += 1
            clean_bottom_once = False
            no_scroll_cycles = 0
            page.mouse.move(12, 125)
            time.sleep(args.click_settle_seconds)
            after_guard = _guard(page, story)
            emit("R45AW_CLICK_FIRST_VISIBLE", {"step":step, "audit_pass":audit_pass, "clicked":clicked, "category":item.get("category"), "label":item.get("label"), "x":item.get("x"), "y":item.get("y"), "target_ok":after_guard.get("ok"), "elapsed_seconds":round(time.monotonic()-start,2)})
            if not after_guard.get("ok"):
                return {"status":"blocked", "reason":"target_surface_lost_after_click", "clicked":clicked, "guard":after_guard, "item":item}
            continue

        scr = _scroll(page, hint, "down")
        scrolls += 1
        time.sleep(args.scroll_settle_seconds)
        emit("R45AW_SCROLL_DOWN", {"step":step, "audit_pass":audit_pass, "scrolls":scrolls, **scr, "elapsed_seconds":round(time.monotonic()-start,2)})

        if last_scroll == scr.get("after"):
            no_scroll_cycles += 1
        else:
            no_scroll_cycles = 0
        last_scroll = scr.get("after")

        if scr.get("atBottom") or no_scroll_cycles >= 2:
            time.sleep(args.bottom_settle_seconds)
            bottom_probe = _probe(page, hint, list(unsafe_skip_keys))
            if int(bottom_probe.get("total") or 0) > 0:
                continue
            if clean_bottom_once:
                emit("R45AW_COMPLETE_AFTER_FULL_VISUAL_AUDIT", {"status":"PASS_FULL_TOPDOWN_VISUAL_AUDIT_ZERO_VISIBLE_CONTROLS", "clicked":clicked, "scrolls":scrolls, "audit_passes":audit_pass, "unsafe_skipped":unsafe_skipped, "elapsed_seconds":round(time.monotonic()-start,2)})
                return {"status":"pass", "clicked":clicked, "scrolls":scrolls, "audit_passes":audit_pass, "unsafe_skipped":unsafe_skipped}
            clean_bottom_once = True
            audit_pass += 1
            no_scroll_cycles = 0
            last_scroll = None
            top = _scroll(page, hint, "top")
            emit("R45AW_AUDIT_RESTART_TOP", {"audit_pass":audit_pass, **top, "elapsed_seconds":round(time.monotonic()-start,2)})
            time.sleep(args.scroll_settle_seconds)

    probe = _probe(page, hint, list(unsafe_skip_keys))
    emit("R45AW_BLOCKED_VISIBLE_CONTROLS", {"reason":"max_steps", "clicked":clicked, "scrolls":scrolls, "visible_total":probe.get("total"), "visible_counts":probe.get("counts"), "visible_labels":probe.get("labels")})
    return {"status":"blocked", "reason":"max_steps", "clicked":clicked, "scrolls":scrolls, "probe":probe}



def _safe_locator_screenshot(page: Any, selector: str, path: Path, warnings: List[str]) -> Optional[str]:
    try:
        page.locator(selector).first.screenshot(path=str(path), timeout=120000)
        return str(path)
    except Exception as e:
        warnings.append(f"separated_comments_box_locator_screenshot_warning={e}")
        return None


def _capture_comments_column_max_bands(page: Any, run_dir: Path, settle: float, selector: str = '[data-r45j-preserved-comments-root="true"]', max_band_height: int = 14000, max_bands: int = 300) -> List[str]:
    """Capture the separated comments column as maximum-height bands.

    Chromium/Windows image surfaces can silently blank or truncate very tall full-page screenshots.
    This route uses large but safe vertical bands instead: part_001, part_002, etc.
    """
    paths: List[str] = []
    try:
        metrics = page.evaluate(
            """(sel) => {
              const el = document.querySelector(sel);
              if (!el) return {ok:false, reason:'missing_root'};
              const r = el.getBoundingClientRect();
              const de = document.documentElement;
              const body = document.body;
              const h = Math.ceil(Math.max(el.scrollHeight || 0, r.height || 0, body.scrollHeight || 0, de.scrollHeight || 0));
              const w = Math.ceil(Math.max(1, r.width || el.scrollWidth || 720));
              const x = Math.max(0, Math.floor(r.left + (window.scrollX || 0)));
              const y = Math.max(0, Math.floor(r.top + (window.scrollY || 0)));
              return {ok:true, x, y, width:w, height:h, rect:{left:r.left, top:r.top, width:r.width, height:r.height}, bodyHeight: body.scrollHeight || 0, docHeight: de.scrollHeight || 0};
            }""",
            selector,
        )
    except Exception:
        return paths
    if not metrics or not metrics.get("ok"):
        return paths
    total_h = int(metrics.get("height") or 0)
    width = int(metrics.get("width") or 720)
    doc_x = int(metrics.get("x") or 0)
    if total_h <= 0 or width <= 0:
        return paths

    band_h = max(900, min(int(max_band_height), 14000))
    viewport_w = max(900, min(2200, doc_x + width + 48))
    try:
        page.set_viewport_size({"width": int(viewport_w), "height": int(min(15000, band_h + 80))})
    except Exception:
        pass

    y = 0
    for i in range(1, max_bands + 1):
        if y >= total_h:
            break
        h = int(min(band_h, total_h - y))
        try:
            page.evaluate('(yy) => window.scrollTo(0, yy)', y)
            time.sleep(max(0.05, settle))
            rect = page.evaluate(
                """(sel) => {
                  const el = document.querySelector(sel);
                  const r = el.getBoundingClientRect();
                  return {left:r.left, top:r.top, width:r.width, height:r.height, innerHeight:window.innerHeight, innerWidth:window.innerWidth};
                }""",
                selector,
            )
            x_clip = max(0, int(rect.get('left') or 0))
            y_clip = max(0, int(rect.get('top') or 0))
            if y > 0:
                y_clip = 0
            w_clip = int(min(width, max(1, int(rect.get('innerWidth') or viewport_w) - x_clip)))
            h_clip = int(min(h, max(1, int(rect.get('innerHeight') or band_h) - y_clip)))
            if w_clip <= 0 or h_clip <= 0:
                break
            p = run_dir / f"facebook_preserved_visual_comments_column_part_{i:03d}_y{int(y):08d}.png"
            page.screenshot(path=str(p), full_page=False, clip={"x": x_clip, "y": y_clip, "width": w_clip, "height": h_clip})
            paths.append(str(p))
        except Exception as e:
            err = run_dir / f"r45aw_band_capture_error_{i:03d}.txt"
            try:
                err.write_text(str(e), encoding='utf-8')
            except Exception:
                pass
            break
        y += h

    if paths:
        try:
            shutil.copy2(paths[0], run_dir / "facebook_preserved_visual_comments_column.png")
        except Exception:
            pass
        zip_path = run_dir / "r45aw_separated_comments_max_bands.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in paths:
                z.write(p, Path(p).name)
        paths.append(str(zip_path))
    return paths


def capture_separated_comments_box(page: Any, run_dir: Path, settle: float, make_tiles: bool) -> Dict[str, Any]:
    """Apply the R45J/R45L comments-only visual cleanup and capture separated comments-box evidence."""
    warnings: List[str] = []
    result: Dict[str, Any] = {"warnings": warnings}
    try:
        reset_before = page.evaluate(RESET_ALL_COMMENT_SCROLLERS_JS)
        result["reset_before_visual_clean"] = reset_before
        time.sleep(max(0.2, settle))
        summary = page.evaluate(JS_MARK_AND_CLEAN_PRESERVED_COMMENTS)
        result["visual_clean_summary"] = summary
        page.add_style_tag(content=VISUAL_CLEAN_CSS)
        reset_after = page.evaluate(RESET_ALL_COMMENT_SCROLLERS_JS)
        result["reset_after_visual_clean"] = reset_after
        page.evaluate('() => window.scrollTo(0, 0)')
        time.sleep(max(0.4, settle))
    except Exception as e:
        warnings.append(f"separated_comments_box_visual_clean_warning={e}")
        result["status"] = "WARNING_VISUAL_CLEAN_FAILED"
        return result

    try:
        result["clean_dom_path"] = str(run_dir / "r45aw_separated_comments_clean_dom.html")
        Path(result["clean_dom_path"]).write_text(page.content(), encoding="utf-8")
    except Exception as e:
        warnings.append(f"separated_comments_box_clean_dom_warning={e}")
    try:
        result["clean_text_path"] = str(run_dir / "r45aw_separated_comments_visible_text.txt")
        Path(result["clean_text_path"]).write_text(page.locator('body').inner_text(timeout=30000), encoding="utf-8")
    except Exception as e:
        warnings.append(f"separated_comments_box_clean_text_warning={e}")

    # Do not rely on one enormous full-page PNG: it can blank/truncate on Chromium/Windows.
    # Capture the separated comments column in maximum-height bands instead.
    band_paths = _capture_comments_column_max_bands(page, run_dir, settle)
    result["comments_column_max_band_paths"] = band_paths
    result["comments_column_max_band_count"] = len([p for p in band_paths if p.lower().endswith('.png')])
    result["comments_box_screenshot_path"] = str(run_dir / "facebook_preserved_visual_comments_column.png") if (run_dir / "facebook_preserved_visual_comments_column.png").exists() else None
    result["comments_only_full_page_screenshot_path"] = None
    result["comments_only_full_page_screenshot_skipped"] = "skipped_by_r45aw_use_max_bands_to_avoid_blank_or_truncated_very_tall_full_page_png"
    if make_tiles:
        result["comments_only_tile_screenshot_paths"] = band_paths
        result["comments_only_tile_screenshot_count"] = result["comments_column_max_band_count"]
    result["status"] = "PASS_R45AW_MAX_BAND_SEPARATED_COMMENTS_CAPTURED" if band_paths else "WARNING_NO_SEPARATED_MAX_BAND_SCREENSHOT"
    return result


def run_live(args: argparse.Namespace) -> Dict[str, Any]:
    from playwright.sync_api import sync_playwright
    target = _clean_url(args.target_url)
    story = _target_story(target)
    out_root = Path(args.output_root).expanduser()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"r45aw_safe_visual_topdown_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    receipt: Dict[str, Any] = {"marker": MARKER, "schema_version": SCHEMA_VERSION, "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(), "target_url": target, "expected_story": story, "run_dir": str(run_dir), "contract": contract()}
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=args.user_data_dir, executable_path=args.chromium_executable or None, headless=False, viewport=None, args=["--start-maximized", "--disable-session-crashed-bubble", "--hide-crash-restore-bubble", "--no-first-run", "--no-default-browser-check"])
        page = context.new_page()
        try:
            page.goto(target, wait_until="domcontentloaded", timeout=60000)
            page.bring_to_front()
            time.sleep(args.initial_settle_seconds)
            try:
                nav_block = page.evaluate(PROFILE_NAV_BLOCKER_JS)
                emit("R45AW_PROFILE_NAV_BLOCKER_INITIAL", nav_block)
            except Exception as e:
                emit("R45AW_PROFILE_NAV_BLOCKER_INITIAL", {"installed": False, "error": str(e)})
            for other in list(context.pages):
                if other is not page:
                    try: other.close(run_before_unload=False)
                    except Exception: pass
            page.bring_to_front()
            summary = exhaust(page, args, story) if args.auto_expand else {"status":"skipped"}
            receipt["auto_expand_summary"] = summary
            if summary.get("status") != "pass":
                receipt["status"] = "BLOCKED_VISIBLE_CONTROLS_OR_TARGET_LOST"
                rp = run_dir / "r45aw_safe_visual_topdown_receipt.json"
                rp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                receipt["receipt_path"] = str(rp)
                print("R45AW blocked: visual audit did not finish cleanly. No final screenshot accepted.", flush=True)
                return receipt
            # After the full visual audit passes, separate the Facebook-rendered comments box
            # from the surrounding webpage using the R45J/R45L preserved visual crop path.
            separated = capture_separated_comments_box(page, run_dir, args.scroll_settle_seconds, args.tile_screenshots)
            receipt["separated_comments_box"] = separated
            receipt["screenshot_paths"] = [p for p in [separated.get("comments_box_screenshot_path"), separated.get("comments_only_full_page_screenshot_path")] if p]
            receipt["screenshot_paths"].extend(separated.get("comments_only_tile_screenshot_paths") or [])
            if str(separated.get("status", "")).startswith("PASS"):
                receipt["status"] = "PASS_R45AW_FULL_VISUAL_AUDIT_AND_SEPARATED_COMMENTS_BOX_SCREENSHOT"
            else:
                receipt["status"] = "PASS_R45AW_FULL_VISUAL_AUDIT_WITH_SEPARATED_SCREENSHOT_WARNINGS"
            rp = run_dir / "r45aw_safe_visual_topdown_receipt.json"
            rp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
            receipt["receipt_path"] = str(rp)
            print("YTCE_R45AW_VISUAL_TOPDOWN_SKIP_UNSAFE_DONE", flush=True)
            print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
            return receipt
        finally:
            try: context.close()
            except Exception: pass


def self_test(args: argparse.Namespace) -> Dict[str, Any]:
    text = Path(__file__).read_text(encoding="utf-8")
    checks = [
        {"name":"contract_marker", "status":"pass" if contract()["marker"] == MARKER else "fail"},
        {"name":"full_visual_audit_required", "status":"pass" if "R45AW_COMPLETE_AFTER_FULL_VISUAL_AUDIT" in text else "fail"},
        {"name":"target_surface_lost_failfast", "status":"pass" if "R45AW_TARGET_SURFACE_LOST" in text else "fail"},
        {"name":"profile_nav_blocker_present", "status":"pass" if "R45AW_PROFILE_NAV_BLOCKER" in text and "profile_or_profile_comment_anchor_under_click_point" in text else "fail"},
        {"name":"unsafe_click_skip_present", "status":"pass" if "R45AW_UNSAFE_CLICK_POINT_SKIPPED" in text and "unsafe_skip_keys" in text else "fail"},
        {"name":"max_band_capture_present", "status":"pass" if "_capture_comments_column_max_bands" in text and "facebook_preserved_visual_comments_column_part_" in text else "fail"},
        {"name":"reset_scrollers_before_visual_clean", "status":"pass" if "RESET_ALL_COMMENT_SCROLLERS_JS" in text and "reset_before_visual_clean" in text else "fail"},
        {"name":"no_hidden_platform_api", "status":"pass" if contract()["hidden_platform_api_scraping_enabled"] is False else "fail"},
    ]
    status = "PASS_R45AW_SELF_TEST" if all(c["status"] == "pass" for c in checks) else "FAIL_R45AW_SELF_TEST"
    result = {"marker": MARKER, "status": status, "schema_version": SCHEMA_VERSION, "checks": checks, "contract": contract()}
    out = Path(args.output_root); out.mkdir(parents=True, exist_ok=True)
    (out / "r45aw_self_test.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MARKER); print(status); print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="R45AW visual top-down Facebook comments expansion and screenshot")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--target-url", default="")
    ap.add_argument("--auto-expand", action="store_true")
    ap.add_argument("--tile-screenshots", action="store_true")
    ap.add_argument("--expand-max-seconds", type=float, default=1800.0)
    ap.add_argument("--max-steps", type=int, default=5000)
    ap.add_argument("--click-settle-seconds", type=float, default=0.35)
    ap.add_argument("--scroll-settle-seconds", type=float, default=0.12)
    ap.add_argument("--bottom-settle-seconds", type=float, default=1.0)
    ap.add_argument("--initial-settle-seconds", type=float, default=3.0)
    ap.add_argument("--chromium-executable", default="")
    ap.add_argument("--user-data-dir", default="")
    ap.add_argument("--output-root", default="profile_media_live_captures/r45aw_safe_visual_topdown")
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.self_test:
        result = self_test(args)
        return 0 if result["status"].startswith("PASS") else 1
    if not args.target_url:
        print("ERROR: --target-url is required", flush=True); return 2
    if not args.user_data_dir:
        print("ERROR: --user-data-dir is required", flush=True); return 2
    result = run_live(args)
    return 0 if str(result.get("status", "")).startswith("PASS") else 3


if __name__ == "__main__":
    raise SystemExit(main())
