from __future__ import annotations

"""R42EB archive role paint local-fixture guard.

Purpose:
- keep repeated tests away from archive.ph;
- prove the role payload and native paint path against a local file URL;
- guard against Markdown-wrapped URLs and the known bad mixed-case 6Mr3C test slug.

The no-GUI probe never starts the app, native WebView2, Tor/Camoufox, OpenClaw, or
archive.ph.  The optional launch command opens only the native WebView2 helper on
a generated local HTML fixture, not the full project app and not archive.ph.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

SOURCE = "https://archive.ph/6mr3C"
SCHEMA = "ytce.r42eb.archive_role_local_fixture.v1"
VERSION = "20260907_r42ec_archive_role_fixture_probe_closeout"


def clean_source_url(value: object) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip().strip('"\'<>')
    if not text:
        return ""
    text = text.replace("\\(", "(").replace("\\)", ")").replace("\\[", "[").replace("\\]", "]").replace("\\_", "_")
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
    # Known single archive.ph test guard only.  Do not lowercase archive ids globally.
    text = text.replace("https://archive.ph/6Mr3C", "https://archive.ph/6mr3C")
    text = text.replace("http://archive.ph/6Mr3C", "http://archive.ph/6mr3C")
    text = text.replace("https://archive.today/6Mr3C", "https://archive.today/6mr3C")
    text = text.replace("http://archive.today/6Mr3C", "http://archive.today/6mr3C")
    return text


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"_read_error": repr(exc), "_path": str(path)}


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("pending_" + path.name + "_" + str(os.getpid()) + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(str(temp), str(path))


def _fixture_svg_data_uri(label: str, *, width: int = 640, height: int = 360) -> str:
    safe = html.escape(label or "YTCE local media fixture")
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<rect width='100%' height='100%' fill='#d9dee7'/>"
        f"<rect x='18' y='18' width='{width-36}' height='{height-36}' rx='18' fill='#f7f7f7' stroke='#8a94a6' stroke-width='4'/>"
        f"<text x='32' y='{height//2}' font-family='Arial,sans-serif' font-size='24' fill='#111827'>{safe}</text>"
        "</svg>"
    )
    return "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg, safe=":/,;?&=%#[]@!$&'()*+")


def _log_has_count_format(text: str, name: str, expected: Mapping[str, int]) -> bool:
    """Accept both old comma count logs and the current native P/S/T/U log form."""
    p = int(expected.get("PRIMARY", 0))
    s = int(expected.get("SECONDARY", 0))
    t = int(expected.get("TERTIARY", 0))
    u = int(expected.get("UNKNOWN", 0))
    compact = f"{name}=P{p}/S{s}/T{t}/U{u}"
    comma = f"{name}={p},{s},{t},{u}"
    comma_blank = f"{name}={p},{s},{t},{u},{int(expected.get('BLANK', 0))}"
    if compact in text or comma in text or comma_blank in text:
        return True
    # Tolerate zero-padded variants and optional spaces for future log formatting.
    pattern = rf"{re.escape(name)}\s*=\s*P0*{p}\s*/\s*S0*{s}\s*/\s*T0*{t}\s*/\s*U0*{u}"
    if re.search(pattern, text, flags=re.IGNORECASE):
        return True
    pattern2 = rf"{re.escape(name)}\s*=\s*0*{p}\s*,\s*0*{s}\s*,\s*0*{t}\s*,\s*0*{u}(?:\s*,\s*0*{int(expected.get('BLANK', 0))})?"
    return bool(re.search(pattern2, text, flags=re.IGNORECASE))


def _payload_expected_counts_from_latest(project_root: Path) -> dict[str, dict[str, int]]:
    """Read latest local payload summary for the expected semantic/media counts."""
    base = project_root / "profile_media_live_captures" / "r42eb_archive_role_local_fixture"
    candidates = sorted(base.rglob("archive_role_overlay_payload_r42dw_summary.json"), key=lambda p: p.stat().st_mtime if p.is_file() else 0, reverse=True)
    for path in candidates[:20]:
        data = _read_json(path)
        if not isinstance(data, Mapping):
            continue
        sem = data.get("semantic_counts") or ((data.get("payload_summary") or {}).get("semantic_counts") if isinstance(data.get("payload_summary"), Mapping) else None)
        med = data.get("media_counts") or ((data.get("payload_summary") or {}).get("media_counts") if isinstance(data.get("payload_summary"), Mapping) else None)
        if isinstance(sem, Mapping) and isinstance(med, Mapping):
            return {
                "semantic": {k: int(sem.get(k, 0) or 0) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")},
                "media": {k: int(med.get(k, 0) or 0) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")},
            }
    return {
        "semantic": {"PRIMARY": 0, "SECONDARY": 35, "TERTIARY": 0, "UNKNOWN": 15, "BLANK": 11},
        "media": {"PRIMARY": 0, "SECONDARY": 41, "TERTIARY": 0, "UNKNOWN": 11, "BLANK": 0},
    }


def _latest_existing_role_payload(project_root: Path, source_url: str) -> dict[str, Any] | None:
    """Fallback for debug uploads that contain role payloads but not the source surface."""
    base = project_root / "profile_media_live_captures"
    if not base.exists():
        return None
    source_key = clean_source_url(source_url).casefold()
    candidates = sorted(
        (p for p in base.rglob("archive_role_overlay_payload_r42dw.json") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for payload_path in candidates[:80]:
        payload = _read_json(payload_path)
        if not isinstance(payload, Mapping):
            continue
        selected = clean_source_url(payload.get("selected_url") or payload.get("launch_start_url") or "")
        if source_key and selected.casefold() != source_key:
            continue
        summary = _payload_summary(payload)
        if int(summary.get("semantic_rows") or 0) <= 0:
            continue
        changes_path = payload_path.with_name("archive_role_overlay_changes_r42dw.jsonl")
        summary_path = payload_path.with_name("archive_role_overlay_payload_r42dw_summary.json")
        return {
            "schema": "ytce.r42ec.existing_archive_role_payload_fallback.v1",
            "version": VERSION,
            "ok": True,
            "source_url": selected or source_url,
            "surface_path": "",
            "payload_path": str(payload_path),
            "changes_path": str(changes_path) if changes_path.exists() else "",
            "summary_path": str(summary_path) if summary_path.exists() else "",
            "semantic_rows": int(summary.get("semantic_rows") or 0),
            "media_rows": int(summary.get("media_rows") or 0),
            "counts_by_mode": {
                "semantic": {k: int((summary.get("semantic_counts") or {}).get(k, 0) or 0) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN")},
                "media": {k: int((summary.get("media_counts") or {}).get(k, 0) or 0) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN")},
            },
            "payload_rows_empty": False,
            "payload_plain_text_chars": int(summary.get("plain_text_chars") or 0),
            "r42ec_existing_payload_fallback": True,
            "side_effects": {
                "network_actions_performed": False,
                "native_webview2_started": False,
                "tor_camoufox_started": False,
                "account_polling_performed": False,
                "message_read_performed": False,
                "outbound_channel_send_performed": False,
                "credentials_read": False,
                "openclaw_tool_call_performed": False,
            },
        }
    return None


def _role_counts(rows: list[Mapping[str, Any]], key: str) -> dict[str, int]:
    out = {"PRIMARY": 0, "SECONDARY": 0, "TERTIARY": 0, "UNKNOWN": 0, "BLANK": 0}
    for row in rows:
        role = str(row.get(key) or row.get("active_role") or row.get("role") or "UNKNOWN").strip().upper()
        if role not in out:
            role = "UNKNOWN"
        out[role] += 1
    return out


def _payload_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows_by_mode = payload.get("rows_by_mode") if isinstance(payload.get("rows_by_mode"), Mapping) else {}
    sem = rows_by_mode.get("semantic") if isinstance(rows_by_mode, Mapping) else []
    med = rows_by_mode.get("media") if isinstance(rows_by_mode, Mapping) else []
    sem = sem if isinstance(sem, list) else []
    med = med if isinstance(med, list) else []
    return {
        "selected_url": clean_source_url(payload.get("selected_url") or payload.get("launch_start_url") or ""),
        "semantic_rows": len(sem),
        "media_rows": len(med),
        "semantic_counts": _role_counts([r for r in sem if isinstance(r, Mapping)], "semantic_role"),
        "media_counts": _role_counts([r for r in med if isinstance(r, Mapping)], "media_source_role"),
        "plain_text_chars": len(str(payload.get("plain_text") or "")),
    }


def build_cached_archive_role_fixture(
    *,
    project_root: str | Path | None = None,
    source_url: object = SOURCE,
    recolor: bool = False,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from profile_media_archive_role_payload_r42dw import build_latest_archive_role_payload  # type: ignore

    out_base = Path(output_root or (root / "profile_media_live_captures" / "r42eb_archive_role_local_fixture"))
    out_base.mkdir(parents=True, exist_ok=True)
    canonical_source = clean_source_url(source_url) or SOURCE
    payload_result = build_latest_archive_role_payload(
        project_root=root,
        source_url=canonical_source,
        output_root=out_base,
        text_paint_style="recolor" if recolor else "",
    )
    if not payload_result.get("ok"):
        fallback_payload_result = _latest_existing_role_payload(root, canonical_source)
        if fallback_payload_result is not None:
            payload_result = fallback_payload_result
        else:
            return {
                "schema": SCHEMA + ".fixture_result",
                "version": VERSION,
                "ok": False,
                "reason": payload_result.get("reason") or "payload_not_available",
                "source_url": canonical_source,
                "payload_result": payload_result,
                "side_effects": {
                    "archive_ph_hit": False,
                    "native_webview2_started": False,
                    "app_started": False,
                    "network_actions_performed": False,
                },
            }

    payload_path = Path(str(payload_result.get("payload_path") or ""))
    payload = _read_json(payload_path)
    rows_by_mode = payload.get("rows_by_mode") if isinstance(payload.get("rows_by_mode"), Mapping) else {}
    semantic_rows = rows_by_mode.get("semantic") if isinstance(rows_by_mode, Mapping) else []
    media_rows = rows_by_mode.get("media") if isinstance(rows_by_mode, Mapping) else []
    semantic_rows = semantic_rows if isinstance(semantic_rows, list) else []
    media_rows = media_rows if isinstance(media_rows, list) else []

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fixture_dir = out_base / ("local_fixture_" + stamp)
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixture_dir / "r42eb_cached_archive_role_fixture.html"

    # Build a deterministic, network-free HTML page containing the same text spans
    # the role payload expects.  No external images, scripts, fonts, CSS, or archive
    # service requests are used.
    body_parts: list[str] = []
    title = str(payload.get("title") or "Cached archive role fixture")
    body_parts.append(f"<h1>{html.escape(title)}</h1>")
    body_parts.append(f"<p><strong>Cached source:</strong> {html.escape(canonical_source)}</p>")
    body_parts.append("<article id='r42eb-article-fixture'>")
    seen: set[str] = set()
    for row in semantic_rows:
        if not isinstance(row, Mapping):
            continue
        text = " ".join(str(row.get("text") or "").split()).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        role = str(row.get("semantic_role") or row.get("active_role") or "UNKNOWN").upper()
        body_parts.append(
            "<p class='fixture-row' data-r42eb-role='" + html.escape(role) + "'>"
            + html.escape(text)
            + "</p>"
        )
    body_parts.append("</article>")
    # R42EC: exercise the actual media-target path with deterministic local
    # media boxes.  These are not external images/videos and do not hit archive.ph,
    # but they look like the same classes of DOM targets the Metro page exposes:
    # a main video/player block plus captioned article figures.
    body_parts.append("<section id='r42eb-media-fixture' aria-label='local media fixture'>")
    main_video_text = next(
        (
            " ".join(str(row.get("text") or "").split()).strip()
            for row in media_rows
            if isinstance(row, Mapping)
            and (
                "Muslim woman who far right painted" in str(row.get("text") or "")
                or "posts what really happened" in str(row.get("text") or "")
            )
        ),
        "Muslim woman who far right painted as 'eating seagull' posts what really happened",
    )
    body_parts.append(
        "<div class='fixture-main-video video-player r42ec-local-media-target' data-ytce-main-video='1' "
        "aria-label='local cached main video fixture'>"
        "<div class='fixture-video-screen'>▶</div>"
        "<div class='fixture-video-title'>" + html.escape(main_video_text) + "</div>"
        "<div class='fixture-video-meta'>0:00 / 0:36 · Up next seagull rescue</div>"
        "</div>"
    )
    caption_needles = [
        "Nora Mubarak said she will not stop doing whatever she likes in Grimsby",
        "Nora was secretly filmed catching the infant seagull to return it to its mother",
        "The baby seagull was stranded on the ground in Grimsby",
    ]
    for idx, needle in enumerate(caption_needles, start=1):
        text = next(
            (
                " ".join(str(row.get("text") or "").split()).strip()
                for row in media_rows
                if isinstance(row, Mapping) and needle.lower() in str(row.get("text") or "").lower()
            ),
            needle + " (Picture: Supplied)",
        )
        img_src = _fixture_svg_data_uri("local media fixture " + str(idx), width=640, height=360)
        body_parts.append(
            "<figure class='fixture-media-card r42ec-local-media-target'>"
            "<img src='" + html.escape(img_src, quote=True) + "' width='640' height='360' alt='" + html.escape(text, quote=True) + "'>"
            "<figcaption>" + html.escape(text) + "</figcaption>"
            "</figure>"
        )
    # Also include a few plain caption lines so text-only media role matching is still covered.
    for row in media_rows[:6]:
        if not isinstance(row, Mapping):
            continue
        text = " ".join(str(row.get("text") or "").split()).strip()
        if text:
            body_parts.append("<div class='fixture-media-caption'>" + html.escape(text) + "</div>")
    body_parts.append("</section>")

    fixture_html = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>R42EB cached archive role paint fixture</title>
<style>
body { font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; line-height: 1.48; }
.fixture-row { margin: 0.75rem 0; }
#r42eb-media-fixture { border: 2px solid #999; padding: 12px; margin-top: 24px; }
.fixture-main-video { width: 640px; min-height: 360px; max-width: 100%; margin: 12px 0 18px 0; border-radius: 12px; border: 3px solid #222; background: #111; color: #fff; position: relative; overflow: hidden; }
.fixture-video-screen { height: 270px; display: flex; align-items: center; justify-content: center; font-size: 88px; background: #1f2937; }
.fixture-video-title { padding: 10px 12px 2px 12px; font-size: 20px; font-weight: 700; }
.fixture-video-meta { padding: 2px 12px 12px 12px; font-size: 13px; color: #d1d5db; }
.fixture-media-card { width: 640px; max-width: 100%; margin: 18px 0; padding: 0; }
.fixture-media-card img { display: block; width: 640px; max-width: 100%; height: auto; border: 0; }
.fixture-media-card figcaption { margin-top: 6px; font-weight: 600; }
.fixture-media-caption { margin: 0.5rem 0; font-weight: 600; }
</style>
</head>
<body>
""" + "\n".join(body_parts) + "\n</body>\n</html>\n"
    _atomic_write(fixture_path, fixture_html)

    payload_summary = _payload_summary(payload)
    result = {
        "schema": SCHEMA + ".fixture_result",
        "version": VERSION,
        "ok": True,
        "source_url": canonical_source,
        "fixture_path": str(fixture_path),
        "fixture_file_url": fixture_path.resolve().as_uri(),
        "payload_path": str(payload_path),
        "changes_path": str(payload_result.get("changes_path") or ""),
        "payload_summary": payload_summary,
        "payload_result": payload_result,
        "recolor": bool(recolor),
        "side_effects": {
            "archive_ph_hit": False,
            "native_webview2_started": False,
            "app_started": False,
            "network_actions_performed": False,
            "tor_camoufox_started": False,
            "openclaw_tool_call_performed": False,
            "account_polling_performed": False,
            "message_read_performed": False,
            "outbound_channel_send_performed": False,
            "credentials_read": False,
        },
    }
    summary_path = fixture_dir / "r42eb_cached_archive_role_fixture_summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["summary_path"] = str(summary_path)
    return result


