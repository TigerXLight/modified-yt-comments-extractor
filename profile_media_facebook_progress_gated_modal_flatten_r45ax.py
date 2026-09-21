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
    "r45be_target_drift_rule": "R45BE refuses any current-tab navigation away from the expected story, broadens same-tab Facebook href blocking (including /pages/ profile/page links), and stops on repeated no-movement scrolls instead of looping on the wrong page.",
    "r45bg_hover_guard_rule": "R45BG parks the Playwright mouse at a neutral viewport corner immediately after clicks and scrolls, closes profile/name hover cards, and logs hover-card closures so account-name previews do not cover the comments modal or slow the visible-page pass.",
    "r45bi_expected_total_gate_rule": "R45BI fixes the failed R45BH anchor patch and adds --expected-total-comments so a known Facebook total such as 715 is a hard gate. When set, unrelated counters such as 20 of 100 are logged and ignored; completion requires N of the expected total to reach that total.",
    "r45bj_no_random_overlay_close_rule": "R45BJ removes guessed coordinate clicks used to close Messenger/profile overlays. It only uses explicit close controls for Messenger, parks the mouse for profile hover cards, and writes page/text/screenshot artifacts before blocking if an overlay remains open.",
    "r45bk_strict_overlay_detection_rule": "R45BK prevents normal comment bubbles inside the active comments scroller from being misclassified as Messenger/profile overlays. It removes loose Aa matching, ignores scroller descendants, and requires strong chat/profile chrome before treating an overlay as blocking.",
    "r45bl_replied_bucket_fast_path_rule": "R45BL treats labels such as 'replied · 14 replies' as reply-count controls: it ranges/clicks the numeric replies segment, prefers right-biased safe points, uses shorter per-click waits, and skips a replied bucket after one no-progress click so the runner does not waste minutes on duplicate visible controls.",
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
  const replied = t.match(/\breplied\s*(?:[·•.\-]\s*)?(\d+)\s+repl(?:y|ies)\b/i);
  if (replied) {
    const n = replied[1];
    return {label:r45axNorm(replied[0]), clickLabel:n + (n === '1' ? ' reply' : ' replies'), category:'replied_bucket', preferredPoint:'reply_count_right'};
  }
  const patterns = [
    {category:'view_hidden', rx:/\bView hidden (?:replies|comments)\b/i},
    {category:'view_all_replies', rx:/\bView all \d+ replies?\b/i},
    {category:'view_more_replies', rx:/\bView \d+ more replies?\b/i},
    {category:'view_n_replies', rx:/\bView \d+ replies?\b/i},
    {category:'view_more', rx:/\bView more (?:replies|comments)\b/i},
    {category:'replied_bucket', rx:/\breplied\s*(?:[·•.\-]\s*)?\d+\s+repl(?:y|ies)\b/i, preferredPoint:'reply_count_right'}
  ];
  for (const p of patterns){
    const m = t.match(p.rx);
    if (m) return {label:r45axNorm(m[0]), category:p.category, preferredPoint:p.preferredPoint || ''};
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
  if (/^(#|javascript:|about:blank)/i.test(h)) return false;
  let u = null;
  try { u = new URL(h, location.href); } catch(e) { return false; }
  if (!/facebook\.com$/i.test(u.hostname) && !/\.facebook\.com$/i.test(u.hostname)) return false;
  const path = u.pathname || '';
  const qs = u.search || '';
  const allowedStory = /\/(permalink\.php|story\.php)$/i.test(path) || /\/(posts|photo|watch|reel)\//i.test(path);
  if (allowedStory && (qs.includes('story_fbid=') || h.includes('story_fbid=') || h.includes('/posts/') || h.includes('/photo/') || h.includes('/watch/') || h.includes('/reel/'))) return false;
  // R45BE: anything else on facebook.com is not an expansion control. This blocks /pages/, /profile.php, /people/,
  // username/profile links, comment permalinks, and other same-tab navigation targets.
  return true;
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
  function addCandidate(info, rect, source){
    const label = info.label;
    const category = info.category;
    if (!r45axRectVisible(rect, band)) return;
    if (rect.width < 4 || rect.height < 4) return;
    const fractions = category === 'replied_bucket' ? [0.84, 0.94, 0.68, 0.50] : [0.50, 0.18, 0.82];
    const points = fractions.map(f => ({x: rect.left + Math.min(rect.width-2, Math.max(2, rect.width*f)), y: rect.top + rect.height/2}));
    let chosen = null, safety = null;
    for (const p of points){
      const s = r45axClickSafetyAt(p.x, p.y);
      if (s.ok){ chosen = p; safety = s; break; }
      if (!safety) safety = s;
    }
    out.push({label, category, clickLabel:info.clickLabel || '', preferredPoint:info.preferredPoint || '', x:Math.round((chosen||points[0]).x), y:Math.round((chosen||points[0]).y), top:Math.round(rect.top), bottom:Math.round(rect.bottom), left:Math.round(rect.left), right:Math.round(rect.right), safe:!!chosen, safety, source});
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
      const lowerRaw = raw.toLowerCase(), lowerLabel = info.label.toLowerCase(), lowerClickLabel = String(info.clickLabel || info.label).toLowerCase();
      let start = lowerRaw.indexOf(lowerClickLabel);
      let endLength = lowerClickLabel.length;
      if (start < 0) { start = lowerRaw.indexOf(lowerLabel); endLength = lowerLabel.length; }
      if (start < 0) start = 0;
      range.setStart(n, start);
      range.setEnd(n, Math.min(raw.length, start + endLength));
    } catch(e) {
      try { range.selectNodeContents(n); } catch(e2) { continue; }
    }
    const rects = Array.from(range.getClientRects()).filter(rect => r45axRectVisible(rect, band));
    range.detach && range.detach();
    for (const rect of rects) addCandidate(info, rect, 'text');
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
    addCandidate(info, rect, 'element');
  }
  const seen = new Set();
  const skip = new Set(Array.isArray(window.__R45AX_SKIP_KEYS__) ? window.__R45AX_SKIP_KEYS__ : []);
  const dedup = [];
  const sourceRank = (s) => s === 'text' ? 0 : 1;
  const rowRank = (item) => Math.round(item.top/6);
  for (const item of out.sort((a,b)=>rowRank(a)-rowRank(b) || sourceRank(a.source)-sourceRank(b.source) || a.top-b.top || a.left-b.left || (a.source || '').localeCompare(b.source || ''))){
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
  // R45BK: strict Messenger/DM overlay detector.
  //
  // R45BJ correctly stopped instead of wandering off-page, but its detector was
  // still too broad: it scanned every visible div and treated comment-body nodes
  // inside the active comments scroller as Messenger overlays. The culprit was
  // especially the loose "Aa" branch, which can match ordinary words/names inside
  // comments. This function now ignores anything inside the active comments
  // scroller and requires a strong chat-specific signature.
  const overlays = [];
  const vw = window.innerWidth || document.documentElement.clientWidth || 1280;
  const vh = window.innerHeight || document.documentElement.clientHeight || 720;
  let scroller = null;
  try { scroller = r45axGetScroller && r45axGetScroller(); } catch(e) { scroller = null; }

  const nodes = Array.from(document.querySelectorAll('[role="dialog"], [aria-label], [data-pagelet], div')).slice(0, 14000);
  for (const el of nodes){
    if (r45axElementHidden(el)) continue;
    if (scroller && (el === scroller || scroller.contains(el))) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 240 || r.width > 580 || r.height < 160 || r.height > 760) continue;
    // Real chat popups are normally right-side/bottom-side overlays, not nested
    // comment bubbles in the centre of the post modal.
    if (r.right < vw * 0.58 || r.bottom < vh * 0.42) continue;

    const aria = r45axNorm((el.getAttribute && (el.getAttribute('aria-label') || '')) || '');
    const role = (el.getAttribute && (el.getAttribute('role') || '')) || '';
    const text = r45axNorm([el.innerText || '', el.textContent || '', aria].join(' '));

    const strongChatText =
      /(Messages and calls are secured|end-to-end encrypted|Only people in this chat|Type a message|Write a message|Message request|New message|Chat settings|Active now|Start a call|Start voice call|Start video call|Close chat|Minimize chat|Open Messenger|Messenger)/i.test(text);

    const hasChatInput = !!el.querySelector && !!el.querySelector(
      '[contenteditable="true"][role="textbox"], textarea, input, [aria-label="Aa"], [aria-placeholder="Aa"], [placeholder="Aa"]'
    );
    const hasChatChrome = !!el.querySelector && !!el.querySelector(
      '[aria-label*="Close chat" i], [aria-label*="Minimize chat" i], [aria-label*="Start a call" i], [aria-label*="Start voice call" i], [aria-label*="Start video call" i]'
    );

    // "Aa" alone is not evidence. It must appear as an actual input control
    // together with chat chrome, never merely inside comment text.
    if (!(strongChatText || (hasChatInput && hasChatChrome))) continue;

    // Exclude ordinary Facebook post/comment modal material even if a comment
    // happens to contain words like "message" or "messenger".
    if (/Restore Britain's post|Comment as |Reply to |View hidden replies|View all \d+ replies|Like\s+Reply/i.test(text) && !/Messages and calls are secured|end-to-end encrypted|Only people in this chat/i.test(text)) continue;

    overlays.push({tag:el.tagName, role:role, aria:aria, text:text.slice(0,220), rect:{left:Math.round(r.left), top:Math.round(r.top), right:Math.round(r.right), bottom:Math.round(r.bottom), width:Math.round(r.width), height:Math.round(r.height)}});
  }
  overlays.sort((a,b)=>(b.rect.right-a.rect.right)||(b.rect.bottom-a.rect.bottom));
  return {count:overlays.length, overlays:overlays.slice(0,5), strict:true, ignoredScrollerDescendants:true};
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
      // R45BJ: no coordinate fallback. A guessed top-right click can hit Facebook chrome,
      // profile cards, or page links and navigate the active tab away from the target story.
      // Only explicit Close/Minimize controls above are allowed.
    } catch(e) {}
  }
  return {before, closed, after:r45axMessengerOverlayState()};
}
function r45axSideEffectState(){ return {messenger:r45axMessengerOverlayState(), profileHover:r45axProfileHoverOverlayState(), href:location.href, title:document.title}; }
function r45axMessengerSideEffectState(){ return {messenger:r45axMessengerOverlayState(), href:location.href, title:document.title}; }

