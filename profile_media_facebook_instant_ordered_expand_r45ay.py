#!/usr/bin/env python3
"""R45AY instant ordered Facebook visible-page expansion runner.

This is a practical fast runner, separate from the cautious R45AX diagnostic
runner. It stays visible-page-only: no Facebook/Graph APIs, no cookies/tokens,
no browser profile parsing/copying, no login automation, and no challenge bypass.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from profile_media_facebook_progress_gated_modal_flatten_r45ax import (
    EXPAND_PATTERNS_JS,
    clean_target_url,
    expected_story,
    import_playwright,
    r45ax_active_window_keepalive,
    r45ax_filter_expected_progress,
    r45ax_foreground_keepalive,
    r45ax_progress_gate_ok,
    r45ax_target_guard_now,
)

MARKER = "YTCE_R45AY_INSTANT_ORDERED_EXPAND"
SCHEMA_VERSION = "facebook_instant_ordered_expand.r45ay.v1"

CHROMIUM_THROTTLE_FLAGS = [
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling",
    "--start-maximized",
    "--no-default-browser-check",
    "--disable-notifications",
]

R45AY_ENGINE_JS = r"""
function r45ayPriority(category, label){
  const c = String(category || '');
  if (c === 'view_hidden' && /comments/i.test(String(label || ''))) return 1;
  if (c === 'view_hidden') return 2;
  if (c === 'view_all_replies') return 3;
  if (c === 'view_n_replies') return 4;
  if (c === 'replied_bucket') return 5;
  if (c === 'view_more_replies') return 6;
  return 99;
}
function r45ayAllowedCategory(category, includeGuardedViewMore){
  const c = String(category || '');
  if (['view_hidden','view_all_replies','view_n_replies','replied_bucket'].includes(c)) return true;
  return !!includeGuardedViewMore && c === 'view_more_replies';
}
function r45ayScanOrdered(opts){
  opts = opts || {};
  const includeGuardedViewMore = !!opts.includeGuardedViewMore;
  const maxCandidates = Math.max(1, Math.min(80, parseInt(opts.maxCandidates || 50, 10) || 50));
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_active_scroller'};
  const scanStart = performance.now();
  const raw = r45axTextCandidates(scroller).filter(item => {
    if (!item || !item.safe) return false;
    if (!r45ayAllowedCategory(item.category, includeGuardedViewMore)) return false;
    const label = r45axNorm(item.label || '');
    if (/^(Like|Reply|GIF|Photo|Camera|Upload|Share|React)$/i.test(label)) return false;
    return true;
  });
  const items = raw.map(item => ({
    label:item.label,
    category:item.category,
    key:item.key || '',
    x:item.x,
    y:item.y,
    top:item.top,
    bottom:item.bottom,
    left:item.left,
    right:item.right,
    source:item.source || '',
    priority:r45ayPriority(item.category, item.label),
    firstSeenPerformanceNow:scanStart,
    safety:item.safety || null
  })).sort((a,b) => (a.priority - b.priority) || (b.y - a.y) || (a.x - b.x)).slice(0, maxCandidates);
  const counts = {};
  for (const item of items) counts[item.category] = (counts[item.category] || 0) + 1;
  return {
    ok:true,
    marker:'R45AY_ORDERED_SCAN',
    scanPerformanceNow:scanStart,
    scanDurationMs:Math.round((performance.now() - scanStart) * 100) / 100,
    candidateCount:items.length,
    counts,
    items,
    progress:r45axProgressFromPage(),
    expectedTotalEvidence: opts.expectedTotal ? r45axExpectedTotalEvidence(opts.expectedTotal) : null,
    scroller:{
      scrollTop:scroller.scrollTop || 0,
      scrollHeight:scroller.scrollHeight || 0,
      clientHeight:scroller.clientHeight || 0,
      atBottom:(scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8)
    }
  };
}
function r45ayScroll(mode){
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_active_scroller'};
  const before = scroller.scrollTop || 0;
  const ch = scroller.clientHeight || 700;
  if (mode === 'top') scroller.scrollTop = 0;
  else if (mode === 'bottom') scroller.scrollTop = scroller.scrollHeight || before;
  else if (mode === 'small_up') scroller.scrollTop = Math.max(0, before - Math.max(160, Math.floor(ch * 0.25)));
  else if (mode === 'bottom_chain_nudge') scroller.scrollTop = Math.max(0, (scroller.scrollHeight || 0) - ch - 80);
  else scroller.scrollTop = before + Math.max(900, Math.floor(ch * 1.55));
  return {ok:true, mode, before, after:scroller.scrollTop || 0, scrollHeight:scroller.scrollHeight || 0, clientHeight:ch, atBottom:(scroller.scrollTop + ch >= scroller.scrollHeight - 8)};
}
function r45aySyntheticStats(){
  return {
    safeClicks: window.__R45AY_SYNTHETIC_SAFE_CLICKS__ || 0,
    decoyClicks: window.__R45AY_SYNTHETIC_DECOY_CLICKS__ || 0,
    controlsRemaining: document.querySelectorAll('[data-r45ay-safe="1"]').length
  };
}
"""

SYNTHETIC_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>R45AY synthetic instant audit</title>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#f0f2f5}
#modal{height:680px;width:760px;margin:24px auto;overflow:auto;background:#fff;border:1px solid #ccc;padding:20px}
.comment{padding:8px 10px;border-bottom:1px solid #eee}
.safe{display:block;margin:7px 0;color:#0866ff;font-weight:600;cursor:pointer}
.decoy{display:inline-block;margin:4px 10px 4px 0;color:#65676b;cursor:pointer}
.revealed{background:#eef6ff}
</style>
</head>
<body>
<div id="modal" role="dialog" aria-label="Comments">
<div>1 of 715</div>
<div>Like Reply</div>
<a class="decoy" href="https://www.facebook.com/profile.php?id=123">Profile link</a>
<button class="decoy" data-decoy="like">Like</button>
<button class="decoy" data-decoy="reply">Reply</button>
<button class="decoy" data-decoy="gif">GIF</button>
<div id="controls"></div>
<div style="height:900px">Synthetic lower comment history Like Reply</div>
</div>
<script>
window.__R45AY_SYNTHETIC_SAFE_CLICKS__ = 0;
window.__R45AY_SYNTHETIC_DECOY_CLICKS__ = 0;
const labels = [
  "View hidden comments","View hidden replies","View all 12 replies","View 5 replies","replied · 168 replies",
  "View hidden comments","View hidden replies","View all 9 replies","View 3 replies","replied · 14 replies",
  "View hidden comments","View hidden replies","View all 7 replies","View 2 replies","replied · 6 replies"
];
const controls = document.getElementById('controls');
function addControl(label, i){
  const b = document.createElement('div');
  b.className = 'safe';
  b.setAttribute('role','button');
  b.setAttribute('tabindex','0');
  b.setAttribute('data-r45ay-safe','1');
  b.textContent = label;
  b.addEventListener('click', () => {
    window.__R45AY_SYNTHETIC_SAFE_CLICKS__ += 1;
    b.remove();
    const d = document.createElement('div');
    d.className = 'comment revealed';
    d.textContent = 'Materialized comment row ' + i;
    controls.appendChild(d);
  });
  controls.appendChild(b);
}
labels.forEach(addControl);
for (const el of document.querySelectorAll('[data-decoy], .decoy')) {
  el.addEventListener('click', (ev) => {
    window.__R45AY_SYNTHETIC_DECOY_CLICKS__ += 1;
    ev.preventDefault();
  });
}
</script>
</body>
</html>"""


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log(marker: str, data: Any = None) -> None:
    print(marker if data is None else marker + " " + json.dumps(data, ensure_ascii=True, sort_keys=True), flush=True)


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * pct / 100.0
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(ordered[lo])
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo))


