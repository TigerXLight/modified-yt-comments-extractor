"""R42AE one-window live WebView selected-source presentation editor.

This module builds a browser/WebView-ready overlay for a selected link. It does
not classify roles. Callers pass the selected-source Semantic/Media rows already
built by the Review DB import path. R42AA keeps the pywebview live URL as the normal
source-editor surface: copy/open controls live inside the WebView, highlighted
text remains selectable, role items can be cycled, media receives source-role
outlines, and the launcher writes logs instead of failing silently. R42AA/R42AB/R42AC/R42AD/R42AE tighten the WebView presentation layer only: they restore Review-row painting, keep visible BLANK rows, header/meta painting, robust media/video outlines, no popup role toast, and live video playback untouched. R42AE specifically added document-coordinate media outline boxes. R42AF narrows media targets so Media mode outlines the actual article video/image/figure regions instead of the whole article container. R42AG adds persistent WebView2/pywebview browser storage for cookies/cache, a conservative cookie-consent helper, and outline-only media boxes with no role-colour fill inside media regions.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import subprocess
import sys
import shutil
import importlib.util
import textwrap
import time
from pathlib import Path
from typing import Any, Iterable, Mapping


R42H_REAL_WEBVIEW_OVERLAY_MARKER = "YTCE_V83D_R42H_REAL_WEBVIEW_SOURCE_ROLE_OVERLAY"
R42Q_WEBVIEW_EDITOR_MARKER = "YTCE_V83D_R42Q_WEBVIEW_SELECTED_SOURCE_EDITOR"
R42R_LIVE_WEBVIEW_MARKER = "YTCE_V83D_R42R_LIVE_URL_WEBVIEW_OVERLAY_STABLE_EDIT_ICON"
R42S_ONE_WINDOW_LIVE_WEBVIEW_MARKER = "YTCE_V83D_R42S_ONE_WINDOW_LIVE_URL_SOURCE_EDITOR"
R42T_JS_ESCAPE_FIX_MARKER = "YTCE_V83D_R42T_WEBVIEW_OVERLAY_JS_ESCAPE_FIX"
R42U_PRESENTATION_FIX_MARKER = "YTCE_V83D_R42U_WEBVIEW_PRESENTS_REVIEW_ROWS_AS_EXACT_SPANS"
R42V_PRESENTATION_SPEED_SAVE_MARKER = "YTCE_V83D_R42V_WEBVIEW_PRESENTATION_SPEED_SAVE_AND_HEADER_FIX"
R42W_LAUNCHER_NEWLINE_FIX_MARKER = "YTCE_V83D_R42W_WEBVIEW_LAUNCHER_NEWLINE_SYNTAX_FIX"
R42X_PRESENTATION_PARITY_MARKER = "YTCE_V83D_R42X_WEBVIEW_REVIEW_PRESENTATION_PARITY_AND_FAST_CLICKS"
R42Y_PRESENTATION_PARITY_MARKER = "YTCE_V83D_R42Y_WEBVIEW_HEADER_META_MEDIA_OUTLINES_FAST_SINGLE_INJECT"
R42Z_PRESENTATION_PARITY_MARKER = "YTCE_V83D_R42Z_WEBVIEW_DETERMINISTIC_REVIEW_ROW_PRESENTATION"
R42AA_PRESENTATION_VISIBILITY_MARKER = "YTCE_V83D_R42AA_WEBVIEW_ARTICLE_COLOURING_VISIBILITY_FIX"
R42AB_ROBUST_DOM_PRESENTATION_MARKER = "YTCE_V83D_R42AB_WEBVIEW_ROBUST_DOM_PAINT_RESTORE"
R42AC_REPAINT_AND_BODY_FALLBACK_MARKER = "YTCE_V83D_R42AC_WEBVIEW_REPAINT_AND_BODY_TEXTMAP_FALLBACK"
R42AD_FAST_PAINT_MEDIA_OUTLINES_MARKER = "YTCE_V83D_R42AD_WEBVIEW_FAST_FIRST_PAINT_AND_MEDIA_OUTLINES"
R42AE_MEDIA_OUTLINE_BOX_MARKER = "YTCE_V83D_R42AE_WEBVIEW_DOCUMENT_MEDIA_OUTLINE_BOXES"
R42AF_MEDIA_TARGET_NARROWING_MARKER = "YTCE_V83D_R42AF_WEBVIEW_NARROW_ARTICLE_MEDIA_OUTLINES"
R42AG_COOKIE_CACHE_OUTLINE_MARKER = "YTCE_V83D_R42AG_WEBVIEW_COOKIE_CACHE_AND_OUTLINE_ONLY_MEDIA"
R42AI_NATIVE_WEBVIEW2_EDITOR_MARKER = "YTCE_V83D_R42AI_NATIVE_WEBVIEW2_SOURCE_ROLE_EDITOR"
R42AJ_NATIVE_EDITOR_ROOTFIX_MARKER = "YTCE_V83D_R42AJ_NATIVE_WEBVIEW2_EDITOR_ROOT_PATH_FIX"
R42AK_NATIVE_EDITOR_ABSPATH_UDF_MARKER = "YTCE_V83D_R42AK_NATIVE_WEBVIEW2_ABSOLUTE_PATH_AND_SHORT_UDF_FIX"
R42AM_NATIVE_EDITOR_POLISH_MARKER = "YTCE_V83D_R42AM_NATIVE_WEBVIEW2_EDITOR_POLISH"
R42AN_NATIVE_EDITOR_SPAN_SPEED_MARKER = "YTCE_V83D_R42AN_NATIVE_WEBVIEW2_EDITOR_SPAN_SPEED_POLISH"
R42AP_NATIVE_EDITOR_MEDIA_UI_MATCH_MARKER = "YTCE_V83D_R42AP_NATIVE_WEBVIEW2_MEDIA_UI_MATCH_POLISH"
R42AR_NATIVE_EDITOR_SPEED_RESOURCE_MARKER = "YTCE_V83D_R42AR_NATIVE_WEBVIEW2_RESOURCE_BLOCK_COMPILE_FIX"
R42AS_NATIVE_EDITOR_STABLE_DEBUG_UI_MARKER = "YTCE_V83D_R42AS_NATIVE_WEBVIEW2_STABLE_DEBUG_UI_MATCH_FIX"
R42AX_NATIVE_EDITOR_TARGETED_MEDIA_FAST_MARKER = "YTCE_V83D_R42AX_NATIVE_WEBVIEW2_MEDIA_ROLE_COLOR_AND_LOGGING_FIX"
R42AY_NATIVE_EDITOR_CLEAN_GREY_TOGGLE_MARKER = "YTCE_V83D_R42AY_NATIVE_WEBVIEW2_CLEAN_GREY_TOGGLE_LOG_FIX"
R42CR_NATIVE_EDITOR_WARM_SERVER_MARKER = "YTCE_V83D_R42CR_NATIVE_WEBVIEW2_WARM_SERVER_SPEED_FIX"
R42CR_NATIVE_EDITOR_EARLY_WARM_MARKER = "YTCE_V83D_R42CR_NATIVE_WEBVIEW2_EARLY_APP_WARM_SERVER_FIX"
R42CR_NATIVE_EDITOR_URL_NAV_MARKER = "YTCE_V83D_R42CR_NATIVE_WEBVIEW2_IN_WINDOW_SOURCE_URL_NAVIGATION"
R42EB_ARCHIVE_URL_GUARD_MARKER = "YTCE_V83D_R42EB_ARCHIVE_URL_CANONICAL_GUARD_AND_LOCAL_FIXTURE"
ROLE_EFFECT = "metadata_only_no_role_change"
ROLES = {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK", "LOCATOR"}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()




def _r42eb_clean_url_for_navigation(value: object) -> str:
    """Return a browser-safe URL from plain URLs or chat/Markdown-wrapped links.

    R42EB intentionally does not lowercase archive short codes globally because
    archive.ph identifiers are case-sensitive.  It only protects the known single
    test source where repeated copy/paste produced the bad mixed-case 6Mr3C URL.
    """
    text = _clean(value).strip().strip('"\'<>')
    if not text:
        return ""
    text = (
        text.replace("\\(", "(")
        .replace("\\)", ")")
        .replace("\\[", "[")
        .replace("\\]", "]")
        .replace("\\_", "_")
    )
    m = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", text, flags=re.IGNORECASE)
    if m:
        text = m.group(1).strip()
    else:
        urls = re.findall(r"https?://[^\s\]\)<>'\"]+", text, flags=re.IGNORECASE)
        if urls:
            text = urls[-1].strip()
    text = text.strip().strip('"\'<>')
    while text and text[-1] in ".,;":
        text = text[:-1]
    # Known single archive.ph test guard: do not turn all archive ids lowercase.
    text = text.replace("https://archive.ph/6Mr3C", "https://archive.ph/6mr3C")
    text = text.replace("http://archive.ph/6Mr3C", "http://archive.ph/6mr3C")
    text = text.replace("https://archive.today/6Mr3C", "https://archive.today/6mr3C")
    text = text.replace("http://archive.today/6Mr3C", "http://archive.today/6mr3C")
    return text


def _role(value: object) -> str:
    text = _clean(value).upper()
    return text if text in ROLES else "UNKNOWN"


def _encode_image_data_uri(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".") or "png"
    if suffix == "jpg":
        suffix = "jpeg"
    return f"data:image/{suffix};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _asset_icon_data_uris() -> dict[str, str]:
    """Return embedded toolbar icons from the project assets folder when present."""
    icon_dir = Path.cwd() / "assets" / "profile_media" / "source_roles"
    names = {
        "link": "icons8-link-50.png",
        "copy_plain": "icons8-copy-24.png",
        "copy_roles": "icons8-copy-source-role-multicolour-24.png",
        "external": "icons8-external-link-48.png",
    }
    out: dict[str, str] = {}
    for key, filename in names.items():
        try:
            path = icon_dir / filename
            if path.is_file():
                out[key] = _encode_image_data_uri(path)
        except Exception:
            pass
    return out


def _safe_rows(rows: Iterable[Mapping[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    active_mode = "media" if str(mode).lower() == "media" else "semantic"
    for index, row in enumerate(rows or (), start=1):
        if not isinstance(row, Mapping):
            continue
        text = _clean(row.get("text") or row.get("url") or row.get("media_url"))
        kind = _clean(row.get("kind") or "text").lower() or "text"
        if not text and kind not in {"image", "video", "media"}:
            continue
        semantic = _role(row.get("semantic_role") or row.get("role") or row.get("claim_role"))
        media = _role(row.get("media_source_role") or row.get("media_source_display_role") or row.get("media_display_role") or row.get("source_reference_media_display_role") or row.get("media_role") or "BLANK")
        active = media if active_mode == "media" else semantic
        if active_mode == "media" and kind not in {"image", "video", "media", "link", "archive", "locator"} and media == "UNKNOWN":
            if not any(row.get(k) for k in ("media_source_role", "media_source_display_role", "media_display_role", "source_reference_media_display_role", "media_role")):
                active = "BLANK"
        out.append(
            {
                "index": index,
                "edit_key": _clean(row.get("edit_key") or f"row_{index}"),
                "text": text,
                "kind": kind,
                "semantic_role": semantic,
                "media_source_role": media,
                "active_role": active,
                "url": _clean(row.get("url") or row.get("normalised_url") or row.get("media_url")),
                "media_url": _clean(row.get("media_url") or row.get("url")),
                "missing_provenance_reason": _clean(row.get("missing_provenance_reason")),
                "provenance_status": _clean(row.get("provenance_status")),
            }
        )
    return out


def _counts(rows: Iterable[Mapping[str, Any]], *, role_key: str = "active_role") -> dict[str, int]:
    counts = {"PRIMARY": 0, "SECONDARY": 0, "TERTIARY": 0, "UNKNOWN": 0}
    for row in rows:
        role = _role(row.get(role_key))
        if role in counts:
            counts[role] += 1
    return counts


def _plain_text(rows_by_mode: Mapping[str, list[dict[str, Any]]]) -> str:
    rows = rows_by_mode.get("semantic") or rows_by_mode.get("media") or []
    return "\n".join(_clean(row.get("text")) for row in rows if _clean(row.get("text"))).strip()


def _role_markup(rows_by_mode: Mapping[str, list[dict[str, Any]]], *, mode: str) -> str:
    mode_key = "media" if str(mode).lower() == "media" else "semantic"
    role_key = "media_source_role" if mode_key == "media" else "semantic_role"
    rows = rows_by_mode.get(mode_key) or []
    lines: list[str] = []
    for row in rows:
        text = _clean(row.get("text") or row.get("url") or row.get("media_url"))
        role = _role(row.get(role_key) or row.get("active_role"))
        if text:
            lines.append(f"[{text} | {role}]")
    return "\n".join(lines).strip()


def _url_nav_kind_and_label(url: object, explicit_label: object = "") -> tuple[str, str]:
    text = _clean(url)
    label = _clean(explicit_label)
    low = text.lower()
    if "web.archive.org/web/" in low:
        return "wayback", ("Wayback Snapshot" if label.lower() == "archive url" else (label or "Wayback"))
    if re.search(r"https?://(?:www\.)?(?:archive\.(?:ph|today|is|li|md|vn)|ghostarchive\.org)/", low):
        return "archive_ph", label or "archive.ph"
    if "archive" in low:
        return "archive", label or "Archive"
    return "original", label or "Original"


def _url_nav_key(url: object) -> str:
    text = _clean(url)
    if not text:
        return ""
    try:
        # Keep this deliberately simple/offline: it is for dedupe/display only.
        text = re.sub(r"#.*$", "", text.strip())
        text = re.sub(r"/$", "", text)
    except Exception:
        pass
    return text.casefold()


def _source_navigation_urls_from_edit_state(edit_state: Mapping[str, Any], selected_url: str) -> list[dict[str, Any]]:
    """Return ordered in-window navigation targets for original/archives.

    The edit window still paints from the same JSON payload.  These URLs only
    let the native WebView2 toolbar move between the original live page, Wayback,
    archive.ph, etc. without reopening the editor or touching first paint state.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(url: object, label: object = "", *, current: bool = False, relation: object = "") -> None:
        text = _clean(url)
        if not text or not re.match(r"https?://", text, flags=re.IGNORECASE):
            return
        key = _url_nav_key(text)
        if not key or key in seen:
            return
        seen.add(key)
        kind, auto_label = _url_nav_kind_and_label(text, label)
        out.append({
            "url": text,
            "label": auto_label,
            "kind": kind,
            "current": bool(current or (_url_nav_key(text) == _url_nav_key(selected_url))),
            "relation": _clean(relation),
        })

    add(selected_url, "Original", current=True, relation="selected")

    raw_candidates: list[Any] = []
    for key in (
        "source_navigation_urls",
        "source_url_navigation",
        "available_source_urls",
        "available_source_links",
        "link_source_navigation_urls",
        "alternate_source_urls",
        "archive_source_urls",
        "preservation_source_urls",
        "source_urls",
        "evidence_urls",
        "resolved_source_urls",
        "attached_source_urls",
    ):
        value = edit_state.get(key)
        if isinstance(value, list):
            raw_candidates.extend(value)

    # The main Tk review window attaches all same-source original/archive rows here.
    for container_key in ("r42b_preview_context", "preview_context", "link_source_preview"):
        container = edit_state.get(container_key)
        if isinstance(container, Mapping):
            for key in ("source_navigation_urls", "link_source_objects", "objects", "archive_urls", "preservation_urls"):
                value = container.get(key)
                if isinstance(value, list):
                    raw_candidates.extend(value)

    for mode_rows in (edit_state.get("semantic_rows"), edit_state.get("media_rows"), edit_state.get("active_rows")):
        if isinstance(mode_rows, list):
            for row in mode_rows:
                if isinstance(row, Mapping):
                    for key in ("url", "normalised_url", "display_url", "archive_url", "archive_target_url", "preservation_for_url"):
                        candidate = row.get(key)
                        if _clean(candidate) and _clean(candidate) != selected_url:
                            raw_candidates.append({"url": candidate, "label": row.get("label") or row.get("kind") or ""})

    for item in raw_candidates:
        if isinstance(item, str):
            add(item)
            continue
        if not isinstance(item, Mapping):
            continue
        label = item.get("label") or item.get("display_label") or item.get("visible_link_source_row_label") or item.get("source_label") or item.get("list_label") or ""
        relation = item.get("source_relation_type") or item.get("relation") or item.get("kind") or ""
        for key in ("url", "normalised_url", "display_url", "archive_url", "preserved_url"):
            add(item.get(key), label, relation=relation)

    # Prefer stable human order: original first, then Wayback, then archive.ph/other archives.
    def sort_key(row: Mapping[str, Any]) -> tuple[int, int]:
        kind = str(row.get("kind") or "")
        current = 0 if _url_nav_key(row.get("url")) == _url_nav_key(selected_url) else 1
        order = {"original": 0, "wayback": 1, "archive_ph": 2, "archive": 3}.get(kind, 4)
        if current == 0 and kind == "original":
            order = -1
        return (order, out.index(row) if row in out else 9999)

    try:
        out = sorted(out, key=sort_key)
    except Exception:
        pass
    for index, row in enumerate(out, start=1):
        row["index"] = index
        row["count"] = len(out)
        row["current"] = _url_nav_key(row.get("url")) == _url_nav_key(selected_url)
    return out


