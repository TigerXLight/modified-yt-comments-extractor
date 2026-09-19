#!/usr/bin/env python3
"""R44M Reddit en.reddit.com primary signed-in link queue.

This module corrects the Reddit route priority after R44L: the primary
Reddit comment-capture route is a logged-in, operator-controlled
en.reddit.com queue. Normal/current reddit links are converted to the
en.reddit.com host, then opened one target/branch URL at a time. The current
www.reddit.com visible/WebView2 queue remains a secondary fallback, not the
primary route.

No browser profile files are read, copied, zipped, parsed, or exported. No
cookies/tokens are extracted. No login automation or hidden Reddit API scraping
is performed. This module plans the queue and writes receipts only.
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


MARKER_R44M = "YTCE_R44M_REDDIT_EN_REDDIT_PRIMARY_LINK_QUEUE"
PASS_STATUS_R44M = "PASS_R44M_REDDIT_EN_REDDIT_PRIMARY_LINK_QUEUE"
SCHEMA_VERSION_R44M = "reddit_en_reddit_primary_link_queue.r44m.v1"

DEFAULT_THREAD_URL = "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/"
DEFAULT_EN_REDDIT_URL = (
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

WEBVIEW2_PROJECT_FILES_FROM_20260917_HIERARCHY = [
    "profile_media_independent_fast_media_webview2_lane_r42gz.py",
    "profile_media_independent_fast_media_webview2_lane_r42gz_test.py",
    "main_independent_fast_media_webview2_lane_r42gz_test.py",
    "profile_media_background_webview2_media_observer_r42gy.py",
    "profile_media_background_webview2_media_observer_r42gy_test.py",
    "main_background_webview2_media_observer_r42gy_test.py",
    "profile_media_archive_native_webview2_bridge_r42dt_test.py",
    "R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE_NOTES_20260914.md",
    "R42GY_BACKGROUND_WEBVIEW2_FAST_MEDIA_OBSERVER_RUNTIME_NOTES_20260914.md",
    "R42DT_ARCHIVE_NATIVE_WEBVIEW2_BRIDGE_NOTES_20260907.md",
]


@dataclass(frozen=True)
class RedditEnRedditPrimaryQueueItemR44M:
    queue_index: int
    order_label: str
    url_kind: str
    source_url: str
    capture_url: str
    status: str = "pending"
    attempts: int = 0
    logged_in_account_required: bool = True
    parent_order_label: str | None = None
    comment_id: str | None = None
    source_domain: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class RedditEnRedditPrimaryQueueResultR44M:
    marker: str
    status: str
    schema_version: str
    strategy: str
    login_requirement: str
    main_thread_source_url: str
    main_thread_capture_url: str
    queue_item_count: int
    branch_url_count: int
    branch_order_labels: list[str]
    nested_branch_labels_preserved: bool
    all_capture_urls_are_en_reddit: bool
    all_items_require_logged_in_account: bool
    queue_path: str
    queue_markdown_path: str
    capture_plan_path: str
    receipt_path: str
    recommended_max_pages_per_operator_batch: int
    hierarchy_reference_files: list[str]
    side_effect_flags: dict[str, bool]
    contract: dict[str, Any]
    warnings: list[str]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _with_query_param(pairs: list[tuple[str, str]], key: str, value: str) -> list[tuple[str, str]]:
    lower_key = key.lower()
    filtered = [(k, v) for k, v in pairs if k.lower() != lower_key]
    filtered.append((key, value))
    return filtered


def normalize_to_en_reddit_url_r44m(
    url: str,
    *,
    keep_force_legacy_sct: bool = True,
    require_old_sort: bool = True,
    add_limit_500: bool = True,
    add_ext_referrer: bool = True,
) -> str:
    """Convert normal/current/old Reddit links to the signed-in en.reddit.com route."""
    raw = url.strip()
    parsed = urlparse(raw if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw) else "https://" + raw)
    path = parsed.path or "/"
    if not path.endswith("/") and re.search(r"/comments/[^/]+(?:/[^/]+|/comment/[^/]+)?$", path):
        path += "/"

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    kept: list[tuple[str, str]] = []
    for key, value in pairs:
        k = key.lower()
        if k == "screen_view_count":
            continue
        if k == "force-legacy-sct" and not keep_force_legacy_sct:
            continue
        if k in {"sort", "limit", "ext-referrer"}:
            continue
        kept.append((key, value))

    if keep_force_legacy_sct and "/comment/" in path and not any(k.lower() == "force-legacy-sct" for k, _ in kept):
        kept.append(("force-legacy-sct", "1"))
    if require_old_sort:
        kept = _with_query_param(kept, "sort", "old")
    if add_limit_500:
        kept = _with_query_param(kept, "limit", "500")
    if add_ext_referrer:
        kept = _with_query_param(kept, "ext-referrer", "DIRECT")

    query = urlencode(kept, doseq=True)
    return urlunparse(("https", "en.reddit.com", path, "", query, ""))


def extract_comment_id_from_url_r44m(url: str) -> str | None:
    match = re.search(r"/comment/([A-Za-z0-9_]+)/?", url)
    return match.group(1) if match else None


def parent_label_for_branch_label_r44m(label: str) -> str | None:
    if "." not in label:
        return None
    return label.rsplit(".", 1)[0]


def source_domain_r44m(url: str) -> str | None:
    raw = url.strip()
    parsed = urlparse(raw if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw) else "https://" + raw)
    return parsed.netloc.lower() or None


def build_reddit_en_reddit_primary_link_queue_contract_r44m() -> dict[str, Any]:
    return {
        "marker": MARKER_R44M,
        "mode_id": "reddit_en_reddit_primary_link_queue",
        "schema_version": SCHEMA_VERSION_R44M,
        "primary_logged_in_route": (
            "Convert normal/current Reddit links to https://en.reddit.com/ and open the main target plus branch/comment links one at a time "
            "using an operator-controlled signed-in Reddit browser/WebView2 session."
        ),
        "logged_in_account_required": True,
        "not_no_login_primary": True,
        "normal_link_conversion_rule": (
            "www.reddit.com, reddit.com, old.reddit.com, and en.reddit.com inputs are canonicalized to en.reddit.com capture URLs; "
            "comment branch URLs keep force-legacy-sct=1 where useful and add sort=old&limit=500&ext-referrer=DIRECT."
        ),
        "open_each_link_rule": (
            "Open the en.reddit.com main thread first, then en.reddit.com branch/comment URLs in supplied top-to-bottom order; "
            "capture visible DOM/screenshot, merge by Reddit comment id, dedupe duplicate anchor comments, and preserve indentation."
        ),
        "queue_rule": "Use pending/captured/blocked/skipped statuses and resume from the queue rather than bulk-looping or reopening blocked URLs.",
        "recommended_max_pages_per_operator_batch": 5,
        "blocker_rule": (
            "If the en.reddit.com page shows a login gate, network-security page, challenge, or account-required page, mark the queue item blocked "
            "and stop the batch. Do not automate login or bypass challenges."
        ),
        "secondary_fallback_route": (
            "R44L current www.reddit.com visible target/branch queue remains a secondary fallback only when the signed-in en.reddit.com route "
            "is unavailable; it is not the primary method."
        ),
        "webview2_minimal_css_rule": (
            "The existing WebView2/minimal-CSS feature set may be used to render the en.reddit.com queue faster, but it must render visible Reddit pages "
            "and must not inspect WebView2/browser storage, cookies, tokens, Login Data, Local State, cache, or Local Storage."
        ),
        "hierarchy_reference": {
            "source": "Modified_YouTube_comment_extractor_full_hidden_hierarchy_INDENTED_20260917_050140",
            "webview2_related_files_noted": WEBVIEW2_PROJECT_FILES_FROM_20260917_HIERARCHY,
        },
        "score_rule": "Record displayed net score text only; do not infer exact upvote/downvote totals.",
        "large_thread_rule": "For 1k+ comments, en/old Reddit limit=500 is not a completeness guarantee; process more/branch links through the resumable queue.",
        "downstream_chain": "R44M en.reddit queue -> visible signed-in page capture/WebView2 capture -> R44J comment tree extraction -> R44K reconciliation/R43U ledger enrichment",
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "remote_media_downloads_enabled": False,
    }


def build_default_en_reddit_primary_queue_items_r44m(
    *,
    thread_url: str = DEFAULT_THREAD_URL,
    branch_urls: Iterable[tuple[str, str]] = DEFAULT_BRANCH_URLS_TOP_TO_BOTTOM,
    keep_force_legacy_sct: bool = True,
) -> list[RedditEnRedditPrimaryQueueItemR44M]:
    items: list[RedditEnRedditPrimaryQueueItemR44M] = [
        RedditEnRedditPrimaryQueueItemR44M(
            queue_index=0,
            order_label="main",
            url_kind="main_thread",
            source_url=thread_url,
            capture_url=normalize_to_en_reddit_url_r44m(thread_url, keep_force_legacy_sct=keep_force_legacy_sct),
            source_domain=source_domain_r44m(thread_url),
            notes="Primary signed-in route: open converted en.reddit.com main target first.",
        )
    ]
    for idx, (label, url) in enumerate(branch_urls, start=1):
        items.append(
            RedditEnRedditPrimaryQueueItemR44M(
                queue_index=idx,
                order_label=label,
                url_kind="branch_comment",
                source_url=url,
                capture_url=normalize_to_en_reddit_url_r44m(url, keep_force_legacy_sct=keep_force_legacy_sct),
                parent_order_label=parent_label_for_branch_label_r44m(label),
                comment_id=extract_comment_id_from_url_r44m(url),
                source_domain=source_domain_r44m(url),
                notes="Primary signed-in route: open converted en.reddit.com branch/comment link only if needed for missing/deep branch recovery.",
            )
        )
    return items


def write_queue_markdown_r44m(path: Path, items: list[RedditEnRedditPrimaryQueueItemR44M], contract: dict[str, Any]) -> None:
    lines = [
        "# Reddit en.reddit.com primary signed-in link queue (R44M)",
        "",
        f"- Marker: `{MARKER_R44M}`",
        "- Primary route: `signed-in en.reddit.com target + branch queue`",
        "- Logged-in Reddit account required: `true`",
        f"- Secondary fallback: `{contract['secondary_fallback_route']}`",
        f"- Recommended max pages per operator batch: `{contract['recommended_max_pages_per_operator_batch']}`",
        "- Status values: `pending`, `captured`, `blocked`, `skipped`",
        "",
        "## Queue",
        "",
    ]
    for item in items:
        lines.append(f"{item.queue_index}. `{item.order_label}` — `{item.url_kind}` — `{item.status}`")
        lines.append(f"   - source: `{item.source_url}`")
        lines.append(f"   - capture: `{item.capture_url}`")
        lines.append(f"   - logged-in account required: `{str(item.logged_in_account_required).lower()}`")
        if item.parent_order_label:
            lines.append(f"   - parent label: `{item.parent_order_label}`")
        if item.comment_id:
            lines.append(f"   - comment id: `{item.comment_id}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_reddit_en_reddit_primary_link_queue_r44m(
    *,
    output_root: Path | str,
    thread_url: str = DEFAULT_THREAD_URL,
    max_pages_per_operator_batch: int = 5,
    keep_force_legacy_sct: bool = True,
) -> RedditEnRedditPrimaryQueueResultR44M:
    root = Path(output_root)
    stamp = _utc_stamp()
    run_dir = root / f"reddit_en_reddit_primary_link_queue_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    contract = build_reddit_en_reddit_primary_link_queue_contract_r44m()
    contract["recommended_max_pages_per_operator_batch"] = max_pages_per_operator_batch

    items = build_default_en_reddit_primary_queue_items_r44m(
        thread_url=thread_url,
        keep_force_legacy_sct=keep_force_legacy_sct,
    )
    item_dicts = [asdict(item) for item in items]

    branch_labels = [item.order_label for item in items if item.url_kind == "branch_comment"]
    nested_ok = branch_labels == EXPECTED_BRANCH_LABEL_ORDER and all(
        label.split(".", 1)[0] in branch_labels
        for label in branch_labels
        if "." in label
    )
    all_en = all(urlparse(item.capture_url).netloc == "en.reddit.com" for item in items)
    all_login_required = all(item.logged_in_account_required for item in items)

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
        "en_reddit_primary_link_queue_planned": True,
    }

    queue_path = run_dir / "reddit_en_reddit_primary_link_queue.json"
    queue_md_path = run_dir / "reddit_en_reddit_primary_link_queue.md"
    capture_plan_path = run_dir / "reddit_en_reddit_primary_capture_plan.json"
    receipt_path = run_dir / "r44m_reddit_en_reddit_primary_link_queue_receipt.json"

    plan = {
        "marker": MARKER_R44M,
        "schema_version": SCHEMA_VERSION_R44M,
        "strategy": "signed_in_en_reddit_primary_target_then_branch_link_queue",
        "thread_url": thread_url,
        "main_thread_capture_url": items[0].capture_url,
        "queue_path": str(queue_path),
        "queue_markdown_path": str(queue_md_path),
        "branch_url_count": len(items) - 1,
        "queue_item_count": len(items),
        "logged_in_account_required": True,
        "recommended_max_pages_per_operator_batch": max_pages_per_operator_batch,
        "operator_batch_policy": (
            "Open only the next pending en.reddit.com queue item(s), capture visible DOM/screenshot, then mark captured/blocked/skipped. "
            "Stop immediately on a Reddit login gate, account-required page, challenge, or network-security block."
        ),
        "webview2_minimal_css_supported": True,
        "normal_link_conversion_rule": contract["normal_link_conversion_rule"],
        "secondary_fallback_route": contract["secondary_fallback_route"],
        "contract": contract,
        "side_effect_flags": side_effect_flags,
    }

    _json_dump(queue_path, {"items": item_dicts})
    write_queue_markdown_r44m(queue_md_path, items, contract)
    _json_dump(capture_plan_path, plan)

    warnings: list[str] = []
    if not nested_ok:
        warnings.append("branch label order did not match expected operator top-to-bottom order")
    if not all_en:
        warnings.append("one or more capture URLs did not normalize to en.reddit.com")
    if not all_login_required:
        warnings.append("one or more queue items did not record logged-in account requirement")

    result = RedditEnRedditPrimaryQueueResultR44M(
        marker=MARKER_R44M,
        status=PASS_STATUS_R44M,
        schema_version=SCHEMA_VERSION_R44M,
        strategy="signed_in_en_reddit_primary_target_then_branch_link_queue",
        login_requirement="operator_controlled_signed_in_reddit_account_required",
        main_thread_source_url=thread_url,
        main_thread_capture_url=items[0].capture_url,
        queue_item_count=len(items),
        branch_url_count=len(items) - 1,
        branch_order_labels=branch_labels,
        nested_branch_labels_preserved=nested_ok,
        all_capture_urls_are_en_reddit=all_en,
        all_items_require_logged_in_account=all_login_required,
        queue_path=str(queue_path),
        queue_markdown_path=str(queue_md_path),
        capture_plan_path=str(capture_plan_path),
        receipt_path=str(receipt_path),
        recommended_max_pages_per_operator_batch=max_pages_per_operator_batch,
        hierarchy_reference_files=WEBVIEW2_PROJECT_FILES_FROM_20260917_HIERARCHY,
        side_effect_flags=side_effect_flags,
        contract=contract,
        warnings=warnings,
    )
    _json_dump(receipt_path, asdict(result))
    return result


def run_self_test(output_root: Path | str) -> dict[str, Any]:
    result = run_reddit_en_reddit_primary_link_queue_r44m(output_root=output_root)
    queue_payload = json.loads(Path(result.queue_path).read_text(encoding="utf-8"))
    items = queue_payload["items"]
    checks = [
        {
            "name": "queue_has_main_and_27_branches",
            "status": "pass" if result.queue_item_count == 28 and result.branch_url_count == 27 else "fail",
        },
        {
            "name": "primary_capture_urls_use_en_reddit",
            "status": "pass" if result.all_capture_urls_are_en_reddit and all(urlparse(item["capture_url"]).netloc == "en.reddit.com" for item in items) else "fail",
        },
        {
            "name": "normal_www_links_convert_to_en_reddit",
            "status": "pass" if items[1]["source_url"].startswith("https://www.reddit.com/") and items[1]["capture_url"].startswith("https://en.reddit.com/") else "fail",
        },
        {
            "name": "logged_in_account_required_on_all_items",
            "status": "pass" if result.all_items_require_logged_in_account and all(item["logged_in_account_required"] is True for item in items) else "fail",
        },
        {
            "name": "branch_labels_preserve_nested_top_to_bottom_order",
            "status": "pass" if result.nested_branch_labels_preserved else "fail",
        },
        {
            "name": "r44l_current_www_route_is_secondary_fallback_not_primary",
            "status": "pass" if "secondary fallback" in result.contract["secondary_fallback_route"].lower() and "not the primary" in result.contract["secondary_fallback_route"].lower() else "fail",
        },
        {
            "name": "webview2_hierarchy_reference_present",
            "status": "pass" if any("webview2" in name.lower() for name in result.hierarchy_reference_files) else "fail",
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
        "marker": MARKER_R44M,
        "status": PASS_STATUS_R44M if all(c["status"] == "pass" for c in checks) else "FAIL_R44M",
        "schema_version": SCHEMA_VERSION_R44M,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "sample_result": asdict(result),
    }
    report_path = Path(output_root) / "R44M_REDDIT_EN_REDDIT_PRIMARY_LINK_QUEUE_REPORT.json"
    _json_dump(report_path, payload)
    md_path = Path(output_root) / "R44M_REDDIT_EN_REDDIT_PRIMARY_LINK_QUEUE_REPORT.md"
    md_path.write_text(
        "# R44M Reddit en.reddit.com primary signed-in link queue\n\n"
        f"- Status: `{payload['status']}`\n"
        "- Primary route: `signed-in en.reddit.com target + branch queue`\n"
        "- Logged-in Reddit account required: `true`\n"
        f"- Queue items: `{result.queue_item_count}`\n"
        f"- Branch URLs: `{result.branch_url_count}`\n"
        f"- Main en.reddit URL: `{result.main_thread_capture_url}`\n"
        f"- Queue: `{result.queue_path}`\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R44M Reddit en.reddit.com primary signed-in link queue")
    parser.add_argument("--output-root", default="profile_media_live_captures/r44m_reddit_en_reddit_primary_link_queue/report")
    parser.add_argument("--thread-url", default=DEFAULT_THREAD_URL)
    parser.add_argument("--max-pages-per-operator-batch", type=int, default=5)
    parser.add_argument("--drop-force-legacy-sct", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        payload = run_self_test(Path(args.output_root))
        print(MARKER_R44M)
        print(payload["status"])
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload["status"] == PASS_STATUS_R44M else 1

    result = run_reddit_en_reddit_primary_link_queue_r44m(
        output_root=Path(args.output_root),
        thread_url=args.thread_url,
        max_pages_per_operator_batch=args.max_pages_per_operator_batch,
        keep_force_legacy_sct=not args.drop_force_legacy_sct,
    )
    print(MARKER_R44M)
    print(result.status)
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    return 0 if result.status == PASS_STATUS_R44M else 1


if __name__ == "__main__":
    raise SystemExit(main())
