from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import urllib.request
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from source_msn_comments_profile_export import (
    MsnCommentsProfileExport,
    MsnCommentsProfileExportFiles,
    build_msn_comments_profile_export,
    build_msn_comments_profile_export_from_paths,
    render_msn_comments_html,
    write_msn_comments_profile_exports,
)
from source_msn_live_viewable_capture_cli import run_live_viewable_capture


MSN_SOURCE_ADAPTER_SCHEMA_VERSION = "msn_source_adapter_v1"
MSN_PRODUCTION_READY = "MSN_SOURCE_ADAPTER_PRODUCTION_READY"
MSN_CLOSEOUT_REVIEW_REQUIRED = "MSN_SOURCE_ADAPTER_REVIEW_REQUIRED"
MSN_MEDIA_SATISFIED = "MSN_MEDIA_SATISFIED"
MSN_MEDIA_MISSING = "MSN_MEDIA_MISSING"
MSN_WARC_REPLAY_NOT_TESTED = "NOT_TESTED"
MSN_WACZ_REPLAY_NOT_TESTED = "NOT_TESTED"
MSN_COMMENTS_CAPTURE_MODE_V15 = "internal_scroller_visual_clip_stitch"
MSN_ARTICLE_SCREENSHOT_METHOD_V6 = "android_article_print_layout_gate_v6"
MSN_ACCEPTED_V15_DECISION = "YORK_ANDROID_COMMENTS_V15_PASS_INTERNAL_STITCH_CONSENT_VISUALLY_CLEAR"
LIVE_VIEWABLE_CAPTURE_COMPLETED = "LIVE_VIEWABLE_CAPTURE_COMPLETED"
NON_FATAL_CLOSEOUT_WARNINGS = {
    "warc_generated_but_replay_not_tested",
    "wacz_generated_but_replay_not_tested",
}

PRIMARY_SOURCE_LOCATED = "PRIMARY_SOURCE_LOCATED"
PRIMARY_SOURCE_NOT_LOCATED = "PRIMARY_SOURCE_NOT_LOCATED"
PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED = "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED"
PRIMARY_SOURCE_DISPUTED = "PRIMARY_SOURCE_DISPUTED"
SECONDARY_FRAMING_ONLY = "SECONDARY_FRAMING_ONLY"
TERTIARY_PROPAGATED_CLAIM = "TERTIARY_PROPAGATED_CLAIM"
MANUAL_SOURCE_NOTE = "MANUAL_SOURCE_NOTE"

PRIMARY_ORIGINAL_AUTHORED_SOURCE = "PRIMARY_ORIGINAL_AUTHORED_SOURCE"
SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE = "SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE"
SECONDARY_AUTHORITY_SOURCE = "SECONDARY_AUTHORITY_SOURCE"
TERTIARY_PROPAGATED_SOURCE = "TERTIARY_PROPAGATED_SOURCE"

CURRENTNESS_STATUSES = ("CURRENT", "HISTORICAL", "UNKNOWN", "REPOSTED", "UNDATED")
CLAIM_SOURCE_ROLE_FIELDS = (
    "claim_text",
    "claim_type",
    "claim_source_role",
    "source_role_scope",
    "source_role_limitation",
    "authored_or_posted_at",
    "captured_at_utc",
    "event_time_or_claim_time",
    "temporal_gap_note",
    "currentness_status",
    "primary_source_status",
    "source_chain_gap",
    "closed_loop_reporting_flag",
    "first_uploader_known",
    "first_uploader_url",
    "first_seen_by_user_utc",
    "media_acquired_at_utc",
    "file_obtained_delay_note",
    "publisher_framing_summary",
    "removed_or_missing_context_note",
    "identity_claim_basis",
    "appearance_claim_basis",
    "forensic_claim_basis",
    "family_or_authority_claim_basis",
    "open_source_media_available",
    "corroborating_sources",
    "contradicting_sources",
    "verification_notes",
)
MEDIA_SOURCE_CHAIN_FIELDS = (
    "media_observed_on_url",
    "publisher_page_url",
    "publisher_name",
    "publisher_headline_or_caption",
    "publisher_framing_summary",
    "visible_source_credit",
    "claimed_original_source",
    "original_source_url",
    "original_author_or_uploader",
    "primary_source_status",
    "source_role",
    "source_chain_gap",
    "social_source_url",
    "wire_agency_source_credit",
    "caption_context_around_media",
    "first_seen_by_user_utc",
    "capture_time_utc",
    "media_hash",
    "checksum",
    "perceptual_hash_future",
    "same_media_seen_on_other_urls",
    "repost_platform",
    "repost_uploader_account",
    "repost_timestamp",
    "source_author_correction_url",
    "source_author_correction_text_or_path",
    "notes_on_context_dispute",
    "confidence",
    "verification_notes",
)

YORK_TARGET_ID = "AA29207o"
YORK_ARTICLE_URL = (
    "https://www.msn.com"
    "/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"
    "?ocid=edgemobile&PC=EMMX01"
)
YORK_COMMENTS_URL = YORK_ARTICLE_URL + "#comments"
YORK_INDEPENDENT_URL = "https://www.independent.co.uk/news/uk/home-news/york-mosque-arrest-north-yorkshire-police-b3024303.html"
YORK_POLICE_URL = "https://www.northyorkshire.police.uk/news/north-yorkshire/news/news/2026/07-july/man-arrested-following-incident-at-york-mosque-and-islamic-centre/"
YORK_POLICE_ARCHIVE_URL = "https://web.archive.org/web/20260730140502/https://www.northyorkshire.police.uk/news/north-yorkshire/news/news/2026/07-july/man-arrested-following-incident-at-york-mosque-and-islamic-centre/"
YORK_EXPECTED_COMMENT_COUNT = 25
YORK_REQUIRED_IMAGE_URL = "https://img-s-msn-com.akamaized.net/tenant/amp/entityid/AA292lx3.img?w=534&h=356&m=6"
YORK_REQUIRED_IMAGE_IDENTITY = "AA292lx3.img"
YORK_ARTICLE_BULLET_CLAIMS = (
    "A 44-year-old man has been arrested after a firearm was discharged outside York Mosque and Islamic Centre on Bull Lane at 2.19am on Thursday.",
    "No one was injured in the incident, and the firearm is believed to have been an air weapon.",
    "North Yorkshire Police confirmed the arrested man is a white UK national from York, who was traced after leaving the scene in a silver vehicle.",
    "Police inquiries are ongoing to establish the motivation behind the incident, and the man remains in custody for questioning.",
    "Authorities are providing reassurance to the Muslim community, with increased patrols around the mosque and officers meeting with the imam.",
)

AA27_TARGET_ID = "AA27OIhw"
AA27_COMMENTS_URL = "https://www.msn.com/en-gb/news/uknews/twelve-arrested-over-terror-threat-at-islamic-festival/ar-AA27OIhw?#comments"
AA27_EXPECTED_MANUAL_COMMENT_COUNT = 87
AA27_EXPECTED_V35_ITEMS = 88

ACCEPTED_ARTICLE_SCREENSHOT_NAME = "android_article_MAIN_SINGLE_reference_style.png"
ACCEPTED_COMMENTS_SCREENSHOT_NAME = "android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png"
DEBUG_ONLY_NAMES = (
    "diagnostic_before_internal_loading.png",
    "comments_stitch_segments",
    "scroller_diagnostic.json",
    "dom_diagnostic.json",
)

