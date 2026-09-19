#!/usr/bin/env python3
"""R44L Reddit normal-site link queue fallback.

This module plans the public/current Reddit fallback for cases where a signed-in
old/en Reddit profile is unavailable or old Reddit is gated. It does not log in,
read browser profile files, extract cookies/tokens, scrape hidden APIs, or
download remote media. It writes a resumable target/branch URL queue that can be
processed by a visible browser/WebView2 operator workflow one link at a time.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


MARKER_R44L = "YTCE_R44L_REDDIT_NORMAL_SITE_LINK_QUEUE_FALLBACK"
PASS_STATUS_R44L = "PASS_R44L_REDDIT_NORMAL_SITE_LINK_QUEUE_FALLBACK"
SCHEMA_VERSION_R44L = "reddit_normal_site_link_queue_fallback.r44l.v1"

DEFAULT_THREAD_URL = "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/"
DEFAULT_OLD_REDDIT_URL = (
    "https://en.reddit.com/r/EdSheeran/comments/1whbgzk/"
    "eds_got_a_show_in_4_days_no_band_no_openers_what/"
    "?sort=old&screen_view_count=1&limit=500&ext-referrer=DIRECT"
)

DEFAULT_BRANCH_URLS_TOP_TO_BOTTOM: list[tuple[str, str]] = [
    ("1", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/?force-legacy-sct=1"),
    ("2", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa15vni/?force-legacy-sct=1"),
    ("2.1", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa19tv2/?force-legacy-sct=1"),
    ("3", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa18iy8/?force-legacy-sct=1"),
    ("3.1", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1d4r7/?force-legacy-sct=1"),
    ("4", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17z4o/?force-legacy-sct=1"),
    ("4.1", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1bbed/?force-legacy-sct=1"),
    ("5", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1hh1w/?force-legacy-sct=1"),
    ("6", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17mb8/?force-legacy-sct=1"),
    ("7", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1o7nd/?force-legacy-sct=1"),
    ("8", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa207qo/?force-legacy-sct=1"),
    ("8.1", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa2634c/?force-legacy-sct=1"),
    ("9", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1efmx/?force-legacy-sct=1"),
    ("10", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14jw3/?force-legacy-sct=1"),
    ("10.1", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa18c1v/?force-legacy-sct=1"),
    ("11", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14kee/?force-legacy-sct=1"),
    ("12", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14guu/?force-legacy-sct=1"),
    ("12.1", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa162nx/?force-legacy-sct=1"),
    ("13", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17wkq/?force-legacy-sct=1"),
    ("13.1", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1ejdr/?force-legacy-sct=1"),
    ("14", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14xsv/?force-legacy-sct=1"),
    ("15", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14iyr/?force-legacy-sct=1"),
    ("16", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/paamt85/?force-legacy-sct=1"),
    ("17", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa15jpo/?force-legacy-sct=1"),
    ("18", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa168md/?force-legacy-sct=1"),
    ("19", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1gsvr/?force-legacy-sct=1"),
    ("20", "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa158vo/?force-legacy-sct=1"),
]

EXPECTED_BRANCH_LABEL_ORDER = [label for label, _ in DEFAULT_BRANCH_URLS_TOP_TO_BOTTOM]


@dataclass(frozen=True)
class RedditNormalSiteQueueItemR44L:
    queue_index: int
    order_label: str
    url_kind: str
    source_url: str
    capture_url: str
    status: str = "pending"
    attempts: int = 0
    parent_order_label: str | None = None
    comment_id: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class RedditNormalSiteQueueResultR44L:
    marker: str
    status: str
    schema_version: str
    strategy: str
    main_thread_url: str
    old_reddit_url_reference: str
    queue_item_count: int
    branch_url_count: int
    branch_order_labels: list[str]
    nested_branch_labels_preserved: bool
    queue_path: str
    queue_markdown_path: str
    capture_plan_path: str
    receipt_path: str
    recommended_max_pages_per_operator_batch: int
    side_effect_flags: dict[str, bool]
    contract: dict[str, Any]
    warnings: list[str]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def normalize_to_current_reddit_url_r44l(url: str, *, keep_force_legacy_sct: bool = True) -> str:
    """Normalize en/old/current Reddit URLs to a current www.reddit.com capture URL."""
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse("https://" + url.strip())
    netloc = parsed.netloc.lower()
    if netloc in {"en.reddit.com", "old.reddit.com", "reddit.com"}:
        netloc = "www.reddit.com"
    elif netloc.endswith(".reddit.com") and netloc != "www.reddit.com":
        netloc = "www.reddit.com"

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    kept: list[tuple[str, str]] = []
    for key, value in pairs:
        k = key.lower()
        if k in {"screen_view_count", "ext-referrer", "limit"}:
            continue
        if k == "force-legacy-sct" and not keep_force_legacy_sct:
            continue
        kept.append((key, value))
    path = parsed.path or "/"
    if not path.endswith("/") and re.search(r"/comments/[^/]+(?:/[^/]+)?$", path):
        path += "/"
    query = urlencode(kept, doseq=True)
    return urlunparse(("https", netloc, path, "", query, ""))


def extract_comment_id_from_url_r44l(url: str) -> str | None:
    match = re.search(r"/comment/([A-Za-z0-9_]+)/?", url)
    return match.group(1) if match else None


def parent_label_for_branch_label_r44l(label: str) -> str | None:
    if "." not in label:
        return None
    return label.rsplit(".", 1)[0]


def build_reddit_normal_site_link_queue_contract_r44l() -> dict[str, Any]:
    return {
        "marker": MARKER_R44L,
        "mode_id": "reddit_normal_site_link_queue_fallback",
        "schema_version": SCHEMA_VERSION_R44L,
        "primary_logged_in_route": "R44I direct-launch old/en Reddit target URL with an operator-controlled browser profile",
        "normal_site_fallback_route": "current www.reddit.com target/branch URLs opened one link at a time in a visible browser/WebView2 surface",
        "webview2_minimal_css_rule": (
            "A WebView2/minimal-CSS view may be used to reduce rendering overhead, but it must still render public/visible Reddit pages "
            "and must not inspect browser profile storage, cookies, tokens, Login Data, Local State, cache, or local storage."
        ),
        "open_each_link_rule": (
            "Open the main thread/current URL first, then branch/comment URLs in the supplied top-to-bottom order; capture the visible page, "
            "merge by Reddit comment id, dedupe duplicate anchor comments, and preserve indentation."
        ),
        "queue_rule": "Use pending/captured/blocked/skipped statuses and resume from the queue rather than bulk-looping or reopening blocked URLs.",
        "recommended_max_pages_per_operator_batch": 5,
        "blocker_rule": "If a login gate, network-security page, or challenge is detected, mark that queue item blocked and stop the batch.",
        "score_rule": "Record displayed net score text only; do not infer exact upvote/downvote totals.",
        "large_thread_rule": "For 1k+ comments, old Reddit limit=500 is not a completeness guarantee; process more/branch links through the resumable queue.",
        "downstream_chain": "R44L queue -> visible current Reddit page capture -> R44J comment tree extraction -> R44K reconciliation/R43U ledger enrichment",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def build_default_normal_site_queue_items_r44l(
    *,
    thread_url: str = DEFAULT_THREAD_URL,
    old_reddit_url_reference: str = DEFAULT_OLD_REDDIT_URL,
    branch_urls: Iterable[tuple[str, str]] = DEFAULT_BRANCH_URLS_TOP_TO_BOTTOM,
    keep_force_legacy_sct: bool = True,
) -> list[RedditNormalSiteQueueItemR44L]:
    items: list[RedditNormalSiteQueueItemR44L] = [
        RedditNormalSiteQueueItemR44L(
            queue_index=0,
            order_label="main",
            url_kind="main_thread",
            source_url=thread_url,
            capture_url=normalize_to_current_reddit_url_r44l(thread_url, keep_force_legacy_sct=keep_force_legacy_sct),
            notes="Open/capture current Reddit main thread first; use visible sort controls or URL params when available.",
        )
    ]
    for idx, (label, url) in enumerate(branch_urls, start=1):
        items.append(
            RedditNormalSiteQueueItemR44L(
                queue_index=idx,
                order_label=label,
                url_kind="branch_comment",
                source_url=url,
                capture_url=normalize_to_current_reddit_url_r44l(url, keep_force_legacy_sct=keep_force_legacy_sct),
                parent_order_label=parent_label_for_branch_label_r44l(label),
                comment_id=extract_comment_id_from_url_r44l(url),
                notes="Open as a separate current Reddit branch/comment page if the main page did not expose this branch.",
            )
        )
    return items


def write_queue_markdown_r44l(path: Path, items: list[RedditNormalSiteQueueItemR44L], contract: dict[str, Any]) -> None:
    lines = [
        "# Reddit normal-site visible link queue (R44L)",
        "",
        f"- Marker: `{MARKER_R44L}`",
        f"- Strategy: `{contract['normal_site_fallback_route']}`",
        f"- Recommended max pages per operator batch: `{contract['recommended_max_pages_per_operator_batch']}`",
        "- Status values: `pending`, `captured`, `blocked`, `skipped`",
        "",
        "## Queue",
        "",
    ]
    for item in items:
        lines.append(
            f"{item.queue_index}. `{item.order_label}` — `{item.url_kind}` — `{item.status}`"
        )
        lines.append(f"   - source: `{item.source_url}`")
        lines.append(f"   - capture: `{item.capture_url}`")
        if item.parent_order_label:
            lines.append(f"   - parent label: `{item.parent_order_label}`")
        if item.comment_id:
            lines.append(f"   - comment id: `{item.comment_id}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_reddit_normal_site_link_queue_fallback_r44l(
    *,
    output_root: Path | str,
    thread_url: str = DEFAULT_THREAD_URL,
    old_reddit_url_reference: str = DEFAULT_OLD_REDDIT_URL,
    max_pages_per_operator_batch: int = 5,
    keep_force_legacy_sct: bool = True,
) -> RedditNormalSiteQueueResultR44L:
    root = Path(output_root)
    stamp = _utc_stamp()
    run_dir = root / f"reddit_normal_site_link_queue_fallback_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    contract = build_reddit_normal_site_link_queue_contract_r44l()
    contract["recommended_max_pages_per_operator_batch"] = max_pages_per_operator_batch

    items = build_default_normal_site_queue_items_r44l(
        thread_url=thread_url,
        old_reddit_url_reference=old_reddit_url_reference,
        keep_force_legacy_sct=keep_force_legacy_sct,
    )
    item_dicts = [asdict(item) for item in items]

    branch_labels = [item.order_label for item in items if item.url_kind == "branch_comment"]
    nested_ok = branch_labels == EXPECTED_BRANCH_LABEL_ORDER and all(
        label.split(".", 1)[0] in branch_labels
        for label in branch_labels
        if "." in label
    )

    side_effect_flags = {
        "browser_session_started": False,
        "network_actions_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "browser_profile_files_read_or_copied": False,
        "browser_profile_files_parsed_by_tool": False,
        "remote_media_downloads_performed": False,
        "webview2_internals_copied": False,
        "normal_reddit_link_queue_planned": True,
    }

    queue_path = run_dir / "reddit_normal_site_link_queue.json"
    queue_md_path = run_dir / "reddit_normal_site_link_queue.md"
    capture_plan_path = run_dir / "reddit_normal_site_capture_plan.json"
    receipt_path = run_dir / "r44l_reddit_normal_site_link_queue_receipt.json"

    plan = {
        "marker": MARKER_R44L,
        "schema_version": SCHEMA_VERSION_R44L,
        "strategy": "current_reddit_visible_link_queue_target_then_branches",
        "thread_url": thread_url,
        "old_reddit_url_reference": old_reddit_url_reference,
        "normal_thread_capture_url": items[0].capture_url,
        "queue_path": str(queue_path),
        "queue_markdown_path": str(queue_md_path),
        "branch_url_count": len(items) - 1,
        "queue_item_count": len(items),
        "recommended_max_pages_per_operator_batch": max_pages_per_operator_batch,
        "operator_batch_policy": (
            "Open only the next pending queue item(s), capture visible DOM/screenshot, then mark captured/blocked/skipped. "
            "Stop immediately on a Reddit login gate or network-security block."
        ),
        "webview2_minimal_css_supported": True,
        "contract": contract,
        "side_effect_flags": side_effect_flags,
    }

    _json_dump(queue_path, {"items": item_dicts})
    write_queue_markdown_r44l(queue_md_path, items, contract)
    _json_dump(capture_plan_path, plan)

    warnings: list[str] = []
    if not nested_ok:
        warnings.append("branch label order did not match expected operator top-to-bottom order")

    result = RedditNormalSiteQueueResultR44L(
        marker=MARKER_R44L,
        status=PASS_STATUS_R44L,
        schema_version=SCHEMA_VERSION_R44L,
        strategy="current_reddit_visible_link_queue_target_then_branches",
        main_thread_url=items[0].capture_url,
        old_reddit_url_reference=old_reddit_url_reference,
        queue_item_count=len(items),
        branch_url_count=len(items) - 1,
        branch_order_labels=branch_labels,
        nested_branch_labels_preserved=nested_ok,
        queue_path=str(queue_path),
        queue_markdown_path=str(queue_md_path),
        capture_plan_path=str(capture_plan_path),
        receipt_path=str(receipt_path),
        recommended_max_pages_per_operator_batch=max_pages_per_operator_batch,
        side_effect_flags=side_effect_flags,
        contract=contract,
        warnings=warnings,
    )
    _json_dump(receipt_path, asdict(result))
    return result


def run_self_test(output_root: Path | str) -> dict[str, Any]:
    result = run_reddit_normal_site_link_queue_fallback_r44l(output_root=output_root)
    queue_payload = json.loads(Path(result.queue_path).read_text(encoding="utf-8"))
    items = queue_payload["items"]
    checks = [
        {
            "name": "queue_has_main_and_27_branches",
            "status": "pass" if result.queue_item_count == 28 and result.branch_url_count == 27 else "fail",
        },
        {
            "name": "normal_site_urls_use_www_reddit",
            "status": "pass" if all(urlparse(item["capture_url"]).netloc == "www.reddit.com" for item in items) else "fail",
        },
        {
            "name": "branch_labels_preserve_nested_top_to_bottom_order",
            "status": "pass" if result.nested_branch_labels_preserved else "fail",
        },
        {
            "name": "pending_statuses_are_resumable",
            "status": "pass" if all(item["status"] == "pending" for item in items) else "fail",
        },
        {
            "name": "normal_site_fallback_is_blocker_aware",
            "status": "pass" if "blocked" in result.contract["queue_rule"] and "network-security" in result.contract["blocker_rule"] else "fail",
        },
        {
            "name": "webview2_minimal_css_rule_present",
            "status": "pass" if "WebView2" in result.contract["webview2_minimal_css_rule"] else "fail",
        },
        {
            "name": "side_effects_safe",
            "status": "pass" if not any(
                result.side_effect_flags[name]
                for name in [
                    "browser_session_started",
                    "network_actions_performed",
                    "hidden_platform_api_scraping_performed",
                    "login_automation_performed",
                    "cookie_or_token_extraction_performed",
                    "browser_profile_files_read_or_copied",
                    "browser_profile_files_parsed_by_tool",
                    "remote_media_downloads_performed",
                    "webview2_internals_copied",
                ]
            ) else "fail",
        },
    ]
    payload = {
        "marker": MARKER_R44L,
        "status": PASS_STATUS_R44L if all(c["status"] == "pass" for c in checks) else "FAIL_R44L",
        "schema_version": SCHEMA_VERSION_R44L,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "sample_result": asdict(result),
    }
    report_path = Path(output_root) / "R44L_REDDIT_NORMAL_SITE_LINK_QUEUE_REPORT.json"
    _json_dump(report_path, payload)
    md_path = Path(output_root) / "R44L_REDDIT_NORMAL_SITE_LINK_QUEUE_REPORT.md"
    md_path.write_text(
        "# R44L Reddit normal-site link queue fallback\n\n"
        f"- Status: `{payload['status']}`\n"
        f"- Queue items: `{result.queue_item_count}`\n"
        f"- Branch URLs: `{result.branch_url_count}`\n"
        f"- Main current Reddit URL: `{result.main_thread_url}`\n"
        f"- Queue: `{result.queue_path}`\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R44L Reddit normal-site link queue fallback")
    parser.add_argument("--output-root", default="profile_media_live_captures/r44l_reddit_normal_site_link_queue_fallback/report")
    parser.add_argument("--thread-url", default=DEFAULT_THREAD_URL)
    parser.add_argument("--old-reddit-url-reference", default=DEFAULT_OLD_REDDIT_URL)
    parser.add_argument("--max-pages-per-operator-batch", type=int, default=5)
    parser.add_argument("--drop-force-legacy-sct", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        payload = run_self_test(Path(args.output_root))
        print(MARKER_R44L)
        print(payload["status"])
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload["status"] == PASS_STATUS_R44L else 1

    result = run_reddit_normal_site_link_queue_fallback_r44l(
        output_root=Path(args.output_root),
        thread_url=args.thread_url,
        old_reddit_url_reference=args.old_reddit_url_reference,
        max_pages_per_operator_batch=args.max_pages_per_operator_batch,
        keep_force_legacy_sct=not args.drop_force_legacy_sct,
    )
    print(MARKER_R44L)
    print(result.status)
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    return 0 if result.status == PASS_STATUS_R44L else 1


if __name__ == "__main__":
    raise SystemExit(main())