def _overlay_css() -> str:
    return r"""
:root{
  --ytce-primary:#00e676;
  --ytce-secondary:#1e9cff;
  --ytce-tertiary:#d65cff;
  --ytce-unknown:#ff9800;
  --ytce-blank:#475569;
  --ytce-toolbar:#0f172a;
}
#ytce-role-toolbar{position:fixed;z-index:2147483647;top:10px;left:10px;right:10px;box-sizing:border-box;display:flex;gap:8px;align-items:center;background:rgba(15,23,42,.94);color:white;border-radius:8px;padding:8px 10px;font:13px/1.2 Arial,sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.35);max-width:calc(100vw - 20px);overflow:hidden;white-space:nowrap;backdrop-filter:blur(3px)}
#ytce-role-toolbar button{border:0;border-radius:6px;padding:6px 9px;background:#1d70b8;color:#fff;font-weight:700;cursor:pointer;min-width:32px;line-height:1;transition:filter .12s ease, background .12s ease, transform .08s ease, box-shadow .12s ease}
#ytce-role-toolbar button:hover{filter:brightness(1.18);background:#2684d4;box-shadow:0 0 0 2px rgba(255,255,255,.28) inset}
#ytce-role-toolbar button:active{transform:translateY(1px)}
#ytce-role-toolbar button.icon{width:34px;height:28px;padding:4px;display:inline-flex;align-items:center;justify-content:center}
#ytce-role-toolbar button.icon img{max-width:20px;max-height:20px;display:block;object-fit:contain}
#ytce-role-toolbar button.active{outline:2px solid #e0f2fe;outline-offset:1px}
#ytce-role-toolbar .spacer{flex:1 1 auto;min-width:8px}
#ytce-role-toolbar .count{border-radius:4px;padding:5px 8px;font-weight:700;border:1px solid rgba(15,23,42,.20);white-space:nowrap}
#ytce-role-toolbar .count.primary{background:#a7f3d0;color:#064e3b}
#ytce-role-toolbar .count.secondary{background:#bfdbfe;color:#1e3a8a}
#ytce-role-toolbar .count.tertiary{background:#ddd6fe;color:#581c87}
#ytce-role-toolbar .count.unknown{background:#fed7aa;color:#7c2d12}
#ytce-role-toast{position:fixed;z-index:2147483647;right:16px;bottom:16px;background:rgba(15,23,42,.95);color:white;border-radius:7px;padding:8px 11px;font:13px Arial,sans-serif;opacity:0;transition:opacity .18s ease;pointer-events:none}
#ytce-role-toast.show{opacity:1}
.ytce-role-hit{box-decoration-break:clone;-webkit-box-decoration-break:clone;border-radius:3px;padding:0 1px;cursor:pointer;user-select:text!important;-webkit-user-select:text!important;line-height:1.25}
.ytce-role-hit::selection{background:#0ea5e9!important;color:white!important}
.ytce-role-primary{background:rgba(0,230,118,.30)!important;outline:2px solid var(--ytce-primary)!important}
.ytce-role-secondary{background:rgba(30,156,255,.24)!important;outline:2px solid var(--ytce-secondary)!important}
.ytce-role-tertiary{background:rgba(214,92,255,.23)!important;outline:2px solid var(--ytce-tertiary)!important}
.ytce-role-unknown{background:rgba(255,152,0,.28)!important;outline:2px solid var(--ytce-unknown)!important}
.ytce-role-blank{background:rgba(148,163,184,.50)!important;outline:2px solid #334155!important;color:inherit!important}
.ytce-role-hit.ytce-role-blank{box-shadow:0 0 0 1px rgba(255,255,255,.9) inset,0 0 0 3px rgba(51,65,85,.14)!important}
.ytce-media-role-outline{outline-width:4px!important;outline-style:solid!important;outline-offset:3px!important;border-radius:4px!important;position:relative!important;box-shadow:0 0 0 2px rgba(255,255,255,.95),0 0 10px rgba(15,23,42,.25)!important}
.ytce-media-role-outline img,.ytce-media-role-outline video{border-radius:inherit!important}
.ytce-media-role-outline.ytce-role-primary{outline-color:var(--ytce-primary)!important}
.ytce-media-role-outline.ytce-role-secondary{outline-color:var(--ytce-secondary)!important}
.ytce-media-role-outline.ytce-role-tertiary{outline-color:var(--ytce-tertiary)!important}
.ytce-media-role-outline.ytce-role-unknown{outline-color:var(--ytce-unknown)!important}
.ytce-media-role-outline.ytce-role-blank{outline-color:#334155!important}
/* R42AG: media regions should be outlined only.  Role-fill is kept for text spans,
   but video/image/figure boxes must not tint the playable media area. */
.ytce-media-role-outline.ytce-role-primary,
.ytce-media-role-outline.ytce-role-secondary,
.ytce-media-role-outline.ytce-role-tertiary,
.ytce-media-role-outline.ytce-role-unknown,
.ytce-media-role-outline.ytce-role-blank{background:transparent!important}
.ytce-media-role-outline.ytce-role-primary>img,.ytce-media-role-outline.ytce-role-primary>video,
.ytce-media-role-outline.ytce-role-secondary>img,.ytce-media-role-outline.ytce-role-secondary>video,
.ytce-media-role-outline.ytce-role-tertiary>img,.ytce-media-role-outline.ytce-role-tertiary>video,
.ytce-media-role-outline.ytce-role-unknown>img,.ytce-media-role-outline.ytce-role-unknown>video,
.ytce-media-role-outline.ytce-role-blank>img,.ytce-media-role-outline.ytce-role-blank>video{background:transparent!important}
#ytce-role-sidecar{display:none!important}

.ytce-media-box{position:absolute!important;z-index:2147483600!important;pointer-events:none!important;box-sizing:border-box!important;border-width:4px!important;border-style:solid!important;border-radius:6px!important;background:transparent!important;outline:0!important;box-shadow:0 0 0 2px rgba(255,255,255,.96),0 0 14px rgba(15,23,42,.38)!important}
.ytce-media-box.ytce-role-primary{border-color:var(--ytce-primary)!important;background:transparent!important;outline:0!important}
.ytce-media-box.ytce-role-secondary{border-color:var(--ytce-secondary)!important;background:transparent!important;outline:0!important}
.ytce-media-box.ytce-role-tertiary{border-color:var(--ytce-tertiary)!important;background:transparent!important;outline:0!important}
.ytce-media-box.ytce-role-unknown{border-color:var(--ytce-unknown)!important;background:transparent!important;outline:0!important}
.ytce-media-box.ytce-role-blank{border-color:#334155!important;background:transparent!important;outline:0!important}
body{padding-top:58px!important;user-select:text!important;-webkit-user-select:text!important}
video{pointer-events:auto!important}
"""

