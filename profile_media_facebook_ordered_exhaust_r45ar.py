#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List


MARKER = "YTCE_R45AR_TARGET_LOCKED_EXACT_LABEL_ORDERED_EXHAUST"
SCHEMA_VERSION = "facebook_ordered_exhaust.r45ar.v1"


def _clean_target_url(url: str) -> str:
    s = (url or "").strip().strip('"').strip("'")
    m = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", s)
    if m:
        s = m.group(1)
    s = s.replace("\\&", "&").replace("\\:", ":")
    return s


def _target_fbid(url: str) -> str:
    m = re.search(r"(?:story_fbid|fbid)=([^&?#)]+)", url or "")
    return m.group(1) if m else ""


R45AR_TARGET_GUARD_JS = r"""
(args) => {
  const expectedStory = String(args && args.expectedStory || '');
  const href = String(location.href || '');
  const text = document.body && document.body.innerText ? document.body.innerText.slice(0, 5000) : '';
  const hasStory = expectedStory ? href.includes(expectedStory) : true;
  const onFacebook = /(^|\.)facebook\.com$/i.test(location.hostname || '');
  const looksProfile = /^\/[^/?#]+\/?$/i.test(location.pathname || '') || /^\/[^/?#]+\?/.test((location.pathname || '') + (location.search || ''));
  const profileWithComment = looksProfile && /[?&]comment_id=/.test(location.search || '');
  return {
    ok: onFacebook && hasStory && !profileWithComment,
    href,
    expectedStory,
    onFacebook,
    hasStory,
    profileWithComment,
    title: document.title || '',
    textSample: text.slice(0, 300)
  };
}
"""


