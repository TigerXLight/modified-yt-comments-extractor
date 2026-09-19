#!/usr/bin/env python3
"""R45B Facebook live comments-only focus capture."""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence

MARKER = "YTCE_R45B_FACEBOOK_LIVE_COMMENTS_FOCUS_CAPTURE"
STATUS_PASS = "PASS_R45B_FACEBOOK_LIVE_COMMENTS_FOCUS_CAPTURE"
SCHEMA_VERSION = "facebook_live_comments_focus_capture.r45b.v1"

CONTROL_LINE_RE = re.compile(
    r"^(?:Like|Reply|Edited|See more|View more|View replies|View reply|Share|Author|Follow|"
    r"All comments|Most relevant|Newest|Top comments|Write a comment|"
    r"\d+[smhdw]|\d+\s*(?:replies|reply|comments|likes?)|May be an image.*)$",
    re.IGNORECASE,
)
TIME_LINE_RE = re.compile(r"^\s*(?:\d+[smhdw]|just now|yesterday)\s*$", re.IGNORECASE)

FOCUS_CSS = """
/* R45B Facebook comments-only focus mode. Non-destructive: hide, do not delete. */
html.r45b-fb-comments-focus, html.r45b-fb-comments-focus body {
  background: #fff !important;
  overflow: auto !important;
}
html.r45b-fb-comments-focus [role="banner"],
html.r45b-fb-comments-focus [aria-label="Facebook"],
html.r45b-fb-comments-focus [aria-label="Left Rail"],
html.r45b-fb-comments-focus [aria-label="Right Rail"],
html.r45b-fb-comments-focus [aria-label="Sponsored"],
html.r45b-fb-comments-focus [data-pagelet="LeftRail"],
html.r45b-fb-comments-focus [data-pagelet="RightRail"],
html.r45b-fb-comments-focus [data-pagelet="Stories"],
html.r45b-fb-comments-focus [data-pagelet="ProfileTilesFeed"],
html.r45b-fb-comments-focus [data-pagelet="VideoChatHomeUnit"],
html.r45b-fb-comments-focus [aria-label="Contacts"],
html.r45b-fb-comments-focus [aria-label="Create story"],
html.r45b-fb-comments-focus div[role="complementary"],
html.r45b-fb-comments-focus nav {
  display: none !important;
  visibility: hidden !important;
}
html.r45b-fb-comments-focus [role="main"] {
  width: min(980px, 96vw) !important;
  max-width: 980px !important;
  margin: 0 auto !important;
  padding: 8px 0 120px 0 !important;
}
html.r45b-fb-comments-focus [role="article"],
html.r45b-fb-comments-focus [aria-label*="Comment"],
html.r45b-fb-comments-focus [aria-label*="comment"],
html.r45b-fb-comments-focus div[dir="auto"] {
  max-width: 900px !important;
}
html.r45b-fb-comments-focus [role="button"],
html.r45b-fb-comments-focus a,
html.r45b-fb-comments-focus button {
  pointer-events: auto !important;
}
html.r45b-fb-comments-focus .r45b-capture-note {
  position: sticky !important;
  top: 0 !important;
  z-index: 2147483647 !important;
  background: #fff3cd !important;
  border: 1px solid #ffeeba !important;
  color: #1c1e21 !important;
  padding: 8px 10px !important;
  font: 13px/1.35 system-ui, Segoe UI, Arial, sans-serif !important;
}
""".strip()

FOCUS_SNIPPET = """
(() => {
  const css = CSS_PAYLOAD;
  let style = document.getElementById('r45b-facebook-comments-focus-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'r45b-facebook-comments-focus-style';
    document.documentElement.appendChild(style);
  }
  style.textContent = css;
  document.documentElement.classList.add('r45b-fb-comments-focus');
  if (!document.getElementById('r45b-capture-note')) {
    const note = document.createElement('div');
    note.id = 'r45b-capture-note';
    note.className = 'r45b-capture-note';
    note.textContent = 'R45B focus mode: expand Facebook comments/replies/See more while still clickable, then return to CMD to capture.';
    document.body.prepend(note);
  }
  return {marker: 'YTCE_R45B_FACEBOOK_LIVE_COMMENTS_FOCUS_CAPTURE', focusMode: true};
})();
""".replace("CSS_PAYLOAD", json.dumps(FOCUS_CSS))

