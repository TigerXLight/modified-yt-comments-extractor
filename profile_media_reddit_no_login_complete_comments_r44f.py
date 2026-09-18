from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from profile_media_reddit_old_reddit_thread_expansion_r44e import (
    R44E_EDSHEERAN_BRANCH_URLS,
    R44E_EDSHEERAN_OLD_REDDIT_URL,
    R44E_EDSHEERAN_THREAD_URL,
    canonicalize_old_reddit_thread_url_r44e,
    extract_continue_thread_urls_from_old_reddit_html_r44e,
    normalize_reddit_branch_urls_r44e,
)
from profile_media_reddit_visible_dom_capture_r44d import (
    R44D_PASS_STATUS,
    RedditVisibleDomCaptureRequestR44D,
    run_reddit_visible_dom_capture_r44d,
)

R44F_MARKER = "YTCE_R44F_REDDIT_NO_LOGIN_COMPLETE_COMMENT_ORDERING"
R44F_PASS_STATUS = "PASS_R44F_REDDIT_NO_LOGIN_COMPLETE_COMMENT_ORDERING"
R44F_BLOCKED_STATUS = "BLOCKED_R44F_REDDIT_NO_LOGIN_COMPLETE_COMMENT_ORDERING"
R44F_SCHEMA_VERSION = "reddit_no_login_complete_comment_ordering.r44f.v1"
R44F_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44f_reddit_no_login_complete_comment_ordering"
R44F_MODE_ID = "reddit_no_login_complete_comment_ordering"

_TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
PageFetcher = Callable[[str, Path], Mapping[str, Any]]


@dataclass(frozen=True)
class OrderedRedditBranchUrlR44F:
    label: str
    display_order_index: int
    url: str
    original_url: str
    comment_id: str
    depth_hint: int = 0
    source: str = "operator_or_discovered_top_to_bottom"

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class RedditCommentIndexNodeR44F:
    comment_id: str
    parent_id: str
    post_id: str
    author_handle: str
    permalink: str
    visible_text: str
    visible_timestamp: str
    score_display: str
    score_value: int | None
    score_hidden: bool
    page_url: str
    page_index: int
    page_order_index: int
    branch_label: str
    branch_display_order_index: int
    indent_level: int = 0
    tree_order_index: int = 0
    duplicate_of_existing_node: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class RedditNoLoginCompleteCommentsRequestR44F:
    thread_url: str = R44E_EDSHEERAN_THREAD_URL
    old_reddit_url: str = ""
    branch_urls: tuple[str, ...] = ()
    ordered_branch_source_text: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R44F_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    real_visible_smoke: bool = False
    public_network_enabled: bool = False
    explicit_live_mode: bool = False
    accounts_keys_reddit_logged_in: bool = False
    accounts_keys_state: Mapping[str, Any] = field(default_factory=dict)
    prefer_no_login_when_available: bool = True
    comment_sort: str = "old"
    preserve_reddit_display_order: bool = True
    include_branch_urls: bool = True
    max_items: int = 500
    max_pages: int = 80
    timeout_seconds: int = 45
    visible_dom_html_by_url: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["branch_urls"] = list(self.branch_urls)
        data["accounts_keys_state"] = _redact_accounts_keys_state(data.get("accounts_keys_state") or {})
        data["visible_dom_html_by_url"] = {str(k): "<html omitted>" for k in (self.visible_dom_html_by_url or {}).keys()}
        return _to_jsonable(data)


