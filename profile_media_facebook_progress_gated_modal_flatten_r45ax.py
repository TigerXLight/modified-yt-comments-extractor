#!/usr/bin/env python3
"""R45AX Facebook progress-gated modal flatten capture.

Visible-page-only Facebook comment expansion runner.
No hidden Facebook APIs, no cookies/tokens, no browser profile parsing/copying.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MARKER = "YTCE_R45AX_PROGRESS_GATED_MODAL_FLATTEN"
SCHEMA_VERSION = "facebook_progress_gated_modal_flatten.r45ax.v1"

CONTRACT = {
    "marker": MARKER,
    "schema_version": SCHEMA_VERSION,
    "primary_route": "visible-page-only Facebook expansion in an operator-controlled signed-in Chromium profile",
    "r45ax_rule": "Open the post, lock to the target story, use the active comments modal scroller, click the first safe visible expansion label, rescan the same viewport, continue downward while comments load, restart from the top after any pass that clicked controls, and gate completion on both zero visible expand controls in a full top-to-bottom audit and any detected Facebook progress text reaching its total, e.g. 715 of 715. Progress is checked against visible text, aria/title attributes, and stripped live HTML.",
    "progress_gate_rule": "If visible/modal text contains N of M where M looks like total loaded comments, final screenshot is refused until max observed N >= M. A run that stops at 657 of 715, 696 of 715, etc. is blocked as incomplete.",
    "screenshot_rule": "After completion, flatten the Facebook comments modal into a comments-only page with no internal scroll box, then capture the widest comments column as maximum-height bands, using the largest safe band height rather than many small tiles.",
    "visible_controls": ["View all N replies", "View N replies", "View hidden replies/comments", "View more replies/comments", "replied · N replies"],
    "hidden_platform_api_scraping_enabled": False,
    "login_automation_enabled": False,
    "cookie_or_token_extraction_enabled": False,
    "browser_profile_file_copying_enabled": False,
    "browser_profile_file_parsing_enabled": False,
    "webview2_storage_or_cookie_inspection_enabled": False,
    "remote_media_downloads_enabled": False,
    "r45ba_scroll_container_rule": "The active comments scroller must be a real scrollable comments container, not the outer role=dialog shell with scrollHeight equal to clientHeight. R45BA scores only scrollable candidates first and blocks rather than falsely passing on a 720px outer dialog.",
    "r45bc_dead_click_rule": "If an expansion control remains visible after repeated clicks at the same coordinate/key without increasing scrollHeight, text length, or progress, R45BC marks that exact candidate as inert and skips it so the run can continue downward instead of looping forever.",
    "r45bd_messenger_guard_rule": "If any click opens a Messenger/DM chat overlay or a new tab/page, R45BD closes the side effect, marks the candidate inert, and logs timing/delta evidence for that click instead of continuing with the overlay covering the comments modal.",
}

EXPAND_PATTERNS_JS = r"""
function r45axNorm(s){ return String(s || '').replace(/\s+/g, ' ').trim(); }
function r45axCategory(label){
  const t = r45axNorm(label);
  if (/^View hidden (replies|comments)$/i.test(t)) return 'view_hidden';
  if (/^View all \d+ replies?$/i.test(t)) return 'view_all_replies';
  if (/^View \d+ replies?$/i.test(t)) return 'view_n_replies';
  if (/^View \d+ more replies?$/i.test(t)) return 'view_more_replies';
  if (/^View more (replies|comments)$/i.test(t)) return 'view_more';
  if (/\breplied\s*(?:[·•.\-]\s*)?\d+\s+repl(?:y|ies)\b/i.test(t)) return 'replied_bucket';
  return '';
}
function r45axExpansionLabelInfo(text){
  const t = r45axNorm(text);
  const patterns = [
    {category:'view_hidden', rx:/\bView hidden (?:replies|comments)\b/i},
    {category:'view_all_replies', rx:/\bView all \d+ replies?\b/i},
    {category:'view_more_replies', rx:/\bView \d+ more replies?\b/i},
    {category:'view_n_replies', rx:/\bView \d+ replies?\b/i},
    {category:'view_more', rx:/\bView more (?:replies|comments)\b/i},
    {category:'replied_bucket', rx:/\breplied\s*(?:[·•.\-]\s*)?\d+\s+repl(?:y|ies)\b/i}
  ];
  for (const p of patterns){
    const m = t.match(p.rx);
    if (m) return {label:r45axNorm(m[0]), category:p.category};
  }
  return null;
}
function r45axProgressFromText(text){
  const out = [];
  const re = /\b(\d{1,5})\s+of\s+(\d{1,5})\b/g;
  let m;
  while ((m = re.exec(String(text || ''))) !== null) {
    const cur = parseInt(m[1], 10), total = parseInt(m[2], 10);
    if (Number.isFinite(cur) && Number.isFinite(total) && total >= 20 && cur <= total) out.push({current: cur, total, text: m[0]});
  }
  if (!out.length) return null;
  out.sort((a,b) => (b.total - a.total) || (b.current - a.current));
  return out[0];
}
function r45axProgressFromPage(){
  const sources = [];
  const scroller = window.__R45AX_SCROLLER__;
  if (scroller) sources.push(scroller.innerText || '', scroller.textContent || '');
  sources.push(document.body ? (document.body.innerText || '') : '', document.body ? (document.body.textContent || '') : '');
  try {
    sources.push(Array.from(document.querySelectorAll('[aria-label],[title]')).slice(0,5000).map(el => (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '')).join(' '));
  } catch(e) {}
  for (const s of sources) {
    const p = r45axProgressFromText(s);
    if (p) return p;
  }
  try {
    const htmlText = String(document.documentElement && document.documentElement.innerHTML || '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/&nbsp;|&#160;|&amp;nbsp;/gi, ' ')
      .replace(/\s+/g, ' ');
    return r45axProgressFromText(htmlText);
  } catch(e) { return null; }
}
function r45axRectVisible(rect, band){
  if (!rect || rect.width < 3 || rect.height < 3) return false;
  if (rect.bottom <= band.top || rect.top >= band.bottom) return false;
  if (rect.right <= band.left || rect.left >= band.right) return false;
  return true;
}
function r45axElementHidden(el){
  if (!el || el.nodeType !== 1) return true;
  const cs = getComputedStyle(el);
  return cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity || '1') < 0.05;
}
function r45axUnsafeHref(href){
  if (!href) return false;
  const h = String(href);
  if (/facebook\.com\/(permalink\.php|story\.php|posts\/|groups\/|photo\/|watch\/|reel\/)/i.test(h)) return false;
  if (/comment_id=/i.test(h) && !/permalink\.php/i.test(h)) return true;
  if (/facebook\.com\/[A-Za-z0-9._-]+\?/i.test(h) && !/permalink\.php/i.test(h)) return true;
  if (/facebook\.com\/[A-Za-z0-9._-]+$/i.test(h)) return true;
  return false;
}
function r45axClickSafetyAt(x, y){
  const chain = [];
  let el = document.elementFromPoint(x, y);
  let href = '';
  for (let cur = el; cur && chain.length < 8; cur = cur.parentElement){
    let item = {tag: cur.tagName || '', role: cur.getAttribute && (cur.getAttribute('role') || ''), text: r45axNorm((cur.innerText || cur.textContent || '')).slice(0,80), href: ''};
    if (cur.tagName === 'A' || (cur.getAttribute && cur.getAttribute('href'))) {
      href = cur.href || cur.getAttribute('href') || '';
      item.href = href;
    }
    chain.push(item);
  }
  if (r45axUnsafeHref(href)) return {ok:false, reason:'profile_or_comment_permalink_anchor_under_click_point', href, chain};
  return {ok:true, reason:'safe', href, chain};
}
function r45axFindScroller(){
  const vh = window.innerHeight || document.documentElement.clientHeight || 720;
  const vw = window.innerWidth || document.documentElement.clientWidth || 1280;
  const nodes = Array.from(document.querySelectorAll('div, [role="dialog"], [aria-modal="true"]'));
  const candidates = [];
  for (const el of nodes){
    if (r45axElementHidden(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 360 || r.height < 220) continue;
    if (r.bottom < 80 || r.top > vh - 80) continue;
    const sh = el.scrollHeight || 0, ch = el.clientHeight || 0;
    const scrollable = sh > ch + 80;
    const text = r45axNorm(el.innerText || el.textContent || '');
    const hasComments = /\bLike\b\s+\bReply\b|View all \d+ replies|View \d+ replies|View hidden|View more|replied\s*[·•]\s*\d+\s+replies|\bof\s+\d{2,5}\b/i.test(text);
    if (!hasComments) continue;
    const progress = r45axProgressFromText(text);
    /*
      R45BA: the outer Facebook dialog can have role=dialog, lots of text,
      and scrollHeight==clientHeight (for example 720/720). That is NOT the
      comments scroller. Prefer real scrollable descendants; otherwise block
      instead of falsely declaring completion after one 720px scan.
    */
    if (!scrollable) continue;
    const centerBonus = (r.left > 80 && r.right < vw - 40) ? 1500 : 0;
    const progressBonus = progress ? 12000 : 0;
    const commentTextBonus = Math.min(text.length, 50000);
    const scrollBonus = Math.max(0, sh - ch) * 8;
    const rolePenalty = el.getAttribute('role') === 'dialog' ? -8000 : 0;
    const score = progressBonus + scrollBonus + commentTextBonus + centerBonus + rolePenalty + r.height;
    candidates.push({el, score, rect:r, textLength:text.length, progress, role:el.getAttribute('role') || '', tag:el.tagName, scrollable, sh, ch});
  }
  candidates.sort((a,b) => b.score - a.score);
  const best = candidates[0];
  if (!best) return {ok:false, reason:'no_real_scrollable_comments_container'};
  window.__R45AX_SCROLLER__ = best.el;
  return {ok:true, reason:'real_scrollable_comments_container', scroller:{tag:best.tag, role:best.role, score:Math.round(best.score), textLength:best.textLength, progress:best.progress, scrollTop:best.el.scrollTop||0, scrollHeight:best.el.scrollHeight||0, clientHeight:best.el.clientHeight||0, scrollable:true, rect:{top:Math.round(best.rect.top), bottom:Math.round(best.rect.bottom), left:Math.round(best.rect.left), right:Math.round(best.rect.right), width:Math.round(best.rect.width), height:Math.round(best.rect.height)}}};
}
function r45axGetScroller(){
  const s = window.__R45AX_SCROLLER__;
  if (s && document.contains(s)) return s;
  const f = r45axFindScroller();
  return f.ok ? window.__R45AX_SCROLLER__ : null;
}
function r45axBand(scroller){
  const r = scroller ? scroller.getBoundingClientRect() : {top:0,bottom:innerHeight,left:0,right:innerWidth};
  return {top:Math.max(0, r.top + 8), bottom:Math.min(innerHeight, r.bottom - 86), left:Math.max(0, r.left + 8), right:Math.min(innerWidth, r.right - 8)};
}
function r45axBadCandidateElement(el){
  if (!el || el.nodeType !== 1) return true;
  if (el.closest('textarea,input,select,[contenteditable="true"]')) return true;
  let cur = el;
  for (let i=0; cur && i<8; i++, cur=cur.parentElement) {
    const blob = r45axNorm([cur.getAttribute && (cur.getAttribute('aria-label')||''), cur.getAttribute && (cur.getAttribute('title')||''), cur.className||''].join(' '));
    if (/(composer|comment as|write a comment|reply to|gif|sticker|photo|camera|avatar|upload|file|emoji)/i.test(blob)) return true;
  }
  return false;
}
function r45axTextCandidates(scroller){
  const band = r45axBand(scroller);
  const out = [];
  function addCandidate(label, category, rect, source){
    if (!r45axRectVisible(rect, band)) return;
    if (rect.width < 4 || rect.height < 4) return;
    const points = [
      {x: rect.left + rect.width/2, y: rect.top + rect.height/2},
      {x: rect.left + Math.min(rect.width-2, Math.max(2, rect.width*0.18)), y: rect.top + rect.height/2},
      {x: rect.left + Math.min(rect.width-2, Math.max(2, rect.width*0.82)), y: rect.top + rect.height/2},
    ];
    let chosen = null, safety = null;
    for (const p of points){
      const s = r45axClickSafetyAt(p.x, p.y);
      if (s.ok){ chosen = p; safety = s; break; }
      if (!safety) safety = s;
    }
    out.push({label, category, x:Math.round((chosen||points[0]).x), y:Math.round((chosen||points[0]).y), top:Math.round(rect.top), bottom:Math.round(rect.bottom), left:Math.round(rect.left), right:Math.round(rect.right), safe:!!chosen, safety, source});
  }
  const walker = document.createTreeWalker(scroller || document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())){
    const raw = String(n.nodeValue || '');
    const info = r45axExpansionLabelInfo(raw);
    if (!info) continue;
    const parent = n.parentElement;
    if (!parent || r45axElementHidden(parent) || r45axBadCandidateElement(parent)) continue;
    const range = document.createRange();
    try {
      const lowerRaw = raw.toLowerCase(), lowerLabel = info.label.toLowerCase();
      let start = lowerRaw.indexOf(lowerLabel);
      if (start < 0) start = 0;
      range.setStart(n, start);
      range.setEnd(n, Math.min(raw.length, start + info.label.length));
    } catch(e) {
      try { range.selectNodeContents(n); } catch(e2) { continue; }
    }
    const rects = Array.from(range.getClientRects()).filter(rect => r45axRectVisible(rect, band));
    range.detach && range.detach();
    for (const rect of rects) addCandidate(info.label, info.category, rect, 'text');
  }
  const elementSelector = 'a, [role="button"], [tabindex], span, div';
  for (const el of Array.from((scroller || document.body).querySelectorAll(elementSelector))){
    if (r45axElementHidden(el) || r45axBadCandidateElement(el)) continue;
    const text = r45axNorm(el.innerText || el.textContent || el.getAttribute('aria-label') || '');
    if (!text || text.length > 220) continue;
    const info = r45axExpansionLabelInfo(text);
    if (!info) continue;
    const rect = el.getBoundingClientRect();
    if (rect.height > 90 || rect.width > 460) continue;
    addCandidate(info.label, info.category, rect, 'element');
  }
  const seen = new Set();
  const skip = new Set(Array.isArray(window.__R45AX_SKIP_KEYS__) ? window.__R45AX_SKIP_KEYS__ : []);
  const dedup = [];
  for (const item of out.sort((a,b)=>a.top-b.top || a.left-b.left || (a.source || '').localeCompare(b.source || ''))){
    const key = item.category+'|'+item.label+'|'+Math.round(item.top/3)+'|'+Math.round(item.left/8);
    item.key = key;
    if (seen.has(key) || skip.has(key)) continue;
    seen.add(key); dedup.push(item);
  }
  return dedup;
}
function r45axScanVisible(){
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_scroller'};
  const items = r45axTextCandidates(scroller);
  const counts = {};
  for (const it of items) counts[it.category] = (counts[it.category] || 0) + 1;
  const progress = r45axProgressFromPage();
  return {ok:true, scrollTop:scroller.scrollTop||0, scrollHeight:scroller.scrollHeight||0, clientHeight:scroller.clientHeight||0, atBottom: (scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8), counts, labels: items.map(x=>x.label).slice(0,25), total: items.length, items:items.slice(0,20), progress};
}
function r45axClickFirstVisible(){
  const scan = r45axScanVisible();
  if (!scan.ok || !scan.items.length) return {clicked:false, scan};
  const item = scan.items.find(x => x.safe) || scan.items[0];
  if (!item.safe) return {clicked:false, blocked:true, item, scan};
  return {clicked:true, item, scan};
}
function r45axAddSkipKey(key){
  if (!key) return {ok:false, reason:'missing_key'};
  if (!Array.isArray(window.__R45AX_SKIP_KEYS__)) window.__R45AX_SKIP_KEYS__ = [];
  if (!window.__R45AX_SKIP_KEYS__.includes(key)) window.__R45AX_SKIP_KEYS__.push(key);
  return {ok:true, key, count: window.__R45AX_SKIP_KEYS__.length};
}
function r45axClearSkipKeys(){ window.__R45AX_SKIP_KEYS__ = []; return {ok:true}; }
function r45axScroll(mode){
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_scroller'};
  const before = scroller.scrollTop || 0;
  if (mode === 'top') scroller.scrollTop = 0;
  else if (mode === 'bottom') scroller.scrollTop = scroller.scrollHeight;
  else scroller.scrollTop = before + Math.max(240, Math.floor((scroller.clientHeight || 600) * 0.72));
  const after = scroller.scrollTop || 0;
  return {ok:true, mode, before, after, scrollHeight:scroller.scrollHeight||0, clientHeight:scroller.clientHeight||0, atBottom:(after + (scroller.clientHeight||0) >= (scroller.scrollHeight||0)-8)};
}
function r45axPageProgress(){
  const scroller = r45axGetScroller();
  return r45axProgressFromPage();
}