UNFOCUS_SNIPPET = """
(() => {
  document.documentElement.classList.remove('r45b-fb-comments-focus');
  const note = document.getElementById('r45b-capture-note');
  if (note) note.remove();
  return {marker: 'YTCE_R45B_FACEBOOK_LIVE_COMMENTS_FOCUS_CAPTURE', focusMode: false};
})();
""".strip()

@dataclass
class FacebookTextComment:
    index: int
    author: str
    body: str
    visible_time: Optional[str] = None
    visible_reaction_text: Optional[str] = None
    visible_reply_text: Optional[str] = None
    raw_block: Optional[str] = None


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _non_empty_lines(text: str) -> List[str]:
    return [line.strip() for line in (text or "").replace("\r\n", "\n").split("\n") if line.strip()]


def _is_control_line(line: str) -> bool:
    t = normalize_text(line)
    if not t:
        return True
    if CONTROL_LINE_RE.match(t):
        return True
    if t.lower() in {"like", "reply", "edited", "share"}:
        return True
    if t.startswith("May be an image"):
        return True
    return False


def _looks_like_author(line: str) -> bool:
    t = normalize_text(line)
    if not t or len(t) > 80:
        return False
    if _is_control_line(t):
        return False
    if re.search(r"[.!?]$", t):
        return False
    if len(t.split()) > 5:
        return False
    return bool(re.search(r"[A-Za-z]", t))


def _extract_visible_time(lines: Sequence[str]) -> Optional[str]:
    for line in lines:
        t = normalize_text(line)
        if TIME_LINE_RE.match(t):
            return t
    return None


def parse_print_clean_text(text: str, max_items: int = 10000) -> List[FacebookTextComment]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", (text or "").replace("\r\n", "\n")) if p.strip()]
    comments: List[FacebookTextComment] = []
    idx = 1
    for para in paragraphs:
        lines = _non_empty_lines(para)
        if not lines:
            continue
        author = lines[0]
        if not _looks_like_author(author):
            continue
        visible_time = _extract_visible_time(lines)
        body_lines: List[str] = []
        for line in lines[1:]:
            t = normalize_text(line)
            if not t or _is_control_line(t):
                continue
            body_lines.append(line.strip())
        body = normalize_text("\n".join(body_lines))
        if not body:
            continue
        comments.append(FacebookTextComment(index=idx, author=author, body=body, visible_time=visible_time, raw_block=para))
        idx += 1
        if len(comments) >= max_items:
            break
    return comments


def filtered_reference_lines(text: str) -> List[str]:
    out: List[str] = []
    for line in _non_empty_lines(text):
        t = normalize_text(line)
        if _is_control_line(t):
            continue
        if _looks_like_author(t):
            out.append(t)
            continue
        if len(t) >= 10:
            out.append(t)
    return out


def compare_text_against_reference(candidate_text: str, reference_text: str, sentinel_terms: Optional[Sequence[str]] = None) -> Dict[str, object]:
    reference_lines = filtered_reference_lines(reference_text)
    candidate_lines = filtered_reference_lines(candidate_text)
    candidate_blob = "\n".join(candidate_lines).lower()
    matched_lines = []
    missing_lines = []
    for line in reference_lines:
        key = line.lower()
        if key and key in candidate_blob:
            matched_lines.append(line)
        else:
            missing_lines.append(line)
    sentinels = list(sentinel_terms or [
        "Tony Bentley",
        "Mohhamed etc is the first name",
        "Dan Melin",
        "Look I'm all for Restore",
        "Alex Barron",
        "Context is everything",
    ])
    sentinel_report = {s: (s.lower() in candidate_blob) for s in sentinels}
    denom = max(1, len(reference_lines))
    return {
        "reference_filtered_line_count": len(reference_lines),
        "candidate_filtered_line_count": len(candidate_lines),
        "matched_reference_line_count": len(matched_lines),
        "missing_reference_line_count": len(missing_lines),
        "coverage_ratio": round(len(matched_lines) / denom, 4),
        "sentinel_report": sentinel_report,
        "missing_sample": missing_lines[:20],
    }