MSN_V15_SHADOW_LOADER_JS = r"""
async ({stableTarget, maxPasses}) => {
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const result = {
    capture_mode: "internal_scroller_visual_clip_stitch",
    host_found: false,
    shadow_open: false,
    passes: 0,
    stable_passes: 0,
    total_reply_expand_clicks: 0,
    total_text_expand_clicks: 0,
    total_load_clicks: 0,
    page_scroll_start: Math.round(window.scrollY || 0),
    page_scroll_end: null,
    page_scroll_changed: false,
    selected_scroller_index: -1,
    scroller_candidates: [],
    body_or_shadow_len: 0,
    comment_word_count: 0,
    reply_word_count: 0,
    see_more_reply_count: null,
    see_more_text_count: null,
    load_more_comment_count: null,
    error: null
  };
  const host = document.querySelector("social-comment-wc");
  result.host_found = !!host;
  result.shadow_open = !!(host && host.shadowRoot);
  if (!host || !host.shadowRoot) {
    result.error = "social-comment-wc shadow root not found";
    return result;
  }
  const lockY = Math.round(window.scrollY || 0);
  document.documentElement.style.setProperty("overflow", "hidden", "important");
  document.body.style.setProperty("overflow", "hidden", "important");
  document.documentElement.style.setProperty("overscroll-behavior", "none", "important");
  document.body.style.setProperty("overscroll-behavior", "none", "important");
  window.scrollTo(0, lockY);
  function roots() {
    const queue = [host.shadowRoot];
    for (let i = 0; i < queue.length; i += 1) {
      for (const el of queue[i].querySelectorAll("*")) {
        if (el.shadowRoot && !queue.includes(el.shadowRoot)) queue.push(el.shadowRoot);
      }
    }
    return queue;
  }
  function elements() { return roots().flatMap(root => Array.from(root.querySelectorAll("*"))); }
  function textOf(el) {
    return ((el.innerText || el.textContent || "") + " " + (el.getAttribute?.("aria-label") || "")).replace(/\s+/g, " ").trim();
  }
  function scrollers() {
    return elements().filter(el => {
      const style = getComputedStyle(el);
      const delta = el.scrollHeight - el.clientHeight;
      return delta > 8 && /(auto|scroll|overlay)/i.test(style.overflowY || "");
    }).map((el, index) => {
      const rect = el.getBoundingClientRect();
      const text = textOf(el);
      const delta = el.scrollHeight - el.clientHeight;
      const score = delta + Math.min(text.length, 24000) + (/comment/i.test(text) ? 3000 : 0) + (/reply/i.test(text) ? 1500 : 0);
      return {el, index, score, delta, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight, scrollTop: el.scrollTop, tag: el.tagName, cls: String(el.className || ""), rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}, textSample: text.slice(0, 280)};
    }).sort((a, b) => b.score - a.score);
  }
  function clickExpands() {
    let replies = 0, texts = 0, loads = 0;
    for (const el of elements()) {
      if (!el.matches?.("button,[role='button'],a") || el.disabled) continue;
      const t = textOf(el);
      if (!t) continue;
      if (/\b(show|view|see|load)\b.*\b(more\s+)?repl(?:y|ies)\b/i.test(t) || /^\d+\s+more\s+repl(?:y|ies)$/i.test(t) || /^see\s+\d+\s+more\s+repl(?:y|ies)$/i.test(t)) {
        try { el.click(); replies += 1; } catch (_) {}
      } else if (/\b(show|see|read)\s+more\b/i.test(t) && !/sponsored|ad|privacy|sign in/i.test(t)) {
        try { el.click(); texts += 1; } catch (_) {}
      } else if (/\b(load|show|view|see)\b.*\b(more\s+)?comments\b/i.test(t)) {
        try { el.click(); loads += 1; } catch (_) {}
      }
    }
    return {replies, texts, loads};
  }
  let previousSignature = "";
  let stable = 0;
  for (let pass = 1; pass <= maxPasses && stable < stableTarget; pass += 1) {
    const clicks = clickExpands();
    result.total_reply_expand_clicks += clicks.replies;
    result.total_text_expand_clicks += clicks.texts;
    result.total_load_clicks += clicks.loads;
    const candidates = scrollers();
    if (!candidates.length) { await wait(600); continue; }
    for (const candidate of candidates.slice(0, 8)) {
      try {
        candidate.el.scrollTop = Math.max(0, candidate.el.scrollHeight - candidate.el.clientHeight - 4);
        candidate.el.dispatchEvent(new Event("scroll", {bubbles: true, composed: true}));
        candidate.el.dispatchEvent(new WheelEvent("wheel", {deltaY: 1200, bubbles: true, composed: true}));
        await wait(100);
        candidate.el.scrollTop = candidate.el.scrollHeight;
        candidate.el.dispatchEvent(new Event("scroll", {bubbles: true, composed: true}));
      } catch (_) {}
    }
    window.scrollTo(0, lockY);
    await wait(750);
    const all = elements();
    const leafTextLength = all.reduce((total, el) => el.children.length ? total : total + (el.textContent || "").length, 0);
    const current = scrollers();
    const signature = [all.length, leafTextLength, ...current.slice(0, 8).map(item => `${item.scrollHeight}/${item.clientHeight}/${Math.round(item.el.scrollTop)}`)].join("|");
    stable = signature === previousSignature ? stable + 1 : 0;
    previousSignature = signature;
    result.passes = pass;
    result.stable_passes = stable;
  }
  const all = elements();
  const allText = all.map(textOf).join("\n");
  const lower = allText.toLowerCase();
  result.body_or_shadow_len = allText.length;
  result.comment_word_count = (lower.match(/comment/g) || []).length;
  result.reply_word_count = (lower.match(/reply/g) || []).length;
  result.see_more_reply_count = (allText.match(/see\s+\d+\s+more\s+repl(?:y|ies)|\b(show|view|see|load)\b[^\n]{0,80}\brepl(?:y|ies)\b/ig) || []).length;
  result.see_more_text_count = (allText.match(/\b(show|see|read)\s+more\b/ig) || []).length;
  result.load_more_comment_count = (allText.match(/\b(load|show|view|see)\b[^\n]{0,80}\bcomments\b/ig) || []).length;
  const candidates = scrollers();
  result.scroller_candidates = candidates.slice(0, 20).map((item, rank) => ({rank, score: item.score, delta: item.delta, scrollHeight: item.scrollHeight, clientHeight: item.clientHeight, scrollTop: item.el.scrollTop, tag: item.tag, cls: item.cls, rect: item.rect, textSample: item.textSample}));
  if (candidates.length) {
    window.__MSN_V15_SELECTED_SCROLLER = candidates[0].el;
    result.selected_scroller_index = 0;
    try { candidates[0].el.scrollTop = 0; candidates[0].el.dispatchEvent(new Event("scroll", {bubbles: true, composed: true})); } catch (_) {}
  }
  result.page_scroll_end = Math.round(window.scrollY || 0);
  result.page_scroll_changed = result.page_scroll_end !== result.page_scroll_start;
  return result;
}
"""

MSN_CONSENT_SUPPRESSION_JS = r"""
() => {
  const selected = window.__MSN_V15_SELECTED_SCROLLER || window.__MSN_V12_SELECTED_SCROLLER;
  const protectedNodes = new Set();
  function protect(node) { while (node) { protectedNodes.add(node); node = node.parentElement || node.host; } }
  if (selected) protect(selected);
  const hidden = [];
  function visible(el) {
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    return {r, st, z: parseInt(st.zIndex || "0", 10) || 0};
  }
  function textOf(el) { return (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim().toLowerCase(); }
  function hide(el, reason) {
    if (!el || protectedNodes.has(el)) return;
    el.setAttribute("data-msn-v15-consent-hidden", reason);
    el.style.setProperty("display", "none", "important");
    el.style.setProperty("visibility", "hidden", "important");
    hidden.push({tag: el.tagName, reason});
  }
  const elements = Array.from(document.querySelectorAll("*")).reverse();
  const consentAttrs = /(consent|privacy|cookie|gdpr|cmp|onetrust|ot-sdk|usercentrics|truste|didomi|quantcast)/i;
  const consentButton = /^(i accept|accept|accept all|reject all|reject|manage preferences|manage options|privacy settings|save choices|confirm my choices)$/i;
  for (const el of elements) {
    if (protectedNodes.has(el)) continue;
    const t = textOf(el);
    const attrs = [el.tagName, el.id || "", el.className || "", el.getAttribute?.("src") || "", el.getAttribute?.("title") || "", el.getAttribute?.("aria-label") || ""].join(" ");
    const v = visible(el);
    const fixedish = /fixed|sticky|absolute/.test(v.st.position) || v.z >= 10;
    const largePanel = v.r.width > 160 && v.r.height > 70;
    const bottomBanner = v.r.width >= window.innerWidth * 0.55 && v.r.bottom > window.innerHeight * 0.45;
    const consentText = t.includes("microsoft cares about your privacy") || ((t.includes("privacy") || t.includes("cookies")) && (t.includes("accept") || t.includes("reject") || t.includes("manage")));
    if ((consentButton.test(t) || consentText || consentAttrs.test(attrs)) && (fixedish || bottomBanner || largePanel)) {
      hide(el, "consent_or_privacy_overlay");
    }
  }
  return {hidden_count: hidden.length, hidden};
}
"""

