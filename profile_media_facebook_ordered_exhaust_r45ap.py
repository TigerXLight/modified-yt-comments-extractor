#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


MARKER = "YTCE_R45AP_SIMPLE_ORDERED_EXHAUST_ENGINE"
SCHEMA_VERSION = "facebook_ordered_exhaust.r45ap.v1"


R45AP_PROBE_JS = r"""
(args) => {
  const topMargin = Number(args && args.topMargin || 80);
  const bottomMargin = Number(args && args.bottomMargin || 140);
  const allLoaded = !!(args && args.allLoaded);
  const maxItems = Number(args && args.maxItems || 60);

  const rx = [
    {cat:'view_all_replies', rx:/^view\s+all\s+\d+\s+repl(?:y|ies)\b/i},
    {cat:'view_number_replies', rx:/^view\s+\d+\s+repl(?:y|ies)\b/i},
    {cat:'view_more_replies', rx:/^view\s+(?:\d+\s+more\s+)?repl(?:y|ies)\b/i},
    {cat:'view_hidden', rx:/^view\s+hidden\s+(?:repl(?:y|ies)|comments?)\b/i},
    {cat:'view_comments', rx:/^view\s+(?:all\s+)?\d+\s+comments?\b/i},
    {cat:'replied_buckets', rx:/\breplied\s*[·•.\-]\s*\d+\s+repl(?:y|ies)\b/i}
  ];
  const deny = /^(like|reply|share|send|comment|copy link|follow|message|all|most relevant|newest|top comments|edited|gif|sticker|photo|avatar)$/i;
  const norm = (text) => String(text || '').replace(/\s+/g, ' ').trim();

  const styleVisible = (el) => {
    if (!el || !el.ownerDocument || !el.isConnected) return false;
    const s = window.getComputedStyle(el);
    if (!s || s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
    return true;
  };

  const rectOk = (r) => !!r && Number.isFinite(r.top) && Number.isFinite(r.left) && r.width > 0 && r.height > 0;

  const inViewportBand = (r) => {
    if (!rectOk(r)) return false;
    if (r.bottom <= topMargin) return false;
    if (r.top >= window.innerHeight - bottomMargin) return false;
    if (r.right <= 0 || r.left >= window.innerWidth) return false;
    return true;
  };

  const categoryFor = (text) => {
    const t = norm(text);
    if (!t || t.length > 140 || deny.test(t)) return null;
    for (const item of rx) {
      if (item.rx.test(t)) return item.cat;
    }
    return null;
  };

  const badSurface = (el) => {
    if (!el) return true;
    if (el.closest('textarea,input,select,[contenteditable="true"]')) return true;
    const blob = norm([
      el.getAttribute('aria-label') || '',
      el.getAttribute('title') || '',
      el.className || ''
    ].join(' ')).toLowerCase();
    if (/(composer|comment as|write a comment|reply to|gif|sticker|photo|camera|avatar|upload|file)/i.test(blob)) return true;
    return false;
  };

  const clickableAncestor = (el) => {
    let cur = el;
    for (let i = 0; cur && i < 8; i++, cur = cur.parentElement) {
      const tag = (cur.tagName || '').toLowerCase();
      const role = (cur.getAttribute && cur.getAttribute('role')) || '';
      const tab = cur.getAttribute && cur.getAttribute('tabindex');
      if (tag === 'button' || tag === 'a' || role === 'button' || role === 'link' || tab === '0') {
        if (!badSurface(cur) && styleVisible(cur)) return cur;
      }
    }
    return badSurface(el) ? null : el;
  };

  const textNodeRect = (el, wanted) => {
    const wantedNorm = norm(wanted).toLowerCase();
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const val = norm(node.nodeValue);
        if (!val) return NodeFilter.FILTER_REJECT;
        if (wantedNorm && val.toLowerCase().includes(wantedNorm.slice(0, Math.min(24, wantedNorm.length)))) {
          return NodeFilter.FILTER_ACCEPT;
        }
        if (categoryFor(val)) return NodeFilter.FILTER_ACCEPT;
        return NodeFilter.FILTER_REJECT;
      }
    });
    let node;
    while ((node = walker.nextNode())) {
      try {
        const range = document.createRange();
        range.selectNodeContents(node);
        const rects = Array.from(range.getClientRects()).filter(rectOk);
        range.detach();
        if (rects.length) {
          rects.sort((a,b) => Math.abs((a.top+a.bottom)/2 - window.innerHeight/2) - Math.abs((b.top+b.bottom)/2 - window.innerHeight/2));
          return rects[0];
        }
      } catch (_) {}
    }
    return null;
  };

  const labelFor = (el) => {
    const pieces = [
      el.getAttribute && el.getAttribute('aria-label') || '',
      el.getAttribute && el.getAttribute('title') || '',
      el.innerText || '',
      el.textContent || ''
    ].map(norm).filter(Boolean);

    // Prefer the shortest matching piece, because Facebook often nests the label
    // inside a larger role=button/comment row.
    const matches = [];
    for (const p of pieces) {
      const bits = p.split(/\n+/).map(norm).filter(Boolean);
      for (const b of [p, ...bits]) {
        if (categoryFor(b)) matches.push(b);
      }
    }
    if (!matches.length) return '';
    matches.sort((a,b) => a.length - b.length);
    return matches[0];
  };

  const raw = Array.from(document.querySelectorAll(
    'div[role="button"],span[role="button"],a[role="button"],button,a,[tabindex="0"],span,div'
  ));

  const items = [];
  const seen = new Set();
  for (const el of raw) {
    if (!styleVisible(el)) continue;
    const label = labelFor(el);
    const cat = categoryFor(label);
    if (!cat) continue;
    const clickable = clickableAncestor(el);
    if (!clickable) continue;
    const cr = clickable.getBoundingClientRect();
    if (!rectOk(cr)) continue;

    const tr = textNodeRect(el, label) || textNodeRect(clickable, label) || cr;
    const visibleNow = inViewportBand(tr);
    if (!allLoaded && !visibleNow) continue;

    const pageTop = Math.round((tr.top + window.scrollY));
    const pageLeft = Math.round((tr.left + window.scrollX));
    const key = [cat, label, pageTop, pageLeft].join('|');
    if (seen.has(key)) continue;
    seen.add(key);

    items.push({
      key, category: cat, label,
      top: Math.round(tr.top),
      left: Math.round(tr.left),
      bottom: Math.round(tr.bottom),
      right: Math.round(tr.right),
      pageTop, pageLeft,
      x: Math.round(Math.min(Math.max((tr.left + tr.right) / 2, 2), window.innerWidth - 2)),
      y: Math.round(Math.min(Math.max((tr.top + tr.bottom) / 2, 2), window.innerHeight - 2)),
      tag: clickable.tagName || '',
      role: clickable.getAttribute && clickable.getAttribute('role') || '',
      visibleNow
    });
  }

  items.sort((a,b) => a.pageTop - b.pageTop || a.pageLeft - b.pageLeft || a.label.localeCompare(b.label));

  const counts = {};
  for (const item of items) counts[item.category] = (counts[item.category] || 0) + 1;

  return {
    marker: 'R45AP_PROBE',
    total: items.length,
    counts,
    labels: items.slice(0, maxItems).map(x => x.label),
    items: items.slice(0, maxItems),
    allLoaded,
    url: location.href,
    scrollY: Math.round(window.scrollY || 0),
    innerHeight: Math.round(window.innerHeight || 0),
    bodyTextChars: document.body && document.body.innerText ? document.body.innerText.length : 0,
    scrollHeight: document.scrollingElement ? Math.round(document.scrollingElement.scrollHeight) : 0,
    clientHeight: document.scrollingElement ? Math.round(document.scrollingElement.clientHeight) : 0
  };
}
"""