def timing_summary(click_timings: List[Dict[str, Any]]) -> Dict[str, Any]:
    gaps = [
        float(click_timings[i]["dispatch_perf_ms"]) - float(click_timings[i - 1]["dispatch_perf_ms"])
        for i in range(1, len(click_timings))
    ]
    latencies = [
        float(item["browser_dispatch_perf_ms"]) - float(item.get("candidate_first_seen_perf_ms") or item["browser_dispatch_perf_ms"])
        for item in click_timings
    ]
    return {
        "click_count": len(click_timings),
        "median_inter_click_gap_ms": round(statistics.median(gaps), 3) if gaps else 0.0,
        "p95_inter_click_gap_ms": round(percentile(gaps, 95), 3) if gaps else 0.0,
        "candidate_to_click_median_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "max_inter_click_gap_ms": round(max(gaps), 3) if gaps else 0.0,
    }


async def install_engine(page) -> None:
    install_js = """() => {
""" + EXPAND_PATTERNS_JS + "\n" + R45AY_ENGINE_JS + """
window.r45axFindScroller = r45axFindScroller;
window.r45axGetScroller = r45axGetScroller;
window.r45axClickSafetyAt = r45axClickSafetyAt;
window.r45axScanVisible = r45axScanVisible;
window.r45axExpectedTotalEvidence = r45axExpectedTotalEvidence;
window.r45axPageProgress = r45axPageProgress;
window.r45axFlattenForScreenshot = r45axFlattenForScreenshot;
window.r45axInstallNavBlocker = r45axInstallNavBlocker;
window.r45ayScanOrdered = r45ayScanOrdered;
window.r45ayScroll = r45ayScroll;
window.r45aySyntheticStats = r45aySyntheticStats;
return window.r45axInstallNavBlocker();
}"""
    await page.evaluate(install_js)