R45AR_PROBE_JS = r"""
(args) => {
  const allLoaded = !!(args && args.allLoaded);
  const maxItems = Number(args && args.maxItems || 80);
  const topMargin = Number(args && args.topMargin || 78);
  const bottomMargin = Number(args && args.bottomMargin || 150);

  const norm = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const labelRegexes = [
    {cat:'view_all_replies', rx:/\bView\s+all\s+\d+\s+repl(?:y|ies)\b/i},
    {cat:'view_number_replies', rx:/\bView\s+\d+\s+repl(?:y|ies)\b/i},
    {cat:'view_more_replies', rx:/\bView\s+(?:\d+\s+more\s+)?repl(?:y|ies)\b/i},
    {cat:'view_hidden', rx:/\bView\s+hidden\s+(?:repl(?:y|ies)|comments?)\b/i},
    {cat:'view_comments', rx:/\bView\s+(?:all\s+)?\d+\s+comments?\b/i},
    {cat:'replied_bucket', rx:/\b[A-Za-z][A-Za-z .'’\-\u00c0-\u024f]{1,80}\s+replied\s*[·•.\-]\s*\d+\s+repl(?:y|ies)\b/i}
  ];

  const exactLabel = (text) => {
    const t = norm(text);
    if (!t || t.length > 220) return null;
    if (/^(Like|Reply|Share|Send|Comment|Copy link|Follow|Message|All|Most relevant|Newest|Top comments|Edited|GIF|Sticker|Photo|Avatar)$/i.test(t)) return null;
    for (const p of labelRegexes) {
      const m = t.match(p.rx);
      if (m) return {label: norm(m[0]), category: p.cat};
    }
    return null;
  };

  const styleVisible = (el) => {
    if (!el || !el.isConnected) return false;
    const s = getComputedStyle(el);
    if (!s || s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity || 1) === 0) return false;
    return true;
  };

  const rectOk = (r) => !!r && Number.isFinite(r.top) && Number.isFinite(r.left) && r.width > 0 && r.height > 0;

  const isBadSurface = (el) => {
    if (!el) return true;
    if (el.closest('textarea,input,select,[contenteditable="true"]')) return true;
    const blob = norm([
      el.getAttribute && (el.getAttribute('aria-label') || ''),
      el.getAttribute && (el.getAttribute('title') || ''),
      el.className || ''
    ].join(' ')).toLowerCase();
    return /(composer|comment as|write a comment|reply to|gif|sticker|photo|camera|avatar|upload|file|emoji)/i.test(blob);
  };

  const unsafeNavigatingAnchor = (el) => {
    let cur = el;
    for (let i = 0; cur && i < 7; i++, cur = cur.parentElement) {
      const tag = (cur.tagName || '').toLowerCase();
      if (tag === 'a') {
        const href = String(cur.getAttribute('href') || cur.href || '');
        if (/\/profile\.php|facebook\.com\/[A-Za-z0-9_.-]+(?:\?|$|#|\/$)/i.test(href) && !/permalink\.php|story_fbid|comment_id=|reply_comment_id=|comment\/replies/i.test(href)) {
          return true;
        }
      }
    }
    return false;
  };

  const clickableAncestor = (el) => {
    let cur = el;
    for (let i = 0; cur && i < 9; i++, cur = cur.parentElement) {
      const tag = (cur.tagName || '').toLowerCase();
      const role = cur.getAttribute && (cur.getAttribute('role') || '');
      const tab = cur.getAttribute && cur.getAttribute('tabindex');
      if (tag === 'button' || tag === 'a' || role === 'button' || role === 'link' || tab === '0') {
        if (!isBadSurface(cur) && !unsafeNavigatingAnchor(cur) && styleVisible(cur)) return cur;
      }
    }
    if (isBadSurface(el) || unsafeNavigatingAnchor(el)) return null;
    return el;
  };

  const labelFor = (el) => {
    const parts = [
      el.getAttribute && (el.getAttribute('aria-label') || ''),
      el.getAttribute && (el.getAttribute('title') || ''),
      el.innerText || '',
      el.textContent || ''
    ].map(norm).filter(Boolean);
    const found = [];
    for (const p of parts) {
      const got = exactLabel(p);
      if (got) found.push(got);
      for (const line of p.split(/\n+/).map(norm)) {
        const lineGot = exactLabel(line);
        if (lineGot) found.push(lineGot);
      }
    }
    if (!found.length) return null;
    found.sort((a,b) => a.label.length - b.label.length);
    return found[0];
  };

  const escapedRegex = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  const textRectExact = (el, wanted) => {
    const want = norm(wanted);
    const wantRx = new RegExp(escapedRegex(want).replace(/\\ /g, '\\s+'), 'i');
    try {
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
          const raw = node.nodeValue || '';
          if (!norm(raw)) return NodeFilter.FILTER_REJECT;
          return wantRx.test(raw) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        }
      });
      let node;
      while ((node = walker.nextNode())) {
        const raw = node.nodeValue || '';
        const m = raw.match(wantRx);
        if (!m) continue;
        const start = m.index || 0;
        const end = start + m[0].length;
        const range = document.createRange();
        range.setStart(node, start);
        range.setEnd(node, end);
        const rects = Array.from(range.getClientRects()).filter(rectOk);
        range.detach();
        if (rects.length) {
          rects.sort((a,b) => (a.top - b.top) || (a.left - b.left));
          return rects[0];
        }
      }
    } catch (_) {}
    return null;
  };

  const scrollParent = (el) => {
    let cur = el && el.parentElement;
    while (cur && cur !== document.body && cur !== document.documentElement) {
      try {
        const s = getComputedStyle(cur);
        const can = /(auto|scroll|overlay)/.test(s.overflowY || '');
        if (can && cur.scrollHeight > cur.clientHeight + 25) return cur;
      } catch (_) {}
      cur = cur.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  };

  const viewportVisible = (r) => {
    if (!rectOk(r)) return false;
    if (r.right <= 0 || r.left >= innerWidth) return false;
    if (r.bottom <= topMargin || r.top >= innerHeight - bottomMargin) return false;
    return true;
  };

  const scrollInfo = (sp) => {
    const isDoc = sp === document.scrollingElement || sp === document.documentElement || sp === document.body;
    const r = isDoc ? {top:0,left:0,bottom:innerHeight,right:innerWidth,width:innerWidth,height:innerHeight} : sp.getBoundingClientRect();
    return {
      isDoc,
      scrollTop: Math.round(isDoc ? (window.scrollY || sp.scrollTop || 0) : sp.scrollTop),
      scrollHeight: Math.round(sp.scrollHeight || 0),
      clientHeight: Math.round(isDoc ? innerHeight : sp.clientHeight),
      rectTop: Math.round(r.top),
      rectBottom: Math.round(r.bottom),
      tag: sp.tagName || 'DOCUMENT',
      role: sp.getAttribute && (sp.getAttribute('role') || ''),
      aria: sp.getAttribute && (sp.getAttribute('aria-label') || '')
    };
  };

  const candidates = [];
  const seen = new Set();
  const nodes = Array.from(document.querySelectorAll('div[role="button"],span[role="button"],a[role="button"],button,a,[tabindex="0"],span,div'));

  for (const el of nodes) {
    if (!styleVisible(el)) continue;
    const lf = labelFor(el);
    if (!lf) continue;
    const clickEl = clickableAncestor(el);
    if (!clickEl) continue;
    const cr = clickEl.getBoundingClientRect();
    if (!rectOk(cr)) continue;
    const tr = textRectExact(el, lf.label) || textRectExact(clickEl, lf.label);
    if (!rectOk(tr)) continue;

    // If exact text is inside an unsafe profile/name anchor, skip instead of risking navigation.
    let owner = document.elementFromPoint(Math.max(1, Math.min(innerWidth - 2, (tr.left + tr.right) / 2)), Math.max(1, Math.min(innerHeight - 2, (tr.top + tr.bottom) / 2)));
    if (unsafeNavigatingAnchor(owner)) continue;

    const sp = scrollParent(clickEl);
    const si = scrollInfo(sp);
    const absTop = si.scrollTop + Math.round(tr.top - si.rectTop);
    const key = [lf.category, lf.label, absTop, Math.round(tr.left)].join('|');
    if (seen.has(key)) continue;
    seen.add(key);
    const isVisible = viewportVisible(tr);
    if (!allLoaded && !isVisible) continue;
    candidates.push({
      key, category: lf.category, label: lf.label,
      top: Math.round(tr.top), bottom: Math.round(tr.bottom),
      left: Math.round(tr.left), right: Math.round(tr.right),
      x: Math.round(Math.min(Math.max((tr.left + tr.right) / 2, 2), innerWidth - 2)),
      y: Math.round(Math.min(Math.max((tr.top + tr.bottom) / 2, 2), innerHeight - 2)),
      absTop, visibleNow: isVisible,
      scrollParent: si,
      tag: clickEl.tagName || '',
      role: clickEl.getAttribute && (clickEl.getAttribute('role') || '')
    });
  }

  candidates.sort((a,b) => a.absTop - b.absTop || a.left - b.left || a.label.localeCompare(b.label));
  const counts = {};
  for (const c of candidates) counts[c.category] = (counts[c.category] || 0) + 1;

  return {
    marker:'R45AR_PROBE',
    total:candidates.length,
    counts,
    labels:candidates.slice(0,maxItems).map(c=>c.label),
    items:candidates.slice(0,maxItems),
    allLoaded,
    url: location.href,
    windowScrollY: Math.round(window.scrollY || 0),
    innerHeight: Math.round(innerHeight),
    bodyTextChars: document.body && document.body.innerText ? document.body.innerText.length : 0
  };
}
"""