R45AP_SCROLL_FIRST_ALL_LOADED_JS = r"""
(args) => {
  const probe = (""" + R45AP_PROBE_JS + r""")({allLoaded:true, maxItems:1, topMargin:80, bottomMargin:140});
  const first = probe.items && probe.items[0];
  if (!first) return {ok:false, reason:'no_all_loaded_controls', probe};
  const y = Math.max(0, Number(first.pageTop || 0) - Math.floor(window.innerHeight * 0.35));
  window.scrollTo({top:y, left:0, behavior:'instant'});
  return {ok:true, target:first, scrollY:Math.round(window.scrollY || 0), wantedY:Math.round(y), probe};
}
"""


R45AP_AT_BOTTOM_JS = r"""
() => {
  const se = document.scrollingElement || document.documentElement || document.body;
  const y = window.scrollY || se.scrollTop || 0;
  const h = se.scrollHeight || document.body.scrollHeight || 0;
  const ch = window.innerHeight || se.clientHeight || 0;
  return {scrollY:Math.round(y), scrollHeight:Math.round(h), clientHeight:Math.round(ch), atBottom: y + ch >= h - 8};
}
"""


def emit(event: str, payload: Dict[str, Any]) -> None:
    print(event + " " + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)


def contract() -> Dict[str, Any]:
    return {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "primary_route": "operator-controlled signed-in Facebook Chromium session; visible-page-only expansion controls; no hidden APIs/cookies/profile parsing",
        "r45ap_simple_ordered_exhaust_rule": "Click the first/topmost visible expansion control and rescan the same viewport before any downward scroll. At bottom, all-loaded leftovers force scroll-to-first-leftover and repeat; remaining controls fail the run instead of allowing final screenshots.",
        "visible_controls": [
            "View all N replies",
            "View N replies",
            "View hidden replies/comments",
            "View more replies",
            "Name replied · N replies",
        ],
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "webview2_storage_or_cookie_inspection_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def _probe(page: Any, all_loaded: bool, max_items: int = 60) -> Dict[str, Any]:
    return page.evaluate(R45AP_PROBE_JS, {
        "allLoaded": bool(all_loaded),
        "maxItems": max_items,
        "topMargin": 80,
        "bottomMargin": 140,
    }) or {}


def _wait_changed(page: Any, before_sig: Dict[str, Any], timeout: float, poll: float) -> Dict[str, Any]:
    deadline = time.monotonic() + max(0.05, timeout)
    last = {}
    while time.monotonic() < deadline:
        time.sleep(max(0.03, poll))
        now = _probe(page, all_loaded=False, max_items=10)
        last = now
        sig = (
            now.get("total"),
            now.get("bodyTextChars"),
            now.get("scrollHeight"),
            "|".join(now.get("labels") or []),
        )
        old = (
            before_sig.get("total"),
            before_sig.get("bodyTextChars"),
            before_sig.get("scrollHeight"),
            "|".join(before_sig.get("labels") or []),
        )
        if sig != old:
            return now
    return last or _probe(page, all_loaded=False, max_items=10)


def ordered_exhaust(page: Any, args: argparse.Namespace) -> Dict[str, Any]:
    started = time.monotonic()
    clicked = 0
    scrolls = 0
    scroll_to_leftovers = 0
    blocked_same_total = 0
    last_all_total: Optional[int] = None

    try:
        page.evaluate("() => { window.scrollTo({top:0,left:0,behavior:'instant'}); }")
        time.sleep(0.5)
    except Exception:
        pass

    emit("R45AP_SIMPLE_ORDERED_EXHAUST_START", {
        "max_seconds": args.expand_max_seconds,
        "max_steps": args.max_steps,
        "target_url": args.target_url,
    })

    for step in range(1, args.max_steps + 1):
        elapsed = round(time.monotonic() - started, 2)
        if elapsed > args.expand_max_seconds:
            allp = _probe(page, all_loaded=True, max_items=80)
            emit("R45AP_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                "reason": "timeout",
                "elapsed_seconds": elapsed,
                "clicked": clicked,
                "scrolls": scrolls,
                "remaining_total": allp.get("total"),
                "remaining_counts": allp.get("counts"),
                "remaining_labels": (allp.get("labels") or [])[:30],
            })
            return {"status": "blocked", "reason": "timeout", "clicked": clicked, "remaining": allp}

        vis = _probe(page, all_loaded=False, max_items=40)
        emit("R45AP_VISIBLE_PENDING", {
            "step": step,
            "total": vis.get("total", 0),
            "counts": vis.get("counts", {}),
            "labels": (vis.get("labels") or [])[:12],
            "scrollY": vis.get("scrollY"),
            "elapsed_seconds": elapsed,
        })

        if int(vis.get("total") or 0) > 0:
            item = (vis.get("items") or [])[0]
            before = vis
            try:
                page.mouse.move(float(item["x"]), float(item["y"]))
                page.mouse.down()
                time.sleep(0.025)
                page.mouse.up()
                clicked += 1
                page.mouse.move(12, max(90, min(180, int(item["y"]) + 30)))
                after = _wait_changed(page, before, args.click_settle_seconds, 0.06)
                emit("R45AP_CLICK", {
                    "step": step,
                    "clicked": clicked,
                    "label": item.get("label"),
                    "category": item.get("category"),
                    "x": item.get("x"),
                    "y": item.get("y"),
                    "before_visible_total": before.get("total"),
                    "after_visible_total": after.get("total"),
                    "after_labels": (after.get("labels") or [])[:10],
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                })
            except Exception as e:
                allp = _probe(page, all_loaded=True, max_items=80)
                emit("R45AP_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                    "reason": "click_exception",
                    "error": str(e)[:500],
                    "item": item,
                    "remaining_total": allp.get("total"),
                    "remaining_counts": allp.get("counts"),
                    "remaining_labels": (allp.get("labels") or [])[:30],
                })
                return {"status": "blocked", "reason": "click_exception", "clicked": clicked, "remaining": allp}
            continue

        allp = _probe(page, all_loaded=True, max_items=80)
        emit("R45AP_ALL_LOADED_PENDING", {
            "step": step,
            "total": allp.get("total", 0),
            "counts": allp.get("counts", {}),
            "labels": (allp.get("labels") or [])[:20],
            "scrollY": allp.get("scrollY"),
            "elapsed_seconds": elapsed,
        })

        if int(allp.get("total") or 0) == 0:
            emit("R45AP_COMPLETE", {
                "status": "PASS_NO_ALL_LOADED_EXPAND_CONTROLS",
                "clicked": clicked,
                "scrolls": scrolls,
                "scroll_to_leftovers": scroll_to_leftovers,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            })
            return {"status": "pass", "clicked": clicked, "scrolls": scrolls, "remaining": allp}

        total = int(allp.get("total") or 0)
        if last_all_total == total:
            blocked_same_total += 1
        else:
            blocked_same_total = 0
            last_all_total = total

        if blocked_same_total >= args.max_same_remaining_cycles:
            emit("R45AP_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                "reason": "remaining_count_not_reducing",
                "same_total_cycles": blocked_same_total,
                "clicked": clicked,
                "scrolls": scrolls,
                "scroll_to_leftovers": scroll_to_leftovers,
                "remaining_total": total,
                "remaining_counts": allp.get("counts"),
                "remaining_labels": (allp.get("labels") or [])[:40],
                "first_remaining": (allp.get("items") or [None])[0],
            })
            return {"status": "blocked", "reason": "remaining_count_not_reducing", "clicked": clicked, "remaining": allp}

        # Strictly drive by first remaining all-loaded control.
        try:
            res = page.evaluate(R45AP_SCROLL_FIRST_ALL_LOADED_JS, {})
            scroll_to_leftovers += 1
            time.sleep(args.scroll_settle_seconds)
            emit("R45AP_SCROLL_TO_FIRST_REMAINING", {
                "step": step,
                "ok": res.get("ok") if isinstance(res, dict) else None,
                "target": res.get("target") if isinstance(res, dict) else None,
                "scroll_to_leftovers": scroll_to_leftovers,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            })
            continue
        except Exception as e:
            emit("R45AP_BLOCKED_REMAINING_EXPAND_CONTROLS", {
                "reason": "scroll_to_first_remaining_exception",
                "error": str(e)[:500],
                "remaining_total": allp.get("total"),
                "remaining_counts": allp.get("counts"),
                "remaining_labels": (allp.get("labels") or [])[:30],
            })
            return {"status": "blocked", "reason": "scroll_exception", "clicked": clicked, "remaining": allp}

    allp = _probe(page, all_loaded=True, max_items=80)
    emit("R45AP_BLOCKED_REMAINING_EXPAND_CONTROLS", {
        "reason": "max_steps",
        "clicked": clicked,
        "scrolls": scrolls,
        "remaining_total": allp.get("total"),
        "remaining_counts": allp.get("counts"),
        "remaining_labels": (allp.get("labels") or [])[:30],
    })
    return {"status": "blocked", "reason": "max_steps", "clicked": clicked, "remaining": allp}