MSN_V6_ARTICLE_ALIGN_JS = r"""
(title) => {
  function textOf(el) { return (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim(); }
  const candidates = Array.from(document.querySelectorAll("h1,h2,[role='heading'],article *,main *"));
  let titleEl = candidates.find(el => textOf(el).toLowerCase().includes(String(title || "").toLowerCase()));
  if (!titleEl) titleEl = document.querySelector("h1,[role='heading']");
  if (!titleEl) return {ok: false, reason: "title element not found"};
  titleEl.scrollIntoView({block: "start", inline: "nearest"});
  window.scrollBy(0, -90);
  const article = titleEl.closest("article") || titleEl.closest("main") || document.querySelector("article,main") || titleEl.parentElement;
  let boundary = null;
  for (const el of Array.from(document.querySelectorAll("section,div,h2,h3"))) {
    const t = textOf(el).toLowerCase();
    if (/sponsored content|more for you|recommended|from around the web/.test(t)) {
      boundary = el;
      break;
    }
  }
  const ar = article ? article.getBoundingClientRect() : titleEl.getBoundingClientRect();
  const br = boundary ? boundary.getBoundingClientRect() : null;
  const viewportW = window.innerWidth || document.documentElement.clientWidth || 412;
  const viewportH = window.innerHeight || document.documentElement.clientHeight || 915;
  const y = Math.max(0, Math.min(titleEl.getBoundingClientRect().top - 16, viewportH - 120));
  const bottom = br && br.top > y + 260 ? Math.min(br.top - 8, viewportH) : Math.min(Math.max(ar.bottom + 120, y + 700), viewportH);
  return {
    ok: true,
    method: "android_article_print_layout_gate_v6",
    titleText: textOf(titleEl).slice(0, 200),
    clip: {x: 0, y, width: viewportW, height: Math.max(260, bottom - y)}
  };
}
"""


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    return value


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_value_for_dict(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return sha256_file(path)


@dataclass(frozen=True)
class MsnUrlParts:
    raw_url: str
    article_url: str
    comments_url: str
    target_id: str
    host: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnMediaReceipt:
    original_url: str
    normalized_identity: str
    local_path: str = ""
    sha256: str = ""
    source_role: str = ""
    media_source_chain: Mapping[str, Any] | None = None
    status: str = MSN_MEDIA_MISSING
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


class MsnV15CaptureError(RuntimeError):
    def __init__(self, message: str, diagnostics: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.diagnostics = dict(diagnostics or {})


@dataclass(frozen=True)
class MsnOfflineArchiveStatus:
    offline_archive_status: str
    rendered_page_html_path: str = ""
    local_viewer_path: str = ""
    warc_gz_path: str = ""
    wacz_path: str = ""
    warc_generated: bool = False
    wacz_generated: bool = False
    warc_replay_tested: bool = False
    wacz_replay_tested: bool = False
    warc_replay_status: str = MSN_WARC_REPLAY_NOT_TESTED
    wacz_replay_status: str = MSN_WACZ_REPLAY_NOT_TESTED
    archive_limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnProductionCaptureOptions:
    target_url: str
    output_dir: str
    expected_comment_count: int = 0
    capture_comments: bool = True
    capture_msn_screenshots: bool = False
    capture_msn_article_screenshot: bool = False
    capture_msn_comments_screenshot: bool = False
    write_warc: bool = True
    write_wacz: bool = True
    write_rendered_html: bool = True
    write_validation_json: bool = True
    write_local_viewer: bool = True
    headed: bool = False
    debug: bool = False
    keep_browser_open: bool = False
    msn_comments_sort: str = "top"

    @property
    def headless(self) -> bool:
        return not self.headed

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnCloseoutResult:
    decision: str
    output_root: str
    article_url: str
    comments_url: str
    target_id: str
    comment_count: int
    expected_comment_count: int
    profile_count: int
    article_screenshot: str = ""
    comments_screenshot: str = ""
    media_required: tuple[Mapping[str, Any], ...] = ()
    media_satisfied: bool = False
    html_export: str = ""
    json_export: str = ""
    md_export: str = ""
    txt_export: str = ""
    profiles_json: str = ""
    profiles_txt: str = ""
    source_role_claims_json: str = ""
    media_source_chain_json: str = ""
    offline_archive: Mapping[str, Any] | None = None
    media_downloaded_classified_count: int = 0
    source_role_fields_included: bool = False
    warnings: tuple[str, ...] = ()
    schema_version: str = MSN_SOURCE_ADAPTER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def final_block(self) -> str:
        warnings = "NONE" if not self.warnings else "; ".join(self.warnings)
        media_required = ", ".join(item.get("normalized_identity", "") for item in self.media_required) or "NONE"
        archive = self.offline_archive or {}
        return "\n".join(
            [
                f"DECISION: {self.decision}",
                f"OUTPUT_ROOT: {self.output_root}",
                f"ARTICLE_URL: {self.article_url}",
                f"COMMENTS_URL: {self.comments_url}",
                f"TARGET_ID: {self.target_id}",
                f"COMMENT_COUNT: {self.comment_count}",
                f"EXPECTED_COMMENT_COUNT: {self.expected_comment_count}",
                f"PROFILE_COUNT: {self.profile_count}",
                f"ARTICLE_SCREENSHOT: {self.article_screenshot}",
                f"COMMENTS_SCREENSHOT: {self.comments_screenshot}",
                f"MEDIA_REQUIRED: {media_required}",
                f"MEDIA_SATISFIED: {self.media_satisfied}",
                f"MEDIA_DOWNLOADED_CLASSIFIED_COUNT: {self.media_downloaded_classified_count}",
                f"OFFLINE_ARCHIVE_STATUS: {archive.get('offline_archive_status', 'NOT_PRESENT')}",
                f"RENDERED_PAGE_HTML: {archive.get('rendered_page_html_path', '')}",
                f"LOCAL_VIEWER: {archive.get('local_viewer_path', '')}",
                f"WARC_GZ: {archive.get('warc_gz_path', '')}",
                f"WACZ: {archive.get('wacz_path', '')}",
                f"WARC_GENERATED: {archive.get('warc_generated', False)}",
                f"WACZ_GENERATED: {archive.get('wacz_generated', False)}",
                f"WARC_REPLAY_TESTED: {archive.get('warc_replay_tested', False)}",
                f"WACZ_REPLAY_TESTED: {archive.get('wacz_replay_tested', False)}",
                f"WARC_REPLAY_STATUS: {archive.get('warc_replay_status', MSN_WARC_REPLAY_NOT_TESTED)}",
                f"WACZ_REPLAY_STATUS: {archive.get('wacz_replay_status', MSN_WACZ_REPLAY_NOT_TESTED)}",
                f"SOURCE_ROLE_FIELDS_INCLUDED: {self.source_role_fields_included}",
                f"HTML_EXPORT: {self.html_export}",
                f"JSON_EXPORT: {self.json_export}",
                f"MD_EXPORT: {self.md_export}",
                f"TXT_EXPORT: {self.txt_export}",
                f"PROFILES_JSON: {self.profiles_json}",
                f"PROFILES_TXT: {self.profiles_txt}",
                f"SOURCE_ROLE_CLAIMS_JSON: {self.source_role_claims_json}",
                f"MEDIA_SOURCE_CHAIN_JSON: {self.media_source_chain_json}",
                f"WARNINGS: {warnings}",
            ]
        )


def build_msn_url_parts(url: str) -> MsnUrlParts:
    raw = str(url or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme.lower() not in ("http", "https") or "msn.com" not in parsed.netloc.lower():
        raise ValueError("MSN source adapter requires an http(s) msn.com URL")
    target_id = ""
    for part in reversed([item for item in parsed.path.split("/") if item]):
        if part.startswith("ar-"):
            target_id = part[3:]
            break
    if not target_id:
        raise ValueError("MSN URL does not contain an ar-* article target id")
    article_url = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))
    comments_url = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, "comments"))
    return MsnUrlParts(raw_url=raw, article_url=article_url, comments_url=comments_url, target_id=target_id, host=parsed.netloc.lower())


def normalize_msn_image_identity(url_or_path: str) -> str:
    text = str(url_or_path or "").strip()
    path = urlsplit(text).path if "://" in text else text
    path = path.split("?", 1)[0].split("#", 1)[0]
    name = Path(path).name
    return name or text.split("?", 1)[0].split("#", 1)[0]


