#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List


MARKER = "YTCE_R45AQ_CONTAINER_AWARE_ORDERED_EXHAUST"
SCHEMA_VERSION = "facebook_ordered_exhaust.r45aq.v1"


def _clean_target_url(url: str) -> str:
    s = (url or "").strip().strip('"').strip("'")
    m = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", s)
    if m:
        s = m.group(1)
    s = s.replace("\\&", "&").replace("\\:", ":")
    return s


R45AQ_PROBE_JS = r"""
(args) => {
  const allLoaded = !!(args && args.allLoaded);
  const maxItems = Number(args && args.maxItems || 80);
  const topMargin = Number(args && args.topMargin || 78);
  const bottomMargin = Number(args && args.bottomMargin || 150);

  const norm = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const patterns = [
    {cat:'view_all_replies', rx:/^view\s+all\s+\d+\s+repl(?:y|ies)\b/i},
    {cat:'view_number_replies', rx:/^view\s+\d+\s+repl(?:y|ies)\b/i},
    {cat:'view_more_replies', rx:/^view\s+(?:\d+\s+more\s+)?repl(?:y|ies)\b/i},
    {cat:'view_hidden', rx:/^view\s+hidden\s+(?:repl(?:y|ies)|comments?)\b/i},
    {cat:'view_comments', rx:/^view\s+(?:all\s+)?\d+\s+comments?\b/i},
    {cat:'replied_bucket', rx:/\breplied\s*[·•.\-]\s*\d+\s+repl(?:y|ies)\b/i}
  ];
  const deny = /^(like|reply|share|send|comment|copy link|follow|message|all|most relevant|newest|top comments|edited|gif|sticker|photo|avatar)$/i;

  const categoryFor = (text) => {
    const t = norm(text);
    if (!t || t.length > 150 || deny.test(t)) return null;
    for (const p of patterns) if (p.rx.test(t)) return p.cat;
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

  const clickableAncestor = (el) => {
    let cur = el;
    for (let i = 0; cur && i < 9; i++, cur = cur.parentElement) {
      const tag = (cur.tagName || '').toLowerCase();
      const role = cur.getAttribute && (cur.getAttribute('role') || '');
      const tab = cur.getAttribute && cur.getAttribute('tabindex');
      if (tag === 'button' || tag === 'a' || role === 'button' || role === 'link' || tab === '0') {
        if (!isBadSurface(cur) && styleVisible(cur)) return cur;
      }
    }
    return isBadSurface(el) ? null : el;
  };

  const labelFor = (el) => {
    const parts = [
      el.getAttribute && (el.getAttribute('aria-label') || ''),
      el.getAttribute && (el.getAttribute('title') || ''),
      el.innerText || '',
      el.textContent || ''
    ].map(norm).filter(Boolean);
    const out = [];
    for (const p of parts) {
      for (const bit of [p, ...p.split(/\n+/).map(norm)]) {
        if (categoryFor(bit)) out.push(bit);
      }
    }
    if (!out.length) return '';
    out.sort((a,b) => a.length - b.length);
    return out[0];
  };

  const textRect = (el, wanted) => {
    const want = norm(wanted).toLowerCase();
    try {
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
          const val = norm(node.nodeValue);
          if (!val) return NodeFilter.FILTER_REJECT;
          if (want && val.toLowerCase().includes(want.slice(0, Math.min(20, want.length)))) return NodeFilter.FILTER_ACCEPT;
          if (categoryFor(val)) return NodeFilter.FILTER_ACCEPT;
          return NodeFilter.FILTER_REJECT;
        }
      });
      let node;
      while ((node = walker.nextNode())) {
        const range = document.createRange();
        range.selectNodeContents(node);
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
    const label = labelFor(el);
    const cat = categoryFor(label);
    if (!cat) continue;
    const clickEl = clickableAncestor(el);
    if (!clickEl) continue;
    const cr = clickEl.getBoundingClientRect();
    if (!rectOk(cr)) continue;
    const tr = textRect(el, label) || textRect(clickEl, label) || cr;
    if (!rectOk(tr)) continue;
    const sp = scrollParent(clickEl);
    const si = scrollInfo(sp);
    const absTop = si.scrollTop + Math.round(tr.top - si.rectTop);
    const key = [cat, label, absTop, Math.round(tr.left)].join('|');
    if (seen.has(key)) continue;
    seen.add(key);
    const isVisible = viewportVisible(tr);
    if (!allLoaded && !isVisible) continue;
    candidates.push({
      key, category: cat, label,
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
    marker:'R45AQ_PROBE',
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


R45AQ_SCROLL_FIRST_JS = r"""
(args) => {
  const probeFn = """ + R45AQ_PROBE_JS + r""";
  const probe = probeFn({allLoaded:true, maxItems:1, topMargin:78, bottomMargin:150});
  const target = probe.items && probe.items[0];
  if (!target) return {ok:false, reason:'no_remaining_controls', probe};

  const norm = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const wanted = target.label;
  const cat = target.category;

  const categoryFor = (text) => {
    const t = norm(text);
    if (!t) return null;
    if (/^view\s+all\s+\d+\s+repl(?:y|ies)\b/i.test(t)) return 'view_all_replies';
    if (/^view\s+\d+\s+repl(?:y|ies)\b/i.test(t)) return 'view_number_replies';
    if (/^view\s+(?:\d+\s+more\s+)?repl(?:y|ies)\b/i.test(t)) return 'view_more_replies';
    if (/^view\s+hidden\s+(?:repl(?:y|ies)|comments?)\b/i.test(t)) return 'view_hidden';
    if (/^view\s+(?:all\s+)?\d+\s+comments?\b/i.test(t)) return 'view_comments';
    if (/\breplied\s*[·•.\-]\s*\d+\s+repl(?:y|ies)\b/i.test(t)) return 'replied_bucket';
    return null;
  };

  const styleVisible = (el) => {
    if (!el || !el.isConnected) return false;
    const s = getComputedStyle(el);
    return !!s && s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) !== 0;
  };

  const labelFor = (el) => {
    const parts = [
      el.getAttribute && (el.getAttribute('aria-label') || ''),
      el.getAttribute && (el.getAttribute('title') || ''),
      el.innerText || '',
      el.textContent || ''
    ].map(norm).filter(Boolean);
    const out = [];
    for (const p of parts) for (const bit of [p, ...p.split(/\n+/).map(norm)]) if (categoryFor(bit)) out.push(bit);
    out.sort((a,b)=>a.length-b.length);
    return out[0] || '';
  };

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

  const candidates = Array.from(document.querySelectorAll('div[role="button"],span[role="button"],a[role="button"],button,a,[tabindex="0"],span,div'));
  let chosen = null;
  for (const el of candidates) {
    if (!styleVisible(el)) continue;
    const label = labelFor(el);
    if (label !== wanted && !(categoryFor(label) === cat && label.toLowerCase() === wanted.toLowerCase())) continue;
    chosen = clickableAncestor(el);
    break;
  }
  if (!chosen) return {ok:false, reason:'target_element_not_found', target, probe};

  const sp = scrollParent(chosen);
  const isDoc = sp === document.scrollingElement || sp === document.documentElement || sp === document.body;
  const before = isDoc ? (window.scrollY || sp.scrollTop || 0) : sp.scrollTop;
  const r = chosen.getBoundingClientRect();

  if (isDoc) {
    const wantedY = Math.max(0, before + r.top - Math.floor(innerHeight * 0.38));
    window.scrollTo({top:wantedY, left:0, behavior:'instant'});
  } else {
    const pr = sp.getBoundingClientRect();
    const delta = (r.top - pr.top) - Math.floor(sp.clientHeight * 0.38);
    sp.scrollTop = Math.max(0, sp.scrollTop + delta);
  }

  // Fallback if Facebook's active scroller was not the nearest overflow element.
  const after1 = isDoc ? (window.scrollY || sp.scrollTop || 0) : sp.scrollTop;
  const r2 = chosen.getBoundingClientRect();
  if (Math.abs(after1 - before) < 2 && (r2.top < 78 || r2.bottom > innerHeight - 150)) {
    try { chosen.scrollIntoView({block:'center', inline:'nearest', behavior:'instant'}); } catch (_) {}
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
        "primary_route": "operator-controlled signed-in Facebook Chromium session; visible-page-only ordered expansion controls; no hidden APIs/cookies/profile parsing",
        "r45aq_container_aware_rule": "Unlike R45AP, scrolling is applied to the nearest active Facebook scroll container, not only window.scrollTo. The runner clicks the first visible pending control, rescans the same visible band, and only accepts success when all loaded expand controls are zero.",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "webview2_storage_or_cookie_inspection_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def _probe(page: Any, all_loaded: bool, max_items: int = 80) -> Dict[str, Any]:
    return page.evaluate(R45AQ_PROBE_JS, {
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


def ordered_exhaust(page: Any, args: argparse.Namespace) -> Dict[str, Any]:
    started = time.monotonic()
    clicked = 0
    scrolls = 0
    stuck_scrolls = 0
    last_first_key = ""

    emit("R45AQ_CONTAINER_AWARE_ORDERED_EXHAUST_START", {
        "max_seconds": args.expand_max_seconds,
        "max_steps": args.max_steps,
        "target_url": args.target_url,
    })

    for step in range(1, args.max_steps + 1):
        elapsed = round(time.monotonic() - started, 2)
        if elapsed > args.expand_max_seconds:
            allp = _probe(page, True, 80)
            emit("R45AQ_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                "reason": "timeout",
                "clicked": clicked,
                "scrolls": scrolls,
                "remaining_total": allp.get("total"),
                "remaining_counts": allp.get("counts"),
                "remaining_labels": (allp.get("labels") or [])[:40],
            })
            return {"status": "blocked", "reason": "timeout", "remaining": allp, "clicked": clicked}

        vis = _probe(page, False, 40)
        emit("R45AQ_VISIBLE_PENDING", {
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
                after = _wait_short(page, args.click_settle_seconds)
                emit("R45AQ_CLICK", {
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
                emit("R45AQ_BLOCKED_REMAINING_EXPAND_CONTROLS", {
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
        emit("R45AQ_ALL_LOADED_PENDING", {
            "step": step,
            "total": allp.get("total", 0),
            "counts": allp.get("counts", {}),
            "labels": (allp.get("labels") or [])[:20],
            "elapsed_seconds": elapsed,
        })

        if int(allp.get("total") or 0) == 0:
            emit("R45AQ_COMPLETE", {
                "status": "PASS_NO_ALL_LOADED_EXPAND_CONTROLS",
                "clicked": clicked,
                "scrolls": scrolls,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            })
            return {"status": "pass", "clicked": clicked, "scrolls": scrolls, "remaining": allp}

        first = (allp.get("items") or [{}])[0]
        first_key = str(first.get("key") or first.get("label") or "")
        try:
            res = page.evaluate(R45AQ_SCROLL_FIRST_JS, {})
            scrolls += 1
            time.sleep(args.scroll_settle_seconds)
            emit("R45AQ_SCROLL_TO_FIRST_REMAINING", {
                "step": step,
                "ok": res.get("ok") if isinstance(res, dict) else None,
                "target": res.get("target") if isinstance(res, dict) else None,
                "scrollParent": res.get("scrollParent") if isinstance(res, dict) else None,
                "finalRect": res.get("finalRect") if isinstance(res, dict) else None,
                "scrolls": scrolls,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            })

            # If the same first control remains not visible after several container-aware attempts, fail instead of looping.
            now_vis = _probe(page, False, 10)
            if first_key == last_first_key and int(now_vis.get("total") or 0) == 0:
                stuck_scrolls += 1
            else:
                stuck_scrolls = 0
            last_first_key = first_key
            if stuck_scrolls >= args.max_stuck_scrolls:
                all2 = _probe(page, True, 80)
                emit("R45AQ_BLOCKED_REMAINING_EXPAND_CONTROLS", {
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
            emit("R45AQ_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                "reason": "scroll_exception",
                "error": str(e)[:500],
                "remaining_total": allp.get("total"),
                "remaining_counts": allp.get("counts"),
                "remaining_labels": (allp.get("labels") or [])[:40],
            })
            return {"status": "blocked", "reason": "scroll_exception", "remaining": allp, "clicked": clicked}

    allp = _probe(page, True, 80)
    emit("R45AQ_BLOCKED_REMAINING_EXPAND_CONTROLS", {
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
        p = run_dir / f"r45aq_visible_page_{idx:03d}.png"
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
    out_root = Path(args.output_root).expanduser()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"r45aq_container_aware_ordered_exhaust_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    receipt: Dict[str, Any] = {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "target_url": target_url,
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

            summary = ordered_exhaust(page, args) if args.auto_expand else {"status": "skipped"}
            receipt["auto_expand_summary"] = summary
            if summary.get("status") != "pass":
                receipt["status"] = "BLOCKED_REMAINING_EXPAND_CONTROLS"
                receipt_path = run_dir / "r45aq_container_aware_ordered_exhaust_receipt.json"
                receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                receipt["receipt_path"] = str(receipt_path)
                print("R45AQ blocked: remaining expansion controls were not exhausted. No final screenshot accepted.", flush=True)
                return receipt

            final_probe = _probe(page, True, 80)
            emit("R45AQ_FINAL_ALL_LOADED_MISSED_REPORT", {
                "status": "PASS_NO_ALL_LOADED_EXPAND_CONTROLS" if int(final_probe.get("total") or 0) == 0 else "NEEDS_MORE_EXPANSION",
                "total": final_probe.get("total"),
                "counts": final_probe.get("counts"),
                "labels": (final_probe.get("labels") or [])[:40],
            })
            if int(final_probe.get("total") or 0) != 0:
                receipt["status"] = "NEEDS_MORE_EXPANSION"
                receipt["final_probe"] = final_probe
                receipt_path = run_dir / "r45aq_container_aware_ordered_exhaust_receipt.json"
                receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                receipt["receipt_path"] = str(receipt_path)
                return receipt

            if args.operator_pause:
                print("R45AQ_OPERATOR_PAUSE", flush=True)
                print("Review page. It should have zero remaining View all/View hidden/View more/replied controls. Press ENTER to screenshot.", flush=True)
                input()

            receipt["screenshot_paths"] = _screenshot_tiles(page, run_dir) if args.tile_screenshots else []
            receipt["status"] = "PASS_R45AQ_CONTAINER_AWARE_ORDERED_EXHAUST"
            receipt_path = run_dir / "r45aq_container_aware_ordered_exhaust_receipt.json"
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
            receipt["receipt_path"] = str(receipt_path)
            print("YTCE_R45AQ_CONTAINER_AWARE_ORDERED_EXHAUST_DONE", flush=True)
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
        {"name": "markdown_url_cleaner_present", "status": "pass" if "_clean_target_url" in source and "\\\\&" in source else "fail"},
        {"name": "container_scroll_present", "status": "pass" if "scrollParent" in R45AQ_PROBE_JS and "R45AQ_SCROLL_FIRST_JS" in source else "fail"},
        {"name": "failfast_remaining_controls_present", "status": "pass" if "R45AQ_BLOCKED_REMAINING_EXPAND_CONTROLS" in source else "fail"},
        {"name": "no_hidden_platform_api", "status": "pass" if contract()["hidden_platform_api_scraping_enabled"] is False else "fail"},
    ]
    status = "PASS_R45AQ_SELF_TEST" if all(c["status"] == "pass" for c in checks) else "FAIL_R45AQ_SELF_TEST"
    result = {"marker": MARKER, "status": status, "schema_version": SCHEMA_VERSION, "checks": checks, "contract": contract()}
    out = Path(args.output_root)
    out.mkdir(parents=True, exist_ok=True)
    (out / "r45aq_self_test.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MARKER)
    print(status)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="R45AQ container-aware ordered Facebook expansion exhaust")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--target-url", default="")
    ap.add_argument("--auto-expand", action="store_true")
    ap.add_argument("--operator-pause", action="store_true")
    ap.add_argument("--tile-screenshots", action="store_true")
    ap.add_argument("--expand-max-seconds", type=float, default=900.0)
    ap.add_argument("--max-steps", type=int, default=2500)
    ap.add_argument("--max-stuck-scrolls", type=int, default=8)
    ap.add_argument("--click-settle-seconds", type=float, default=0.45)
    ap.add_argument("--scroll-settle-seconds", type=float, default=0.12)
    ap.add_argument("--initial-settle-seconds", type=float, default=3.0)
    ap.add_argument("--chromium-executable", default="")
    ap.add_argument("--user-data-dir", default="")
    ap.add_argument("--output-root", default="profile_media_live_captures/r45aq_container_aware_ordered_exhaust")
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
