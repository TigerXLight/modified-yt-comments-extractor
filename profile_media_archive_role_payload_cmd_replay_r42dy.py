from __future__ import annotations

"""R42DY no-GUI archive role-paint replay.

This module validates the archive.ph source-role path from local files only:
R42CT material capture -> R42DS source-role surface -> R42DW role-ready payload
-> paint/counter candidate rows.  It deliberately does not open the app, start
WebView2, hit archive.ph, start Tor/Camoufox, call OpenClaw, poll accounts, read
credentials, or send messages.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping, Iterable
import json
import os
import re
import subprocess
import sys

SOURCE = "https://archive.ph/6mr3C"
SCHEMA = "ytce.r42dy.no_gui_archive_role_paint_replay.v1"
VERSION = "20260907_r42dy_cmdline_archive_role_paint_no_gui"


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _canonical(value: object) -> str:
    text = str(value or "").strip().strip('"\'')
    if not text:
        return ""
    text = text.replace("\\(", "(").replace("\\)", ")").replace("\\]", "]").replace("\\[", "[")
    urls = re.findall(r"https?://[^\s\]\)]+", text, flags=re.IGNORECASE)
    if urls:
        text = urls[0]
    return text.strip().strip("<>").rstrip(".,;:)]}")


def _norm(value: object) -> str:
    s = _clean(value)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[‘’‚‛]", "'", s)
    s = re.sub(r"[“”„‟]", '"', s)
    s = re.sub(r"[‐‑‒–—―]", "-", s)
    return s.casefold()


def _loose(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _norm(value)).strip()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1
        if tag.lower() in {"p", "div", "br", "li", "h1", "h2", "h3", "section", "article", "main"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        t = _clean(data)
        if t:
            self.parts.append(t)

    def text(self) -> str:
        return _clean("\n".join(self.parts))


def _read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"_read_error": repr(exc), "_path": str(path)}


def _read_text(path: Path | None) -> str:
    if not path or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _find_files(base: Path, filename: str) -> list[Path]:
    if not base.exists():
        return []
    out = [p for p in base.rglob(filename) if p.is_file()]
    out.sort(key=lambda p: (p.parent.name, p.name), reverse=True)
    return out


def _latest_good_capture(root: Path, source_url: str = SOURCE) -> tuple[Path | None, dict[str, Any]]:
    base = root / "profile_media_live_captures" / "r42ct_archive_source_material"
    best: tuple[str, Path, dict[str, Any]] | None = None
    for path in _find_files(base, "native_webview2_material_capture.json"):
        data = _read_json(path)
        src = _canonical(data.get("source_url") or data.get("visible_url") or data.get("url") or "")
        folder = path.parent.name
        status = str(data.get("status") or "").casefold()
        text_len = int(data.get("text_length") or data.get("text_len") or 0)
        good_src = src == source_url or source_url.rsplit("/", 1)[-1] in folder
        bad_mixed_case = "6Mr3C" in folder or src == "https://archive.ph/6Mr3C"
        good_status = status == "success" and text_len > 1000
        if good_src and good_status and not bad_mixed_case:
            key = folder
            if best is None or key > best[0]:
                best = (key, path, data)
    if best:
        return best[1], best[2]
    return None, {}


def _surface_candidates(root: Path, source_url: str = SOURCE) -> list[tuple[int, Path, dict[str, Any]]]:
    base = root / "profile_media_live_captures" / "r42ds_archive_source_roles_webview2"
    rows: list[tuple[int, Path, dict[str, Any]]] = []
    for path in _find_files(base, "archive_source_role_surface_r42ds.json"):
        data = _read_json(path)
        src = _canonical(data.get("canonical_source") or data.get("source_url") or "")
        if src and src != source_url:
            continue
        span_count = int(data.get("span_count") or len(data.get("claim_role_spans") or []) or 0)
        score = span_count
        if span_count > 0:
            score += 100000
        if "6Mr3C" in path.parent.name:
            score -= 100000
        if "6mr3C" in path.parent.name:
            score += 1000
        rows.append((score, path, data))
    rows.sort(key=lambda item: (item[0], item[1].parent.name), reverse=True)
    return rows


def _count_role_rows(rows: Iterable[Mapping[str, Any]], mode: str = "semantic") -> dict[str, int]:
    c = Counter()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        role = _clean(row.get("active_role") or row.get("role") or (row.get("media_source_role") if mode == "media" else row.get("semantic_role")) or "UNKNOWN").upper()
        if role in {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK"}:
            c[role] += 1
    return {k: int(c.get(k, 0)) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")}


def _article_text_from_capture(capture_path: Path | None, capture: Mapping[str, Any]) -> tuple[str, str, str]:
    if capture:
        for key in ("article_text_path", "text_path", "visible_text_path"):
            p = Path(str(capture.get(key) or ""))
            if p.is_file():
                return _read_text(p), str(p), "article_text_path"
        if capture_path:
            for name in ("article_text.txt", "webpage_text.txt"):
                p = capture_path.parent / name
                if p.is_file():
                    return _read_text(p), str(p), name
            html_path = capture_path.parent / "archive_page.html"
            if html_path.is_file():
                parser = _TextExtractor()
                try:
                    parser.feed(_read_text(html_path))
                except Exception:
                    pass
                return parser.text(), str(html_path), "archive_page_html_extracted_text"
    return "", "", "not_found"


def _rows_from_payload(payload: Mapping[str, Any], mode: str) -> list[dict[str, Any]]:
    rows_by_mode = payload.get("rows_by_mode") if isinstance(payload.get("rows_by_mode"), Mapping) else {}
    rows = rows_by_mode.get(mode) if isinstance(rows_by_mode, Mapping) else []
    return [dict(r) for r in rows if isinstance(r, Mapping)] if isinstance(rows, list) else []


def _row_match_quality(row_text: str, page_text: str) -> str:
    if not row_text:
        return "empty"
    n_page = _norm(page_text)
    n_row = _norm(row_text)
    l_page = _loose(page_text)
    l_row = _loose(row_text)
    if n_row and n_row in n_page:
        return "exact_normalized_substring"
    if l_row and l_row in l_page:
        return "loose_substring"
    # Some header/byline rows are displayed as multiple adjacent DOM text nodes.
    parts = [_loose(part) for part in re.split(r"\s*\|\s*", row_text) if _loose(part)]
    if len(parts) > 1 and all(part in l_page for part in parts):
        return "pipe_parts_present"
    words = [w for w in l_row.split() if len(w) >= 4]
    if words:
        hits = sum(1 for w in dict.fromkeys(words) if w in l_page)
        ratio = hits / max(1, len(set(words)))
        if ratio >= 0.80:
            return "token_coverage_80"
        if ratio >= 0.50:
            return "token_coverage_50"
    return "not_found_in_saved_page_text"


def _match_summary(rows: list[dict[str, Any]], page_text: str) -> dict[str, Any]:
    counts = Counter()
    missing: list[dict[str, str]] = []
    for row in rows:
        text = _clean(row.get("text") or row.get("excerpt") or "")
        q = _row_match_quality(text, page_text)
        counts[q] += 1
        if q == "not_found_in_saved_page_text" and len(missing) < 20:
            missing.append({
                "role": _clean(row.get("active_role") or row.get("role") or ""),
                "text": text[:220],
            })
    return {
        "total_rows": len(rows),
        "match_quality_counts": dict(counts),
        "paintable_or_present_count": len(rows) - int(counts.get("not_found_in_saved_page_text", 0)),
        "missing_preview": missing,
    }


def _program_js_static_check(root: Path) -> dict[str, Any]:
    program = root / "tools" / "webview2_source_role_editor_native" / "Program.cs"
    text = _read_text(program)
    out: dict[str, Any] = {
        "program_cs_present": program.is_file(),
        "r42dw_role_overlay_refresh_branch": "role_overlay_refresh" in text,
        "r42dv_ready_marker_present": "r42dv_role_paint_js_ready" in text,
        "native_toolbar_state_bridge_present": "native_toolbar_state" in text,
        "bad_duplicate_text_for_row_present": "function textForRow  function textForRow" in text,
    }
    # Optional syntax check of the embedded JS. It uses a dummy payload so this
    # stays no-GUI/no-network.  Skips cleanly if Node is unavailable.
    try:
        m = re.search(r"private static string DocumentStartRoleEditorScript.*?return \$\$\"\"\"(.*?)\"\"\";\s*}", text, re.S)
        if not m:
            out["document_start_script_found"] = False
            return out
        js = m.group(1)
        dummy_payload = json.dumps({
            "rows_by_mode": {
                "semantic": [{"text": "People shout seagull eater", "active_role": "SECONDARY", "semantic_role": "SECONDARY"}],
                "media": [{"text": "People shout seagull eater", "active_role": "SECONDARY", "media_source_role": "SECONDARY"}],
            },
            "selected_url": SOURCE,
            "source_navigation_urls": [],
        }, ensure_ascii=False)
        js = js.replace("{{payloadJson}}", dummy_payload)
        js = js.replace("{{ProjectIconsJson(root)}}", "{}")
        js = js.replace("{{modeJson}}", '"semantic"')
        js = js.replace("{{tokenJson}}", '"r42dy_syntax_probe"')
        tmp = root / "profile_media_live_captures" / "r42dy_archive_role_paint_no_gui"
        tmp.mkdir(parents=True, exist_ok=True)
        js_path = tmp / "document_start_role_editor_script_r42dy_syntax_probe.js"
        js_path.write_text(js, encoding="utf-8")
        out["document_start_script_found"] = True
        out["document_start_script_probe_path"] = str(js_path)
        node = shutil_which("node")
        out["node_available"] = bool(node)
        if node:
            cp = subprocess.run([node, "--check", str(js_path)], cwd=str(root), text=True, capture_output=True, timeout=20)
            out["node_check_returncode"] = cp.returncode
            out["node_check_ok"] = cp.returncode == 0
            out["node_check_stderr"] = (cp.stderr or "")[-2000:]
        else:
            out["node_check_ok"] = None
            out["node_check_stderr"] = "node_not_available"
    except Exception as exc:
        out["node_check_ok"] = False
        out["node_check_stderr"] = repr(exc)
    return out


def shutil_which(name: str) -> str | None:
    # Local import keeps the module importable even if shutil is shadowed in tests.
    import shutil
    return shutil.which(name)


def build_no_gui_archive_role_paint_replay(
    *,
    project_root: str | Path | None = None,
    source_url: str = SOURCE,
    output_root: str | Path | None = None,
    text_paint_style: str = "",
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from profile_media_archive_role_payload_r42dw import build_latest_archive_role_payload

    source_url = _canonical(source_url) or SOURCE
    outroot = Path(output_root or (root / "profile_media_live_captures" / "r42dy_archive_role_paint_no_gui"))
    outroot.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = outroot / ("replay_" + stamp)
    outdir.mkdir(parents=True, exist_ok=True)

    capture_path, capture = _latest_good_capture(root, source_url=source_url)
    article_text, article_source_path, article_text_source = _article_text_from_capture(capture_path, capture)
    surfaces = _surface_candidates(root, source_url=source_url)
    surface_path = surfaces[0][1] if surfaces else None
    surface = surfaces[0][2] if surfaces else {}

    payload_result = build_latest_archive_role_payload(
        project_root=root,
        source_url=source_url,
        output_root=outroot,
        text_paint_style=text_paint_style or os.environ.get("YTCE_R42DU_TEXT_PAINT_STYLE", "").strip(),
    )
    payload_path = Path(str(payload_result.get("payload_path") or ""))
    payload = _read_json(payload_path if payload_path.is_file() else None)

    semantic_rows = _rows_from_payload(payload, "semantic")
    media_rows = _rows_from_payload(payload, "media")

    semantic_counts = _count_role_rows(semantic_rows, "semantic")
    media_counts = _count_role_rows(media_rows, "media")
    semantic_match = _match_summary(semantic_rows, article_text)
    media_match = _match_summary(media_rows, article_text)

    role_plan = {
        "schema": SCHEMA + ".paint_plan",
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "source_url": source_url,
        "toolbar_counts_candidate": {
            "semantic": {k: semantic_counts.get(k, 0) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN")},
            "media": {k: media_counts.get(k, 0) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN")},
        },
        "semantic_rows": semantic_rows,
        "media_rows": media_rows,
        "text_paint_style": text_paint_style or os.environ.get("YTCE_R42DU_TEXT_PAINT_STYLE", "").strip(),
    }
    paint_plan_path = outdir / "r42dy_archive_role_paint_plan_no_gui.json"
    paint_plan_path.write_text(json.dumps(role_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "schema": SCHEMA,
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT",
        "source_url": source_url,
        "do_not_open_app_for_this_probe": True,
        "archive_ph_hit": False,
        "native_webview2_started": False,
        "tor_camoufox_started": False,
        "openclaw_tool_call_performed": False,
        "account_polling_performed": False,
        "outbound_channel_send_performed": False,
        "credentials_read": False,
        "latest_good_capture": {
            "path": str(capture_path) if capture_path else "",
            "status": capture.get("status") if capture else "",
            "source_url": _canonical(capture.get("source_url") or capture.get("visible_url") or "") if capture else "",
            "text_length": int(capture.get("text_length") or capture.get("text_len") or 0) if capture else 0,
            "html_length": int(capture.get("html_length") or capture.get("html_len") or 0) if capture else 0,
            "article_text_source": article_text_source,
            "article_text_path": article_source_path,
            "article_text_chars": len(article_text),
        },
        "selected_r42ds_surface": {
            "path": str(surface_path) if surface_path else "",
            "span_count": int(surface.get("span_count") or len(surface.get("claim_role_spans") or []) or 0) if surface else 0,
            "role_counts": surface.get("role_counts") if surface else {},
            "canonical_source": _canonical(surface.get("canonical_source") or surface.get("source_url") or "") if surface else "",
        },
        "role_ready_payload": {
            "ok": bool(payload_result.get("ok")),
            "payload_path": str(payload_path) if payload_path else "",
            "semantic_rows": len(semantic_rows),
            "media_rows": len(media_rows),
            "semantic_counts": semantic_counts,
            "media_counts": media_counts,
            "text_paint_style": payload.get("text_paint_style") if isinstance(payload, Mapping) else "",
        },
        "saved_page_text_match": {
            "semantic": semantic_match,
            "media": media_match,
        },
        "program_static_check": _program_js_static_check(root),
        "paint_plan_path": str(paint_plan_path),
        "verdict": {
            "local_archive_material_ok": bool(capture and int(capture.get("text_length") or capture.get("text_len") or 0) > 1000),
            "r42ds_surface_ok": bool(surface and int(surface.get("span_count") or 0) > 0),
            "role_payload_ok": bool(len(semantic_rows) > 0 and len(media_rows) > 0),
            "counter_values_are_nonzero_in_cmd": bool(semantic_counts.get("SECONDARY", 0) > 0 and semantic_counts.get("UNKNOWN", 0) > 0),
            "safe_to_continue_without_gui_or_archive_hits": True,
            "next_problem_if_gui_still_zero": "native_editor_runtime_dispatch_or_visual_dom_paint_not_payload_generation",
        },
    }

    summary_path = outdir / "r42dy_no_gui_archive_role_paint_replay_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    compact = {
        "mode": summary["mode"],
        "source_url": source_url,
        "archive_ph_hit": False,
        "native_webview2_started": False,
        "latest_good_capture_status": summary["latest_good_capture"]["status"],
        "latest_good_text_length": summary["latest_good_capture"]["text_length"],
        "selected_surface_span_count": summary["selected_r42ds_surface"]["span_count"],
        "generated_semantic_rows": len(semantic_rows),
        "generated_media_rows": len(media_rows),
        "generated_semantic_counts": semantic_counts,
        "generated_media_counts": media_counts,
        "semantic_match": semantic_match["match_quality_counts"],
        "media_match": media_match["match_quality_counts"],
        "node_check_ok": summary["program_static_check"].get("node_check_ok"),
        "payload_path": str(payload_path) if payload_path else "",
        "paint_plan_path": str(paint_plan_path),
        "outdir": str(outdir),
        "verdict": summary["verdict"],
    }
    return compact


def run_self_test() -> None:
    rows = [
        {"text": "People shout seagull eater", "active_role": "SECONDARY"},
        {"text": "Missing item", "active_role": "UNKNOWN"},
    ]
    m = _match_summary(rows, "People shout seagull eater in the street")
    assert m["match_quality_counts"].get("exact_normalized_substring", 0) == 1
    assert m["match_quality_counts"].get("not_found_in_saved_page_text", 0) == 1
    assert _canonical("[https://archive.ph/6mr3C](https://archive.ph/6mr3C)") == "https://archive.ph/6mr3C"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="R42DY no-GUI/no-network archive role-paint replay.")
    parser.add_argument("source_url", nargs="?", default=SOURCE)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-root", default="")
    parser.add_argument("--recolor", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        print("R42DY self-test passed.")
        raise SystemExit(0)
    result = build_no_gui_archive_role_paint_replay(
        project_root=args.root,
        source_url=args.source_url,
        output_root=args.output_root or None,
        text_paint_style="recolor" if args.recolor else "",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ok = result.get("verdict", {}).get("role_payload_ok") and result.get("verdict", {}).get("counter_values_are_nonzero_in_cmd")
    raise SystemExit(0 if ok else 5)