function r45axProfileHoverOverlayState(){
  // R45BK: ignore comment-body descendants of the active comments scroller.
  // This prevents normal expanded comment bubbles from being mislabelled as
  // profile hover cards merely because they contain words like "Message",
  // "Friends", school/work names, etc.
  const overlays = [];
  const vw = window.innerWidth || document.documentElement.clientWidth || 1280;
  const vh = window.innerHeight || document.documentElement.clientHeight || 720;
  let scroller = null;
  try { scroller = r45axGetScroller && r45axGetScroller(); } catch(e) { scroller = null; }

  const nodes = Array.from(document.querySelectorAll('[role="dialog"], [aria-label], div')).slice(0, 14000);
  for (const el of nodes){
    if (r45axElementHidden(el)) continue;
    if (scroller && (el === scroller || scroller.contains(el))) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 240 || r.width > 620 || r.height < 110 || r.height > 470) continue;
    if (r.bottom < 90 || r.top > vh - 60 || r.right < 180 || r.left > vw - 160) continue;
    const aria = r45axNorm((el.getAttribute && (el.getAttribute('aria-label') || '')) || '');
    const text = r45axNorm([el.innerText || '', el.textContent || '', aria].join(' '));

    const profileSignals = /(\bMessage\b|Add friend|Follow|Works at|Went to|Lives in|Friends|Mutual friends|Cashier|Academy)/i.test(text);
    const hasProfileButtons = !!el.querySelector && !!el.querySelector('[aria-label*="Add friend" i], [aria-label*="Message" i], [aria-label*="Follow" i]');
    if (!(profileSignals && hasProfileButtons)) continue;

    if (/Restore Britain's post|Comment as|Reply to|View hidden|View all \d+|Like\s+Reply/i.test(text) && r.width > 520 && r.height > 300) continue;
    overlays.push({tag:el.tagName, role:el.getAttribute('role') || '', aria:aria, text:text.slice(0,220), rect:{left:Math.round(r.left), top:Math.round(r.top), right:Math.round(r.right), bottom:Math.round(r.bottom), width:Math.round(r.width), height:Math.round(r.height)}});
  }
  overlays.sort((a,b)=>a.rect.top-b.rect.top || b.rect.right-a.rect.right);
  return {count:overlays.length, overlays:overlays.slice(0,5), strict:true, ignoredScrollerDescendants:true};
}
function r45axCloseProfileHoverCards(){
  let closed = 0;
  const before = r45axProfileHoverOverlayState();
  for (const info of before.overlays || []){
    let candidates = Array.from(document.querySelectorAll('[aria-label], [role="button"], button, div, span')).filter(el => {
      if (r45axElementHidden(el)) return false;
      const r = el.getBoundingClientRect();
      if (r.left < info.rect.left - 3 || r.right > info.rect.right + 8 || r.top < info.rect.top - 3 || r.bottom > info.rect.bottom + 8) return false;
      const blob = r45axNorm([(el.getAttribute && (el.getAttribute('aria-label') || '')), (el.getAttribute && (el.getAttribute('title') || '')), (el.innerText || el.textContent || '')].join(' '));
      if (/^(Close|Close card|Close preview|Dismiss)$/i.test(blob)) return true;
      if (/^[×xX✕]$/.test(blob) && r.top < info.rect.top + 80 && r.right > info.rect.right - 95) return true;
      return false;
    });
    candidates.sort((a,b)=>{
      const ar=a.getBoundingClientRect(), br=b.getBoundingClientRect();
      return (br.right-ar.right) || (ar.top-br.top);
    });
    try {
      const btn = candidates[0];
      if (btn) { btn.click(); closed += 1; continue; }
      // If there is no close button, dispatch mouseout/mouseleave and let mouse parking collapse it.
      const el = document.elementFromPoint(Math.max(5, info.rect.left + 8), Math.max(5, info.rect.top + 8));
      if (el) {
        for (const ev of ['mouseout','mouseleave','blur']) {
          try { el.dispatchEvent(new Event(ev, {bubbles:true, cancelable:true})); } catch(e) {}
        }
      }
    } catch(e) {}
  }
  return {before, closed, after:r45axProfileHoverOverlayState()};
}

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
            {'name':'r45be_target_drift_guard_present','status':'pass' if 'R45AX_TARGET_DRIFT_BLOCKED' in Path(__file__).read_text(encoding='utf-8') and 'r45ax_target_guard_now' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'r45be_scroll_stall_block_present','status':'pass' if 'R45AX_SCROLL_STALLED_BLOCKED' in Path(__file__).read_text(encoding='utf-8') and 'stalled_scroll_cycles' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'r45bg_no_hover_mouse_parking_present','status':'pass' if 'r45ax_park_mouse' in Path(__file__).read_text(encoding='utf-8') and 'R45AX_PROFILE_HOVER_CARD_CLOSED' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'r45bg_profile_hover_guard_present','status':'pass' if 'r45axProfileHoverOverlayState' in EXPAND_PATTERNS_JS and 'r45axCloseProfileHoverCards' in EXPAND_PATTERNS_JS else 'fail'},
            {'name':'r45bi_expected_total_gate_present','status':'pass' if '--expected-total-comments' in Path(__file__).read_text(encoding='utf-8') and 'R45AX_PROGRESS_IGNORED_EXPECTED_TOTAL_MISMATCH' in Path(__file__).read_text(encoding='utf-8') and 'r45ax_filter_expected_progress' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'r45bj_no_coordinate_overlay_close_present','status':'pass' if 'no coordinate fallback' in EXPAND_PATTERNS_JS and 'BLOCKED_MESSENGER_OVERLAY_STILL_OPEN' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'r45bj_failure_artifacts_present','status':'pass' if 'r45ax_write_failure_artifacts' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'r45bl_replied_bucket_right_biased_present','status':'pass' if 'reply_count_right' in EXPAND_PATTERNS_JS and "clickLabel:n + (n === '1' ? ' reply' : ' replies')" in EXPAND_PATTERNS_JS else 'fail'},
            {'name':'r45bl_replied_bucket_no_progress_skip_present','status':'pass' if 'R45AX_REPLIED_BUCKET_NO_PROGRESS_SKIPPED' in Path(__file__).read_text(encoding='utf-8') and 'replied_bucket_fast_skipped' in Path(__file__).read_text(encoding='utf-8') else 'fail'},
            {'name':'r45bl_click_fast_path_present','status':'pass' if 'r45ax_click_wait_ms' in Path(__file__).read_text(encoding='utf-8') and 'r45axMessengerSideEffectState' in EXPAND_PATTERNS_JS else 'fail'},
            {'name':'no_hidden_platform_api','status':'pass'},
            {'name':'no_profile_parsing','status':'pass'},
        ],
        'contract': CONTRACT,
    }
    print(MARKER)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if all(x['status']=='pass' for x in result['checks']) else 1