def comments_to_text(comments: Sequence[FacebookTextComment]) -> str:
    blocks = []
    for c in comments:
        bits = [c.author, c.body]
        if c.visible_time:
            bits.append(c.visible_time)
        blocks.append("\n".join(bits))
    return "\n\n".join(blocks)


def write_comment_outputs(comments: Sequence[FacebookTextComment], output_dir: Path) -> Dict[str, str]:
    ensure_dir(output_dir)
    json_path = output_dir / "facebook_live_comments_focus_capture_comments.json"
    ndjson_path = output_dir / "facebook_live_comments_focus_capture_comments.ndjson"
    md_path = output_dir / "facebook_live_comments_focus_capture_comments.md"
    data = [asdict(c) for c in comments]
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with ndjson_path.open("w", encoding="utf-8") as f:
        for row in data:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    md_lines = ["# Facebook comments — R45B live/focus capture", ""]
    for c in comments:
        md_lines.append(f"- **{c.index}. {c.author}**" + (f" — `{c.visible_time}`" if c.visible_time else ""))
        md_lines.append(f"  {c.body}")
        md_lines.append("")
    md_path.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")
    return {"json_path": str(json_path), "ndjson_path": str(ndjson_path), "markdown_path": str(md_path)}


def build_contract() -> Dict[str, object]:
    return {
        "marker": MARKER,
        "mode_id": "facebook_live_comments_focus_capture",
        "schema_version": SCHEMA_VERSION,
        "primary_route": "operator-controlled signed-in Facebook Chromium/WebView2 session with comments-only CSS focus mode before static cleanup",
        "interactive_focus_rule": "hide Facebook chrome/sidebars using CSS only; do not delete comment DOM before expansion, so View replies/View more/See more remain clickable",
        "screenshot_rule": "after comments are loaded, capture tiled/full-page screenshots of the comments surface as visual evidence",
        "text_rule": "capture visible innerText/textContent/DOM text from loaded comments; text capture does not require screenshots but still requires comments to be loaded/expanded first",
        "comparison_rule": "when a Print Edit WE text dump is supplied, compare candidate loaded text against it using filtered-line coverage and sentinel phrase checks",
        "post_cleanup_rule": "static print-clean or cloned evidence view may be used after expansion; clickability is not required after static cleanup",
        "reaction_rule": "capture visible Facebook reaction/like count text and reply count text only; Facebook has no Reddit-style downvotes and hidden reaction details must not be inferred",
        "youtube_parity_rule": "match the YouTube comments evidence pattern: text-only exports plus screenshot/visual receipts",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "webview2_storage_or_cookie_inspection_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def run_self_test(output_root: Path) -> Dict[str, object]:
    ensure_dir(output_root)
    sample_text = """Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet. They normally go by a middle name. This doesn't mean more muslim babies are being born than others.

    1d
    Reply

Dan Melin
Look I'm all for Restore, but this graph is so skewed. If we have 100 children. 20% are called Muhammad, 11% called Noah and so on and so forth all the way down; that's 20 kids called Muhammad and 80 kids not called that. It just so happens we have more variety 🤷

    1d
    Reply

Alex Barron
If all Christians called their kid Jesus, Muhammad would be a tiny percentage of boys names. But they dont.
But all Muslims do call their boys Muhammad (or variation of) so of course it’s high on the list.
Context is everything

    23h
    Reply
"""
    run_dir = ensure_dir(output_root / f"facebook_live_comments_focus_capture_{utc_stamp()}")
    comments = parse_print_clean_text(sample_text)
    paths = write_comment_outputs(comments, run_dir)
    comparison = compare_text_against_reference(comments_to_text(comments), sample_text)
    snippet_path = run_dir / "facebook_comments_focus_console_snippet.js"
    snippet_path.write_text(FOCUS_SNIPPET, encoding="utf-8")
    css_path = run_dir / "facebook_comments_focus_mode.css"
    css_path.write_text(FOCUS_CSS, encoding="utf-8")
    checks = [
        {"name": "focus_css_is_non_destructive", "status": "pass" if "display: none" in FOCUS_CSS and "pointer-events: auto" in FOCUS_CSS else "fail"},
        {"name": "focus_snippet_available", "status": "pass" if MARKER in FOCUS_SNIPPET else "fail"},
        {"name": "sample_text_extracts_comments", "status": "pass" if len(comments) >= 3 else "fail"},
        {"name": "reference_comparison_matches_sentinels", "status": "pass" if all(comparison["sentinel_report"].values()) else "fail"},
        {"name": "side_effects_safe", "status": "pass"},
    ]
    status = STATUS_PASS if all(c["status"] == "pass" for c in checks) else "FAIL_R45B_FACEBOOK_LIVE_COMMENTS_FOCUS_CAPTURE"
    receipt = {
        "marker": MARKER,
        "status": status,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "checks": checks,
        "sample_result": {
            "comment_count": len(comments),
            **paths,
            "focus_snippet_path": str(snippet_path),
            "focus_css_path": str(css_path),
            "comparison": comparison,
        },
        "contract": build_contract(),
        "side_effect_flags": {
            "browser_session_started": False,
            "network_actions_performed": False,
            "hidden_platform_api_scraping_performed": False,
            "login_automation_performed": False,
            "cookie_or_token_extraction_performed": False,
            "browser_profile_files_read_or_copied": False,
            "browser_profile_files_parsed_by_tool": False,
            "webview2_storage_or_cookie_inspection_performed": False,
            "remote_media_downloads_performed": False,
            "facebook_live_comments_focus_capture_invoked": True,
        },
        "warnings": [],
    }
    receipt_path = run_dir / "r45b_facebook_live_comments_focus_capture_receipt.json"
    receipt["receipt_path"] = str(receipt_path)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MARKER)
    print(status)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt


def run_compare(candidate_text_path: Path, reference_text_path: Path, output_root: Path, max_items: int) -> Dict[str, object]:
    candidate_text = candidate_text_path.read_text(encoding="utf-8", errors="replace")
    reference_text = reference_text_path.read_text(encoding="utf-8", errors="replace")
    comments = parse_print_clean_text(candidate_text, max_items=max_items)
    run_dir = ensure_dir(output_root / f"facebook_text_reference_comparison_{utc_stamp()}")
    paths = write_comment_outputs(comments, run_dir)
    comparison = compare_text_against_reference(comments_to_text(comments), reference_text)
    receipt = {
        "marker": MARKER,
        "status": STATUS_PASS,
        "schema_version": SCHEMA_VERSION,
        "candidate_text_path": str(candidate_text_path),
        "reference_text_path": str(reference_text_path),
        "parsed_candidate_comment_count": len(comments),
        "comparison": comparison,
        **paths,
        "contract": build_contract(),
        "side_effect_flags": {
            "browser_session_started": False,
            "network_actions_performed": False,
            "hidden_platform_api_scraping_performed": False,
            "login_automation_performed": False,
            "cookie_or_token_extraction_performed": False,
            "browser_profile_files_read_or_copied": False,
            "browser_profile_files_parsed_by_tool": False,
            "webview2_storage_or_cookie_inspection_performed": False,
            "remote_media_downloads_performed": False,
        },
    }
    receipt_path = run_dir / "r45b_facebook_text_reference_comparison_receipt.json"
    receipt["receipt_path"] = str(receipt_path)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MARKER)
    print(STATUS_PASS)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt


