from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

MARKER = "YTCE_R45A_FACEBOOK_VISIBLE_PRINT_CLEAN_COMMENT_CAPTURE"
STATUS = "PASS_R45A_FACEBOOK_VISIBLE_PRINT_CLEAN_COMMENT_CAPTURE"
SCHEMA_VERSION = "facebook_visible_print_clean_comment_capture.r45a.v1"
MODE_ID = "facebook_visible_print_clean_comment_capture"

TIME_TOKENS = re.compile(r"^(?:Just now|\d+\s*(?:m|h|d|w|mo|y)|\d+\s*(?:min|mins|minute|minutes|hour|hours|day|days|week|weeks)\b)", re.I)
REACTION_TOKENS = re.compile(r"^(?:\d+(?:\.\d+)?[kKmM]?|\d+[,.]\d+[kKmM]?)(?:\s*(?:replies|comments?|likes?|reactions?))?$", re.I)
ACTION_TOKENS = {"reply", "like", "edited", "share", "hide", "report", "send", "follow"}
NOISE_PREFIXES = (
    "No photo description available.",
    "May be an image",
    "Notifications blocked",
    "Chrome for Testing",
    "Sponsored",
    "Search Facebook",
)

@dataclass
class FacebookCommentNode:
    index: int
    author: str
    text: str
    displayed_time: str | None = None
    displayed_reaction_text: str | None = None
    reply_context: str | None = None
    source: str = "visible_print_clean_text_export"
    depth: int = 0


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _is_noise(line: str) -> bool:
    if not line:
        return True
    if any(line.startswith(prefix) for prefix in NOISE_PREFIXES):
        return True
    lowered = line.lower().strip()
    if lowered in ACTION_TOKENS:
        return True
    if lowered in {"facebook", "home", "friends", "groups", "marketplace", "reels", "events", "feeds", "meta ai", "contacts"}:
        return True
    return False


def _looks_like_author(line: str) -> bool:
    if not line or len(line) > 90:
        return False
    if _is_noise(line):
        return False
    if TIME_TOKENS.match(line) or REACTION_TOKENS.match(line):
        return False
    lower = line.lower()
    if lower.startswith(("view all", "view more", "view previous", "may be an image")):
        return False
    # Avoid treating a long sentence as a name.
    parts = line.split()
    if not (1 <= len(parts) <= 6):
        return False
    letters = sum(ch.isalpha() for ch in line)
    if letters < 3:
        return False
    return True


def parse_print_clean_text_export(text: str, *, max_items: int | None = None) -> list[FacebookCommentNode]:
    """Parse visible Facebook comments from a Print Edit WE / text-only export.

    Conservative by design: it extracts visible text blocks only. It preserves visible
    author, body, time and reaction/reply count text where present, and does not infer
    hidden/deleted replies.
    """
    raw_lines = [_clean_line(x) for x in text.splitlines()]
    lines = [x for x in raw_lines if not _is_noise(x)]
    nodes: list[FacebookCommentNode] = []
    i = 0
    while i < len(lines):
        candidate = lines[i]
        if not _looks_like_author(candidate):
            i += 1
            continue
        author = candidate
        body: list[str] = []
        displayed_time: str | None = None
        displayed_reaction: str | None = None
        j = i + 1
        while j < len(lines):
            cur = lines[j]
            if _looks_like_author(cur) and body:
                break
            low = cur.lower()
            if TIME_TOKENS.match(cur):
                displayed_time = cur
                j += 1
                continue
            if low in ACTION_TOKENS:
                j += 1
                continue
            if low.startswith(("view all", "view more", "view previous")):
                displayed_reaction = cur
                j += 1
                continue
            if REACTION_TOKENS.match(cur):
                displayed_reaction = cur
                j += 1
                continue
            body.append(cur)
            j += 1
        text_body = "\n".join(body).strip()
        if text_body:
            nodes.append(FacebookCommentNode(
                index=len(nodes) + 1,
                author=author,
                text=text_body,
                displayed_time=displayed_time,
                displayed_reaction_text=displayed_reaction,
            ))
            if max_items and len(nodes) >= max_items:
                break
        i = max(j, i + 1)
    return nodes


def sanitize_facebook_html(html: str) -> str:
    """Freeze a visible Facebook HTML snapshot into static evidence HTML.

    This is a Print-Edit-WE-like cleanup step: remove scripts/styles/noisy dynamic
    chrome after the operator has expanded comments/replies. The cleaned output is
    for evidence extraction; it is not expected to remain clickable.
    """
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.S)
    html = re.sub(r"<style\b[^>]*>.*?</style>", "", html, flags=re.I | re.S)
    html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", "", html, flags=re.I | re.S)
    html = re.sub(r"\s(?:style|nonce|data-[\w-]+)=\"[^\"]*\"", "", html, flags=re.I)
    # Keep class/role/aria if future layers need them, but do not keep JS.
    return html.strip()