def required_msn_article_media(url: str) -> tuple[MsnMediaReceipt, ...]:
    parts = build_msn_url_parts(url)
    if parts.target_id == YORK_TARGET_ID:
        return (
            MsnMediaReceipt(
                original_url=YORK_REQUIRED_IMAGE_URL,
                normalized_identity=YORK_REQUIRED_IMAGE_IDENTITY,
                source_role=SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE,
                media_source_chain=default_york_image_source_chain(parts.article_url),
            ),
        )
    return ()


def default_msn_comment_claim_source_role(item: Mapping[str, Any]) -> dict[str, Any]:
    text = str(item.get("text") or "")
    return {
        "claim_text": text,
        "claim_type": "comment_authorship",
        "claim_source_role": PRIMARY_ORIGINAL_AUTHORED_SOURCE,
        "source_role_scope": "limited_to_comment_or_reply_text_authored_by_the_commenter_at_capture_time",
        "source_role_limitation": (
            "The commenter's own comment/reply is primary/original authored evidence only for the claim "
            "that this user authored this comment text. It is not automatically primary evidence for "
            "real-world incident claims contained inside the comment."
        ),
        "authored_or_posted_at": str(item.get("date") or item.get("comment_or_post_timestamp") or ""),
        "captured_at_utc": str(item.get("captured_at_utc") or ""),
        "event_time_or_claim_time": "",
        "temporal_gap_note": "",
        "currentness_status": "UNKNOWN",
        "primary_source_status": PRIMARY_SOURCE_LOCATED,
        "source_chain_gap": False,
        "closed_loop_reporting_flag": False,
        "first_uploader_known": False,
        "first_uploader_url": "",
        "first_seen_by_user_utc": "",
        "media_acquired_at_utc": "",
        "file_obtained_delay_note": "",
        "publisher_framing_summary": "",
        "removed_or_missing_context_note": "",
        "identity_claim_basis": "",
        "appearance_claim_basis": "",
        "forensic_claim_basis": "",
        "family_or_authority_claim_basis": "",
        "open_source_media_available": "",
        "corroborating_sources": [],
        "contradicting_sources": [],
        "verification_notes": "MSN adapter default; operator review required for any incident-level claim.",
    }


def default_msn_article_claim_source_role(*, article_url: str, publisher_name: str = "The Independent") -> dict[str, Any]:
    return {
        "claim_text": "",
        "claim_type": "publisher_article_framing",
        "claim_source_role": SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE,
        "source_role_scope": "publisher_or_reporter_framing_observed_on_msn_page",
        "source_role_limitation": (
            "MSN/the republished outlet is an observed platform/publisher source for article framing; it is not "
            "silently promoted to the primary/original source for each factual incident claim."
        ),
        "authored_or_posted_at": "",
        "captured_at_utc": "",
        "event_time_or_claim_time": "",
        "temporal_gap_note": "",
        "currentness_status": "UNKNOWN",
        "primary_source_status": PRIMARY_SOURCE_NOT_LOCATED,
        "source_chain_gap": True,
        "closed_loop_reporting_flag": False,
        "first_uploader_known": False,
        "first_uploader_url": "",
        "first_seen_by_user_utc": "",
        "media_acquired_at_utc": "",
        "file_obtained_delay_note": "",
        "publisher_framing_summary": f"Observed MSN article republished/framed by {publisher_name}.",
        "removed_or_missing_context_note": "",
        "identity_claim_basis": "",
        "appearance_claim_basis": "",
        "forensic_claim_basis": "",
        "family_or_authority_claim_basis": "",
        "open_source_media_available": "",
        "corroborating_sources": [],
        "contradicting_sources": [],
        "verification_notes": f"Publisher page observed at {article_url}; direct original/primary statement is not implied.",
    }


def default_york_image_source_chain(article_url: str = YORK_ARTICLE_URL) -> dict[str, Any]:
    values = {field: "" for field in MEDIA_SOURCE_CHAIN_FIELDS}
    values.update(
        {
            "media_observed_on_url": article_url,
            "publisher_page_url": article_url,
            "publisher_name": "The Independent via MSN",
            "publisher_headline_or_caption": "Arrest made after shot fired outside York mosque",
            "visible_source_credit": "Google Street View",
            "claimed_original_source": "Google Street View",
            "original_source_url": "",
            "original_author_or_uploader": "",
            "primary_source_status": PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED,
            "source_role": SECONDARY_OUTSIDE_PERSPECTIVE_SOURCE,
            "source_chain_gap": True,
            "media_url": YORK_REQUIRED_IMAGE_URL,
            "normalized_identity": YORK_REQUIRED_IMAGE_IDENTITY,
            "confidence": "visible_credit_claimed_not_independently_verified",
            "verification_notes": (
                "The captured MSN/Independent page is the observed publisher page for this image. "
                "The original Google Street View source URL was not captured by the adapter."
            ),
        }
    )
    return values


def _base_claim_source_role_record(
    *,
    claim_text: str,
    claim_type: str,
    claim_source_role: str,
    source_role_scope: str,
    source_role_limitation: str,
    publisher_framing_summary: str,
    primary_source_status: str,
    source_chain_gap: bool,
    source_url: str,
    publisher_page_url: str,
    source_platform: str,
    publisher_name: str,
    capture_method: str,
    captured_at_utc: str = "",
) -> dict[str, Any]:
    values = {field: "" for field in CLAIM_SOURCE_ROLE_FIELDS}
    values.update(
        {
            "claim_text": claim_text,
            "claim_type": claim_type,
            "claim_source_role": claim_source_role,
            "source_role_scope": source_role_scope,
            "source_role_limitation": source_role_limitation,
            "authored_or_posted_at": "",
            "captured_at_utc": captured_at_utc,
            "event_time_or_claim_time": "",
            "temporal_gap_note": "",
            "currentness_status": "HISTORICAL",
            "primary_source_status": primary_source_status,
            "source_chain_gap": source_chain_gap,
            "closed_loop_reporting_flag": False,
            "publisher_framing_summary": publisher_framing_summary,
            "corroborating_sources": [YORK_POLICE_URL, YORK_POLICE_ARCHIVE_URL],
            "contradicting_sources": [],
            "verification_notes": (
                "Project evidence-role mapping preserves the observed source layer separately from primary/original evidence. "
                "People mentioned in the article are not assigned primary/original source status unless their own direct authored/raw source is captured."
            ),
        }
    )
    values.update(
        {
            "source_url": source_url,
            "canonical_url": source_url,
            "publisher_page_url": publisher_page_url,
            "source_platform": source_platform,
            "publisher_name": publisher_name,
            "adapter_name": "msn_source_adapter",
            "access_mode": "operator_approved_or_local_reference",
            "capture_method": capture_method,
            "capture_purpose": "source_role_claim_mapping",
        }
    )
    return values


def build_york_article_claim_source_role_records(
    *,
    captured_at_utc: str = "",
    capture_method: str = "msn_source_adapter_mapping",
) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for claim in YORK_ARTICLE_BULLET_CLAIMS:
        records.append(
            _base_claim_source_role_record(
                claim_text=claim,
                claim_type="police_derived_incident_detail",
                claim_source_role=TERTIARY_PROPAGATED_SOURCE,
                source_role_scope="MSN is a repost/republisher of The Independent article.",
                source_role_limitation="MSN is not the primary/original source for police-derived incident claims.",
                publisher_framing_summary="MSN / Microsoft Start reposts The Independent article.",
                primary_source_status=PRIMARY_SOURCE_NOT_LOCATED,
                source_chain_gap=True,
                source_url=YORK_ARTICLE_URL,
                publisher_page_url=YORK_ARTICLE_URL,
                source_platform="MSN",
                publisher_name="MSN / Microsoft Start",
                capture_method=capture_method,
                captured_at_utc=captured_at_utc,
            )
        )
        records.append(
            _base_claim_source_role_record(
                claim_text=claim,
                claim_type="police_derived_incident_detail",
                claim_source_role=TERTIARY_PROPAGATED_SOURCE,
                source_role_scope="The Independent relays/publishes details attributed to North Yorkshire Police.",
                source_role_limitation=(
                    "The Independent may be secondary for its own framing/headline/presentation, but is not primary/original "
                    "for police-derived incident facts unless the direct police source is linked for that claim."
                ),
                publisher_framing_summary="The Independent presents the article framing and relays police-derived incident details.",
                primary_source_status=PRIMARY_SOURCE_NOT_LOCATED,
                source_chain_gap=True,
                source_url=YORK_INDEPENDENT_URL,
                publisher_page_url=YORK_INDEPENDENT_URL,
                source_platform="Independent",
                publisher_name="The Independent",
                capture_method=capture_method,
                captured_at_utc=captured_at_utc,
            )
        )
        records.append(
            _base_claim_source_role_record(
                claim_text=claim,
                claim_type="authority_incident_statement",
                claim_source_role=SECONDARY_AUTHORITY_SOURCE,
                source_role_scope="official police/investigation statement and authority perspective.",
                source_role_limitation=(
                    "This is the closest located authority source for the York incident claims, not primary/original "
                    "eyewitness evidence unless direct raw media, witness statement, or officer observation is captured."
                ),
                publisher_framing_summary="North Yorkshire Police official statement.",
                primary_source_status=PRIMARY_SOURCE_LOCATED,
                source_chain_gap=False,
                source_url=YORK_POLICE_URL,
                publisher_page_url=YORK_POLICE_URL,
                source_platform="North Yorkshire Police",
                publisher_name="North Yorkshire Police",
                capture_method=capture_method,
                captured_at_utc=captured_at_utc,
            )
        )
    return tuple(records)