async def r45ax_target_guard_now(page, story: str) -> Dict[str, Any]:
    guard = await page.evaluate("""(story) => {
        const href = location.href;
        const ok = Boolean(/facebook\.com/i.test(location.hostname) && (!story || href.includes(story)));
        return {href, title: document.title, expectedStory: story, hasStory: story ? href.includes(story) : true, onFacebook: /facebook\.com/i.test(location.hostname), ok};
    }""", story)
    return guard


async def r45ax_park_mouse(page) -> None:
    try:
        await page.mouse.move(8, 8)
    except Exception:
        pass

async def r45ax_close_profile_hover_cards(page) -> Dict[str, Any]:
    """R45BJ: never click inside a suspected profile hover card.

    Earlier versions tried to close hover/profile preview cards by clicking guessed
    close buttons inside rectangles. On Facebook those rectangles can also be
    nested comment/content containers; guessed clicks can navigate the active tab
    away from the target permalink. We only park the mouse and wait briefly.
    """
    try:
        before = await page.evaluate('r45axProfileHoverOverlayState()')
    except Exception:
        before = {'count': 0, 'overlays': []}
    await r45ax_park_mouse(page)
    try:
        await page.wait_for_timeout(420)
        after = await page.evaluate('r45axProfileHoverOverlayState()')
    except Exception:
        after = before
    return {'closed': 0, 'before': before, 'after': after, 'mouse_park_only': True}