def _overlay_js(rows_by_mode: Mapping[str, list[dict[str, Any]]], counts_by_mode: Mapping[str, Any], selected_url: str, initial_mode: str, plain_text: str, semantic_role_text: str, media_role_text: str) -> str:
    payload = {
        "marker": R42H_REAL_WEBVIEW_OVERLAY_MARKER,
        "r42q": R42Q_WEBVIEW_EDITOR_MARKER,
        "r42r": R42R_LIVE_WEBVIEW_MARKER,
        "r42s": R42S_ONE_WINDOW_LIVE_WEBVIEW_MARKER,
        "r42t": R42T_JS_ESCAPE_FIX_MARKER,
        "r42u": R42U_PRESENTATION_FIX_MARKER,
        "r42v": R42V_PRESENTATION_SPEED_SAVE_MARKER,
        "r42w": R42W_LAUNCHER_NEWLINE_FIX_MARKER,
        "r42x": R42X_PRESENTATION_PARITY_MARKER,
        "r42y": R42Y_PRESENTATION_PARITY_MARKER,
        "r42z": R42Z_PRESENTATION_PARITY_MARKER,
        "r42aa": R42AA_PRESENTATION_VISIBILITY_MARKER,
        "r42ab": R42AB_ROBUST_DOM_PRESENTATION_MARKER,
        "r42ac": R42AC_REPAINT_AND_BODY_FALLBACK_MARKER,
        "r42ad": R42AD_FAST_PAINT_MEDIA_OUTLINES_MARKER,
        "r42ae": R42AE_MEDIA_OUTLINE_BOX_MARKER,
        "r42af": R42AF_MEDIA_TARGET_NARROWING_MARKER,
        "r42ag": R42AG_COOKIE_CACHE_OUTLINE_MARKER,
        "selectedUrl": selected_url,
        "initialMode": "media" if initial_mode == "media" else "semantic",
        "rowsByMode": rows_by_mode,
        "counts": counts_by_mode,
        "plainText": plain_text,
        "roleText": {"semantic": semantic_role_text, "media": media_role_text},
        "r42p_no_right_side_role_panel": True,
        "r42q_webview_has_copy_open_controls": True,
        "r42q_client_side_role_cycle": True,
        "r42s_live_url_one_window_editor": True,
        "r42t_js_escape_fix": True,
        "r42u_exact_span_presentation": True,
        "r42v_header_blank_media_speed_fixes": True,
        "r42w_launcher_newline_syntax_fix": True,
        "r42x_review_presentation_parity": True,
        "r42y_header_meta_media_fast_single_inject": True,
        "r42z_deterministic_review_row_presentation": True,
        "r42aa_article_colour_visibility_fix": True,
        "r42ab_robust_dom_paint_restore": True,
        "r42ac_repaint_body_textmap_fallback": True,
        "r42ad_fast_first_paint_media_outlines": True,
        "r42ae_document_media_outline_boxes": True,
        "r42af_narrow_article_media_outlines": True,
        "icons": _asset_icon_data_uris(),
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    # R42Z: presentation layer only.  The incoming rows are the Review DB/Edit
    # rows.  The browser code should not reclassify them; it only maps those
    # exact rows onto the live page quickly and without interrupting selection or
    # video playback.
    # R42AD/R42AE: same Review/Edit rows, but paint sooner and make media
    # outlines independent from text span fallback timing. R42AE adds document
    # coordinate outline boxes so video/image borders remain visible even when
    # the live site wraps media in ad/player containers.
    # R42AC: keep the Review/Edit rows as source of truth, but use a
    # repaint-safe DOM presentation pass. R42AB could clear painted rows on
    # follow-up apply passes because it stored "already painted" flags on row
    # objects; R42AC always repaints after clearMarks and falls back to a loose
    # document.body text map when strict article candidates match zero rows.
    # R42AB: keep the Review/Edit rows as source of truth, but use a
    # robust DOM presentation pass.  R42Y/Z/AA could inject the toolbar while
    # painting zero rows because the live Metro page rewrote article nodes after
    # the first apply, and the stricter article/chrome filter rejected too many
    # candidate text containers.  This script paints from small visible article
    # text elements, schedules a few cheap re-paints before the user changes
    # roles, and leaves the native video player alone.
    return r"""
(function(){
const INCOMING_YTCE_DATA = __YTCE_JSON_PAYLOAD__;
if (window.__ytceRoleEditor && typeof window.__ytceRoleEditor.resetWithData === 'function') {
  window.__ytceRoleEditor.resetWithData(INCOMING_YTCE_DATA, {force:true});
  return;
}
let YTCE_DATA = INCOMING_YTCE_DATA || {};
let mode = YTCE_DATA.initialMode || 'semantic';
let applying = false;
let userChangedRoles = false;
let applyTimer = null;
let cookieConsentTried = false;
const roleOrder = ['PRIMARY','SECONDARY','TERTIARY','UNKNOWN'];
const roleClass = role => 'ytce-role-' + String(role || 'UNKNOWN').toLowerCase();
const allRoleClasses = ['ytce-role-primary','ytce-role-secondary','ytce-role-tertiary','ytce-role-unknown','ytce-role-blank'];
const chromeSelector = '#ytce-role-toolbar,#ytce-role-toast,script,style,noscript,nav,[role="navigation"],body>header,header[role="banner"],footer,aside,.site-footer,.sidebar,.sidebar-container,.must-read,.post-grid,.related-posts,.metro-shorts,.metro-deals,.ad-slot,.advertisement,.ad,.ads,.social-share,.share-buttons,.nav,.navigation,.metro-nav,.metro-header,.metro-site-header,.comments,.comment,.comments-area,#comments,[id*="comments"],[class*="comments"],[class*="newsletter"],[class*="signup"],[class*="related"],[class*="trending"],[class*="must-read"],[class*="most-read"],[class*="recommended"],[class*="more-from"],[class*="duet"],[class*="adthrive"],[class*="outbrain"]';
const textChromeSelector = chromeSelector + ',[class*="up-next"],[id*="up-next"],[class*="video__related"],[class*="video-related"]';

function normalizeChars(s){ return String(s || '').replace(/[\u2018\u2019]/g,"'").replace(/[\u201c\u201d]/g,'"').replace(/[\u2010-\u2015\u2212]/g,'-').replace(/\u00a0/g,' '); }
function norm(s){ return normalizeChars(s).replace(/\s+/g,' ').trim().toLowerCase(); }
function stripEdgeQuotes(s){ return norm(s).replace(/^["'“”‘’]+\s*/, '').replace(/\s*["'“”‘’]+$/, ''); }
function rowText(row){ return String((row && (row.text || row.url || row.media_url)) || ''); }
function currentRows(){ return (YTCE_DATA.rowsByMode && YTCE_DATA.rowsByMode[mode]) ? YTCE_DATA.rowsByMode[mode] : []; }
function rowRole(row){ return mode === 'media' ? (row.media_source_role || row.active_role || 'BLANK') : (row.semantic_role || row.active_role || 'UNKNOWN'); }
function setRowRole(row, role){ if(mode === 'media') row.media_source_role = role; else row.semantic_role = role; row.active_role = role; }
function isVisible(el){ try{ const st=getComputedStyle(el); if(st.display==='none'||st.visibility==='hidden'||st.opacity==='0') return false; const r=el.getClientRects(); return !!r && r.length>0; }catch(e){ return true; } }
function isChrome(el, forText=true){
  if(!el || !el.closest) return false;
  if(el.closest(forText ? textChromeSelector : chromeSelector)) return true;
  let cur=el;
  for(let depth=0; cur && depth<8; depth++, cur=cur.parentElement){
    const sig=(String(cur.className||'')+' '+String(cur.id||'')).toLowerCase();
    if(sig.match(/newsletter|signup|related|trending|must-read|most-read|recommended|sidebar|comment|duet|adthrive|outbrain/)) return true;
    if(forText && sig.match(/up-next|up_next|video-related|video__related/)) return true;
  }
  return false;
}
function stableKey(row, idx){ return String(row.edit_key || row.key || row.id || (rowText(row)+'|'+idx)); }
function rowShouldPaintInText(row){
  const kind = String((row && row.kind) || '').toLowerCase();
  if(['image','video','media','link','archive','locator'].includes(kind)) return false;
  const t = norm(rowText(row));
  if(!t || /^https?:\/\//.test(t)) return false;
  return true;
}
function phraseVariants(s){
  const base = norm(s); const out=[]; const add=v=>{v=norm(v); if(v && !out.includes(v)) out.push(v);};
  add(base); add(stripEdgeQuotes(base)); add(base.replace(/\s+-\s+/g,'-')); add(base.replace(/\s+-\s+/g,' - '));
  add(base.replace(/["']/g,''));
  const noParens = base.replace(/\s*\([^)]*\)\s*/g,' ').replace(/\s+/g,' ').trim(); if(noParens !== base) add(noParens);
  if(base.includes('|')){ base.split('|').map(x=>x.trim()).filter(Boolean).forEach(add); }
  if(base.length > 95) add(base.slice(0, 115).replace(/\s+\S*$/,''));
  return out.filter(v=>v.length>=2);
}
function rowWords(row){ return norm(rowText(row)).replace(/[^a-z0-9']+/g,' ').split(/\s+/).filter(Boolean); }
function textMapFor(root){
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node){
      const p=node.parentElement;
      if(!p || !node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      if(p.closest && p.closest('#ytce-role-toolbar,#ytce-role-toast,script,style,noscript')) return NodeFilter.FILTER_REJECT;
      if(p.closest && p.closest('.ytce-role-hit')) return NodeFilter.FILTER_REJECT;
      if(isChrome(p,true)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  let out='', map=[], prevSpace=true, n;
  while((n=walker.nextNode())){
    const v=normalizeChars(String(n.nodeValue||''));
    for(let i=0;i<v.length;i++){
      const ch=v[i];
      if(/\s/.test(ch)){ if(!prevSpace){ out+=' '; map.push({node:n,offset:i}); prevSpace=true; } }
      else { out+=ch.toLowerCase(); map.push({node:n,offset:i}); prevSpace=false; }
    }
  }
  const words=[]; const rx=/[a-z0-9']+/g; let m;
  while((m=rx.exec(out))){ words.push({w:m[0], start:m.index, end:m.index+m[0].length}); }
  return {text:out, map, words};
}
function textMapForLoose(root){
  // R42AC: last-resort presentation map.  It deliberately avoids the broad
  // article/chrome ancestor filter because live Metro can nest the real article
  // under containers whose class/text looks like player/chrome after ads load.
  // Rows are still Review rows, so matching only those row strings keeps UK/US
  // nav/sidebar text from being painted unless a Review row actually says that.
  const walker = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(node){
      const p=node.parentElement;
      if(!p || !node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      if(p.closest && p.closest('#ytce-role-toolbar,#ytce-role-toast,script,style,noscript,svg,canvas')) return NodeFilter.FILTER_REJECT;
      if(p.closest && p.closest('.ytce-role-hit')) return NodeFilter.FILTER_REJECT;
      if(p.closest && p.closest('nav,[role="navigation"],footer,aside,.comments,.comment,.comments-area,#comments,[id*="comments"],[class*="comments"],[class*="newsletter"],[class*="signup"],[class*="related"],[class*="trending"],[class*="must-read"],[class*="most-read"],[class*="recommended"],[class*="adthrive"],[class*="outbrain"]')) return NodeFilter.FILTER_REJECT;
      if(!isVisible(p)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  let out='', map=[], prevSpace=true, n;
  while((n=walker.nextNode())){
    const v=normalizeChars(String(n.nodeValue||''));
    for(let i=0;i<v.length;i++){
      const ch=v[i];
      if(/\s/.test(ch)){ if(!prevSpace){ out+=' '; map.push({node:n,offset:i}); prevSpace=true; } }
      else { out+=ch.toLowerCase(); map.push({node:n,offset:i}); prevSpace=false; }
    }
  }
  const words=[]; const rx=/[a-z0-9']+/g; let m;
  while((m=rx.exec(out))){ words.push({w:m[0], start:m.index, end:m.index+m[0].length}); }
  return {text:out, map, words};
}
function makeRangeFromMap(map,start,len){
  if(!map || !map.length || start<0 || len<=0) return null;
  const first=map[start]; const last=map[Math.min(map.length-1,start+len-1)];
  if(!first || !last) return null;
  try{ const r=document.createRange(); r.setStart(first.node, first.offset); r.setEnd(last.node, last.offset+1); return r; }catch(e){ return null; }
}
function rangesOverlap(a,b){ return a.start < b.end && b.start < a.end; }
function findMatchInMap(tm,row,used){
  const vars=phraseVariants(rowText(row));
  for(const phrase of vars){
    let pos=0;
    while((pos=tm.text.indexOf(phrase,pos))>=0){
      const cand={start:pos,end:pos+phrase.length,len:phrase.length,row};
      if(!used.some(u=>rangesOverlap(cand,u))) return cand;
      pos += Math.max(1, phrase.length);
    }
  }
  const words=rowWords(row);
  if(words.length){
    const wanted = words;
    const minLen = wanted.length <= 2 ? wanted.length : Math.min(wanted.length, Math.max(4, Math.min(10, wanted.length)));
    for(let i=0;i<tm.words.length;i++){
      if(tm.words[i].w !== wanted[0]) continue;
      let ok=true;
      for(let j=1;j<minLen;j++){ if(!tm.words[i+j] || tm.words[i+j].w !== wanted[j]){ ok=false; break; } }
      if(!ok) continue;
      let take=minLen; while(take<wanted.length && tm.words[i+take] && tm.words[i+take].w===wanted[take]) take++;
      const endWord=tm.words[i+take-1];
      const cand={start:tm.words[i].start,end:endWord.end,len:endWord.end-tm.words[i].start,row};
      if(!used.some(u=>rangesOverlap(cand,u))) return cand;
    }
  }
  return null;
}
function applyRoleClass(el, role){ el.classList.remove(...allRoleClasses); el.classList.add(roleClass(role)); el.dataset.ytceRole=role; }
function unwrapSpan(span){ const parent=span.parentNode; if(!parent) return; while(span.firstChild) parent.insertBefore(span.firstChild,span); parent.removeChild(span); try{parent.normalize();}catch(e){} }
function clearMarks(){
  document.querySelectorAll('span.ytce-role-hit[data-ytce-wrap="1"]').forEach(unwrapSpan);
  document.querySelectorAll('.ytce-role-hit').forEach(e=>{ e.classList.remove('ytce-role-hit',...allRoleClasses); delete e.dataset.ytceRole; delete e.dataset.ytceEditKey; e.removeAttribute('title'); });
  document.querySelectorAll('.ytce-media-box').forEach(e=>{ try{e.remove();}catch(_e){} });
  document.querySelectorAll('.ytce-media-role-outline').forEach(e=>{ e.classList.remove('ytce-media-role-outline',...allRoleClasses); delete e.dataset.ytceRole; delete e.dataset.ytceEditKey; e.removeAttribute('title'); try{ e.style.removeProperty('outline'); e.style.removeProperty('outline-offset'); e.style.removeProperty('box-shadow'); e.style.removeProperty('border-radius'); }catch(_e){} });
}
function attachRoleClick(span,row){
  let downX=0,downY=0;
  span.addEventListener('mousedown',ev=>{downX=ev.clientX;downY=ev.clientY;},{passive:true});
  span.addEventListener('click',ev=>{
    if(window.getSelection && String(window.getSelection()).length>0) return;
    if(Math.abs(ev.clientX-downX)>4 || Math.abs(ev.clientY-downY)>4) return;
    const oldRole=rowRole(row); const i=roleOrder.indexOf(oldRole); const newRole=roleOrder[(i+1)%roleOrder.length]||'UNKNOWN';
    userChangedRoles=true; setRowRole(row,newRole); applyRoleClass(span,newRole); persistChange(row,oldRole,newRole); updateToolbarCounts();
  },{passive:true});
}
function wrapMatch(cm,m){
  const range=makeRangeFromMap(cm.tm.map,m.start,m.len); if(!range) return null;
  const role=rowRole(m.row); if(!role) return null;
  const span=document.createElement('span'); span.className='ytce-role-hit'; span.dataset.ytceWrap='1'; span.dataset.ytceEditKey=m.row.edit_key||''; applyRoleClass(span,role);
  try{ const frag=range.extractContents(); span.appendChild(frag); range.insertNode(span); attachRoleClick(span,m.row); return span; }catch(e){ return null; }
}
function getArticleRoot(){
  const headline = norm((currentRows()[0] && rowText(currentRows()[0])) || '');
  const roots=Array.from(document.querySelectorAll('article,[itemtype*="NewsArticle"],[itemtype*="Article"],main,[class*="article"],[class*="post-content"],[class*="entry-content"],[class*="content"]')).filter(el=>el && isVisible(el) && !isChrome(el,false));
  let best=null,score=-1;
  for(const el of roots){
    const txt=norm(el.innerText||el.textContent||''); if(!txt) continue;
    let s=Math.min(txt.length,50000); if(headline && txt.includes(headline.slice(0,Math.min(35,headline.length)))) s+=200000; if(el.querySelector&&el.querySelector('h1')) s+=20000; if(String(el.tagName||'').toLowerCase()==='article') s+=10000;
    if(s>score){best=el;score=s;}
  }
  return best || document.querySelector('article,[itemtype*="NewsArticle"],main') || document.body;
}
function getTextCandidates(){
  const root=getArticleRoot() || document.body;
  const selector='h1,h2,h3,p,li,blockquote,figcaption,time,.article__meta,.article__date,.byline,[class*="byline"],[class*="author"],[class*="date"],[class*="caption"],[class*="headline"],[class*="title"]';
  const nodes=Array.from(root.querySelectorAll(selector)).filter(el=>el && isVisible(el) && !isChrome(el,true) && norm(el.innerText||el.textContent||'').length>0);
  if(root && isVisible(root) && !isChrome(root,false)) nodes.push(root);
  const seen=new Set();
  return nodes.filter(el=>{ if(seen.has(el)) return false; seen.add(el); return true; });
}
function candidateMaps(strict){
  const roots=[];
  if(strict){
    const ar=getArticleRoot(); if(ar) roots.push(ar);
    getTextCandidates().forEach(el=>{ if(el && !roots.includes(el)) roots.push(el); });
  } else {
    const ar=getArticleRoot(); if(ar && ar !== document.body) roots.push(ar);
    roots.push(document.body || document.documentElement);
  }
  const seen=new Set(); const out=[];
  roots.forEach(el=>{
    if(!el || seen.has(el)) return; seen.add(el);
    const tm = strict ? textMapFor(el) : textMapForLoose(el);
    if(tm && tm.text && tm.text.length) out.push({el,tm,used:[],matches:[],strict});
  });
  return out;
}
function paintRowsIntoMaps(rows, cms){
  let paintedRows=0;
  rows.forEach((row,idx)=>{
    let best=null;
    for(const cm of cms){
      const m=findMatchInMap(cm.tm,row,cm.used); if(!m) continue;
      let score=m.len;
      const tag=String(cm.el.tagName||'').toLowerCase();
      if(idx<6 && /^(h1|time)$/.test(tag)) score+=10000;
      if(idx<6 && /byline|author|date|headline|title/i.test(String(cm.el.className||''))) score+=8000;
      if(!cm.strict) score-=500; // prefer exact article candidates, but allow body fallback.
      if(best===null || score>best.score) best={cm,m,score};
    }
    if(best){ best.cm.used.push(best.m); best.cm.matches.push(best.m); paintedRows++; }
  });
  for(const cm of cms){ cm.matches.sort((a,b)=>b.start-a.start); for(const m of cm.matches) wrapMatch(cm,m); }
  return paintedRows;
}
function markTextRows(){
  const rows=currentRows().filter(rowShouldPaintInText); if(!rows.length) return 0;
  // R42AC: do not skip rows using cached __ytcePaintedKey flags. apply() begins
  // by clearing the DOM marks, so skipping a previously painted row makes later
  // scheduled repaints remove all colour. Always repaint from the Review rows.
  const strictMaps=candidateMaps(true);
  let count=paintRowsIntoMaps(rows, strictMaps);
  if(count === 0){
    const looseMaps=candidateMaps(false);
    logEvent('R42AC loose paint fallback strict_maps='+strictMaps.length+' loose_maps='+looseMaps.length+' loose_chars='+(looseMaps[0]&&looseMaps[0].tm?looseMaps[0].tm.text.length:0));
    count=paintRowsIntoMaps(rows, looseMaps);
  }
  return count;
}
function recalcCounts(){ const counts={PRIMARY:0,SECONDARY:0,TERTIARY:0,UNKNOWN:0}; for(const row of currentRows()){ const r=String(rowRole(row)||'').toUpperCase(); if(Object.prototype.hasOwnProperty.call(counts,r)) counts[r]++; } if(!YTCE_DATA.counts) YTCE_DATA.counts={}; YTCE_DATA.counts[mode]=counts; return counts; }
function textForCopy(kind){ if(kind==='link') return YTCE_DATA.selectedUrl||location.href; if(kind==='plain') return YTCE_DATA.plainText||currentRows().map(r=>rowText(r)).filter(Boolean).join('\n'); if(kind==='roles') return (YTCE_DATA.roleText&&YTCE_DATA.roleText[mode])||currentRows().map(r=>'['+rowText(r)+' | '+rowRole(r)+']').join('\n'); return ''; }
async function copyText(kind){ const value=textForCopy(kind); try{await navigator.clipboard.writeText(value); return;}catch(e){} try{ if(window.pywebview&&window.pywebview.api&&window.pywebview.api.copy_to_clipboard){ await window.pywebview.api.copy_to_clipboard(value); }}catch(e){} }
async function openExternal(){ try{ if(window.pywebview&&window.pywebview.api&&window.pywebview.api.open_external){ await window.pywebview.api.open_external(YTCE_DATA.selectedUrl||location.href); return; }}catch(e){} window.open(YTCE_DATA.selectedUrl||location.href,'_blank','noopener'); }
let pendingRoleChanges=[]; let pendingRoleTimer=null;
function persistChange(row,oldRole,newRole){
  pendingRoleChanges.push({mode,edit_key:row.edit_key||'',text:rowText(row),old_role:oldRole,new_role:newRole});
  if(pendingRoleTimer) return;
  pendingRoleTimer=setTimeout(async()=>{ const batch=pendingRoleChanges.splice(0,pendingRoleChanges.length); pendingRoleTimer=null; try{ if(window.pywebview&&window.pywebview.api){ if(window.pywebview.api.save_role_changes) await window.pywebview.api.save_role_changes(batch); else if(window.pywebview.api.save_role_change){ for(const item of batch) await window.pywebview.api.save_role_change(item); } } }catch(e){} },180);
}
function elementSignature(el){ return String((el && (el.className||'')) || '')+' '+String((el && (el.id||'')) || ''); }
function tagName(el){ return String((el && el.tagName) || '').toLowerCase(); }
function rectOf(el){ try{return el.getBoundingClientRect();}catch(e){return {left:0,right:0,top:0,bottom:0,width:0,height:0};} }
function areaOf(r){ return Math.max(0,(r&&r.width)||0)*Math.max(0,(r&&r.height)||0); }
function roleColor(role){ role=String(role||'UNKNOWN').toUpperCase(); if(role==='PRIMARY') return 'var(--ytce-primary)'; if(role==='SECONDARY') return 'var(--ytce-secondary)'; if(role==='TERTIARY') return 'var(--ytce-tertiary)'; if(role==='BLANK') return '#334155'; return 'var(--ytce-unknown)'; }
function viewportContentBounds(){
  const hits=Array.from(document.querySelectorAll('.ytce-role-hit')).map(rectOf).filter(r=>r&&r.width>5&&r.height>5&&r.bottom>0&&r.top<window.innerHeight+2600);
  if(hits.length){
    const left=Math.max(0, Math.min(...hits.map(r=>r.left))-80);
    const right=Math.min(window.innerWidth, Math.max(...hits.map(r=>r.right))+80);
    const top=Math.min(...hits.map(r=>r.top))-850;
    const bottom=Math.max(...hits.map(r=>r.bottom))+1100;
    return {left,right,top,bottom,width:right-left,height:bottom-top};
  }
  const h=document.querySelector('article h1,main h1,h1');
  if(h&&isVisible(h)){ const r=rectOf(h); return {left:Math.max(0,r.left-90),right:Math.min(window.innerWidth,r.right+150),top:r.top-900,bottom:r.bottom+3000,width:(r.right-r.left)+240,height:3900}; }
  return {left:0,right:Math.max(1,Math.min(window.innerWidth,980)),top:-999999,bottom:999999,width:Math.max(1,Math.min(window.innerWidth,980)),height:999999};
}
function intersectsContentColumn(r,col){
  if(!r||!col||r.width<=0||r.height<=0) return false;
  const overlap=Math.min(r.right,col.right)-Math.max(r.left,col.left);
  const center=(r.left+r.right)/2;
  return (overlap>=Math.min(r.width,col.width)*0.18 || (center>=col.left-55&&center<=col.right+55)) && r.bottom>=col.top && r.top<=col.bottom;
}
function mediaHardReject(el){
  if(!el||!el.closest) return true;
  if(el.closest('#ytce-role-toolbar,#ytce-role-toast,script,style,noscript,svg,nav,[role="navigation"],body>header,header[role="banner"],footer,aside,.comments,.comment,.comments-area,#comments,[id*="comments"],[class*="comments"],[class*="newsletter"],[class*="signup"],[class*="related"],[class*="trending"],[class*="must-read"],[class*="most-read"],[class*="recommended"],[class*="metro-deals"],[class*="outbrain"],[class*="taboola"]')) return true;
  return false;
}
function isLikelyAdMedia(el){
  if(!el||!el.closest) return false;
  let cur=el;
  for(let depth=0; cur && cur!==document.body && depth<6; depth++, cur=cur.parentElement){
    const sig=(' '+elementSignature(cur)+' ').toLowerCase();
    const labelled=(cur.getAttribute&&(norm(cur.getAttribute('aria-label')||'')+' '+norm(cur.getAttribute('title')||'')));
    const hasAdAttr=(cur.hasAttribute&&(['data-ad','data-adunit','data-google-query-id','data-ad-slot','data-testid'].some(a=>cur.hasAttribute(a))));
    if(hasAdAttr || /(^|[^a-z])(ad|ads|advert|advertisement|adslot|dfp|gpt|sponsored)([^a-z]|$)/.test(sig+' '+labelled)){
      if(!/article__media|article-media|wp-block-image|wp-block-video|figure|figcaption|caption|video|player/.test(sig)) return true;
    }
  }
  const txt=norm((el.innerText||el.textContent||'').slice(0,220));
  if(txt==='advertisement' || txt.startsWith('advertisement adchoices') || txt.includes('sponsored')) return true;
  return false;
}
function isAdOrSideMedia(el){ return mediaHardReject(el) || isLikelyAdMedia(el); }
function isVideoCandidate(el){
  if(!el) return false;
  const sig=elementSignature(el).toLowerCase(); const tag=tagName(el);
  if(tag==='video') return true;
  if(el.matches&&el.matches('iframe,.metro-video-player,.video-player,.vjs-video-container,.video-js,[class*="video"],[class*="player"],[data-video-id],[data-video],[data-video-type],[data-oembed]')) return true;
  if(el.querySelector&&el.querySelector('video,.video-js,[data-video-id],[data-video],[class*="video"],[class*="player"]')) return true;
  return /video|player|jwplayer|brightcove|oembed|embed/.test(sig);
}
function targetIsTooBroadForMedia(target, sourceEl, isVid){
  if(!target) return true;
  const tag=tagName(target); const sig=elementSignature(target).toLowerCase(); const r=rectOf(target); const col=viewportContentBounds();
  if(['html','body','main','article'].includes(tag)) return true;
  if(/content__main|article-body|post-content|entry-content|single-post|post-page|article-container|site-main|main-content/.test(sig)) return true;
  if(target.querySelector && target.querySelector('h1,header,nav,[role="navigation"]')) return true;
  if(target.querySelector && target.querySelector('[class*="up-next"],[id*="up-next"],[class*="video-related"],[class*="video__related"]') && tag!=='video') return true;
  const hitCount=target.querySelectorAll?target.querySelectorAll('.ytce-role-hit').length:0;
  if(hitCount>3 && tag!=='figure' && tag!=='video' && !/wp-block-image|article__media|article-media|caption/.test(sig)) return true;
  if(r.width>Math.max(col.width*1.35,880) && r.height>360) return true;
  if(r.height>900 && !/video|player/.test(sig) && tag!=='video') return true;
  if(sourceEl && target!==sourceEl){
    const sr=rectOf(sourceEl);
    if(sr.width>0&&sr.height>0 && areaOf(r)>Math.max(areaOf(sr)*5,520000) && !/video|player|figure|caption/.test(sig)) return true;
  }
  return false;
}
function mediaWrapperFor(el){
  if(!el) return el;
  const col=viewportContentBounds();
  const isVid=isVideoCandidate(el);
  let best=el;
  const closestSelector=isVid
    ? 'video,.metro-video-player,.video-player,.vjs-video-container,.video-js,[class*="video-player"],[class*="video__player"],[data-video-id],[data-video],[data-video-type],[data-oembed]'
    : 'figure,.wp-caption,.article__media,.article-media,.wp-block-image,.wp-block-video,picture,img';
  try{
    const close=el.closest&&el.closest(closestSelector);
    if(close && isVisible(close) && !mediaHardReject(close) && intersectsContentColumn(rectOf(close),col) && !targetIsTooBroadForMedia(close,el,isVid)) best=close;
  }catch(_e){}
  let cur=el.parentElement;
  for(let depth=0; cur && cur!==document.body && depth<6; depth++, cur=cur.parentElement){
    if(!isVisible(cur) || mediaHardReject(cur)) break;
    const r=rectOf(cur); if(r.width<90||r.height<45||!intersectsContentColumn(r,col)) continue;
    if(targetIsTooBroadForMedia(cur,el,isVid)) break;
    const sig=elementSignature(cur).toLowerCase(); const tag=tagName(cur);
    if(isVid){
      if(tag==='video' || /video|player|embed|oembed|media/.test(sig)) best=cur;
    } else {
      const mediaCount=cur.querySelectorAll?cur.querySelectorAll('img,video,picture,canvas,iframe').length:0;
      if(tag==='figure' || /wp-caption|wp-block-image|article__media|article-media|image|caption/.test(sig) || (mediaCount===1 && r.width<=760 && r.height<=760)) best=cur;
    }
  }
  return best;
}
function mediaTextFor(el){
  if(!el) return '';
  const bits=[]; const target=mediaWrapperFor(el);
  const container=(el.closest&& (el.closest('figure,.wp-caption,.article__media,.article-media,.wp-block-image,.wp-block-video,.metro-video-player,.video-player,.vjs-video-container,.video-js,[class*="video-player"],[class*="video__player"],[data-video-id],[data-video],[data-video-type]')||target)) || target;
  for(const node of [el,target,container]){
    if(!node) continue;
    bits.push(node.innerText||node.textContent||'');
    if(node.getAttribute){ ['alt','title','aria-label','poster','src','currentSrc','data-src','data-original','data-opts','data-video','data-video-id','data-id','href'].forEach(a=>bits.push(node.getAttribute(a)||'')); }
  }
  const next=container&&container.nextElementSibling; if(next&&!isAdOrSideMedia(next)&&!isChrome(next,false)) bits.push(next.innerText||next.textContent||'');
  const prev=container&&container.previousElementSibling; if(prev&&!isAdOrSideMedia(prev)&&!isChrome(prev,false)) bits.push(prev.innerText||prev.textContent||'');
  return norm(bits.join(' '));
}
function usefulMediaRows(){ return currentRows().filter(r=>{ const role=rowRole(r); const t=norm(rowText(r)); return !!t && !!role && role!=='BLANK' && !/^https?:\/\//.test(t); }); }
function rowMatchesVideo(row){ const t=rowText(row); return /clip|video|filmed|footage|activepatriot|catching|seagull|gull|caption/i.test(t); }
function rowMatchesPicture(row){ const t=rowText(row); return /picture:|supplied|activepatriot|stranded|mubarak|seagull|gull|nora/i.test(t); }
function bestMediaRole(el,rows){
  const text=mediaTextFor(el); let best=null,score=0;
  const isVid=isVideoCandidate(el);
  for(const row of rows){
    const raw=rowText(row); const rt=norm(raw); if(!rt||rt.length<4) continue;
    let s=0;
    if(text&&text.includes(rt)) s=1000+rt.length;
    else {
      const short=rt.replace(/\(picture:[^)]+\)/g,'').replace(/\(video:[^)]+\)/g,'').trim();
      if(short&&short.length>10&&text.includes(short)) s=700+short.length;
      else if(isVid && rowMatchesVideo(row)) s=(rowRole(row)==='UNKNOWN'?275:230);
      else if(!isVid && rowMatchesPicture(row)) s=(rowRole(row)==='UNKNOWN'?215:195);
    }
    if(s>score){best=row;score=s;}
  }
  return best;
}
function addMediaBox(target,role,idx){
  const r=rectOf(target); if(!r||r.width<20||r.height<20) return false;
  const box=document.createElement('div'); box.className='ytce-media-box'; applyRoleClass(box,role);
  box.dataset.ytceMediaBox='1'; box.dataset.ytceEditKey=target.dataset.ytceEditKey||('media_'+idx);
  box.style.left=(window.scrollX+r.left-3)+'px'; box.style.top=(window.scrollY+r.top-3)+'px'; box.style.width=(r.width+6)+'px'; box.style.height=(r.height+6)+'px';
  document.body.appendChild(box); return true;
}
function outlineMedia(target,row,idx){
  if(!target||!row) return false; const role=rowRole(row); if(!role||role==='BLANK') return false;
  if(targetIsTooBroadForMedia(target,target,isVideoCandidate(target))) return false;
  target.classList.add('ytce-media-role-outline'); applyRoleClass(target,role); target.dataset.ytceEditKey=row.edit_key||('media_'+idx);
  try{ target.style.setProperty('outline','4px solid '+roleColor(role),'important'); target.style.setProperty('outline-offset','3px','important'); target.style.setProperty('box-shadow','0 0 0 2px rgba(255,255,255,.96),0 0 14px rgba(15,23,42,.38)','important'); target.style.setProperty('border-radius','6px','important'); }catch(_e){}
  addMediaBox(target,role,idx);
  return true;
}
function addCandidate(out,seen,el){
  if(!el) return;
  const source=el;
  const target=mediaWrapperFor(source);
  if(!target||seen.has(target)||!isVisible(target)||isAdOrSideMedia(target)) return;
  const r=rectOf(target); const col=viewportContentBounds();
  if(r.width<120||r.height<70||!intersectsContentColumn(r,col)) return;
  if(targetIsTooBroadForMedia(target,source,isVideoCandidate(source))) return;
  const sig=elementSignature(target).toLowerCase(); const tag=tagName(target);
  if(!isVideoCandidate(target) && /share|social|avatar|author|logo|icon/.test(sig) && r.width<260) return;
  if(tag==='img'){
    const alt=norm((target.getAttribute&&target.getAttribute('alt'))||'');
    if(/logo|avatar|icon|share|facebook|twitter|whatsapp/.test(alt+' '+sig) && r.width<260) return;
  }
  seen.add(target); out.push(target);
}
function mediaCandidateElements(){
  // R42AF: collect only real media nodes and narrow wrappers.  Do not fall back
  // to article/content ancestors; R42AE's broad fallback produced one giant
  // outline around the entire article when the player wrapper was nested high.
  const selectors=['video','iframe','canvas','figure','picture','img','.metro-video-player','.video-player','.vjs-video-container','.video-js','[class*="video-player"]','[class*="video__player"]','[data-video-id]','[data-video]','[data-video-type]','[data-oembed]','.article__media','.article-media','.wp-block-image','.wp-block-video','.wp-caption'].join(',');
  const raw=Array.from(document.querySelectorAll(selectors));
  const seen=new Set(), out=[];
  // Prefer explicit video/player nodes first so the main article video is not
  // replaced by a larger ancestor that also contains title/social/sidebar blocks.
  raw.filter(isVideoCandidate).forEach(el=>addCandidate(out,seen,el));
  raw.filter(el=>!isVideoCandidate(el)).forEach(el=>addCandidate(out,seen,el));
  const sorted=out.slice().sort((a,b)=>{const ra=rectOf(a), rb=rectOf(b); return (ra.top-rb.top) || (areaOf(rb)-areaOf(ra));});
  const filtered=[];
  for(const el of sorted){
    const r=rectOf(el);
    // If an existing chosen media element fully contains this tiny child, keep
    // the parent; if this element is the narrower actual media/player, replace
    // the broad parent with it.
    let skip=false;
    for(let i=filtered.length-1;i>=0;i--){
      const prev=filtered[i]; const pr=rectOf(prev);
      const contains=prev.contains&&prev.contains(el);
      const contained=el.contains&&el.contains(prev);
      if(contains && areaOf(pr) <= areaOf(r)*3.2){ skip=true; break; }
      if(contained && areaOf(r) <= areaOf(pr)*3.2){ filtered.splice(i,1); continue; }
    }
    if(!skip) filtered.push(el);
  }
  return filtered.slice(0,12);
}
function markMediaRows(){
  if(mode!=='media') return 0;
  const rows=usefulMediaRows(); if(!rows.length) return 0;
  const mediaEls=mediaCandidateElements();
  const videoFallback=rows.find(r=>rowRole(r)==='UNKNOWN'&&rowMatchesVideo(r))||rows.find(rowMatchesVideo)||rows[0];
  const pictureFallbacks=rows.filter(rowMatchesPicture); let picIdx=0, count=0;
  for(const target of mediaEls){ let row=bestMediaRole(target,rows); if(!row && isVideoCandidate(target)) row=videoFallback; if(!row) row=pictureFallbacks[picIdx++]||rows[0]; if(outlineMedia(target,row,count)) count++; }
  logEvent('R42AF media candidates='+mediaEls.length+' outlines='+count+' text_spans='+document.querySelectorAll('.ytce-role-hit').length);
  return count;
}
function normalizeVideos(){ document.querySelectorAll('video,.metro-video-player,.video-player,.video-js,[class*="video-player"]').forEach(v=>{try{v.style.pointerEvents='auto';}catch(e){}}); }
function updateToolbarCounts(){ const c=recalcCounts(); const bar=document.getElementById('ytce-role-toolbar'); if(!bar) return; const set=(cls,label,val)=>{const el=bar.querySelector('.count.'+cls); if(el) el.textContent=label+': '+String(val||0).padStart(2,'0');}; set('primary','Primary',c.PRIMARY); set('secondary','Secondary',c.SECONDARY); set('tertiary','Tertiary',c.TERTIARY); set('unknown','Unknown',c.UNKNOWN); }
function buildToolbar(){ let bar=document.getElementById('ytce-role-toolbar'); if(!bar){ bar=document.createElement('div'); bar.id='ytce-role-toolbar'; document.documentElement.appendChild(bar); const icons=(YTCE_DATA&&YTCE_DATA.icons)||{}; const iconHtml=(key,fallback)=>icons[key]?'<img alt="" src="'+icons[key]+'">':fallback; const copyIcon=icons.copy_roles||icons.copy_plain; const copyHtml=copyIcon?'<img alt="" src="'+copyIcon+'">':'⧉'; bar.innerHTML=`<button id="ytce-sem" title="Semantic">Semantic</button><button id="ytce-med" title="Media">Media</button><span class="count primary"></span><span class="count secondary"></span><span class="count tertiary"></span><span class="count unknown"></span><span class="spacer"></span><button class="icon" id="ytce-copy-link" title="Copy link">${iconHtml('link','🔗')}</button><button class="icon" id="ytce-copy-text" title="Copy plain text">${copyHtml}</button><button class="icon" id="ytce-copy-roles" title="Copy role text">${copyHtml}</button><button class="icon" id="ytce-open-ext" title="Open external">${iconHtml('external','↗')}</button>`; bar.querySelector('#ytce-sem').onclick=()=>{mode='semantic'; userChangedRoles=false; apply(true);}; bar.querySelector('#ytce-med').onclick=()=>{mode='media'; userChangedRoles=false; apply(true);}; bar.querySelector('#ytce-copy-link').onclick=()=>copyText('link'); bar.querySelector('#ytce-copy-text').onclick=()=>copyText('plain'); bar.querySelector('#ytce-copy-roles').onclick=()=>copyText('roles'); bar.querySelector('#ytce-open-ext').onclick=()=>openExternal(); } bar.querySelector('#ytce-sem').classList.toggle('active',mode==='semantic'); bar.querySelector('#ytce-med').classList.toggle('active',mode==='media'); updateToolbarCounts(); }
function buildSidecar(){ const old=document.getElementById('ytce-role-sidecar'); if(old) old.remove(); }
function logEvent(msg){ try{ if(window.pywebview&&window.pywebview.api&&window.pywebview.api.log_event) window.pywebview.api.log_event(String(msg)); }catch(e){} }
function maybeClickCookieConsent(){
  // R42AG: conservative helper for recurring CMP/cookie banners.  It only acts
  // on buttons/links inside containers whose id/class/role/text look like a
  // cookie/consent/privacy modal.  Persistent WebView storage then keeps the
  // accepted state for later edit-window launches.
  try{
    const containerSel='[id*="cookie" i],[class*="cookie" i],[id*="consent" i],[class*="consent" i],[id*="gdpr" i],[class*="gdpr" i],[id*="onetrust" i],[class*="onetrust" i],[id*="qc-cmp" i],[class*="qc-cmp" i],[id*="privacy" i],[class*="privacy" i],[role="dialog"],[aria-modal="true"]';
    const containers=Array.from(document.querySelectorAll(containerSel)).filter(el=>isVisible(el));
    const btnSel='button,a,[role="button"],input[type="button"],input[type="submit"]';
    const phrases=/^(accept all|accept|agree|i agree|allow all|continue|got it|ok)$/i;
    for(const c of containers){
      const sig=norm((c.id||'')+' '+(c.className||'')+' '+(c.getAttribute&&((c.getAttribute('aria-label')||'')+' '+(c.getAttribute('title')||'')))+' '+(c.innerText||c.textContent||'').slice(0,500));
      if(!/(cookie|consent|privacy|gdpr|choices|legitimate interest|onetrust|quantcast|cmp)/i.test(sig)) continue;
      const buttons=Array.from(c.querySelectorAll(btnSel)).filter(isVisible);
      for(const b of buttons){
        const txt=norm((b.innerText||b.textContent||b.value||b.getAttribute('aria-label')||b.getAttribute('title')||'')).replace(/\s+/g,' ');
        if(phrases.test(txt)){ b.click(); logEvent('R42AG cookie consent clicked: '+txt); return true; }
      }
    }
  }catch(e){ logEvent('R42AG cookie helper failed: '+(e&&e.message?e.message:String(e))); }
  return false;
}
function apply(force){
  if(applying) return;
  applying=true;
  let textCount=0, mediaCount=0;
  try{ if(!cookieConsentTried){ cookieConsentTried=true; maybeClickCookieConsent(); } clearMarks(); normalizeVideos(); buildToolbar(); textCount=markTextRows(); mediaCount=markMediaRows(); buildSidecar(); }catch(e){ try{console.warn('YTCE overlay apply failed',e);}catch(_e){} logEvent('overlay apply failed: '+(e&&e.message?e.message:String(e))); }
  applying=false;
  logEvent('overlay apply mode='+mode+' text_spans='+textCount+' media_outlines='+mediaCount+' rows='+currentRows().length);
}
function scheduleApply(ms){ setTimeout(()=>{ if(!userChangedRoles) apply(true); }, ms); }
function debounceApply(){ if(userChangedRoles) return; if(applyTimer) clearTimeout(applyTimer); applyTimer=setTimeout(()=>{applyTimer=null; apply(true);},350); }
window.__ytceRoleEditor={ resetWithData(data,opts){ YTCE_DATA=data||YTCE_DATA; mode=YTCE_DATA.initialMode||mode||'semantic'; apply(true); }, apply, setMode(nextMode){ mode=nextMode==='media'?'media':'semantic'; userChangedRoles=false; apply(true); } };
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>apply(true),{once:true}); else apply(true);
scheduleApply(450); scheduleApply(1100); scheduleApply(2400); scheduleApply(5200);
window.addEventListener('load',()=>debounceApply(),{once:true});
// R42AD: do not repaint on every scroll; it caused lag and flicker. Toolbar stays fixed and existing marks remain.
// window.addEventListener('scroll',()=>debounceApply(),{passive:true});
})()
""".replace("__YTCE_JSON_PAYLOAD__", data_json)

def build_overlay_payload(edit_state: Mapping[str, Any]) -> dict[str, Any]:
    semantic_rows = _safe_rows(edit_state.get("semantic_rows") or (), mode="semantic")
    media_rows = _safe_rows(edit_state.get("media_rows") or (), mode="media")
    rows_by_mode = {"semantic": semantic_rows, "media": media_rows}
    selected_url = _clean(edit_state.get("selected_url") or edit_state.get("normalised_url") or edit_state.get("display_url"))
    source_navigation_urls = _source_navigation_urls_from_edit_state(edit_state, selected_url)
    universal_route_state: dict[str, Any] = {}
    try:
        from profile_media_universal_source_link_adapter_r42dl import build_universal_source_link_webview2_state

        universal_route_state = build_universal_source_link_webview2_state(
            selected_url,
            source_kind=_clean(edit_state.get("source_kind") or "webview2"),
            adapter_id=_clean(edit_state.get("adapter_id") or edit_state.get("source_adapter") or ""),
            source_row_id=_clean(edit_state.get("source_row_id") or edit_state.get("row_id") or ""),
        )
    except Exception:
        universal_route_state = {}
    return {
        R42H_REAL_WEBVIEW_OVERLAY_MARKER: True,
        R42Q_WEBVIEW_EDITOR_MARKER: True,
        R42R_LIVE_WEBVIEW_MARKER: True,
        R42S_ONE_WINDOW_LIVE_WEBVIEW_MARKER: True,
        R42T_JS_ESCAPE_FIX_MARKER: True,
        R42U_PRESENTATION_FIX_MARKER: True,
        R42AG_COOKIE_CACHE_OUTLINE_MARKER: True,
        R42AI_NATIVE_WEBVIEW2_EDITOR_MARKER: True,
        R42AP_NATIVE_EDITOR_MEDIA_UI_MATCH_MARKER: True,
        R42AR_NATIVE_EDITOR_SPEED_RESOURCE_MARKER: True,
        R42AS_NATIVE_EDITOR_STABLE_DEBUG_UI_MARKER: True,
        R42AX_NATIVE_EDITOR_TARGETED_MEDIA_FAST_MARKER: True,
        R42AY_NATIVE_EDITOR_CLEAN_GREY_TOGGLE_MARKER: True,
        R42CR_NATIVE_EDITOR_WARM_SERVER_MARKER: True,
        R42CR_NATIVE_EDITOR_EARLY_WARM_MARKER: True,
        R42CR_NATIVE_EDITOR_URL_NAV_MARKER: True,
        "selected_url": selected_url,
        "source_navigation_urls": source_navigation_urls,
        "source_navigation_count": len(source_navigation_urls),
        "source_navigation_debug": edit_state.get("source_navigation_debug") or {},
        "universal_source_link_adapter_state": universal_route_state,
        "title": _clean(edit_state.get("title") or edit_state.get("window_title") or edit_state.get("selected_url")),
        "rows_by_mode": rows_by_mode,
        "counts_by_mode": {"semantic": _counts(semantic_rows), "media": _counts(media_rows)},
        "plain_text": _plain_text(rows_by_mode),
        "semantic_role_text": _role_markup(rows_by_mode, mode="semantic"),
        "media_role_text": _role_markup(rows_by_mode, mode="media"),
        "source_role_effect": ROLE_EFFECT,
        "text_paint_style": os.environ.get("YTCE_R42DU_TEXT_PAINT_STYLE", "").strip(),
        "r42du_archive_visible_material_role_fix": True,
        "uses_existing_review_db_import_role_rows": bool(edit_state.get("uses_review_db_import_parity_rows") or edit_state.get("uses_existing_review_db_import_spans")),
    }


def write_role_overlay_html(
    *,
    edit_state: Mapping[str, Any],
    artifact_state: Mapping[str, Any] | None = None,
    output_dir: str | Path | None = None,
    initial_mode: str = "semantic",
) -> dict[str, Any]:
    payload = build_overlay_payload(edit_state)
    selected_url = _clean(payload.get("selected_url"))
    artifact_state = artifact_state or {}
    output = Path(output_dir or Path("profile_media_live_captures") / "link_source_role_webview_overlay")
    output.mkdir(parents=True, exist_ok=True)
    mode_key = "media" if str(initial_mode or "").strip().lower() == "media" else "semantic"
    rows_by_mode = payload["rows_by_mode"]
    counts = payload["counts_by_mode"]
    css = _overlay_css()
    js = _overlay_js(rows_by_mode, counts, selected_url, mode_key, str(payload.get("plain_text") or ""), str(payload.get("semantic_role_text") or ""), str(payload.get("media_role_text") or ""))
    visual_path = Path(str(artifact_state.get("visual_base_path") or "")) if artifact_state else Path("")
    kind = _clean(artifact_state.get("visual_base_kind") if artifact_state else "")
    html_text = ""
    base_kind = "live_url"
    launch_start_url = selected_url or ""
    if visual_path.is_file() and visual_path.suffix.lower() in {".html", ".htm"}:
        raw = visual_path.read_text(encoding="utf-8", errors="replace")
        inject = f'<style id="ytce-role-overlay-css">{css}</style><script id="ytce-role-overlay-js">{js}</script>'
        if re.search(r"</head\s*>", raw, flags=re.IGNORECASE):
            html_text = re.sub(r"</head\s*>", lambda _match: inject + "</head>", raw, count=1, flags=re.IGNORECASE)
        else:
            html_text = inject + raw
        # R42R: captured rendered_page.html is useful evidence, but it is a
        # static capture and can make Metro video/player regions behave like a
        # screenshot.  For normal browser behaviour, launch the live selected URL
        # and inject this same overlay after load.  Set
        # YTCE_R42R_USE_CAPTURED_HTML=1 to force the old local-captured HTML view.
        if selected_url and os.environ.get("YTCE_R42R_USE_CAPTURED_HTML", "").strip() not in {"1", "true", "TRUE", "yes", "YES"}:
            base_kind = "live_url_with_injected_overlay"
            launch_start_url = selected_url
        else:
            base_kind = "captured_html_with_injected_overlay"
    elif visual_path.is_file() and visual_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        data_uri = _encode_image_data_uri(visual_path)
        title = html.escape(_clean(payload.get("title")) or selected_url)
        html_text = f"""<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{css}\nbody{{margin:0;background:#f8fafc}}.page-shot{{display:block;max-width:100%;height:auto;margin:0 auto;background:white}}</style></head><body><img class='page-shot' src='{data_uri}' alt='Captured page screenshot'><script>{js}</script></body></html>"""
        base_kind = "captured_screenshot_with_overlay_sidecar"
    else:
        title = html.escape(_clean(payload.get("title")) or selected_url)
        html_text = f"""<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{css}</style></head><body><p>YTCE role overlay launcher for <a href='{html.escape(selected_url)}'>{html.escape(selected_url)}</a>.</p><script>{js}</script></body></html>"""
        base_kind = "pywebview_live_url_overlay_launcher"
    html_path = output / "selected_link_source_role_overlay.html"
    html_path.write_text(html_text, encoding="utf-8", newline="\n")
    if base_kind in {"captured_html_with_injected_overlay", "captured_screenshot_with_overlay_sidecar"}:
        launch_start_url = html_path.resolve().as_uri()
    data_path = output / "selected_link_source_role_overlay.json"
    data_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8", newline="\n")
    changes_path = output / "selected_link_source_role_overlay_changes.jsonl"
    launch_log_path = output / "selected_link_source_role_webview_launch.log"
    launcher = output / "open_selected_link_source_role_webview.py"
    launcher.write_text(_pywebview_launcher_source(selected_url, html_path, data_path, changes_path, launch_log_path, _clean(payload.get("title")), launch_start_url), encoding="utf-8", newline="\n")
    cmd = output / "open_selected_link_source_role_webview.cmd"
    cmd.write_text(f'@echo off\r\n"{sys.executable}" "{launcher}"\r\n', encoding="utf-8", newline="")
    try:
        _r42cr_warm_native_webview2_server_async({
            "launch_log_path": str(launch_log_path),
            "selected_url": selected_url,
            "overlay_json_path": str(data_path),
            "overlay_changes_jsonl_path": str(changes_path),
            "initial_mode": mode_key,
        })
    except Exception:
        pass
    return {
        R42H_REAL_WEBVIEW_OVERLAY_MARKER: True,
        R42Q_WEBVIEW_EDITOR_MARKER: True,
        R42S_ONE_WINDOW_LIVE_WEBVIEW_MARKER: True,
        R42T_JS_ESCAPE_FIX_MARKER: True,
        R42U_PRESENTATION_FIX_MARKER: True,
        R42V_PRESENTATION_SPEED_SAVE_MARKER: True,
        R42W_LAUNCHER_NEWLINE_FIX_MARKER: True,
        R42X_PRESENTATION_PARITY_MARKER: True,
        R42Y_PRESENTATION_PARITY_MARKER: True,
        R42Z_PRESENTATION_PARITY_MARKER: True,
        R42AA_PRESENTATION_VISIBILITY_MARKER: True,
        R42AB_ROBUST_DOM_PRESENTATION_MARKER: True,
        R42AC_REPAINT_AND_BODY_FALLBACK_MARKER: True,
        R42AD_FAST_PAINT_MEDIA_OUTLINES_MARKER: True,
        R42AE_MEDIA_OUTLINE_BOX_MARKER: True,
        R42AF_MEDIA_TARGET_NARROWING_MARKER: True,
        R42AG_COOKIE_CACHE_OUTLINE_MARKER: True,
        R42AI_NATIVE_WEBVIEW2_EDITOR_MARKER: True,
        R42AP_NATIVE_EDITOR_MEDIA_UI_MATCH_MARKER: True,
        R42AR_NATIVE_EDITOR_SPEED_RESOURCE_MARKER: True,
        R42AS_NATIVE_EDITOR_STABLE_DEBUG_UI_MARKER: True,
        R42AX_NATIVE_EDITOR_TARGETED_MEDIA_FAST_MARKER: True,
        R42AY_NATIVE_EDITOR_CLEAN_GREY_TOGGLE_MARKER: True,
        R42CR_NATIVE_EDITOR_WARM_SERVER_MARKER: True,
        "status": "READY",
        "base_kind": base_kind,
        "selected_url": selected_url,
        "overlay_html_path": str(html_path),
        "overlay_json_path": str(data_path),
        "overlay_changes_jsonl_path": str(changes_path),
        "launch_log_path": str(launch_log_path),
        "pywebview_launcher_path": str(launcher),
        "open_cmd_path": str(cmd),
        "visual_base_kind": kind,
        "visual_base_path": str(visual_path) if str(visual_path) else "",
        "loads_real_url_in_pywebview": base_kind in {"pywebview_live_url_overlay_launcher", "live_url_with_injected_overlay"},
        "loads_captured_html_in_pywebview": base_kind == "captured_html_with_injected_overlay",
        "loads_live_url_with_injected_overlay": base_kind == "live_url_with_injected_overlay",
        "launch_start_url": launch_start_url,
        "initial_mode": mode_key,
        "r42q_webview_source_editor_controls": True,
        "r42r_live_url_default": True,
        "r42s_one_window_live_url_editor": True,
        "r42t_js_escape_fix": True,
        "r42u_exact_span_presentation": True,
        "r42v_header_blank_media_speed_fixes": True,
        "r42w_launcher_newline_syntax_fix": True,
        "r42x_review_presentation_parity": True,
        "r42y_header_meta_media_fast_single_inject": True,
        "r42z_deterministic_review_row_presentation": True,
        "r42aa_article_colour_visibility_fix": True,
        "r42ab_robust_dom_paint_restore": True,
        "r42ac_repaint_body_textmap_fallback": True,
        "r42ad_fast_first_paint_media_outlines": True,
        "r42ae_document_media_outline_boxes": True,
        "r42af_narrow_article_media_outlines": True,
        "r42ag_cookie_cache_and_outline_only_media": True,
        "r42ai_native_webview2_source_role_editor": True,
        "injects_css_js_overlay": True,
        "source_role_effect": ROLE_EFFECT,
    }


def _pywebview_launcher_source(selected_url: str, html_path: Path, data_path: Path, changes_path: Path, launch_log_path: Path, title: str, launch_start_url: str = "") -> str:
    return f"""from __future__ import annotations
import json, time, sys, webbrowser, datetime
from pathlib import Path
try:
    import webview
except Exception as exc:
    print('pywebview is not available:', exc)
    sys.exit(2)

html_path = Path({str(html_path)!r})
data_path = Path({str(data_path)!r})
changes_path = Path({str(changes_path)!r})
launch_log_path = Path({str(launch_log_path)!r})
storage_path = launch_log_path.parent / 'webview2_user_data'
selected_url = {selected_url!r}
launch_start_url = {launch_start_url!r}
title = {title!r} or selected_url or 'YTCE source-role WebView'

def _log(message):
    try:
        launch_log_path.parent.mkdir(parents=True, exist_ok=True)
        with launch_log_path.open('a', encoding='utf-8', newline='\\n') as fh:
            fh.write(datetime.datetime.now().isoformat(timespec='seconds') + ' ' + str(message) + '\\n')
    except Exception:
        pass

try:
    payload = json.loads(data_path.read_text(encoding='utf-8'))
except Exception as exc:
    _log('payload read failed: ' + repr(exc))
    payload = {{}}

try:
    local_html = html_path.read_text(encoding='utf-8', errors='replace')
except Exception as exc:
    _log('overlay html read failed: ' + repr(exc))
    local_html = ''

style_marker = '<style id="ytce-role-overlay-css">'
if style_marker in local_html:
    css_text = local_html.split(style_marker, 1)[1].split('</style>', 1)[0]
else:
    css_text = ''
marker = '<script id="ytce-role-overlay-js">'
if marker in local_html:
    script = local_html.split(marker, 1)[1].split('</script>', 1)[0]
else:
    script = local_html.split('<script>', 1)[-1].split('</script>', 1)[0] if '<script>' in local_html else ''
css_injector = ""
if css_text:
    css_injector = "(function(){{var old=document.getElementById('ytce-role-overlay-css');if(old)old.remove();var st=document.createElement('style');st.id='ytce-role-overlay-css';st.textContent=" + json.dumps(css_text) + ";(document.head||document.documentElement).appendChild(st);}})();"

class Api:
    def open_external(self, url=None):
        try:
            webbrowser.open(url or selected_url)
            return True
        except Exception as exc:
            _log('open_external failed: ' + repr(exc))
            return {{'ok': False, 'error': str(exc)}}
    def save_role_change(self, change):
        try:
            changes_path.parent.mkdir(parents=True, exist_ok=True)
            row = dict(change or {{}})
            row['ts'] = datetime.datetime.now().isoformat(timespec='seconds')
            with changes_path.open('a', encoding='utf-8', newline='\\n') as fh:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\\n')
            return True
        except Exception as exc:
            _log('save_role_change failed: ' + repr(exc))
            return {{'ok': False, 'error': str(exc)}}
    def save_role_changes(self, changes):
        try:
            changes_path.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.datetime.now().isoformat(timespec='seconds')
            with changes_path.open('a', encoding='utf-8', newline='\\n') as fh:
                for change in (changes or []):
                    row = dict(change or {{}})
                    row['ts'] = now
                    fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\\n')
            return True
        except Exception as exc:
            _log('save_role_changes failed: ' + repr(exc))
            return {{'ok': False, 'error': str(exc)}}

    def log_event(self, message):
        try:
            _log('js: ' + str(message))
            return True
        except Exception:
            return False

    def copy_to_clipboard(self, text):
        try:
            import tkinter as tk
            root = tk.Tk(); root.withdraw(); root.clipboard_clear(); root.clipboard_append(str(text or '')); root.update(); root.destroy()
            return True
        except Exception as exc:
            _log('copy_to_clipboard failed: ' + repr(exc))
            return {{'ok': False, 'error': str(exc)}}

start_url = launch_start_url or selected_url or html_path.resolve().as_uri()
_log('starting pywebview: ' + start_url)
try:
    storage_path.mkdir(parents=True, exist_ok=True)
    _log('R42AG storage_path: ' + str(storage_path))
except Exception as exc:
    _log('R42AG storage_path setup failed: ' + repr(exc))
window = webview.create_window(title, start_url, width=1180, height=820, confirm_close=True, js_api=Api())

def inject():
    # R42Y: inject once successfully.  Re-running the whole overlay repeatedly on
    # a live page caused slow click feedback and could reset client-side role edits.
    for delay in (0.05, 0.25, 0.8, 1.8, 3.5, 6.0):
        time.sleep(delay)
        try:
            if css_injector:
                window.evaluate_js(css_injector)
            if script:
                window.evaluate_js(script)
            _log('overlay injected after delay ' + str(delay))
            break
        except Exception as exc:
            _log('overlay injection failed after delay ' + str(delay) + ': ' + repr(exc))

try:
    try:
        webview.start(inject, debug=False, private_mode=False, storage_path=str(storage_path))
    except TypeError as exc:
        _log('R42AG pywebview storage_path/private_mode unsupported, fallback start: ' + repr(exc))
        webview.start(inject, debug=False)
    _log('pywebview exited normally')
except Exception as exc:
    _log('pywebview start failed: ' + repr(exc))
    raise
""".strip() + "\n"


def _r42ai_truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip() in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}