def write_york_source_role_sidecars(output_dir: str | Path, *, captured_at_utc: str = "") -> dict[str, str]:
    root = Path(output_dir)
    claims_path = root / "source-role-claims.json"
    media_path = root / "media-source-chain.json"
    claims_hash = _write_json(
        claims_path,
        {
            "schema_version": MSN_SOURCE_ADAPTER_SCHEMA_VERSION,
            "source_role_fields": list(CLAIM_SOURCE_ROLE_FIELDS),
            "records": list(build_york_article_claim_source_role_records(captured_at_utc=captured_at_utc)),
        },
    )
    media_hash = _write_json(
        media_path,
        {
            "schema_version": MSN_SOURCE_ADAPTER_SCHEMA_VERSION,
            "media_source_chain_fields": list(MEDIA_SOURCE_CHAIN_FIELDS),
            "records": [default_york_image_source_chain(YORK_ARTICLE_URL)],
        },
    )
    return {
        "source_role_claims_json": str(claims_path),
        "source_role_claims_sha256": claims_hash,
        "media_source_chain_json": str(media_path),
        "media_source_chain_sha256": media_hash,
    }


def download_msn_article_media(
    *,
    article_url: str,
    output_dir: str | Path,
    downloader: Callable[[str], bytes] | None = None,
) -> tuple[MsnMediaReceipt, ...]:
    out = Path(output_dir) / "media"
    receipts: list[MsnMediaReceipt] = []
    for item in required_msn_article_media(article_url):
        destination = out / item.normalized_identity
        try:
            if downloader:
                payload = downloader(item.original_url)
            else:
                request = urllib.request.Request(
                    item.original_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
                        ),
                        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                        "Referer": article_url,
                    },
                )
                payload = urllib.request.urlopen(request, timeout=45).read()
            out.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            receipts.append(
                MsnMediaReceipt(
                    original_url=item.original_url,
                    normalized_identity=item.normalized_identity,
                    local_path=str(destination),
                    sha256=sha256_file(destination),
                    source_role=item.source_role,
                    media_source_chain={
                        **dict(item.media_source_chain or {}),
                        "local_media_path": str(destination),
                        "media_hash": sha256_file(destination),
                        "checksum": sha256_file(destination),
                    },
                    status=MSN_MEDIA_SATISFIED,
                )
            )
        except Exception as exc:
            receipts.append(
                MsnMediaReceipt(
                    original_url=item.original_url,
                    normalized_identity=item.normalized_identity,
                    local_path=str(destination),
                    source_role=item.source_role,
                    media_source_chain=item.media_source_chain,
                    status=MSN_MEDIA_MISSING,
                    error=str(exc),
                )
            )
    return tuple(receipts)


def production_output_names(*, debug: bool = False) -> tuple[str, ...]:
    normal = (
        "comments.json",
        "comments.txt",
        "comments.md",
        "comments.html",
        "profiles.json",
        "profiles.txt",
        f"screenshots/{ACCEPTED_ARTICLE_SCREENSHOT_NAME}",
        f"screenshots/{ACCEPTED_COMMENTS_SCREENSHOT_NAME}",
        "media/AA292lx3.img",
        "msn-closeout-report.json",
        "msn-closeout-report.txt",
    )
    if debug:
        return normal + DEBUG_ONLY_NAMES
    return normal


def _copy_if_present(source: Path, destination: Path) -> str:
    if not source.is_file():
        return ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return str(destination)


def promote_accepted_screenshot_outputs(output_dir: str | Path, *, debug: bool = False) -> dict[str, str]:
    root = Path(output_dir)
    screenshots = root / "screenshots"
    promoted = {
        "article": _copy_if_present(screenshots / "article-top.png", screenshots / ACCEPTED_ARTICLE_SCREENSHOT_NAME),
        "comments": _copy_if_present(
            screenshots / "full-comments-thread.png"
            if (screenshots / "full-comments-thread.png").is_file()
            else screenshots / "comments-region.png",
            screenshots / ACCEPTED_COMMENTS_SCREENSHOT_NAME,
        ),
    }
    if not debug:
        promoted["diagnostics_written"] = "false"
    return promoted


def build_offline_archive_status(output_dir: str | Path) -> MsnOfflineArchiveStatus:
    root = Path(output_dir)
    rendered = root / "rendered-page.html"
    local_viewer = root / "local_viewer" / "local-viewer-index.html"
    if not local_viewer.is_file():
        local_viewer = root / "local_viewer" / "open_local_viewer.cmd"
    warc_gz = root / "rendered-page.warc.gz"
    wacz = root / "archive.viewable-live-capture.wacz"
    limitations: list[str] = []
    if warc_gz.is_file():
        limitations.append("raw_warc_replay_not_tested_by_adapter")
    if wacz.is_file():
        limitations.append("wacz_replay_not_tested_by_adapter")
    if not rendered.is_file() and not warc_gz.is_file() and not wacz.is_file() and not local_viewer.is_file():
        return MsnOfflineArchiveStatus(offline_archive_status="NOT_PRESENT")
    return MsnOfflineArchiveStatus(
        offline_archive_status="GENERATED_REPLAY_NOT_TESTED",
        rendered_page_html_path=str(rendered) if rendered.is_file() else "",
        local_viewer_path=str(local_viewer) if local_viewer.is_file() else "",
        warc_gz_path=str(warc_gz) if warc_gz.is_file() else "",
        wacz_path=str(wacz) if wacz.is_file() else "",
        warc_generated=warc_gz.is_file(),
        wacz_generated=wacz.is_file(),
        warc_replay_tested=False,
        wacz_replay_tested=False,
        warc_replay_status=MSN_WARC_REPLAY_NOT_TESTED,
        wacz_replay_status=MSN_WACZ_REPLAY_NOT_TESTED,
        archive_limitations=tuple(limitations),
    )


def build_msn_comments_v15_capture_metadata() -> dict[str, Any]:
    return {
        "decision_reference": MSN_ACCEPTED_V15_DECISION,
        "capture_mode": MSN_COMMENTS_CAPTURE_MODE_V15,
        "normal_output": f"screenshots/{ACCEPTED_COMMENTS_SCREENSHOT_NAME}",
        "host": "social-comment-wc",
        "shadow_dom": "open nested shadow roots traversed recursively",
        "scroller_rule": "internal MSN comments scroller only; document/page/feed scroll locked",
        "reply_expansion": "reply controls and clamped See more text controls expanded before stitching",
        "consent_handling": "Microsoft cookie/privacy/grey overlays suppressed for final capture without hiding the selected scroller",
        "debug_only_outputs": list(DEBUG_ONLY_NAMES),
    }


def build_msn_article_v6_capture_metadata() -> dict[str, Any]:
    return {
        "capture_method": MSN_ARTICLE_SCREENSHOT_METHOD_V6,
        "normal_output": f"screenshots/{ACCEPTED_ARTICLE_SCREENSHOT_NAME}",
        "url_rule": "article URL without #comments",
        "viewport": "Android/mobile viewport and user agent",
        "alignment": "headline/body aligned and clipped before sponsored/recommendation boundary where detected",
    }


def suppress_msn_consent_for_capture(page: Any) -> Mapping[str, Any]:
    return page.evaluate(MSN_CONSENT_SUPPRESSION_JS)