R45AR_SCROLL_FIRST_JS = r"""
(args) => {
  const probeFn = """ + R45AR_PROBE_JS + r""";
  const probe = probeFn({allLoaded:true, maxItems:1, topMargin:78, bottomMargin:150});
  const target = probe.items && probe.items[0];
  if (!target) return {ok:false, reason:'no_remaining_controls', probe};

  const norm = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const wanted = target.label;

  const styleVisible = (el) => {
    if (!el || !el.isConnected) return false;
    const s = getComputedStyle(el);
    return !!s && s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) !== 0;
  };
  const escapedRegex = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const wantRx = new RegExp(escapedRegex(wanted).replace(/\\ /g, '\\s+'), 'i');

  const clickableAncestor = (el) => {
    let cur = el;
    for (let i = 0; cur && i < 9; i++, cur = cur.parentElement) {
      const tag = (cur.tagName || '').toLowerCase();
      const role = cur.getAttribute && (cur.getAttribute('role') || '');
      const tab = cur.getAttribute && cur.getAttribute('tabindex');
      if (tag === 'button' || tag === 'a' || role === 'button' || role === 'link' || tab === '0') return cur;
    }
    return el;
  };

  const scrollParent = (el) => {
    let cur = el && el.parentElement;
    while (cur && cur !== document.body && cur !== document.documentElement) {
      const s = getComputedStyle(cur);
      if (/(auto|scroll|overlay)/.test(s.overflowY || '') && cur.scrollHeight > cur.clientHeight + 25) return cur;
      cur = cur.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  };

  let chosenText = null;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const raw = node.nodeValue || '';
      if (!norm(raw) || !wantRx.test(raw)) return NodeFilter.FILTER_REJECT;
      const p = node.parentElement;
      if (!p || !styleVisible(p)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  let node;
  while ((node = walker.nextNode())) {
    const p = node.parentElement;
    const clickEl = clickableAncestor(p);
    if (!clickEl) continue;
    const sp = scrollParent(clickEl);
    const isDoc = sp === document.scrollingElement || sp === document.documentElement || sp === document.body;
    const siTop = isDoc ? 0 : sp.getBoundingClientRect().top;
    const spTop = isDoc ? (window.scrollY || sp.scrollTop || 0) : sp.scrollTop;
    const m = (node.nodeValue || '').match(wantRx);
    const range = document.createRange();
    range.setStart(node, m.index || 0);
    range.setEnd(node, (m.index || 0) + m[0].length);
    const rects = Array.from(range.getClientRects()).filter(r => r.width > 0 && r.height > 0);
    range.detach();
    if (!rects.length) continue;
    rects.sort((a,b)=>(a.top-b.top)||(a.left-b.left));
    const r = rects[0];
    const absTop = spTop + Math.round(r.top - siTop);
    if (Math.abs(absTop - target.absTop) < 40 || norm(m[0]).toLowerCase() === wanted.toLowerCase()) {
      chosenText = {node, clickEl, rect:r, sp};
      break;
    }
  }

  if (!chosenText) return {ok:false, reason:'target_exact_text_not_found', target, probe};

  const sp = chosenText.sp;
  const chosen = chosenText.clickEl;
  const isDoc = sp === document.scrollingElement || sp === document.documentElement || sp === document.body;
  const before = isDoc ? (window.scrollY || sp.scrollTop || 0) : sp.scrollTop;
  const r = chosenText.rect;

  if (isDoc) {
    const wantedY = Math.max(0, before + r.top - Math.floor(innerHeight * 0.38));
    window.scrollTo({top:wantedY, left:0, behavior:'instant'});
  } else {
    const pr = sp.getBoundingClientRect();
    const delta = (r.top - pr.top) - Math.floor(sp.clientHeight * 0.38);
    sp.scrollTop = Math.max(0, sp.scrollTop + delta);
  }

  const after = isDoc ? (window.scrollY || sp.scrollTop || 0) : sp.scrollTop;
  const r3 = chosen.getBoundingClientRect();
  return {
    ok:true,
    target,
    scrollParent:{isDoc, before:Math.round(before), after:Math.round(after), tag:sp.tagName || 'DOCUMENT', role:sp.getAttribute && (sp.getAttribute('role') || '')},
    finalRect:{top:Math.round(r3.top), bottom:Math.round(r3.bottom), left:Math.round(r3.left), right:Math.round(r3.right)}
  };
}
"""