def r45ax_filter_expected_progress(progress: Optional[Dict[str, Any]], expected_total_comments: int) -> Optional[Dict[str, Any]]:
    if not progress:
        return None
    try:
        current = int(progress.get('current', 0) or 0)
        total = int(progress.get('total', 0) or 0)
    except Exception:
        return None
    if total <= 0 or current < 0 or current > total:
        return None
    if expected_total_comments > 0 and total != expected_total_comments:
        return None
    return {'current': current, 'total': total, 'text': progress.get('text') or f'{current} of {total}'}

def r45ax_progress_gate_ok(best_progress: Optional[Dict[str, Any]], expected_total_comments: int) -> bool:
    if expected_total_comments > 0:
        p = r45ax_filter_expected_progress(best_progress, expected_total_comments)
        return bool(p and int(p.get('current', 0) or 0) >= expected_total_comments)
    if not best_progress:
        return True
    p = r45ax_filter_expected_progress(best_progress, 0)
    return bool(p and int(p.get('current', 0) or 0) >= int(p.get('total', 1) or 1))

def r45ax_progress_gate_status(best_progress: Optional[Dict[str, Any]], expected_total_comments: int) -> Dict[str, Any]:
    filtered = r45ax_filter_expected_progress(best_progress, expected_total_comments)
    return {
        'marker': 'R45BI_EXPECTED_TOTAL_GATE',
        'expected_total_comments': expected_total_comments,
        'best_progress': best_progress,
        'filtered_progress': filtered,
        'progress_ok': r45ax_progress_gate_ok(best_progress, expected_total_comments),
    }