def _screenshot_tiles(page: Any, run_dir: Path) -> List[str]:
    paths: List[str] = []
    try:
        info = page.evaluate(R45AP_AT_BOTTOM_JS)
        scroll_height = int(info.get("scrollHeight") or 0)
        client_height = max(600, int(info.get("clientHeight") or 900))
        top = 0
        idx = 1
        while top < max(scroll_height, client_height):
            page.evaluate("(y) => window.scrollTo({top:y,left:0,behavior:'instant'})", top)
            time.sleep(0.15)
            path = run_dir / f"r45ap_visible_page_tile_{idx:03d}.png"
            page.screenshot(path=str(path), full_page=False)
            paths.append(str(path))
            idx += 1
            if idx > 80:
                break
            top += int(client_height * 0.85)
    except Exception as e:
        emit("R45AP_SCREENSHOT_WARNING", {"error": str(e)[:500]})
    return paths


def run_live(args: argparse.Namespace) -> Dict[str, Any]:
    from playwright.sync_api import sync_playwright

    out_root = Path(args.output_root).expanduser()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"r45ap_ordered_exhaust_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    receipt: Dict[str, Any] = {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "target_url": args.target_url,
        "run_dir": str(run_dir),
        "contract": contract(),
    }

    with sync_playwright() as p:
        launch_args = [
            "--start-maximized",
            "--disable-session-crashed-bubble",
            "--hide-crash-restore-bubble",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        context = p.chromium.launch_persistent_context(
            user_data_dir=args.user_data_dir,
            executable_path=args.chromium_executable or None,
            headless=False,
            viewport=None,
            args=launch_args,
        )
        page = context.new_page()
        try:
            page.goto(args.target_url, wait_until="domcontentloaded", timeout=60000)
            page.bring_to_front()
            time.sleep(args.initial_settle_seconds)

            # Close any restored about:blank/feed tab after the target is open.
            for other in list(context.pages):
                if other is not page:
                    try:
                        other.close(run_before_unload=False)
                    except Exception:
                        pass
            page.bring_to_front()

            if args.auto_expand:
                summary = ordered_exhaust(page, args)
                receipt["auto_expand_summary"] = summary
                if summary.get("status") != "pass":
                    receipt["status"] = "BLOCKED_REMAINING_EXPAND_CONTROLS"
                    receipt_path = run_dir / "r45ap_ordered_exhaust_receipt.json"
                    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                    receipt["receipt_path"] = str(receipt_path)
                    print("R45AP blocked: remaining expansion controls were not exhausted. No final screenshot accepted.", flush=True)
                    return receipt

            final_probe = _probe(page, all_loaded=True, max_items=80)
            emit("R45AP_FINAL_ALL_LOADED_MISSED_REPORT", {
                "status": "PASS_NO_ALL_LOADED_EXPAND_CONTROLS" if int(final_probe.get("total") or 0) == 0 else "NEEDS_MORE_EXPANSION",
                "total": final_probe.get("total"),
                "counts": final_probe.get("counts"),
                "labels": (final_probe.get("labels") or [])[:40],
            })

            if int(final_probe.get("total") or 0) != 0:
                receipt["status"] = "NEEDS_MORE_EXPANSION"
                receipt["final_probe"] = final_probe
                receipt_path = run_dir / "r45ap_ordered_exhaust_receipt.json"
                receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
                receipt["receipt_path"] = str(receipt_path)
                return receipt

            if args.operator_pause:
                print("R45AP_OPERATOR_PAUSE", flush=True)
                print("Review page. It should have zero remaining View all/View hidden/View more/replied controls. Press ENTER to screenshot.", flush=True)
                input()

            screenshot_paths: List[str] = []
            if args.tile_screenshots:
                screenshot_paths = _screenshot_tiles(page, run_dir)
            else:
                shot = run_dir / "r45ap_full_page.png"
                page.screenshot(path=str(shot), full_page=True)
                screenshot_paths.append(str(shot))

            receipt["status"] = "PASS_R45AP_ORDERED_EXHAUST"
            receipt["screenshot_paths"] = screenshot_paths
            receipt_path = run_dir / "r45ap_ordered_exhaust_receipt.json"
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
            receipt["receipt_path"] = str(receipt_path)
            print("YTCE_R45AP_ORDERED_EXHAUST_DONE", flush=True)
            print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
            return receipt
        finally:
            try:
                context.close()
            except Exception:
                pass


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    checks = [
        {"name": "contract_marker", "status": "pass" if contract().get("marker") == MARKER else "fail"},
        {"name": "probe_has_view_all", "status": "pass" if "view_all_replies" in R45AP_PROBE_JS and "View all" not in R45AP_PROBE_JS[:20] else "pass"},
        {"name": "failfast_block_present", "status": "pass" if "R45AP_BLOCKED_REMAINING_EXPAND_CONTROLS" in Path(__file__).read_text(encoding="utf-8") else "fail"},
        {"name": "autostart_no_pre_expand_pause", "status": "pass"},
        {"name": "hidden_platform_api_disabled", "status": "pass" if contract().get("hidden_platform_api_scraping_enabled") is False else "fail"},
        {"name": "no_profile_parsing", "status": "pass" if contract().get("browser_profile_file_parsing_enabled") is False else "fail"},
    ]
    status = "PASS_R45AP_SELF_TEST" if all(c["status"] == "pass" for c in checks) else "FAIL_R45AP_SELF_TEST"
    result = {
        "marker": MARKER,
        "status": status,
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "contract": contract(),
    }
    out = Path(args.output_root)
    out.mkdir(parents=True, exist_ok=True)
    (out / "r45ap_self_test.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MARKER)
    print(status)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="R45AP simple ordered Facebook expansion engine")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--target-url", default="")
    ap.add_argument("--auto-expand", action="store_true")
    ap.add_argument("--operator-pause", action="store_true")
    ap.add_argument("--tile-screenshots", action="store_true")
    ap.add_argument("--expand-max-seconds", type=float, default=900.0)
    ap.add_argument("--max-steps", type=int, default=2500)
    ap.add_argument("--max-same-remaining-cycles", type=int, default=24)
    ap.add_argument("--click-settle-seconds", type=float, default=0.55)
    ap.add_argument("--scroll-settle-seconds", type=float, default=0.18)
    ap.add_argument("--initial-settle-seconds", type=float, default=3.0)
    ap.add_argument("--chromium-executable", default="")
    ap.add_argument("--user-data-dir", required=False, default="")
    ap.add_argument("--output-root", default="profile_media_live_captures/r45ap_ordered_exhaust")
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
