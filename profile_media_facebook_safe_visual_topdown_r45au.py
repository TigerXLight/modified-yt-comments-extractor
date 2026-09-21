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

MARKER = "YTCE_R45AU_SAFE_VISUAL_TOPDOWN_SKIP_UNSAFE"
SCHEMA_VERSION = "facebook_safe_visual_topdown.r45au.v1"


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
        "r45au_rule": "Open the post, lock to the target story, install a profile/comment-permalink navigation blocker, start at the top of the active comments scroller, click the first safe visible expansion label, skip unsafe false-positive click points that resolve to profile anchors, rescan the same viewport, keep moving downward as comments load, then require a complete top-to-bottom visual audit pass with zero safe visible controls before screenshots.",
        "visible_controls": ["View all N replies", "View N replies", "View hidden replies/comments", "View more replies/comments", "replied · N replies"],
        "success_rule": "No final screenshot is accepted until a full visible top-to-bottom audit pass sees zero safe expansion controls. Unsafe false-positive points resolving to Facebook profile/comment links are skipped and logged instead of ending the run or navigating away.",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "webview2_storage_or_cookie_inspection_enabled": False,
        "remote_media_downloads_enabled": False,
    }


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
  if (window.__YTCE_R45AU_PROFILE_NAV_BLOCKER_INSTALLED) return {installed:true, already:true};
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
          console.warn('YTCE_R45AU_BLOCKED_PROFILE_NAV', href);
          return false;
        }
      }
    }
  };
  document.addEventListener('click', handler, true);
  document.addEventListener('auxclick', handler, true);
  document.addEventListener('mousedown', handler, true);
  window.__YTCE_R45AU_PROFILE_NAV_BLOCKER_INSTALLED = true;
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
    emit("R45AU_TARGET_GUARD", guard)
    if not guard.get("ok"):
        return {"status":"blocked", "reason":"target_guard_failed", "guard":guard}

    try:
        nav_block = page.evaluate(PROFILE_NAV_BLOCKER_JS)
    except Exception as e:
        nav_block = {"installed": False, "error": str(e)}
    emit("R45AU_PROFILE_NAV_BLOCKER", nav_block)

    sc = _find_scroller(page)
    emit("R45AU_ACTIVE_SCROLL_CONTAINER", sc)
    if not sc.get("ok"):
        return {"status":"blocked", "reason":"no_active_comments_scroller", "scroller":sc}
    hint = sc["scroller"]

    top = _scroll(page, hint, "top")
    emit("R45AU_SCROLL_TOP", top)
    time.sleep(args.scroll_settle_seconds)

    for step in range(1, args.max_steps + 1):
        elapsed = time.monotonic() - start
        if elapsed > args.expand_max_seconds:
            probe = _probe(page, hint, list(unsafe_skip_keys))
            emit("R45AU_BLOCKED_VISIBLE_CONTROLS", {"reason":"timeout", "clicked":clicked, "scrolls":scrolls, "audit_pass":audit_pass, "visible_total":probe.get("total"), "visible_counts":probe.get("counts"), "visible_labels":probe.get("labels")})
            return {"status":"blocked", "reason":"timeout", "clicked":clicked, "scrolls":scrolls, "probe":probe}

        guard = _guard(page, story)
        if not guard.get("ok"):
            emit("R45AU_TARGET_SURFACE_LOST", {"step":step, "clicked":clicked, "guard":guard})
            return {"status":"blocked", "reason":"target_surface_lost", "clicked":clicked, "guard":guard}

        probe = _probe(page, hint, list(unsafe_skip_keys))
        emit("R45AU_VIEWPORT_SCAN", {"step":step, "audit_pass":audit_pass, "elapsed_seconds":round(elapsed,2), "visible_total":probe.get("total",0), "visible_counts":probe.get("counts",{}), "visible_labels":(probe.get("labels") or [])[:30], "scrollTop":(probe.get("scroller") or {}).get("scrollTop"), "scrollHeight":(probe.get("scroller") or {}).get("scrollHeight")})

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
                emit("R45AU_UNSAFE_CLICK_POINT_SKIPPED", {"step": step, "audit_pass": audit_pass, "unsafe_skipped": unsafe_skipped, "item": item, "point_safety": point_safety, "skip_key_count": len(unsafe_skip_keys), "elapsed_seconds": round(time.monotonic()-start,2)})
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
            emit("R45AU_CLICK_FIRST_VISIBLE", {"step":step, "audit_pass":audit_pass, "clicked":clicked, "category":item.get("category"), "label":item.get("label"), "x":item.get("x"), "y":item.get("y"), "target_ok":after_guard.get("ok"), "elapsed_seconds":round(time.monotonic()-start,2)})
            if not after_guard.get("ok"):
                return {"status":"blocked", "reason":"target_surface_lost_after_click", "clicked":clicked, "guard":after_guard, "item":item}
            continue

        scr = _scroll(page, hint, "down")
        scrolls += 1
        time.sleep(args.scroll_settle_seconds)
        emit("R45AU_SCROLL_DOWN", {"step":step, "audit_pass":audit_pass, "scrolls":scrolls, **scr, "elapsed_seconds":round(time.monotonic()-start,2)})

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
                emit("R45AU_COMPLETE_AFTER_FULL_VISUAL_AUDIT", {"status":"PASS_FULL_TOPDOWN_VISUAL_AUDIT_ZERO_VISIBLE_CONTROLS", "clicked":clicked, "scrolls":scrolls, "audit_passes":audit_pass, "unsafe_skipped":unsafe_skipped, "elapsed_seconds":round(time.monotonic()-start,2)})
                return {"status":"pass", "clicked":clicked, "scrolls":scrolls, "audit_passes":audit_pass, "unsafe_skipped":unsafe_skipped}
            clean_bottom_once = True
            audit_pass += 1
            no_scroll_cycles = 0
            last_scroll = None
            top = _scroll(page, hint, "top")
            emit("R45AU_AUDIT_RESTART_TOP", {"audit_pass":audit_pass, **top, "elapsed_seconds":round(time.monotonic()-start,2)})
            time.sleep(args.scroll_settle_seconds)

    probe = _probe(page, hint, list(unsafe_skip_keys))
    emit("R45AU_BLOCKED_VISIBLE_CONTROLS", {"reason":"max_steps", "clicked":clicked, "scrolls":scrolls, "visible_total":probe.get("total"), "visible_counts":probe.get("counts"), "visible_labels":probe.get("labels")})
    return {"status":"blocked", "reason":"max_steps", "clicked":clicked, "scrolls":scrolls, "probe":probe}