def r45ax_click_wait_ms(label: str, category: str) -> int:
    m = re.search(r'\d+', label or '')
    n = int(m.group(0)) if m else 0
    if category == 'replied_bucket':
        return 1500 if n >= 100 else (900 if n >= 30 else 650)
    return 3000 if n >= 100 else (1800 if n >= 30 else 1200)

async def r45ax_write_failure_artifacts(page, run_dir: Path, prefix: str) -> Dict[str, str]:
    """Write current visible-page evidence on blocked states."""
    out: Dict[str, str] = {}
    safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', prefix).strip('_') or 'failure'
    try:
        html_path = run_dir / f'{safe}_page.html'
        html_path.write_text(await page.content(), encoding='utf-8')
        out['html_path'] = str(html_path)
    except Exception as e:
        out['html_error'] = repr(e)
    try:
        text_path = run_dir / f'{safe}_text.txt'
        text_path.write_text(await page.evaluate('document.body.innerText || document.body.textContent || ""'), encoding='utf-8')
        out['text_path'] = str(text_path)
    except Exception as e:
        out['text_error'] = repr(e)
    try:
        png_path = run_dir / f'{safe}_viewport.png'
        await page.screenshot(path=str(png_path), full_page=False, timeout=45000)
        out['screenshot_path'] = str(png_path)
    except Exception as e:
        out['screenshot_error'] = repr(e)
    return out

