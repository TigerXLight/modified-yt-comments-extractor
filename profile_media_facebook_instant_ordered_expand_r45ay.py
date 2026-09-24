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
import re
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
  if (c === 'comment_list_loader') return 1;
  if (c === 'view_hidden') return 2;
  if (c === 'view_all_replies') return 3;
  if (c === 'view_n_replies') return 4;
  if (c === 'replied_bucket') return 5;
  if (c === 'view_more_replies') return 6;
  return 99;
}
function r45ayAllowedCategory(category, includeGuardedViewMore){
  const c = String(category || '');
  if (['comment_list_loader','view_hidden','view_all_replies','view_n_replies','replied_bucket'].includes(c)) return true;
  return !!includeGuardedViewMore && c === 'view_more_replies';
}
function r45ayExpansionTextInfo(text){
  const t = r45axNorm(text);
  if (/^(View|See|Show|More) (?:more )?comments$/i.test(t)) return {label:t, category:'comment_list_loader', replyCount:0, clickLabel:t};
  if (/^(View|See) previous comments$/i.test(t)) return {label:t, category:'comment_list_loader', replyCount:0, clickLabel:t};
  if (/^More comments$/i.test(t)) return {label:t, category:'comment_list_loader', replyCount:0, clickLabel:t};
  const patterns = [
    {category:'view_hidden', rx:/\bView hidden (?:replies|comments)\b/i},
    {category:'view_all_replies', rx:/\bView all (\d+) replies?\b/i},
    {category:'view_n_replies', rx:/\bView (\d+) replies?\b/i},
    {category:'replied_bucket', rx:/\breplied\s*(?:[·•.\-]\s*)?(\d+)\s+repl(?:y|ies)\b/i}
  ];
  for (const p of patterns) {
    const m = t.match(p.rx);
    if (m) {
      const n = m[1] ? parseInt(m[1], 10) || 0 : 0;
      return {label:r45axNorm(m[0]), category:p.category, replyCount:n, clickLabel:r45axNorm(m[0])};
    }
  }
  return null;
}
function r45ayExpansionTextMatches(text){
  const t = r45axNorm(text);
  const out = [];
  const patterns = [
    /\bView hidden (?:replies|comments)\b/ig,
    /\bView all \d+ replies?\b/ig,
    /\bView \d+ replies?\b/ig,
    /\breplied\s*(?:[·•.\-]\s*)?\d+\s+repl(?:y|ies)\b/ig
  ];
  for (const rx of patterns) {
    let m;
    while ((m = rx.exec(t)) !== null && out.length < 80) out.push(r45axNorm(m[0]));
  }
  return Array.from(new Set(out));
}
function r45ayProgressEvidenceFromSources(expectedTotal, sources){
  const expected = parseInt(expectedTotal || 0, 10) || 0;
  let progress = null;
  let evidence = expected > 0 ? {expected_total: expected, found: false, searched_sources: []} : null;
  const patterns = expected > 0 ? [
    new RegExp('\\b\\d{1,5}\\s+of\\s+' + expected + '\\b', 'i'),
    new RegExp('\\b' + expected + '\\b.{0,40}\\b(?:comments?|replies)\\b', 'i'),
    new RegExp('\\b(?:comments?|replies)\\b.{0,40}\\b' + expected + '\\b', 'i')
  ] : [];
  for (const src of sources || []) {
    const text = String((src && src.text) || '');
    if (evidence) evidence.searched_sources.push(src.name || 'unknown');
    const foundProgress = r45axProgressFromText(text);
    if (foundProgress && (!progress || foundProgress.total > progress.total || (foundProgress.total === progress.total && foundProgress.current > progress.current))) {
      progress = {...foundProgress, source:src.name || 'unknown'};
    }
    if (evidence && !evidence.found) {
      for (const rx of patterns) {
        const match = text.match(rx);
        if (match) {
          const idx = Math.max(0, (match.index || 0) - 90);
          evidence = {
            expected_total: expected,
            found: true,
            source: src.name || 'unknown',
            match: match[0],
            snippet: text.slice(idx, Math.min(text.length, idx + 260)).replace(/\s+/g, ' ').trim()
          };
          break;
        }
      }
    }
  }
  return {progress, expectedTotalEvidence:evidence};
}
function r45ayVisibleScrollerText(scroller){
  if (!scroller) return '';
  const sr = scroller.getBoundingClientRect();
  const band = {top:Math.max(0, sr.top - 160), bottom:Math.min(innerHeight, sr.bottom + 160), left:Math.max(0, sr.left), right:Math.min(innerWidth, sr.right)};
  const pieces = [];
  const seen = new Set();
  const els = r45ayViewportProbeElements(scroller, band, {maxElements:260});
  for (const el of els.elements) {
    if (!el || seen.has(el) || r45axElementHidden(el)) continue;
    seen.add(el);
    const r = el.getBoundingClientRect();
    if (r.width < 3 || r.height < 3) continue;
    if (r.bottom <= band.top || r.top >= band.bottom || r.right <= band.left || r.left >= band.right) continue;
    const text = r45axNorm([el.getAttribute && (el.getAttribute('aria-label') || ''), el.getAttribute && (el.getAttribute('title') || ''), el.textContent || ''].join(' '));
    if (text) pieces.push(text);
    if (pieces.length >= 220) break;
  }
  return pieces.join(' ');
}
function r45ayProgressEvidenceScan(expectedTotal, mode){
  const started = performance.now();
  const expected = parseInt(expectedTotal || 0, 10) || 0;
  const scanMode = String(mode || 'cheap');
  const scroller = r45axGetScroller();
  let sources = [];
  if (scanMode === 'heavy') {
    const progress = r45axProgressFromPage();
    const expectedTotalEvidence = expected ? r45axExpectedTotalEvidence(expected) : null;
    return {
      ok:true,
      mode:scanMode,
      progress,
      expectedTotalEvidence,
      durationMs:Math.round((performance.now() - started) * 100) / 100,
      scroller:{scrollTop:scroller ? (scroller.scrollTop || 0) : 0, scrollHeight:scroller ? (scroller.scrollHeight || 0) : 0, clientHeight:scroller ? (scroller.clientHeight || 0) : 0}
    };
  }
  if (scroller) {
    sources.push({name:'visible_scroller_viewport_text', text:r45ayVisibleScrollerText(scroller)});
  }
  const out = r45ayProgressEvidenceFromSources(expected, sources);
  return {
    ok:true,
    mode:scanMode,
    progress:out.progress,
    expectedTotalEvidence:out.expectedTotalEvidence,
    durationMs:Math.round((performance.now() - started) * 100) / 100,
    scroller:{scrollTop:scroller ? (scroller.scrollTop || 0) : 0, scrollHeight:scroller ? (scroller.scrollHeight || 0) : 0, clientHeight:scroller ? (scroller.clientHeight || 0) : 0}
  };
}
function r45ayScanOrdered(opts){
  opts = opts || {};
  const includeGuardedViewMore = !!opts.includeGuardedViewMore;
  const includeProgress = !!opts.includeProgress;
  const includeExpectedEvidence = !!opts.includeExpectedEvidence;
  const maxCandidates = Math.max(1, Math.min(80, parseInt(opts.maxCandidates || 50, 10) || 50));
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_active_scroller'};
  const scanStart = performance.now();
  const raw = r45axTextCandidates(scroller).map(item => {
    const info = r45ayExactInfo(item && item.label);
    return info ? {...item, label:info.label, category:info.category, replyCount:info.replyCount || 0, clickLabel:info.clickLabel || info.label} : item;
  }).filter(item => {
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
    replyCount:Number(item.replyCount || 0),
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
    progress: includeProgress ? r45axProgressFromPage() : null,
    expectedTotalEvidence: includeExpectedEvidence && opts.expectedTotal ? r45axExpectedTotalEvidence(opts.expectedTotal) : null,
    scroller:{
      scrollTop:scroller.scrollTop || 0,
      scrollHeight:scroller.scrollHeight || 0,
      clientHeight:scroller.clientHeight || 0,
      childElementCount:scroller.childElementCount || 0,
      atBottom:(scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8)
    }
  };
}
function r45ayViewportProbeElements(scroller, band, opts){
  opts = opts || {};
  const started = performance.now();
  const maxElements = Math.max(40, Math.min(180, parseInt(opts.maxElements || 120, 10) || 120));
  const out = [];
  const seen = new Set();
  let skippedOffscreen = 0, probes = 0;
  const width = Math.max(1, band.right - band.left);
  const xs = [
    band.left + width * 0.36,
    band.left + width * 0.68
  ].filter(x => x >= band.left + 1 && x <= band.right - 1);
  const stepY = Math.max(58, Math.min(96, Math.floor(((band.bottom - band.top) || 600) / 8)));
  const maybeAdd = el => {
    if (!el || el === scroller || seen.has(el) || !scroller.contains(el)) return;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || r.bottom <= band.top || r.top >= band.bottom || r.right <= band.left || r.left >= band.right) {
      skippedOffscreen += 1;
      return;
    }
    seen.add(el);
    out.push(el);
  };
  for (let y = band.top + 6; y <= band.bottom - 3 && out.length < maxElements; y += stepY) {
    for (const x of xs) {
      probes += 1;
      const stack = document.elementsFromPoint(x, y).slice(0, 8);
      for (const hit of stack) {
          if (!hit || !scroller.contains(hit)) continue;
          for (let cur = hit, depth = 0; cur && cur !== scroller && depth < 8 && out.length < maxElements; cur = cur.parentElement, depth++) {
          maybeAdd(cur);
          const role = cur.getAttribute && (cur.getAttribute('role') || '');
          if (role === 'button' || cur.tagName === 'BUTTON' || cur.tagName === 'A') break;
        }
      }
    }
  }
  return {elements:out, probes, skippedOffscreen, durationMs:Math.round((performance.now() - started) * 100) / 100};
}
function r45ayViewportRoleElements(scroller, band, opts){
  opts = opts || {};
  const started = performance.now();
  const maxElements = Math.max(80, Math.min(900, parseInt(opts.maxElements || 520, 10) || 520));
  const out = [];
  const seen = new Set();
  let considered = 0, skippedOffscreen = 0;
  const selector = '[role="button"],button,a[href],[tabindex="0"],[aria-label],[title]';
  let nodes = [];
  try { nodes = Array.from(scroller.querySelectorAll(selector)); } catch(e) { nodes = []; }
  for (const el of nodes) {
    if (out.length >= maxElements) break;
    if (!el || seen.has(el) || !scroller.contains(el)) continue;
    considered += 1;
    const r = el.getBoundingClientRect();
    if (r.width < 3 || r.height < 3 || r.bottom <= band.top || r.top >= band.bottom || r.right <= band.left || r.left >= band.right) {
      skippedOffscreen += 1;
      continue;
    }
    seen.add(el);
    out.push(el);
  }
  return {elements:out, considered, skippedOffscreen, durationMs:Math.round((performance.now() - started) * 100) / 100};
}
function r45ayAddRangeCandidateForText(out, seen, el, info, started, source){
  if (!el || !info) return false;
  const needle = String(info.clickLabel || info.label || '').toLowerCase();
  if (!needle) return false;
  let walker = null, node = null, scanned = 0;
  try {
    walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while ((node = walker.nextNode()) && scanned < 80) {
      scanned += 1;
      const raw = String(node.nodeValue || '');
      if (!raw || raw.length > 420) continue;
      const start = raw.toLowerCase().indexOf(needle);
      if (start < 0) continue;
      const range = document.createRange();
      try {
        range.setStart(node, start);
        range.setEnd(node, Math.min(raw.length, start + needle.length));
        const rects = Array.from(range.getClientRects());
        for (const rect of rects) {
          const before = out.length;
          r45ayAddVisibleCandidate(out, seen, el, rect, info, started, source);
          if (out.length > before) return true;
        }
      } finally {
        try { range.detach && range.detach(); } catch(e) {}
      }
    }
  } catch(e) {}
  return false;
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
  return r45ayExpansionTextInfo(text);
}
function r45ayTrustedPointSafety(item){
  item = item || {};
  const x = Number(item.x), y = Number(item.y);
  const label = r45axNorm(item.label || '');
  const category = String(item.category || '');
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_active_scroller'};
  if (!Number.isFinite(x) || !Number.isFinite(y)) return {ok:false, reason:'invalid_point', x, y};
  const hit = document.elementFromPoint(x, y);
  if (!hit || !scroller.contains(hit)) return {ok:false, reason:'point_outside_active_scroller', hitTag:hit && hit.tagName || ''};
  if (hit.closest && hit.closest('textarea,input,select,[contenteditable="true"]')) return {ok:false, reason:'composer_or_form_control'};
  const clickable = hit.closest && hit.closest('a, button, [role="button"], [tabindex], span, div');
  const target = (clickable && scroller.contains(clickable)) ? clickable : hit;
  if (r45axBadCandidateElement(target)) return {ok:false, reason:'bad_candidate_element'};
  const anchor = hit.closest && hit.closest('a[href]');
  if (anchor) {
    const href = anchor.href || anchor.getAttribute('href') || '';
    if (href && !/^(#|javascript:|about:blank)/i.test(String(href))) {
      return {ok:false, reason:'anchor_href_under_trusted_point', href:String(href).slice(0, 220)};
    }
  }
  const chain = [];
  for (let cur = hit; cur && chain.length < 8; cur = cur.parentElement) {
    chain.push({
      tag:cur.tagName || '',
      role:cur.getAttribute && (cur.getAttribute('role') || ''),
      href:(cur.href || (cur.getAttribute && cur.getAttribute('href')) || ''),
      text:r45axNorm([cur.getAttribute && (cur.getAttribute('aria-label') || ''), cur.getAttribute && (cur.getAttribute('title') || ''), cur.innerText || cur.textContent || ''].join(' ')).slice(0, 180)
    });
  }
  const blob = r45axNorm(chain.map(c => c.text || '').join(' '));
  const immediateBlob = r45axNorm(chain.slice(0, 3).map(c => c.text || '').join(' '));
  if (/^(Like|Reply|Share|React|GIF|Photo|Camera|Upload)$/i.test(blob)) return {ok:false, reason:'unsafe_control_label', text:blob.slice(0, 120)};
  if (/\b(Comment as|Reply to|Write a comment|Add photo|Choose a GIF|Upload|Camera|Sticker)\b/i.test(immediateBlob)) {
    return {ok:false, reason:'composer_or_media_control_text', text:immediateBlob.slice(0, 180)};
  }
  const exact = r45ayExpansionTextInfo(label);
  const blobInfo = r45ayExpansionTextInfo(blob);
  const labelPresent = label && blob.toLowerCase().includes(label.toLowerCase());
  if (!exact || !r45ayAllowedCategory(exact.category, true)) return {ok:false, reason:'candidate_label_not_whitelisted', label};
  if (!labelPresent && !blobInfo) return {ok:false, reason:'hit_target_lacks_expansion_text', label, text:blob.slice(0, 180)};
  if (blobInfo && blobInfo.category !== category && exact.category !== category) {
    return {ok:false, reason:'category_mismatch_at_hit_target', label, category, hitCategory:blobInfo.category, text:blob.slice(0, 180)};
  }
  return {ok:true, reason:'r45ay_trusted_expansion_point', label, category, chain};
}
function r45ayValidateTrustedCdpItems(items){
  const accepted = [];
  const rejected = [];
  for (const item of (Array.isArray(items) ? items : [])) {
    const safety = r45ayTrustedPointSafety(item);
    if (safety.ok) accepted.push({...item, safety});
    else rejected.push({
      label:item && item.label,
      category:item && item.category,
      key:item && item.key,
      x:item && item.x,
      y:item && item.y,
      reason:safety.reason,
      safety
    });
  }
  return {ok:true, accepted, rejected, accepted_count:accepted.length, rejected_count:rejected.length};
}
function r45ayAddVisibleCandidate(out, seen, el, rect, info, started, source){
  if (!info || !el || !rect) return;
  if (rect.width < 4 || rect.height < 4 || rect.height > 100 || rect.width > 620) return;
  const fractions = info.category === 'replied_bucket' ? [0.50, 0.70, 0.88] : [0.50, 0.18, 0.82];
  let chosen = null, safety = null;
  for (const f of fractions) {
    const x = rect.left + Math.min(rect.width - 2, Math.max(2, rect.width * f));
    const y = rect.top + rect.height / 2;
    const s = r45ayTrustedPointSafety({x, y, label:info.label, category:info.category});
    if (s.ok) { chosen = {x, y}; safety = s; break; }
    if (!safety) safety = s;
  }
  if (!chosen) return;
  const key = info.category + '|' + info.label + '|' + Math.round(rect.top / 3) + '|' + Math.round(rect.left / 8) + '|' + r45axHashText(r45axCandidateContext(el, info.label));
  if (seen.has(key)) return;
  seen.add(key);
  out.push({
    label:info.label,
    category:info.category,
    replyCount:Number(info.replyCount || 0),
    key,
    x:Math.round(chosen.x),
    y:Math.round(chosen.y),
    top:Math.round(rect.top),
    bottom:Math.round(rect.bottom),
    left:Math.round(rect.left),
    right:Math.round(rect.right),
    source,
    priority:r45ayPriority(info.category, info.label),
    insideActiveScroller:true,
    firstSeenPerformanceNow:started,
    safety
  });
}
function r45ayFastVisibleCandidates(opts){
  opts = opts || {};
  const includeProgress = !!opts.includeProgress;
  const includeExpectedEvidence = !!opts.includeExpectedEvidence;
  const maxCandidates = Math.max(1, Math.min(120, parseInt(opts.maxCandidates || 50, 10) || 50));
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_active_scroller', items:[]};
  const started = performance.now();
  const sr = scroller.getBoundingClientRect();
  const buffer = Math.max(0, Math.min(300, parseInt(opts.viewportBufferPx || 250, 10) || 250));
  const band = {top:Math.max(0, sr.top - buffer), bottom:Math.min(innerHeight, sr.bottom + buffer), left:Math.max(0, sr.left + 6), right:Math.min(innerWidth, sr.right - 6)};
  const out = [];
  const seen = new Set();
  const roleProbe = r45ayViewportRoleElements(scroller, band, {maxElements:520});
  const pointProbe = {elements:[], probes:0, skippedOffscreen:0, durationMs:0};
  let probe = roleProbe;
  let scannedNodes = 0;
  let scannedRanges = 0;
  const scanElements = (elements, source) => {
  for (const el of elements) {
    if (out.length >= maxCandidates * 3) break;
    scannedNodes += 1;
    if (!el || r45axElementHidden(el) || r45axBadCandidateElement(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.height > 180) continue;
    if (r.bottom <= band.top || r.top >= band.bottom || r.right <= band.left || r.left >= band.right) continue;
    const variants = [el.getAttribute && (el.getAttribute('aria-label') || ''), el.getAttribute && (el.getAttribute('title') || ''), el.textContent || '']
      .map(value => r45axNorm(value)).filter(value => value && value.length <= 260);
    if (!variants.length) continue;
    let info = null;
    for (const variant of variants) {
      const candidateInfo = r45ayExactInfo(variant) || r45ayExpansionTextInfo(variant);
      if (candidateInfo) { info = candidateInfo; break; }
    }
    if (!info || !r45ayAllowedCategory(info.category, !!opts.includeGuardedViewMore)) continue;
    const exactLabel = variants.some(value => r45axNorm(value) === info.label);
    if (r.width > 680) {
      scannedRanges += 1;
      if (r45ayAddRangeCandidateForText(out, seen, el, info, started, source + '_wide_text_range')) continue;
      continue;
    }
    if (!exactLabel && (info.category === 'replied_bucket' || String(variants.join(' ')).length > String(info.label || '').length + 10)) {
      scannedRanges += 1;
      if (r45ayAddRangeCandidateForText(out, seen, el, info, started, source + '_text_range')) continue;
    }
    r45ayAddVisibleCandidate(out, seen, el, r, info, started, source);
  }
  };
  scanElements(roleProbe.elements, 'viewport_role_element');
  if (out.length === 0) {
    const p = r45ayViewportProbeElements(scroller, band, {maxElements:120});
    pointProbe.elements = p.elements;
    pointProbe.probes = p.probes;
    pointProbe.skippedOffscreen = p.skippedOffscreen;
    pointProbe.durationMs = p.durationMs;
    probe = p;
    scanElements(pointProbe.elements, 'viewport_point_element');
  }
  out.sort((a,b) => (a.priority - b.priority) || (b.y - a.y) || (a.x - b.x));
  const items = out.slice(0, maxCandidates);
  const counts = {};
  for (const item of items) counts[item.category] = (counts[item.category] || 0) + 1;
  const scanMs = Math.round((performance.now() - started) * 100) / 100;
  return {
    ok:true,
    marker:'R45AY_FAST_VISIBLE_SCAN',
    viewportOnly:true,
    scanPerformanceNow:started,
    scanDurationMs:scanMs,
    scanStats:{
      viewport_only:true,
      scanned_nodes:scannedNodes,
      scanned_ranges:scannedRanges,
      role_nodes:roleProbe.elements.length,
      role_considered:roleProbe.considered,
      role_skipped_offscreen_nodes:roleProbe.skippedOffscreen,
      role_probe_ms:roleProbe.durationMs,
      probe_points:pointProbe.probes,
      skipped_offscreen_nodes:(roleProbe.skippedOffscreen || 0) + (pointProbe.skippedOffscreen || 0),
      probe_ms:(roleProbe.durationMs || 0) + (pointProbe.durationMs || 0),
      scan_ms:scanMs
    },
    candidateCount:items.length,
    counts,
    items,
    rejected:[],
    progress: includeProgress ? r45axProgressFromPage() : null,
    expectedTotalEvidence: includeExpectedEvidence && opts.expectedTotal ? r45axExpectedTotalEvidence(opts.expectedTotal) : null,
    scroller:{scrollTop:scroller.scrollTop||0, scrollHeight:scroller.scrollHeight||0, clientHeight:scroller.clientHeight||0, childElementCount:scroller.childElementCount||0, atBottom:(scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8)}
  };
}
function r45ayFinalBlockEvidence(opts){
  opts = opts || {};
  const scroller = r45axGetScroller();
  const scan = r45ayPageLoopScan({maxCandidates:80, includeGuardedViewMore:!!opts.includeGuardedViewMore, includeProgress:false, includeExpectedEvidence:false});
  const text = scroller ? String(scroller.innerText || scroller.textContent || '') : '';
  const boundaryText = {
    top:text.slice(0, 1600),
    bottom:text.slice(Math.max(0, text.length - 1600))
  };
  const expansionTextMatches = r45ayExpansionTextMatches(boundaryText.top + ' ' + boundaryText.bottom);
  const largeBucketCandidates = (scan.items || []).filter(item => (item.category === 'view_all_replies' || item.category === 'replied_bucket') && Number(item.replyCount || 0) >= 20);
  return {
    ok:!!scroller,
    contains_expansion_text: expansionTextMatches.length > 0,
    expansion_text_matches: expansionTextMatches.slice(0, 40),
    safe_candidates: scan.candidateCount || 0,
    rejected_candidates: (scan.rejected || []).length,
    large_bucket_candidates: largeBucketCandidates.length,
    top_candidates: 0,
    bottom_candidates: scan.candidateCount || 0,
    candidate_labels:(scan.items || []).map(item => item.label).slice(0, 30),
    scroll:(scan.scroller || null),
    visible_boundary_text: boundaryText,
    reason_for_block: expansionTextMatches.length ? 'expansion_text_still_visible_requires_recorded_rejection_or_more_sweeps' : 'no_visible_whitelisted_expansion_text_or_safe_candidates'
  };
}
function r45ayLocateExpansionTextCandidates(opts){
  opts = opts || {};
  const started = performance.now();
  const scroller = r45axGetScroller();
  if (!scroller) {
    return {ok:false, reason:'no_active_scroller', text_matches:0, candidates:[], rejected:[], durationMs:0};
  }
  const maxCandidates = Math.max(1, Math.min(240, parseInt(opts.maxCandidates || 120, 10) || 120));
  const maxNodes = Math.max(200, Math.min(12000, parseInt(opts.maxNodes || 7000, 10) || 7000));
  const candidates = [];
  const rejected = [];
  const seen = new Set();
  const scrollerRect = scroller.getBoundingClientRect();
  const scrollerTop = scroller.scrollTop || 0;
  let textMatches = 0;
  let scannedNodes = 0;
  const rx = /\bView hidden (?:replies|comments)\b|\bView all \d+ replies?\b|\bView \d+ replies?\b|\breplied\s*(?:[·•.\-]\s*)?\d+\s+repl(?:y|ies)\b/ig;
  const reject = (label, reason, extra) => {
    rejected.push({label:r45axNorm(label || ''), reason, ...(extra || {})});
  };
  const contextHash = (el, label) => {
    try { return r45axHashText(r45axCandidateContext(el, label)); } catch(e) { return r45axHashText(String(label || '')); }
  };
  const loadedSafety = (el, label, category) => {
    if (!el || !scroller.contains(el)) return {ok:false, reason:'outside_active_scroller'};
    if (r45axBadCandidateElement(el)) return {ok:false, reason:'bad_candidate_element'};
    const text = r45axNorm([el.getAttribute && (el.getAttribute('aria-label') || ''), el.getAttribute && (el.getAttribute('title') || ''), el.innerText || el.textContent || ''].join(' '));
    const immediate = text.slice(0, 260);
    if (/^(Like|Reply|Share|React|GIF|Photo|Camera|Upload)$/i.test(immediate)) return {ok:false, reason:'unsafe_control_label', text:immediate};
    if (/\b(Comment as|Reply to|Write a comment|Add photo|Choose a GIF|Upload|Camera|Sticker)\b/i.test(immediate)) return {ok:false, reason:'composer_or_media_control_text', text:immediate};
    const anchor = el.closest && el.closest('a[href]');
    const button = el.closest && el.closest('button,[role="button"],[tabindex="0"]');
    if (anchor && (!button || !scroller.contains(button))) {
      const href = anchor.href || anchor.getAttribute('href') || '';
      if (href && !/^(#|javascript:|about:blank)/i.test(String(href))) {
        return {ok:false, reason:'unsafe_anchor_without_button_ancestor', href:String(href).slice(0, 220)};
      }
    }
    const info = r45ayExpansionTextInfo(label);
    if (!info || !r45ayAllowedCategory(info.category, !!opts.includeGuardedViewMore)) return {ok:false, reason:'label_not_whitelisted', label};
    if (info.category !== category) return {ok:false, reason:'category_mismatch', label, category, infoCategory:info.category};
    return {ok:true, reason:'loaded_scroller_expansion_text'};
  };
  try {
    const walker = document.createTreeWalker(scroller, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode()) && scannedNodes < maxNodes && candidates.length < maxCandidates) {
      scannedNodes += 1;
      const raw = String(node.nodeValue || '');
      if (!raw || raw.length > 800) continue;
      rx.lastIndex = 0;
      let match;
      while ((match = rx.exec(raw)) !== null && candidates.length < maxCandidates) {
        const label = r45axNorm(match[0]);
        const info = r45ayExpansionTextInfo(label);
        if (!info || !r45ayAllowedCategory(info.category, !!opts.includeGuardedViewMore)) continue;
        textMatches += 1;
        const parent = node.parentElement;
        if (!parent) {
          reject(label, 'text_node_without_parent');
          continue;
        }
        let rect = null;
        try {
          const range = document.createRange();
          range.setStart(node, match.index);
          range.setEnd(node, Math.min(raw.length, match.index + match[0].length));
          const rects = Array.from(range.getClientRects()).filter(r => r.width >= 2 && r.height >= 2);
          rect = rects[0] || null;
          try { range.detach && range.detach(); } catch(e) {}
        } catch(e) {}
        if (!rect) {
          try {
            const r = parent.getBoundingClientRect();
            if (r && r.width >= 2 && r.height >= 2) rect = r;
          } catch(e) {}
        }
        if (!rect) {
          reject(label, 'no_range_or_parent_rect');
          continue;
        }
        const safety = loadedSafety(parent, label, info.category);
        if (!safety.ok) {
          reject(label, safety.reason, {safety});
          continue;
        }
        const approx = Math.max(0, Math.round(scrollerTop + rect.top - scrollerRect.top));
        const xBand = Math.round((rect.left || 0) / 24);
        const yBand = Math.round(approx / 24);
        const key = [info.category, info.label, yBand, xBand, contextHash(parent, info.label)].join('|');
        if (seen.has(key)) continue;
        seen.add(key);
        candidates.push({
          label:info.label,
          category:info.category,
          replyCount:Number(info.replyCount || 0),
          key,
          contextual_key:key,
          approx_scroll_position:approx,
          band:Math.floor(approx / 350),
          top:Math.round(rect.top),
          bottom:Math.round(rect.bottom),
          left:Math.round(rect.left),
          right:Math.round(rect.right),
          source:'loaded_scroller_text_locator',
          safety
        });
      }
    }
  } catch(e) {
    return {ok:false, reason:'locator_failed', error:String(e), text_matches:textMatches, candidates, rejected, durationMs:Math.round((performance.now() - started) * 100) / 100};
  }
  return {
    ok:true,
    marker:'R45AY_RESIDUAL_TEXT_LOCATOR_DONE',
    text_matches:textMatches,
    candidates_created:candidates.length,
    rejected_count:rejected.length,
    labels:Array.from(new Set(candidates.map(c => c.label))).slice(0, 40),
    approx_positions:candidates.map(c => c.approx_scroll_position).slice(0, 40),
    scanned_nodes:scannedNodes,
    candidates,
    rejected:rejected.slice(0, 80),
    scroll:{scrollTop:scroller.scrollTop || 0, scrollHeight:scroller.scrollHeight || 0, clientHeight:scroller.clientHeight || 0},
    durationMs:Math.round((performance.now() - started) * 100) / 100
  };
}
function r45ayCommentFilterState(){
  const scroller = r45axGetScroller();
  const root = scroller || document.body;
  const text = r45axNorm(root ? (root.innerText || root.textContent || '') : '');
  const labels = ['Most relevant', 'All comments', 'Newest', 'Top comments'];
  const present = labels.filter(label => new RegExp('(^|\\s)' + label.replace(/ /g, '\\s+') + '($|\\s)', 'i').test(text));
  return {ok:!!scroller, present, current:present[0] || '', scroller:!!scroller};
}
function r45ayPageLoopScan(opts){
  opts = opts || {};
  let scan = r45ayFastVisibleCandidates(opts);
  if (scan.ok && scan.candidateCount === 0 && opts.allowVisibleTextFallback) {
    const scroller = r45axGetScroller();
    const visibleMatches = scroller ? r45ayExpansionTextMatches(r45ayVisibleScrollerText(scroller)) : [];
    if (visibleMatches.length) {
      const full = r45ayScanOrdered(opts);
      if (full.ok && full.candidateCount > 0) {
        full.viewportOnly = false;
        full.viewportFallbackReason = 'visible_expansion_text_without_probe_candidates';
        full.visibleExpansionTextMatches = visibleMatches.slice(0, 20);
        scan = full;
      } else {
        scan.visibleExpansionTextMatches = visibleMatches.slice(0, 20);
      }
    }
  }
  if (scan.ok && scan.candidateCount === 0 && opts.allowFullFallback) {
    const full = r45ayScanOrdered(opts);
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
function r45ayCheapScrollerSignature(scroller){
  scroller = scroller || r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_active_scroller'};
  return {
    ok:true,
    scrollHeight:scroller.scrollHeight || 0,
    scrollTop:scroller.scrollTop || 0,
    clientHeight:scroller.clientHeight || 0,
    childElementCount:scroller.childElementCount || 0,
    atBottom:(scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8)
  };
}
function r45ayCheapSignatureChanged(a, b){
  if (!a || !b || !a.ok || !b.ok) return true;
  return a.scrollHeight !== b.scrollHeight || a.scrollTop !== b.scrollTop || a.clientHeight !== b.clientHeight || a.childElementCount !== b.childElementCount || a.atBottom !== b.atBottom;
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
async function r45ayTrustedCdpSettle(opts){
  opts = opts || {};
  const started = performance.now();
  const maxMs = Math.max(40, Math.min(600, parseInt(opts.maxMs || 160, 10) || 160));
  const beforeSignature = opts.beforeScrollerSignature || null;
  let scroller = r45axGetScroller();
  if (!scroller) return {materialized:false, duration_ms:0, polls:0, reason:'no_active_scroller', after_scan:{}};
  let observer = null, resizeObserver = null, timeoutId = null, settled = false, polls = 0;
  const signatureNow = () => {
    scroller = r45axGetScroller() || scroller;
    polls += 1;
    return r45ayCheapScrollerSignature(scroller);
  };
  const changed = sig => r45ayCheapSignatureChanged(beforeSignature, sig);
  return await new Promise(resolve => {
    const finish = (sig, reason, observedChange) => {
      if (settled) return;
      settled = true;
      try { if (observer) observer.disconnect(); } catch(e) {}
      try { if (resizeObserver) resizeObserver.disconnect(); } catch(e) {}
      try { if (timeoutId) clearTimeout(timeoutId); } catch(e) {}
      const materialized = !!observedChange || changed(sig);
      resolve({
        materialized,
        duration_ms:Math.round((performance.now() - started) * 1000) / 1000,
        polls,
        reason,
        after_signature:sig,
        after_scan:{
          ok:!!(sig && sig.ok),
          marker:'R45AY_CHEAP_SETTLE_SIGNATURE',
          candidateCount:null,
          counts:null,
          items:[],
          scroller:sig && sig.ok ? {scrollTop:sig.scrollTop, scrollHeight:sig.scrollHeight, clientHeight:sig.clientHeight, atBottom:sig.atBottom} : {}
        }
      });
    };
    const checkAfterFrame = reason => {
      requestAnimationFrame(() => finish(signatureNow(), reason, true));
    };
    try {
      observer = new MutationObserver(() => checkAfterFrame('mutation'));
      observer.observe(scroller, {childList:true, subtree:true, characterData:true});
    } catch(e) {}
    try {
      resizeObserver = new ResizeObserver(() => checkAfterFrame('resize'));
      resizeObserver.observe(scroller);
    } catch(e) {}
    const initial = signatureNow();
    if (changed(initial)) {
      finish(initial, 'immediate_change', true);
      return;
    }
    timeoutId = setTimeout(() => finish(signatureNow(), 'timeout', false), maxMs);
  });
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


def sanitize_target_url(raw_url: str) -> Dict[str, Any]:
    """Reject ambiguous Markdown wrappers before Playwright navigation."""
    raw = str(raw_url or "").strip().strip('"').strip("'")
    match = re.fullmatch(r"\[([^\]]+)\]\((https?://[^)]+)\)", raw, flags=re.IGNORECASE)
    if match:
        href = match.group(2).replace("\\&", "&").replace("&amp;", "&").strip()
        label = match.group(1).replace("\\&", "&").strip()
        if href and (label == href or label.startswith("http://") or label.startswith("https://")):
            return {"ok": True, "url": href, "sanitized": True, "reason": "markdown_href_extracted"}
        return {"ok": False, "url": "", "sanitized": False, "reason": "markdown_label_href_mismatch"}
    if raw.startswith("[") or "](" in raw or (raw.count("http") > 1 and raw.endswith(")")):
        return {"ok": False, "url": "", "sanitized": False, "reason": "ambiguous_markdown_target_url"}
    return {"ok": True, "url": raw.replace("\\&", "&").replace("&amp;", "&"), "sanitized": False, "reason": "raw_url"}


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


def py_candidate_dedupe_key(item: Dict[str, Any]) -> str:
    label = str((item or {}).get("label") or "")
    category = str((item or {}).get("category") or "")
    y_band = str(round(float((item or {}).get("y") or 0.0) / 18.0))
    x_band = str(round(float((item or {}).get("x") or 0.0) / 28.0))
    stable = py_stable_candidate_key(item)
    return "|".join([category, label, y_band, x_band, stable])


def dedupe_candidates(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []
    for item in items or []:
        key = py_candidate_dedupe_key(item)
        if key in seen:
            duplicates.append(item)
            continue
        seen.add(key)
        out.append(item)
    return out, duplicates


def residual_candidate_position(item: Dict[str, Any], scan: Dict[str, Any]) -> int:
    scroller = (scan or {}).get("scroller") or {}
    try:
        return max(0, int(float(scroller.get("scrollTop") or 0) + float((item or {}).get("y") or 0)))
    except Exception:
        return max(0, int(scroller.get("scrollTop") or 0))


def residual_queue_update(
    queue: Dict[str, Dict[str, Any]],
    item: Dict[str, Any],
    *,
    step: int,
    scan: Dict[str, Any],
    result: str,
    reject_reason: str = "",
) -> str:
    key = py_stable_candidate_key(item)
    position = residual_candidate_position(item, scan)
    band = int(position / 350)
    entry = queue.get(key)
    marker = "R45AY_RESIDUAL_QUEUE_UPDATE" if entry else "R45AY_RESIDUAL_QUEUE_ADD"
    if not entry:
        entry = {
            "category": str((item or {}).get("category") or ""),
            "label": str((item or {}).get("label") or ""),
            "contextual_key": key,
            "approx_scroll_position": position,
            "band": band,
            "first_seen_step": step,
            "attempt_count": 0,
            "last_result": "",
            "last_reject_reason": "",
        }
        queue[key] = entry
    entry["last_seen_step"] = step
    entry["approx_scroll_position"] = min(int(entry.get("approx_scroll_position") or position), position)
    entry["band"] = min(int(entry.get("band") or band), band)
    entry["last_result"] = result
    if reject_reason:
        entry["last_reject_reason"] = reject_reason
    if result in {"clicked", "clicked_no_materialization", "rejected"}:
        entry["attempt_count"] = int(entry.get("attempt_count") or 0) + 1
    log(marker, {
        "key": key,
        "label": entry.get("label"),
        "category": entry.get("category"),
        "band": entry.get("band"),
        "position": entry.get("approx_scroll_position"),
        "step": step,
        "attempt_count": entry.get("attempt_count"),
        "last_result": entry.get("last_result"),
        "last_reject_reason": entry.get("last_reject_reason"),
    })
    return key


def residual_queue_merge_text_candidates(
    queue: Dict[str, Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    *,
    step: int,
) -> Dict[str, Any]:
    added = 0
    updated = 0
    labels: List[str] = []
    positions: List[int] = []
    for item in candidates or []:
        key = str(item.get("contextual_key") or item.get("key") or py_stable_candidate_key(item))
        if not key:
            continue
        position = max(0, int(float(item.get("approx_scroll_position") or 0)))
        band = int(position / 350)
        labels.append(str(item.get("label") or ""))
        positions.append(position)
        entry = queue.get(key)
        marker = "R45AY_RESIDUAL_QUEUE_UPDATE" if entry else "R45AY_RESIDUAL_QUEUE_ADD"
        if not entry:
            queue[key] = {
                "category": str(item.get("category") or ""),
                "label": str(item.get("label") or ""),
                "contextual_key": key,
                "approx_scroll_position": position,
                "band": band,
                "first_seen_step": step,
                "last_seen_step": step,
                "attempt_count": 0,
                "last_result": "text_locator_seen",
                "last_reject_reason": "",
                "source": "loaded_scroller_text_locator",
            }
            added += 1
        else:
            entry["last_seen_step"] = step
            entry["approx_scroll_position"] = min(int(entry.get("approx_scroll_position") or position), position)
            entry["band"] = min(int(entry.get("band") or band), band)
            entry["last_result"] = "text_locator_seen"
            updated += 1
        log(marker, {
            "key": key,
            "label": str(item.get("label") or ""),
            "category": str(item.get("category") or ""),
            "band": band,
            "position": position,
            "step": step,
            "last_result": "text_locator_seen",
        })
    summary = {
        "text_candidates": len(candidates or []),
        "added": added,
        "updated": updated,
        "queue_size": len(queue),
        "labels": sorted(set(label for label in labels if label))[:40],
        "approx_positions": positions[:40],
    }
    log("R45AY_RESIDUAL_QUEUE_TEXT_MERGE", summary)
    return summary


def residual_queue_resolve(queue: Dict[str, Dict[str, Any]], item: Dict[str, Any], *, step: int, reason: str) -> None:
    key = py_stable_candidate_key(item)
    if key in queue:
        entry = queue.pop(key)
        log("R45AY_RESIDUAL_QUEUE_UPDATE", {
            "key": key,
            "label": entry.get("label"),
            "category": entry.get("category"),
            "step": step,
            "last_result": "resolved",
            "reason": reason,
            "remaining": len(queue),
        })


def residual_queue_resolve_near(
    queue: Dict[str, Dict[str, Any]],
    *,
    position: int,
    client_height: int,
    step: int,
    reason: str,
) -> int:
    low = max(0, int(position) - 220)
    high = max(low + 1, int(position) + max(220, int(client_height)) + 420)
    removed = 0
    for key, entry in list(queue.items()):
        entry_pos = int(entry.get("approx_scroll_position") or 0)
        if low <= entry_pos <= high:
            queue.pop(key, None)
            removed += 1
            log("R45AY_RESIDUAL_QUEUE_UPDATE", {
                "key": key,
                "label": entry.get("label"),
                "category": entry.get("category"),
                "step": step,
                "last_result": "resolved_nearby",
                "reason": reason,
                "position": entry_pos,
                "remaining": len(queue),
            })
    return removed


def scan_signature(scan: Dict[str, Any]) -> Dict[str, Any]:
    scroller = (scan or {}).get("scroller") or {}
    return {
        "scrollHeight": int(scroller.get("scrollHeight") or 0),
        "candidateCount": int((scan or {}).get("candidateCount") or 0),
        "counts": (scan or {}).get("counts") or {},
        "candidateKeys": sorted(py_stable_candidate_key(item) for item in ((scan or {}).get("items") or [])),
    }


def scroller_signature(scan: Dict[str, Any]) -> Dict[str, Any]:
    scroller = (scan or {}).get("scroller") or {}
    scroll_top = int(scroller.get("scrollTop") or 0)
    scroll_height = int(scroller.get("scrollHeight") or 0)
    client_height = int(scroller.get("clientHeight") or 0)
    return {
        "ok": bool(scroller),
        "scrollHeight": scroll_height,
        "scrollTop": scroll_top,
        "clientHeight": client_height,
        "childElementCount": int(scroller.get("childElementCount") or 0),
        "atBottom": bool(scroll_top + client_height >= scroll_height - 8) if client_height else bool(scroller.get("atBottom")),
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
window.r45ayVisibleScrollerText = r45ayVisibleScrollerText;
window.r45ayExpansionTextMatches = r45ayExpansionTextMatches;
window.r45ayTrustedPointSafety = r45ayTrustedPointSafety;
window.r45ayValidateTrustedCdpItems = r45ayValidateTrustedCdpItems;
window.r45ayScanOrdered = r45ayScanOrdered;
window.r45ayScroll = r45ayScroll;
window.r45ayFastVisibleCandidates = r45ayFastVisibleCandidates;
window.r45ayCommentFilterState = r45ayCommentFilterState;
window.r45ayProgressEvidenceScan = r45ayProgressEvidenceScan;
window.r45ayPageLoopScan = r45ayPageLoopScan;
window.r45ayTrustedCdpSettle = r45ayTrustedCdpSettle;
window.r45ayDispatchPageBurst = r45ayDispatchPageBurst;
window.r45ayFinalBlockEvidence = r45ayFinalBlockEvidence;
window.r45ayLocateExpansionTextCandidates = r45ayLocateExpansionTextCandidates;
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
    page,
    cdp_session: Any,
    items: List[Dict[str, Any]],
    *,
    max_clicks: int,
    debug_clicks: bool = False,
    no_hover_clicks: bool = True,
) -> Dict[str, Any]:
    preselected = list(items or [])[:max(1, min(80, max_clicks))]
    validation = await page.evaluate("(items) => r45ayValidateTrustedCdpItems(items)", preselected)
    selected = list((validation or {}).get("accepted") or [])
    rejected = list((validation or {}).get("rejected") or [])
    if rejected:
        log("R45AY_TRUSTED_CDP_REJECTED_CANDIDATE", {
            "rejected_count": len(rejected),
            "items": [
                {
                    "label": item.get("label"),
                    "category": item.get("category"),
                    "reason": item.get("reason"),
                    "x": item.get("x"),
                    "y": item.get("y"),
                    "href": (((item.get("safety") or {}).get("href")) or ""),
                }
                for item in rejected[:12]
            ],
        })
    if not selected:
        return {"ok": False, "reason": "no_validated_trusted_points", "clicked": 0, "items": [], "click_timings": [], "rejected": rejected}
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
        events = []
        if not no_hover_clicks:
            events.append({"type": "mouseMoved", "x": x, "y": y, "button": "none"})
        events.extend([
            {"type": "mousePressed", "x": x, "y": y, "button": "left", "buttons": 1, "clickCount": 1},
            {"type": "mouseReleased", "x": x, "y": y, "button": "left", "buttons": 0, "clickCount": 1},
        ])
        for params in events:
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
        "cdp_events_per_click": round(event_count / max(len(selected), 1), 3),
        "no_hover_clicks": bool(no_hover_clicks),
        "cdp_send_elapsed_ms": elapsed_ms,
        "errors": errors[:10],
        "rejected": rejected,
        "prevalidated_count": len(preselected),
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
    before_scroller_sig = scroller_signature(before_scan)
    before_progress = before_scan.get("progress")
    after_scan = before_scan
    settle = await page.evaluate(
        "(opts) => r45ayTrustedCdpSettle(opts)",
        {
            "maxMs": max_ms,
            "maxCandidates": 60,
            "includeGuardedViewMore": include_guarded_view_more,
            "beforeScrollerSignature": before_scroller_sig,
        },
    )
    after_scan = (settle or {}).get("after_scan") or before_scan
    materialized = bool((settle or {}).get("materialized"))
    polls = int((settle or {}).get("polls") or 0)
    duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
    before_scroll_height = ((before_scan or {}).get("scroller") or {}).get("scrollHeight")
    after_scroll_height = (((after_scan or {}).get("scroller") or {}).get("scrollHeight"))
    before_candidates = int((before_scan or {}).get("candidateCount") or 0)
    after_candidate_value = (after_scan or {}).get("candidateCount")
    after_candidates = int(after_candidate_value) if after_candidate_value is not None else None
    reason = (settle or {}).get("reason") or "unknown"
    materialization_reason = "no_change"
    if int(after_scroll_height or 0) > int(before_scroll_height or 0):
        materialization_reason = "scrollHeight_growth"
        materialized = True
    elif after_candidates is not None and after_candidates != before_candidates:
        materialization_reason = "candidate_list_changed"
        materialized = True
    elif materialized:
        materialization_reason = str(reason)
    return {
        "duration_ms": duration_ms,
        "polls": polls,
        "materialized": materialized,
        "after_scan": after_scan,
        "reason": reason,
        "materialization_reason": materialization_reason,
        "progress_before": before_scan.get("progress"),
        "progress_after": (after_scan or {}).get("progress"),
        "scroll_height_before": before_scroll_height,
        "scroll_height_after": after_scroll_height,
        "visible_candidates_after": after_candidates,
    }


async def trusted_wheel_scroll(page, cdp_session: Any, delta_y: float) -> Dict[str, Any]:
    """Send a real wheel event over the visible browser input boundary."""
    point = await page.evaluate(
        """() => {
          const s = r45axGetScroller();
          if (!s) return null;
          const r = s.getBoundingClientRect();
          return {x: Math.max(1, r.left + r.width / 2), y: Math.max(1, r.top + Math.min(r.height / 2, 400))};
        }"""
    )
    if not point:
        return {"ok": False, "reason": "no_active_scroller"}
    params = {
        "type": "mouseWheel",
        "x": float(point["x"]),
        "y": float(point["y"]),
        "deltaX": 0,
        "deltaY": float(delta_y),
    }
    try:
        await cdp_session.send("Input.dispatchMouseEvent", params)
        return {"ok": True, "method": "cdp_mouseWheel", "delta_y": float(delta_y), "point": point}
    except Exception as cdp_error:
        try:
            await page.mouse.wheel(0, float(delta_y))
            return {"ok": True, "method": "playwright_mouse_wheel_fallback", "delta_y": float(delta_y), "point": point}
        except Exception as wheel_error:
            return {"ok": False, "reason": "wheel_dispatch_failed", "cdp_error": repr(cdp_error), "wheel_error": repr(wheel_error)}


async def progress_evidence_scan(page, expected_total: int, *, mode: str, step: int = 0, reason: str = "") -> Dict[str, Any]:
    result = await page.evaluate(
        "(opts) => r45ayProgressEvidenceScan(opts.expectedTotal, opts.mode)",
        {"expectedTotal": int(expected_total or 0), "mode": mode},
    )
    progress = r45ax_filter_expected_progress((result or {}).get("progress"), int(expected_total or 0))
    log("R45AY_PROGRESS_SCAN", {
        "step": step,
        "mode": mode,
        "reason": reason,
        "progress": progress or (result or {}).get("progress"),
        "expected_total": int(expected_total or 0),
        "evidence": (result or {}).get("expectedTotalEvidence"),
        "duration_ms": (result or {}).get("durationMs"),
        "source": "visible_scroller_viewport" if mode == "cheap" else "scroller_body_aria_title_html",
    })
    return {**(result or {}), "filtered_progress": progress}


async def false_bottom_recovery(
    page,
    cdp_session: Any,
    args: argparse.Namespace,
    *,
    expected_total: int,
    recovery_number: int,
) -> Dict[str, Any]:
    """Give virtualized comment lists a bounded top/bottom materialization chance."""
    log("R45AY_FALSE_BOTTOM_RECOVERY_START", {"recovery": recovery_number, "expected_total": expected_total})
    actions = [("top", 0), ("bottom", 0), ("wheel_up", -520), ("wheel_down", 920), ("bottom", 0)]
    loader_clicks = 0
    boundary_clicks = 0
    height_before = 0
    height_after = 0
    progress_before = None
    progress_after = None
    boundary_text = {"top": "", "bottom": ""}
    initial_progress_scan = await progress_evidence_scan(page, expected_total, mode="heavy", reason="false_bottom_before_recovery")
    progress_before = initial_progress_scan.get("filtered_progress")
    for action, delta in actions:
        if action.startswith("wheel"):
            scroll_result = await trusted_wheel_scroll(page, cdp_session, delta)
        else:
            scroll_result = await page.evaluate("(mode) => r45ayScroll(mode)", action)
        log("R45AY_FALSE_BOTTOM_RECOVERY_SCROLL", {"recovery": recovery_number, "mode": action, "scroll": scroll_result})
        await page.wait_for_timeout(55 if action != "bottom" else 80)
        scan = await page.evaluate(
            "(opts) => r45ayPageLoopScan(opts)",
            {"maxCandidates": 50, "includeGuardedViewMore": bool(args.include_guarded_view_more), "expectedTotal": expected_total},
        )
        scroller = (scan or {}).get("scroller") or {}
        height_before = max(height_before, int(scroller.get("scrollHeight") or 0))
        before_signature = scan_signature(scan)
        boundary_candidates = list((scan or {}).get("items") or [])
        loaders = [item for item in boundary_candidates if item.get("category") == "comment_list_loader"]
        expansions = [item for item in boundary_candidates if item.get("category") != "comment_list_loader"]
        labels_summary = [str(item.get("label") or "") for item in boundary_candidates[:16]]
        log("R45AY_FALSE_BOTTOM_BOUNDARY_CANDIDATES", {
            "recovery": recovery_number,
            "mode": action,
            "candidate_count": len(boundary_candidates),
            "loader_count": len(loaders),
            "expansion_count": len(expansions),
            "labels": labels_summary,
            "rejected_count": len(list((scan or {}).get("rejected") or [])),
            "scrollTop": scroller.get("scrollTop"),
            "scrollHeight": scroller.get("scrollHeight"),
        })
        log("R45AY_LOADER_CANDIDATES", {
            "recovery": recovery_number,
            "mode": action,
            "count": len(loaders),
            "items": [{"label": item.get("label"), "category": item.get("category"), "key": item.get("key"), "inside_active_scroller": bool(item.get("insideActiveScroller", True)), "safety": item.get("safety")} for item in loaders[:8]],
        })
        log("R45AY_EXPANSION_CANDIDATES_AT_BOTTOM", {
            "recovery": recovery_number,
            "mode": action,
            "count": len(expansions),
            "items": [{"label": item.get("label"), "category": item.get("category"), "key": item.get("key"), "inside_active_scroller": bool(item.get("insideActiveScroller", True)), "safety": item.get("safety")} for item in expansions[:12]],
        })
        rejected = list((scan or {}).get("rejected") or [])
        if rejected:
            log("R45AY_FALSE_BOTTOM_REJECTED_CANDIDATE", {"recovery": recovery_number, "mode": action, "count": len(rejected), "items": rejected[:8]})
        if boundary_candidates:
            burst = await trusted_cdp_burst(
                page,
                cdp_session,
                boundary_candidates,
                max_clicks=min(20, len(boundary_candidates)),
                debug_clicks=bool(args.debug_clicks),
                no_hover_clicks=bool(getattr(args, "no_hover_clicks", True)),
            )
            clicked_in_burst = int(burst.get("clicked") or 0)
            boundary_clicks += clicked_in_burst
            loader_clicks += sum(1 for item in list(burst.get("items") or []) if item.get("category") == "comment_list_loader")
            log("R45AY_FALSE_BOTTOM_RECOVERY_CLICK", {
                "recovery": recovery_number,
                "mode": action,
                "candidate_count": len(boundary_candidates),
                "clicked": clicked_in_burst,
                "labels": [item.get("label") for item in boundary_candidates[:12]],
            })
            log("R45AY_FALSE_BOTTOM_RECOVERY_BURST", {
                "recovery": recovery_number,
                "mode": action,
                "candidate_count": len(boundary_candidates),
                "clicked": clicked_in_burst,
                "loader_clicks": loader_clicks,
                "expansion_candidates": len(expansions),
                "materialized_hint": bool(burst.get("clicked")),
            })
            await page.wait_for_timeout(75)
        refreshed = await page.evaluate(
            "(opts) => r45ayPageLoopScan(opts)",
            {"maxCandidates": 50, "includeGuardedViewMore": bool(args.include_guarded_view_more), "includeProgress": False, "includeExpectedEvidence": False},
        )
        refreshed_scroller = (refreshed or {}).get("scroller") or {}
        height_after = max(height_after, int(refreshed_scroller.get("scrollHeight") or 0))
        refreshed_progress_scan = await progress_evidence_scan(page, expected_total, mode="heavy", reason=f"false_bottom_after_{action}")
        refreshed_progress = refreshed_progress_scan.get("filtered_progress")
        if refreshed_progress and (not progress_after or int(refreshed_progress.get("current") or 0) > int(progress_after.get("current") or 0)):
            progress_after = refreshed_progress
        after_signature = scan_signature(refreshed)
        progress_improved = bool(
            progress_after
            and (
                not progress_before
                or int(progress_after.get("current") or 0) > int(progress_before.get("current") or 0)
            )
        )
        before_candidate_count = int((scan or {}).get("candidateCount") or 0)
        after_candidate_count = int((refreshed or {}).get("candidateCount") or 0)
        candidate_signature_changed = signature_changed(before_signature, after_signature)
        new_visible_controls = after_candidate_count > before_candidate_count
        materialized = (
            height_after > height_before
            or progress_improved
            or candidate_signature_changed
            or new_visible_controls
        )
        if materialized:
            return {
                "recovered": True,
                "clicked": boundary_clicks,
                "loader_clicks": loader_clicks,
                "scroll_height_before": height_before,
                "scroll_height_after": height_after,
                "progress_before": progress_before,
                "progress_after": progress_after,
                "materialized_reason": {
                    "scroll_height_increased": height_after > height_before,
                    "progress_improved": progress_improved,
                    "candidate_signature_changed": candidate_signature_changed,
                    "new_visible_controls": new_visible_controls,
                    "before_candidate_count": before_candidate_count,
                    "after_candidate_count": after_candidate_count,
                },
            }
    boundary_text = await page.evaluate(
        """() => {
          const s = r45axGetScroller();
          const text = s ? String(s.innerText || s.textContent || '') : '';
          return {top: text.slice(0, 1200), bottom: text.slice(Math.max(0, text.length - 1200))};
        }"""
    )
    result = {
        "recovered": False,
        "clicked": boundary_clicks,
        "loader_clicks": loader_clicks,
        "scroll_height_before": height_before,
        "scroll_height_after": height_after,
        "progress_before": progress_before,
        "progress_after": progress_after,
        "visible_boundary_text": boundary_text,
    }
    log("R45AY_FALSE_BOTTOM_RECOVERY_RESULT", {"recovery": recovery_number, **result})
    return result


def large_bucket_items(items: List[Dict[str, Any]], *, min_count: int = 20) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items or []:
        category = str((item or {}).get("category") or "")
        if category not in {"view_all_replies", "replied_bucket"}:
            continue
        reply_count = int((item or {}).get("replyCount") or 0)
        if reply_count >= min_count:
            out.append(item)
    return out


async def large_bucket_bootstrap(
    page,
    cdp_session: Any,
    args: argparse.Namespace,
    *,
    expected_total: int,
) -> Dict[str, Any]:
    log("R45AY_LARGE_BUCKET_BOOTSTRAP_START", {"expected_total": expected_total, "min_reply_count": 20})
    clicked = 0
    bursts = 0
    materialized = 0
    rejected: List[Dict[str, Any]] = []
    labels_seen: List[str] = []
    scans = 0
    viewport = await page.evaluate("""() => {
      const s = r45axGetScroller();
      return s ? {clientHeight:Math.max(220, s.clientHeight || 520), scrollHeight:s.scrollHeight || 0} : {clientHeight:520, scrollHeight:0};
    }""")
    step_px = max(260, int(float((viewport or {}).get("clientHeight") or 520) * 0.45))
    scan_positions = [0, step_px, step_px * 2, step_px * 3, step_px * 4, step_px * 5, step_px * 6, step_px * 7]
    for pass_index, scroll_top in enumerate(scan_positions, start=1):
        await page.evaluate(
            """(top) => {
              const s = r45axGetScroller();
              if (s) s.scrollTop = Math.max(0, Math.min(Number(top)||0, Math.max(0, (s.scrollHeight||0) - (s.clientHeight||0))));
            }""",
            scroll_top,
        )
        await page.wait_for_timeout(45)
        scan = await page.evaluate(
            "(opts) => r45ayPageLoopScan(opts)",
            {
                "maxCandidates": 80,
                "includeGuardedViewMore": bool(args.include_guarded_view_more),
                "expectedTotal": expected_total,
                "includeProgress": False,
                "includeExpectedEvidence": False,
            },
        )
        scans += 1
        items = list((scan or {}).get("items") or [])
        large_raw = large_bucket_items(items, min_count=20)
        large, duplicate_large = dedupe_candidates(large_raw)
        if duplicate_large:
            log("R45AY_CANDIDATE_DEDUPE", {
                "scope": "large_bucket_bootstrap",
                "pass": pass_index,
                "duplicate_count": len(duplicate_large),
                "labels": [item.get("label") for item in duplicate_large[:12]],
            })
        labels_seen.extend(str(item.get("label") or "") for item in large)
        log("R45AY_LARGE_BUCKET_BOOTSTRAP_SCAN", {
            "pass": pass_index,
            "candidate_count": len(items),
            "large_bucket_count": len(large),
            "labels": [item.get("label") for item in large[:12]],
            "reply_counts": [item.get("replyCount") for item in large[:12]],
            "scroll": (scan or {}).get("scroller"),
            "scroll_target": scroll_top,
        })
        if not large:
            rejected.extend([
                {
                    "label": item.get("label"),
                    "category": item.get("category"),
                    "replyCount": item.get("replyCount"),
                    "reason": "not_large_bucket",
                }
                for item in items[:12]
                if str(item.get("category") or "") in {"view_all_replies", "replied_bucket"}
            ])
            continue
        burst = await trusted_cdp_burst(
            page,
            cdp_session,
            large,
            max_clicks=min(20, len(large)),
            debug_clicks=bool(args.debug_clicks),
            no_hover_clicks=bool(getattr(args, "no_hover_clicks", True)),
        )
        clicked_now = int(burst.get("clicked") or 0)
        clicked += clicked_now
        bursts += 1
        settle = await settle_after_trusted_cdp_burst(
            page,
            scan,
            max_ms=max(160, min(450, int(getattr(args, "forward_settle_max_ms", 350) or 350))),
            include_guarded_view_more=bool(args.include_guarded_view_more),
            expected_total=expected_total,
        )
        if settle.get("materialized"):
            materialized += 1
        log("R45AY_LARGE_BUCKET_BOOTSTRAP_BURST", {
            "pass": pass_index,
            "candidate_count": len(large),
            "clicked": clicked_now,
            "labels": [item.get("label") for item in large[:12]],
            "reply_counts": [item.get("replyCount") for item in large[:12]],
            "cdp_event_count": burst.get("cdp_event_count"),
            "cdp_events_per_click": burst.get("cdp_events_per_click"),
            "no_hover_clicks": burst.get("no_hover_clicks"),
            "settle_ms": settle.get("duration_ms"),
            "materialized": settle.get("materialized"),
        })
        await page.evaluate("(mode) => r45ayScroll(mode)", "top")
    result = {
        "clicked": clicked,
        "bursts": bursts,
        "materializedBursts": materialized,
        "scans": scans,
        "labelsSeen": sorted(set(label for label in labels_seen if label)),
        "rejected": rejected[:20],
    }
    await page.evaluate("(mode) => r45ayScroll(mode)", "top")
    log("R45AY_LARGE_BUCKET_BOOTSTRAP_DONE", result)
    return result


async def full_sweep_retry(
    page,
    cdp_session: Any,
    args: argparse.Namespace,
    *,
    expected_total: int,
    retry_number: int,
    started_monotonic: Optional[float] = None,
    max_seconds: float = 0.0,
) -> Dict[str, Any]:
    log("R45AY_FULL_SURFACE_SWEEP_START", {"retry": retry_number, "expected_total": expected_total})
    clicked = 0
    bursts = 0
    materialized = 0
    max_scroll_height = 0
    candidate_scans = 0
    bands_scanned = 0
    coverage_intervals: List[Tuple[int, int]] = []
    labels_seen: List[str] = []
    stopped_by_time_budget = False
    sweep_started = time.perf_counter()
    local_inert: Dict[str, int] = {}
    initial_state = await page.evaluate("""() => {
      const s = r45axGetScroller();
      return s ? {
        scrollTop:Math.round(s.scrollTop||0),
        scrollHeight:Math.round(s.scrollHeight||0),
        clientHeight:Math.round(s.clientHeight||0),
        atBottom:(s.scrollTop+s.clientHeight>=s.scrollHeight-8)
      } : {scrollTop:0, scrollHeight:0, clientHeight:0, atBottom:true};
    }""")
    scroll_height_start = int((initial_state or {}).get("scrollHeight") or 0)
    client_height_start = max(220, int((initial_state or {}).get("clientHeight") or 0) or 520)
    for direction in ("top_to_bottom", "bottom_to_top"):
        state = await page.evaluate("""(dir) => {
          const s = r45axGetScroller();
          if (!s) return {scrollTop:0, scrollHeight:0, clientHeight:0, atBottom:true, ok:false};
          s.scrollTop = dir === 'top_to_bottom' ? 0 : Math.max(0, (s.scrollHeight||0) - (s.clientHeight||0));
          return {ok:true, scrollTop:Math.round(s.scrollTop||0), scrollHeight:Math.round(s.scrollHeight||0), clientHeight:Math.round(s.clientHeight||0), atBottom:(s.scrollTop+s.clientHeight>=s.scrollHeight-8)};
        }""", direction)
        await page.wait_for_timeout(35)
        pass_clicked = 0
        pass_growth = False
        index = 0
        visited_static = set()
        while True:
            if started_monotonic is not None and max_seconds and (time.monotonic() - started_monotonic) >= max_seconds:
                stopped_by_time_budget = True
                break
            state = await page.evaluate("""() => {
              const s = r45axGetScroller();
              return s ? {
                ok:true,
                scrollTop:Math.round(s.scrollTop||0),
                scrollHeight:Math.round(s.scrollHeight||0),
                clientHeight:Math.round(s.clientHeight||0),
                atBottom:(s.scrollTop+s.clientHeight>=s.scrollHeight-8)
              } : {ok:false, scrollTop:0, scrollHeight:0, clientHeight:0, atBottom:true};
            }""")
            scroll_height = int((state or {}).get("scrollHeight") or 0)
            client_height = max(220, int((state or {}).get("clientHeight") or 0) or client_height_start)
            scroll_top = int((state or {}).get("scrollTop") or 0)
            max_top = max(0, scroll_height - client_height)
            max_scroll_height = max(max_scroll_height, scroll_height)
            step_px = max(160, min(350, int(client_height * 0.55)))
            band_key = (direction, round(scroll_top / max(step_px, 1)))
            if band_key in visited_static and not pass_growth:
                break
            visited_static.add(band_key)
            coverage_intervals.append((max(0, scroll_top), min(scroll_height, scroll_top + client_height)))
            scan = await page.evaluate(
                "(opts) => r45ayPageLoopScan(opts)",
                {
                    "maxCandidates": int(args.max_burst_clicks or 30),
                    "includeGuardedViewMore": bool(args.include_guarded_view_more),
                    "expectedTotal": expected_total,
                    "includeProgress": False,
                    "includeExpectedEvidence": False,
                },
            )
            candidate_scans += 1
            bands_scanned += 1
            scroller = (scan or {}).get("scroller") or {}
            scroll_height = int(scroller.get("scrollHeight") or scroll_height)
            scroll_top = int(scroller.get("scrollTop") or scroll_top)
            max_scroll_height = max(max_scroll_height, scroll_height)
            raw_candidates = list((scan or {}).get("items") or [])
            candidates, duplicate_candidates = dedupe_candidates(raw_candidates)
            if duplicate_candidates:
                log("R45AY_CANDIDATE_DEDUPE", {
                    "scope": "full_surface_sweep",
                    "retry": retry_number,
                    "direction": direction,
                    "band": index,
                    "duplicate_count": len(duplicate_candidates),
                    "labels": [item.get("label") for item in duplicate_candidates[:12]],
                })
            candidates = [item for item in candidates if local_inert.get(py_stable_candidate_key(item), 0) < 2]
            labels_seen.extend(str(item.get("label") or "") for item in candidates[:10])
            log("R45AY_FULL_SURFACE_SWEEP_BAND", {
                "retry": retry_number,
                "direction": direction,
                "band": index,
                "candidate_count": len(candidates),
                "raw_candidate_count": len(raw_candidates),
                "labels": [item.get("label") for item in candidates[:10]],
                "scrollTop": scroll_top,
                "scrollHeight": scroll_height,
                "clientHeight": int(scroller.get("clientHeight") or client_height),
                "step_px": step_px,
            })
            if candidates:
                burst = await trusted_cdp_burst(
                    page,
                    cdp_session,
                    candidates,
                    max_clicks=min(int(args.max_burst_clicks or 30), len(candidates)),
                    debug_clicks=bool(args.debug_clicks),
                    no_hover_clicks=bool(getattr(args, "no_hover_clicks", True)),
                )
                clicked_now = int(burst.get("clicked") or 0)
                clicked += clicked_now
                pass_clicked += clicked_now
                bursts += 1
                settle = await settle_after_trusted_cdp_burst(
                    page,
                    scan,
                    max_ms=1000,
                    include_guarded_view_more=bool(args.include_guarded_view_more),
                    expected_total=expected_total,
                )
                if settle.get("materialized"):
                    materialized += 1
                    pass_growth = True
                    for item in candidates:
                        local_inert.pop(py_stable_candidate_key(item), None)
                else:
                    for item in candidates[: max(1, clicked_now)]:
                        key = py_stable_candidate_key(item)
                        local_inert[key] = local_inert.get(key, 0) + 1
                log("R45AY_FULL_SURFACE_SWEEP_BURST", {
                    "retry": retry_number,
                    "direction": direction,
                    "band": index,
                    "candidate_count": len(candidates),
                    "clicked": clicked_now,
                    "labels": [item.get("label") for item in candidates[:10]],
                    "cdp_event_count": burst.get("cdp_event_count"),
                    "cdp_events_per_click": burst.get("cdp_events_per_click"),
                    "no_hover_clicks": burst.get("no_hover_clicks"),
                    "settle_ms": settle.get("duration_ms"),
                    "materialized": settle.get("materialized"),
                })
                index += 1
                continue
            if direction == "top_to_bottom":
                next_top = min(max_top, scroll_top + step_px)
                if next_top <= scroll_top + 2 and scroll_top >= max_top - 4:
                    break
            else:
                next_top = max(0, scroll_top - step_px)
                if next_top >= scroll_top - 2 and scroll_top <= 4:
                    break
            await page.evaluate(
                """(top) => {
                  const s = r45axGetScroller();
                  if (s) s.scrollTop = Math.max(0, Math.min(Number(top)||0, Math.max(0, (s.scrollHeight||0) - (s.clientHeight||0))));
                }""",
                next_top,
            )
            await page.wait_for_timeout(24)
            new_state = await page.evaluate("""() => {
              const s = r45axGetScroller();
              return s ? {scrollTop:Math.round(s.scrollTop||0), scrollHeight:Math.round(s.scrollHeight||0), clientHeight:Math.round(s.clientHeight||0), atBottom:(s.scrollTop+s.clientHeight>=s.scrollHeight-8)} : {scrollTop:0, scrollHeight:0, clientHeight:0, atBottom:true};
            }""")
            if int(new_state.get("scrollTop") or 0) == scroll_top and int(new_state.get("scrollHeight") or 0) == scroll_height:
                break
            index += 1
        if stopped_by_time_budget:
            break
        log("R45AY_FULL_SWEEP_RETRY_PASS", {"retry": retry_number, "direction": direction, "pass_clicked": pass_clicked, "pass_growth": pass_growth})
    merged: List[Tuple[int, int]] = []
    for start, end in sorted((max(0, a), max(0, b)) for a, b in coverage_intervals if b > a):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    covered_px = sum(end - start for start, end in merged)
    final_state = await page.evaluate("""() => {
      const s = r45axGetScroller();
      return s ? {scrollTop:Math.round(s.scrollTop||0), scrollHeight:Math.round(s.scrollHeight||0), clientHeight:Math.round(s.clientHeight||0), atBottom:(s.scrollTop+s.clientHeight>=s.scrollHeight-8)} : {scrollTop:0, scrollHeight:0, clientHeight:0, atBottom:true};
    }""")
    scroll_height_end = int((final_state or {}).get("scrollHeight") or max_scroll_height)
    max_scroll_height = max(max_scroll_height, scroll_height_end)
    coverage_percent = round(min(100.0, (covered_px / max(max_scroll_height, 1)) * 100.0), 2)
    completed = not stopped_by_time_budget and coverage_percent >= 92.0 and bands_scanned > 5
    result = {
        "retry": retry_number,
        "clicked": clicked,
        "bursts": bursts,
        "materializedBursts": materialized,
        "candidateScans": candidate_scans,
        "bandsScanned": bands_scanned,
        "maxScrollHeight": max_scroll_height,
        "scrollHeightStart": scroll_height_start,
        "scrollHeightEnd": scroll_height_end,
        "coveragePercent": coverage_percent,
        "fullSurfaceSweepCompleted": completed,
        "stoppedByTimeBudget": stopped_by_time_budget,
        "elapsedMs": round((time.perf_counter() - sweep_started) * 1000.0, 3),
        "labelsSeen": sorted(set(label for label in labels_seen if label))[:40],
    }
    log("R45AY_FULL_SURFACE_SWEEP_DONE", result)
    log("R45AY_FULL_SWEEP_RETRY_DONE", result)
    return result


async def collect_final_block_evidence(
    page,
    args: argparse.Namespace,
    *,
    include_guarded: bool,
    full_sweep_result: Dict[str, Any],
) -> Dict[str, Any]:
    top_scan = await page.evaluate(
        """(opts) => {
          r45ayScroll('top');
          return r45ayPageLoopScan(opts);
        }""",
        {"maxCandidates": 80, "includeGuardedViewMore": include_guarded, "includeProgress": False, "includeExpectedEvidence": False},
    )
    bottom_scan = await page.evaluate(
        """(opts) => {
          r45ayScroll('bottom');
          return r45ayPageLoopScan(opts);
        }""",
        {"maxCandidates": 80, "includeGuardedViewMore": include_guarded, "includeProgress": False, "includeExpectedEvidence": False},
    )
    state = await page.evaluate("""() => {
      const s = r45axGetScroller();
      return s ? {scrollTop:Math.round(s.scrollTop||0), scrollHeight:Math.round(s.scrollHeight||0), clientHeight:Math.round(s.clientHeight||0), atBottom:(s.scrollTop+s.clientHeight>=s.scrollHeight-8)} : {scrollTop:0, scrollHeight:0, clientHeight:0, atBottom:true};
    }""")
    scroll_height = int((state or {}).get("scrollHeight") or 0)
    client_height = max(220, int((state or {}).get("clientHeight") or 0) or 520)
    step_px = max(320, min(900, int(client_height * 0.8)))
    positions = list(range(0, max(1, scroll_height), step_px))
    bottom_pos = max(0, scroll_height - client_height)
    if bottom_pos not in positions:
        positions.append(bottom_pos)
    positions = sorted(set(max(0, min(pos, bottom_pos)) for pos in positions))
    sampled_matches: List[str] = []
    sampled_candidate_count = 0
    sampled_rejected_count = 0
    sampled_bands = 0
    for pos in positions:
        await page.evaluate(
            """(top) => {
              const s = r45axGetScroller();
              if (s) s.scrollTop = Math.max(0, Math.min(Number(top)||0, Math.max(0, (s.scrollHeight||0) - (s.clientHeight||0))));
            }""",
            pos,
        )
        await page.wait_for_timeout(12)
        sample = await page.evaluate(
            """(opts) => {
              const s = r45axGetScroller();
              const text = s ? r45ayVisibleScrollerText(s) : '';
              const scan = r45ayPageLoopScan(opts);
              return {
                matches:r45ayExpansionTextMatches(text),
                candidateCount:scan.candidateCount || 0,
                rejectedCount:(scan.rejected || []).length,
                labels:(scan.items || []).map(item => item.label).slice(0, 12),
                scroll:scan.scroller || null
              };
            }""",
            {"maxCandidates": 80, "includeGuardedViewMore": include_guarded, "includeProgress": False, "includeExpectedEvidence": False},
        )
        sampled_bands += 1
        sampled_candidate_count += int((sample or {}).get("candidateCount") or 0)
        sampled_rejected_count += int((sample or {}).get("rejectedCount") or 0)
        sampled_matches.extend(str(label) for label in ((sample or {}).get("matches") or []) if label)
    base = await page.evaluate(
        "(opts) => r45ayFinalBlockEvidence(opts)",
        {"includeGuardedViewMore": include_guarded},
    )
    expansion_matches = sorted(set(list((base or {}).get("expansion_text_matches") or []) + sampled_matches))[:80]
    full_completed = bool((full_sweep_result or {}).get("fullSurfaceSweepCompleted"))
    full_candidates = int((full_sweep_result or {}).get("candidateScans") or 0)
    top_candidates = int((top_scan or {}).get("candidateCount") or 0)
    bottom_candidates = int((bottom_scan or {}).get("candidateCount") or 0)
    loaded_height = max(scroll_height, int((full_sweep_result or {}).get("maxScrollHeight") or 0))
    evidence = {
        **(base or {}),
        "full_surface_sweep_completed": full_completed,
        "bands_scanned": int((full_sweep_result or {}).get("bandsScanned") or 0),
        "loaded_scroll_height": loaded_height,
        "coverage_percent": float((full_sweep_result or {}).get("coveragePercent") or 0.0),
        "top_candidates": top_candidates,
        "bottom_candidates": bottom_candidates,
        "full_surface_candidates": sampled_candidate_count,
        "full_surface_candidate_scans": full_candidates,
        "full_surface_sampled_bands": sampled_bands,
        "expansion_text_matches": expansion_matches,
        "contains_expansion_text": bool(expansion_matches),
        "rejected_candidates": sampled_rejected_count + int((base or {}).get("rejected_candidates") or 0),
        "top_candidate_labels": [item.get("label") for item in list((top_scan or {}).get("items") or [])[:20]],
        "bottom_candidate_labels": [item.get("label") for item in list((bottom_scan or {}).get("items") or [])[:20]],
    }
    terminal = (
        full_completed
        and evidence["coverage_percent"] >= 92.0
        and top_candidates == 0
        and bottom_candidates == 0
        and sampled_candidate_count == 0
        and not expansion_matches
        and bool(((bottom_scan or {}).get("scroller") or {}).get("atBottom"))
    )
    evidence["terminal_block_proven"] = terminal
    evidence["reason_for_block"] = (
        "full_surface_sweep_completed_no_candidates_or_expansion_text"
        if terminal
        else "not_terminal_full_surface_or_candidates_still_visible"
    )
    return evidence


async def bottom_range_check(
    page,
    cdp_session: Any,
    args: argparse.Namespace,
    *,
    expected_total: int,
    check_number: int,
    started_monotonic: float,
    max_seconds: float,
) -> Dict[str, Any]:
    """Check only the loaded tail; the normal engine must not back-scan the whole list."""
    log("R45AY_BOTTOM_RANGE_CHECK_START", {"check": check_number, "expected_total": expected_total})
    state = await page.evaluate("""() => {
      const s = r45axGetScroller();
      return s ? {scrollTop:Math.round(s.scrollTop||0), scrollHeight:Math.round(s.scrollHeight||0), clientHeight:Math.round(s.clientHeight||0), atBottom:(s.scrollTop+s.clientHeight>=s.scrollHeight-8)} : {scrollTop:0, scrollHeight:0, clientHeight:0, atBottom:true};
    }""")
    height_start = int((state or {}).get("scrollHeight") or 0)
    client_height = max(220, int((state or {}).get("clientHeight") or 0) or 520)
    max_top = max(0, height_start - client_height)
    step_px = max(260, min(520, int(client_height * 0.85)))
    range_start = max(0, max_top - (client_height * 3))
    positions = list(range(range_start, max_top + 1, step_px))
    positions.extend([range_start, max_top])
    positions = sorted(set(max(0, min(max_top, int(pos))) for pos in positions))
    bands_scanned = 0
    clicked = 0
    bursts = 0
    materialized = 0
    candidate_labels: List[str] = []
    expansion_matches: List[str] = []
    safe_candidates = 0
    inert: Dict[str, int] = {}
    for band_index, position in enumerate(positions, start=1):
        if time.monotonic() - started_monotonic >= max_seconds:
            break
        await page.evaluate("""(top) => {
          const s = r45axGetScroller();
          if (s) s.scrollTop = Math.max(0, Math.min(Number(top)||0, Math.max(0, (s.scrollHeight||0)-(s.clientHeight||0))));
        }""", position)
        await page.wait_for_timeout(12)
        scan = await page.evaluate(
            "(opts) => r45ayPageLoopScan(opts)",
            {
                "maxCandidates": int(args.max_burst_clicks or 30),
                "includeGuardedViewMore": bool(args.include_guarded_view_more),
                "expectedTotal": expected_total,
                "includeProgress": False,
                "includeExpectedEvidence": False,
            },
        )
        bands_scanned += 1
        raw_items = list((scan or {}).get("items") or [])
        candidates, duplicates = dedupe_candidates(raw_items)
        if duplicates:
            log("R45AY_CANDIDATE_DEDUPE", {"scope": "bottom_range", "check": check_number, "band": band_index, "duplicate_count": len(duplicates)})
        candidates = [item for item in candidates if inert.get(py_stable_candidate_key(item), 0) < 1]
        safe_candidates += len(candidates)
        candidate_labels.extend(str(item.get("label") or "") for item in candidates[:10])
        text = await page.evaluate("""() => {
          const s = r45axGetScroller();
          return s ? r45ayExpansionTextMatches(r45ayVisibleScrollerText(s)) : [];
        }""")
        expansion_matches.extend(str(label) for label in (text or []) if label)
        log("R45AY_BOTTOM_RANGE_CHECK_BAND", {
            "check": check_number,
            "band": band_index,
            "position": position,
            "candidate_count": len(candidates),
            "labels": [item.get("label") for item in candidates[:10]],
            "scroll": (scan or {}).get("scroller"),
        })
        if not candidates:
            continue
        burst = await trusted_cdp_burst(
            page,
            cdp_session,
            candidates,
            max_clicks=min(int(args.max_burst_clicks or 30), len(candidates)),
            debug_clicks=bool(args.debug_clicks),
            no_hover_clicks=bool(getattr(args, "no_hover_clicks", True)),
        )
        clicked_now = int(burst.get("clicked") or 0)
        clicked += clicked_now
        bursts += 1
        settle_limit = max(
            int(getattr(args, "forward_settle_ms", 120) or 120),
            min(
                int(getattr(args, "forward_settle_max_ms", 350) or 350),
                350 if any(str(item.get("category")) == "view_all_replies" for item in candidates) else 180,
            ),
        )
        settle = await settle_after_trusted_cdp_burst(
            page,
            scan,
            max_ms=settle_limit,
            include_guarded_view_more=bool(args.include_guarded_view_more),
            expected_total=expected_total,
        )
        if settle.get("materialized"):
            materialized += 1
        else:
            for item in candidates[:max(1, clicked_now)]:
                key = py_stable_candidate_key(item)
                inert[key] = inert.get(key, 0) + 1
                if inert[key] == 1:
                    log("R45AY_INERT_CANDIDATE", {"scope": "bottom_range", "check": check_number, "label": item.get("label"), "key": key, "reason": "fast_settle_no_change_current_bottom_range"})
        log("R45AY_BOTTOM_RANGE_CHECK_BURST", {
            "check": check_number,
            "band": band_index,
            "candidate_count": len(candidates),
            "clicked": clicked_now,
            "materialized": bool(settle.get("materialized")),
            "settle_ms": settle.get("duration_ms"),
            "labels": [item.get("label") for item in candidates[:10]],
        })
    final_state = await page.evaluate("""() => {
      const s = r45axGetScroller();
      return s ? {scrollTop:Math.round(s.scrollTop||0), scrollHeight:Math.round(s.scrollHeight||0), clientHeight:Math.round(s.clientHeight||0), atBottom:(s.scrollTop+s.clientHeight>=s.scrollHeight-8)} : {scrollTop:0, scrollHeight:0, clientHeight:0, atBottom:true};
    }""")
    height_end = int((final_state or {}).get("scrollHeight") or height_start)
    result = {
        "check": check_number,
        "bands_scanned": bands_scanned,
        "clicked": clicked,
        "bursts": bursts,
        "materialized_bursts": materialized,
        "safe_candidates": safe_candidates,
        "candidate_labels": sorted(set(label for label in candidate_labels if label))[:40],
        "expansion_text_matches": sorted(set(label for label in expansion_matches if label))[:40],
        "scroll_height_start": height_start,
        "scroll_height_end": height_end,
        "growth": height_end > height_start,
        "at_bottom": bool((final_state or {}).get("atBottom")),
        "terminal": not safe_candidates and not expansion_matches and height_end <= height_start,
    }
    log("R45AY_BOTTOM_RANGE_CHECK_DONE", result)
    return result


async def collect_final_residual_evidence(
    page,
    args: argparse.Namespace,
    *,
    expected_total: int,
    best_progress: Optional[Dict[str, Any]],
    residual_queue: Dict[str, Dict[str, Any]],
    bottom: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    include_guarded = bool(args.include_guarded_view_more)
    result = await page.evaluate(
        """(opts) => {
          const scroller = r45axGetScroller();
          const scan = r45ayPageLoopScan({
            maxCandidates:80,
            includeGuardedViewMore:!!opts.includeGuardedViewMore,
            includeProgress:false,
            includeExpectedEvidence:false,
            allowVisibleTextFallback:true
          });
          const text = scroller ? String(scroller.innerText || scroller.textContent || '') : '';
          const matches = r45ayExpansionTextMatches(text);
          return {
            ok:!!scroller,
            loadedTextLength:text.length,
            matches,
            samples:matches.slice(0, 40),
            safeCandidates:scan.candidateCount || 0,
            candidateLabels:(scan.items || []).map(item => item.label).slice(0, 30),
            rejectedCandidates:(scan.rejected || []).length,
            scroll:scan.scroller || null
          };
        }""",
        {"includeGuardedViewMore": include_guarded},
    )
    final_matches = list((result or {}).get("matches") or [])
    queue_entries = list(residual_queue.values())
    rejected_reasons: Dict[str, int] = {}
    for entry in queue_entries:
        reason = str(entry.get("last_reject_reason") or entry.get("last_result") or "unknown")
        rejected_reasons[reason] = rejected_reasons.get(reason, 0) + 1
    terminal_allowed = not final_matches and not queue_entries and int((result or {}).get("safeCandidates") or 0) == 0
    reason = (
        "no_loaded_expansion_text_or_residual_queue"
        if terminal_allowed
        else "loaded_expansion_text_or_residual_queue_remains"
    )
    evidence = {
        "expected_total": expected_total,
        "best_progress": best_progress,
        "residual_queue_count": len(queue_entries),
        "final_loaded_expansion_text_count": len(final_matches),
        "final_loaded_expansion_text_samples": final_matches[:40],
        "safe_candidates_in_current_viewport": int((result or {}).get("safeCandidates") or 0),
        "current_viewport_candidate_labels": list((result or {}).get("candidateLabels") or []),
        "bottom_range_candidates": int((bottom or {}).get("safe_candidates") or 0) if bottom else 0,
        "bottom_range_candidate_labels": list((bottom or {}).get("candidate_labels") or [])[:30] if bottom else [],
        "rejected_candidate_reasons": rejected_reasons,
        "terminal_block_allowed": terminal_allowed,
        "reason": reason,
        "scroll": (result or {}).get("scroll"),
        "loaded_text_length": int((result or {}).get("loadedTextLength") or 0),
    }
    log("R45AY_FINAL_RESIDUAL_EVIDENCE", evidence)
    return evidence


async def locate_residual_text_candidates(
    page,
    args: argparse.Namespace,
    *,
    max_candidates: int = 160,
) -> Dict[str, Any]:
    log("R45AY_RESIDUAL_TEXT_LOCATOR_START", {"max_candidates": max_candidates})
    result = await page.evaluate(
        "(opts) => r45ayLocateExpansionTextCandidates(opts)",
        {
            "includeGuardedViewMore": bool(args.include_guarded_view_more),
            "maxCandidates": max_candidates,
        },
    )
    candidates = list((result or {}).get("candidates") or [])
    rejected = list((result or {}).get("rejected") or [])
    for item in candidates[:20]:
        log("R45AY_RESIDUAL_TEXT_LOCATOR_CANDIDATE", {
            "label": item.get("label"),
            "category": item.get("category"),
            "replyCount": item.get("replyCount"),
            "approx_scroll_position": item.get("approx_scroll_position"),
            "key": item.get("key"),
            "source": item.get("source"),
        })
    for item in rejected[:20]:
        log("R45AY_RESIDUAL_TEXT_LOCATOR_REJECT", item)
    summary = {
        "ok": bool((result or {}).get("ok")),
        "text_matches": int((result or {}).get("text_matches") or 0),
        "candidates_created": len(candidates),
        "rejected": len(rejected),
        "labels": list((result or {}).get("labels") or []),
        "approx_positions": list((result or {}).get("approx_positions") or []),
        "duration_ms": (result or {}).get("durationMs"),
        "scanned_nodes": (result or {}).get("scanned_nodes"),
        "scroll": (result or {}).get("scroll"),
        "candidates": candidates,
        "rejected_items": rejected,
    }
    log("R45AY_RESIDUAL_TEXT_LOCATOR_DONE", {k: v for k, v in summary.items() if k not in {"candidates", "rejected_items"}})
    return summary


async def residual_forward_drain(
    page,
    cdp_session: Any,
    args: argparse.Namespace,
    *,
    residual_queue: Dict[str, Dict[str, Any]],
    expected_total: int,
    started_monotonic: float,
    max_seconds: float,
    pass_number: int,
) -> Dict[str, Any]:
    include_guarded = bool(args.include_guarded_view_more)
    max_burst = max(1, int(args.max_burst_clicks or 30))
    forward_settle_ms = max(40, min(300, int(getattr(args, "forward_settle_ms", 120) or 120)))
    forward_settle_max_ms = max(forward_settle_ms, min(600, int(getattr(args, "forward_settle_max_ms", 350) or 350)))
    entries = sorted(list(residual_queue.values()), key=lambda entry: (int(entry.get("approx_scroll_position") or 0), str(entry.get("contextual_key") or "")))
    if not entries:
        log("R45AY_RESIDUAL_DRAIN_START", {"pass": pass_number, "residual_candidates_start": 0})
        result = {
            "pass": pass_number,
            "residual_candidates_start": 0,
            "residual_candidates_revisited": 0,
            "residual_candidates_clicked": 0,
            "residual_candidates_materialized": 0,
            "residual_candidates_rejected": 0,
            "residual_candidates_remaining": 0,
            "residual_drain_bands_scanned": 0,
            "scrollHeight_start": 0,
            "scrollHeight_end": 0,
            "elapsed_ms": 0.0,
            "clicked": 0,
            "bursts": 0,
            "materialized_bursts": 0,
            "click_timings": [],
            "settle_durations": [],
            "scan_durations": [],
            "ok": True,
        }
        log("R45AY_RESIDUAL_DRAIN_DONE", result)
        return result
    drain_started = time.perf_counter()
    start_state = await page.evaluate("""() => {
      const s = r45axGetScroller();
      return s ? {scrollTop:Math.round(s.scrollTop||0), scrollHeight:Math.round(s.scrollHeight||0), clientHeight:Math.round(s.clientHeight||0)} : {scrollTop:0, scrollHeight:0, clientHeight:0};
    }""")
    scroll_height_start = int((start_state or {}).get("scrollHeight") or 0)
    client_height = max(220, int((start_state or {}).get("clientHeight") or 0) or 520)
    log("R45AY_RESIDUAL_DRAIN_START", {
        "pass": pass_number,
        "residual_candidates_start": len(entries),
        "scrollHeight_start": scroll_height_start,
    })
    clicked = 0
    bursts = 0
    materialized_bursts = 0
    rejected_count = 0
    bands_scanned = 0
    revisited = 0
    click_timings: List[Dict[str, Any]] = []
    settle_durations: List[float] = []
    scan_durations: List[float] = []
    visited_bands = set()
    for entry in entries:
        if time.monotonic() - started_monotonic >= max_seconds:
            break
        position = max(0, int(entry.get("approx_scroll_position") or 0) - int(client_height * 0.35))
        band = int(position / max(280, int(client_height * 0.5)))
        if band in visited_bands:
            continue
        visited_bands.add(band)
        await page.evaluate(
            """(top) => {
              const s = r45axGetScroller();
              if (s) s.scrollTop = Math.max(0, Math.min(Number(top)||0, Math.max(0, (s.scrollHeight||0) - (s.clientHeight||0))));
            }""",
            position,
        )
        await page.wait_for_timeout(18)
        for local_attempt in range(1, 3):
            if time.monotonic() - started_monotonic >= max_seconds:
                break
            scan_started = time.perf_counter()
            scan = await page.evaluate(
                "(opts) => r45ayPageLoopScan(opts)",
                {
                    "maxCandidates": max_burst,
                    "includeGuardedViewMore": include_guarded,
                    "expectedTotal": expected_total,
                    "includeProgress": False,
                    "includeExpectedEvidence": False,
                    "allowVisibleTextFallback": True,
                },
            )
            scan_ms = round((time.perf_counter() - scan_started) * 1000.0, 3)
            scan_durations.append(scan_ms)
            bands_scanned += 1
            raw_items = list((scan or {}).get("items") or [])
            candidates, duplicates = dedupe_candidates(raw_items)
            if duplicates:
                log("R45AY_CANDIDATE_DEDUPE", {"scope": "residual_drain", "pass": pass_number, "duplicate_count": len(duplicates)})
            revisited += len(candidates)
            log("R45AY_RESIDUAL_DRAIN_BAND", {
                "pass": pass_number,
                "band": bands_scanned,
                "local_attempt": local_attempt,
                "position": position,
                "candidate_count": len(candidates),
                "labels": [item.get("label") for item in candidates[:10]],
                "scan_ms": scan_ms,
                "scroll": (scan or {}).get("scroller"),
            })
            if not candidates:
                break
            burst = await trusted_cdp_burst(
                page,
                cdp_session,
                candidates,
                max_clicks=min(max_burst, len(candidates)),
                debug_clicks=bool(args.debug_clicks),
                no_hover_clicks=bool(getattr(args, "no_hover_clicks", True)),
            )
            rejected = list(burst.get("rejected") or [])
            rejected_count += len(rejected)
            for rejected_item in rejected:
                residual_queue_update(
                    residual_queue,
                    rejected_item,
                    step=-pass_number,
                    scan=scan,
                    result="rejected",
                    reject_reason=str(rejected_item.get("reason") or "trusted_cdp_validation_rejected"),
                )
            clicked_now = int(burst.get("clicked") or 0)
            clicked += clicked_now
            bursts += 1
            click_timings.extend(list(burst.get("click_timings") or []))
            settle_limit = forward_settle_max_ms if any(str(item.get("category")) == "view_all_replies" for item in candidates) else forward_settle_ms
            settle = await settle_after_trusted_cdp_burst(
                page,
                scan,
                max_ms=settle_limit,
                include_guarded_view_more=include_guarded,
                expected_total=expected_total,
            )
            settle_ms = float(settle.get("duration_ms") or 0.0)
            settle_durations.append(settle_ms)
            materialized = bool(settle.get("materialized"))
            if materialized:
                materialized_bursts += 1
                for item in candidates:
                    residual_queue_resolve(residual_queue, item, step=-pass_number, reason="residual_drain_materialized")
                residual_queue_resolve_near(
                    residual_queue,
                    position=position,
                    client_height=client_height,
                    step=-pass_number,
                    reason="residual_drain_materialized_nearby_band",
                )
            else:
                for item in candidates[:max(1, clicked_now)]:
                    residual_queue_update(
                        residual_queue,
                        item,
                        step=-pass_number,
                        scan=scan,
                        result="clicked_no_materialization",
                    )
            log("R45AY_RESIDUAL_DRAIN_BURST", {
                "pass": pass_number,
                "band": bands_scanned,
                "candidate_count": len(candidates),
                "clicked": clicked_now,
                "materialized": materialized,
                "settle_ms": settle_ms,
                "labels": [item.get("label") for item in candidates[:10]],
                "cdp_event_count": burst.get("cdp_event_count"),
                "cdp_events_per_click": burst.get("cdp_events_per_click"),
                "no_hover_clicks": burst.get("no_hover_clicks"),
            })
            if not materialized:
                break
    end_state = await page.evaluate("""() => {
      const s = r45axGetScroller();
      return s ? {scrollTop:Math.round(s.scrollTop||0), scrollHeight:Math.round(s.scrollHeight||0), clientHeight:Math.round(s.clientHeight||0)} : {scrollTop:0, scrollHeight:0, clientHeight:0};
    }""")
    scroll_height_end = int((end_state or {}).get("scrollHeight") or scroll_height_start)
    result = {
        "pass": pass_number,
        "residual_candidates_start": len(entries),
        "residual_candidates_revisited": revisited,
        "residual_candidates_clicked": clicked,
        "residual_candidates_materialized": materialized_bursts,
        "residual_candidates_rejected": rejected_count,
        "residual_candidates_remaining": len(residual_queue),
        "residual_drain_bands_scanned": bands_scanned,
        "scrollHeight_start": scroll_height_start,
        "scrollHeight_end": scroll_height_end,
        "growth": scroll_height_end > scroll_height_start,
        "elapsed_ms": round((time.perf_counter() - drain_started) * 1000.0, 3),
        "clicked": clicked,
        "bursts": bursts,
        "materialized_bursts": materialized_bursts,
        "click_timings": click_timings,
        "settle_durations": settle_durations,
        "scan_durations": scan_durations,
        "ok": True,
    }
    log("R45AY_RESIDUAL_DRAIN_DONE", result)
    return result


async def run_forward_throughput_engine(
    page,
    cdp_session: Any,
    args: argparse.Namespace,
    story: str,
    *,
    started_monotonic: Optional[float] = None,
    skip_bootstrap: bool = False,
    skip_residual_phase: bool = False,
    resume_depth: int = 0,
) -> Dict[str, Any]:
    """Monotonic visible-page conveyor for real Facebook; no global backward proof sweep."""
    started = started_monotonic if started_monotonic is not None else time.monotonic()
    max_seconds = float(args.expand_max_seconds or 120)
    residual_reserve_ms = max(30000, int(getattr(args, "residual_reserve_ms", 45000) or 45000))
    expected_total = int(args.expected_total_comments or 0)
    max_steps = max(200000, max(1, int(args.max_steps or 300)))
    max_burst = max(1, int(args.max_burst_clicks or 30))
    forward_settle_ms = max(40, min(300, int(getattr(args, "forward_settle_ms", 120) or 120)))
    forward_settle_max_ms = max(forward_settle_ms, min(600, int(getattr(args, "forward_settle_max_ms", 350) or 350)))
    include_guarded = bool(args.include_guarded_view_more)
    inert_counts: Dict[str, int] = {}
    clicked = 0
    bursts = 0
    materialized_bursts = 0
    fallback_count = 0
    target_drift_count = 0
    scrolls = 0
    trusted_wheel_scrolls = 0
    loader_clicks = 0
    bottom_checks = 0
    forward_bands_scanned = 0
    bottom_range_bands_scanned = 0
    max_scroll_height = 0
    best_progress: Optional[Dict[str, Any]] = None
    total_candidates_seen = 0
    scan_durations: List[float] = []
    settle_durations: List[float] = []
    scroll_durations: List[float] = []
    click_timings_all: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    stalled_wheels = 0
    last_scroll_signature: Optional[Tuple[int, int]] = None
    same_band_attempts = 0
    previous_band_top: Optional[int] = None
    last_bottom_check_step = -1000000
    last_bottom_check_height = -1
    stable_height_checks = 0
    last_height_seen = 0
    residual_queue: Dict[str, Dict[str, Any]] = {}
    residual_drains: List[Dict[str, Any]] = []
    residual_text_locator_runs: List[Dict[str, Any]] = []
    residual_queue_text_merges: List[Dict[str, Any]] = []
    residual_progress_continued = False
    last_residual_cycle_made_progress = False
    last_residual_cycle_no_progress = False
    final_residual_evidence: Dict[str, Any] = {}
    residual_reserve_triggered = False
    residual_phase_ran = False
    residual_phase_skipped_no_time = False
    bottom: Optional[Dict[str, Any]] = None
    bootstrap: Dict[str, Any] = {}
    resumed_inert_count = 0
    resumed_result: Optional[Dict[str, Any]] = None
    log("R45AY_FORWARD_THROUGHPUT_START", {"max_seconds": max_seconds, "expected_total": expected_total, "max_steps": max_steps, "residual_reserve_ms": residual_reserve_ms, "no_hover_clicks": bool(getattr(args, "no_hover_clicks", True)), "forward_settle_ms": forward_settle_ms, "forward_settle_max_ms": forward_settle_max_ms, "resume_depth": resume_depth, "skip_bootstrap": skip_bootstrap, "skip_residual_phase": skip_residual_phase})
    log("R45AY_PROGRESS_CADENCE", {"cheap_visible_every_steps": 50, "heavy_every_steps": 250, "heavy_min_interval_seconds": 60, "heavy_reasons": ["startup", "cadence_250_steps", "final"]})
    if expected_total and not skip_bootstrap:
        startup_progress = await progress_evidence_scan(page, expected_total, mode="heavy", step=0, reason="forward_startup")
        best_progress = startup_progress.get("filtered_progress")
        bootstrap = await large_bucket_bootstrap(page, cdp_session, args, expected_total=expected_total)
        clicked += int(bootstrap.get("clicked") or 0)
        bursts += int(bootstrap.get("bursts") or 0)
        materialized_bursts += int(bootstrap.get("materializedBursts") or 0)
        await page.evaluate("(mode) => r45ayScroll(mode)", "top")
    elif expected_total:
        log("R45AY_RESIDUAL_FORWARD_RESUME_START", {"resume_depth": resume_depth, "elapsed_ms": round((time.monotonic() - started) * 1000.0, 3), "reason": "productive_residual_drain"})
    for step in range(1, max_steps + 1):
        elapsed_now = time.monotonic() - started
        if elapsed_now >= max_seconds:
            break
        remaining_before_scan_ms = max(0, round((max_seconds - elapsed_now) * 1000.0, 3))
        if (
            not skip_residual_phase
            and not residual_reserve_triggered
            and remaining_before_scan_ms <= residual_reserve_ms
            and (residual_queue or (expected_total and not r45ax_progress_gate_ok(best_progress, expected_total)))
        ):
            residual_reserve_triggered = True
            log("R45AY_RESIDUAL_RESERVE_TRIGGER", {
                "step": step,
                "time_remaining_ms": remaining_before_scan_ms,
                "residual_reserve_ms": residual_reserve_ms,
                "residual_queue_count": len(residual_queue),
                "reason": "time_reserve_reached_before_next_forward_scan",
                "scrollTop": None,
                "scrollHeight": max_scroll_height,
                "progress": best_progress,
            })
            break
        if story:
            href = await page.evaluate("location.href")
            if story not in str(href):
                target_drift_count += 1
                return {"ok": False, "status": "BLOCKED_TARGET_DRIFT", "clicked": clicked, "bursts": bursts, "materializedBursts": materialized_bursts, "fallbackCount": fallback_count, "targetDriftCount": target_drift_count, "bestProgress": best_progress, "forwardBandsScanned": forward_bands_scanned, "bottomRangeBandsScanned": bottom_range_bands_scanned, "maxScrollHeight": max_scroll_height, "elapsed_ms": round((time.monotonic()-started)*1000, 3)}
        scan_started = time.perf_counter()
        scan = await page.evaluate("(opts) => r45ayPageLoopScan(opts)", {
            "maxCandidates": max_burst,
            "includeGuardedViewMore": include_guarded,
            "expectedTotal": expected_total,
            "includeProgress": False,
            "includeExpectedEvidence": False,
        })
        scan_ms = round((time.perf_counter() - scan_started) * 1000.0, 3)
        scan_durations.append(scan_ms)
        scroller = scan.get("scroller") or {}
        current_top = int(scroller.get("scrollTop") or 0)
        current_height = int(scroller.get("scrollHeight") or 0)
        client_height = max(220, int(scroller.get("clientHeight") or 520))
        max_scroll_height = max(max_scroll_height, current_height)
        if current_height == last_height_seen:
            stable_height_checks += 1
        else:
            stable_height_checks = 0
            last_height_seen = current_height
            if inert_counts:
                inert_counts.clear()
                log("R45AY_INERT_RESET_ON_GROWTH", {"step": step, "scrollHeight": current_height})
        forward_bands_scanned += 1
        if previous_band_top != current_top:
            same_band_attempts = 0
            previous_band_top = current_top
        if expected_total and (step % 50 == 0 or step % 250 == 0):
            progress_mode = "heavy" if step % 250 == 0 else "cheap"
            progress_scan = await progress_evidence_scan(page, expected_total, mode=progress_mode, step=step, reason=f"forward_cadence_{progress_mode}")
            progress = progress_scan.get("filtered_progress")
            if progress and (not best_progress or int(progress.get("current") or 0) > int(best_progress.get("current") or 0)):
                best_progress = progress
            if r45ax_progress_gate_ok(best_progress, expected_total):
                break
        raw_items = list(scan.get("items") or [])
        candidates, duplicates = dedupe_candidates(raw_items)
        if duplicates:
            log("R45AY_CANDIDATE_DEDUPE", {"scope": "forward_throughput", "step": step, "duplicate_count": len(duplicates)})
        filtered: List[Dict[str, Any]] = []
        for item in candidates:
            key = py_stable_candidate_key(item)
            if inert_counts.get(key, 0) >= 1:
                residual_queue_update(residual_queue, item, step=step, scan=scan, result="inert_skip")
                log("R45AY_INERT_SKIP", {"scope": "forward_throughput", "step": step, "label": item.get("label"), "key": key})
                continue
            residual_queue_update(residual_queue, item, step=step, scan=scan, result="seen")
            copied = dict(item)
            copied["loopKey"] = key
            filtered.append(copied)
        total_candidates_seen += len(filtered)
        scan_stats = scan.get("scanStats") or {}
        if step == 1 or step % 50 == 0 or scan_ms > 500:
            log("R45AY_VIEWPORT_SCAN_MODE", {"step": step, **scan_stats})
        if step == 1 or step % 50 == 0 or filtered or residual_queue:
            log("R45AY_RESIDUAL_QUEUE_SIZE", {"step": step, "size": len(residual_queue)})
        log("R45AY_FORWARD_BAND_SCAN", {"step": step, "band": forward_bands_scanned, "candidate_count": len(filtered), "labels": [item.get("label") for item in filtered[:10]], "scrollTop": current_top, "scrollHeight": current_height, "scan_ms": scan_ms, "viewport_only": bool(scan.get("viewportOnly")), "scanned_nodes": scan_stats.get("scanned_nodes"), "skipped_offscreen_nodes": scan_stats.get("skipped_offscreen_nodes")})
        if filtered and same_band_attempts < 3:
            same_band_attempts += 1
            burst = await trusted_cdp_burst(page, cdp_session, filtered, max_clicks=min(max_burst, len(filtered)), debug_clicks=bool(args.debug_clicks), no_hover_clicks=bool(getattr(args, "no_hover_clicks", True)))
            for rejected_item in list(burst.get("rejected") or []):
                residual_queue_update(
                    residual_queue,
                    rejected_item,
                    step=step,
                    scan=scan,
                    result="rejected",
                    reject_reason=str(rejected_item.get("reason") or "trusted_cdp_validation_rejected"),
                )
            bursts += 1
            clicked_now = int(burst.get("clicked") or 0)
            clicked += clicked_now
            loader_clicks += sum(1 for item in list(burst.get("items") or []) if item.get("category") == "comment_list_loader")
            click_timings_all.extend(list(burst.get("click_timings") or []))
            settle_limit = forward_settle_max_ms if any(str(item.get("category")) == "view_all_replies" for item in filtered) else forward_settle_ms
            settle = await settle_after_trusted_cdp_burst(page, scan, max_ms=settle_limit, include_guarded_view_more=include_guarded, expected_total=expected_total)
            settle_ms = float(settle.get("duration_ms") or 0.0)
            settle_durations.append(settle_ms)
            materialized = bool(settle.get("materialized"))
            log("R45AY_FORWARD_FAST_SETTLE", {"step": step, "max_ms": settle_limit, "duration_ms": settle_ms, "reason": settle.get("reason"), "materialized": materialized, "materialization_reason": settle.get("materialization_reason")})
            log("R45AY_MATERIALIZATION_REASON", {"step": step, "reason": settle.get("materialization_reason"), "label_count": len(filtered), "labels": [item.get("label") for item in filtered[:5]]})
            if materialized:
                materialized_bursts += 1
                for item in filtered:
                    inert_counts.pop(str(item.get("loopKey") or py_stable_candidate_key(item)), None)
                    residual_queue_resolve(residual_queue, item, step=step, reason=str(settle.get("materialization_reason") or "forward_materialized"))
            else:
                for item in filtered[:max(1, clicked_now)]:
                    key = str(item.get("loopKey") or py_stable_candidate_key(item))
                    inert_counts[key] = inert_counts.get(key, 0) + 1
                    residual_queue_update(residual_queue, item, step=step, scan=scan, result="clicked_no_materialization")
                    if inert_counts[key] == 1:
                        log("R45AY_INERT_CANDIDATE", {"scope": "forward_throughput", "step": step, "label": item.get("label"), "key": key, "reason": "fast_settle_no_change_current_band"})
            log("R45AY_FORWARD_BURST", {"step": step, "band": forward_bands_scanned, "candidate_count": len(filtered), "clicked": clicked_now, "materialized": materialized, "settle_ms": settle_ms, "labels": [item.get("label") for item in filtered[:10]], "cdp_event_count": burst.get("cdp_event_count"), "cdp_events_per_click": burst.get("cdp_events_per_click"), "no_hover_clicks": burst.get("no_hover_clicks")})
            continue
        if filtered:
            for item in filtered:
                residual_queue_update(residual_queue, item, step=step, scan=scan, result="found_not_clicked_same_band_limit")
        scroll_started = time.perf_counter()
        delta = max(760, min(1400, int(client_height * 1.35)))
        if getattr(args, "scroll_engine", "trusted_wheel") == "trusted_wheel":
            scroll_result = await trusted_wheel_scroll(page, cdp_session, delta)
            if scroll_result.get("ok"):
                trusted_wheel_scrolls += 1
        else:
            scroll_result = await page.evaluate("(mode) => r45ayScroll(mode)", "down")
        await page.wait_for_timeout(25)
        scroll_ms = round((time.perf_counter() - scroll_started) * 1000.0, 3)
        scroll_durations.append(scroll_ms)
        scrolls += 1
        post = await page.evaluate("(opts) => r45ayPageLoopScan(opts)", {"maxCandidates": max_burst, "includeGuardedViewMore": include_guarded, "includeProgress": False, "includeExpectedEvidence": False})
        post_scroller = post.get("scroller") or {}
        signature = (int(post_scroller.get("scrollTop") or 0), int(post_scroller.get("scrollHeight") or 0))
        if signature == last_scroll_signature:
            stalled_wheels += 1
        else:
            stalled_wheels = 0
        last_scroll_signature = signature
        max_scroll_height = max(max_scroll_height, signature[1])
        log("R45AY_FORWARD_SCROLL", {"step": step, "scroll": scroll_result, "scroll_ms": scroll_ms, "scrollTop": signature[0], "scrollHeight": signature[1], "stalled_wheels": stalled_wheels})
        at_bottom = bool(post_scroller.get("atBottom"))
        near_bottom = bool(signature[0] + client_height >= signature[1] - client_height)
        remaining_ms = max(0, round((max_seconds - (time.monotonic() - started)) * 1000.0, 3))
        progress_below_expected = bool(expected_total and not r45ax_progress_gate_ok(best_progress, expected_total))
        if (
            not skip_residual_phase
            and not residual_reserve_triggered
            and remaining_ms <= residual_reserve_ms
            and (residual_queue or filtered or near_bottom or stalled_wheels >= 3 or progress_below_expected)
        ):
            residual_reserve_triggered = True
            log("R45AY_RESIDUAL_RESERVE_TRIGGER", {
                "step": step,
                "time_remaining_ms": remaining_ms,
                "residual_reserve_ms": residual_reserve_ms,
                "residual_queue_count": len(residual_queue),
                "reason": "time_reserve_reached_with_incomplete_expected_total_or_residual_candidates",
                "scrollTop": signature[0],
                "scrollHeight": signature[1],
                "progress": best_progress,
                "near_bottom": near_bottom,
                "stalled_wheels": stalled_wheels,
            })
            break
        bottom_cooldown_active = (step - last_bottom_check_step) < 80 and signature[1] <= last_bottom_check_height
        bottom_trigger = bool((at_bottom or near_bottom) and stalled_wheels >= 3 and stable_height_checks >= 2)
        if (at_bottom or near_bottom) and not bottom_trigger:
            log("R45AY_BOTTOM_RANGE_SUPPRESSED", {"step": step, "atBottom": at_bottom, "nearBottom": near_bottom, "stalled_wheels": stalled_wheels, "stable_height_checks": stable_height_checks})
        if bottom_trigger and bottom_cooldown_active:
            log("R45AY_BOTTOM_RANGE_COOLDOWN", {"step": step, "last_bottom_check_step": last_bottom_check_step, "scrollHeight": signature[1]})
            bottom_trigger = False
        if bottom_trigger:
            log("R45AY_BOTTOM_RANGE_TRIGGER", {"step": step, "atBottom": at_bottom, "nearBottom": near_bottom, "stalled_wheels": stalled_wheels, "stable_height_checks": stable_height_checks, "scrollHeight": signature[1]})
            last_bottom_check_step = step
            last_bottom_check_height = signature[1]
            bottom_checks += 1
            bottom = await bottom_range_check(page, cdp_session, args, expected_total=expected_total, check_number=bottom_checks, started_monotonic=started, max_seconds=max_seconds)
            bottom_range_bands_scanned += int(bottom.get("bands_scanned") or 0)
            clicked += int(bottom.get("clicked") or 0)
            bursts += int(bottom.get("bursts") or 0)
            materialized_bursts += int(bottom.get("materialized_bursts") or 0)
            max_scroll_height = max(max_scroll_height, int(bottom.get("scroll_height_end") or 0))
            if bottom.get("terminal") and expected_total and not r45ax_progress_gate_ok(best_progress, expected_total):
                break
            stalled_wheels = 0
            same_band_attempts = 0
    elapsed_ms = round((time.monotonic() - started) * 1000.0, 3)
    final_progress = None
    if expected_total:
        final_progress_scan = await progress_evidence_scan(page, expected_total, mode="heavy", step=max_steps, reason="forward_final")
        final_progress = final_progress_scan.get("filtered_progress")
        if final_progress and (not best_progress or int(final_progress.get("current") or 0) > int(best_progress.get("current") or 0)):
            best_progress = final_progress
    ok = bool(expected_total and r45ax_progress_gate_ok(best_progress, expected_total))
    if not ok and not skip_residual_phase:
        residual_phase_ran = True
        for residual_cycle in range(1, 3):
            final_residual_evidence = await collect_final_residual_evidence(
                page,
                args,
                expected_total=expected_total,
                best_progress=best_progress,
                residual_queue=residual_queue,
                bottom=bottom,
            )
            final_text_count = int(final_residual_evidence.get("final_loaded_expansion_text_count") or 0)
            queue_count = int(final_residual_evidence.get("residual_queue_count") or 0)
            needs_residual_drain = bool(
                final_text_count
                or queue_count
                or final_residual_evidence.get("safe_candidates_in_current_viewport")
            )
            log("R45AY_RESIDUAL_CYCLE_START", {
                "cycle": residual_cycle,
                "needs_residual_drain": needs_residual_drain,
                "final_loaded_expansion_text_count": final_text_count,
                "residual_queue_count": queue_count,
                "time_remaining_ms": max(0, round((max_seconds - (time.monotonic() - started)) * 1000.0, 3)),
            })
            if not needs_residual_drain:
                break
            if time.monotonic() - started >= max_seconds:
                residual_phase_skipped_no_time = True
                log("R45AY_RESIDUAL_SKIPPED_NO_TIME", {
                    "cycle": residual_cycle,
                    "time_remaining_ms": 0,
                    "residual_queue_count": queue_count,
                    "final_loaded_expansion_text_count": final_text_count,
                    "reason": "time_budget_expired_before_residual_locator_or_drain",
                })
                break
            locator_summary: Dict[str, Any] = {}
            merge_summary: Dict[str, Any] = {}
            if final_text_count > queue_count or final_text_count:
                locator_summary = await locate_residual_text_candidates(page, args, max_candidates=180)
                residual_text_locator_runs.append(locator_summary)
                merge_summary = residual_queue_merge_text_candidates(
                    residual_queue,
                    list(locator_summary.get("candidates") or []),
                    step=-1000 - residual_cycle,
                )
                residual_queue_text_merges.append(merge_summary)
            if not residual_queue:
                log("R45AY_RESIDUAL_NO_PROGRESS_BLOCK", {
                    "cycle": residual_cycle,
                    "reason": "no_safe_residual_candidates_after_text_locator",
                    "final_loaded_expansion_text_count": final_text_count,
                    "locator_candidates_created": int(locator_summary.get("candidates_created") or 0) if locator_summary else 0,
                    "locator_rejected": int(locator_summary.get("rejected") or 0) if locator_summary else 0,
                })
                last_residual_cycle_no_progress = True
                break
            queue_count_before_drain = len(residual_queue)
            progress_before_drain = dict(best_progress) if best_progress else None
            drain = await residual_forward_drain(
                page,
                cdp_session,
                args,
                residual_queue=residual_queue,
                expected_total=expected_total,
                started_monotonic=started,
                max_seconds=max_seconds,
                pass_number=residual_cycle,
            )
            residual_drains.append(drain)
            clicked += int(drain.get("clicked") or 0)
            bursts += int(drain.get("bursts") or 0)
            materialized_bursts += int(drain.get("materialized_bursts") or 0)
            click_timings_all.extend(list(drain.get("click_timings") or []))
            settle_durations.extend(float(v) for v in list(drain.get("settle_durations") or []) if isinstance(v, (int, float)))
            scan_durations.extend(float(v) for v in list(drain.get("scan_durations") or []) if isinstance(v, (int, float)))
            max_scroll_height = max(max_scroll_height, int(drain.get("scrollHeight_end") or 0))
            clicked_in_drain = int(drain.get("residual_candidates_clicked") or drain.get("clicked") or 0)
            materialized_in_drain = int(drain.get("residual_candidates_materialized") or drain.get("materialized_bursts") or 0)
            scroll_height_start = int(drain.get("scrollHeight_start") or 0)
            scroll_height_end = int(drain.get("scrollHeight_end") or 0)
            queue_decreased = len(residual_queue) < queue_count_before_drain
            growth = bool(drain.get("growth")) or scroll_height_end > scroll_height_start
            if expected_total:
                final_progress_scan = await progress_evidence_scan(page, expected_total, mode="heavy", step=max_steps, reason="after_residual_drain")
                final_progress = final_progress_scan.get("filtered_progress")
                if final_progress and (not best_progress or int(final_progress.get("current") or 0) > int(best_progress.get("current") or 0)):
                    best_progress = final_progress
                ok = bool(r45ax_progress_gate_ok(best_progress, expected_total))
            progress_improved = bool(
                best_progress
                and (
                    not progress_before_drain
                    or int(best_progress.get("current") or 0) > int(progress_before_drain.get("current") or 0)
                    or int(best_progress.get("total") or 0) > int(progress_before_drain.get("total") or 0)
                )
            )
            last_residual_cycle_made_progress = bool(
                clicked_in_drain > 0
                or materialized_in_drain > 0
                or growth
                or progress_improved
                or queue_decreased
            )
            last_residual_cycle_no_progress = not last_residual_cycle_made_progress
            time_remaining_after_drain_ms = max(0, round((max_seconds - (time.monotonic() - started)) * 1000.0, 3))
            if last_residual_cycle_made_progress:
                residual_progress_continued = True
                log("R45AY_RESIDUAL_PROGRESS_CONTINUE", {
                    "cycle": residual_cycle,
                    "clicked": clicked_in_drain,
                    "materialized_bursts": materialized_in_drain,
                    "growth": growth,
                    "scrollHeight_start": scroll_height_start,
                    "scrollHeight_end": scroll_height_end,
                    "progress_improved": progress_improved,
                    "queue_decreased": queue_decreased,
                    "time_remaining_ms": time_remaining_after_drain_ms,
                    "remaining_queue": len(residual_queue),
                })
                if time_remaining_after_drain_ms <= 0:
                    log("R45AY_RESIDUAL_PROGRESS_NO_TIME", {
                        "cycle": residual_cycle,
                        "reason": "residual_drain_made_progress_but_absolute_deadline_expired",
                        "clicked": clicked_in_drain,
                        "materialized_bursts": materialized_in_drain,
                        "growth": growth,
                        "remaining_queue": len(residual_queue),
                    })
                    break
            else:
                log("R45AY_RESIDUAL_NO_PROGRESS_BLOCK", {
                    "cycle": residual_cycle,
                    "clicked": clicked_in_drain,
                    "materialized_bursts": materialized_in_drain,
                    "growth": growth,
                    "progress_improved": progress_improved,
                    "queue_decreased": queue_decreased,
                    "remaining_queue": len(residual_queue),
                })
                break
            log("R45AY_RESIDUAL_CYCLE_DONE", {
                "cycle": residual_cycle,
                "progress": last_residual_cycle_made_progress,
                "ok": ok,
                "remaining_queue": len(residual_queue),
            })
            if ok:
                break
            final_residual_evidence = await collect_final_residual_evidence(
                page,
                args,
                expected_total=expected_total,
                best_progress=best_progress,
                residual_queue=residual_queue,
                bottom=bottom,
            )
        if residual_progress_continued and not ok and time.monotonic() - started < max_seconds and resume_depth < 1:
            log("R45AY_FORWARD_RESUME_START", {
                "resume_depth": resume_depth + 1,
                "remaining_ms": max(0, round((max_seconds - (time.monotonic() - started)) * 1000.0, 3)),
                "reason": "residual_progress_detected",
            })
            log("R45AY_RESIDUAL_PROGRESS_RESUME_FORWARD", {
                "resume_depth": resume_depth,
                "remaining_ms": max(0, round((max_seconds - (time.monotonic() - started)) * 1000.0, 3)),
                "reason": "residual_drain_made_progress_after_bounded_cycles",
            })
            resumed_result = await run_forward_throughput_engine(
                page,
                cdp_session,
                args,
                story,
                started_monotonic=started,
                skip_bootstrap=True,
                skip_residual_phase=True,
                resume_depth=resume_depth + 1,
            )
            log("R45AY_FORWARD_RESUME_DONE", {
                "resume_depth": resume_depth + 1,
                "status": resumed_result.get("status"),
                "clicked": int(resumed_result.get("clicked") or 0),
                "materialized_bursts": int(resumed_result.get("materializedBursts") or 0),
                "remaining_ms": max(0, round((max_seconds - (time.monotonic() - started)) * 1000.0, 3)),
            })
            clicked += int(resumed_result.get("clicked") or 0)
            bursts += int(resumed_result.get("bursts") or 0)
            materialized_bursts += int(resumed_result.get("materializedBursts") or 0)
            fallback_count += int(resumed_result.get("fallbackCount") or 0)
            target_drift_count += int(resumed_result.get("targetDriftCount") or 0)
            scrolls += int(resumed_result.get("scrolls") or 0)
            trusted_wheel_scrolls += int(resumed_result.get("trustedWheelScrolls") or 0)
            loader_clicks += int(resumed_result.get("loaderClicks") or 0)
            bottom_checks += int(resumed_result.get("bottomRangeChecks") or 0)
            forward_bands_scanned += int(resumed_result.get("forwardBandsScanned") or 0)
            bottom_range_bands_scanned += int(resumed_result.get("bottomRangeBandsScanned") or 0)
            max_scroll_height = max(max_scroll_height, int(resumed_result.get("maxScrollHeight") or 0))
            total_candidates_seen += int(resumed_result.get("totalCandidatesSeen") or 0)
            resumed_inert_count = int(resumed_result.get("inertCount") or 0)
            scan_durations.extend(float(v) for v in (resumed_result.get("metrics") or {}).get("scanDurations", []) if isinstance(v, (int, float)))
            settle_durations.extend(float(v) for v in (resumed_result.get("metrics") or {}).get("settleDurations", []) if isinstance(v, (int, float)))
            scroll_durations.extend(float(v) for v in (resumed_result.get("metrics") or {}).get("emptyScrollDurations", []) if isinstance(v, (int, float)))
            click_timings_all.extend(list((resumed_result.get("metrics") or {}).get("clickTimings", [])))
            residual_drains.extend(list(resumed_result.get("residualDrains") or []))
            resumed_summary = resumed_result.get("residualSummary") or {}
            if resumed_summary.get("text_locator_runs"):
                residual_text_locator_runs.extend([{
                    "text_matches": resumed_summary.get("text_locator_matches", 0),
                    "candidates_created": resumed_summary.get("text_locator_candidates_created", 0),
                    "rejected": resumed_summary.get("text_locator_rejected", 0),
                }])
            if resumed_result.get("bestProgress") and (not best_progress or int(resumed_result["bestProgress"].get("current") or 0) > int(best_progress.get("current") or 0)):
                best_progress = resumed_result["bestProgress"]
            ok = bool(resumed_result.get("ok"))
            if resumed_result.get("status") == "BLOCKED_TARGET_DRIFT":
                target_drift_count = max(1, target_drift_count)
            final_residual_evidence = await collect_final_residual_evidence(
                page,
                args,
                expected_total=expected_total,
                best_progress=best_progress,
                residual_queue=residual_queue,
                bottom=bottom,
            )
        if not final_residual_evidence:
            final_residual_evidence = await collect_final_residual_evidence(
                page,
                args,
                expected_total=expected_total,
                best_progress=best_progress,
                residual_queue=residual_queue,
                bottom=bottom,
            )
    if ok:
        status = "PASS_R45AY_TRUSTED_CDP_EXPECTED_TOTAL_REACHED"
    elif (
        final_residual_evidence
        and not final_residual_evidence.get("terminal_block_allowed")
        and last_residual_cycle_no_progress
    ):
        status = "BLOCKED_R45AY_TRUSTED_CDP_RESIDUAL_EXPANSION_REMAINS"
    elif final_residual_evidence and int(final_residual_evidence.get("final_loaded_expansion_text_count") or 0) > 0:
        status = (
            "BLOCKED_R45AY_TRUSTED_CDP_RESIDUAL_NOT_RUN_TIME_EXPIRED"
            if residual_phase_skipped_no_time
            else "BLOCKED_R45AY_TRUSTED_CDP_TIME_BUDGET_EXPIRED_WITHOUT_TERMINAL_PROOF"
        )
    else:
        status = "BLOCKED_R45AY_TRUSTED_CDP_EXPECTED_TOTAL_UNSATISFIED" if bottom_checks and bool((bottom or {}).get("terminal")) else "BLOCKED_R45AY_TRUSTED_CDP_TIME_BUDGET_EXPIRED_WITHOUT_TERMINAL_PROOF"
    timing = {"scan_duration": value_summary(scan_durations), "adaptive_settle": value_summary(settle_durations), "empty_scan_scroll": value_summary(scroll_durations), "clicks": timing_summary(click_timings_all)}
    inert_count = sum(1 for value in inert_counts.values() if value >= 1) + resumed_inert_count
    clicks_per_minute = round(clicked / max((elapsed_ms / 1000.0) / 60.0, 0.001), 2)
    residual_summary = {
        "drain_count": len(residual_drains),
        "residual_candidates_clicked": sum(int(drain.get("residual_candidates_clicked") or 0) for drain in residual_drains),
        "residual_candidates_materialized": sum(int(drain.get("residual_candidates_materialized") or 0) for drain in residual_drains),
        "residual_candidates_rejected": sum(int(drain.get("residual_candidates_rejected") or 0) for drain in residual_drains),
        "residual_candidates_remaining": len(residual_queue),
        "residual_drain_bands_scanned": sum(int(drain.get("residual_drain_bands_scanned") or 0) for drain in residual_drains),
        "text_locator_runs": len(residual_text_locator_runs),
        "text_locator_matches": sum(int(run.get("text_matches") or 0) for run in residual_text_locator_runs),
        "text_locator_candidates_created": sum(int(run.get("candidates_created") or 0) for run in residual_text_locator_runs),
        "text_locator_rejected": sum(int(run.get("rejected") or 0) for run in residual_text_locator_runs),
        "text_merge_added": sum(int(run.get("added") or 0) for run in residual_queue_text_merges),
        "text_merge_updated": sum(int(run.get("updated") or 0) for run in residual_queue_text_merges),
        "continued_after_residual_progress": residual_progress_continued,
        "reserve_triggered": residual_reserve_triggered,
        "residual_phase_ran": residual_phase_ran,
        "residual_phase_skipped_no_time": residual_phase_skipped_no_time,
        "residual_reserve_ms": residual_reserve_ms,
    }
    log("R45AY_FORWARD_TIMING", {"clicked": clicked, "clicks_per_minute": clicks_per_minute, "materialized_bursts": materialized_bursts, "inert_count": inert_count, "forward_bands_scanned": forward_bands_scanned, "bottom_range_bands_scanned": bottom_range_bands_scanned, "max_scroll_height": max_scroll_height, "fallback_count": fallback_count, "target_drift_count": target_drift_count, "cdp_events_per_click": timing.get("clicks", {}).get("click_count") and 2.0 or 0.0, "median_scan_duration_ms": timing["scan_duration"]["median_ms"], "p95_scan_duration_ms": timing["scan_duration"]["p95_ms"], "median_settle_ms": timing["adaptive_settle"]["median_ms"], "p95_settle_ms": timing["adaptive_settle"]["p95_ms"], "status": status, "elapsed_ms": elapsed_ms, **residual_summary})
    return {"ok": ok, "status": status, "clicked": clicked, "bursts": bursts, "materializedBursts": materialized_bursts, "fallbackCount": fallback_count, "targetDriftCount": target_drift_count, "bestProgress": best_progress, "scrolls": scrolls, "trustedWheelScrolls": trusted_wheel_scrolls, "loaderClicks": loader_clicks, "falseBottomRecoveries": 0, "bottomRangeChecks": bottom_checks, "forwardBandsScanned": forward_bands_scanned, "bottomRangeBandsScanned": bottom_range_bands_scanned, "inertCount": inert_count, "maxScrollHeight": max_scroll_height, "totalCandidatesSeen": total_candidates_seen, "fullSweepRetries": 0, "lastFullSurfaceSweep": {}, "largeBucketBootstrap": bootstrap, "residualDrains": residual_drains, "residualSummary": residual_summary, "finalResidualEvidence": final_residual_evidence, "elapsed_ms": elapsed_ms, "events": events, "timing": timing, "metrics": {"clickTimings": click_timings_all, "scanDurations": scan_durations, "settleDurations": settle_durations, "emptyScrollDurations": scroll_durations}}


async def run_trusted_cdp_engine(page, cdp_session: Any, args: argparse.Namespace, story: str) -> Dict[str, Any]:
    if not bool(getattr(args, "debug_full_surface_proof", False)):
        return await run_forward_throughput_engine(page, cdp_session, args, story)
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
    trusted_wheel_count = 0
    loader_click_count = 0
    false_bottom_recovery_count = 0
    max_scroll_height = 0
    last_scroll_signature: Optional[Tuple[int, int]] = None
    stalled_wheels = 0
    best_progress: Optional[Dict[str, Any]] = None
    click_timings_all: List[Dict[str, Any]] = []
    scan_durations: List[float] = []
    settle_durations: List[float] = []
    scroll_durations: List[float] = []
    events: List[Dict[str, Any]] = []
    total_candidates_seen = 0
    full_sweep_retry_count = 0
    large_bucket_bootstrap_result: Dict[str, Any] = {}
    last_full_sweep_result: Dict[str, Any] = {}
    last_bootstrap_rerun_height = 0
    step_budget_escalated = False
    log("R45AY_TRUSTED_CDP_START", {
        "max_steps": max_steps,
        "max_seconds": max_seconds,
        "expected_total": expected_total,
        "max_burst_clicks": max_burst,
        "scroll_engine": getattr(args, "scroll_engine", "trusted_wheel"),
        "no_hover_clicks": bool(getattr(args, "no_hover_clicks", True)),
    })
    log("R45AY_TRUSTED_CDP_NO_HOVER_BURST", {
        "enabled": bool(getattr(args, "no_hover_clicks", True)),
        "hot_path_events": ["mousePressed", "mouseReleased"] if bool(getattr(args, "no_hover_clicks", True)) else ["mouseMoved", "mousePressed", "mouseReleased"],
    })
    filter_state = await page.evaluate("r45ayCommentFilterState()")
    log("R45AY_COMMENT_FILTER_STATE", filter_state)
    if expected_total:
        startup_progress = await progress_evidence_scan(page, expected_total, mode="heavy", step=0, reason="startup")
        if startup_progress.get("filtered_progress"):
            best_progress = startup_progress["filtered_progress"]
    if expected_total:
        large_bucket_bootstrap_result = await large_bucket_bootstrap(page, cdp_session, args, expected_total=expected_total)
        clicked += int(large_bucket_bootstrap_result.get("clicked") or 0)
        burst_count += int(large_bucket_bootstrap_result.get("bursts") or 0)
        materialized_burst_count += int(large_bucket_bootstrap_result.get("materializedBursts") or 0)
    effective_max_steps = max_steps
    if max_seconds > 180 and max_steps < 200000:
        effective_max_steps = 200000
        step_budget_escalated = True
        log("R45AY_STEP_BUDGET_ESCALATED", {
            "requested_max_steps": max_steps,
            "effective_max_steps": effective_max_steps,
            "max_seconds": max_seconds,
            "reason": "full_run_uses_time_budget_before_terminal_block",
        })
    for step in range(1, effective_max_steps + 1):
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
                    "trustedWheelScrolls": trusted_wheel_count,
                    "loaderClicks": loader_click_count,
                    "falseBottomRecoveries": false_bottom_recovery_count,
                    "fullSweepRetries": full_sweep_retry_count,
                    "largeBucketBootstrap": large_bucket_bootstrap_result,
                    "maxScrollHeight": max_scroll_height,
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
            {
                "maxCandidates": max_burst,
                "includeGuardedViewMore": include_guarded,
                "expectedTotal": expected_total,
                "includeProgress": False,
                "includeExpectedEvidence": False,
            },
        )
        scan_ms = round((time.perf_counter() - scan_t0) * 1000.0, 3)
        scan_durations.append(scan_ms)
        scroller_state = scan.get("scroller") or {}
        max_scroll_height = max(max_scroll_height, int(scroller_state.get("scrollHeight") or 0))
        if (
            expected_total
            and max_scroll_height > 0
            and max_scroll_height - last_bootstrap_rerun_height >= 10000
            and step > 1
        ):
            log("R45AY_LARGE_BUCKET_BOOTSTRAP_RERUN", {
                "step": step,
                "previous_height": last_bootstrap_rerun_height,
                "current_height": max_scroll_height,
                "threshold_px": 10000,
            })
            rerun = await large_bucket_bootstrap(page, cdp_session, args, expected_total=expected_total)
            clicked += int(rerun.get("clicked") or 0)
            burst_count += int(rerun.get("bursts") or 0)
            materialized_burst_count += int(rerun.get("materializedBursts") or 0)
            large_bucket_bootstrap_result.setdefault("reruns", []).append(rerun)
            last_bootstrap_rerun_height = max_scroll_height
        progress = None
        raw_progress = None
        if expected_total:
            progress_mode = ""
            progress_reason = ""
            if bool(scroller_state.get("atBottom")) and (empty_scans > 0 or step % 5 == 0):
                progress_mode = "heavy"
                progress_reason = "near_bottom"
            elif step % 25 == 0:
                progress_mode = "heavy"
                progress_reason = "cadence_25_steps"
            elif step % 10 == 0:
                progress_mode = "cheap"
                progress_reason = "cadence_10_steps"
            if progress_mode:
                progress_result = await progress_evidence_scan(page, expected_total, mode=progress_mode, step=step, reason=progress_reason)
                raw_progress = progress_result.get("progress")
                progress = progress_result.get("filtered_progress")
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
                "trustedWheelScrolls": trusted_wheel_count,
                "loaderClicks": loader_click_count,
                "falseBottomRecoveries": false_bottom_recovery_count,
                "fullSweepRetries": full_sweep_retry_count,
                "largeBucketBootstrap": large_bucket_bootstrap_result,
                "maxScrollHeight": max_scroll_height,
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
        duplicate_count = 0
        for item in list(scan.get("items") or []):
            stable_key = py_stable_candidate_key(item)
            if stable_key in seen_stable:
                duplicate_count += 1
                continue
            seen_stable.add(stable_key)
            if inert_counts.get(stable_key, 0) >= 2:
                continue
            copied = dict(item)
            copied["loopKey"] = stable_key
            candidates.append(copied)
        if duplicate_count:
            log("R45AY_CANDIDATE_DEDUPE", {"scope": "trusted_cdp_loop", "step": step, "duplicate_count": duplicate_count})
        total_candidates_seen += len(candidates)
        if step <= 5 or step % 20 == 0 or candidates:
            log("R45AY_TRUSTED_CDP_SCAN", {
                "step": step,
                "candidate_count": len(candidates),
                "counts": scan.get("counts"),
                "progress": progress or raw_progress or best_progress,
                "scan_duration_ms": scan_ms,
                "scrollTop": scroller_state.get("scrollTop"),
                "scrollHeight": scroller_state.get("scrollHeight"),
            })
            reply_bucket_candidates = [item for item in candidates if str(item.get("category") or "") == "replied_bucket"]
            if reply_bucket_candidates:
                log("R45AY_REPLY_BUCKET_CANDIDATE", {
                    "step": step,
                    "count": len(reply_bucket_candidates),
                    "items": [
                        {
                            "label": item.get("label"),
                            "replyCount": item.get("replyCount"),
                            "source": item.get("source"),
                            "x": item.get("x"),
                            "y": item.get("y"),
                            "key": item.get("key"),
                        }
                        for item in reply_bucket_candidates[:10]
                    ],
                })
        if candidates:
            empty_scans = 0
            large = any(str(item.get("category")) == "view_all_replies" for item in candidates)
            burst = await trusted_cdp_burst(
                page,
                cdp_session,
                candidates,
                max_clicks=max_burst,
                debug_clicks=bool(args.debug_clicks),
                no_hover_clicks=bool(getattr(args, "no_hover_clicks", True)),
            )
            burst_count += 1
            clicked += int(burst.get("clicked") or 0)
            loader_click_count += sum(1 for item in list(burst.get("items") or []) if item.get("category") == "comment_list_loader")
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
                "cdp_events_per_click": burst.get("cdp_events_per_click"),
                "no_hover_clicks": burst.get("no_hover_clicks"),
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
        if getattr(args, "scroll_engine", "trusted_wheel") == "trusted_wheel":
            delta = -420 if mode == "bottom_chain_nudge" else 980
            scroll = await trusted_wheel_scroll(page, cdp_session, delta)
            if scroll.get("ok"):
                trusted_wheel_count += 1
            log("R45AY_TRUSTED_WHEEL_SCROLL", {"step": step, "mode": mode, "delta_y": delta, "scroll": scroll})
        else:
            scroll = await page.evaluate("(mode) => r45ayScroll(mode)", mode)
        await page.wait_for_timeout(35 if empty_scans < 3 else 70)
        scroll_ms = round((time.perf_counter() - scroll_t0) * 1000.0, 3)
        scroll_durations.append(scroll_ms)
        scroll_count += 1
        post_scroll = await page.evaluate(
            "(opts) => r45ayPageLoopScan(opts)",
            {"maxCandidates": max_burst, "includeGuardedViewMore": include_guarded, "includeProgress": False, "includeExpectedEvidence": False},
        )
        post_scroller = (post_scroll.get("scroller") or {})
        post_scroll_height = int(post_scroller.get("scrollHeight") or 0)
        post_scroll_top = int(post_scroller.get("scrollTop") or 0)
        max_scroll_height = max(max_scroll_height, post_scroll_height)
        current_scroll_signature = (post_scroll_top, post_scroll_height)
        if current_scroll_signature == last_scroll_signature:
            stalled_wheels += 1
        else:
            stalled_wheels = 0
        last_scroll_signature = current_scroll_signature
        at_bottom = bool(post_scroller.get("atBottom"))
        log("R45AY_TRUSTED_CDP_SCROLL", {"step": step, "mode": mode, "scroll": scroll, "empty_scans": empty_scans, "stalled_wheels": stalled_wheels, "scroll_duration_ms": scroll_ms, "scrollHeight": max_scroll_height, "scrollTop": post_scroll_top})
        if empty_scans >= int(args.progress_stall_cycles or 3) and (at_bottom or stalled_wheels >= int(args.progress_stall_cycles or 3)):
            if expected_total and (not best_progress or int(best_progress.get("current") or 0) < expected_total):
                false_bottom_recovery_count += 1
                recovery = await false_bottom_recovery(page, cdp_session, args, expected_total=expected_total, recovery_number=false_bottom_recovery_count)
                clicked += int(recovery.get("clicked") or 0)
                loader_click_count += int(recovery.get("loader_clicks") or 0)
                max_scroll_height = max(max_scroll_height, int(recovery.get("scroll_height_after") or 0))
                if recovery.get("progress_after") and (not best_progress or int(recovery["progress_after"].get("current") or 0) > int(best_progress.get("current") or 0)):
                    best_progress = recovery["progress_after"]
                log("R45AY_FALSE_BOTTOM_RECOVERY_RESULT", {"recovery": false_bottom_recovery_count, **recovery})
                if recovery.get("recovered") and false_bottom_recovery_count < 3:
                    empty_scans = 0
                    continue
                full_sweep_retry_count += 1
                retry = await full_sweep_retry(
                    page,
                    cdp_session,
                    args,
                    expected_total=expected_total,
                    retry_number=full_sweep_retry_count,
                    started_monotonic=started,
                    max_seconds=max_seconds,
                )
                last_full_sweep_result = retry
                clicked += int(retry.get("clicked") or 0)
                burst_count += int(retry.get("bursts") or 0)
                materialized_burst_count += int(retry.get("materializedBursts") or 0)
                max_scroll_height = max(max_scroll_height, int(retry.get("maxScrollHeight") or 0))
                if int(retry.get("clicked") or 0) > 0 and full_sweep_retry_count < 3:
                    empty_scans = 0
                    continue
                if not retry.get("fullSurfaceSweepCompleted") and (time.monotonic() - started) < max_seconds:
                    empty_scans = 0
                    continue
                if full_sweep_retry_count < 2 and (time.monotonic() - started) < max_seconds:
                    empty_scans = 0
                    continue
            break
    if (
        expected_total
        and (not best_progress or int(best_progress.get("current") or 0) < expected_total)
        and (time.monotonic() - started) < max_seconds
        and not (last_full_sweep_result or {}).get("fullSurfaceSweepCompleted")
    ):
        full_sweep_retry_count += 1
        log("R45AY_STEP_BUDGET_ENTER_FULL_SWEEP", {
            "fullSweepRetries": full_sweep_retry_count,
            "elapsed_ms": round((time.monotonic() - started) * 1000.0, 3),
            "max_seconds": max_seconds,
            "step_budget_escalated": step_budget_escalated,
        })
        retry = await full_sweep_retry(
            page,
            cdp_session,
            args,
            expected_total=expected_total,
            retry_number=full_sweep_retry_count,
            started_monotonic=started,
            max_seconds=max_seconds,
        )
        last_full_sweep_result = retry
        clicked += int(retry.get("clicked") or 0)
        burst_count += int(retry.get("bursts") or 0)
        materialized_burst_count += int(retry.get("materializedBursts") or 0)
        max_scroll_height = max(max_scroll_height, int(retry.get("maxScrollHeight") or 0))
    if expected_total and (time.monotonic() - started) < max_seconds:
        log("R45AY_LARGE_BUCKET_BOOTSTRAP_RERUN", {
            "phase": "before_final_block",
            "current_height": max_scroll_height,
        })
        rerun = await large_bucket_bootstrap(page, cdp_session, args, expected_total=expected_total)
        clicked += int(rerun.get("clicked") or 0)
        burst_count += int(rerun.get("bursts") or 0)
        materialized_burst_count += int(rerun.get("materializedBursts") or 0)
        large_bucket_bootstrap_result.setdefault("reruns", []).append(rerun)
        if int(rerun.get("clicked") or 0) > 0 and (time.monotonic() - started) < max_seconds:
            full_sweep_retry_count += 1
            retry = await full_sweep_retry(
                page,
                cdp_session,
                args,
                expected_total=expected_total,
                retry_number=full_sweep_retry_count,
                started_monotonic=started,
                max_seconds=max_seconds,
            )
            last_full_sweep_result = retry
            clicked += int(retry.get("clicked") or 0)
            burst_count += int(retry.get("bursts") or 0)
            materialized_burst_count += int(retry.get("materializedBursts") or 0)
            max_scroll_height = max(max_scroll_height, int(retry.get("maxScrollHeight") or 0))
    final_progress_scan = None
    if expected_total:
        final_progress_scan = await progress_evidence_scan(page, expected_total, mode="heavy", step=max_steps, reason="final_block")
        final_progress = final_progress_scan.get("filtered_progress")
        if final_progress and (not best_progress or int(final_progress.get("current") or 0) > int(best_progress.get("current") or 0)):
            best_progress = final_progress
        if r45ax_progress_gate_ok(best_progress, expected_total):
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
                "trustedWheelScrolls": trusted_wheel_count,
                "loaderClicks": loader_click_count,
                "falseBottomRecoveries": false_bottom_recovery_count,
                "fullSweepRetries": full_sweep_retry_count,
                "largeBucketBootstrap": large_bucket_bootstrap_result,
                "maxScrollHeight": max_scroll_height,
                "elapsed_ms": round((time.monotonic() - started) * 1000.0, 3),
                "events": events,
                "metrics": {
                    "clickTimings": click_timings_all,
                    "scanDurations": scan_durations,
                    "settleDurations": settle_durations,
                    "emptyScrollDurations": scroll_durations,
                },
            }
    final_block_evidence = await collect_final_block_evidence(
        page,
        args,
        include_guarded=include_guarded,
        full_sweep_result=last_full_sweep_result,
    )
    log("R45AY_FINAL_BLOCK_EVIDENCE", final_block_evidence)
    status = (
        "BLOCKED_R45AY_TRUSTED_CDP_EXPECTED_TOTAL_UNSATISFIED"
        if final_block_evidence.get("terminal_block_proven")
        else "BLOCKED_R45AY_TRUSTED_CDP_TIME_BUDGET_EXPIRED_WITHOUT_TERMINAL_PROOF"
    )
    return {
        "ok": False,
        "status": status,
        "clicked": clicked,
        "bursts": burst_count,
        "materializedBursts": materialized_burst_count,
        "fallbackCount": fallback_count,
        "targetDriftCount": target_drift_count,
        "bestProgress": best_progress,
        "scrolls": scroll_count,
        "trustedWheelScrolls": trusted_wheel_count,
        "loaderClicks": loader_click_count,
        "falseBottomRecoveries": false_bottom_recovery_count,
        "fullSweepRetries": full_sweep_retry_count,
        "lastFullSurfaceSweep": last_full_sweep_result,
        "largeBucketBootstrap": large_bucket_bootstrap_result,
        "maxScrollHeight": max_scroll_height,
        "finalProgressScan": final_progress_scan,
        "finalBlockEvidence": final_block_evidence,
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
                no_hover_clicks=True,
                scroll_engine="trusted_wheel",
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
    target_info = sanitize_target_url(args.target_url)
    if not target_info.get("ok"):
        log("R45AY_TARGET_URL_INVALID_MARKDOWN", {"reason": target_info.get("reason"), "target_url": str(args.target_url)[:240]})
        return 2
    if target_info.get("sanitized"):
        log("R45AY_TARGET_URL_SANITIZED", {"reason": target_info.get("reason"), "from_markdown": True})
    target_url = clean_target_url(str(target_info.get("url") or ""))
    story = expected_story(target_url)
    run_dir = Path(args.output_root) / ("r45ay_instant_ordered_expand_" + now_stamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    receipt: Dict[str, Any] = {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "mode": "real_visible_smoke" if args.instant_audit else "real_capture",
        "target_url": target_url,
        "target_url_sanitized": bool(target_info.get("sanitized")),
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
                "trusted_wheel_scrolls": trusted_result.get("trustedWheelScrolls"),
                "loader_clicks": trusted_result.get("loaderClicks"),
                "false_bottom_recoveries": trusted_result.get("falseBottomRecoveries"),
                "max_scroll_height": trusted_result.get("maxScrollHeight"),
                "elapsed_ms": elapsed_ms,
                "clicks_per_minute": clicks_per_minute,
                "timing": trusted_timing,
                "target_guard_ok": bool(final_guard.get("ok")),
                "residual_summary": trusted_result.get("residualSummary"),
                "final_loaded_expansion_text_count": ((trusted_result.get("finalResidualEvidence") or {}).get("final_loaded_expansion_text_count")),
            })
            receipt.update({
                "instant_engine": "trusted_cdp",
                "trusted_cdp_result": trusted_result,
                "clicked": clicked,
                "burst_count": int(trusted_result.get("bursts") or 0),
                "candidate_count": int(trusted_result.get("totalCandidatesSeen") or 0),
                "loader_click_count": int(trusted_result.get("loaderClicks") or 0),
                "false_bottom_recovery_count": int(trusted_result.get("falseBottomRecoveries") or 0),
                "trusted_wheel_scroll_count": int(trusted_result.get("trustedWheelScrolls") or 0),
                "max_scroll_height": int(trusted_result.get("maxScrollHeight") or 0),
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
                "residual_summary": trusted_result.get("residualSummary"),
                "final_residual_evidence": trusted_result.get("finalResidualEvidence"),
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
    ap.add_argument("--scroll-engine", choices=["trusted_wheel", "dom_scroll"], default="trusted_wheel")
    ap.add_argument("--no-hover-clicks", dest="no_hover_clicks", action="store_true", default=True)
    ap.add_argument("--hover-clicks", dest="no_hover_clicks", action="store_false")
    ap.add_argument("--debug-clicks", action="store_true")
    ap.add_argument("--include-guarded-view-more", action="store_true")
    ap.add_argument("--max-burst-clicks", type=int, default=30)
    ap.add_argument("--inter-click-delay-ms", type=int, default=0)
    ap.add_argument("--settle-ms", type=int, default=125)
    ap.add_argument("--forward-settle-ms", type=int, default=120)
    ap.add_argument("--forward-settle-max-ms", type=int, default=350)
    ap.add_argument("--residual-reserve-ms", type=int, default=45000)
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