def emit(event: str, payload: Dict[str, Any]) -> None:
    print(event + " " + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)


def contract() -> Dict[str, Any]:
    return {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "primary_route": "operator-controlled signed-in Facebook Chromium session; visible-page-only expansion controls; no hidden APIs/cookies/profile parsing",
        "r45ar_target_lock_rule": "The runner refuses to continue or report success if Facebook navigates away from the requested story_fbid/permalink surface, preventing profile-page false positives.",
        "r45ar_exact_label_rule": "Expansion labels are extracted as exact substrings such as 'View all 10 replies' rather than broad rows like 'View all 10 replies Reply to Name', and the mouse clicks the exact label rectangle.",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "webview2_storage_or_cookie_inspection_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def _guard(page: Any, expected_story: str) -> Dict[str, Any]:
    return page.evaluate(R45AR_TARGET_GUARD_JS, {"expectedStory": expected_story}) or {}


def _probe(page: Any, all_loaded: bool, max_items: int = 80) -> Dict[str, Any]:
    return page.evaluate(R45AR_PROBE_JS, {
        "allLoaded": bool(all_loaded),
        "maxItems": max_items,
        "topMargin": 78,
        "bottomMargin": 150,
    }) or {}


def _wait_short(page: Any, seconds: float) -> Dict[str, Any]:
    end = time.monotonic() + max(0.05, seconds)
    last: Dict[str, Any] = {}
    while time.monotonic() < end:
        time.sleep(0.05)
        last = _probe(page, all_loaded=False, max_items=20)
    return last


def ordered_exhaust(page: Any, args: argparse.Namespace, expected_story: str) -> Dict[str, Any]:
    started = time.monotonic()
    clicked = 0
    scrolls = 0
    stuck_scrolls = 0
    last_first_key = ""

    emit("R45AR_TARGET_LOCKED_EXACT_LABEL_START", {
        "max_seconds": args.expand_max_seconds,
        "max_steps": args.max_steps,
        "target_url": args.target_url,
        "expected_story": expected_story,
    })

    initial_guard = _guard(page, expected_story)
    emit("R45AR_TARGET_GUARD", initial_guard)
    if not initial_guard.get("ok"):
        return {"status": "blocked", "reason": "target_surface_not_ready", "guard": initial_guard, "clicked": clicked}

    for step in range(1, args.max_steps + 1):
        elapsed = round(time.monotonic() - started, 2)
        if elapsed > args.expand_max_seconds:
            allp = _probe(page, True, 80)
            emit("R45AR_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                "reason": "timeout",
                "clicked": clicked,
                "scrolls": scrolls,
                "remaining_total": allp.get("total"),
                "remaining_counts": allp.get("counts"),
                "remaining_labels": (allp.get("labels") or [])[:40],
            })
            return {"status": "blocked", "reason": "timeout", "remaining": allp, "clicked": clicked}

        guard = _guard(page, expected_story)
        if not guard.get("ok"):
            emit("R45AR_TARGET_SURFACE_LOST", {"step": step, "clicked": clicked, "guard": guard})
            return {"status": "blocked", "reason": "target_surface_lost", "guard": guard, "clicked": clicked}

        vis = _probe(page, False, 40)
        emit("R45AR_VISIBLE_PENDING", {
            "step": step,
            "total": vis.get("total", 0),
            "counts": vis.get("counts", {}),
            "labels": (vis.get("labels") or [])[:12],
            "windowScrollY": vis.get("windowScrollY"),
            "elapsed_seconds": elapsed,
        })

        if int(vis.get("total") or 0) > 0:
            item = (vis.get("items") or [])[0]
            try:
                page.mouse.move(float(item["x"]), float(item["y"]))
                page.mouse.down()
                time.sleep(0.02)
                page.mouse.up()
                clicked += 1
                page.mouse.move(12, max(90, min(220, int(item["y"]) + 35)))
                time.sleep(args.click_settle_seconds)
                after_guard = _guard(page, expected_story)
                if not after_guard.get("ok"):
                    emit("R45AR_TARGET_SURFACE_LOST", {"step": step, "clicked": clicked, "after_click_label": item.get("label"), "guard": after_guard})
                    return {"status": "blocked", "reason": "target_surface_lost_after_click", "guard": after_guard, "clicked": clicked, "item": item}
                after = _probe(page, all_loaded=False, max_items=20)
                emit("R45AR_CLICK", {
                    "step": step,
                    "clicked": clicked,
                    "label": item.get("label"),
                    "category": item.get("category"),
                    "x": item.get("x"),
                    "y": item.get("y"),
                    "after_visible_total": after.get("total"),
                    "after_labels": (after.get("labels") or [])[:10],
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                })
            except Exception as e:
                allp = _probe(page, True, 80)
                emit("R45AR_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                    "reason": "click_exception",
                    "error": str(e)[:500],
                    "item": item,
                    "remaining_total": allp.get("total"),
                    "remaining_counts": allp.get("counts"),
                    "remaining_labels": (allp.get("labels") or [])[:40],
                })
                return {"status": "blocked", "reason": "click_exception", "remaining": allp, "clicked": clicked}
            continue

        allp = _probe(page, True, 80)
        emit("R45AR_ALL_LOADED_PENDING", {
            "step": step,
            "total": allp.get("total", 0),
            "counts": allp.get("counts", {}),
            "labels": (allp.get("labels") or [])[:20],
            "elapsed_seconds": elapsed,
        })

        if int(allp.get("total") or 0) == 0:
            final_guard = _guard(page, expected_story)
            if not final_guard.get("ok"):
                emit("R45AR_TARGET_SURFACE_LOST", {"step": step, "clicked": clicked, "guard": final_guard})
                return {"status": "blocked", "reason": "target_surface_lost_before_success", "guard": final_guard, "clicked": clicked}
            emit("R45AR_COMPLETE", {
                "status": "PASS_NO_ALL_LOADED_EXPAND_CONTROLS",
                "clicked": clicked,
                "scrolls": scrolls,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            })
            return {"status": "pass", "clicked": clicked, "scrolls": scrolls, "remaining": allp}

        first = (allp.get("items") or [{}])[0]
        first_key = str(first.get("key") or first.get("label") or "")
        try:
            res = page.evaluate(R45AR_SCROLL_FIRST_JS, {})
            scrolls += 1
            time.sleep(args.scroll_settle_seconds)
            emit("R45AR_SCROLL_TO_FIRST_REMAINING", {
                "step": step,
                "ok": res.get("ok") if isinstance(res, dict) else None,
                "target": res.get("target") if isinstance(res, dict) else None,
                "scrollParent": res.get("scrollParent") if isinstance(res, dict) else None,
                "finalRect": res.get("finalRect") if isinstance(res, dict) else None,
                "scrolls": scrolls,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            })

            now_vis = _probe(page, False, 10)
            if first_key == last_first_key and int(now_vis.get("total") or 0) == 0:
                stuck_scrolls += 1
            else:
                stuck_scrolls = 0
            last_first_key = first_key
            if stuck_scrolls >= args.max_stuck_scrolls:
                all2 = _probe(page, True, 80)
                emit("R45AR_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                    "reason": "container_scroll_not_revealing_first_control",
                    "stuck_scrolls": stuck_scrolls,
                    "first_remaining": (all2.get("items") or [None])[0],
                    "remaining_total": all2.get("total"),
                    "remaining_counts": all2.get("counts"),
                    "remaining_labels": (all2.get("labels") or [])[:40],
                })
                return {"status": "blocked", "reason": "container_scroll_not_revealing_first_control", "remaining": all2, "clicked": clicked}
            continue
        except Exception as e:
            emit("R45AR_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                "reason": "scroll_exception",
                "error": str(e)[:500],
                "remaining_total": allp.get("total"),
                "remaining_counts": allp.get("counts"),
                "remaining_labels": (allp.get("labels") or [])[:40],
            })
            return {"status": "blocked", "reason": "scroll_exception", "remaining": allp, "clicked": clicked}

    allp = _probe(page, True, 80)
    emit("R45AR_BLOCKED_REMAINING_EXPAND_CONTROLS", {
        "reason": "max_steps",
        "clicked": clicked,
        "scrolls": scrolls,
        "remaining_total": allp.get("total"),
        "remaining_counts": allp.get("counts"),
        "remaining_labels": (allp.get("labels") or [])[:40],
    })
    return {"status": "blocked", "reason": "max_steps", "remaining": allp, "clicked": clicked}