async def write_failure_artifacts(page, run_dir: Path, prefix: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    html_path = run_dir / f"{prefix}_page.html"
    text_path = run_dir / f"{prefix}_text.txt"
    png_path = run_dir / f"{prefix}_viewport.png"
    try:
        html_path.write_text(await page.content(), encoding="utf-8")
        out["html_path"] = str(html_path)
    except Exception as e:
        out["html_error"] = repr(e)
    try:
        text_path.write_text(await page.evaluate("document.body ? (document.body.innerText || '') : ''"), encoding="utf-8")
        out["text_path"] = str(text_path)
    except Exception as e:
        out["text_error"] = repr(e)
    try:
        await page.screenshot(path=str(png_path), full_page=False, timeout=45000)
        out["screenshot_path"] = str(png_path)
    except Exception as e:
        out["screenshot_error"] = repr(e)
    return out


async def cdp_ordered_burst(
    page,
    cdp_session: Any,
    scan: Dict[str, Any],
    *,
    max_clicks: int,
    inter_click_delay_ms: int,
    settle_ms: int,
    debug_clicks: bool = False,
) -> Dict[str, Any]:
    items = list((scan or {}).get("items") or [])[:max(1, min(60, max_clicks))]
    if not items:
        return {"ok": False, "reason": "no_candidates", "clicked": 0, "items": []}
    before_perf = time.perf_counter()
    payload = [
        {
            "index": index,
            "label": item.get("label"),
            "category": item.get("category"),
            "key": item.get("key"),
            "x": float(item.get("x") or 0),
            "y": float(item.get("y") or 0),
            "candidate_first_seen_perf_ms": float(item.get("firstSeenPerformanceNow") or 0),
        }
        for index, item in enumerate(items)
    ]
    dispatch = await page.evaluate(
        """(payload) => {
          const scroller = r45axGetScroller();
          if (!scroller) return {ok:false, reason:'no_active_scroller', clicked:0, click_timings:[], items:[]};
          const clicked = [];
          const timings = [];
          const rejected = [];
          const started = performance.now();
          for (const item of payload) {
            const x = Number(item.x), y = Number(item.y);
            const safety = r45axClickSafetyAt(x, y);
            const hit = document.elementFromPoint(x, y);
            if (!safety.ok || !hit || !scroller.contains(hit)) {
              rejected.push({label:item.label, category:item.category, key:item.key, x, y, safety, hitTag:hit && hit.tagName || '', inside:!!(hit && scroller.contains(hit))});
              continue;
            }
            let target = hit.closest && hit.closest('a, button, [role="button"], [tabindex], span, div');
            if (!target || !scroller.contains(target)) target = hit;
            const opts = {bubbles:true, cancelable:true, view:window, clientX:x, clientY:y, button:0, buttons:1};
            const dispatchNow = performance.now();
            try {
              try { target.dispatchEvent(new PointerEvent('pointerdown', {...opts, pointerId:1, pointerType:'mouse', isPrimary:true})); } catch(e) {}
              target.dispatchEvent(new MouseEvent('mousemove', opts));
              target.dispatchEvent(new MouseEvent('mousedown', opts));
              target.dispatchEvent(new MouseEvent('mouseup', {...opts, buttons:0}));
              try { target.dispatchEvent(new PointerEvent('pointerup', {...opts, buttons:0, pointerId:1, pointerType:'mouse', isPrimary:true})); } catch(e) {}
              target.dispatchEvent(new MouseEvent('click', {...opts, buttons:0}));
              clicked.push({label:item.label, category:item.category, key:item.key, x:Math.round(x), y:Math.round(y)});
              timings.push({
                index:item.index,
                label:item.label,
                category:item.category,
                key:item.key,
                x:Math.round(x),
                y:Math.round(y),
                candidate_first_seen_perf_ms:item.candidate_first_seen_perf_ms || started,
                browser_dispatch_perf_ms:Math.round(dispatchNow * 1000) / 1000,
                dispatch_perf_ms:Math.round((dispatchNow - started) * 1000) / 1000
              });
            } catch(e) {
              rejected.push({label:item.label, category:item.category, key:item.key, x, y, reason:'dispatch_failed', error:String(e)});
            }
          }
          return {ok:true, method:'in_page_pointer_mouse_event_burst', started, elapsed_ms:Math.round((performance.now() - started) * 1000) / 1000, clicked:clicked.length, items:clicked, click_timings:timings, rejected};
        }""",
        payload,
    )
    click_timings = list((dispatch or {}).get("click_timings") or [])
    clicked_items = list((dispatch or {}).get("items") or [])
    if debug_clicks:
        for timing in click_timings:
            log("R45AY_AUDIT_CLICK_GAP", timing)
    burst_elapsed_ms = round((time.perf_counter() - before_perf) * 1000.0, 3)
    if settle_ms > 0:
        await page.wait_for_timeout(settle_ms)
    after = await page.evaluate("r45ayScanOrdered({maxCandidates:60})")
    return {
        "ok": True,
        "method": (dispatch or {}).get("method") or "in_page_pointer_mouse_event_burst",
        "candidate_count": len(items),
        "clicked": len(clicked_items),
        "items": clicked_items,
        "click_timings": click_timings,
        "timing": timing_summary(click_timings),
        "burst_elapsed_ms": burst_elapsed_ms,
        "browser_burst_elapsed_ms": (dispatch or {}).get("elapsed_ms"),
        "settle_ms": settle_ms,
        "rejected": (dispatch or {}).get("rejected") or [],
        "after_scan": after,
        "progress_before": scan.get("progress"),
        "progress_after": (after or {}).get("progress"),
        "scroll_height_before": ((scan or {}).get("scroller") or {}).get("scrollHeight"),
        "scroll_height_after": (((after or {}).get("scroller") or {}).get("scrollHeight")),
    }


async def synthetic_instant_audit(output_root: Path) -> Tuple[int, Dict[str, Any]]:
    run_dir = output_root / ("r45ay_synthetic_instant_audit_" + now_stamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    receipt: Dict[str, Any] = {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "mode": "synthetic_instant_audit",
        "run_dir": str(run_dir),
        "checks": [],
    }
    async_playwright = await import_playwright()
    async with async_playwright() as p:
        launch_kwargs: Dict[str, Any] = {"headless": True, "args": CHROMIUM_THROTTLE_FLAGS}
        chromium_path = Path(r"C:\Users\fahad\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe")
        if chromium_path.exists():
            launch_kwargs["executable_path"] = str(chromium_path)
        browser = await p.chromium.launch(**launch_kwargs)
        page = await browser.new_page(viewport={"width": 1100, "height": 760})
        await page.set_content(SYNTHETIC_HTML, wait_until="domcontentloaded")
        await install_engine(page)
        cdp = await page.context.new_cdp_session(page)
        scan = await page.evaluate("r45ayScanOrdered({maxCandidates:50})")
        log("R45AY_AUDIT_START", {"mode": "synthetic", "candidate_count": scan.get("candidateCount"), "counts": scan.get("counts")})
        burst = await cdp_ordered_burst(page, cdp, scan, max_clicks=30, inter_click_delay_ms=0, settle_ms=75)
        stats = await page.evaluate("r45aySyntheticStats()")
        await browser.close()
    timing = burst.get("timing") or {}
    checks = [
        {"name": "median_inter_click_gap_le_25ms", "status": "pass" if timing.get("median_inter_click_gap_ms", 999) <= 25 else "fail"},
        {"name": "p95_inter_click_gap_le_75ms", "status": "pass" if timing.get("p95_inter_click_gap_ms", 999) <= 75 else "fail"},
        {"name": "candidate_to_click_median_le_50ms", "status": "pass" if timing.get("candidate_to_click_median_ms", 999) <= 50 else "fail"},
        {"name": "ten_plus_visible_controls_clicked_in_one_burst", "status": "pass" if burst.get("clicked", 0) >= 10 else "fail"},
        {"name": "no_unsafe_decoy_clicks", "status": "pass" if stats.get("decoyClicks") == 0 else "fail"},
        {"name": "one_settle_per_burst", "status": "pass" if burst.get("settle_ms") == 75 else "fail"},
    ]
    status = "PASS_R45AY_INSTANT_SYNTHETIC_AUDIT" if all(c["status"] == "pass" for c in checks) else "FAIL_R45AY_INSTANT_SYNTHETIC_AUDIT"
    receipt.update({"status": status, "checks": checks, "burst": burst, "synthetic_stats": stats})
    (run_dir / "r45ay_synthetic_audit_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    log("R45AY_AUDIT_SYNTHETIC_RESULT", {"status": status, "timing": timing, "clicked": burst.get("clicked"), "decoy_clicks": stats.get("decoyClicks")})
    log("R45AY_AUDIT_PASS" if status.startswith("PASS") else "R45AY_AUDIT_FAIL", receipt)
    return (0 if status.startswith("PASS") else 1), receipt


async def flatten_and_capture(page, run_dir: Path, max_band_height: int) -> Dict[str, Any]:
    live_html_path = run_dir / "r45ay_live_before_flatten.html"
    live_text_path = run_dir / "r45ay_live_before_flatten_text.txt"
    live_html_path.write_text(await page.content(), encoding="utf-8")
    live_text_path.write_text(await page.evaluate("document.body ? (document.body.innerText || '') : ''"), encoding="utf-8")
    flatten = await page.evaluate("r45axFlattenForScreenshot()")
    await page.wait_for_timeout(800)
    dims = await page.evaluate(
        """() => {
          const page = document.querySelector('#r45ax-page') || document.body;
          const r = page.getBoundingClientRect();
          return {x:Math.max(0, Math.floor(r.x)), y:0, width:Math.ceil(Math.max(r.width, 800)), height:Math.ceil(document.documentElement.scrollHeight || document.body.scrollHeight || r.height)};
        }"""
    )
    width = max(600, min(1400, int(dims.get("width") or 1000)))
    height = max(1, int(dims.get("height") or 1))
    band_h = max(600, min(int(max_band_height or 30000), height))
    paths: List[str] = []
    y = 0
    band = 1
    while y < height:
        h = min(band_h, height - y)
        path = run_dir / f"r45ay_comments_band_{band:03d}.png"
        await page.screenshot(path=str(path), clip={"x": int(dims.get("x", 0)), "y": y, "width": width, "height": h}, timeout=120000)
        paths.append(str(path))
        y += h
        band += 1
    zip_path = run_dir / "r45ay_comments_capture.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for pth in [live_html_path, live_text_path, *[Path(p) for p in paths]]:
            zf.write(pth, pth.name)
    return {
        "flatten": flatten,
        "live_html_path": str(live_html_path),
        "live_text_path": str(live_text_path),
        "max_band_paths": paths,
        "zip_path": str(zip_path),
        "capture_height": height,
        "capture_width": width,
    }


async def run_live(args: argparse.Namespace) -> int:
    target_url = clean_target_url(args.target_url)
    story = expected_story(target_url)
    run_dir = Path(args.output_root) / ("r45ay_instant_ordered_expand_" + now_stamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    receipt: Dict[str, Any] = {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "mode": "real_visible_smoke" if args.instant_audit else "real_capture",
        "target_url": target_url,
        "expected_story": story,
        "run_dir": str(run_dir),
        "status": "RUNNING",
        "sweeps": [],
        "safety": {
            "hidden_facebook_api_enabled": False,
            "cookie_or_token_extraction_enabled": False,
            "browser_profile_parsing_enabled": False,
            "login_automation_enabled": False,
            "challenge_bypass_enabled": False,
        },
    }
    async_playwright = await import_playwright()
    async with async_playwright() as p:
        log("R45AY_START", {"target_url": target_url, "run_dir": str(run_dir), "instant_audit": bool(args.instant_audit)})
        log("R45AY_CHROMIUM_THROTTLE_FLAGS", {"args": CHROMIUM_THROTTLE_FLAGS})
        context = await p.chromium.launch_persistent_context(
            user_data_dir=args.user_data_dir,
            executable_path=args.chromium_executable or None,
            headless=False,
            args=CHROMIUM_THROTTLE_FLAGS,
            viewport=None,
            accept_downloads=False,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        if args.keep_page_foreground:
            log("R45AY_FOREGROUND_KEEPALIVE", await r45ax_foreground_keepalive(page, "startup", "before_goto"))
            log("R45AY_ACTIVE_WINDOW_KEEPALIVE", r45ax_active_window_keepalive("Facebook"))
        await page.goto(target_url, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(3000)
        if args.keep_page_foreground:
            log("R45AY_FOREGROUND_KEEPALIVE", await r45ax_foreground_keepalive(page, "startup", "after_goto"))
            log("R45AY_ACTIVE_WINDOW_KEEPALIVE", r45ax_active_window_keepalive(await page.title()))
        await install_engine(page)
        guard = await r45ax_target_guard_now(page, story)
        log("R45AY_TARGET_GUARD", guard)
        if not guard.get("ok"):
            receipt.update({"status": "BLOCKED_TARGET_GUARD", "target_guard": guard})
            receipt["failure_artifacts"] = await write_failure_artifacts(page, run_dir, "blocked_target_guard")
            (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
            await context.close()
            return 2
        scroller_info = await page.evaluate("r45axFindScroller()")
        log("R45AY_ACTIVE_SCROLL_CONTAINER", scroller_info)
        if not scroller_info.get("ok"):
            receipt.update({"status": "BLOCKED_NO_ACTIVE_COMMENTS_SCROLLER", "active_scroller": scroller_info})
            receipt["failure_artifacts"] = await write_failure_artifacts(page, run_dir, "blocked_no_active_comments_scroller")
            (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
            await context.close()
            return 3
        cdp = await context.new_cdp_session(page)
        clicked = 0
        burst_count = 0
        fallback_count = 0
        target_drift_count = 0
        inert_counts: Dict[str, int] = {}
        click_timings_all: List[Dict[str, Any]] = []
        start = time.monotonic()
        best_progress: Optional[Dict[str, Any]] = None
        empty_scans = 0
        max_steps = max(1, int(args.max_steps or 300))
        for sweep in range(1, max_steps + 1):
            elapsed = time.monotonic() - start
            if elapsed >= float(args.expand_max_seconds):
                break
            if args.keep_page_foreground and (sweep == 1 or sweep % 25 == 0):
                log("R45AY_FOREGROUND_KEEPALIVE", await r45ax_foreground_keepalive(page, sweep, "sweep_boundary"))
            guard = await r45ax_target_guard_now(page, story)
            if not guard.get("ok"):
                target_drift_count += 1
                receipt.update({"status": "BLOCKED_TARGET_DRIFT", "target_guard": guard})
                receipt["failure_artifacts"] = await write_failure_artifacts(page, run_dir, "blocked_target_drift")
                (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
                log("R45AY_BLOCKED", {"status": receipt["status"], "guard": guard})
                await context.close()
                return 4
            scan_t0 = time.perf_counter()
            scan = await page.evaluate(
                "(opts) => r45ayScanOrdered(opts)",
                {"maxCandidates": 50, "includeGuardedViewMore": bool(args.include_guarded_view_more), "expectedTotal": int(args.expected_total_comments or 0)},
            )
            scan_duration_ms = round((time.perf_counter() - scan_t0) * 1000.0, 3)
            raw_progress = scan.get("progress")
            progress = r45ax_filter_expected_progress(raw_progress, int(args.expected_total_comments or 0))
            if progress and ((not best_progress) or progress.get("current", 0) > best_progress.get("current", 0)):
                best_progress = progress
            if args.expected_total_comments and r45ax_progress_gate_ok(best_progress, int(args.expected_total_comments)):
                receipt["auto_expand_summary"] = {"status": "pass", "best_progress": best_progress, "clicked": clicked, "sweeps": sweep - 1}
                log("R45AY_DONE", receipt["auto_expand_summary"])
                break
            candidates = list(scan.get("items") or [])
            candidates = [c for c in candidates if inert_counts.get(str(c.get("key") or ""), 0) < 2]
            log("R45AY_SWEEP_START", {
                "sweep": sweep,
                "candidate_count": len(candidates),
                "counts": scan.get("counts"),
                "progress": progress or raw_progress,
                "scrollTop": ((scan.get("scroller") or {}).get("scrollTop")),
                "scrollHeight": ((scan.get("scroller") or {}).get("scrollHeight")),
                "elapsed_seconds": round(elapsed, 2),
            })
            if candidates:
                empty_scans = 0
                scan_for_burst = {**scan, "items": candidates}
                burst = await cdp_ordered_burst(
                    page,
                    cdp,
                    scan_for_burst,
                    max_clicks=int(args.max_burst_clicks or 30),
                    inter_click_delay_ms=int(args.inter_click_delay_ms or 0),
                    settle_ms=int(args.settle_ms or 125),
                    debug_clicks=bool(args.debug_clicks),
                )
                burst_count += 1
                clicked += int(burst.get("clicked") or 0)
                click_timings_all.extend(burst.get("click_timings") or [])
                materialized = (
                    json.dumps(burst.get("progress_before") or {}, sort_keys=True) != json.dumps(burst.get("progress_after") or {}, sort_keys=True)
                    or int(burst.get("scroll_height_after") or 0) > int(burst.get("scroll_height_before") or 0)
                    or int((((burst.get("after_scan") or {}).get("candidateCount")) or 0)) != len(candidates)
                )
                if not materialized:
                    for item in candidates[: max(1, int(burst.get("clicked") or 0))]:
                        key = str(item.get("key") or "")
                        if key:
                            inert_counts[key] = inert_counts.get(key, 0) + 1
                    if any(v >= 2 for v in inert_counts.values()):
                        log("R45AY_INERT_SKIP", {"sweep": sweep, "inert_key_count": sum(1 for v in inert_counts.values() if v >= 2)})
                else:
                    for item in candidates:
                        inert_counts.pop(str(item.get("key") or ""), None)
                timing = burst.get("timing") or {}
                clicks_per_minute = round(clicked / max((time.monotonic() - start) / 60.0, 0.001), 2)
                log("R45AY_SWEEP_CLICKED", {
                    "sweep": sweep,
                    "candidate_count": len(candidates),
                    "clicked": burst.get("clicked"),
                    "label_summary": [x.get("label") for x in (burst.get("items") or [])[:12]],
                    "burst_elapsed_ms": burst.get("burst_elapsed_ms"),
                    "settle_ms": burst.get("settle_ms"),
                    "median_inter_click_gap_ms": timing.get("median_inter_click_gap_ms"),
                    "p95_inter_click_gap_ms": timing.get("p95_inter_click_gap_ms"),
                    "candidate_to_click_median_ms": timing.get("candidate_to_click_median_ms"),
                    "progress_before": burst.get("progress_before"),
                    "progress_after": burst.get("progress_after"),
                    "clicks_per_minute": clicks_per_minute,
                    "fallback_count": fallback_count,
                })
                receipt["sweeps"].append({"sweep": sweep, "clicked": burst.get("clicked"), "timing": timing, "progress_after": burst.get("progress_after")})
                continue
            empty_scans += 1
            scroll_mode = "bottom_chain_nudge" if (best_progress and best_progress.get("current", 0) >= max(1, int(args.expected_total_comments or 0) - 40)) else "down"
            scroll = await page.evaluate("(mode) => r45ayScroll(mode)", scroll_mode)
            log("R45AY_SCROLL", {"sweep": sweep, "mode": scroll_mode, "scroll": scroll, "empty_scans": empty_scans, "scan_duration_ms": scan_duration_ms})
            await page.wait_for_timeout(80 if empty_scans < 3 else 180)
            if empty_scans >= int(args.progress_stall_cycles or 3) and (scroll or {}).get("atBottom"):
                break
        if "auto_expand_summary" not in receipt:
            final_scan = await page.evaluate(
                "(opts) => r45ayScanOrdered(opts)",
                {"maxCandidates": 50, "includeGuardedViewMore": bool(args.include_guarded_view_more), "expectedTotal": int(args.expected_total_comments or 0)},
            )
            status = "BLOCKED_R45AY_EXPECTED_TOTAL_UNSATISFIED"
            receipt.update({
                "status": status,
                "best_progress": best_progress,
                "final_scan": final_scan,
                "clicked": clicked,
                "burst_count": burst_count,
                "fallback_count": fallback_count,
                "target_drift_count": target_drift_count,
                "timing": timing_summary(click_timings_all),
                "failure_artifacts": await write_failure_artifacts(page, run_dir, status.lower()),
            })
            log("R45AY_BLOCKED", {"status": status, "best_progress": best_progress, "clicked": clicked, "burst_count": burst_count, "timing": receipt["timing"], "failure_artifacts": receipt["failure_artifacts"]})
            (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
            await context.close()
            return 5 if not args.instant_audit else 0
        outputs = await flatten_and_capture(page, run_dir, int(args.max_band_height or 30000))
        receipt.update({
            "status": "PASS_R45AY_INSTANT_ORDERED_CAPTURE",
            "clicked": clicked,
            "burst_count": burst_count,
            "fallback_count": fallback_count,
            "target_drift_count": target_drift_count,
            "timing": timing_summary(click_timings_all),
            "outputs": outputs,
        })
        (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
        log("R45AY_DONE", {"status": receipt["status"], "clicked": clicked, "burst_count": burst_count, "timing": receipt["timing"], "zip_path": outputs.get("zip_path")})
        await context.close()
        return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="R45AY instant ordered Facebook visible-page expansion runner")
    ap.add_argument("--target-url", default="")
    ap.add_argument("--auto-expand", action="store_true", default=True)
    ap.add_argument("--tile-screenshots", action="store_true")
    ap.add_argument("--expand-max-seconds", type=float, default=3600)
    ap.add_argument("--max-steps", type=int, default=5000)
    ap.add_argument("--max-audit-passes", type=int, default=20)
    ap.add_argument("--progress-stall-cycles", type=int, default=3)
    ap.add_argument("--expected-total-comments", type=int, default=0)
    ap.add_argument("--max-band-height", type=int, default=30000)
    ap.add_argument("--chromium-executable", default="")
    ap.add_argument("--user-data-dir", default="")
    ap.add_argument("--output-root", default="profile_media_live_captures/r45ay_instant_ordered_expand")
    ap.add_argument("--keep-page-foreground", dest="keep_page_foreground", action="store_true", default=True)
    ap.add_argument("--no-keep-page-foreground", dest="keep_page_foreground", action="store_false")
    ap.add_argument("--instant-audit", action="store_true")
    ap.add_argument("--debug-clicks", action="store_true")
    ap.add_argument("--include-guarded-view-more", action="store_true")
    ap.add_argument("--max-burst-clicks", type=int, default=30)
    ap.add_argument("--inter-click-delay-ms", type=int, default=0)
    ap.add_argument("--settle-ms", type=int, default=125)
    return ap.parse_args(argv)


async def amain(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.instant_audit and not args.target_url:
        code, _receipt = await synthetic_instant_audit(Path(args.output_root))
        return code
    if not args.target_url:
        print("R45AY requires --target-url unless --instant-audit synthetic mode is used.", flush=True)
        return 2
    return await run_live(args)


def main() -> None:
    raise SystemExit(asyncio.run(amain()))


if __name__ == "__main__":
    main()