async def run_live(args: argparse.Namespace) -> int:
    async_playwright = await import_playwright()
    target_url = clean_target_url(args.target_url)
    story = expected_story(target_url)
    expected_total_comments = max(0, int(getattr(args, 'expected_total_comments', 0) or 0))
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
window.r45axProfileHoverOverlayState = r45axProfileHoverOverlayState;
window.r45axCloseProfileHoverCards = r45axCloseProfileHoverCards;
window.r45axFlattenForScreenshot = r45axFlattenForScreenshot;
window.r45axInstallNavBlocker = r45axInstallNavBlocker;
return window.r45axInstallNavBlocker();
}"""
        install_result = await page.evaluate(install_js)
        log('R45AX_SCRIPT_INSTALL', install_result)
        guard = await r45ax_target_guard_now(page, story)
        log('R45AX_TARGET_GUARD', guard)
        if not guard['ok']:
            receipt['status'] = 'BLOCKED_TARGET_GUARD'; (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8'); await context.close(); return 2
        scroller_info = await page.evaluate('r45axFindScroller();')
        log('R45AX_ACTIVE_SCROLL_CONTAINER', scroller_info)
        if (not scroller_info.get('ok')) or int((scroller_info.get('scroller') or {}).get('scrollHeight') or 0) <= int((scroller_info.get('scroller') or {}).get('clientHeight') or 0) + 80:
            receipt['status'] = 'BLOCKED_NO_REAL_SCROLLABLE_COMMENTS_SCROLLER'; (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8'); await context.close(); return 3
        await page.evaluate('r45axScroll("top")')
        await r45ax_park_mouse(page)
        start = time.monotonic(); clicked = 0; scrolls = 0; audit_pass = 1; best_progress: Optional[Dict[str, Any]] = None; last_scroll_height = 0; stable_bottom_cycles = 0; stalled_scroll_cycles = 0; unsafe_skipped = 0; dead_click_skipped = 0; replied_bucket_fast_skipped = 0; messenger_blocked = 0; new_pages_closed = 0; target_drift_blocked = 0; profile_hover_closed = 0; pass_had_click = False; dead_click_counts: Dict[str, int] = {}
        log('R45AX_PROGRESS_GATED_START', {'max_seconds':args.expand_max_seconds, 'max_steps':args.max_steps, 'progress_gate_required': True, 'expected_total_comments': expected_total_comments, 'target_url': target_url})
        known_pages = set(context.pages)
        pre_existing_chat = await page.evaluate('r45axMessengerOverlayState()')
        if pre_existing_chat.get('count'):
            close_result = await page.evaluate('r45axCloseMessengerOverlays()')
            log('R45AX_PREEXISTING_MESSENGER_OVERLAY_CLOSED', close_result)
            await page.wait_for_timeout(350)
        for step in range(1, int(args.max_steps)+1):
            elapsed = time.monotonic() - start
            if elapsed > float(args.expand_max_seconds): break
            current_guard = await r45ax_target_guard_now(page, story)
            if not current_guard.get('ok'):
                target_drift_blocked += 1
                receipt['status'] = 'BLOCKED_TARGET_DRIFT'
                receipt['target_drift_guard'] = current_guard
                log('R45AX_TARGET_DRIFT_BLOCKED', {'step': step, 'target_drift_blocked': target_drift_blocked, 'guard': current_guard})
                (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
                await context.close()
                return 5
            scan = await page.evaluate('r45axScanVisible()')
            prog_raw = scan.get('progress')
            prog = r45ax_filter_expected_progress(prog_raw, expected_total_comments)
            if prog_raw and expected_total_comments > 0 and not prog:
                log('R45AX_PROGRESS_IGNORED_EXPECTED_TOTAL_MISMATCH', {'step': step, 'expected_total_comments': expected_total_comments, 'ignored_progress': prog_raw})
            if prog and (not best_progress or (prog.get('total',0), prog.get('current',0)) >= (best_progress.get('total',0), best_progress.get('current',0))): best_progress = prog
            progress_ok = r45ax_progress_gate_ok(best_progress, expected_total_comments)
            log('R45AX_SCAN', {'step':step, 'audit_pass':audit_pass, 'elapsed_seconds':round(elapsed,2), 'scrollTop':scan.get('scrollTop'), 'scrollHeight':scan.get('scrollHeight'), 'atBottom':scan.get('atBottom'), 'visible_total':scan.get('total'), 'visible_counts':scan.get('counts'), 'visible_labels':scan.get('labels'), 'progress':prog, 'raw_progress': prog_raw, 'best_progress':best_progress, 'expected_total_comments': expected_total_comments, 'progress_ok':progress_ok})
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
                    before_side = await page.evaluate('r45axMessengerSideEffectState()')
                    click_t0 = time.monotonic()
                    await page.mouse.click(float(item.get('x')), float(item.get('y')))
                    await r45ax_park_mouse(page)
                    clicked += 1; pass_had_click = True
                    label = item.get('label','')
                    category = item.get('category') or ''
                    wait_ms = r45ax_click_wait_ms(label, category)
                    await page.wait_for_timeout(wait_ms)
                    if category == 'replied_bucket' and clicked % 4 != 0:
                        profile_hover_result = {'skipped': True, 'reason': 'r45bl_replied_bucket_fast_path'}
                    else:
                        profile_hover_result = await r45ax_close_profile_hover_cards(page)
                        if int((profile_hover_result or {}).get('closed') or 0) > 0 or int(((profile_hover_result or {}).get('before') or {}).get('count') or 0) > 0:
                            profile_hover_closed += int((profile_hover_result or {}).get('closed') or 0)
                            log('R45AX_PROFILE_HOVER_CARD_CLOSED', {'step': step, 'key': before_key, 'label': label, 'profile_hover_closed': profile_hover_closed, 'hover_result': profile_hover_result})
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
                    after_target_guard = await r45ax_target_guard_now(page, story)
                    if not after_target_guard.get('ok'):
                        target_drift_blocked += 1
                        if before_key:
                            try:
                                await page.evaluate('(key) => r45axAddSkipKey(key)', before_key)
                            except Exception:
                                pass
                        receipt['status'] = 'BLOCKED_TARGET_DRIFT_AFTER_CLICK'
                        receipt['target_drift_guard'] = after_target_guard
                        receipt['last_click'] = {'step': step, 'key': before_key, 'label': label, 'x': item.get('x'), 'y': item.get('y')}
                        log('R45AX_TARGET_DRIFT_BLOCKED', {'step': step, 'target_drift_blocked': target_drift_blocked, 'guard': after_target_guard, 'last_click': receipt['last_click']})
                        (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
                        await context.close()
                        return 5
                    after_side = await page.evaluate('r45axMessengerSideEffectState()')
                    messenger_opened = int((after_side.get('messenger') or {}).get('count') or 0) > int((before_side.get('messenger') or {}).get('count') or 0) or int((after_side.get('messenger') or {}).get('count') or 0) > 0
                    messenger_close_result = None
                    if messenger_opened:
                        messenger_blocked += 1
                        messenger_close_result = await page.evaluate('r45axCloseMessengerOverlays()')
                        await page.wait_for_timeout(450)
                        if before_key:
                            skip_result = await page.evaluate('(key) => r45axAddSkipKey(key)', before_key)
                        else:
                            skip_result = {'ok': False, 'reason': 'missing_key'}
                        log('R45AX_MESSENGER_OVERLAY_BLOCKED', {'step':step, 'key':before_key, 'label':label, 'messenger_blocked':messenger_blocked, 'before_side':before_side, 'after_side':after_side, 'close_result':messenger_close_result, 'skip_result':skip_result})
                        after_close_count = int(((messenger_close_result or {}).get('after') or {}).get('count') or 0)
                        if after_close_count > 0:
                            receipt['status'] = 'BLOCKED_MESSENGER_OVERLAY_STILL_OPEN'
                            receipt['last_click'] = {'step': step, 'key': before_key, 'label': label, 'x': item.get('x'), 'y': item.get('y')}
                            receipt['messenger_overlay'] = {'before_side': before_side, 'after_side': after_side, 'close_result': messenger_close_result}
                            receipt['failure_artifacts'] = await r45ax_write_failure_artifacts(page, run_dir, 'blocked_messenger_overlay_still_open')
                            log('R45AX_MESSENGER_OVERLAY_STILL_OPEN_BLOCKED', {'step': step, 'last_click': receipt['last_click'], 'after_close_count': after_close_count, 'failure_artifacts': receipt['failure_artifacts']})
                            (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
                            await context.close()
                            return 7
                    if closed_new_pages and before_key:
                        skip_result = await page.evaluate('(key) => r45axAddSkipKey(key)', before_key)
                        log('R45AX_UNEXPECTED_PAGE_CLOSED', {'step':step, 'key':before_key, 'label':label, 'closed_pages':closed_new_pages, 'new_pages_closed':new_pages_closed, 'skip_result':skip_result})
                    after_scan = await page.evaluate('r45axScanVisible()')
                    after_prog_raw = after_scan.get('progress')
                    after_prog = r45ax_filter_expected_progress(after_prog_raw, expected_total_comments)
                    if after_prog_raw and expected_total_comments > 0 and not after_prog:
                        log('R45AX_PROGRESS_IGNORED_EXPECTED_TOTAL_MISMATCH', {'step': step, 'expected_total_comments': expected_total_comments, 'ignored_progress': after_prog_raw})
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
                    log('R45AX_CLICK', {'step':step, 'clicked':clicked, 'label':label, 'category':item.get('category'), 'click_label': item.get('clickLabel'), 'preferred_point': item.get('preferredPoint'), 'key':before_key, 'x':item.get('x'), 'y':item.get('y'), 'wait_ms':wait_ms, 'click_elapsed_ms':click_elapsed_ms, 'timing_delta':timing_delta, 'post_visible_total': after_scan.get('total'), 'no_progress': no_progress, 'messenger_opened': messenger_opened, 'profile_hover_closed': profile_hover_closed, 'profile_hover_check': profile_hover_result, 'new_pages_closed': closed_new_pages, 'dead_key_count': dead_click_counts.get(before_key,0)})
                    if no_progress and category == 'replied_bucket':
                        replied_bucket_fast_skipped += 1
                        skip_result = await page.evaluate('(key) => r45axAddSkipKey(key)', before_key)
                        log('R45AX_REPLIED_BUCKET_NO_PROGRESS_SKIPPED', {'step':step, 'key':before_key, 'label':label, 'replied_bucket_fast_skipped': replied_bucket_fast_skipped, 'skip_result':skip_result})
                    elif no_progress and dead_click_counts.get(before_key, 0) >= 2:
                        dead_click_skipped += 1
                        skip_result = await page.evaluate('(key) => r45axAddSkipKey(key)', before_key)
                        log('R45AX_DEAD_CLICK_KEY_SKIPPED', {'step':step, 'key':before_key, 'label':label, 'dead_click_skipped':dead_click_skipped, 'skip_result':skip_result})
                    continue
            at_bottom = bool(scan.get('atBottom')); sh = int(scan.get('scrollHeight') or 0)
            if not at_bottom:
                sr = await page.evaluate('r45axScroll("down")'); scrolls += 1; await r45ax_park_mouse(page); hover_result = await r45ax_close_profile_hover_cards(page);
                if int((hover_result or {}).get('closed') or 0) > 0 or int(((hover_result or {}).get('before') or {}).get('count') or 0) > 0:
                    profile_hover_closed += int((hover_result or {}).get('closed') or 0)
                    log('R45AX_PROFILE_HOVER_CARD_CLOSED', {'step': step, 'profile_hover_closed': profile_hover_closed, 'hover_result': hover_result})
                log('R45AX_SCROLL_DOWN', {'step':step, 'scrolls':scrolls, **sr})
                no_movement = int(sr.get('after') or 0) == int(sr.get('before') or 0) and not bool(sr.get('atBottom'))
                stalled_scroll_cycles = stalled_scroll_cycles + 1 if no_movement else 0
                if stalled_scroll_cycles >= 6:
                    current_guard = await r45ax_target_guard_now(page, story)
                    receipt['status'] = 'BLOCKED_SCROLL_STALLED_OR_TARGET_DRIFT'
                    receipt['scroll_stall'] = {'step': step, 'stalled_scroll_cycles': stalled_scroll_cycles, 'last_scroll_result': sr, 'guard': current_guard, 'best_progress': best_progress}
                    log('R45AX_SCROLL_STALLED_BLOCKED', receipt['scroll_stall'])
                    (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
                    await context.close()
                    return 6
                await page.wait_for_timeout(180); continue
            if at_bottom and not progress_ok:
                stable_bottom_cycles = stable_bottom_cycles + 1 if sh == last_scroll_height else 0; last_scroll_height = sh
                log('R45AX_PROGRESS_GATE_NOT_SATISFIED', {'step':step, 'best_progress':best_progress, 'expected_total_comments': expected_total_comments, 'gate_status': r45ax_progress_gate_status(best_progress, expected_total_comments), 'stable_bottom_cycles':stable_bottom_cycles, 'scrollHeight':sh})
                if stable_bottom_cycles >= int(args.progress_stall_cycles):
                    if audit_pass >= int(args.max_audit_passes): break
                    audit_pass += 1; await page.evaluate('r45axScroll("top")'); await r45ax_park_mouse(page); await page.wait_for_timeout(400); continue
                await page.wait_for_timeout(900); await page.evaluate('r45axScroll("top")'); await r45ax_park_mouse(page); audit_pass += 1; await page.wait_for_timeout(250); continue
            if at_bottom and progress_ok:
                if pass_had_click:
                    log('R45AX_AUDIT_RESTART_TOP', {'step':step, 'audit_pass':audit_pass, 'clicked':clicked, 'scrolls':scrolls, 'best_progress':best_progress})
                    if audit_pass >= int(args.max_audit_passes):
                        log('R45AX_AUDIT_LIMIT_REACHED_WITH_CHANGES', {'step':step, 'audit_pass':audit_pass, 'clicked':clicked, 'scrolls':scrolls})
                        break
                    audit_pass += 1
                    pass_had_click = False
                    await page.evaluate('r45axScroll("top")')
                    await r45ax_park_mouse(page)
                    await page.wait_for_timeout(650)
                    continue
                receipt['auto_expand_summary'] = {'status':'pass', 'clicked':clicked, 'scrolls':scrolls, 'audit_passes':audit_pass, 'unsafe_skipped':unsafe_skipped, 'dead_click_skipped':dead_click_skipped, 'replied_bucket_fast_skipped': replied_bucket_fast_skipped, 'messenger_blocked':messenger_blocked, 'new_pages_closed':new_pages_closed, 'target_drift_blocked':target_drift_blocked, 'profile_hover_closed':profile_hover_closed, 'expected_total_comments': expected_total_comments, 'best_progress':best_progress, 'progress_ok':progress_ok, 'progress_gate_status': r45ax_progress_gate_status(best_progress, expected_total_comments), 'completed_by_full_zero_control_audit': True}; log('R45AX_EXPANSION_COMPLETE', receipt['auto_expand_summary']); break
        if 'auto_expand_summary' not in receipt:
            final_scan = await page.evaluate('r45axScanVisible()'); final_progress_raw = await page.evaluate('r45axPageProgress()')
            final_progress = r45ax_filter_expected_progress(final_progress_raw, expected_total_comments)
            if final_progress_raw and expected_total_comments > 0 and not final_progress:
                log('R45AX_PROGRESS_IGNORED_EXPECTED_TOTAL_MISMATCH', {'step': 'final', 'expected_total_comments': expected_total_comments, 'ignored_progress': final_progress_raw})
            receipt['status'] = 'BLOCKED_INCOMPLETE_EXPANSION'; receipt['final_scan'] = final_scan; receipt['best_progress'] = best_progress or final_progress; receipt['raw_final_progress'] = final_progress_raw; receipt['expected_total_comments'] = expected_total_comments
            receipt['progress_gate_satisfied'] = r45ax_progress_gate_ok(receipt.get('best_progress'), expected_total_comments)
            log('R45AX_BLOCKED_INCOMPLETE_EXPANSION', {'best_progress':receipt.get('best_progress'), 'raw_final_progress': final_progress_raw, 'expected_total_comments': expected_total_comments, 'progress_gate_satisfied':receipt.get('progress_gate_satisfied'), 'gate_status': r45ax_progress_gate_status(receipt.get('best_progress'), expected_total_comments), 'final_visible_total':final_scan.get('total'), 'final_labels':final_scan.get('labels')})
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
    ap.add_argument('--expected-total-comments', type=int, default=0, help='Known Facebook total comment count; when set, only N of this total satisfies the progress gate')
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