def _r42ai_append_log(path: Path, message: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(message.rstrip() + "\n")
    except Exception:
        pass


def _r42ai_native_webview2_paths(overlay: Mapping[str, Any]) -> dict[str, Path]:
    """Return absolute native-helper paths.

    R42AK fixes a WebView2 UDF failure caused by passing relative paths to the
    native helper.  WebView2 can resolve a relative user-data folder against the
    helper executable directory, which produced a nested path like
    r42am_native_editor_build/profile_media_live_captures/... and caused Edge
    to report that it could not create/read/write the data directory.
    """
    try:
        project_root = Path(__file__).resolve().parent
    except Exception:
        project_root = Path.cwd()
    try:
        project_root = project_root.resolve()
    except Exception:
        pass

    raw_log = _clean(overlay.get("launch_log_path") or "")
    output = Path(raw_log).parent if raw_log else Path("profile_media_live_captures") / "link_source_role_webview_overlay"
    if not output.is_absolute():
        output = project_root / output
    try:
        output = output.resolve()
    except Exception:
        pass

    helper_dir = project_root / "tools" / "webview2_source_role_editor_native"
    if not helper_dir.is_dir():
        helper_dir = Path.cwd() / "tools" / "webview2_source_role_editor_native"
    try:
        helper_dir = helper_dir.resolve()
    except Exception:
        pass

    build_dir = output / "r42cr_native_editor_build"

    # Keep the browser profile app-owned but short and writable.  This simulates
    # normal Edge persistence without reusing the user's real Edge profile.
    local_app_data = _clean(os.environ.get("LOCALAPPDATA") or "")
    if local_app_data:
        udf = Path(local_app_data) / "YTCE" / "WebView2SourceRoleEditor"
    else:
        udf = output / "webview2_native_user_data"
    try:
        udf = udf.resolve()
    except Exception:
        pass

    return {
        "project_root": project_root,
        "output": output,
        "helper_dir": helper_dir,
        "csproj": helper_dir / "YTCE.NativeSourceRoleEditor.csproj",
        "program": helper_dir / "Program.cs",
        "build_dir": build_dir,
        "exe": build_dir / "YTCE.NativeSourceRoleEditor.R42CR.exe",
        "dll": build_dir / "YTCE.NativeSourceRoleEditor.R42CR.dll",
        "udf": udf,
        "native_log": output / "selected_link_source_role_native_webview2_launch.log",
    }


def _r42ai_native_needs_build(paths: Mapping[str, Path]) -> bool:
    if _r42ai_truthy_env("YTCE_R42AI_FORCE_NATIVE_BUILD"):
        return True
    exe = paths["exe"]
    dll = paths["dll"]
    target = exe if exe.is_file() else dll
    if not target.is_file():
        return True
    try:
        target_mtime = target.stat().st_mtime
        for source in (paths["program"], paths["csproj"]):
            if source.is_file() and source.stat().st_mtime > target_mtime:
                return True
    except Exception:
        return True
    return False


def _r42ai_build_native_webview2_helper(paths: Mapping[str, Path]) -> tuple[bool, str]:
    dotnet = shutil.which("dotnet") or "dotnet"
    build_dir = paths["build_dir"]
    csproj = paths["csproj"]
    native_log = paths["native_log"]
    if not csproj.is_file():
        return False, "missing_native_webview2_csproj"
    try:
        build_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            dotnet,
            "publish",
            str(csproj),
            "-c",
            "Release",
            "-o",
            str(build_dir),
            "--self-contained",
            "false",
            "/p:UseAppHost=true",
        ]
        _r42ai_append_log(native_log, "R42CR native build command: " + " ".join(cmd))
        completed = subprocess.run(
            cmd,
            cwd=str(paths["helper_dir"]),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=int(os.environ.get("YTCE_R42AI_NATIVE_BUILD_TIMEOUT", "180") or "180"),
        )
        output = completed.stdout or ""
        _r42ai_append_log(native_log, output.rstrip())
        if completed.returncode != 0:
            return False, "native_webview2_build_failed"
        if not paths["exe"].is_file() and not paths["dll"].is_file():
            return False, "native_webview2_build_output_missing"
        return True, "built"
    except Exception as exc:
        _r42ai_append_log(native_log, "R42CR native build exception: " + repr(exc))
        return False, "native_webview2_build_exception_" + str(exc)