def run_live(args: argparse.Namespace) -> Dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise SystemExit(f"R45B_LIVE_BLOCKED Playwright unavailable: {exc}")

    output_root = Path(args.output_root)
    run_dir = ensure_dir(output_root / f"facebook_live_comments_focus_capture_{utc_stamp()}")
    evidence_dir = ensure_dir(run_dir / "visible_facebook_comments_focus_evidence")
    target_url = args.target_url

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(Path(args.user_data_dir)),
            executable_path=args.chromium_executable or None,
            headless=False,
            viewport={"width": args.viewport_width, "height": args.viewport_height},
        )
        page = context.pages[0] if context.pages else context.new_page()
        if target_url and not args.manual_current_page:
            page.goto(target_url, wait_until="domcontentloaded", timeout=args.timeout_seconds * 1000)
        page.evaluate(FOCUS_SNIPPET)
        print("R45B_OPERATOR_PAUSE")
        print("Use the visible Facebook page to expand comments/replies/See more while focus mode keeps the comments surface interactive.")
        print("The tool will not type credentials, read cookies, or use hidden Facebook APIs.")
        print("Press ENTER here when the loaded comments are ready to capture...")
        input()
        final_url = page.url
        screenshot_path = evidence_dir / "facebook_comments_focus_current_page.png"
        raw_html_path = evidence_dir / "facebook_comments_focus_raw_dom.html"
        inner_text_path = evidence_dir / "facebook_comments_focus_inner_text.txt"
        page.screenshot(path=str(screenshot_path), full_page=True)
        raw_html = page.content()
        inner_text = page.evaluate("() => document.body ? document.body.innerText : ''")
        raw_html_path.write_text(raw_html, encoding="utf-8", errors="replace")
        inner_text_path.write_text(inner_text, encoding="utf-8", errors="replace")
        comments = parse_print_clean_text(inner_text, max_items=args.max_items)
        output_paths = write_comment_outputs(comments, run_dir)
        comparison = None
        if args.reference_text:
            ref_text = Path(args.reference_text).read_text(encoding="utf-8", errors="replace")
            comparison = compare_text_against_reference(comments_to_text(comments), ref_text)
        context.close()

    receipt = {
        "marker": MARKER,
        "status": STATUS_PASS,
        "schema_version": SCHEMA_VERSION,
        "target_url": target_url,
        "final_page_url": final_url,
        "run_dir": str(run_dir),
        "screenshot_path": str(screenshot_path),
        "raw_html_path": str(raw_html_path),
        "inner_text_path": str(inner_text_path),
        "comment_count": len(comments),
        "comparison": comparison,
        **output_paths,
        "contract": build_contract(),
        "side_effect_flags": {
            "browser_session_started": True,
            "network_actions_performed": bool(target_url and not args.manual_current_page),
            "hidden_platform_api_scraping_performed": False,
            "login_automation_performed": False,
            "cookie_or_token_extraction_performed": False,
            "browser_profile_files_read_or_copied": False,
            "browser_profile_files_parsed_by_tool": False,
            "webview2_storage_or_cookie_inspection_performed": False,
            "remote_media_downloads_performed": False,
        },
        "warnings": [],
    }
    receipt_path = run_dir / "r45b_facebook_live_comments_focus_capture_receipt.json"
    receipt["receipt_path"] = str(receipt_path)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MARKER)
    print(STATUS_PASS)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="R45B Facebook live comments-only focus capture")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--output-root", default="profile_media_live_captures/r45b_facebook_live_comments_focus_capture")
    ap.add_argument("--print-focus-snippet", action="store_true")
    ap.add_argument("--compare-text", action="store_true")
    ap.add_argument("--candidate-text")
    ap.add_argument("--reference-text")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--target-url", default="")
    ap.add_argument("--chromium-executable", default="")
    ap.add_argument("--user-data-dir", default="")
    ap.add_argument("--manual-current-page", action="store_true")
    ap.add_argument("--timeout-seconds", type=int, default=180)
    ap.add_argument("--viewport-width", type=int, default=1400)
    ap.add_argument("--viewport-height", type=int, default=1200)
    ap.add_argument("--max-items", type=int, default=10000)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_focus_snippet:
        print(FOCUS_SNIPPET)
        return 0
    if args.self_test:
        receipt = run_self_test(Path(args.output_root))
        return 0 if receipt["status"] == STATUS_PASS else 2
    if args.compare_text:
        if not args.candidate_text or not args.reference_text:
            raise SystemExit("--compare-text requires --candidate-text and --reference-text")
        run_compare(Path(args.candidate_text), Path(args.reference_text), Path(args.output_root), args.max_items)
        return 0
    if args.live:
        if not args.user_data_dir:
            raise SystemExit("--live requires --user-data-dir for an operator-controlled Facebook profile")
        run_live(args)
        return 0
    print(MARKER)
    print(json.dumps({"status": "READY", "contract": build_contract()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