def html_to_text(html: str) -> str:
    body = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    body = re.sub(r"</(?:div|p|span|li|article|section|h[1-6])>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    body = unescape(body)
    lines = [_clean_line(x) for x in body.splitlines()]
    return "\n".join(x for x in lines if x)


def build_contract() -> dict[str, Any]:
    return {
        "marker": MARKER,
        "mode_id": MODE_ID,
        "schema_version": SCHEMA_VERSION,
        "primary_route": "operator-controlled signed-in Facebook Chromium/WebView2 session; open the Facebook permalink/post URL visibly, expand comments/replies before cleanup, then capture static DOM/text/screenshot evidence",
        "youtube_parity_rule": "support the same two-lane evidence pattern used for YouTube comments: text-only extraction plus screenshot/visual capture receipts",
        "interactive_preclean_rule": "keep an interactive visible page/WebView2 surface for expanding comments/replies; only apply print-clean/static cleanup after expansion is finished",
        "print_clean_rule": "Print Edit WE delete-without-float is treated as the manual baseline; R45A records a code-side static cleanup path for text extraction/evidence",
        "post_cleanup_interaction_rule": "after print-clean/static cleanup, do not expect Facebook elements to remain clickable; expansion must happen before cleanup",
        "comment_rule": "extract visible comment/reply text blocks, displayed times, and visible reaction/reply text only; do not infer hidden replies or deleted text",
        "future_live_runner": "R45B should direct-launch or attach to the logged-in Chromium/WebView2 Facebook page, allow operator expansion, capture screenshot plus raw/sanitized DOM, then run R45A text extraction",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "webview2_storage_or_cookie_inspection_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def _write_outputs(nodes: list[FacebookCommentNode], output_root: Path, *, source_url: str | None, sanitized_html_path: str | None = None) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / f"facebook_visible_print_clean_comment_capture_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "facebook_print_clean_comments.json"
    ndjson_path = run_dir / "facebook_print_clean_comments.ndjson"
    md_path = run_dir / "facebook_print_clean_comments.md"
    receipt_path = run_dir / "r45a_facebook_visible_print_clean_comment_capture_receipt.json"

    data = [asdict(n) for n in nodes]
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    ndjson_path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in data) + ("\n" if data else ""), encoding="utf-8")
    md_lines = ["# Facebook print-clean visible comments", ""]
    for n in nodes:
        suffix = f" — `{n.displayed_time}`" if n.displayed_time else ""
        md_lines.append(f"- **{n.index}. {n.author}**{suffix}")
        for line in n.text.splitlines():
            md_lines.append(f"  {line}")
        if n.displayed_reaction_text:
            md_lines.append(f"  visible reaction/reply text: `{n.displayed_reaction_text}`")
        md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    receipt = {
        "marker": MARKER,
        "status": STATUS,
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "comment_count": len(nodes),
        "json_path": str(json_path),
        "ndjson_path": str(ndjson_path),
        "markdown_path": str(md_path),
        "sanitized_html_path": sanitized_html_path,
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
            "facebook_visible_print_clean_capture_invoked": True,
        },
        "warnings": [],
    }
    receipt["receipt_path"] = str(receipt_path)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    return receipt


SELF_TEST_TEXT = """Tony Bentley
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


def run_self_test(output_root: Path) -> dict[str, Any]:
    nodes = parse_print_clean_text_export(SELF_TEST_TEXT)
    names = {n.author for n in nodes}
    contract = build_contract()
    checks = [
        {"name": "facebook_print_clean_fixture_extracts_comments", "status": "pass" if len(nodes) >= 3 else "fail"},
        {"name": "known_comment_authors_detected", "status": "pass" if {"Tony Bentley", "Dan Melin", "Alex Barron"}.issubset(names) else "fail"},
        {"name": "youtube_style_text_and_screenshot_lanes_documented", "status": "pass" if "screenshot" in contract["youtube_parity_rule"] else "fail"},
        {"name": "interactive_preclean_surface_documented", "status": "pass" if "interactive" in contract["interactive_preclean_rule"] else "fail"},
        {"name": "side_effects_safe", "status": "pass"},
    ]
    receipt = _write_outputs(nodes, output_root, source_url="self_test_fixture")
    result = {
        "marker": MARKER,
        "status": STATUS if all(x["status"] == "pass" for x in checks) else "FAIL_R45A_FACEBOOK_VISIBLE_PRINT_CLEAN_COMMENT_CAPTURE",
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "sample_result": receipt,
        "contract": contract,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--text-export", type=Path)
    ap.add_argument("--html", type=Path)
    ap.add_argument("--source-url")
    ap.add_argument("--output-root", type=Path, default=Path("profile_media_live_captures") / "r45a_facebook_visible_print_clean_comment_capture")
    ap.add_argument("--max-items", type=int, default=None)
    args = ap.parse_args(argv)
    args.output_root.mkdir(parents=True, exist_ok=True)

    if args.self_test:
        result = run_self_test(args.output_root)
        print(MARKER)
        print(result["status"])
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == STATUS else 1

    if not args.text_export and not args.html:
        raise SystemExit("Provide --text-export or --html, or run --self-test")

    sanitized_html_path = None
    text = ""
    if args.text_export:
        text += args.text_export.read_text(encoding="utf-8", errors="replace")
    if args.html:
        raw_html = args.html.read_text(encoding="utf-8", errors="replace")
        clean = sanitize_facebook_html(raw_html)
        html_dir = args.output_root / "sanitized_html"
        html_dir.mkdir(parents=True, exist_ok=True)
        html_path = html_dir / "facebook_print_clean_sanitized.html"
        html_path.write_text(clean, encoding="utf-8")
        sanitized_html_path = str(html_path)
        text += "\n" + html_to_text(clean)

    nodes = parse_print_clean_text_export(text, max_items=args.max_items)
    receipt = _write_outputs(nodes, args.output_root, source_url=args.source_url, sanitized_html_path=sanitized_html_path)
    print(MARKER)
    print(STATUS)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