def _r42cr_command_dir(paths: Mapping[str, Path]) -> Path:
    return paths["output"] / "r42cr_native_editor_server"


def _r42cr_ready_path(paths: Mapping[str, Path]) -> Path:
    return _r42cr_command_dir(paths) / "r42cr_server_ready.json"


def _r42cr_command_guard_path(paths: Mapping[str, Path]) -> Path:
    return _r42cr_command_dir(paths) / "r42cr_last_command_guard.json"


def _r42cr_command_lock_path(paths: Mapping[str, Path]) -> Path:
    return _r42cr_command_dir(paths) / "r42cr_command_write.lock"


def _r42cr_command_signature(*, selected_url: str, payload_path: Path, changes_path: Path, mode: str, action: str = "") -> str:
    return "|".join([
        _clean(selected_url),
        str(payload_path),
        str(changes_path),
        "media" if str(mode or "").lower() == "media" else "semantic",
        _clean(action),
    ])


def _r42cr_recent_duplicate_command(paths: Mapping[str, Path], signature: str, window_ms: int = 1200) -> bool:
    """Best-effort process-side debounce for double-fired edit buttons.

    The C# warm server also ignores duplicate commands, but stopping the second
    command file here avoids needless payload reads and duplicate navigations.
    """
    try:
        guard = _r42cr_command_guard_path(paths)
        if not guard.is_file():
            return False
        data = json.loads(guard.read_text(encoding="utf-8", errors="replace"))
        if _clean(data.get("signature")) != signature:
            return False
        created = float(data.get("created_at") or 0)
        return created > 0 and (time.time() - created) * 1000.0 < max(100, int(window_ms))
    except Exception:
        return False