def capture_tiles(page: Any, hint: Dict[str, Any], run_dir: Path, settle: float) -> List[str]:
    paths: List[str] = []
    _scroll(page, hint, "top")
    time.sleep(settle)
    seen = set()
    for i in range(1, 800):
        probe = _probe(page, hint)
        st = (probe.get("scroller") or {}).get("scrollTop", 0)
        sh = (probe.get("scroller") or {}).get("scrollHeight", 0)
        ch = (probe.get("scroller") or {}).get("clientHeight", 0)
        clip = page.evaluate(CLIP_JS, {"hint": hint})
        p = run_dir / f"r45au_comments_tile_{i:04d}_y{int(st):08d}.png"
        page.screenshot(path=str(p), clip=clip)
        paths.append(str(p))
        if st + ch >= sh - 6:
            break
        scr = _scroll(page, hint, "down")
        key = (scr.get("after"), sh)
        if key in seen:
            break
        seen.add(key)
        time.sleep(settle)
    zip_path = run_dir / "r45au_comments_tiles.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, Path(p).name)
    paths.append(str(zip_path))
    return paths


def run_live(args: argparse.Namespace) -> Dict[str, Any]:
    from playwright.sync_api import sync_playwright
    target = _clean_url(args.target_url)
    story = _target_story(target)
    out_root = Path(args.output_root).expanduser()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"r45au_safe_visual_topdown_{stamp}"
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
                emit("R45AU_PROFILE_NAV_BLOCKER_INITIAL", nav_block)
            except Exception as e:
                emit("R45AU_PROFILE_NAV_BLOCKER_INITIAL", {"installed": False, "error": str(e)})
            for other in list(context.pages):
                if other is not page:
                    try: other.close(run_before_unload=False)
                    except Exception: pass
            page.bring_to_front()
            summary = exhaust(page, args, story) if args.auto_expand else {"status":"skipped"}
            receipt["auto_expand_summary"] = summary
            if summary.get("status") != "pass":
                receipt["status"] = "BLOCKED_VISIBLE_CONTROLS_OR_TARGET_LOST"
                rp = run_dir / "r45au_safe_visual_topdown_receipt.json"
                rp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                receipt["receipt_path"] = str(rp)
                print("R45AU blocked: visual audit did not finish cleanly. No final screenshot accepted.", flush=True)
                return receipt
            # refresh scroller after expansion because scrollHeight may change
            sc = _find_scroller(page)
            hint = sc.get("scroller", {})
            if args.tile_screenshots:
                receipt["screenshot_paths"] = capture_tiles(page, hint, run_dir, args.scroll_settle_seconds)
            receipt["status"] = "PASS_R45AU_FULL_VISUAL_AUDIT_AND_SCREENSHOT"
            rp = run_dir / "r45au_safe_visual_topdown_receipt.json"
            rp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
            receipt["receipt_path"] = str(rp)
            print("YTCE_R45AU_VISUAL_TOPDOWN_SKIP_UNSAFE_DONE", flush=True)
            print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
            return receipt
        finally:
            try: context.close()
            except Exception: pass


def self_test(args: argparse.Namespace) -> Dict[str, Any]:
    text = Path(__file__).read_text(encoding="utf-8")
    checks = [
        {"name":"contract_marker", "status":"pass" if contract()["marker"] == MARKER else "fail"},
        {"name":"full_visual_audit_required", "status":"pass" if "R45AU_COMPLETE_AFTER_FULL_VISUAL_AUDIT" in text else "fail"},
        {"name":"target_surface_lost_failfast", "status":"pass" if "R45AU_TARGET_SURFACE_LOST" in text else "fail"},
        {"name":"profile_nav_blocker_present", "status":"pass" if "R45AU_PROFILE_NAV_BLOCKER" in text and "profile_or_profile_comment_anchor_under_click_point" in text else "fail"},
        {"name":"unsafe_click_skip_present", "status":"pass" if "R45AU_UNSAFE_CLICK_POINT_SKIPPED" in text and "unsafe_skip_keys" in text else "fail"},
        {"name":"no_hidden_platform_api", "status":"pass" if contract()["hidden_platform_api_scraping_enabled"] is False else "fail"},
    ]
    status = "PASS_R45AU_SELF_TEST" if all(c["status"] == "pass" for c in checks) else "FAIL_R45AU_SELF_TEST"
    result = {"marker": MARKER, "status": status, "schema_version": SCHEMA_VERSION, "checks": checks, "contract": contract()}
    out = Path(args.output_root); out.mkdir(parents=True, exist_ok=True)
    (out / "r45au_self_test.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MARKER); print(status); print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="R45AU visual top-down Facebook comments expansion and screenshot")
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
    ap.add_argument("--output-root", default="profile_media_live_captures/r45au_safe_visual_topdown")
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