def open_msn_comments_overlay(page: Any, comments_url: str, *, target_id: str = YORK_TARGET_ID) -> Mapping[str, Any]:
    diagnostics: dict[str, Any] = {
        "requested_comments_url": comments_url,
        "page_url_after_open": "",
        "comments_url_contains_target_id": False,
        "overlay_opened": False,
        "social_comment_wc_found": False,
        "shadow_root_found": False,
    }
    page.goto(comments_url, wait_until="domcontentloaded", timeout=70000)
    page.wait_for_timeout(5000)
    try:
        suppress_msn_consent_for_capture(page)
    except Exception:
        pass
    if target_id.lower() not in str(getattr(page, "url", "")).lower():
        page.goto(comments_url, wait_until="domcontentloaded", timeout=70000)
        page.wait_for_timeout(3000)
    try:
        page.evaluate("location.hash = '#comments'")
    except Exception:
        pass
    page.wait_for_timeout(3000)
    for _ in range(8):
        try:
            clicked = page.evaluate(
                r"""
                () => {
                  let clicked = 0;
                  for (const el of Array.from(document.querySelectorAll("button,a,[role=button]"))) {
                    const text = ((el.innerText || el.textContent || "") + " " + (el.getAttribute("aria-label") || "")).replace(/\s+/g, " ").trim().toLowerCase();
                    const href = el.getAttribute("href") || "";
                    if (href && !href.includes("#comments")) continue;
                    if (/\b(comment|comments)\b/.test(text) || text === "25" || text.includes("25 comments")) {
                      try { el.click(); clicked += 1; } catch (_) {}
                    }
                  }
                  return clicked;
                }
                """
            )
            diagnostics["comments_button_clicks"] = int(diagnostics.get("comments_button_clicks") or 0) + int(clicked or 0)
        except Exception as exc:
            diagnostics["comments_button_click_error"] = repr(exc)
        page.wait_for_timeout(1800)
        try:
            found = bool(page.evaluate("() => !!document.querySelector('social-comment-wc')"))
            diagnostics["social_comment_wc_found"] = found
            diagnostics["shadow_root_found"] = bool(page.evaluate("() => { const h=document.querySelector('social-comment-wc'); return !!(h && h.shadowRoot); }"))
            if found:
                diagnostics["overlay_opened"] = True
                break
        except Exception as exc:
            diagnostics["comments_overlay_probe_error"] = repr(exc)
    diagnostics["page_url_after_open"] = str(getattr(page, "url", ""))
    diagnostics["comments_url_contains_target_id"] = target_id.lower() in diagnostics["page_url_after_open"].lower()
    return diagnostics


def expand_msn_comment_shadow_roots(page: Any, *, stable_target: int = 10, max_passes: int = 260) -> Mapping[str, Any]:
    return page.evaluate(MSN_V15_SHADOW_LOADER_JS, {"stableTarget": stable_target, "maxPasses": max_passes})


def collect_msn_v15_scroller_diagnostics(page: Any, loader: Mapping[str, Any] | None = None) -> dict[str, Any]:
    loader = dict(loader or {})
    diagnostics = {
        "social_comment_wc_found": bool(loader.get("host_found")),
        "shadow_root_found": bool(loader.get("shadow_open")),
        "overlay_opened": bool(loader.get("host_found") and loader.get("shadow_open")),
        "scroller_candidate_count": len(loader.get("scroller_candidates") or []),
        "selected_scroller_reason": "selected_top_ranked_internal_comment_scroller" if loader.get("selected_scroller_index") == 0 else str(loader.get("error") or "no_selected_internal_comments_scroller"),
        "page_url_after_open": str(getattr(page, "url", "")),
        "body_or_shadow_text_len": int(loader.get("body_or_shadow_len") or 0),
        "comments_word_count": int(loader.get("comment_word_count") or 0),
        "reply_word_count": int(loader.get("reply_word_count") or 0),
        "see_more_reply_count": loader.get("see_more_reply_count"),
        "see_more_text_count": loader.get("see_more_text_count"),
        "page_scroll_changed": bool(loader.get("page_scroll_changed")),
    }
    if loader.get("load_more_comment_count") is not None:
        diagnostics["load_more_comment_count"] = loader.get("load_more_comment_count")
    return diagnostics


def _selected_scroller_metrics(page: Any) -> Mapping[str, Any] | None:
    return page.evaluate(
        r"""
        () => {
          const el = window.__MSN_V15_SELECTED_SCROLLER || window.__MSN_V12_SELECTED_SCROLLER;
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return {
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight,
            scrollTop: el.scrollTop,
            rect: {x: r.x, y: r.y, width: r.width, height: r.height},
            textLen: ((el.innerText || el.textContent || "")).length
          };
        }
        """
    )


def capture_msn_android_comments_stitched_screenshot(
    page: Any,
    output_dir: str | Path,
    *,
    debug: bool = False,
    stable_target: int = 10,
    max_passes: int = 260,
    max_segments: int = 90,
    overlap_css: int = 80,
) -> dict[str, Any]:
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - exercised only when optional dependency is missing
        raise RuntimeError("Pillow is required for MSN V15 internal scroller image stitching") from exc

    root = Path(output_dir)
    screenshots = root / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    debug_segments = screenshots / "comments_stitch_segments"
    if debug:
        debug_segments.mkdir(parents=True, exist_ok=True)

    loader = expand_msn_comment_shadow_roots(page, stable_target=stable_target, max_passes=max_passes)
    suppressions = [suppress_msn_consent_for_capture(page)]
    metrics = _selected_scroller_metrics(page)
    if not metrics:
        raise MsnV15CaptureError(
            "MSN V15 comments screenshot failed: no selected internal comments scroller",
            collect_msn_v15_scroller_diagnostics(page, loader),
        )
    rect = metrics["rect"]
    scroll_height = int(metrics.get("scrollHeight") or 0)
    client_height = int(metrics.get("clientHeight") or 0)
    if scroll_height <= 0 or client_height <= 0:
        raise MsnV15CaptureError(
            "MSN V15 comments screenshot failed: invalid internal scroller metrics",
            collect_msn_v15_scroller_diagnostics(page, loader),
        )

    x = max(0.0, float(rect["x"]))
    y = max(0.0, float(rect["y"]))
    width = max(1.0, min(float(rect["width"]), 1082.0))
    height = max(1.0, min(float(rect["height"]), 1400.0 - y))
    if width < 100 or height < 180:
        raise MsnV15CaptureError(
            f"MSN V15 comments screenshot failed: bad selected scroller rectangle {rect}",
            collect_msn_v15_scroller_diagnostics(page, loader),
        )

    step = max(120, int(height - overlap_css))
    max_scroll_top = max(0, scroll_height - client_height)
    positions = list(range(0, max_scroll_top + 1, step))
    if not positions or positions[-1] != max_scroll_top:
        positions.append(max_scroll_top)
    positions = positions[:max_segments]

    segments = []
    for index, position in enumerate(positions):
        page.evaluate(
            "(y) => { const el = window.__MSN_V15_SELECTED_SCROLLER || window.__MSN_V12_SELECTED_SCROLLER; if (el) { el.scrollTop = y; el.dispatchEvent(new Event('scroll', {bubbles:true, composed:true})); } }",
            position,
        )
        page.wait_for_timeout(250)
        suppressions.append(suppress_msn_consent_for_capture(page))
        page.wait_for_timeout(80)
        png_bytes = page.screenshot(
            full_page=False,
            clip={"x": x, "y": y, "width": width, "height": height},
            timeout=30000,
        )
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        segments.append(image)
        if debug:
            image.save(debug_segments / f"segment_{index:03d}_{position}.png")
    if not segments:
        raise RuntimeError("MSN V15 comments screenshot failed: no scroller segments captured")
    final = Image.new("RGB", (max(segment.width for segment in segments), sum(segment.height for segment in segments)))
    y_offset = 0
    for segment in segments:
        final.paste(segment, (0, y_offset))
        y_offset += segment.height
    output = screenshots / ACCEPTED_COMMENTS_SCREENSHOT_NAME
    final.save(output)
    return {
        "capture_mode": MSN_COMMENTS_CAPTURE_MODE_V15,
        "comments_single_screenshot": str(output),
        "comments_single_dims": [final.width, final.height],
        "segments": len(segments),
        "debug_segments_written": debug,
        "page_scroll_changed_during_comments_load": bool(loader.get("page_scroll_changed")),
        "reply_expand_clicks": loader.get("total_reply_expand_clicks"),
        "comment_text_expand_clicks": loader.get("total_text_expand_clicks"),
        "comment_load_clicks": loader.get("total_load_clicks"),
        "see_more_reply_count_after_expansion": loader.get("see_more_reply_count"),
        "see_more_text_count_after_expansion": loader.get("see_more_text_count"),
        "load_more_comment_count_after_expansion": loader.get("load_more_comment_count"),
        "consent_suppressions": suppressions,
    }