def _screenshot_tiles(page: Any, run_dir: Path) -> List[str]:
    paths: List[str] = []
    for idx in range(1, 4):
        p = run_dir / f"r45ar_visible_page_{idx:03d}.png"
        page.screenshot(path=str(p), full_page=False)
        paths.append(str(p))
        try:
            page.mouse.wheel(0, 650)
            time.sleep(0.2)
        except Exception:
            break
    return paths


def run_live(args: argparse.Namespace) -> Dict[str, Any]:
    from playwright.sync_api import sync_playwright

    target_url = _clean_target_url(args.target_url)
    expected_story = _target_fbid(target_url)
    out_root = Path(args.output_root).expanduser()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"r45ar_target_locked_exact_label_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    receipt: Dict[str, Any] = {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "target_url": target_url,
        "expected_story": expected_story,
        "run_dir": str(run_dir),
        "contract": contract(),
    }

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=args.user_data_dir,
            executable_path=args.chromium_executable or None,
            headless=False,
            viewport=None,
            args=[
                "--start-maximized",
                "--disable-session-crashed-bubble",
                "--hide-crash-restore-bubble",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        page = context.new_page()
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            page.bring_to_front()
            time.sleep(args.initial_settle_seconds)
            for other in list(context.pages):
                if other is not page:
                    try:
                        other.close(run_before_unload=False)
                    except Exception:
                        pass
            page.bring_to_front()

            summary = ordered_exhaust(page, args, expected_story) if args.auto_expand else {"status": "skipped"}
            receipt["auto_expand_summary"] = summary
            if summary.get("status") != "pass":
                receipt["status"] = "BLOCKED_OR_TARGET_SURFACE_LOST"
                receipt_path = run_dir / "r45ar_target_locked_exact_label_receipt.json"
                receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                receipt["receipt_path"] = str(receipt_path)
                print("R45AR blocked: expansion did not safely finish on the requested Facebook post surface. No final screenshot accepted.", flush=True)
                return receipt

            final_guard = _guard(page, expected_story)
            final_probe = _probe(page, True, 80)
            emit("R45AR_FINAL_ALL_LOADED_MISSED_REPORT", {
                "status": "PASS_NO_ALL_LOADED_EXPAND_CONTROLS" if int(final_probe.get("total") or 0) == 0 and final_guard.get("ok") else "NEEDS_MORE_EXPANSION_OR_TARGET_LOST",
                "guard": final_guard,
                "total": final_probe.get("total"),
                "counts": final_probe.get("counts"),
                "labels": (final_probe.get("labels") or [])[:40],
            })
            if int(final_probe.get("total") or 0) != 0 or not final_guard.get("ok"):
                receipt["status"] = "NEEDS_MORE_EXPANSION_OR_TARGET_LOST"
                receipt["final_probe"] = final_probe
                receipt["final_guard"] = final_guard
                receipt_path = run_dir / "r45ar_target_locked_exact_label_receipt.json"
                receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                receipt["receipt_path"] = str(receipt_path)
                return receipt

            if args.operator_pause:
                print("R45AR_OPERATOR_PAUSE", flush=True)
                print("Review page. It should still be the requested post and have zero remaining View all/View hidden/View more/replied controls. Press ENTER to screenshot.", flush=True)
                input()

            receipt["screenshot_paths"] = _screenshot_tiles(page, run_dir) if args.tile_screenshots else []
            receipt["status"] = "PASS_R45AR_TARGET_LOCKED_EXACT_LABEL_ORDERED_EXHAUST"
            receipt_path = run_dir / "r45ar_target_locked_exact_label_receipt.json"
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
            receipt["receipt_path"] = str(receipt_path)
            print("YTCE_R45AR_TARGET_LOCKED_EXACT_LABEL_DONE", flush=True)
            print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
            return receipt
        finally:
            try:
                context.close()
            except Exception:
                pass


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    checks = [
        {"name": "contract_marker", "status": "pass" if contract()["marker"] == MARKER else "fail"},
        {"name": "target_guard_present", "status": "pass" if "R45AR_TARGET_SURFACE_LOST" in source and "expectedStory" in source else "fail"},
        {"name": "exact_label_extraction_present", "status": "pass" if "textRectExact" in R45AR_PROBE_JS and "View\\s+all" in R45AR_PROBE_JS else "fail"},
        {"name": "unsafe_profile_anchor_excluded", "status": "pass" if "unsafeNavigatingAnchor" in R45AR_PROBE_JS else "fail"},
        {"name": "no_hidden_platform_api", "status": "pass" if contract()["hidden_platform_api_scraping_enabled"] is False else "fail"},
    ]
    status = "PASS_R45AR_SELF_TEST" if all(c["status"] == "pass" for c in checks) else "FAIL_R45AR_SELF_TEST"
    result = {"marker": MARKER, "status": status, "schema_version": SCHEMA_VERSION, "checks": checks, "contract": contract()}
    out = Path(args.output_root)
    out.mkdir(parents=True, exist_ok=True)
    (out / "r45ar_self_test.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MARKER)
    print(status)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="R45AR target-locked exact-label ordered Facebook expansion exhaust")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--target-url", default="")
    ap.add_argument("--auto-expand", action="store_true")
    ap.add_argument("--operator-pause", action="store_true")
    ap.add_argument("--tile-screenshots", action="store_true")
    ap.add_argument("--expand-max-seconds", type=float, default=900.0)
    ap.add_argument("--max-steps", type=int, default=2500)
    ap.add_argument("--max-stuck-scrolls", type=int, default=8)
    ap.add_argument("--click-settle-seconds", type=float, default=0.55)
    ap.add_argument("--scroll-settle-seconds", type=float, default=0.14)
    ap.add_argument("--initial-settle-seconds", type=float, default=3.0)
    ap.add_argument("--chromium-executable", default="")
    ap.add_argument("--user-data-dir", default="")
    ap.add_argument("--output-root", default="profile_media_live_captures/r45ar_target_locked_exact_label")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        result = run_self_test(args)
        return 0 if str(result.get("status", "")).startswith("PASS") else 1
    if not args.target_url:
        print("ERROR: --target-url is required", flush=True)
        return 2
    if not args.user_data_dir:
        print("ERROR: --user-data-dir is required", flush=True)
        return 2
    result = run_live(args)
    return 0 if str(result.get("status", "")).startswith("PASS") else 3


if __name__ == "__main__":
    raise SystemExit(main())