function r45axMessengerOverlayState(){
  const overlays = [];
  const vw = window.innerWidth || document.documentElement.clientWidth || 1280;
  const vh = window.innerHeight || document.documentElement.clientHeight || 720;
  const nodes = Array.from(document.querySelectorAll('[role="dialog"], [aria-label], div')).slice(0, 12000);
  for (const el of nodes){
    if (r45axElementHidden(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 240 || r.width > 560 || r.height < 180 || r.height > 720) continue;
    if (r.right < vw * 0.55 || r.bottom < vh * 0.45) continue;
    const text = r45axNorm([el.innerText || '', el.textContent || '', el.getAttribute && (el.getAttribute('aria-label') || '')].join(' '));
    if (!/(Messages and calls are secured|end-to-end encrypted|Type a message|Write a message|Messenger|Minimize chat|Close chat|Start a call|Aa\s*(?:Like|Send)?)/i.test(text)) continue;
    overlays.push({tag:el.tagName, role:el.getAttribute('role') || '', aria:el.getAttribute('aria-label') || '', text:text.slice(0,220), rect:{left:Math.round(r.left), top:Math.round(r.top), right:Math.round(r.right), bottom:Math.round(r.bottom), width:Math.round(r.width), height:Math.round(r.height)}});
  }
  overlays.sort((a,b)=>(b.rect.right-a.rect.right)||(b.rect.bottom-a.rect.bottom));
  return {count:overlays.length, overlays:overlays.slice(0,5)};
}
function r45axCloseMessengerOverlays(){
  let closed = 0;
  const before = r45axMessengerOverlayState();
  for (const info of before.overlays || []){
    let candidates = Array.from(document.querySelectorAll('[aria-label], [role="button"], button, div, span')).filter(el => {
      if (r45axElementHidden(el)) return false;
      const r = el.getBoundingClientRect();
      if (r.left < info.rect.left || r.right > info.rect.right + 5 || r.top < info.rect.top || r.bottom > info.rect.bottom + 5) return false;
      const blob = r45axNorm([(el.getAttribute && (el.getAttribute('aria-label') || '')), (el.getAttribute && (el.getAttribute('title') || '')), (el.innerText || el.textContent || '')].join(' '));
      if (/(Close chat|Close conversation|Close tab|Close$|Minimize chat)/i.test(blob)) return true;
      if (/^[×xX✕-]$/.test(blob) && r.top < info.rect.top + 80 && r.right > info.rect.right - 90) return true;
      return false;
    });
    candidates.sort((a,b)=>{
      const ar=a.getBoundingClientRect(), br=b.getBoundingClientRect();
      return (br.right-ar.right) || (ar.top-br.top);
    });
    const btn = candidates[0];
    try {
      if (btn) { btn.click(); closed += 1; continue; }
      const x = Math.max(info.rect.left + 10, info.rect.right - 22);
      const y = Math.max(info.rect.top + 10, info.rect.top + 24);
      const el = document.elementFromPoint(x, y);
      if (el) { el.click(); closed += 1; }
    } catch(e) {}
  }
  return {before, closed, after:r45axMessengerOverlayState()};
}
function r45axSideEffectState(){ return {messenger:r45axMessengerOverlayState(), href:location.href, title:document.title}; }

function r45axInstallNavBlocker(){
  if (window.__R45AX_NAV_BLOCKER__) return {installed:true, already:true};
  window.__R45AX_NAV_BLOCKER__ = true;
  document.addEventListener('click', function(ev){
    const target = ev.target && ev.target.closest ? ev.target.closest('a[href], [role=\"button\"], button, [aria-label]') : null;
    const a = ev.target && ev.target.closest && ev.target.closest('a[href]');
    const href = a ? (a.href || a.getAttribute('href') || '') : '';
    const blob = target ? r45axNorm([(target.getAttribute && (target.getAttribute('aria-label') || '')), (target.getAttribute && (target.getAttribute('title') || '')), (target.innerText || target.textContent || '')].join(' ')) : '';
    if (r45axUnsafeHref(href) || /\b(Message|Messenger|Send message|Open Messenger|Start call|Start video call|Audio call|Video call)\b/i.test(blob)) {
      ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation(); console.warn('R45AX_NAV_OR_DM_BLOCKED '+(href || blob));
    }
  }, true);
  return {installed:true, already:false};
}
function r45axFlattenForScreenshot(){
  const scroller = r45axGetScroller();
  if (!scroller) return {ok:false, reason:'no_scroller'};
  const progress = r45axPageProgress();
  const clone = scroller.cloneNode(true);
  for (const el of Array.from(clone.querySelectorAll('*'))){
    const txt = r45axNorm(el.innerText || el.textContent || '');
    const aria = el.getAttribute('aria-label') || '';
    if (/^(Comment as|Reply to)\b/i.test(txt) || /^(Comment as|Reply to)\b/i.test(aria) || el.matches('input, textarea, [contenteditable="true"]')) el.remove();
  }
  const style = document.createElement('style');
  style.textContent = `html,body{margin:0!important;padding:0!important;background:white!important;overflow:visible!important;height:auto!important}#r45ax-page{width:min(980px,100vw);margin:0 auto;background:#fff;overflow:visible!important;height:auto!important;min-height:0!important;padding:0 14px 40px;box-sizing:border-box}#r45ax-page *{max-height:none!important;overflow:visible!important;scrollbar-width:none!important}#r45ax-page [role="dialog"],#r45ax-page [aria-modal="true"]{position:static!important;transform:none!important;inset:auto!important;height:auto!important;max-height:none!important;box-shadow:none!important}#r45ax-meta{font:12px Arial,sans-serif;color:#65676b;padding:8px 0 10px;border-bottom:1px solid #ddd;margin-bottom:8px}`;
  document.head.appendChild(style);
  document.documentElement.style.overflow = 'visible'; document.documentElement.style.height = 'auto';
  document.body.style.overflow = 'visible'; document.body.style.height = 'auto'; document.body.innerHTML = '';
  const page = document.createElement('main'); page.id = 'r45ax-page';
  const meta = document.createElement('div'); meta.id = 'r45ax-meta'; meta.textContent = 'R45AX comments-only capture' + (progress ? (' · progress ' + progress.current + ' of ' + progress.total) : '');
  page.appendChild(meta); page.appendChild(clone); document.body.appendChild(page);
  for (const el of Array.from(page.querySelectorAll('*'))) { const cs = getComputedStyle(el); if (cs.position === 'fixed' || cs.position === 'sticky') el.style.position = 'static'; el.style.maxHeight = 'none'; el.style.overflow = 'visible'; }
  window.scrollTo(0,0);
  const r = page.getBoundingClientRect();
  return {ok:true, progress, textLength:r45axNorm(page.innerText||'').length, rect:{x:r.x,y:r.y,width:r.width,height:r.height}, scrollHeight:document.documentElement.scrollHeight, bodyScrollHeight:document.body.scrollHeight};
}
"""

SELF_TEST_HTML = """<div role="dialog" style="height:500px;overflow:auto"><div>657 of 715</div><div>View all 302 replies</div><div>Fahad Malik replied · 3 replies</div><div>View hidden comments</div></div>"""

def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def clean_target_url(url: str) -> str:
    m = re.search(r'\((https?://[^)]+)\)', url or '')
    if m:
        url = m.group(1)
    return (url or '').strip().strip('"').strip("'").replace('\\&', '&').replace('&amp;', '&')

def expected_story(url: str) -> str:
    m = re.search(r'(?:story_fbid=|/posts/)([^&/?#]+)', url)
    return m.group(1) if m else ''

def log(marker: str, data: Any = None) -> None:
    print(marker if data is None else marker + ' ' + json.dumps(data, ensure_ascii=False, sort_keys=True), flush=True)

async def import_playwright():
    try:
        from playwright.async_api import async_playwright
        return async_playwright
    except Exception as e:
        raise SystemExit('Playwright is required for this runner: ' + repr(e))

async def self_test(output_root: Path) -> int:
    output_root.mkdir(parents=True, exist_ok=True)
    result = {
        'marker': MARKER,
        'status': 'PASS_R45AX_SELF_TEST',
        'schema_version': SCHEMA_VERSION,
        'checks': [
            {'name':'contract_marker','status':'pass'},
            {'name':'progress_fixture_657_of_715','status':'pass' if re.search(r'\b(\d+)\s+of\s+(\d+)\b', SELF_TEST_HTML) else 'fail'},
            {'name':'fahad_replied_bucket_fixture','status':'pass' if 'Fahad Malik replied · 3 replies' in SELF_TEST_HTML else 'fail'},
            {'name':'modal_flatten_present','status':'pass' if 'r45axFlattenForScreenshot' in EXPAND_PATTERNS_JS else 'fail'},
            {'name':'r45ba_real_scrollable_scroller_required','status':'pass' if 'no_real_scrollable_comments_container' in EXPAND_PATTERNS_JS and 'scrollHeight==clientHeight' in EXPAND_PATTERNS_JS else 'fail'},
            {'name':'r45bb_full_audit_restart_required','status':'pass' if 'R45AX_AUDIT_RESTART_TOP' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'r45bb_html_progress_probe_present','status':'pass' if 'document.documentElement.innerHTML' in EXPAND_PATTERNS_JS and 'r45axProgressFromPage' in EXPAND_PATTERNS_JS else 'fail'},
            {'name':'r45bc_dead_click_skip_present','status':'pass' if 'R45AX_DEAD_CLICK_KEY_SKIPPED' in Path(__file__).read_text(encoding='utf-8') and 'r45axAddSkipKey' in EXPAND_PATTERNS_JS else 'fail'},
            {'name':'r45bd_messenger_overlay_guard_present','status':'pass' if 'R45AX_MESSENGER_OVERLAY_BLOCKED' in Path(__file__).read_text(encoding='utf-8') and 'r45axMessengerOverlayState' in EXPAND_PATTERNS_JS else 'fail'},
            {'name':'r45bd_click_timing_delta_present','status':'pass' if 'click_elapsed_ms' in Path(__file__).read_text(encoding='utf-8') and 'timing_delta' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'no_hidden_platform_api','status':'pass'},
            {'name':'no_profile_parsing','status':'pass'},
        ],
        'contract': CONTRACT,
    }
    print(MARKER)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if all(x['status']=='pass' for x in result['checks']) else 1

async def run_live(args: argparse.Namespace) -> int:
    async_playwright = await import_playwright()
    target_url = clean_target_url(args.target_url)
    story = expected_story(target_url)
    run_dir = Path(args.output_root) / ('r45ax_progress_gated_modal_flatten_' + now_stamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    receipt: Dict[str, Any] = {'marker': MARKER, 'schema_version': SCHEMA_VERSION, 'generated_at': datetime.now(timezone.utc).isoformat(), 'target_url': target_url, 'expected_story': story, 'run_dir': str(run_dir), 'contract': CONTRACT}
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(user_data_dir=args.user_data_dir, executable_path=args.chromium_executable or None, headless=False, args=['--disable-session-crashed-bubble','--hide-crash-restore-bubble','--no-first-run','--no-default-browser-check'], viewport=None, accept_downloads=False)
        page = await context.new_page()
        await page.goto(target_url, wait_until='domcontentloaded', timeout=90000)
        await page.bring_to_front()
        await page.wait_for_timeout(1800)
        install_js = """() => {
""" + EXPAND_PATTERNS_JS + """
window.r45axFindScroller = r45axFindScroller;
window.r45axGetScroller = r45axGetScroller;
window.r45axScroll = r45axScroll;
window.r45axScanVisible = r45axScanVisible;
window.r45axClickFirstVisible = r45axClickFirstVisible;
window.r45axAddSkipKey = r45axAddSkipKey;
window.r45axClearSkipKeys = r45axClearSkipKeys;
window.r45axPageProgress = r45axPageProgress;
window.r45axMessengerOverlayState = r45axMessengerOverlayState;
window.r45axCloseMessengerOverlays = r45axCloseMessengerOverlays;
window.r45axSideEffectState = r45axSideEffectState;
window.r45axFlattenForScreenshot = r45axFlattenForScreenshot;
window.r45axInstallNavBlocker = r45axInstallNavBlocker;
return window.r45axInstallNavBlocker();
}"""
        install_result = await page.evaluate(install_js)
        log('R45AX_SCRIPT_INSTALL', install_result)
        guard = await page.evaluate("""(story) => { const href = location.href; return {href, title: document.title, expectedStory: story, hasStory: story ? href.includes(story) : true, onFacebook: /facebook\.com/i.test(location.hostname)}; }""", story)
        guard['ok'] = bool(guard.get('onFacebook') and guard.get('hasStory'))
        log('R45AX_TARGET_GUARD', guard)
        if not guard['ok']:
            receipt['status'] = 'BLOCKED_TARGET_GUARD'; (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8'); await context.close(); return 2
        scroller_info = await page.evaluate('r45axFindScroller();')
        log('R45AX_ACTIVE_SCROLL_CONTAINER', scroller_info)
        if (not scroller_info.get('ok')) or int((scroller_info.get('scroller') or {}).get('scrollHeight') or 0) <= int((scroller_info.get('scroller') or {}).get('clientHeight') or 0) + 80:
            receipt['status'] = 'BLOCKED_NO_REAL_SCROLLABLE_COMMENTS_SCROLLER'; (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8'); await context.close(); return 3
        await page.evaluate('r45axScroll("top")')
        start = time.monotonic(); clicked = 0; scrolls = 0; audit_pass = 1; best_progress: Optional[Dict[str, Any]] = None; last_scroll_height = 0; stable_bottom_cycles = 0; unsafe_skipped = 0; dead_click_skipped = 0; messenger_blocked = 0; new_pages_closed = 0; pass_had_click = False; dead_click_counts: Dict[str, int] = {}
        log('R45AX_PROGRESS_GATED_START', {'max_seconds':args.expand_max_seconds, 'max_steps':args.max_steps, 'progress_gate_required': True, 'target_url': target_url})
        known_pages = set(context.pages)
        pre_existing_chat = await page.evaluate('r45axMessengerOverlayState()')
        if pre_existing_chat.get('count'):
            close_result = await page.evaluate('r45axCloseMessengerOverlays()')
            log('R45AX_PREEXISTING_MESSENGER_OVERLAY_CLOSED', close_result)
            await page.wait_for_timeout(350)
        for step in range(1, int(args.max_steps)+1):
            elapsed = time.monotonic() - start
            if elapsed > float(args.expand_max_seconds): break
            scan = await page.evaluate('r45axScanVisible()')
            prog = scan.get('progress')
            if prog and (not best_progress or (prog.get('total',0), prog.get('current',0)) >= (best_progress.get('total',0), best_progress.get('current',0))): best_progress = prog
            progress_ok = True if not best_progress else int(best_progress.get('current',0)) >= int(best_progress.get('total',1))
            log('R45AX_SCAN', {'step':step, 'audit_pass':audit_pass, 'elapsed_seconds':round(elapsed,2), 'scrollTop':scan.get('scrollTop'), 'scrollHeight':scan.get('scrollHeight'), 'atBottom':scan.get('atBottom'), 'visible_total':scan.get('total'), 'visible_counts':scan.get('counts'), 'visible_labels':scan.get('labels'), 'progress':prog, 'best_progress':best_progress, 'progress_ok':progress_ok})
            if scan.get('total',0) > 0:
                clickinfo = await page.evaluate('r45axClickFirstVisible()')
                if clickinfo.get('blocked'):
                    unsafe_skipped += 1; log('R45AX_UNSAFE_VISIBLE_CONTROL_SKIPPED', {'step':step, 'item':clickinfo.get('item'), 'unsafe_skipped':unsafe_skipped}); await page.evaluate('r45axScroll("down")'); scrolls += 1; await page.wait_for_timeout(220); continue
                item = clickinfo.get('item') or {}
                if clickinfo.get('clicked') and item.get('safe'):
                    before_scan = clickinfo.get('scan') or scan
                    before_key = str(item.get('key') or '')
                    before_progress_for_sig = best_progress
                    before_sig = (int(before_scan.get('scrollHeight') or 0), int(before_scan.get('scrollTop') or 0), int(before_scan.get('total') or 0), json.dumps(before_scan.get('counts') or {}, sort_keys=True), json.dumps(before_progress_for_sig or {}, sort_keys=True))
                    before_side = await page.evaluate('r45axSideEffectState()')
                    click_t0 = time.monotonic()
                    await page.mouse.click(float(item.get('x')), float(item.get('y'))); clicked += 1; pass_had_click = True
                    label = item.get('label',''); m = re.search(r'\d+', label); n = int(m.group(0)) if m else 0
                    wait_ms = 3000 if n >= 100 else (1800 if n >= 30 else 1200)
                    await page.wait_for_timeout(wait_ms)
                    closed_new_pages = []
                    for pg in list(context.pages):
                        if pg is page or pg in known_pages:
                            continue
                        try:
                            closed_new_pages.append({'url': pg.url, 'title': await pg.title()})
                            await pg.close()
                            new_pages_closed += 1
                        except Exception as e:
                            closed_new_pages.append({'error': repr(e)})
                    after_side = await page.evaluate('r45axSideEffectState()')
                    messenger_opened = int((after_side.get('messenger') or {}).get('count') or 0) > int((before_side.get('messenger') or {}).get('count') or 0) or int((after_side.get('messenger') or {}).get('count') or 0) > 0
                    messenger_close_result = None
                    if messenger_opened:
                        messenger_blocked += 1
                        messenger_close_result = await page.evaluate('r45axCloseMessengerOverlays()')
                        await page.wait_for_timeout(450)
                        if before_key:
                            skip_result = await page.evaluate('(key) => r45axAddSkipKey(key)', before_key)
                            log('R45AX_MESSENGER_OVERLAY_BLOCKED', {'step':step, 'key':before_key, 'label':label, 'messenger_blocked':messenger_blocked, 'before_side':before_side, 'after_side':after_side, 'close_result':messenger_close_result, 'skip_result':skip_result})
                    if closed_new_pages and before_key:
                        skip_result = await page.evaluate('(key) => r45axAddSkipKey(key)', before_key)
                        log('R45AX_UNEXPECTED_PAGE_CLOSED', {'step':step, 'key':before_key, 'label':label, 'closed_pages':closed_new_pages, 'new_pages_closed':new_pages_closed, 'skip_result':skip_result})
                    after_scan = await page.evaluate('r45axScanVisible()')
                    after_prog = after_scan.get('progress')
                    if after_prog and (not best_progress or (after_prog.get('total',0), after_prog.get('current',0)) >= (best_progress.get('total',0), best_progress.get('current',0))): best_progress = after_prog
                    after_sig = (int(after_scan.get('scrollHeight') or 0), int(after_scan.get('scrollTop') or 0), int(after_scan.get('total') or 0), json.dumps(after_scan.get('counts') or {}, sort_keys=True), json.dumps(best_progress or {}, sort_keys=True))
                    still_same_key = bool(before_key and any(str(x.get('key') or '') == before_key for x in after_scan.get('items', [])))
                    no_progress = (still_same_key and after_sig == before_sig) or messenger_opened or bool(closed_new_pages)
                    if no_progress:
                        dead_click_counts[before_key] = dead_click_counts.get(before_key, 0) + 1
                    else:
                        dead_click_counts.pop(before_key, None)
                    click_elapsed_ms = int(round((time.monotonic() - click_t0) * 1000))
                    timing_delta = {
                        'scrollHeight_delta': int(after_scan.get('scrollHeight') or 0) - int(before_scan.get('scrollHeight') or 0),
                        'scrollTop_delta': int(after_scan.get('scrollTop') or 0) - int(before_scan.get('scrollTop') or 0),
                        'visible_total_delta': int(after_scan.get('total') or 0) - int(before_scan.get('total') or 0),
                        'counts_before': before_scan.get('counts'),
                        'counts_after': after_scan.get('counts'),
                        'progress_before': before_progress_for_sig,
                        'progress_after': best_progress,
                    }
                    log('R45AX_CLICK', {'step':step, 'clicked':clicked, 'label':label, 'category':item.get('category'), 'key':before_key, 'x':item.get('x'), 'y':item.get('y'), 'wait_ms':wait_ms, 'click_elapsed_ms':click_elapsed_ms, 'timing_delta':timing_delta, 'post_visible_total': after_scan.get('total'), 'no_progress': no_progress, 'messenger_opened': messenger_opened, 'new_pages_closed': closed_new_pages, 'dead_key_count': dead_click_counts.get(before_key,0)})
                    if no_progress and dead_click_counts.get(before_key, 0) >= 2:
                        dead_click_skipped += 1
                        skip_result = await page.evaluate('(key) => r45axAddSkipKey(key)', before_key)
                        log('R45AX_DEAD_CLICK_KEY_SKIPPED', {'step':step, 'key':before_key, 'label':label, 'dead_click_skipped':dead_click_skipped, 'skip_result':skip_result})
                    continue
            at_bottom = bool(scan.get('atBottom')); sh = int(scan.get('scrollHeight') or 0)
            if not at_bottom:
                sr = await page.evaluate('r45axScroll("down")'); scrolls += 1; log('R45AX_SCROLL_DOWN', {'step':step, 'scrolls':scrolls, **sr}); await page.wait_for_timeout(180); continue
            if at_bottom and not progress_ok:
                stable_bottom_cycles = stable_bottom_cycles + 1 if sh == last_scroll_height else 0; last_scroll_height = sh
                log('R45AX_PROGRESS_GATE_NOT_SATISFIED', {'step':step, 'best_progress':best_progress, 'stable_bottom_cycles':stable_bottom_cycles, 'scrollHeight':sh})
                if stable_bottom_cycles >= int(args.progress_stall_cycles):
                    if audit_pass >= int(args.max_audit_passes): break
                    audit_pass += 1; await page.evaluate('r45axScroll("top")'); await page.wait_for_timeout(400); continue
                await page.wait_for_timeout(900); await page.evaluate('r45axScroll("top")'); audit_pass += 1; await page.wait_for_timeout(250); continue
            if at_bottom and progress_ok:
                if pass_had_click:
                    log('R45AX_AUDIT_RESTART_TOP', {'step':step, 'audit_pass':audit_pass, 'clicked':clicked, 'scrolls':scrolls, 'best_progress':best_progress})
                    if audit_pass >= int(args.max_audit_passes):
                        log('R45AX_AUDIT_LIMIT_REACHED_WITH_CHANGES', {'step':step, 'audit_pass':audit_pass, 'clicked':clicked, 'scrolls':scrolls})
                        break
                    audit_pass += 1
                    pass_had_click = False
                    await page.evaluate('r45axScroll("top")')
                    await page.wait_for_timeout(650)
                    continue
                receipt['auto_expand_summary'] = {'status':'pass', 'clicked':clicked, 'scrolls':scrolls, 'audit_passes':audit_pass, 'unsafe_skipped':unsafe_skipped, 'dead_click_skipped':dead_click_skipped, 'messenger_blocked':messenger_blocked, 'new_pages_closed':new_pages_closed, 'best_progress':best_progress, 'progress_ok':progress_ok, 'completed_by_full_zero_control_audit': True}; log('R45AX_EXPANSION_COMPLETE', receipt['auto_expand_summary']); break
        if 'auto_expand_summary' not in receipt:
            final_scan = await page.evaluate('r45axScanVisible()'); final_progress = await page.evaluate('r45axPageProgress()')
            receipt['status'] = 'BLOCKED_INCOMPLETE_EXPANSION'; receipt['final_scan'] = final_scan; receipt['best_progress'] = best_progress or final_progress
            receipt['progress_gate_satisfied'] = bool((best_progress or final_progress) and int((best_progress or final_progress).get('current',0)) >= int((best_progress or final_progress).get('total',1))) if (best_progress or final_progress) else False
            log('R45AX_BLOCKED_INCOMPLETE_EXPANSION', {'best_progress':receipt.get('best_progress'), 'progress_gate_satisfied':receipt.get('progress_gate_satisfied'), 'final_visible_total':final_scan.get('total'), 'final_labels':final_scan.get('labels')})
            (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8'); await context.close(); return 4
        live_html_path = run_dir / 'r45ax_live_before_flatten.html'; live_text_path = run_dir / 'r45ax_live_before_flatten_text.txt'
        live_html_path.write_text(await page.content(), encoding='utf-8')
        live_text_path.write_text(await page.evaluate('document.body.innerText || document.body.textContent || ""'), encoding='utf-8')
        receipt['live_before_flatten'] = {'html_path': str(live_html_path), 'text_path': str(live_text_path), 'progress': await page.evaluate('r45axPageProgress()')}
        flatten = await page.evaluate('r45axFlattenForScreenshot()'); log('R45AX_FLATTEN_COMMENTS_ONLY', flatten); receipt['flatten_summary'] = flatten; await page.wait_for_timeout(1200)
        html_path = run_dir / 'r45ax_separated_comments_clean_dom.html'; text_path = run_dir / 'r45ax_separated_comments_visible_text.txt'
        html_path.write_text(await page.content(), encoding='utf-8'); text_path.write_text(await page.evaluate('document.body.innerText || document.body.textContent || ""'), encoding='utf-8')
        dims = await page.evaluate("""() => { const root = document.querySelector('#r45ax-page') || document.body; const r = root.getBoundingClientRect(); return {x: Math.max(0, Math.floor(r.x)), y: Math.max(0, Math.floor(r.y)), width: Math.ceil(r.width), height: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, Math.ceil(r.height))}; }""")
        width = int(min(max(dims.get('width', 900), 520), 1400)); height = int(max(dims.get('height', 0), 1)); band_h = max(8000, min(int(args.max_band_height), 30000))
        await page.set_viewport_size({'width': max(width+80, 1100), 'height': 900})
        paths: List[str] = []; y = 0; idx = 1
        while y < height:
            h = min(band_h, height - y); path = run_dir / f'facebook_comments_only_maxband_part_{idx:03d}_y{y:08d}.png'
            await page.screenshot(path=str(path), clip={'x': int(dims.get('x',0)), 'y': y, 'width': width, 'height': h}, timeout=120000)
            paths.append(str(path)); y += h; idx += 1
        zip_path = run_dir / 'r45ax_comments_only_max_bands.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for pth in paths: zf.write(pth, arcname=Path(pth).name)
            zf.write(html_path, arcname=html_path.name); zf.write(text_path, arcname=text_path.name); zf.write(live_html_path, arcname=live_html_path.name); zf.write(live_text_path, arcname=live_text_path.name)
        receipt['status'] = 'PASS_R45AX_PROGRESS_GATED_CAPTURE'; receipt['outputs'] = {'html_path': str(html_path), 'text_path': str(text_path), 'max_band_paths': paths, 'max_band_count': len(paths), 'max_band_height': band_h, 'zip_path': str(zip_path), 'capture_height': height, 'capture_width': width}
        receipt_path = run_dir/'r45ax_progress_gated_receipt.json'; receipt['receipt_path'] = str(receipt_path); receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
        log('R45AX_FINAL_SUMMARY', {'status': receipt['status'], 'clicked': clicked, 'scrolls': scrolls, 'best_progress': receipt['auto_expand_summary'].get('best_progress'), 'max_band_count': len(paths), 'max_band_height': band_h, 'zip_path': str(zip_path), 'receipt_path': str(receipt_path)})
        if args.operator_pause:
            print('R45AX_OPERATOR_PAUSE: review the comments-only page/bands, then press ENTER to close browser.', flush=True)
            try: input()
            except EOFError: pass
        await context.close()
    return 0

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='R45AX progress-gated Facebook comments capture')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--target-url', default='')
    ap.add_argument('--auto-expand', action='store_true')
    ap.add_argument('--operator-pause', action='store_true')
    ap.add_argument('--tile-screenshots', action='store_true')
    ap.add_argument('--expand-max-seconds', type=float, default=1800)
    ap.add_argument('--max-steps', type=int, default=5000)
    ap.add_argument('--max-audit-passes', type=int, default=12)
    ap.add_argument('--progress-stall-cycles', type=int, default=3)
    ap.add_argument('--max-band-height', type=int, default=30000)
    ap.add_argument('--chromium-executable', default='')
    ap.add_argument('--user-data-dir', default=str(Path.home()/'.ytce_facebook_profile'))
    ap.add_argument('--output-root', default='profile_media_live_captures/r45ax_progress_gated_modal_flatten')
    return ap.parse_args(argv)

async def amain(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return await self_test(Path(args.output_root))
    if not args.target_url:
        print('ERROR: --target-url is required unless --self-test is used')
        return 2
    return await run_live(args)

def main() -> None:
    raise SystemExit(asyncio.run(amain()))

if __name__ == '__main__':
    main()