def capture_msn_android_article_screenshot(
    page: Any,
    output_dir: str | Path,
    *,
    title: str = "Arrest made after shot fired outside York mosque",
) -> dict[str, Any]:
    screenshots = Path(output_dir) / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    align = page.evaluate(MSN_V6_ARTICLE_ALIGN_JS, title)
    page.wait_for_timeout(1000)
    output = screenshots / ACCEPTED_ARTICLE_SCREENSHOT_NAME
    clip = align.get("clip") if isinstance(align, Mapping) else None
    if clip:
        page.screenshot(path=str(output), full_page=False, clip=clip, timeout=30000)
    else:
        page.screenshot(path=str(output), full_page=False, timeout=30000)
    return {
        "capture_method": MSN_ARTICLE_SCREENSHOT_METHOD_V6,
        "article_screenshot": str(output),
        "align": _value_for_dict(align),
    }


def run_msn_browser_screenshot_capture(
    *,
    target_url: str,
    output_dir: str | Path,
    capture_article: bool = True,
    capture_comments: bool = True,
    headed: bool = False,
    debug: bool = False,
    keep_browser_open: bool = False,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on operator environment
        raise RuntimeError("Playwright is required for MSN browser screenshot capture") from exc

    parts = build_msn_url_parts(target_url)
    result: dict[str, Any] = {
        "headless": not headed,
        "article": None,
        "comments": None,
        "debug": debug,
        "capture_methods": {
            "article": build_msn_article_v6_capture_metadata(),
            "comments": build_msn_comments_v15_capture_metadata(),
        },
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=2.625,
            is_mobile=True,
            has_touch=True,
            user_agent=(
                "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
            ),
        )
        try:
            if capture_article:
                page = context.new_page()
                page.goto(parts.article_url, wait_until="domcontentloaded", timeout=70000)
                page.wait_for_timeout(6000)
                result["article"] = capture_msn_android_article_screenshot(page, output_dir)
                page.close()
            if capture_comments:
                page = context.new_page()
                result["comments_overlay_open"] = open_msn_comments_overlay(page, parts.comments_url, target_id=parts.target_id)
                result["comments"] = capture_msn_android_comments_stitched_screenshot(page, output_dir, debug=debug)
                page.close()
        finally:
            if not keep_browser_open:
                context.close()
                browser.close()
    return result


def write_msn_adapter_comment_exports(
    export: MsnCommentsProfileExport,
    output_dir: str | Path,
    *,
    generated_at: str = "",
) -> MsnCommentsProfileExportFiles:
    files = write_msn_comments_profile_exports(
        export,
        output_dir,
        base_name="comments",
        generated_at=generated_at,
    )
    out = Path(output_dir)
    copies = {
        Path(files.json_path): out / "comments.json",
        Path(files.txt_path): out / "comments.txt",
        Path(files.markdown_path): out / "comments.md",
        Path(files.html_path): out / "comments.html",
        Path(files.profiles_json_path): out / "profiles.json",
        Path(files.profiles_txt_path): out / "profiles.txt",
    }
    for source, destination in copies.items():
        if source != destination:
            shutil.copy2(source, destination)
    return files


def _rendered_comment_rows_to_capture(rows: Sequence[Mapping[str, Any]], *, source_url: str, title: str = "", shown_count: int = 0) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: int(item.get("capture_order") or 0)):
        comment_id = str(row.get("comment_id") or row.get("stable_identifier") or row.get("network_api_correlation_id") or "")
        parent_id = str(row.get("parent_comment_id") or row.get("reply_to") or "")
        item = {
            "source_comment_id": comment_id,
            "type": "Reply" if parent_id or int(row.get("depth") or 0) > 0 else "Parent Comment",
            "author": str(row.get("author") or "Unknown"),
            "date": str(row.get("posted_at") or row.get("date") or ""),
            "author_profile_url": str(row.get("author_profile_url") or ""),
            "author_profile_cid": str(row.get("author_reference_id") or ""),
            "likes": str(row.get("reaction_count") if row.get("reaction_count") is not None else row.get("likes") or ""),
            "dislikes": str(row.get("dislikes") or ""),
            "text": str(row.get("text") or ""),
            "deleted_placeholder": str(row.get("visible_status") or "").lower() == "deleted",
            "capture_source_note": str(row.get("capture_source") or "rendered_browser_validation"),
            "replies": [],
        }
        by_id[comment_id] = item
        if parent_id and parent_id in by_id:
            by_id[parent_id]["replies"].append(item)
        else:
            roots.append(item)
    return {
        "file": "live_capture_rendered_browser_comments.json",
        "source_url": source_url,
        "title": title,
        "sort_filter": "Top",
        "shown_msn_count": shown_count or len(rows),
        "comments": roots,
    }


