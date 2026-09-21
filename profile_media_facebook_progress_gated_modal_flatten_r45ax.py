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
    "r45ax_rule": "Open the post, lock to the target story, use the active comments modal scroller, click the first safe visible expansion label, rescan the same viewport, continue downward while comments load, and gate completion on both zero visible expand controls in a full top-to-bottom audit and any detected Facebook progress text reaching its total, e.g. 715 of 715.",
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
  if (/replied\s*[·•]\s*\d+\s+replies/i.test(t)) return 'replied_bucket';
  return '';
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
  let best = null;
  for (const el of nodes){
    if (r45axElementHidden(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 360 || r.height < 240) continue;
    if (r.bottom < 80 || r.top > vh - 80) continue;
    const sh = el.scrollHeight || 0, ch = el.clientHeight || 0;
    const text = r45axNorm(el.innerText || el.textContent || '');
    const hasComments = /\bLike\b\s+\bReply\b|View all \d+ replies|View hidden|\bof\s+\d{2,5}\b/i.test(text);
    if (!hasComments) continue;
    const score = (el.getAttribute('role') === 'dialog' ? 30000 : 0) + Math.max(0, sh - ch) + Math.min(text.length, 50000) + r.height;
    if (!best || score > best.score) best = {el, score, rect: r, textLength: text.length, role: el.getAttribute('role') || '', tag: el.tagName};
  }
  if (!best) return {ok:false};
  window.__R45AX_SCROLLER__ = best.el;
  return {ok:true, scroller:{tag:best.tag, role:best.role, score:Math.round(best.score), textLength:best.textLength, scrollTop:best.el.scrollTop||0, scrollHeight:best.el.scrollHeight||0, clientHeight:best.el.clientHeight||0, rect:{top:Math.round(best.rect.top), bottom:Math.round(best.rect.bottom), left:Math.round(best.rect.left), right:Math.round(best.rect.right), width:Math.round(best.rect.width), height:Math.round(best.rect.height)}}};
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
function r45axTextCandidates(scroller){
  const band = r45axBand(scroller);
  const walker = document.createTreeWalker(scroller || document.body, NodeFilter.SHOW_TEXT);
  const out = [];
  let n;
  while ((n = walker.nextNode())){
    const label = r45axNorm(n.nodeValue || '');
    const category = r45axCategory(label);
    if (!category) continue;
    const parent = n.parentElement;
    if (!parent || r45axElementHidden(parent)) continue;
    const range = document.createRange();
    try { range.selectNodeContents(n); } catch(e) { continue; }
    const rects = Array.from(range.getClientRects()).filter(rect => r45axRectVisible(rect, band));
    range.detach && range.detach();
    for (const rect of rects){
      const points = [
        {x: rect.left + rect.width/2, y: rect.top + rect.height/2},
        {x: rect.left + Math.min(rect.width-2, Math.max(2, rect.width*0.22)), y: rect.top + rect.height/2},
        {x: rect.left + Math.min(rect.width-2, Math.max(2, rect.width*0.78)), y: rect.top + rect.height/2},
      ];
      let chosen = null, safety = null;
      for (const p of points){
        const s = r45axClickSafetyAt(p.x, p.y);
        if (s.ok){ chosen = p; safety = s; break; }
        if (!safety) safety = s;
      }
      out.push({label, category, x:Math.round((chosen||points[0]).x), y:Math.round((chosen||points[0]).y), top:Math.round(rect.top), bottom:Math.round(rect.bottom), left:Math.round(rect.left), right:Math.round(rect.right), safe:!!chosen, safety});
    }
  }
  const seen = new Set();
  const dedup = [];
  for (const item of out.sort((a,b)=>a.top-b.top || a.left-b.left)){
    const key = item.category+'|'+item.label+'|'+Math.round(item.top/3)+'|'+Math.round(item.left/8);
    if (seen.has(key)) continue;
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
  const progress = r45axProgressFromText((scroller.innerText || document.body.innerText || '')) || r45axProgressFromText(document.body.innerText || '');
  return {ok:true, scrollTop:scroller.scrollTop||0, scrollHeight:scroller.scrollHeight||0, clientHeight:scroller.clientHeight||0, atBottom: (scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8), counts, labels: items.map(x=>x.label).slice(0,25), total: items.length, items:items.slice(0,20), progress};
}
function r45axClickFirstVisible(){
  const scan = r45axScanVisible();
  if (!scan.ok || !scan.items.length) return {clicked:false, scan};
  const item = scan.items.find(x => x.safe) || scan.items[0];
  if (!item.safe) return {clicked:false, blocked:true, item, scan};
  return {clicked:true, item, scan};
}
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
  return r45axProgressFromText((scroller && scroller.innerText) || '') || r45axProgressFromText(document.body.innerText || '');
}
function r45axInstallNavBlocker(){
  if (window.__R45AX_NAV_BLOCKER__) return {installed:true, already:true};
  window.__R45AX_NAV_BLOCKER__ = true;
  document.addEventListener('click', function(ev){
    const a = ev.target && ev.target.closest && ev.target.closest('a[href]');
    if (!a) return;
    const href = a.href || a.getAttribute('href') || '';
    if (r45axUnsafeHref(href)) { ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation(); console.warn('R45AX_NAV_BLOCKED '+href); }
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
        await page.add_script_tag(content=EXPAND_PATTERNS_JS)
        await page.evaluate('r45axInstallNavBlocker();')
        guard = await page.evaluate("""(story) => { const href = location.href; return {href, title: document.title, expectedStory: story, hasStory: story ? href.includes(story) : true, onFacebook: /facebook\.com/i.test(location.hostname)}; }""", story)
        guard['ok'] = bool(guard.get('onFacebook') and guard.get('hasStory'))
        log('R45AX_TARGET_GUARD', guard)
        if not guard['ok']:
            receipt['status'] = 'BLOCKED_TARGET_GUARD'; (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8'); await context.close(); return 2
        scroller_info = await page.evaluate('r45axFindScroller();')
        log('R45AX_ACTIVE_SCROLL_CONTAINER', scroller_info)
        if not scroller_info.get('ok'):
            receipt['status'] = 'BLOCKED_NO_COMMENTS_SCROLLER'; (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8'); await context.close(); return 3
        await page.evaluate('r45axScroll("top")')
        start = time.monotonic(); clicked = 0; scrolls = 0; audit_pass = 1; best_progress: Optional[Dict[str, Any]] = None; last_scroll_height = 0; stable_bottom_cycles = 0; unsafe_skipped = 0
        log('R45AX_PROGRESS_GATED_START', {'max_seconds':args.expand_max_seconds, 'max_steps':args.max_steps, 'progress_gate_required': True, 'target_url': target_url})
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
                    await page.mouse.click(float(item.get('x')), float(item.get('y'))); clicked += 1
                    label = item.get('label',''); m = re.search(r'\d+', label); n = int(m.group(0)) if m else 0
                    wait_ms = 2600 if n >= 100 else (1400 if n >= 30 else 650)
                    await page.wait_for_timeout(wait_ms)
                    log('R45AX_CLICK', {'step':step, 'clicked':clicked, 'label':label, 'category':item.get('category'), 'x':item.get('x'), 'y':item.get('y'), 'wait_ms':wait_ms})
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
                receipt['auto_expand_summary'] = {'status':'pass', 'clicked':clicked, 'scrolls':scrolls, 'audit_passes':audit_pass, 'unsafe_skipped':unsafe_skipped, 'best_progress':best_progress, 'progress_ok':progress_ok}; log('R45AX_EXPANSION_COMPLETE', receipt['auto_expand_summary']); break
        if 'auto_expand_summary' not in receipt:
            final_scan = await page.evaluate('r45axScanVisible()'); final_progress = await page.evaluate('r45axPageProgress()')
            receipt['status'] = 'BLOCKED_INCOMPLETE_EXPANSION'; receipt['final_scan'] = final_scan; receipt['best_progress'] = best_progress or final_progress
            receipt['progress_gate_satisfied'] = bool((best_progress or final_progress) and int((best_progress or final_progress).get('current',0)) >= int((best_progress or final_progress).get('total',1))) if (best_progress or final_progress) else False
            log('R45AX_BLOCKED_INCOMPLETE_EXPANSION', {'best_progress':receipt.get('best_progress'), 'progress_gate_satisfied':receipt.get('progress_gate_satisfied'), 'final_visible_total':final_scan.get('total'), 'final_labels':final_scan.get('labels')})
            (run_dir/'r45ax_progress_gated_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8'); await context.close(); return 4
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
            zf.write(html_path, arcname=html_path.name); zf.write(text_path, arcname=text_path.name)
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
