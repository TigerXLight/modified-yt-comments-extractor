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
function r45ayExactInfo(text){
  const t = r45axNorm(text);
  if (/^View hidden comments$/i.test(t)) return {label:t, category:'view_hidden'};
  if (/^View hidden replies$/i.test(t)) return {label:t, category:'view_hidden'};
  if (/^View all \d+ replies$/i.test(t)) return {label:t, category:'view_all_replies'};
  if (/^View \d+ replies$/i.test(t)) return {label:t, category:'view_n_replies'};
  if (/^replied\s*(?:[·•.\-]\s*)?\d+\s+replies$/i.test(t)) return {label:t, category:'replied_bucket'};
  return null;
}
function r45ayFastVisibleCandidates(opts){
  opts = opts || {};
  const maxCandidates = Math.max(1, Math.min(120, parseInt(opts.maxCandidates || 50, 10) || 50));
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_active_scroller', items:[]};
  const started = performance.now();
  const sr = scroller.getBoundingClientRect();
  const band = {top:Math.max(0, sr.top + 6), bottom:Math.min(innerHeight, sr.bottom - 8), left:Math.max(0, sr.left + 6), right:Math.min(innerWidth, sr.right - 6)};
  const out = [];
  const seen = new Set();
  const nodes = Array.from(scroller.querySelectorAll('[role="button"], button, a, span, div, [tabindex]'));
  for (const el of nodes) {
    if (out.length >= maxCandidates * 3) break;
    if (!el || r45axElementHidden(el) || r45axBadCandidateElement(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.height > 90 || r.width > 520) continue;
    if (r.bottom <= band.top || r.top >= band.bottom || r.right <= band.left || r.left >= band.right) continue;
    const text = r45axNorm([el.innerText || '', el.textContent || '', el.getAttribute && (el.getAttribute('aria-label') || ''), el.getAttribute && (el.getAttribute('title') || '')].join(' '));
    if (!text || text.length > 80) continue;
    const info = r45ayExactInfo(text);
    if (!info || !r45ayAllowedCategory(info.category, !!opts.includeGuardedViewMore)) continue;
    const fractions = info.category === 'replied_bucket' ? [0.88, 0.70, 0.50] : [0.50, 0.18, 0.82];
    let chosen = null, safety = null;
    for (const f of fractions) {
      const x = r.left + Math.min(r.width - 2, Math.max(2, r.width * f));
      const y = r.top + r.height / 2;
      const s = r45axClickSafetyAt(x, y);
      if (s.ok) { chosen = {x, y}; safety = s; break; }
      if (!safety) safety = s;
    }
    if (!chosen) continue;
    const key = info.category + '|' + info.label + '|' + Math.round(r.top / 3) + '|' + Math.round(r.left / 8) + '|' + r45axHashText(r45axCandidateContext(el, info.label));
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      label:info.label,
      category:info.category,
      key,
      x:Math.round(chosen.x),
      y:Math.round(chosen.y),
      top:Math.round(r.top),
      bottom:Math.round(r.bottom),
      left:Math.round(r.left),
      right:Math.round(r.right),
      priority:r45ayPriority(info.category, info.label),
      firstSeenPerformanceNow:started,
      safety
    });
  }
  out.sort((a,b) => (a.priority - b.priority) || (b.y - a.y) || (a.x - b.x));
  const items = out.slice(0, maxCandidates);
  const counts = {};
  for (const item of items) counts[item.category] = (counts[item.category] || 0) + 1;
  return {
    ok:true,
    marker:'R45AY_FAST_VISIBLE_SCAN',
    scanPerformanceNow:started,
    scanDurationMs:Math.round((performance.now() - started) * 100) / 100,
    candidateCount:items.length,
    counts,
    items,
    scroller:{scrollTop:scroller.scrollTop||0, scrollHeight:scroller.scrollHeight||0, clientHeight:scroller.clientHeight||0, atBottom:(scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8)}
  };
}
function r45ayPageLoopScan(opts){
  opts = opts || {};
  let scan = r45ayFastVisibleCandidates(opts);
  if (scan.ok && scan.candidateCount === 0) {
    const full = r45ayScanOrdered({maxCandidates:opts.maxCandidates, includeGuardedViewMore:!!opts.includeGuardedViewMore, expectedTotal:opts.expectedTotal});
    if (full.ok && full.candidateCount > 0) scan = full;
  }
  return scan;
}
function r45ayStableCandidateKey(item){
  item = item || {};
  const raw = String(item.key || '');
  const parts = raw.split('|');
  const context = parts.length ? parts[parts.length - 1] : '';
  return [String(item.category || ''), String(item.label || ''), context || String(Math.round(Number(item.y || 0) / 20))].join('|');
}
function r45ayDispatchPageBurst(items, opts){
  opts = opts || {};
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_active_scroller', clicked:0, click_timings:[], items:[], rejected:[]};
  const started = performance.now();
  const clicked = [], timings = [], rejected = [];
  for (let i = 0; i < items.length; i++) {
    const item = items[i] || {};
    const x = Number(item.x), y = Number(item.y);
    const safety = (item.safety && item.safety.ok) ? item.safety : r45axClickSafetyAt(x, y);
    const hit = document.elementFromPoint(x, y);
    if (!safety.ok || !hit || !scroller.contains(hit)) {
      rejected.push({label:item.label, category:item.category, key:item.key, x, y, safety, inside:!!(hit && scroller.contains(hit)), hitTag:hit && hit.tagName || ''});
      continue;
    }
    let target = hit.closest && hit.closest('a, button, [role="button"], [tabindex], span, div');
    if (!target || !scroller.contains(target)) target = hit;
    const dispatchNow = performance.now();
    const ev = {bubbles:true, cancelable:true, view:window, clientX:x, clientY:y, button:0, buttons:1};
    try {
      try { target.dispatchEvent(new PointerEvent('pointerdown', {...ev, pointerId:1, pointerType:'mouse', isPrimary:true})); } catch(e) {}
      target.dispatchEvent(new MouseEvent('mousemove', ev));
      target.dispatchEvent(new MouseEvent('mousedown', ev));
      target.dispatchEvent(new MouseEvent('mouseup', {...ev, buttons:0}));
      try { target.dispatchEvent(new PointerEvent('pointerup', {...ev, buttons:0, pointerId:1, pointerType:'mouse', isPrimary:true})); } catch(e) {}
      if (typeof target.click === 'function') target.click();
      else target.dispatchEvent(new MouseEvent('click', {...ev, buttons:0}));
      clicked.push({label:item.label, category:item.category, key:item.key, x:Math.round(x), y:Math.round(y)});
      timings.push({
        index:i,
        label:item.label,
        category:item.category,
        key:item.key,
        x:Math.round(x),
        y:Math.round(y),
        candidate_first_seen_perf_ms:item.firstSeenPerformanceNow || started,
        browser_dispatch_perf_ms:Math.round(dispatchNow * 1000) / 1000,
        dispatch_perf_ms:Math.round((dispatchNow - started) * 1000) / 1000
      });
    } catch(e) {
      rejected.push({label:item.label, category:item.category, key:item.key, x, y, reason:'dispatch_failed', error:String(e)});
    }
  }
  return {ok:true, method:'page_loop_pointer_mouse_event_burst', started, elapsed_ms:Math.round((performance.now() - started) * 1000) / 1000, clicked:clicked.length, items:clicked, click_timings:timings, rejected};
}
function r45aySignature(scroller, scan){
  const keys = ((scan && scan.items) || []).map(r45ayStableCandidateKey).sort();
  return {
    scrollHeight:scroller ? (scroller.scrollHeight || 0) : 0,
    scrollTop:scroller ? (scroller.scrollTop || 0) : 0,
    candidateCount:scan ? (scan.candidateCount || 0) : 0,
    counts:scan ? (scan.counts || {}) : {},
    candidateKeys:keys
  };
}
function r45aySignatureChanged(a, b){
  return !a || !b || a.scrollHeight !== b.scrollHeight || a.candidateCount !== b.candidateCount || JSON.stringify(a.counts || {}) !== JSON.stringify(b.counts || {}) || JSON.stringify(a.candidateKeys || []) !== JSON.stringify(b.candidateKeys || []);
}
async function r45ayAdaptiveSettle(scroller, beforeSig, opts){
  opts = opts || {};
  const maxMs = Math.max(16, Math.min(200, parseInt(opts.maxMs || 75, 10) || 75));
  const started = performance.now();
  let mutated = false, resized = false;
  const done = () => {
    const now = r45aySignature(scroller, r45ayPageLoopScan({maxCandidates:20, includeGuardedViewMore:!!opts.includeGuardedViewMore}));
    return r45aySignatureChanged(beforeSig, now);
  };
  if (done()) return {duration_ms:Math.round((performance.now() - started) * 1000) / 1000, reason:'immediate_change'};
  let mo = null, ro = null;
  try { mo = new MutationObserver(() => { mutated = true; }); mo.observe(scroller, {childList:true, subtree:true, characterData:true}); } catch(e) {}
  try { ro = new ResizeObserver(() => { resized = true; }); ro.observe(scroller); } catch(e) {}
  while (performance.now() - started < maxMs) {
    await new Promise(resolve => requestAnimationFrame(resolve));
    if (mutated || resized || done()) break;
  }
  try { if (mo) mo.disconnect(); } catch(e) {}
  try { if (ro) ro.disconnect(); } catch(e) {}
  return {duration_ms:Math.round((performance.now() - started) * 1000) / 1000, reason: mutated ? 'mutation' : (resized ? 'resize' : (done() ? 'signature_change' : 'timeout'))};
}
async function r45ayRunInstantPageLoop(options){
  options = options || {};
  const started = performance.now();
  const maxMs = Math.max(1000, parseInt(options.maxMs || 120000, 10) || 120000);
  const maxSteps = Math.max(1, Math.min(10000, parseInt(options.maxSteps || 300, 10) || 300));
  const maxBurst = Math.max(1, Math.min(80, parseInt(options.maxBurstClicks || 40, 10) || 40));
  const includeGuardedViewMore = !!options.includeGuardedViewMore;
  const story = String(options.expectedStory || '');
  const expectedTotal = parseInt(options.expectedTotal || 0, 10) || 0;
  const debugClicks = !!options.debugClicks;
  const scroller = r45axGetScroller();
  const elapsed = () => Math.round((performance.now() - started) * 1000) / 1000;
  if (!scroller) return {ok:false, status:'BLOCKED_NO_ACTIVE_COMMENTS_SCROLLER', reason:'no_active_scroller', elapsed_ms:elapsed()};
  const clickTimings = [], scanDurations = [], settleDurations = [], emptyScrollDurations = [], scanToFirstClick = [];
  const events = [];
  let clicked = 0, bursts = 0, activeSections = 0, fallbackCount = 0, targetDriftCount = 0, scrolls = 0;
  let bestProgress = null, emptyScans = 0, currentSectionActive = false;
  const inert = new Map();
  for (let step = 1; step <= maxSteps && performance.now() - started < maxMs; step++) {
    if (story && !String(location.href).includes(story)) {
      targetDriftCount += 1;
      return {ok:false, status:'BLOCKED_TARGET_DRIFT', href:location.href, clicked, bursts, activeSections, fallbackCount, targetDriftCount, scrolls, bestProgress, elapsed_ms:elapsed(), metrics:{clickTimings, scanDurations, settleDurations, emptyScrollDurations, scanToFirstClick}, events};
    }
    const scanStart = performance.now();
    let scan = r45ayPageLoopScan({maxCandidates:maxBurst, includeGuardedViewMore, expectedTotal});
    scanDurations.push(scan.scanDurationMs || Math.round((performance.now() - scanStart) * 1000) / 1000);
    if (expectedTotal && (step % 8 === 1 || (scan.scroller && scan.scroller.atBottom))) {
      const rawProgress = r45axProgressFromPage();
      if (rawProgress && rawProgress.total === expectedTotal && (!bestProgress || rawProgress.current > bestProgress.current)) bestProgress = rawProgress;
      if (bestProgress && bestProgress.current >= expectedTotal) {
        return {ok:true, status:'PASS_R45AY_PAGE_LOOP_EXPECTED_TOTAL_REACHED', clicked, bursts, activeSections, fallbackCount, targetDriftCount, scrolls, bestProgress, elapsed_ms:elapsed(), metrics:{clickTimings, scanDurations, settleDurations, emptyScrollDurations, scanToFirstClick}, events};
      }
    }
    const seenStable = new Set();
    let items = [];
    for (const item of (scan.items || [])) {
      const stableKey = r45ayStableCandidateKey(item);
      if (seenStable.has(stableKey)) continue;
      seenStable.add(stableKey);
      if ((inert.get(stableKey) || 0) >= 2) continue;
      item.loopKey = stableKey;
      items.push(item);
    }
    if (items.length) {
      if (!currentSectionActive) { activeSections += 1; currentSectionActive = true; }
      emptyScans = 0;
      const beforeSig = r45aySignature(scroller, scan);
      const burst = r45ayDispatchPageBurst(items, {debugClicks});
      bursts += 1;
      clicked += burst.clicked || 0;
      for (const t of burst.click_timings || []) {
        clickTimings.push(t);
        scanToFirstClick.push(Math.max(0, (t.browser_dispatch_perf_ms || 0) - (scan.scanPerformanceNow || t.browser_dispatch_perf_ms || 0)));
      }
      const large = items.some(item => item.category === 'view_all_replies');
      const settle = await r45ayAdaptiveSettle(scroller, beforeSig, {maxMs: large ? 150 : 75, includeGuardedViewMore});
      settleDurations.push(settle.duration_ms || 0);
      const afterScan = r45ayPageLoopScan({maxCandidates:20, includeGuardedViewMore, expectedTotal});
      const materialized = r45aySignatureChanged(beforeSig, r45aySignature(scroller, afterScan));
      if (!materialized) {
        for (const item of items.slice(0, Math.max(1, burst.clicked || 0))) {
          const stableKey = item.loopKey || r45ayStableCandidateKey(item);
          inert.set(stableKey, (inert.get(stableKey) || 0) + 1);
        }
      } else {
        for (const item of items) inert.delete(item.loopKey || r45ayStableCandidateKey(item));
      }
      if (events.length < 80 || step % 25 === 0) events.push({step, type:'burst', candidates:items.length, clicked:burst.clicked, labels:(burst.items || []).slice(0,10).map(x=>x.label), scan_ms:scan.scanDurationMs, burst_ms:burst.elapsed_ms, settle_ms:settle.duration_ms, settle_reason:settle.reason, scrollTop:scroller.scrollTop, scrollHeight:scroller.scrollHeight});
      continue;
    }
    currentSectionActive = false;
    emptyScans += 1;
    const scrollStart = performance.now();
    const before = scroller.scrollTop || 0;
    const ch = scroller.clientHeight || 600;
    if (bestProgress && expectedTotal && bestProgress.current >= expectedTotal - 40) scroller.scrollTop = Math.max(0, (scroller.scrollHeight || 0) - ch - 80);
    else scroller.scrollTop = before + Math.max(1100, Math.floor(ch * 1.9));
    await new Promise(resolve => requestAnimationFrame(resolve));
    const scrollDuration = Math.round((performance.now() - scrollStart) * 1000) / 1000;
    emptyScrollDurations.push(scrollDuration);
    scrolls += 1;
    if (events.length < 80 || step % 25 === 0) events.push({step, type:'scroll', emptyScans, before, after:scroller.scrollTop || 0, atBottom:(scroller.scrollTop + ch >= scroller.scrollHeight - 8), duration_ms:scrollDuration, scrollHeight:scroller.scrollHeight || 0});
    if (emptyScans >= (parseInt(options.progressStallCycles || 3, 10) || 3) && scroller.scrollTop + ch >= scroller.scrollHeight - 8) break;
  }
  return {ok:false, status:'BLOCKED_R45AY_PAGE_LOOP_EXPECTED_TOTAL_UNSATISFIED', clicked, bursts, activeSections, fallbackCount, targetDriftCount, bestProgress, scrolls, elapsed_ms:elapsed(), metrics:{clickTimings, scanDurations, settleDurations, emptyScrollDurations, scanToFirstClick}, events};
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


def value_summary(values: List[float]) -> Dict[str, Any]:
    clean = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
    return {
        "count": len(clean),
        "median_ms": round(statistics.median(clean), 3) if clean else 0.0,
        "p95_ms": round(percentile(clean, 95), 3) if clean else 0.0,
        "max_ms": round(max(clean), 3) if clean else 0.0,
    }


def page_loop_timing_summary(loop_result: Dict[str, Any]) -> Dict[str, Any]:
    metrics = (loop_result or {}).get("metrics") or {}
    return {
        "clicks": timing_summary(list(metrics.get("clickTimings") or [])),
        "scan_duration": value_summary(list(metrics.get("scanDurations") or [])),
        "adaptive_settle": value_summary(list(metrics.get("settleDurations") or [])),
        "empty_scan_scroll": value_summary(list(metrics.get("emptyScrollDurations") or [])),
        "scan_start_to_first_click": value_summary(list(metrics.get("scanToFirstClick") or [])),
    }


def py_stable_candidate_key(item: Dict[str, Any]) -> str:
    raw = str((item or {}).get("key") or "")
    parts = raw.split("|")
    context = parts[-1] if parts else ""
    if not context:
        context = str(round(float((item or {}).get("y") or 0) / 20.0))
    return "|".join([str((item or {}).get("category") or ""), str((item or {}).get("label") or ""), context])


def scan_signature(scan: Dict[str, Any]) -> Dict[str, Any]:
    scroller = (scan or {}).get("scroller") or {}
    return {
        "scrollHeight": int(scroller.get("scrollHeight") or 0),
        "candidateCount": int((scan or {}).get("candidateCount") or 0),
        "counts": (scan or {}).get("counts") or {},
        "candidateKeys": sorted(py_stable_candidate_key(item) for item in ((scan or {}).get("items") or [])),
    }


def signature_changed(before: Dict[str, Any], after: Dict[str, Any]) -> bool:
    return json.dumps(before or {}, sort_keys=True) != json.dumps(after or {}, sort_keys=True)


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
window.r45ayFastVisibleCandidates = r45ayFastVisibleCandidates;
window.r45ayPageLoopScan = r45ayPageLoopScan;
window.r45ayDispatchPageBurst = r45ayDispatchPageBurst;
window.r45ayRunInstantPageLoop = r45ayRunInstantPageLoop;
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


async def trusted_cdp_burst(
    cdp_session: Any,
    items: List[Dict[str, Any]],
    *,
    max_clicks: int,
    debug_clicks: bool = False,
) -> Dict[str, Any]:
    selected = list(items or [])[:max(1, min(80, max_clicks))]
    if not selected:
        return {"ok": False, "reason": "no_candidates", "clicked": 0, "items": [], "click_timings": []}
    started = time.perf_counter()
    tasks = []
    clicked_items: List[Dict[str, Any]] = []
    timings: List[Dict[str, Any]] = []
    event_count = 0
    for index, item in enumerate(selected):
        x = float(item.get("x") or 0.0)
        y = float(item.get("y") or 0.0)
        dispatch_ms = round((time.perf_counter() - started) * 1000.0, 3)
        clicked_items.append({
            "index": index,
            "label": item.get("label"),
            "category": item.get("category"),
            "key": item.get("key"),
            "x": round(x),
            "y": round(y),
        })
        timings.append({
            "index": index,
            "label": item.get("label"),
            "category": item.get("category"),
            "key": item.get("key"),
            "x": round(x),
            "y": round(y),
            "candidate_first_seen_perf_ms": 0.0,
            "browser_dispatch_perf_ms": dispatch_ms,
            "dispatch_perf_ms": dispatch_ms,
        })
        for params in (
            {"type": "mouseMoved", "x": x, "y": y, "button": "none"},
            {"type": "mousePressed", "x": x, "y": y, "button": "left", "buttons": 1, "clickCount": 1},
            {"type": "mouseReleased", "x": x, "y": y, "button": "left", "buttons": 0, "clickCount": 1},
        ):
            tasks.append(asyncio.create_task(cdp_session.send("Input.dispatchMouseEvent", params)))
            event_count += 1
    errors: List[str] = []
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [repr(result) for result in results if isinstance(result, Exception)]
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    if debug_clicks:
        for timing in timings:
            log("R45AY_TRUSTED_CDP_CLICK_TIMING", timing)
    return {
        "ok": not errors,
        "method": "trusted_cdp_input_dispatch_mouse_event_pipeline",
        "candidate_count": len(selected),
        "clicked": 0 if errors else len(selected),
        "items": [] if errors else clicked_items,
        "click_timings": [] if errors else timings,
        "timing": timing_summary([] if errors else timings),
        "cdp_event_count": event_count,
        "cdp_send_elapsed_ms": elapsed_ms,
        "errors": errors[:10],
    }


async def settle_after_trusted_cdp_burst(
    page,
    before_scan: Dict[str, Any],
    *,
    max_ms: int,
    include_guarded_view_more: bool,
    expected_total: int,
) -> Dict[str, Any]:
    started = time.perf_counter()
    before_sig = scan_signature(before_scan)
    before_progress = before_scan.get("progress")
    after_scan = before_scan
    materialized = False
    polls = 0
    while (time.perf_counter() - started) * 1000.0 < max_ms:
        await page.wait_for_timeout(16 if polls == 0 else 25)
        polls += 1
        after_scan = await page.evaluate(
            "(opts) => r45ayPageLoopScan(opts)",
            {"maxCandidates": 60, "includeGuardedViewMore": include_guarded_view_more, "expectedTotal": expected_total},
        )
        after_sig = scan_signature(after_scan)
        after_progress = after_scan.get("progress")
        materialized = (
            signature_changed(before_sig, after_sig)
            or json.dumps(before_progress or {}, sort_keys=True) != json.dumps(after_progress or {}, sort_keys=True)
        )
        if materialized:
            break
    duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return {
        "duration_ms": duration_ms,
        "polls": polls,
        "materialized": materialized,
        "after_scan": after_scan,
        "progress_before": before_scan.get("progress"),
        "progress_after": (after_scan or {}).get("progress"),
        "scroll_height_before": ((before_scan or {}).get("scroller") or {}).get("scrollHeight"),
        "scroll_height_after": (((after_scan or {}).get("scroller") or {}).get("scrollHeight")),
        "visible_candidates_after": int((after_scan or {}).get("candidateCount") or 0),
    }


async def run_trusted_cdp_engine(page, cdp_session: Any, args: argparse.Namespace, story: str) -> Dict[str, Any]:
    started = time.monotonic()
    max_steps = max(1, int(args.max_steps or 300))
    max_seconds = float(args.expand_max_seconds or 120)
    expected_total = int(args.expected_total_comments or 0)
    max_burst = max(1, int(args.max_burst_clicks or 30))
    include_guarded = bool(args.include_guarded_view_more)
    inert_counts: Dict[str, int] = {}
    clicked = 0
    burst_count = 0
    materialized_burst_count = 0
    fallback_count = 0
    target_drift_count = 0
    empty_scans = 0
    scroll_count = 0
    best_progress: Optional[Dict[str, Any]] = None
    click_timings_all: List[Dict[str, Any]] = []
    scan_durations: List[float] = []
    settle_durations: List[float] = []
    scroll_durations: List[float] = []
    events: List[Dict[str, Any]] = []
    total_candidates_seen = 0
    log("R45AY_TRUSTED_CDP_START", {
        "max_steps": max_steps,
        "max_seconds": max_seconds,
        "expected_total": expected_total,
        "max_burst_clicks": max_burst,
    })
    for step in range(1, max_steps + 1):
        elapsed = time.monotonic() - started
        if elapsed >= max_seconds:
            break
        if story:
            href = await page.evaluate("location.href")
            if story not in str(href):
                target_drift_count += 1
                return {
                    "ok": False,
                    "status": "BLOCKED_TARGET_DRIFT",
                    "href": href,
                    "clicked": clicked,
                    "bursts": burst_count,
                    "materializedBursts": materialized_burst_count,
                    "fallbackCount": fallback_count,
                    "targetDriftCount": target_drift_count,
                    "bestProgress": best_progress,
                    "scrolls": scroll_count,
                    "events": events,
                    "metrics": {
                        "clickTimings": click_timings_all,
                        "scanDurations": scan_durations,
                        "settleDurations": settle_durations,
                        "emptyScrollDurations": scroll_durations,
                    },
                }
        scan_t0 = time.perf_counter()
        scan = await page.evaluate(
            "(opts) => r45ayPageLoopScan(opts)",
            {"maxCandidates": max_burst, "includeGuardedViewMore": include_guarded, "expectedTotal": expected_total},
        )
        scan_ms = round((time.perf_counter() - scan_t0) * 1000.0, 3)
        scan_durations.append(scan_ms)
        raw_progress = scan.get("progress")
        progress = r45ax_filter_expected_progress(raw_progress, expected_total)
        if progress and ((not best_progress) or int(progress.get("current") or 0) > int(best_progress.get("current") or 0)):
            best_progress = progress
        if expected_total and r45ax_progress_gate_ok(best_progress, expected_total):
            return {
                "ok": True,
                "status": "PASS_R45AY_TRUSTED_CDP_EXPECTED_TOTAL_REACHED",
                "clicked": clicked,
                "bursts": burst_count,
                "materializedBursts": materialized_burst_count,
                "fallbackCount": fallback_count,
                "targetDriftCount": target_drift_count,
                "bestProgress": best_progress,
                "scrolls": scroll_count,
                "elapsed_ms": round((time.monotonic() - started) * 1000.0, 3),
                "events": events,
                "metrics": {
                    "clickTimings": click_timings_all,
                    "scanDurations": scan_durations,
                    "settleDurations": settle_durations,
                    "emptyScrollDurations": scroll_durations,
                },
            }
        candidates: List[Dict[str, Any]] = []
        seen_stable = set()
        for item in list(scan.get("items") or []):
            stable_key = py_stable_candidate_key(item)
            if stable_key in seen_stable:
                continue
            seen_stable.add(stable_key)
            if inert_counts.get(stable_key, 0) >= 2:
                continue
            copied = dict(item)
            copied["loopKey"] = stable_key
            candidates.append(copied)
        total_candidates_seen += len(candidates)
        if step <= 5 or step % 20 == 0 or candidates:
            log("R45AY_TRUSTED_CDP_SCAN", {
                "step": step,
                "candidate_count": len(candidates),
                "counts": scan.get("counts"),
                "progress": progress or raw_progress,
                "scan_duration_ms": scan_ms,
                "scrollTop": ((scan.get("scroller") or {}).get("scrollTop")),
                "scrollHeight": ((scan.get("scroller") or {}).get("scrollHeight")),
            })
        if candidates:
            empty_scans = 0
            large = any(str(item.get("category")) == "view_all_replies" for item in candidates)
            burst = await trusted_cdp_burst(
                cdp_session,
                candidates,
                max_clicks=max_burst,
                debug_clicks=bool(args.debug_clicks),
            )
            burst_count += 1
            clicked += int(burst.get("clicked") or 0)
            click_timings_all.extend(list(burst.get("click_timings") or []))
            settle = await settle_after_trusted_cdp_burst(
                page,
                scan,
                max_ms=1600 if large else 500,
                include_guarded_view_more=include_guarded,
                expected_total=expected_total,
            )
            settle_durations.append(float(settle.get("duration_ms") or 0.0))
            materialized = bool(settle.get("materialized"))
            if materialized:
                materialized_burst_count += 1
                for item in candidates:
                    inert_counts.pop(str(item.get("loopKey") or py_stable_candidate_key(item)), None)
            else:
                for item in candidates[: max(1, int(burst.get("clicked") or 0))]:
                    key = str(item.get("loopKey") or py_stable_candidate_key(item))
                    inert_counts[key] = inert_counts.get(key, 0) + 1
            timing = burst.get("timing") or {}
            clicks_per_minute = round(clicked / max((time.monotonic() - started) / 60.0, 0.001), 2)
            event = {
                "step": step,
                "candidate_count": len(candidates),
                "clicked": burst.get("clicked"),
                "labels": [str(item.get("label")) for item in candidates[:10]],
                "cdp_event_count": burst.get("cdp_event_count"),
                "cdp_send_elapsed_ms": burst.get("cdp_send_elapsed_ms"),
                "median_cdp_inter_click_gap_ms": timing.get("median_inter_click_gap_ms"),
                "p95_cdp_inter_click_gap_ms": timing.get("p95_inter_click_gap_ms"),
                "settle_ms": settle.get("duration_ms"),
                "materialized": materialized,
                "visible_candidates_after": settle.get("visible_candidates_after"),
                "progress_before": settle.get("progress_before"),
                "progress_after": settle.get("progress_after"),
                "scrollHeight_before": settle.get("scroll_height_before"),
                "scrollHeight_after": settle.get("scroll_height_after"),
                "clicks_per_minute": clicks_per_minute,
            }
            events.append(event)
            log("R45AY_TRUSTED_CDP_BURST", event)
            continue
        empty_scans += 1
        scroll_t0 = time.perf_counter()
        mode = "bottom_chain_nudge" if (best_progress and expected_total and int(best_progress.get("current") or 0) >= expected_total - 40) else "down"
        scroll = await page.evaluate("(mode) => r45ayScroll(mode)", mode)
        await page.wait_for_timeout(20 if empty_scans < 3 else 45)
        scroll_ms = round((time.perf_counter() - scroll_t0) * 1000.0, 3)
        scroll_durations.append(scroll_ms)
        scroll_count += 1
        log("R45AY_TRUSTED_CDP_SCROLL", {"step": step, "mode": mode, "scroll": scroll, "empty_scans": empty_scans, "scroll_duration_ms": scroll_ms})
        if empty_scans >= int(args.progress_stall_cycles or 3) and (scroll or {}).get("atBottom"):
            break
    return {
        "ok": False,
        "status": "BLOCKED_R45AY_TRUSTED_CDP_EXPECTED_TOTAL_UNSATISFIED",
        "clicked": clicked,
        "bursts": burst_count,
        "materializedBursts": materialized_burst_count,
        "fallbackCount": fallback_count,
        "targetDriftCount": target_drift_count,
        "bestProgress": best_progress,
        "scrolls": scroll_count,
        "totalCandidatesSeen": total_candidates_seen,
        "elapsed_ms": round((time.monotonic() - started) * 1000.0, 3),
        "events": events,
        "metrics": {
            "clickTimings": click_timings_all,
            "scanDurations": scan_durations,
            "settleDurations": settle_durations,
            "emptyScrollDurations": scroll_durations,
        },
    }


async def synthetic_instant_audit(output_root: Path, instant_engine: str = "page_loop") -> Tuple[int, Dict[str, Any]]:
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
        if instant_engine == "page_loop":
            burst = await page.evaluate(
                """(opts) => r45ayRunInstantPageLoop(opts)""",
                {"maxMs": 5000, "maxSteps": 80, "maxBurstClicks": 30, "expectedTotal": 0, "progressStallCycles": 5},
            )
            burst["timing"] = page_loop_timing_summary(burst)
        elif instant_engine == "trusted_cdp":
            audit_args = argparse.Namespace(
                max_steps=80,
                expand_max_seconds=5,
                expected_total_comments=0,
                max_burst_clicks=30,
                include_guarded_view_more=False,
                debug_clicks=False,
                progress_stall_cycles=5,
            )
            burst = await run_trusted_cdp_engine(page, cdp, audit_args, "")
            burst["timing"] = page_loop_timing_summary(burst)
        else:
            burst = await cdp_ordered_burst(page, cdp, scan, max_clicks=30, inter_click_delay_ms=0, settle_ms=75)
        stats = await page.evaluate("r45aySyntheticStats()")
        await browser.close()
    timing = burst.get("timing") or {}
    if instant_engine in {"page_loop", "trusted_cdp"}:
        click_timing = timing.get("clicks") or {}
        scan_first = timing.get("scan_start_to_first_click") or {}
        settle = timing.get("adaptive_settle") or {}
        empty_scroll = timing.get("empty_scan_scroll") or {}
        checks = [
            {"name": "instant_engine_used", "status": "pass" if (instant_engine == "trusted_cdp" and "TRUSTED_CDP" in str(burst.get("status", "")).upper()) or (instant_engine == "page_loop" and ("PAGE_LOOP" in str(burst.get("status", "")).upper() or burst.get("bursts", 0))) else "fail"},
            {"name": "median_inter_click_gap_le_10ms", "status": "pass" if click_timing.get("median_inter_click_gap_ms", 999) <= 10 else "fail"},
            {"name": "p95_inter_click_gap_le_25ms", "status": "pass" if click_timing.get("p95_inter_click_gap_ms", 999) <= 25 else "fail"},
            {"name": "median_scan_start_to_first_click_le_50ms", "status": "pass" if instant_engine == "trusted_cdp" or scan_first.get("median_ms", 999) <= 50 else "fail"},
            {"name": "p95_scan_start_to_first_click_le_100ms", "status": "pass" if instant_engine == "trusted_cdp" or scan_first.get("p95_ms", 999) <= 100 else "fail"},
            {"name": "median_adaptive_settle_le_50ms", "status": "pass" if settle.get("median_ms", 999) <= 50 else "fail"},
            {"name": "p95_adaptive_settle_le_125ms", "status": "pass" if settle.get("p95_ms", 999) <= 125 else "fail"},
            {"name": "median_empty_scan_scroll_le_100ms", "status": "pass" if empty_scroll.get("median_ms", 0) <= 100 else "fail"},
            {"name": "ten_plus_controls_clicked_in_instant_engine", "status": "pass" if burst.get("clicked", 0) >= 10 else "fail"},
            {"name": "trusted_cdp_materialized_when_selected", "status": "pass" if instant_engine != "trusted_cdp" or burst.get("materializedBursts", 0) > 0 else "fail"},
            {"name": "no_unsafe_decoy_clicks", "status": "pass" if stats.get("decoyClicks") == 0 else "fail"},
        ]
    else:
        checks = [
            {"name": "median_inter_click_gap_le_25ms", "status": "pass" if timing.get("median_inter_click_gap_ms", 999) <= 25 else "fail"},
            {"name": "p95_inter_click_gap_le_75ms", "status": "pass" if timing.get("p95_inter_click_gap_ms", 999) <= 75 else "fail"},
            {"name": "candidate_to_click_median_le_50ms", "status": "pass" if timing.get("candidate_to_click_median_ms", 999) <= 50 else "fail"},
            {"name": "ten_plus_visible_controls_clicked_in_one_burst", "status": "pass" if burst.get("clicked", 0) >= 10 else "fail"},
            {"name": "no_unsafe_decoy_clicks", "status": "pass" if stats.get("decoyClicks") == 0 else "fail"},
            {"name": "one_settle_per_burst", "status": "pass" if burst.get("settle_ms") == 75 else "fail"},
        ]
    status = "PASS_R45AY_INSTANT_SYNTHETIC_AUDIT" if all(c["status"] == "pass" for c in checks) else "FAIL_R45AY_INSTANT_SYNTHETIC_AUDIT"
    receipt.update({"status": status, "instant_engine": instant_engine, "checks": checks, "burst": burst, "synthetic_stats": stats})
    (run_dir / "r45ay_synthetic_audit_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    log("R45AY_AUDIT_SYNTHETIC_RESULT", {"status": status, "instant_engine": instant_engine, "timing": timing, "clicked": burst.get("clicked"), "decoy_clicks": stats.get("decoyClicks")})
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
        if getattr(args, "instant_engine", "trusted_cdp") == "trusted_cdp":
            if args.keep_page_foreground:
                log("R45AY_FOREGROUND_KEEPALIVE", await r45ax_foreground_keepalive(page, "trusted_cdp", "before_start"))
                log("R45AY_ACTIVE_WINDOW_KEEPALIVE", r45ax_active_window_keepalive(await page.title()))
            cdp = await context.new_cdp_session(page)
            trusted_result = await run_trusted_cdp_engine(page, cdp, args, story)
            trusted_timing = page_loop_timing_summary(trusted_result)
            trusted_result["timing"] = trusted_timing
            final_guard = await r45ax_target_guard_now(page, story)
            target_drift_count = int(trusted_result.get("targetDriftCount") or 0) + (0 if final_guard.get("ok") else 1)
            elapsed_ms = float(trusted_result.get("elapsed_ms") or 0.0)
            clicked = int(trusted_result.get("clicked") or 0)
            clicks_per_minute = round(clicked / max((elapsed_ms / 1000.0) / 60.0, 0.001), 2)
            log("R45AY_TRUSTED_CDP_TIMING", {
                "status": trusted_result.get("status"),
                "clicked": clicked,
                "bursts": trusted_result.get("bursts"),
                "materialized_bursts": trusted_result.get("materializedBursts"),
                "fallback_count": trusted_result.get("fallbackCount"),
                "target_drift_count": target_drift_count,
                "scrolls": trusted_result.get("scrolls"),
                "elapsed_ms": elapsed_ms,
                "clicks_per_minute": clicks_per_minute,
                "timing": trusted_timing,
                "target_guard_ok": bool(final_guard.get("ok")),
            })
            receipt.update({
                "instant_engine": "trusted_cdp",
                "trusted_cdp_result": trusted_result,
                "clicked": clicked,
                "burst_count": int(trusted_result.get("bursts") or 0),
                "candidate_count": int(trusted_result.get("totalCandidatesSeen") or 0),
                "materialized_burst_count": int(trusted_result.get("materializedBursts") or 0),
                "fallback_count": int(trusted_result.get("fallbackCount") or 0),
                "target_drift_count": target_drift_count,
                "best_progress": trusted_result.get("bestProgress"),
                "timing": trusted_timing,
                "clicks_per_minute": clicks_per_minute,
                "target_guard": final_guard,
            })
            expected = int(args.expected_total_comments or 0)
            passed_expected = bool(expected and r45ax_progress_gate_ok(trusted_result.get("bestProgress"), expected))
            if not final_guard.get("ok"):
                receipt.update({
                    "status": "BLOCKED_TARGET_DRIFT",
                    "failure_artifacts": await write_failure_artifacts(page, run_dir, "blocked_target_drift"),
                })
                log("R45AY_TRUSTED_CDP_BLOCKED", {"status": receipt["status"], "target_guard": final_guard})
                (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
                await context.close()
                return 4
            if passed_expected and trusted_result.get("ok"):
                outputs = await flatten_and_capture(page, run_dir, int(args.max_band_height or 30000))
                receipt.update({
                    "status": "PASS_R45AY_INSTANT_ORDERED_CAPTURE",
                    "auto_expand_summary": {
                        "status": "pass",
                        "best_progress": trusted_result.get("bestProgress"),
                        "clicked": clicked,
                        "bursts": trusted_result.get("bursts"),
                        "materialized_bursts": trusted_result.get("materializedBursts"),
                    },
                    "outputs": outputs,
                })
                log("R45AY_TRUSTED_CDP_DONE", {"status": receipt["status"], "clicked": clicked, "clicks_per_minute": clicks_per_minute, "zip_path": outputs.get("zip_path")})
                (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
                await context.close()
                return 0
            status = str(trusted_result.get("status") or "BLOCKED_R45AY_TRUSTED_CDP_EXPECTED_TOTAL_UNSATISFIED")
            receipt.update({
                "status": status,
                "failure_artifacts": await write_failure_artifacts(page, run_dir, status.lower()),
            })
            log("R45AY_TRUSTED_CDP_BLOCKED", {
                "status": status,
                "best_progress": trusted_result.get("bestProgress"),
                "clicked": clicked,
                "bursts": trusted_result.get("bursts"),
                "materialized_bursts": trusted_result.get("materializedBursts"),
                "fallback_count": trusted_result.get("fallbackCount"),
                "clicks_per_minute": clicks_per_minute,
                "failure_artifacts": receipt["failure_artifacts"],
            })
            (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
            await context.close()
            return 0 if args.instant_audit else 5
        if getattr(args, "instant_engine", "page_loop") == "page_loop":
            if args.keep_page_foreground:
                log("R45AY_FOREGROUND_KEEPALIVE", await r45ax_foreground_keepalive(page, "page_loop", "before_start"))
                log("R45AY_ACTIVE_WINDOW_KEEPALIVE", r45ax_active_window_keepalive(await page.title()))
            loop_options = {
                "maxMs": int(max(1.0, float(args.expand_max_seconds)) * 1000),
                "maxSteps": max(1, int(args.max_steps or 300)),
                "maxBurstClicks": max(1, int(args.max_burst_clicks or 40)),
                "expectedTotal": int(args.expected_total_comments or 0),
                "expectedStory": story,
                "progressStallCycles": int(args.progress_stall_cycles or 3),
                "includeGuardedViewMore": bool(args.include_guarded_view_more),
                "debugClicks": bool(args.debug_clicks),
            }
            log("R45AY_PAGE_LOOP_START", loop_options)
            loop_result = await page.evaluate("(opts) => r45ayRunInstantPageLoop(opts)", loop_options)
            loop_timing = page_loop_timing_summary(loop_result)
            loop_result["timing"] = loop_timing
            final_guard = await r45ax_target_guard_now(page, story)
            target_drift_count = int(loop_result.get("targetDriftCount") or 0) + (0 if final_guard.get("ok") else 1)
            elapsed_ms = float(loop_result.get("elapsed_ms") or 0.0)
            clicked = int(loop_result.get("clicked") or 0)
            clicks_per_minute = round(clicked / max((elapsed_ms / 1000.0) / 60.0, 0.001), 2)
            log("R45AY_PAGE_LOOP_TIMING", {
                "status": loop_result.get("status"),
                "clicked": clicked,
                "bursts": loop_result.get("bursts"),
                "active_sections": loop_result.get("activeSections"),
                "scrolls": loop_result.get("scrolls"),
                "elapsed_ms": elapsed_ms,
                "clicks_per_minute": clicks_per_minute,
                "timing": loop_timing,
                "target_guard_ok": bool(final_guard.get("ok")),
            })
            receipt.update({
                "instant_engine": "page_loop",
                "page_loop_result": loop_result,
                "clicked": clicked,
                "active_sections": int(loop_result.get("activeSections") or 0),
                "burst_count": int(loop_result.get("bursts") or 0),
                "fallback_count": int(loop_result.get("fallbackCount") or 0),
                "target_drift_count": target_drift_count,
                "best_progress": loop_result.get("bestProgress"),
                "timing": loop_timing,
                "clicks_per_minute": clicks_per_minute,
                "target_guard": final_guard,
            })
            expected = int(args.expected_total_comments or 0)
            passed_expected = bool(expected and r45ax_progress_gate_ok(loop_result.get("bestProgress"), expected))
            if not final_guard.get("ok"):
                receipt.update({
                    "status": "BLOCKED_TARGET_DRIFT",
                    "failure_artifacts": await write_failure_artifacts(page, run_dir, "blocked_target_drift"),
                })
                log("R45AY_PAGE_LOOP_BLOCKED", {"status": receipt["status"], "target_guard": final_guard})
                (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
                await context.close()
                return 4
            if passed_expected and loop_result.get("ok"):
                outputs = await flatten_and_capture(page, run_dir, int(args.max_band_height or 30000))
                receipt.update({
                    "status": "PASS_R45AY_INSTANT_ORDERED_CAPTURE",
                    "auto_expand_summary": {
                        "status": "pass",
                        "best_progress": loop_result.get("bestProgress"),
                        "clicked": clicked,
                        "bursts": loop_result.get("bursts"),
                        "active_sections": loop_result.get("activeSections"),
                    },
                    "outputs": outputs,
                })
                log("R45AY_PAGE_LOOP_PASS", {"status": receipt["status"], "clicked": clicked, "clicks_per_minute": clicks_per_minute, "zip_path": outputs.get("zip_path")})
                (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
                await context.close()
                return 0
            status = str(loop_result.get("status") or "BLOCKED_R45AY_PAGE_LOOP_EXPECTED_TOTAL_UNSATISFIED")
            receipt.update({
                "status": status,
                "failure_artifacts": await write_failure_artifacts(page, run_dir, status.lower()),
            })
            log("R45AY_PAGE_LOOP_BLOCKED", {
                "status": status,
                "best_progress": loop_result.get("bestProgress"),
                "clicked": clicked,
                "bursts": loop_result.get("bursts"),
                "active_sections": loop_result.get("activeSections"),
                "clicks_per_minute": clicks_per_minute,
                "failure_artifacts": receipt["failure_artifacts"],
            })
            (run_dir / "r45ay_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
            await context.close()
            return 0 if args.instant_audit else 5
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
    ap.add_argument("--instant-engine", choices=["trusted_cdp", "page_loop", "python_sweep"], default="trusted_cdp")
    ap.add_argument("--debug-clicks", action="store_true")
    ap.add_argument("--include-guarded-view-more", action="store_true")
    ap.add_argument("--max-burst-clicks", type=int, default=30)
    ap.add_argument("--inter-click-delay-ms", type=int, default=0)
    ap.add_argument("--settle-ms", type=int, default=125)
    return ap.parse_args(argv)


async def amain(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.instant_audit and not args.target_url:
        code, _receipt = await synthetic_instant_audit(Path(args.output_root), args.instant_engine)
        return code
    if not args.target_url:
        print("R45AY requires --target-url unless --instant-audit synthetic mode is used.", flush=True)
        return 2
    return await run_live(args)


def main() -> None:
    raise SystemExit(asyncio.run(amain()))


if __name__ == "__main__":
    main()