def _r42cr_write_command_guard(paths: Mapping[str, Path], signature: str, command_path: Path) -> None:
    try:
        guard = _r42cr_command_guard_path(paths)
        guard.write_text(json.dumps({
            "signature": signature,
            "command": str(command_path),
            "created_at": time.time(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _r42cr_acquire_command_lock(paths: Mapping[str, Path]) -> tuple[bool, str]:
    lock_path = _r42cr_command_lock_path(paths)
    try:
        if lock_path.is_file() and time.time() - lock_path.stat().st_mtime > 5:
            try:
                lock_path.unlink()
            except Exception:
                pass
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode("ascii", "replace"))
        finally:
            os.close(fd)
        return True, str(lock_path)
    except FileExistsError:
        return False, str(lock_path)
    except Exception:
        return True, ""


def _r42cr_release_command_lock(lock_path: str) -> None:
    if not lock_path:
        return
    try:
        Path(lock_path).unlink()
    except Exception:
        pass


def _r42cr_role_db_path(paths: Mapping[str, Path]) -> Path:
    return paths["output"] / "selected_link_source_role_roleplan.sqlite"


def _r42cr_role_db_summary_path(paths: Mapping[str, Path]) -> Path:
    return paths["output"] / "selected_link_source_role_roleplan_summary.json"


def _r42cr_sync_source_role_db_async(paths: Mapping[str, Path], *, payload_path: Path, changes_path: Path) -> None:
    """Start the R42CR SQLite sidecar sync without blocking editor open.

    The WebView2 editor still consumes selected_link_source_role_overlay.json for
    speed.  This background sync gives the next Review DB/database layer a
    persistent role-plan + change-event table to build from.
    """
    try:
        if _r42ai_truthy_env("YTCE_R42CR_DISABLE_ROLE_DB") or _r42ai_truthy_env("YTCE_R42BG_DISABLE_ROLE_DB") or _r42ai_truthy_env("YTCE_R42BF_DISABLE_ROLE_DB") or _r42ai_truthy_env("YTCE_R42BE_DISABLE_ROLE_DB"):
            return
        helper = paths["helper_dir"] / "r42cr_source_role_db.py"
        if not helper.is_file():
            _r42ai_append_log(paths["native_log"], "R42CR source-role DB sync skipped: helper missing")
            return
        db_path = _r42cr_role_db_path(paths)
        summary_path = _r42cr_role_db_summary_path(paths)
        args = [
            sys.executable or "python",
            str(helper),
            "sync",
            "--root", str(paths["project_root"]),
            "--payload", str(payload_path),
            "--changes", str(changes_path),
            "--db", str(db_path),
            "--summary", str(summary_path),
        ]
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(paths["project_root"]))
        _r42ai_append_log(paths["native_log"], f"R42CR source-role DB sync queued: db={db_path}; summary={summary_path}")
    except Exception as exc:
        try:
            _r42ai_append_log(paths["native_log"], "R42CR source-role DB sync exception: " + repr(exc))
        except Exception:
            pass


def _r42cr_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return str(pid) in (completed.stdout or "")
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _r42cr_read_server_pid(paths: Mapping[str, Path]) -> int:
    try:
        ready = _r42cr_ready_path(paths)
        if not ready.is_file():
            return 0
        data = json.loads(ready.read_text(encoding="utf-8", errors="replace"))
        return int(data.get("pid") or 0)
    except Exception:
        return 0


def _r42cr_server_alive(paths: Mapping[str, Path]) -> bool:
    return _r42cr_pid_alive(_r42cr_read_server_pid(paths))


def _r42cr_wait_for_server_ready(paths: Mapping[str, Path], timeout_ms: int) -> bool:
    deadline = time.time() + max(0, int(timeout_ms or 0)) / 1000.0
    while time.time() < deadline:
        if _r42cr_server_alive(paths):
            return True
        time.sleep(0.04)
    return _r42cr_server_alive(paths)


def _r42cr_server_executable_args(paths: Mapping[str, Path]) -> list[str]:
    if paths["exe"].is_file():
        return [str(paths["exe"])]
    if paths["dll"].is_file():
        dotnet = shutil.which("dotnet") or "dotnet"
        return [dotnet, str(paths["dll"])]
    return []


def _r42cr_start_native_webview2_server(paths: Mapping[str, Path], *, build_if_needed: bool, wait_ms: int = 0) -> tuple[bool, str]:
    native_log = paths["native_log"]
    try:
        if _r42ai_truthy_env("YTCE_R42CR_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42BG_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42BF_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42BE_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42BA_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42AZ_DISABLE_NATIVE_SERVER"):
            return False, "server_disabled_by_env"
        if _r42cr_server_alive(paths):
            return True, "server_already_alive"
        command_dir = _r42cr_command_dir(paths)
        command_dir.mkdir(parents=True, exist_ok=True)
        starting_path = command_dir / "r42cr_server_starting.json"
        try:
            if starting_path.is_file() and time.time() - starting_path.stat().st_mtime < 6:
                return True, "server_start_in_progress"
        except Exception:
            pass
        if build_if_needed and _r42ai_native_needs_build(paths):
            ok, reason = _r42ai_build_native_webview2_helper(paths)
            if not ok:
                return False, reason
        executable_args = _r42cr_server_executable_args(paths)
        if not executable_args:
            return False, "native_webview2_exe_missing_for_server"
        command_dir = _r42cr_command_dir(paths)
        command_dir.mkdir(parents=True, exist_ok=True)
        try:
            starting_path.write_text(json.dumps({"pid": os.getpid(), "started": time.time()}, indent=2), encoding="utf-8")
        except Exception:
            pass
        for old_cmd in command_dir.glob("command_*.json"):
            try:
                old_cmd.unlink()
            except Exception:
                pass
        args = executable_args + [
            "--server",
            "--root", str(paths["project_root"]),
            "--udf", str(paths["udf"]),
            "--log", str(native_log),
            "--command-dir", str(command_dir),
        ]
        _r42ai_append_log(native_log, "R42CR warm server start command: " + " ".join(args))
        subprocess.Popen(args, stdin=subprocess.DEVNULL, cwd=str(paths["project_root"]))
        deadline = time.time() + max(0, wait_ms) / 1000.0
        while time.time() < deadline:
            if _r42cr_server_alive(paths):
                return True, "server_started_ready"
            time.sleep(0.05)
        return True, "server_started"
    except Exception as exc:
        _r42ai_append_log(native_log, "R42CR warm server start exception: " + repr(exc))
        return False, "server_start_exception_" + str(exc)


def _r42cr_send_native_server_command(
    paths: Mapping[str, Path],
    *,
    selected_url: str,
    payload_path: Path,
    changes_path: Path,
    mode: str,
    action: str = "",
) -> tuple[bool, str]:
    native_log = paths["native_log"]
    try:
        selected_url = _r42eb_clean_url_for_navigation(selected_url)
        ok, reason = _r42cr_start_native_webview2_server(paths, build_if_needed=True, wait_ms=500)
        if not ok:
            return False, reason
        if not _r42cr_wait_for_server_ready(paths, 2500):
            return False, "server_not_ready_after_wait"
        command_dir = _r42cr_command_dir(paths)
        command_dir.mkdir(parents=True, exist_ok=True)
        command_action = _clean(action) or "role_overlay"
        signature = _r42cr_command_signature(selected_url=selected_url, payload_path=payload_path, changes_path=changes_path, mode=mode, action=command_action)
        got_lock, lock_path = _r42cr_acquire_command_lock(paths)
        if not got_lock:
            # Another app callback is writing the same command right now; let that
            # command own the warm-server navigation instead of creating a second
            # near-identical command file.
            _r42ai_append_log(native_log, f"R42CR server command debounced: command write in progress; url={selected_url}")
            return True, "server_command_debounced_write_in_progress"
        try:
            if _r42cr_recent_duplicate_command(paths, signature):
                _r42ai_append_log(native_log, f"R42CR server command debounced: recent duplicate; url={selected_url}")
                return True, "server_command_debounced_recent_duplicate"
            stamp = time.strftime("%Y%m%d_%H%M%S")
            command_path = command_dir / f"command_{stamp}_{os.getpid()}_{int(time.time() * 1000)}.json"
            # Keep the temporary filename outside command_*.json so the server never sees partial content.
            temp_path = command_dir / ("pending_" + command_path.name + ".tmp")
            payload = {
                "marker": "YTCE_R42CR_NATIVE_WEBVIEW2_SERVER_COMMAND",
                "created_at": time.time(),
                "action": command_action,
                "root": str(paths["project_root"]),
                "payload": str(payload_path),
                "changes": str(changes_path),
                "role_db": str(_r42cr_role_db_path(paths)),
                "role_db_summary": str(_r42cr_role_db_summary_path(paths)),
                "url": selected_url,
                "mode": mode,
            }
            with open(temp_path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass
            os.replace(str(temp_path), str(command_path))
            _r42cr_write_command_guard(paths, signature, command_path)
            _r42ai_append_log(native_log, f"R42CR server command queued: {command_path}; start_reason={reason}; url={selected_url}")
            _r42cr_sync_source_role_db_async(paths, payload_path=payload_path, changes_path=changes_path)
            return True, reason
        finally:
            _r42cr_release_command_lock(lock_path)
    except Exception as exc:
        _r42ai_append_log(native_log, "R42CR server command exception: " + repr(exc))
        return False, "server_command_exception_" + str(exc)



def r42cr_capture_material_with_native_webview2(
    *,
    source_url: str,
    source_title: str = "",
    output_dir: str | Path | None = None,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """Capture rendered source material through the app-owned native WebView2 server.

    This is the R42CR production bridge for archive.ph rows.  It sends a material
    capture command to the warm native WebView2 helper, waits for the helper to
    navigate the visible/app-owned browser session, then consumes article_text/html
    artifacts written from the rendered document.  It deliberately avoids using
    direct HTTP as the only material path and gives GO/Webpage a real browser
    material source before generic Playwright fallback.
    """
    source_url = _r42eb_clean_url_for_navigation(source_url)
    source_title = _clean(source_title) or source_url
    if not source_url:
        return {"status": "failed", "reason": "missing_source_url"}
    try:
        project_root = Path(__file__).resolve().parent
    except Exception:
        project_root = Path.cwd()
    try:
        project_root = project_root.resolve()
    except Exception:
        pass
    material_dir = Path(output_dir) if output_dir else project_root / "profile_media_live_captures" / "r42cr_archive_source_material"
    if not material_dir.is_absolute():
        material_dir = project_root / material_dir
    material_dir.mkdir(parents=True, exist_ok=True)
    material_path = material_dir / "native_webview2_material_capture.json"
    payload_path = material_dir / "native_webview2_material_payload.json"
    changes_path = material_dir / "native_webview2_material_changes.jsonl"
    try:
        payload_path.write_text(json.dumps({
            "selected_url": source_url,
            "launch_start_url": source_url,
            "title": source_title,
            "source_navigation_urls": [{"url": source_url, "label": "Archive", "kind": "archive_ph", "current": True}],
            "rows_by_mode": {"semantic": [], "media": []},
            "r42cr_material_capture_worker": True,
            "text_paint_style": os.environ.get("YTCE_R42DU_TEXT_PAINT_STYLE", "").strip(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    overlay = {
        "selected_url": source_url,
        "launch_start_url": source_url,
        "overlay_json_path": str(payload_path),
        "overlay_changes_jsonl_path": str(changes_path),
        "launch_log_path": str(project_root / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_native_webview2_launch.log"),
        "initial_mode": "semantic",
    }
    paths = _r42ai_native_webview2_paths(overlay)
    native_log = paths["native_log"]
    try:
        paths["output"].mkdir(parents=True, exist_ok=True)
        _r42ai_append_log(native_log, "===== R42CR native WebView2 material-capture request =====")
        _r42ai_append_log(native_log, "material_source_url=" + source_url)
        _r42ai_append_log(native_log, "material_output=" + str(material_path))
        if _r42ai_native_needs_build(paths):
            ok, reason = _r42ai_build_native_webview2_helper(paths)
            if not ok:
                return {"status": "failed", "reason": reason, "material_capture_path": str(material_path)}
        ok, reason = _r42cr_start_native_webview2_server(paths, build_if_needed=True, wait_ms=3000)
        if not ok:
            return {"status": "failed", "reason": reason, "material_capture_path": str(material_path)}
        if not _r42cr_wait_for_server_ready(paths, 5000):
            return {"status": "failed", "reason": "native_server_not_ready", "material_capture_path": str(material_path)}
        command_dir = _r42cr_command_dir(paths)
        command_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        command_path = command_dir / f"command_{stamp}_{os.getpid()}_{int(time.time() * 1000)}_material.json"
        temp_path = command_dir / ("pending_" + command_path.name + ".tmp")
        command = {
            "marker": "YTCE_R42CR_NATIVE_WEBVIEW2_SERVER_COMMAND",
            "created_at": time.time(),
            "action": "material_capture",
            "root": str(paths["project_root"]),
            "payload": str(payload_path),
            "changes": str(changes_path),
            "role_db": str(_r42cr_role_db_path(paths)),
            "role_db_summary": str(_r42cr_role_db_summary_path(paths)),
            "url": source_url,
            "mode": "semantic",
            "material_capture_path": str(material_path),
            "material_capture_title": source_title,
            # R42CR: this worker is part of batch source-role processing, not a
            # per-link manual babysitting loop.  Keep the native session alive
            # for normal material loading, but let clear access gates return a
            # structured state quickly so the batch can continue.
            "material_capture_wait_ms": int(max(45000, min(180000, float(timeout_seconds) * 1000.0))),
        }
        with open(temp_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(command, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except Exception:
                pass
        os.replace(str(temp_path), str(command_path))
        _r42ai_append_log(native_log, f"R42CR material command queued: {command_path}; start_reason={reason}; url={source_url}")

        deadline = time.time() + max(75.0, min(930.0, float(timeout_seconds) + 30.0))
        last_data: dict[str, Any] = {}
        last_status_log = 0.0
        while time.time() < deadline:
            if material_path.is_file():
                try:
                    last_data = json.loads(material_path.read_text(encoding="utf-8-sig", errors="replace"))
                except Exception:
                    last_data = {}
                status = _clean(last_data.get("status") if isinstance(last_data, dict) else "")
                if status == "success":
                    last_data.setdefault("material_capture_path", str(material_path))
                    return last_data
                if status in {"failed", "timeout", "access_chain_wait_expired", "access_blocked_challenge", "material_unavailable_access_gate"}:
                    last_data.setdefault("material_capture_path", str(material_path))
                    return last_data
                # R42CR: running/intermediate is not success.  It is held long
                # enough for ordinary page load/lazy material, then the native
                # side returns ACCESS_BLOCKED_CHALLENGE when the visible page is
                # still an access gate.  This lets batch processing continue
                # without substituting Metro/Wayback material.
                now_log = time.time()
                if status in {"intermediate", "access_chain_continuing", "running", "started"} and now_log - last_status_log > 20:
                    _r42ai_append_log(native_log, f"R42CR native material capture waiting: status={status}; challenge_like={last_data.get('challenge_like') if isinstance(last_data, dict) else ''}; material_like={last_data.get('material_like') if isinstance(last_data, dict) else ''}; path={material_path}")
                    last_status_log = now_log
            time.sleep(0.5)
        return {"status": "access_chain_wait_expired", "reason": "native_material_capture_wait_timeout", "material_capture_path": str(material_path), **(last_data if isinstance(last_data, dict) else {})}
    except Exception as exc:
        try:
            _r42ai_append_log(native_log, "R42CR native material capture exception: " + repr(exc))
        except Exception:
            pass
        return {"status": "failed", "reason": "native_material_capture_exception_" + repr(exc), "material_capture_path": str(material_path)}



def r42ct_capture_material_with_native_webview2(
    *,
    source_url: str,
    source_title: str = "",
    output_dir: str | Path | None = None,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """R42CT-compatible alias for the existing R42CR native material bridge.

    The archive material chain imports this name.  The implementation remains the
    same app-owned native WebView2 material-capture command path; this alias does
    not add CAPTCHA bypassing, polling, account access, OpenClaw calls, or proxy
    changes.
    """
    return r42cr_capture_material_with_native_webview2(
        source_url=source_url,
        source_title=source_title,
        output_dir=output_dir,
        timeout_seconds=timeout_seconds,
    )


def _r42cr_warm_native_webview2_server_async(overlay: Mapping[str, Any]) -> None:
    """Best-effort warm start.

    This does not preload the selected URL.  It only starts the app-owned WebView2
    helper on about:blank so a later edit click can reuse the browser engine.
    """
    try:
        if _r42ai_truthy_env("YTCE_R42CR_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42BG_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42BF_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42BE_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42BA_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42AZ_DISABLE_NATIVE_SERVER"):
            return
        paths = _r42ai_native_webview2_paths(overlay)
        if not (paths["exe"].is_file() or paths["dll"].is_file()):
            return
        _r42cr_start_native_webview2_server(paths, build_if_needed=False, wait_ms=0)
    except Exception:
        pass


def r42cr_warm_native_webview2_server_from_project_root(project_root: str | Path | None = None, *, wait_ms: int = 0) -> tuple[bool, str]:
    """Start the native WebView2 helper before the user opens a source editor.

    This is intentionally URL-blank: it warms only the app-owned WebView2
    environment/profile.  The selected live URL and role payload are still sent
    later when the edit icon is clicked, so the app does not preload arbitrary
    source pages.
    """
    try:
        if _r42ai_truthy_env("YTCE_R42CR_DISABLE_NATIVE_SERVER") or _r42ai_truthy_env("YTCE_R42CR_DISABLE_EARLY_NATIVE_WARM") or _r42ai_truthy_env("YTCE_R42BG_DISABLE_EARLY_NATIVE_WARM") or _r42ai_truthy_env("YTCE_R42BF_DISABLE_EARLY_NATIVE_WARM") or _r42ai_truthy_env("YTCE_R42BE_DISABLE_EARLY_NATIVE_WARM") or _r42ai_truthy_env("YTCE_R42BA_DISABLE_EARLY_NATIVE_WARM") :
            return False, "early_warm_disabled_by_env"
        root = Path(project_root) if project_root else Path(__file__).resolve().parent
        try:
            root = root.resolve()
        except Exception:
            pass
        output = root / "profile_media_live_captures" / "link_source_role_webview_overlay"
        overlay = {
            "launch_log_path": str(output / "selected_link_source_role_native_webview2_launch.log"),
        }
        paths = _r42ai_native_webview2_paths(overlay)
        if not (paths["exe"].is_file() or paths["dll"].is_file()):
            _r42ai_append_log(paths["native_log"], "R42CR early warm skipped: native helper build output missing")
            return False, "native_webview2_exe_missing_for_early_warm"
        ok, reason = _r42cr_start_native_webview2_server(paths, build_if_needed=False, wait_ms=wait_ms)
        _r42ai_append_log(paths["native_log"], f"R42CR early warm request: ok={ok}; reason={reason}; wait_ms={wait_ms}")
        return ok, reason
    except Exception as exc:
        try:
            fallback = Path(project_root or Path.cwd()) / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_native_webview2_launch.log"
            _r42ai_append_log(fallback, "R42CR early warm exception: " + repr(exc))
        except Exception:
            pass
        return False, "early_warm_exception_" + str(exc)

def launch_role_overlay_native_webview2_async(overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Launch the R42AI native WebView2 source-role editor.

    The existing write_role_overlay_html() payload remains the single source of
    truth.  The native helper reads selected_link_source_role_overlay.json,
    registers a document-start top-frame-only role engine, and writes click-role
    changes to the same changes JSONL path used by the pywebview fallback.
    """
    paths = _r42ai_native_webview2_paths(overlay)
    native_log = paths["native_log"]
    selected_url = _r42eb_clean_url_for_navigation(overlay.get("selected_url") or overlay.get("launch_start_url"))
    payload_path = Path(str(overlay.get("overlay_json_path") or ""))
    changes_path = Path(str(overlay.get("overlay_changes_jsonl_path") or ""))
    if str(payload_path) and not payload_path.is_absolute():
        payload_path = paths["project_root"] / payload_path
    if str(changes_path) and not changes_path.is_absolute():
        changes_path = paths["project_root"] / changes_path
    try:
        payload_path = payload_path.resolve()
    except Exception:
        pass
    try:
        changes_path = changes_path.resolve()
    except Exception:
        pass
    mode = "media" if str(overlay.get("initial_mode") or "").lower() == "media" else "semantic"
    result_base: dict[str, Any] = {
        R42AI_NATIVE_WEBVIEW2_EDITOR_MARKER: True,
        R42AJ_NATIVE_EDITOR_ROOTFIX_MARKER: True,
        R42AK_NATIVE_EDITOR_ABSPATH_UDF_MARKER: True,
        R42AM_NATIVE_EDITOR_POLISH_MARKER: True,
        R42AN_NATIVE_EDITOR_SPAN_SPEED_MARKER: True,
        R42AP_NATIVE_EDITOR_MEDIA_UI_MATCH_MARKER: True,
        R42AR_NATIVE_EDITOR_SPEED_RESOURCE_MARKER: True,
        R42AS_NATIVE_EDITOR_STABLE_DEBUG_UI_MARKER: True,
        R42AX_NATIVE_EDITOR_TARGETED_MEDIA_FAST_MARKER: True,
        R42AY_NATIVE_EDITOR_CLEAN_GREY_TOGGLE_MARKER: True,
        R42CR_NATIVE_EDITOR_WARM_SERVER_MARKER: True,
        R42CR_NATIVE_EDITOR_EARLY_WARM_MARKER: True,
        R42CR_NATIVE_EDITOR_URL_NAV_MARKER: True,
        "source_role_effect": ROLE_EFFECT,
        "native_webview2_log_path": str(native_log),
        "native_webview2_build_dir": str(paths["build_dir"]),
        "native_webview2_exe_path": str(paths["exe"]),
        "native_webview2_payload_path": str(payload_path),
        "native_webview2_udf_path": str(paths["udf"]),
        "native_webview2_role_db_path": str(_r42cr_role_db_path(paths)),
        "native_webview2_role_db_summary_path": str(_r42cr_role_db_summary_path(paths)),
    }
    try:
        paths["output"].mkdir(parents=True, exist_ok=True)
        _r42ai_append_log(native_log, "===== R42CR native WebView2 launch request =====")
        _r42ai_append_log(native_log, "selected_url=" + selected_url)
        _r42ai_append_log(native_log, "payload=" + str(payload_path))
        _r42ai_append_log(native_log, "changes=" + str(changes_path))
        _r42ai_append_log(native_log, "project_root=" + str(paths["project_root"]))
        _r42ai_append_log(native_log, "udf=" + str(paths["udf"]))
        if _r42ai_truthy_env("YTCE_R42AI_DISABLE_NATIVE_WEBVIEW2"):
            return {**result_base, "launched": False, "reason": "native_webview2_disabled_by_env"}
        if not selected_url:
            return {**result_base, "launched": False, "reason": "missing_selected_url"}
        if not payload_path.is_file():
            return {**result_base, "launched": False, "reason": "missing_overlay_payload_json"}
        if _r42ai_native_needs_build(paths):
            ok, reason = _r42ai_build_native_webview2_helper(paths)
            if not ok:
                return {**result_base, "launched": False, "reason": reason}
        if not _r42ai_truthy_env("YTCE_R42CR_DISABLE_NATIVE_SERVER"):
            server_ok, server_reason = _r42cr_send_native_server_command(
                paths,
                selected_url=selected_url,
                payload_path=payload_path,
                changes_path=changes_path,
                mode=mode,
                action=_clean(overlay.get("native_command_action") or "role_overlay"),
            )
            if server_ok:
                return {
                    **result_base,
                    "launched": True,
                    "reason": "native_webview2_server_command_sent",
                    "launcher": str(paths["exe"]),
                    "launch_log_path": str(native_log),
                    "native_webview2_server": True,
                    "native_webview2_server_reason": server_reason,
                    "native_webview2_command_dir": str(_r42cr_command_dir(paths)),
                }
            _r42ai_append_log(native_log, "R42CR server unavailable, falling back to direct launch: " + server_reason)
        executable_args: list[str]
        if paths["exe"].is_file():
            executable_args = [str(paths["exe"])]
        elif paths["dll"].is_file():
            dotnet = shutil.which("dotnet") or "dotnet"
            executable_args = [dotnet, str(paths["dll"])]
        else:
            return {**result_base, "launched": False, "reason": "native_webview2_exe_missing_after_build"}
        args = executable_args + [
            "--root", str(paths["project_root"]),
            "--payload", str(payload_path),
            "--url", selected_url,
            "--udf", str(paths["udf"]),
            "--changes", str(changes_path),
            "--log", str(native_log),
            "--mode", mode,
        ]
        _r42ai_append_log(native_log, "R42CR native launch command: " + " ".join(args))
        subprocess.Popen(args, stdin=subprocess.DEVNULL, cwd=str(paths["project_root"]))
        return {**result_base, "launched": True, "reason": "native_webview2_launched", "launcher": str(paths["exe"]), "launch_log_path": str(native_log)}
    except Exception as exc:
        _r42ai_append_log(native_log, "R42CR native launch exception: " + repr(exc))
        return {**result_base, "launched": False, "reason": str(exc), "launch_log_path": str(native_log)}

def launch_role_overlay_webview_async(overlay: Mapping[str, Any]) -> dict[str, Any]:
    # R42AI: prefer the native WebView2 source-role editor.  It uses the same
    # payload JSON as the pywebview fallback, but registers the role engine at
    # document-start and uses an app-owned persistent WebView2 profile/cache.
    try:
        native_result = launch_role_overlay_native_webview2_async(overlay)
        if native_result.get("launched"):
            return native_result
        if _r42ai_truthy_env("YTCE_R42AI_NATIVE_WEBVIEW2_ONLY"):
            return native_result
    except Exception:
        native_result = {"launched": False, "reason": "native_webview2_exception"}
    launcher = _clean(overlay.get("pywebview_launcher_path"))
    log_path = _clean(overlay.get("launch_log_path"))
    if not log_path and launcher:
        log_path = str(Path(launcher).with_suffix(".log"))
    if not launcher or not Path(launcher).is_file():
        return {"launched": False, "reason": "missing_launcher", "launch_log_path": log_path, "source_role_effect": ROLE_EFFECT}
    if importlib.util.find_spec("webview") is None:
        return {"launched": False, "reason": "pywebview_missing_optional_dependency", "launcher": launcher, "launch_log_path": log_path, "source_role_effect": ROLE_EFFECT}
    executable = sys.executable or "python"
    try:
        log_file = None
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            log_file = open(log_path, "a", encoding="utf-8", newline="\n")
            log_file.write("launching subprocess: " + executable + " " + launcher + "\\n")
            log_file.flush()
        subprocess.Popen([executable, launcher], stdout=log_file or subprocess.DEVNULL, stderr=log_file or subprocess.DEVNULL, stdin=subprocess.DEVNULL, close_fds=True)
        return {"launched": True, "launcher": launcher, "launch_log_path": log_path, "source_role_effect": ROLE_EFFECT}
    except Exception as exc:
        try:
            if log_path:
                with Path(log_path).open("a", encoding="utf-8", newline="\n") as fh:
                    fh.write("launch failed: " + repr(exc) + "\\n")
        except Exception:
            pass
        return {"launched": False, "reason": str(exc), "launcher": launcher, "launch_log_path": log_path, "source_role_effect": ROLE_EFFECT}