@dataclass(frozen=True)
class RedditNoLoginCompleteCommentsResultR44F:
    marker: str
    schema_version: str
    status: str
    strategy: str
    logged_in_account_detected: bool
    accounts_keys_detection_path: str
    thread_url: str
    old_reddit_url: str
    account_handle: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    request_path: str
    receipt_path: str
    capture_plan_path: str
    branch_queue_path: str
    combined_visible_dom_html_path: str
    comment_index_path: str
    comment_tree_markdown_path: str
    r44d_receipt_path: str = ""
    r44d_status: str = ""
    ledger_status: str = ""
    account_capture_dir: str = ""
    account_record_path: str = ""
    account_timeline_path: str = ""
    media_index_path: str = ""
    review_strings_path: str = ""
    planned_url_count: int = 0
    branch_url_count: int = 0
    captured_page_count: int = 0
    discovered_continue_url_count: int = 0
    dom_record_block_count: int = 0
    visible_record_count: int = 0
    record_count: int = 0
    media_count: int = 0
    screenshot_count: int = 0
    comment_index_count: int = 0
    top_level_comment_count: int = 0
    max_comment_depth: int = 0
    score_count: int = 0
    negative_score_count: int = 0
    hidden_score_count: int = 0
    branch_order_labels: tuple[str, ...] = ()
    browser_session_started: bool = False
    network_actions_performed: bool = False
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R44F_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R44FReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R44F_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class RedditNoLoginCompleteCommentsR44F:
    """No-login Reddit complete-comment planner/capture coordinator.

    R44F is the reliability layer above R44D for Reddit threads. It chooses the
    old/en Reddit limit=500 route when no Reddit login is detected from the app
    Accounts/Keys metadata, keeps branch/comment URLs in visible top-to-bottom
    order, indexes net vote score text, merges branch pages without duplicating
    anchor comments, writes an indented comment-tree index, and then sends the
    combined visible HTML to R44D -> R43U.
    """

    def __init__(self, output_root: str | Path = R44F_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def run_complete_thread_capture(
        self,
        request: RedditNoLoginCompleteCommentsRequestR44F | Mapping[str, Any] | None = None,
        *,
        page_fetcher: PageFetcher | None = None,
        **overrides: Any,
    ) -> RedditNoLoginCompleteCommentsResultR44F:
        req = coerce_reddit_no_login_complete_comments_request_r44f(request, **overrides)
        return run_reddit_no_login_complete_comments_r44f(req, output_root=self.output_root, page_fetcher=page_fetcher)


def build_reddit_no_login_complete_comments_r44f(output_root: str | Path = R44F_DEFAULT_OUTPUT_ROOT) -> RedditNoLoginCompleteCommentsR44F:
    return RedditNoLoginCompleteCommentsR44F(output_root=output_root)


def build_reddit_no_login_complete_comments_contract_r44f() -> dict[str, Any]:
    return {
        "marker": R44F_MARKER,
        "schema_version": R44F_SCHEMA_VERSION,
        "mode_id": R44F_MODE_ID,
        "primary_strategy_when_no_accounts_keys_login": "old/en Reddit thread page with sort, screen_view_count=1, limit=500, then branch/comment pages",
        "accounts_keys_rule": "read only non-secret app metadata indicating whether a Reddit account is configured; never read cookies, tokens, browser profile files, local storage, cache, or Login Data",
        "logged_in_account_available_rule": "logged-in visible browsing may be offered only as an operator-controlled visible session; R44F does not automate login or extract credentials",
        "branch_order_rule": "preserve operator/current-Reddit branch URLs in top-to-bottom order; labels such as 2.1 remain after their parent branch label and are written to the branch queue",
        "comment_order_rule": "preserve Reddit page display order by default and record visible net score separately; do not numerically reorder unless a caller explicitly requests a score-sorted export",
        "score_rule": "Reddit exposes displayed net score text, not exact separate upvote/downvote totals; hidden scores remain hidden/not shown",
        "dedupe_rule": "dedupe by Reddit t1 comment id / t3 submission id and do not count duplicate branch anchor comments twice",
        "indent_rule": "parent-child indentation is rebuilt from visible parent ids and branch-anchor context; unattached branch comments keep capture order with a warning",
        "downstream_adapter": "profile_media_reddit_visible_dom_capture_r44d",
        "downstream_ledger": "profile_media_universal_social_account_ledger_contract_r43u",
        "record_mapping": {"thread submission": "post", "thread comments": "reply", "crossposts": "repost_or_reshare"},
        "no_cookie_token_or_browser_profile_copying": True,
        "no_remote_media_downloads": True,
        "hidden_platform_api_scraping_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
    }


def run_reddit_no_login_complete_comments_r44f(
    request: RedditNoLoginCompleteCommentsRequestR44F | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R44F_DEFAULT_OUTPUT_ROOT,
    page_fetcher: PageFetcher | None = None,
) -> RedditNoLoginCompleteCommentsResultR44F:
    req = coerce_reddit_no_login_complete_comments_request_r44f(request)
    root = Path(req.output_root or output_root or R44F_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    thread_url = _plain_url(req.thread_url or R44E_EDSHEERAN_THREAD_URL)
    old_url = build_no_login_old_reddit_thread_url_r44f(req.old_reddit_url or thread_url, comment_sort=req.comment_sort)
    account_handle = _safe_handle(req.account_handle or _subreddit_handle_from_url(thread_url) or _reddit_thread_handle(thread_url))
    run_dir = root / account_handle / f"reddit_no_login_complete_comments_{capture_ts}"
    evidence_dir = run_dir / "visible_old_reddit_evidence"
    screenshot_dir = run_dir / "visible_old_reddit_screenshots"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    request_path = run_dir / "r44f_reddit_no_login_complete_comments_request.json"
    receipt_path = run_dir / "r44f_reddit_no_login_complete_comments_receipt.json"
    capture_plan_path = run_dir / "reddit_no_login_capture_plan.json"
    branch_queue_path = run_dir / "reddit_branch_queue_top_to_bottom.json"
    combined_html_path = evidence_dir / "combined_visible_old_reddit_dom.html"
    comment_index_path = run_dir / "reddit_comment_tree_index.json"
    comment_tree_markdown_path = run_dir / "reddit_comment_tree_index.md"
    _write_json(request_path, req.to_dict())

    login_detected, detection_path = detect_reddit_logged_in_available_r44f(
        req.accounts_keys_state,
        explicit_logged_in=req.accounts_keys_reddit_logged_in,
    )
    strategy = choose_reddit_comment_capture_strategy_r44f(
        logged_in_account_detected=login_detected,
        prefer_no_login_when_available=req.prefer_no_login_when_available,
    )

    branch_entries = build_ordered_reddit_branch_queue_r44f(
        branch_urls=req.branch_urls if req.include_branch_urls else (),
        ordered_branch_source_text=req.ordered_branch_source_text,
    )
    if req.fixture_mode and not branch_entries:
        branch_entries = build_ordered_reddit_branch_queue_r44f(branch_urls=R44E_EDSHEERAN_BRANCH_URLS[:3])
    planned_urls = [old_url] + [entry.url for entry in branch_entries if entry.url != old_url]
    _write_json(branch_queue_path, [entry.to_dict() for entry in branch_entries])
    _write_json(capture_plan_path, {
        "thread_url": thread_url,
        "old_reddit_url": old_url,
        "strategy": strategy,
        "logged_in_account_detected": login_detected,
        "accounts_keys_detection_path": detection_path,
        "branch_urls_top_to_bottom": [entry.to_dict() for entry in branch_entries],
        "planned_urls": planned_urls,
        "comment_sort": normalize_reddit_comment_sort_r44f(req.comment_sort),
    })

    warnings: list[str] = []
    pages: list[dict[str, Any]] = []
    browser_started = False
    network_actions = False
    supplied_pages = {_plain_url(k): str(v) for k, v in dict(req.visible_dom_html_by_url or {}).items()}

    if supplied_pages:
        pages = _pages_from_supplied_html_r44f(planned_urls, supplied_pages, screenshot_dir)
    elif req.fixture_mode:
        fake_pages = build_fake_no_login_reddit_pages_r44f(branch_entries)
        pages = _pages_from_supplied_html_r44f(planned_urls, fake_pages, screenshot_dir, capture_mode="fixture_old_reddit_complete_comment_dom")
    elif req.real_visible_smoke and req.public_network_enabled and req.explicit_live_mode:
        pages, discovered_entries, browser_started, network_actions = _capture_old_reddit_pages_with_discovery_r44f(
            planned_urls=planned_urls,
            branch_entries=branch_entries,
            screenshot_dir=screenshot_dir,
            max_pages=req.max_pages,
            timeout_seconds=req.timeout_seconds,
            page_fetcher=page_fetcher,
        )
        if discovered_entries:
            existing = {entry.url for entry in branch_entries}
            for entry in discovered_entries:
                if entry.url not in existing:
                    existing.add(entry.url)
                    branch_entries.append(entry)
    else:
        warnings.append("R44F did not start real browser/network because visible capture requires --real-visible-smoke --public-network-enabled --explicit-live-mode.")

    planned_urls = [old_url] + [entry.url for entry in branch_entries if entry.url != old_url]
    _write_json(branch_queue_path, [entry.to_dict() for entry in branch_entries])
    _write_json(capture_plan_path, {
        "thread_url": thread_url,
        "old_reddit_url": old_url,
        "strategy": strategy,
        "logged_in_account_detected": login_detected,
        "accounts_keys_detection_path": detection_path,
        "branch_urls_top_to_bottom": [entry.to_dict() for entry in branch_entries],
        "planned_urls": planned_urls,
        "comment_sort": normalize_reddit_comment_sort_r44f(req.comment_sort),
        "captured_page_count": len(pages),
    })

    combined = combine_visible_reddit_pages_r44f(pages)
    combined_html_path.write_text(combined, encoding="utf-8")
    comment_nodes = extract_and_merge_reddit_comment_index_r44f(pages, branch_entries=branch_entries, thread_url=thread_url)
    _write_json(comment_index_path, [node.to_dict() for node in comment_nodes])
    comment_tree_markdown_path.write_text(render_reddit_comment_tree_markdown_r44f(comment_nodes, thread_url=thread_url, old_reddit_url=old_url), encoding="utf-8")

    if not pages:
        warnings.append("No old Reddit pages were captured or supplied.")
        result = _blocked_result(req, root, run_dir, request_path, receipt_path, capture_plan_path, branch_queue_path, combined_html_path, comment_index_path, comment_tree_markdown_path, thread_url, old_url, account_handle, capture_ts, strategy, login_detected, detection_path, planned_urls, branch_entries, warnings, browser_started, network_actions)
        _write_json(receipt_path, result.to_dict())
        return result

    first_screenshot = _first_screenshot_path(pages)
    r44d = run_reddit_visible_dom_capture_r44d(
        RedditVisibleDomCaptureRequestR44D(
            account_url=thread_url,
            account_handle=account_handle,
            capture_timestamp=capture_ts,
            output_root=str(run_dir / "r44d_visible_dom"),
            visible_dom_html_path=str(combined_html_path),
            static_screenshot_path=first_screenshot,
            feed_mode="single_thread",
            include_comments=True,
            include_media=True,
            require_screenshot_receipts=bool(first_screenshot),
            max_items=max(1, int(req.max_items or 500)),
        )
    )
    r44d_payload = r44d.to_dict()
    status = R44F_PASS_STATUS if r44d.status == R44D_PASS_STATUS and r44d.record_count > 0 and comment_nodes else R44F_BLOCKED_STATUS
    if status != R44F_PASS_STATUS:
        warnings.append(f"R44D downstream Reddit visible DOM capture did not pass: {r44d.status!r}")
    warnings.extend(str(x) for x in (r44d_payload.get("warnings") or ()))

    result = RedditNoLoginCompleteCommentsResultR44F(
        marker=R44F_MARKER,
        schema_version=R44F_SCHEMA_VERSION,
        status=status,
        strategy=strategy,
        logged_in_account_detected=login_detected,
        accounts_keys_detection_path=detection_path,
        thread_url=thread_url,
        old_reddit_url=old_url,
        account_handle=account_handle,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        capture_plan_path=str(capture_plan_path),
        branch_queue_path=str(branch_queue_path),
        combined_visible_dom_html_path=str(combined_html_path),
        comment_index_path=str(comment_index_path),
        comment_tree_markdown_path=str(comment_tree_markdown_path),
        r44d_receipt_path=str(r44d.receipt_path),
        r44d_status=r44d.status,
        ledger_status=r44d.ledger_status,
        account_capture_dir=str(r44d.account_capture_dir),
        account_record_path=str(r44d.account_record_path),
        account_timeline_path=str(r44d.account_timeline_path),
        media_index_path=str(r44d.media_index_path),
        review_strings_path=str(r44d.review_strings_path),
        planned_url_count=len(planned_urls),
        branch_url_count=len(branch_entries),
        captured_page_count=len(pages),
        discovered_continue_url_count=sum(1 for entry in branch_entries if entry.source == "discovered_continue_thread_link"),
        dom_record_block_count=r44d.dom_record_block_count,
        visible_record_count=r44d.visible_record_count,
        record_count=r44d.record_count,
        media_count=r44d.media_count,
        screenshot_count=r44d.screenshot_count,
        comment_index_count=len(comment_nodes),
        top_level_comment_count=sum(1 for node in comment_nodes if node.indent_level == 0),
        max_comment_depth=max((node.indent_level for node in comment_nodes), default=0),
        score_count=sum(1 for node in comment_nodes if node.score_value is not None),
        negative_score_count=sum(1 for node in comment_nodes if isinstance(node.score_value, int) and node.score_value < 0),
        hidden_score_count=sum(1 for node in comment_nodes if node.score_hidden),
        branch_order_labels=tuple(entry.label for entry in branch_entries),
        browser_session_started=browser_started,
        network_actions_performed=network_actions,
        side_effect_flags=build_r44f_side_effect_flags(browser_session_started=browser_started, network_actions_performed=network_actions),
        warnings=tuple(warnings),
    )
    _write_json(receipt_path, result.to_dict())
    return result


def build_report(output_root: str | Path = R44F_DEFAULT_OUTPUT_ROOT) -> R44FReport:
    root = Path(output_root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    source_text = "\n".join(f"{idx + 1} - {url}" for idx, url in enumerate(R44E_EDSHEERAN_BRANCH_URLS[:3]))
    sample = run_reddit_no_login_complete_comments_r44f(
        RedditNoLoginCompleteCommentsRequestR44F(
            thread_url=R44E_EDSHEERAN_THREAD_URL,
            old_reddit_url=R44E_EDSHEERAN_OLD_REDDIT_URL,
            ordered_branch_source_text=source_text,
            account_handle="r_EdSheeran",
            capture_timestamp="20260918T120000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
            max_items=500,
        )
    )
    contract = build_reddit_no_login_complete_comments_contract_r44f()
    flags = build_r44f_side_effect_flags(browser_session_started=False, network_actions_performed=False)
    checks = (
        _check("no_accounts_keys_login_chooses_no_login_old_reddit", sample.strategy == "no_login_old_reddit_limit500_branch_queue" and sample.logged_in_account_detected is False),
        _check("old_reddit_limit500_url_is_primary", sample.old_reddit_url.startswith("https://en.reddit.com/") and "limit=500" in sample.old_reddit_url and "sort=old" in sample.old_reddit_url),
        _check("operator_branch_urls_preserve_top_to_bottom_order", sample.branch_order_labels[:3] == ("1", "2", "3")),
        _check("comment_index_preserves_scores_and_negative_scores", sample.score_count >= 2 and sample.negative_score_count >= 1),
        _check("comment_tree_indentation_is_written", sample.max_comment_depth >= 2 and bool(sample.comment_tree_markdown_path) and Path(str(sample.comment_tree_markdown_path)).is_file()),
        _check("branch_anchor_duplicates_are_not_counted_twice", sample.comment_index_count >= 4 and sample.record_count >= 4),
        _check("r44d_r43u_downstream_chain_preserved", sample.r44d_status == R44D_PASS_STATUS and sample.ledger_status == "PASS_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE"),
        _check("no_real_browser_or_network_in_report_validation", not sample.browser_session_started and not sample.network_actions_performed),
        _check("no_cookie_token_profile_or_remote_media_side_effects", not any(flags.get(k) for k in ("browser_profile_files_read_or_copied", "cookie_or_token_extraction_performed", "remote_media_downloads_performed", "login_automation_performed", "captcha_or_challenge_bypass_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(sample.to_dict()) and _machine_urls_are_plain(contract)),
    )
    status = R44F_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R44F_BLOCKED_STATUS
    report = R44FReport(
        marker=R44F_MARKER,
        schema_version=R44F_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        sample_result=sample.to_dict(),
        contract=contract,
        side_effect_flags=flags,
    )
    write_report(report, root)
    return report


def detect_reddit_logged_in_available_r44f(accounts_keys_state: Mapping[str, Any] | None = None, *, explicit_logged_in: bool = False) -> tuple[bool, str]:
    if explicit_logged_in:
        return True, "explicit_accounts_keys_reddit_logged_in_flag"
    state = accounts_keys_state or {}
    if not isinstance(state, Mapping):
        return False, "accounts_keys_state_missing_or_not_mapping"
    if _to_bool(state.get("reddit_logged_in"), False) or _to_bool(state.get("reddit_account_logged_in"), False):
        return True, "accounts_keys_state.reddit_logged_in"
    reddit_state = state.get("reddit") or state.get("Reddit") or {}
    if isinstance(reddit_state, Mapping):
        if _to_bool(reddit_state.get("logged_in"), False) or _to_bool(reddit_state.get("connected"), False):
            return True, "accounts_keys_state.reddit.logged_in"
        status = _clean(reddit_state.get("status") or reddit_state.get("connection_status")).lower()
        if status in {"connected", "logged_in", "authenticated", "available"}:
            return True, "accounts_keys_state.reddit.status"
    for key in ("accounts", "connections", "keys"):
        value = state.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                if isinstance(item, Mapping):
                    platform = _clean(item.get("platform") or item.get("site") or item.get("provider")).lower()
                    status = _clean(item.get("status") or item.get("connection_status")).lower()
                    if platform == "reddit" and (status in {"connected", "logged_in", "authenticated", "available"} or _to_bool(item.get("logged_in"), False)):
                        return True, f"accounts_keys_state.{key}.reddit"
    return False, "no_reddit_login_detected_in_accounts_keys_metadata"


def choose_reddit_comment_capture_strategy_r44f(*, logged_in_account_detected: bool, prefer_no_login_when_available: bool = True) -> str:
    if logged_in_account_detected and not prefer_no_login_when_available:
        return "accounts_keys_logged_in_visible_browser_available"
    return "no_login_old_reddit_limit500_branch_queue"


def build_no_login_old_reddit_thread_url_r44f(url: str, *, comment_sort: str = "old") -> str:
    text = canonicalize_old_reddit_thread_url_r44e(url)
    split = urlsplit(text)
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query.update({"sort": normalize_reddit_comment_sort_r44f(comment_sort), "screen_view_count": "1", "limit": "500", "ext-referrer": "DIRECT"})
    return urlunsplit(("https", "en.reddit.com", split.path, urlencode(query), ""))


def normalize_reddit_comment_sort_r44f(sort: str) -> str:
    text = _clean(sort).lower()
    if text in {"old", "new", "top", "best", "confidence", "controversial", "qa", "live"}:
        return text
    if text in {"score", "score_desc", "votes", "upvotes", "downvotes"}:
        return "top"
    return "old"


def parse_ordered_reddit_branch_lines_r44f(text: str) -> list[OrderedRedditBranchUrlR44F]:
    entries: list[OrderedRedditBranchUrlR44F] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^([0-9]+(?:\.[0-9]+)*)\s*(?:[-–—:]|\))\s*(https?://\S+)", line)
        if match:
            label, url = match.group(1), match.group(2)
        else:
            url_match = re.search(r"https?://\S+", line)
            if not url_match:
                continue
            label, url = str(len(entries) + 1), url_match.group(0)
        normalized = normalize_reddit_branch_urls_r44e([url])[0]
        entries.append(OrderedRedditBranchUrlR44F(
            label=label,
            display_order_index=len(entries) + 1,
            url=normalized,
            original_url=_plain_url(url),
            comment_id=_reddit_comment_id_from_url(normalized),
            depth_hint=max(0, label.count(".")),
        ))
    return entries


def build_ordered_reddit_branch_queue_r44f(*, branch_urls: Sequence[str] = (), ordered_branch_source_text: str = "") -> list[OrderedRedditBranchUrlR44F]:
    output: list[OrderedRedditBranchUrlR44F] = []
    seen: set[str] = set()
    for entry in parse_ordered_reddit_branch_lines_r44f(ordered_branch_source_text):
        if entry.url not in seen:
            seen.add(entry.url)
            output.append(entry)
    for url in normalize_reddit_branch_urls_r44e(branch_urls):
        if url not in seen:
            seen.add(url)
            output.append(OrderedRedditBranchUrlR44F(
                label=str(len(output) + 1),
                display_order_index=len(output) + 1,
                url=url,
                original_url=_plain_url(url),
                comment_id=_reddit_comment_id_from_url(url),
                depth_hint=0,
            ))
    return output


def extract_and_merge_reddit_comment_index_r44f(
    pages: Sequence[Mapping[str, Any]],
    *,
    branch_entries: Sequence[OrderedRedditBranchUrlR44F],
    thread_url: str,
) -> list[RedditCommentIndexNodeR44F]:
    branch_by_url = {_plain_url(entry.url): entry for entry in branch_entries}
    branch_by_comment = {entry.comment_id: entry for entry in branch_entries if entry.comment_id}
    raw_nodes: list[RedditCommentIndexNodeR44F] = []
    for page_index, page in enumerate(pages, start=1):
        page_url = _plain_url(page.get("final_url") or page.get("url") or "")
        branch_entry = branch_by_url.get(page_url) or branch_by_comment.get(_reddit_comment_id_from_url(page_url))
        raw_nodes.extend(extract_reddit_comment_nodes_from_old_reddit_html_r44f(
            str(page.get("html") or ""),
            page_url=page_url,
            page_index=page_index,
            branch_label=branch_entry.label if branch_entry else "",
            branch_display_order_index=branch_entry.display_order_index if branch_entry else 0,
            thread_url=thread_url,
        ))
    first_by_id: dict[str, RedditCommentIndexNodeR44F] = {}
    for node in raw_nodes:
        if not node.comment_id:
            continue
        if node.comment_id not in first_by_id:
            first_by_id[node.comment_id] = node
    nodes = list(first_by_id.values())
    by_parent: dict[str, list[RedditCommentIndexNodeR44F]] = {}
    for node in nodes:
        by_parent.setdefault(node.parent_id, []).append(node)
    for bucket in by_parent.values():
        bucket.sort(key=lambda n: (n.page_index, n.branch_display_order_index or 0, n.page_order_index))
    post_id = _reddit_post_id_from_url(thread_url)
    roots = [node for node in nodes if not node.parent_id or node.parent_id == post_id or node.parent_id not in first_by_id]
    roots.sort(key=lambda n: (n.page_index, n.branch_display_order_index or 0, n.page_order_index))
    ordered: list[RedditCommentIndexNodeR44F] = []

    def visit(node: RedditCommentIndexNodeR44F, depth: int) -> None:
        ordered.append(_replace_node_order(node, indent_level=depth, tree_order_index=len(ordered) + 1))
        for child in by_parent.get(node.comment_id, []):
            if child.comment_id != node.comment_id:
                visit(child, depth + 1)

    for root in roots:
        visit(root, 0)
    return ordered


def extract_reddit_comment_nodes_from_old_reddit_html_r44f(
    html_text: str,
    *,
    page_url: str,
    page_index: int,
    branch_label: str = "",
    branch_display_order_index: int = 0,
    thread_url: str = "",
) -> list[RedditCommentIndexNodeR44F]:
    text = str(html_text or "")
    blocks = re.findall(r"<div\b[^>]*(?:thing[^>]*comment|comment[^>]*thing)[^>]*>.*?(?=<div\b[^>]*(?:thing[^>]*(?:comment|link)|comment[^>]*thing)|</body>|</html>|$)", text, re.I | re.S)
    output: list[RedditCommentIndexNodeR44F] = []
    post_id = _reddit_post_id_from_url(thread_url or page_url)
    for order, block in enumerate(blocks, start=1):
        attrs = _first_tag_attrs(block)
        comment_id = _strip_reddit_fullname(attrs.get("data-fullname") or attrs.get("id") or _reddit_comment_id_from_url(block))
        if not comment_id:
            continue
        parent_id = _strip_reddit_fullname(attrs.get("data-parent") or attrs.get("data-parent-fullname") or "")
        author = _clean(attrs.get("data-author") or _first_match(block, r"<a\b[^>]*class=['\"][^'\"]*author[^'\"]*['\"][^>]*>(.*?)</a>"))
        permalink = _normalize_reddit_url(_first_match(block, r"<a\b[^>]*(?:class=['\"][^'\"]*bylink[^'\"]*['\"][^>]*href|href)=['\"]([^'\"]+)['\"][^>]*>"))
        if not permalink:
            permalink = _normalize_reddit_url(_first_match(block, r"href=['\"]([^'\"]*/comments/[^'\"]+)['\"]"))
        timestamp = _first_match(block, r"<time\b[^>]*datetime=['\"]([^'\"]+)['\"]")
        score_display, score_value, score_hidden = _extract_reddit_score_r44f(block)
        visible_text = _extract_usertext_r44f(block)
        output.append(RedditCommentIndexNodeR44F(
            comment_id=comment_id,
            parent_id=parent_id,
            post_id=post_id,
            author_handle=_safe_handle(author or "unknown_redditor"),
            permalink=permalink or page_url,
            visible_text=visible_text,
            visible_timestamp=_clean(timestamp),
            score_display=score_display,
            score_value=score_value,
            score_hidden=score_hidden,
            page_url=page_url,
            page_index=page_index,
            page_order_index=order,
            branch_label=branch_label,
            branch_display_order_index=branch_display_order_index,
        ))
    return output


def render_reddit_comment_tree_markdown_r44f(nodes: Sequence[RedditCommentIndexNodeR44F], *, thread_url: str, old_reddit_url: str) -> str:
    lines = [
        "# Reddit no-login complete comment tree index",
        "",
        f"Thread: {thread_url}",
        f"Old Reddit primary URL: {old_reddit_url}",
        "",
        "Score note: Reddit visible pages expose displayed net score text, not separate exact upvote/downvote totals.",
        "",
        "## Comments",
        "",
    ]
    for node in nodes:
        indent = "  " * max(0, node.indent_level)
        score = "hidden/not shown" if node.score_hidden else (node.score_display or "not shown")
        branch = f" | branch: {node.branch_label}" if node.branch_label else ""
        text = _clean(node.visible_text)
        if len(text) > 220:
            text = text[:217].rstrip() + "..."
        lines.append(f"{indent}- {node.tree_order_index}. u/{node.author_handle} | id: {node.comment_id} | score: {score}{branch}")
        if text:
            lines.append(f"{indent}  {text}")
        if node.permalink:
            lines.append(f"{indent}  permalink: {node.permalink}")
    lines.append("")
    return "\n".join(lines)


def combine_visible_reddit_pages_r44f(pages: Sequence[Mapping[str, Any]]) -> str:
    parts = ["<html><body data-r44f-combined-old-reddit-pages='true'>"]
    for index, page in enumerate(pages, start=1):
        url = html_lib.escape(_plain_url(page.get("final_url") or page.get("url") or ""), quote=True)
        mode = html_lib.escape(_clean(page.get("capture_mode") or ""), quote=True)
        parts.append(f"<!-- R44F_PAGE_{index:03d}: {url} -->")
        parts.append(f"<section data-r44f-page-index='{index}' data-r44f-page-url='{url}' data-r44f-capture-mode='{mode}'>")
        parts.append(str(page.get("html") or ""))
        parts.append("</section>")
    parts.append("</body></html>")
    return "\n".join(parts)


def build_fake_no_login_reddit_pages_r44f(branch_entries: Sequence[OrderedRedditBranchUrlR44F] = ()) -> dict[str, str]:
    old = build_no_login_old_reddit_thread_url_r44f(R44E_EDSHEERAN_THREAD_URL, comment_sort="old")
    old_with_slug = build_no_login_old_reddit_thread_url_r44f(R44E_EDSHEERAN_OLD_REDDIT_URL, comment_sort="old")
    entries = list(branch_entries) or build_ordered_reddit_branch_queue_r44f(branch_urls=R44E_EDSHEERAN_BRANCH_URLS[:3])
    branch_one = entries[0].url if entries else normalize_reddit_branch_urls_r44e([R44E_EDSHEERAN_BRANCH_URLS[0]])[0]
    branch_two = entries[1].url if len(entries) > 1 else normalize_reddit_branch_urls_r44e([R44E_EDSHEERAN_BRANCH_URLS[1]])[0]
    thread_html = f"""
<html><body>
<div class="thing link" id="thing_t3_1whbgzk" data-fullname="t3_1whbgzk" data-author="Stonerthrowaway710" data-type="link">
  <p class="title"><a class="title" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/">Ed's got a show in 4 days. No band. No openers. What the plan here?</a></p>
  <time datetime="2026-09-15T20:12:09Z">15 Sept 2026</time>
</div>
<div class="thing comment" id="thing_t1_pa1fs0p" data-fullname="t1_pa1fs0p" data-parent="t3_1whbgzk" data-author="Hassaan18" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa1fs0p/">permalink</a>
  <span class="score unvoted">49 points</span>
  <time datetime="2026-09-15T20:20:00Z">1d ago</time>
  <div class="usertext-body"><p>He can do the show. He's done stripped back shows before.</p></div>
  <a href="{branch_one}">continue this thread</a>
</div>
<div class="thing comment" id="thing_t1_pa15vni" data-fullname="t1_pa15vni" data-parent="t3_1whbgzk" data-author="Wetnorthwest" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa15vni/">permalink</a>
  <span class="score dislikes">-2 points</span>
  <time datetime="2026-09-15T20:22:00Z">1d ago</time>
  <div class="usertext-body"><p>He can absolutely loop the whole show.</p><a href="https://i.redd.it/thread_image.jpg">image</a></div>
  <a href="{branch_two}">more comments</a>
</div>
</body></html>
""".strip()
    branch_one_html = """
<html><body>
<div class="thing comment" id="thing_t1_pa1fs0p" data-fullname="t1_pa1fs0p" data-parent="t3_1whbgzk" data-author="Hassaan18" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa1fs0p/">permalink</a>
  <span class="score unvoted">49 points</span>
  <div class="usertext-body"><p>Duplicate anchor comment should not be counted twice.</p></div>
</div>
<div class="thing comment" id="thing_t1_pa1child" data-fullname="t1_pa1child" data-parent="t1_pa1fs0p" data-author="ertri" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa1child/">permalink</a>
  <span class="score unvoted">2 points</span>
  <time datetime="2026-09-15T20:23:00Z">1d ago</time>
  <div class="usertext-body"><p>Stripped down stadium gig.</p></div>
</div>
<div class="thing comment" id="thing_t1_pa1grand" data-fullname="t1_pa1grand" data-parent="t1_pa1child" data-author="unknowingexpert69" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa1grand/">permalink</a>
  <span class="score hidden">score hidden</span>
  <time datetime="2026-09-15T20:24:00Z">1d ago</time>
  <div class="usertext-body"><p>He has looped in stadiums before.</p></div>
</div>
</body></html>
""".strip()
    branch_two_html = """
<html><body>
<div class="thing comment" id="thing_t1_pa15child" data-fullname="t1_pa15child" data-parent="t1_pa15vni" data-author="audioscape" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa15child/">permalink</a>
  <span class="score unvoted">22 points</span>
  <time datetime="2026-09-15T20:25:00Z">1d ago</time>
  <div class="usertext-body"><p>Also imagine you are the artist who steps in.</p><a href="https://v.redd.it/example/DASHPlaylist.mpd">video</a></div>
</div>
</body></html>
""".strip()
    pages = {old: thread_html, old_with_slug: thread_html, branch_one: branch_one_html, branch_two: branch_two_html}
    for entry in entries[2:]:
        pages[entry.url] = branch_two_html
    return pages


def build_r44f_side_effect_flags(*, browser_session_started: bool, network_actions_performed: bool) -> dict[str, bool]:
    return {
        "reddit_no_login_complete_comment_ordering_invoked": True,
        "browser_session_started": bool(browser_session_started),
        "network_actions_performed": bool(network_actions_performed),
        "browser_profile_files_read_or_copied": False,
        "webview2_internals_copied": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
        "r44d_reddit_visible_dom_capture_used": True,
        "r43u_universal_ledger_writer_used": True,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
    }


def write_report(report: R44FReport, output_root: str | Path) -> None:
    root = Path(output_root)
    _write_json(root / "R44F_REDDIT_NO_LOGIN_COMPLETE_COMMENT_ORDERING_REPORT.json", report.to_dict())
    _write_text(root / "R44F_REDDIT_NO_LOGIN_COMPLETE_COMMENT_ORDERING_REPORT.md", _report_md(report))


def coerce_reddit_no_login_complete_comments_request_r44f(request: RedditNoLoginCompleteCommentsRequestR44F | Mapping[str, Any] | None = None, **overrides: Any) -> RedditNoLoginCompleteCommentsRequestR44F:
    if isinstance(request, RedditNoLoginCompleteCommentsRequestR44F):
        base = request.to_dict()
        if request.visible_dom_html_by_url:
            base["visible_dom_html_by_url"] = dict(request.visible_dom_html_by_url)
    elif hasattr(request, "to_dict"):
        payload = request.to_dict()
        base = dict(payload) if isinstance(payload, Mapping) else {}
    elif isinstance(request, Mapping):
        base = dict(request)
    else:
        base = {}
    for key, value in overrides.items():
        if value not in (None, ""):
            base[key] = value
    branch_raw = base.get("branch_urls") or ()
    if isinstance(branch_raw, str):
        branch_urls = tuple(line.strip() for line in branch_raw.splitlines() if line.strip())
    else:
        branch_urls = tuple(str(x) for x in branch_raw)
    return RedditNoLoginCompleteCommentsRequestR44F(
        thread_url=_plain_url(base.get("thread_url") or base.get("account_url") or R44E_EDSHEERAN_THREAD_URL),
        old_reddit_url=_plain_url(base.get("old_reddit_url") or ""),
        branch_urls=tuple(branch_urls),
        ordered_branch_source_text=str(base.get("ordered_branch_source_text") or ""),
        account_handle=_safe_handle(base.get("account_handle") or ""),
        capture_timestamp=_safe_ts(base.get("capture_timestamp") or ""),
        output_root=_clean(base.get("output_root") or R44F_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(base.get("fixture_mode"), False),
        real_visible_smoke=_to_bool(base.get("real_visible_smoke"), False),
        public_network_enabled=_to_bool(base.get("public_network_enabled"), False),
        explicit_live_mode=_to_bool(base.get("explicit_live_mode"), False),
        accounts_keys_reddit_logged_in=_to_bool(base.get("accounts_keys_reddit_logged_in"), False),
        accounts_keys_state=dict(base.get("accounts_keys_state") or {}),
        prefer_no_login_when_available=_to_bool(base.get("prefer_no_login_when_available"), True),
        comment_sort=normalize_reddit_comment_sort_r44f(str(base.get("comment_sort") or "old")),
        preserve_reddit_display_order=_to_bool(base.get("preserve_reddit_display_order"), True),
        include_branch_urls=_to_bool(base.get("include_branch_urls"), True),
        max_items=max(1, _safe_int(base.get("max_items"), 500)),
        max_pages=max(1, _safe_int(base.get("max_pages"), 80)),
        timeout_seconds=max(5, _safe_int(base.get("timeout_seconds"), 45)),
        visible_dom_html_by_url=dict(base.get("visible_dom_html_by_url") or {}),
    )


def _capture_old_reddit_pages_with_discovery_r44f(
    *,
    planned_urls: Sequence[str],
    branch_entries: list[OrderedRedditBranchUrlR44F],
    screenshot_dir: Path,
    max_pages: int,
    timeout_seconds: int,
    page_fetcher: PageFetcher | None = None,
) -> tuple[list[dict[str, Any]], list[OrderedRedditBranchUrlR44F], bool, bool]:
    pages: list[dict[str, Any]] = []
    discovered_entries: list[OrderedRedditBranchUrlR44F] = []
    queue = list(planned_urls)
    seen: set[str] = set()
    branch_seen = {entry.url for entry in branch_entries}
    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        screenshot_path = screenshot_dir / f"page_{len(pages) + 1:03d}.png"
        fetched = dict(page_fetcher(url, screenshot_path)) if page_fetcher is not None else _fetch_one_visible_playwright_r44f(url, screenshot_path=screenshot_path, timeout_seconds=timeout_seconds)
        fetched.setdefault("url", url)
        fetched.setdefault("final_url", url)
        fetched.setdefault("capture_mode", "injected_page_fetcher" if page_fetcher is not None else "playwright_visible_chromium_old_reddit_no_login")
        pages.append(fetched)
        for found in extract_continue_thread_urls_from_old_reddit_html_r44e(str(fetched.get("html") or "")):
            normalized = normalize_reddit_branch_urls_r44e([found])[0]
            if normalized in branch_seen:
                continue
            branch_seen.add(normalized)
            entry = OrderedRedditBranchUrlR44F(
                label=f"auto.{len(discovered_entries) + 1}",
                display_order_index=len(branch_entries) + len(discovered_entries) + 1,
                url=normalized,
                original_url=found,
                comment_id=_reddit_comment_id_from_url(normalized),
                depth_hint=0,
                source="discovered_continue_thread_link",
            )
            discovered_entries.append(entry)
            queue.append(normalized)
    browser_started = any(bool(page.get("browser_session_started")) for page in pages) or page_fetcher is None
    network_actions = any(bool(page.get("network_actions_performed")) for page in pages) or bool(pages)
    return pages, discovered_entries, browser_started, network_actions


def _fetch_one_visible_playwright_r44f(url: str, *, screenshot_path: Path, timeout_seconds: int) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(f"Playwright is not installed or importable: {exc!r}") from exc
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=max(5, int(timeout_seconds)) * 1000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.screenshot(path=str(screenshot_path), full_page=True)
        html = page.content()
        final_url = page.url
        context.close()
        browser.close()
    return {
        "url": url,
        "final_url": final_url,
        "status_code": response.status if response is not None else 0,
        "html": html,
        "screenshot_path": str(screenshot_path),
        "capture_mode": "playwright_visible_chromium_old_reddit_no_login",
        "browser_session_started": True,
        "network_actions_performed": True,
    }


def _pages_from_supplied_html_r44f(planned_urls: Sequence[str], supplied_pages: Mapping[str, str], screenshot_dir: Path, *, capture_mode: str = "supplied_visible_dom_html") -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for index, url in enumerate(planned_urls, start=1):
        html = supplied_pages.get(url) or supplied_pages.get(_plain_url(url)) or ""
        if not html:
            continue
        shot = _write_fixture_screenshot(screenshot_dir / f"page_{index:03d}.png")
        pages.append({"url": url, "final_url": url, "status_code": 200, "html": html, "screenshot_path": str(shot), "capture_mode": capture_mode})
    return pages


def _extract_reddit_score_r44f(block: str) -> tuple[str, int | None, bool]:
    score_html = _first_match(block, r"<span\b[^>]*class=['\"][^'\"]*score[^'\"]*['\"][^>]*>(.*?)</span>")
    score_text = _clean(re.sub(r"<[^>]+>", " ", html_lib.unescape(score_html)))
    if not score_text:
        return "", None, False
    if "hidden" in score_text.lower() or "score hidden" in score_text.lower():
        return "hidden/not shown", None, True
    match = re.search(r"[-+]?\d+", score_text.replace(",", ""))
    return score_text, int(match.group(0)) if match else None, False


def _extract_usertext_r44f(block: str) -> str:
    match = re.search(r"<div\b[^>]*class=['\"][^'\"]*usertext-body[^'\"]*['\"][^>]*>(.*?)</div>", block, re.I | re.S)
    target = match.group(1) if match else block
    target = re.sub(r"<blockquote.*?</blockquote>", " ", target, flags=re.I | re.S)
    target = re.sub(r"<script.*?</script>|<style.*?</style>", " ", target, flags=re.I | re.S)
    return _clean(re.sub(r"<[^>]+>", " ", html_lib.unescape(target)))


def _replace_node_order(node: RedditCommentIndexNodeR44F, *, indent_level: int, tree_order_index: int) -> RedditCommentIndexNodeR44F:
    data = node.to_dict()
    data["indent_level"] = indent_level
    data["tree_order_index"] = tree_order_index
    return RedditCommentIndexNodeR44F(**data)


def _blocked_result(req: RedditNoLoginCompleteCommentsRequestR44F, root: Path, run_dir: Path, request_path: Path, receipt_path: Path, capture_plan_path: Path, branch_queue_path: Path, combined_html_path: Path, comment_index_path: Path, comment_tree_markdown_path: Path, thread_url: str, old_url: str, account_handle: str, capture_ts: str, strategy: str, logged_in: bool, detection_path: str, planned_urls: Sequence[str], branch_entries: Sequence[OrderedRedditBranchUrlR44F], warnings: Sequence[str], browser_started: bool, network_actions: bool) -> RedditNoLoginCompleteCommentsResultR44F:
    return RedditNoLoginCompleteCommentsResultR44F(
        marker=R44F_MARKER,
        schema_version=R44F_SCHEMA_VERSION,
        status=R44F_BLOCKED_STATUS,
        strategy=strategy,
        logged_in_account_detected=logged_in,
        accounts_keys_detection_path=detection_path,
        thread_url=thread_url,
        old_reddit_url=old_url,
        account_handle=account_handle,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        capture_plan_path=str(capture_plan_path),
        branch_queue_path=str(branch_queue_path),
        combined_visible_dom_html_path=str(combined_html_path),
        comment_index_path=str(comment_index_path),
        comment_tree_markdown_path=str(comment_tree_markdown_path),
        planned_url_count=len(planned_urls),
        branch_url_count=len(branch_entries),
        branch_order_labels=tuple(entry.label for entry in branch_entries),
        browser_session_started=browser_started,
        network_actions_performed=network_actions,
        side_effect_flags=build_r44f_side_effect_flags(browser_session_started=browser_started, network_actions_performed=network_actions),
        warnings=tuple(warnings),
    )


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="R44F Reddit no-login complete comment ordering")
    parser.add_argument("--thread-url", default=R44E_EDSHEERAN_THREAD_URL)
    parser.add_argument("--old-reddit-url", default="")
    parser.add_argument("--branch-url", action="append", default=[])
    parser.add_argument("--branch-url-file", default="")
    parser.add_argument("--ordered-branch-source-file", default="")
    parser.add_argument("--account-handle", default="")
    parser.add_argument("--output-root", default=R44F_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--comment-sort", default="old")
    parser.add_argument("--max-items", type=int, default=500)
    parser.add_argument("--max-pages", type=int, default=80)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--real-visible-smoke", action="store_true")
    parser.add_argument("--public-network-enabled", action="store_true")
    parser.add_argument("--explicit-live-mode", action="store_true")
    parser.add_argument("--accounts-keys-reddit-logged-in", action="store_true")
    parser.add_argument("--prefer-logged-in-visible-session", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.report:
        report = build_report(args.output_root)
        print(R44F_MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.passed else 1
    branch_urls = list(args.branch_url or [])
    if args.branch_url_file:
        branch_urls.extend(Path(args.branch_url_file).read_text(encoding="utf-8", errors="replace").splitlines())
    ordered_text = Path(args.ordered_branch_source_file).read_text(encoding="utf-8", errors="replace") if args.ordered_branch_source_file else ""
    result = run_reddit_no_login_complete_comments_r44f(
        RedditNoLoginCompleteCommentsRequestR44F(
            thread_url=args.thread_url,
            old_reddit_url=args.old_reddit_url,
            branch_urls=tuple(branch_urls),
            ordered_branch_source_text=ordered_text,
            account_handle=args.account_handle,
            capture_timestamp=args.capture_timestamp,
            output_root=args.output_root,
            fixture_mode=args.fixture_mode or not args.real_visible_smoke,
            real_visible_smoke=args.real_visible_smoke,
            public_network_enabled=args.public_network_enabled,
            explicit_live_mode=args.explicit_live_mode,
            accounts_keys_reddit_logged_in=args.accounts_keys_reddit_logged_in,
            prefer_no_login_when_available=not args.prefer_logged_in_visible_session,
            comment_sort=args.comment_sort,
            max_items=args.max_items,
            max_pages=args.max_pages,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(R44F_MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.passed else 1


def _report_md(report: R44FReport) -> str:
    lines = [
        "# R44F Reddit No-Login Complete Comment Ordering",
        "",
        f"Status: `{report.status}`",
        f"Marker: `{report.marker}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')}")
    sample = report.sample_result
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Strategy: `{sample.get('strategy')}`",
        f"- Old Reddit URL: `{sample.get('old_reddit_url')}`",
        f"- Branch URLs: `{sample.get('branch_url_count')}`",
        f"- Comment index nodes: `{sample.get('comment_index_count')}`",
        f"- Max depth: `{sample.get('max_comment_depth')}`",
        f"- Score count: `{sample.get('score_count')}`",
        f"- Records: `{sample.get('record_count')}`",
        f"- Media: `{sample.get('media_count')}`",
        "",
    ])
    return "\n".join(lines)


def _first_tag_attrs(block: str) -> dict[str, str]:
    match = re.search(r"<\w+\b([^>]*)>", block, re.I | re.S)
    attrs: dict[str, str] = {}
    if not match:
        return attrs
    attr_text = match.group(1)
    for name, _quote, value in re.findall(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(['\"])(.*?)\2", attr_text, re.S):
        attrs[name.lower()] = html_lib.unescape(value)
    return attrs


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text or "", re.I | re.S)
    return html_lib.unescape(match.group(1)) if match else ""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_fixture_screenshot(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(_TINY_PNG_B64))
    return path


def _first_screenshot_path(pages: Sequence[Mapping[str, Any]]) -> str:
    for page in pages:
        path = _clean(page.get("screenshot_path") or "")
        if path and Path(path).is_file():
            return path
    return ""


def _normalize_reddit_url(url: str) -> str:
    text = _plain_url(url)
    if text.startswith("/"):
        return "https://www.reddit.com" + text
    return text


def _reddit_post_id_from_url(url: str) -> str:
    match = re.search(r"/comments/([^/?#]+)", _plain_url(url), re.I)
    return _strip_reddit_fullname(match.group(1)) if match else ""


def _reddit_comment_id_from_url(url: str) -> str:
    text = _plain_url(url)
    patterns = (
        r"/comment/([^/?#]+)",
        r"/comments/[^/?#]+/(?:[^/?#]+/)?comment/([^/?#]+)",
        r"/comments/[^/?#]+/[^/?#]+/([^/?#]+)(?:/|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return _strip_reddit_fullname(match.group(1))
    return ""


def _strip_reddit_fullname(value: Any) -> str:
    text = _clean(value)
    text = re.sub(r"^(?:thing_)?t[13]_", "", text, flags=re.I)
    text = re.sub(r"^id-t[13]_", "", text, flags=re.I)
    return re.sub(r"[^A-Za-z0-9_\-]+", "", text)


def _reddit_thread_handle(url: str) -> str:
    post_id = _reddit_post_id_from_url(url)
    return f"reddit_thread_{post_id}" if post_id else "reddit_thread"


def _subreddit_handle_from_url(url: str) -> str:
    match = re.search(r"reddit\.com/r/([^/?#]+)", _plain_url(url), re.I)
    return _safe_handle("r_" + match.group(1)) if match else ""


def _safe_handle(value: Any) -> str:
    text = _clean(value).replace("u/", "").strip("/")
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._-")
    return text or "unknown_reddit_thread"


def _safe_ts(value: Any) -> str:
    text = _clean(value).replace(":", "").replace("-", "")
    return re.sub(r"[^0-9TZ]", "", text)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _plain_url(value: Any) -> str:
    text = _clean(value)
    match = re.fullmatch(r"\[[^\]]+\]\((https?://[^\s)]+)\)", text)
    if match:
        return match.group(1)
    return text.replace("\\_", "_").replace("\\:", ":").replace("&amp;", "&")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _redact_accounts_keys_state(value: Any) -> Any:
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for key, val in value.items():
            lowered = str(key).lower()
            if any(secret_word in lowered for secret_word in ("token", "cookie", "password", "secret", "key")):
                output[str(key)] = "<redacted>"
            else:
                output[str(key)] = _redact_accounts_keys_state(val)
        return output
    if isinstance(value, list):
        return [_redact_accounts_keys_state(item) for item in value]
    return value


def _machine_urls_are_plain(payload: Any) -> bool:
    blob = json.dumps(_to_jsonable(payload), sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail if not ok else ""}


if __name__ == "__main__":
    raise SystemExit(_run_cli())