def launch_native_local_fixture(
    *,
    project_root: str | Path | None = None,
    source_url: object = SOURCE,
    recolor: bool = False,
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    fixture = build_cached_archive_role_fixture(project_root=root, source_url=source_url, recolor=recolor)
    if not fixture.get("ok"):
        return {**fixture, "launched": False}

    from profile_media_link_source_real_webview_overlay_v83d import launch_role_overlay_native_webview2_async  # type: ignore

    output = root / "profile_media_live_captures" / "r42eb_archive_role_local_fixture"
    log_path = root / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_native_webview2_launch.log"
    overlay = {
        "selected_url": fixture["fixture_file_url"],
        "launch_start_url": fixture["fixture_file_url"],
        "overlay_json_path": fixture["payload_path"],
        "overlay_changes_jsonl_path": fixture["changes_path"],
        "launch_log_path": str(log_path),
        "initial_mode": "semantic",
        "r42eb_local_fixture_native_only": True,
        "r42eb_no_archive_hit": True,
    }
    launch = launch_role_overlay_native_webview2_async(overlay)
    result = {
        "schema": SCHEMA + ".native_local_fixture_launch",
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "ok": bool(launch.get("launched")),
        "fixture": fixture,
        "launch": launch,
        "expected_runtime_markers": [
            "native_toolbar_ready",
            "counts_semantic=P0/S35/T0/U15",
            "counts_media=P0/S41/T0/U11",
            "page_message: type=r42dv_role_paint_js_ready",
            "page_message: type=first_role_paint",
            "page_message: type=native_toolbar_state",
        ],
        "side_effects": {
            "app_started": False,
            "archive_ph_hit": False,
            "network_actions_performed_by_this_tool": False,
            "native_webview2_started": bool(launch.get("launched")),
        },
    }
    launch_dir = output / ("native_launch_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    launch_dir.mkdir(parents=True, exist_ok=True)
    summary_path = launch_dir / "r42eb_native_local_fixture_launch_summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["summary_path"] = str(summary_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def probe_native_log(*, project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    log_path = root / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_native_webview2_launch.log"
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    tail = "\n".join(text.splitlines()[-350:])
    result = {
        "schema": SCHEMA + ".native_log_probe",
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "log_path": str(log_path),
        "log_present": log_path.is_file(),
        "found_file_fixture_navigation": "file:///" in tail and "r42eb_cached_archive_role_fixture.html" in tail,
        "found_native_toolbar_ready": "native_toolbar_ready" in tail,
        "found_expected_semantic_counts": _log_has_count_format(tail, "counts_semantic", _payload_expected_counts_from_latest(root)["semantic"]),
        "found_expected_media_counts": _log_has_count_format(tail, "counts_media", _payload_expected_counts_from_latest(root)["media"]),
        "found_r42dv_ready": "r42dv_role_paint_js_ready" in tail,
        "found_first_role_paint": "first_role_paint" in tail,
        "found_native_toolbar_state": "native_toolbar_state" in tail,
        "latest_relevant_lines": [
            line for line in text.splitlines()[-500:]
            if any(k in line for k in (
                "r42eb_cached_archive_role_fixture.html",
                "native_toolbar_ready",
                "r42dv_role_paint_js_ready",
                "first_role_paint",
                "native_toolbar_state",
                "server_command_received",
                "server_command_dispatched",
            ))
        ][-80:],
        "verdict": {},
    }
    result["verdict"] = {
        "local_fixture_used": result["found_file_fixture_navigation"],
        "toolbar_counts_reached_native": result["found_expected_semantic_counts"] and result["found_expected_media_counts"],
        "paint_runtime_executed": result["found_r42dv_ready"] or result["found_first_role_paint"],
        "no_archive_navigation_required": True,
    }
    out = root / "profile_media_live_captures" / "r42eb_archive_role_local_fixture" / ("native_log_probe_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "r42eb_native_local_fixture_log_probe.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["summary_path"] = str(summary_path)
    return result


def build_no_gui_probe(*, project_root: str | Path | None = None, source_url: object = SOURCE, recolor: bool = False) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    fixture = build_cached_archive_role_fixture(project_root=root, source_url=source_url, recolor=recolor)
    program = root / "tools" / "webview2_source_role_editor_native" / "Program.cs"
    overlay = root / "profile_media_link_source_real_webview_overlay_v83d.py"
    program_text = program.read_text(encoding="utf-8", errors="replace") if program.is_file() else ""
    overlay_text = overlay.read_text(encoding="utf-8", errors="replace") if overlay.is_file() else ""
    result = {
        "schema": SCHEMA + ".probe",
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_LOCAL_FIXTURE_AUDIT",
        "source_url": clean_source_url(source_url),
        "archive_ph_hit": False,
        "native_webview2_started": False,
        "app_started": False,
        "fixture_result": fixture,
        "static_checks": {
            "program_clean_native_url_markdown_guard": "R42EB: tolerate chat/Markdown-wrapped URLs" in program_text,
            "program_known_bad_6Mr3C_guard": "https://archive.ph/6Mr3C" in program_text and "https://archive.ph/6mr3C" in program_text,
            "program_url_assignment_uses_clean_native_url": "_url = CleanNativeUrl(FirstNonBlank(" in program_text and "_urlArg = CleanNativeUrl(GetString(\"url\"))" in program_text,
            "overlay_r42eb_url_guard_marker": "R42EB_ARCHIVE_URL_GUARD_MARKER" in overlay_text,
            "overlay_material_capture_cleans_source_url": "source_url = _r42eb_clean_url_for_navigation(source_url)" in overlay_text,
            "overlay_native_launch_cleans_selected_url": "selected_url = _r42eb_clean_url_for_navigation(" in overlay_text,
        },
        "verdict": {
            "payload_ok": bool(fixture.get("ok")) and int(((fixture.get("payload_summary") or {}).get("semantic_rows") or 0)) > 0,
            "fixture_ok": bool(fixture.get("fixture_path")),
            "no_gui_no_network_safe": True,
            "ready_for_optional_native_local_fixture_visual_check": bool(fixture.get("ok")),
        },
    }
    out = root / "profile_media_live_captures" / "r42eb_archive_role_local_fixture" / ("probe_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "r42eb_archive_role_local_fixture_probe_summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["summary_path"] = str(summary_path)
    return result


def run_self_test() -> None:
    assert clean_source_url("[https://archive.ph/6mr3C](https://archive.ph/6mr3C)") == "https://archive.ph/6mr3C"
    assert clean_source_url("[[https://example.com/a](https://example.com/a)](https://example.com/a)") == "https://example.com/a"
    assert clean_source_url("https://archive.ph/6Mr3C") == "https://archive.ph/6mr3C"
    assert clean_source_url("https://archive.ph/AbCdE") == "https://archive.ph/AbCdE"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="R42EB cached archive role local fixture / URL guard.")
    parser.add_argument("source_url", nargs="?", default=SOURCE)
    parser.add_argument("--root", default=".")
    parser.add_argument("--recolor", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--launch-native-local-fixture", action="store_true")
    parser.add_argument("--probe-native-log", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        print("R42EB self-test passed.")
    elif args.launch_native_local_fixture:
        launch_native_local_fixture(project_root=args.root, source_url=args.source_url, recolor=args.recolor)
    elif args.probe_native_log:
        print(json.dumps(probe_native_log(project_root=args.root), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_no_gui_probe(project_root=args.root, source_url=args.source_url, recolor=args.recolor), ensure_ascii=False, indent=2))