def find_live_capture_comments_path(live_capture_dir: str | Path) -> Path | None:
    root = Path(live_capture_dir)
    candidates = (
        root / "browser_capture" / "android_mobile_chromium" / "comments.json",
        root / "browser_capture" / "desktop_chromium" / "comments.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    matches = sorted(root.glob("browser_capture/*/comments.json"))
    return matches[0] if matches else None


def build_msn_comments_profile_export_from_live_capture(live_capture_dir: str | Path) -> MsnCommentsProfileExport | None:
    root = Path(live_capture_dir)
    comments_path = find_live_capture_comments_path(root)
    if not comments_path:
        return None
    try:
        rows = json.loads(comments_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(rows, list) or not rows:
        return None
    validation: Mapping[str, Any] = {}
    validation_path = root / "validation.json"
    if validation_path.is_file():
        try:
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
        except Exception:
            validation = {}
    capture = _rendered_comment_rows_to_capture(
        [row for row in rows if isinstance(row, Mapping)],
        source_url=str(validation.get("target_url") or YORK_COMMENTS_URL),
        title=str(validation.get("title") or "Arrest made after shot fired outside York mosque"),
        shown_count=int(validation.get("comment_count") or len(rows)),
    )
    return build_msn_comments_profile_export([capture])


def build_msn_closeout_result(
    *,
    output_dir: str | Path,
    url: str,
    expected_comment_count: int,
    comments_export: MsnCommentsProfileExport | None = None,
    comments_files: MsnCommentsProfileExportFiles | None = None,
    media_receipts: Sequence[MsnMediaReceipt] = (),
    offline_archive: MsnOfflineArchiveStatus | None = None,
    source_role_fields_included: bool = False,
    warnings: Sequence[str] = (),
) -> MsnCloseoutResult:
    parts = build_msn_url_parts(url)
    root = Path(output_dir)
    article_screenshot = root / "screenshots" / ACCEPTED_ARTICLE_SCREENSHOT_NAME
    comments_screenshot = root / "screenshots" / ACCEPTED_COMMENTS_SCREENSHOT_NAME
    comment_count = comments_export.items_captured if comments_export else 0
    profile_count = len(comments_export.profiles) if comments_export else 0
    warnings_list = list(warnings)
    if expected_comment_count and comment_count != expected_comment_count:
        warnings_list.append(f"comment_count_mismatch expected={expected_comment_count} actual={comment_count}")
    if not article_screenshot.is_file():
        warnings_list.append("article_screenshot_missing")
    if not comments_screenshot.is_file():
        warnings_list.append("comments_screenshot_missing")
    required = tuple(media_receipts or required_msn_article_media(parts.article_url))
    media_satisfied = bool(required) and all(item.status == MSN_MEDIA_SATISFIED for item in required)
    if required and not media_satisfied:
        warnings_list.append("required_media_missing")
    archive = offline_archive or build_offline_archive_status(root)
    if archive.warc_generated and not archive.warc_replay_tested:
        warnings_list.append("warc_generated_but_replay_not_tested")
    if archive.wacz_generated and not archive.wacz_replay_tested:
        warnings_list.append("wacz_generated_but_replay_not_tested")
    if comments_files and not source_role_fields_included:
        warnings_list.append("source_role_fields_absent_from_comments_export")
    source_role_claims_json = ""
    media_source_chain_json = ""
    if parts.target_id == YORK_TARGET_ID:
        sidecars = write_york_source_role_sidecars(root)
        source_role_claims_json = sidecars["source_role_claims_json"]
        media_source_chain_json = sidecars["media_source_chain_json"]
        source_role_fields_included = True
    files = comments_files
    fatal_warnings = [warning for warning in warnings_list if warning not in NON_FATAL_CLOSEOUT_WARNINGS]
    result = MsnCloseoutResult(
        decision=MSN_PRODUCTION_READY if not fatal_warnings else MSN_CLOSEOUT_REVIEW_REQUIRED,
        output_root=str(root),
        article_url=parts.article_url,
        comments_url=parts.comments_url,
        target_id=parts.target_id,
        comment_count=comment_count,
        expected_comment_count=expected_comment_count,
        profile_count=profile_count,
        article_screenshot=str(article_screenshot) if article_screenshot.is_file() else "",
        comments_screenshot=str(comments_screenshot) if comments_screenshot.is_file() else "",
        media_required=tuple(item.to_dict() for item in required),
        media_satisfied=media_satisfied,
        html_export=str(root / "comments.html") if (root / "comments.html").is_file() else (files.html_path if files else ""),
        json_export=str(root / "comments.json") if (root / "comments.json").is_file() else (files.json_path if files else ""),
        md_export=str(root / "comments.md") if (root / "comments.md").is_file() else (files.markdown_path if files else ""),
        txt_export=str(root / "comments.txt") if (root / "comments.txt").is_file() else (files.txt_path if files else ""),
        profiles_json=str(root / "profiles.json") if (root / "profiles.json").is_file() else (files.profiles_json_path if files else ""),
        profiles_txt=str(root / "profiles.txt") if (root / "profiles.txt").is_file() else (files.profiles_txt_path if files else ""),
        source_role_claims_json=source_role_claims_json,
        media_source_chain_json=media_source_chain_json,
        offline_archive=archive.to_dict(),
        media_downloaded_classified_count=sum(1 for item in required if item.status == MSN_MEDIA_SATISFIED),
        source_role_fields_included=source_role_fields_included,
        warnings=tuple(sorted(set(warnings_list))),
    )
    _write_json(root / "msn-closeout-report.json", result.to_dict())
    (root / "msn-closeout-report.txt").write_text(result.final_block() + "\n", encoding="utf-8")
    return result


def run_msn_closeout_validation(
    *,
    target_url: str,
    output_dir: str | Path,
    comments_capture_paths: Sequence[str | Path] = (),
    expected_comment_count: int = 0,
    capture_msn_screenshots: bool = False,
    capture_msn_article_screenshot: bool = False,
    capture_msn_comments_screenshot: bool = False,
    download_media: bool = False,
    headed: bool = False,
    debug: bool = False,
    keep_browser_open: bool = False,
    live_capture_runner: Callable[..., Any] = run_live_viewable_capture,
    screenshot_runner: Callable[..., Any] | None = run_msn_browser_screenshot_capture,
    media_downloader: Callable[[str], bytes] | None = None,
) -> MsnCloseoutResult:
    parts = build_msn_url_parts(target_url)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    comments_export: MsnCommentsProfileExport | None = None
    comments_files: MsnCommentsProfileExportFiles | None = None
    warnings: list[str] = []
    source_role_fields_included = False
    if comments_capture_paths:
        comments_export = build_msn_comments_profile_export_from_paths(comments_capture_paths)
        comments_files = write_msn_adapter_comment_exports(comments_export, root)
        source_role_fields_included = all(
            bool(item.get("source_role_metadata")) for item in comments_export.comments
        )
    offline_archive = build_offline_archive_status(root / "live_capture")
    if capture_msn_screenshots or capture_msn_article_screenshot or capture_msn_comments_screenshot:
        capture_result = live_capture_runner(
            target_url=parts.comments_url,
            output_dir=root / "live_capture",
            capture_comments=True,
            write_wacz=True,
            write_warc=True,
            write_rendered_html=True,
            write_screenshots=True,
            write_validation_json=True,
            write_local_viewer=True,
            headed=headed,
        )
        if getattr(capture_result, "status", "") and getattr(capture_result, "status") != LIVE_VIEWABLE_CAPTURE_COMPLETED:
            warnings.append(f"live_capture_status={getattr(capture_result, 'status')}")
        offline_archive = build_offline_archive_status(root / "live_capture")
        if comments_export is None:
            comments_export = build_msn_comments_profile_export_from_live_capture(root / "live_capture")
            if comments_export:
                comments_files = write_msn_adapter_comment_exports(comments_export, root)
                source_role_fields_included = all(
                    bool(item.get("source_role_metadata")) for item in comments_export.comments
                )
            elif expected_comment_count:
                warnings.append("live_capture_completed_but_comments_export_missing")
        if screenshot_runner is not None:
            try:
                screenshot_runner(
                    target_url=parts.comments_url,
                    output_dir=root,
                    capture_article=capture_msn_screenshots or capture_msn_article_screenshot,
                    capture_comments=capture_msn_screenshots or capture_msn_comments_screenshot,
                    headed=headed,
                    debug=debug,
                    keep_browser_open=keep_browser_open,
                )
            except MsnV15CaptureError as exc:
                warnings.append(f"accepted_screenshot_methods_failed={exc}")
                for key, value in exc.diagnostics.items():
                    warnings.append(f"v15_diagnostic_{key}={value}")
                promoted = promote_accepted_screenshot_outputs(root / "live_capture", debug=debug)
                for key, value in promoted.items():
                    if value and key in {"article", "comments"}:
                        _copy_if_present(Path(value), root / "screenshots" / Path(value).name)
                warnings.append("accepted_screenshot_outputs_promoted_from_live_capture_fallback")
            except Exception as exc:
                warnings.append(f"accepted_screenshot_methods_failed={exc}")
                promoted = promote_accepted_screenshot_outputs(root / "live_capture", debug=debug)
                for key, value in promoted.items():
                    if value and key in {"article", "comments"}:
                        _copy_if_present(Path(value), root / "screenshots" / Path(value).name)
                warnings.append("accepted_screenshot_outputs_promoted_from_live_capture_fallback")
        else:
            promoted = promote_accepted_screenshot_outputs(root / "live_capture", debug=debug)
            for key, value in promoted.items():
                if value and key in {"article", "comments"}:
                    _copy_if_present(Path(value), root / "screenshots" / Path(value).name)
            warnings.append("accepted_v15_v6_screenshot_methods_not_run")
    if keep_browser_open and not headed:
        warnings.append("keep_browser_open_ignored_without_headed")
    elif keep_browser_open:
        warnings.append("keep_browser_open_requested_but_current_runner_closes_browser_after_capture")
    media_receipts = download_msn_article_media(article_url=parts.article_url, output_dir=root, downloader=media_downloader) if download_media else required_msn_article_media(parts.article_url)
    return build_msn_closeout_result(
        output_dir=root,
        url=parts.comments_url,
        expected_comment_count=expected_comment_count,
        comments_export=comments_export,
        comments_files=comments_files,
        media_receipts=media_receipts,
        offline_archive=offline_archive,
        source_role_fields_included=source_role_fields_included,
        warnings=warnings,
    )


def render_msn_comments_html_export(export: MsnCommentsProfileExport) -> str:
    return render_msn_comments_html(export)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MSN source adapter production closeout workflow.")
    parser.add_argument("--source-adapter", default="msn", choices=("msn",))
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--comments-json", action="append", default=[])
    parser.add_argument("--expected-comment-count", type=int, default=0)
    parser.add_argument("--msn-comments-sort", default="top", choices=("top", "newest", "both"))
    parser.add_argument("--capture-msn-screenshots", action="store_true")
    parser.add_argument("--capture-msn-article-screenshot", action="store_true")
    parser.add_argument("--capture-msn-comments-screenshot", action="store_true")
    parser.add_argument("--download-media", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--keep-browser-open", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_msn_closeout_validation(
        target_url=args.target_url,
        output_dir=args.output_dir,
        comments_capture_paths=args.comments_json,
        expected_comment_count=args.expected_comment_count,
        capture_msn_screenshots=args.capture_msn_screenshots,
        capture_msn_article_screenshot=args.capture_msn_article_screenshot,
        capture_msn_comments_screenshot=args.capture_msn_comments_screenshot,
        download_media=args.download_media,
        headed=args.headed,
        debug=args.debug,
        keep_browser_open=args.keep_browser_open,
    )
    print(result.final_block())
    return 0 if result.decision == MSN_PRODUCTION_READY else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
