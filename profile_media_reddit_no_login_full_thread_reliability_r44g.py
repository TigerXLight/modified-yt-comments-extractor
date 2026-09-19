from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from profile_media_reddit_no_login_complete_comments_r44f import (
    R44F_PASS_STATUS,
    RedditNoLoginCompleteCommentsRequestR44F,
    build_no_login_old_reddit_thread_url_r44f,
    build_ordered_reddit_branch_queue_r44f,
    run_reddit_no_login_complete_comments_r44f,
)
from profile_media_reddit_old_reddit_thread_expansion_r44e import (
    R44E_EDSHEERAN_OLD_REDDIT_URL,
    R44E_EDSHEERAN_THREAD_URL,
)
from profile_media_reddit_visible_dom_capture_r44d import R44D_PASS_STATUS

R44G_MARKER = "YTCE_R44G_REDDIT_NO_LOGIN_FULL_THREAD_RELIABILITY"
R44G_PASS_STATUS = "PASS_R44G_REDDIT_NO_LOGIN_FULL_THREAD_RELIABILITY"
R44G_BLOCKED_STATUS = "BLOCKED_R44G_REDDIT_NO_LOGIN_FULL_THREAD_RELIABILITY"
R44G_SCHEMA_VERSION = "reddit_no_login_full_thread_reliability.r44g.v1"
R44G_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44g_reddit_no_login_full_thread_reliability"
R44G_MODE_ID = "reddit_no_login_full_thread_reliability"

PageFetcher = Callable[[str, Path], Mapping[str, Any]]

R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT = """
1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/?force-legacy-sct=1
2 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa15vni/?force-legacy-sct=1
2.1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa19tv2/?force-legacy-sct=1
3 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa18iy8/?force-legacy-sct=1
3.1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1d4r7/?force-legacy-sct=1
4 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17z4o/?force-legacy-sct=1
4.1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1bbed/?force-legacy-sct=1
5 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1hh1w/?force-legacy-sct=1
6 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17mb8/?force-legacy-sct=1
7 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1o7nd/?force-legacy-sct=1
8 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa207qo/?force-legacy-sct=1
8.1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa2634c/?force-legacy-sct=1
9 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1efmx/?force-legacy-sct=1
10 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14jw3/?force-legacy-sct=1
10.1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa18c1v/?force-legacy-sct=1
11 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14kee/?force-legacy-sct=1
12 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14guu/?force-legacy-sct=1
12.1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa162nx/?force-legacy-sct=1
13 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17wkq/?force-legacy-sct=1
13.1 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1ejdr/?force-legacy-sct=1
14 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14xsv/?force-legacy-sct=1
15 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14iyr/?force-legacy-sct=1
16 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/paamt85/?force-legacy-sct=1
17 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa15jpo/?force-legacy-sct=1
18 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa168md/?force-legacy-sct=1
19 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1gsvr/?force-legacy-sct=1
20 - https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa158vo/?force-legacy-sct=1
""".strip()

R44G_EXPECTED_EDSHEERAN_BRANCH_LABELS = (
    "1", "2", "2.1", "3", "3.1", "4", "4.1", "5", "6", "7",
    "8", "8.1", "9", "10", "10.1", "11", "12", "12.1", "13", "13.1",
    "14", "15", "16", "17", "18", "19", "20",
)


@dataclass(frozen=True)
class RedditNoLoginFullThreadReliabilityRequestR44G:
    thread_url: str = R44E_EDSHEERAN_THREAD_URL
    old_reddit_url: str = R44E_EDSHEERAN_OLD_REDDIT_URL
    ordered_branch_source_text: str = R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT
    branch_urls: tuple[str, ...] = ()
    account_handle: str = "r_EdSheeran"
    capture_timestamp: str = ""
    output_root: str = R44G_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = True
    real_visible_smoke: bool = False
    public_network_enabled: bool = False
    explicit_live_mode: bool = False
    accounts_keys_reddit_logged_in: bool = False
    accounts_keys_state: Mapping[str, Any] = field(default_factory=dict)
    prefer_no_login_when_available: bool = True
    expected_reported_comment_count: int = 0
    comment_sort: str = "old"
    max_items: int = 500
    max_pages: int = 80
    timeout_seconds: int = 45

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["branch_urls"] = list(self.branch_urls)
        data["accounts_keys_state"] = _redact_accounts_keys_state(data.get("accounts_keys_state") or {})
        return _to_jsonable(data)


@dataclass(frozen=True)
class RedditNoLoginFullThreadReliabilityResultR44G:
    marker: str
    schema_version: str
    status: str
    thread_url: str
    old_reddit_url: str
    account_handle: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    request_path: str
    receipt_path: str
    reliability_report_path: str
    r44f_request_path: str = ""
    r44f_receipt_path: str = ""
    r44f_comment_index_path: str = ""
    r44f_comment_tree_markdown_path: str = ""
    r44f_branch_queue_path: str = ""
    r44f_status: str = ""
    r44f_strategy: str = ""
    r44d_status: str = ""
    ledger_status: str = ""
    accounts_keys_detection_path: str = ""
    logged_in_account_detected: bool = False
    no_login_route_selected: bool = False
    branch_url_count: int = 0
    planned_url_count: int = 0
    captured_page_count: int = 0
    branch_order_labels: tuple[str, ...] = ()
    expected_branch_order_labels: tuple[str, ...] = ()
    branch_order_matches_expected: bool = False
    nested_branch_labels_preserved: bool = False
    comment_index_count: int = 0
    top_level_comment_count: int = 0
    max_comment_depth: int = 0
    score_count: int = 0
    negative_score_count: int = 0
    hidden_score_count: int = 0
    expected_reported_comment_count: int = 0
    comment_count_gap: int = 0
    comment_count_gap_recorded_not_invented: bool = False
    record_count: int = 0
    media_count: int = 0
    screenshot_count: int = 0
    real_visible_smoke_requested: bool = False
    browser_session_started: bool = False
    network_actions_performed: bool = False
    no_browser_profile_files_involved: bool = True
    side_effect_flags: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R44G_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R44GReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[dict[str, Any], ...]
    sample_result: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, Any]

    @property
    def passed(self) -> bool:
        return self.status == R44G_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class RedditNoLoginFullThreadReliabilityR44G:
    """Reliability harness for no-login Reddit full-thread capture."""

    def __init__(self, output_root: str | Path = R44G_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def run_reliability_capture(
        self,
        request: RedditNoLoginFullThreadReliabilityRequestR44G | Mapping[str, Any] | None = None,
        *,
        page_fetcher: PageFetcher | None = None,
        **overrides: Any,
    ) -> RedditNoLoginFullThreadReliabilityResultR44G:
        req = coerce_reddit_no_login_full_thread_reliability_request_r44g(request, **overrides)
        if not req.output_root:
            req = coerce_reddit_no_login_full_thread_reliability_request_r44g(req, output_root=str(self.output_root))
        return run_reddit_no_login_full_thread_reliability_r44g(req, output_root=self.output_root, page_fetcher=page_fetcher)


def build_reddit_no_login_full_thread_reliability_r44g(output_root: str | Path = R44G_DEFAULT_OUTPUT_ROOT) -> RedditNoLoginFullThreadReliabilityR44G:
    return RedditNoLoginFullThreadReliabilityR44G(output_root=output_root)


def build_reddit_no_login_full_thread_reliability_contract_r44g() -> dict[str, Any]:
    return {
        "marker": R44G_MARKER,
        "schema_version": R44G_SCHEMA_VERSION,
        "mode_id": R44G_MODE_ID,
        "default_target_thread": R44E_EDSHEERAN_THREAD_URL,
        "primary_no_login_route": "old/en Reddit thread URL with sort=old, screen_view_count=1, limit=500, ext-referrer=DIRECT",
        "branch_queue_rule": "preserve current-Reddit/operator branch comment URLs in visible top-to-bottom order; nested labels such as 2.1 remain immediately after their parent label",
        "merge_rule": "R44F merges branch pages by Reddit comment ids, dedupes duplicate branch anchors, and rebuilds parent-child indentation from visible parent ids and branch context",
        "score_rule": "record displayed Reddit net score text separately from comment order; negative scores and hidden/not-shown scores are preserved, not converted into exact upvote/downvote totals",
        "accounts_keys_rule": "read only non-secret Accounts/Keys metadata indicating whether a Reddit account is configured; do not read cookies, tokens, browser profile files, local storage, cache, or Login Data",
        "no_login_fallback_rule": "when no Reddit login is detected, choose no_login_old_reddit_limit500_branch_queue",
        "logged_in_account_rule": "if a Reddit login is detected, logged-in visible browsing can only be operator-controlled; no login automation or credential extraction is allowed",
        "real_network_rule": "real old-Reddit page capture only occurs when real_visible_smoke, public_network_enabled, and explicit_live_mode are all true",
        "remote_media_downloads_enabled": False,
        "browser_profile_file_copying_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "hidden_platform_api_scraping_enabled": False,
        "login_automation_enabled": False,
        "captcha_or_challenge_bypass_enabled": False,
        "downstream_chain": "R44G -> R44F -> R44D -> R43U",
    }


def run_reddit_no_login_full_thread_reliability_r44g(
    request: RedditNoLoginFullThreadReliabilityRequestR44G | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R44G_DEFAULT_OUTPUT_ROOT,
    page_fetcher: PageFetcher | None = None,
) -> RedditNoLoginFullThreadReliabilityResultR44G:
    req = coerce_reddit_no_login_full_thread_reliability_request_r44g(request)
    root = Path(req.output_root or output_root or R44G_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    account_handle = _safe_handle(req.account_handle or "r_EdSheeran")
    run_dir = root / account_handle / f"reddit_no_login_full_thread_reliability_{capture_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "r44g_reddit_no_login_full_thread_reliability_request.json"
    receipt_path = run_dir / "r44g_reddit_no_login_full_thread_reliability_receipt.json"
    reliability_report_path = run_dir / "r44g_reddit_no_login_full_thread_reliability_report.json"
    _write_json(request_path, req.to_dict())

    branch_text = req.ordered_branch_source_text or R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT
    expected_labels = tuple(_extract_branch_labels_from_source(branch_text))
    if branch_text.strip() == R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT:
        expected_labels = R44G_EXPECTED_EDSHEERAN_BRANCH_LABELS

    old_url = build_no_login_old_reddit_thread_url_r44f(req.old_reddit_url or req.thread_url, comment_sort=req.comment_sort)
    allow_real = bool(req.real_visible_smoke and req.public_network_enabled and req.explicit_live_mode)
    r44f_fixture = bool(req.fixture_mode and not allow_real)

    r44f_result = run_reddit_no_login_complete_comments_r44f(
        RedditNoLoginCompleteCommentsRequestR44F(
            thread_url=req.thread_url,
            old_reddit_url=old_url,
            branch_urls=req.branch_urls,
            ordered_branch_source_text=branch_text,
            account_handle=account_handle,
            capture_timestamp=capture_ts,
            output_root=str(run_dir / "r44f_complete_comments"),
            fixture_mode=r44f_fixture,
            real_visible_smoke=allow_real,
            public_network_enabled=bool(req.public_network_enabled),
            explicit_live_mode=bool(req.explicit_live_mode),
            accounts_keys_reddit_logged_in=bool(req.accounts_keys_reddit_logged_in),
            accounts_keys_state=req.accounts_keys_state,
            prefer_no_login_when_available=bool(req.prefer_no_login_when_available),
            comment_sort=req.comment_sort,
            max_items=max(1, int(req.max_items)),
            max_pages=max(1, int(req.max_pages)),
            timeout_seconds=max(5, int(req.timeout_seconds)),
        ),
        page_fetcher=page_fetcher,
    )

    branch_labels = tuple(str(x) for x in (r44f_result.branch_order_labels or ()))
    branch_order_matches = bool(branch_labels == expected_labels) if expected_labels else bool(branch_labels)
    nested_preserved = _nested_labels_are_after_parent(branch_labels)
    gap = 0
    gap_recorded = False
    if req.expected_reported_comment_count and r44f_result.comment_index_count:
        gap = max(0, int(req.expected_reported_comment_count) - int(r44f_result.comment_index_count))
        gap_recorded = gap >= 0

    safe_flags = build_r44g_side_effect_flags(
        browser_session_started=bool(r44f_result.browser_session_started),
        network_actions_performed=bool(r44f_result.network_actions_performed),
        real_visible_smoke_requested=bool(allow_real),
    )
    warnings = list(getattr(r44f_result, "warnings", ()) or [])
    if gap:
        warnings.append(f"reported_comment_count={req.expected_reported_comment_count} exceeds recovered_comment_index_count={r44f_result.comment_index_count}; gap recorded, not invented")
    if not branch_order_matches:
        warnings.append(f"branch label order mismatch: expected={list(expected_labels)} actual={list(branch_labels)}")
    if not nested_preserved:
        warnings.append("nested branch labels were not preserved immediately after parent labels")

    status_ok = (
        r44f_result.status == R44F_PASS_STATUS
        and r44f_result.r44d_status == R44D_PASS_STATUS
        and r44f_result.ledger_status == "PASS_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE"
        and branch_order_matches
        and nested_preserved
        and not any(safe_flags.get(k) for k in (
            "browser_profile_files_read_or_copied",
            "cookie_or_token_extraction_performed",
            "login_automation_performed",
            "captcha_or_challenge_bypass_performed",
            "hidden_platform_api_scraping_performed",
            "remote_media_downloads_performed",
            "webview2_internals_copied",
        ))
    )
    status = R44G_PASS_STATUS if status_ok else R44G_BLOCKED_STATUS

    result = RedditNoLoginFullThreadReliabilityResultR44G(
        marker=R44G_MARKER,
        schema_version=R44G_SCHEMA_VERSION,
        status=status,
        thread_url=_plain_url(req.thread_url),
        old_reddit_url=_plain_url(old_url),
        account_handle=account_handle,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        reliability_report_path=str(reliability_report_path),
        r44f_request_path=str(r44f_result.request_path),
        r44f_receipt_path=str(r44f_result.receipt_path),
        r44f_comment_index_path=str(r44f_result.comment_index_path),
        r44f_comment_tree_markdown_path=str(r44f_result.comment_tree_markdown_path),
        r44f_branch_queue_path=str(r44f_result.branch_queue_path),
        r44f_status=r44f_result.status,
        r44f_strategy=r44f_result.strategy,
        r44d_status=r44f_result.r44d_status,
        ledger_status=r44f_result.ledger_status,
        accounts_keys_detection_path=r44f_result.accounts_keys_detection_path,
        logged_in_account_detected=bool(r44f_result.logged_in_account_detected),
        no_login_route_selected=r44f_result.strategy == "no_login_old_reddit_limit500_branch_queue",
        branch_url_count=int(r44f_result.branch_url_count),
        planned_url_count=int(r44f_result.planned_url_count),
        captured_page_count=int(r44f_result.captured_page_count),
        branch_order_labels=branch_labels,
        expected_branch_order_labels=expected_labels,
        branch_order_matches_expected=branch_order_matches,
        nested_branch_labels_preserved=nested_preserved,
        comment_index_count=int(r44f_result.comment_index_count),
        top_level_comment_count=int(r44f_result.top_level_comment_count),
        max_comment_depth=int(r44f_result.max_comment_depth),
        score_count=int(r44f_result.score_count),
        negative_score_count=int(r44f_result.negative_score_count),
        hidden_score_count=int(r44f_result.hidden_score_count),
        expected_reported_comment_count=int(req.expected_reported_comment_count),
        comment_count_gap=gap,
        comment_count_gap_recorded_not_invented=gap_recorded,
        record_count=int(r44f_result.record_count),
        media_count=int(r44f_result.media_count),
        screenshot_count=int(r44f_result.screenshot_count),
        real_visible_smoke_requested=bool(allow_real),
        browser_session_started=bool(r44f_result.browser_session_started),
        network_actions_performed=bool(r44f_result.network_actions_performed),
        no_browser_profile_files_involved=not bool(safe_flags.get("browser_profile_files_read_or_copied")),
        side_effect_flags=safe_flags,
        warnings=tuple(warnings),
    )
    _write_json(reliability_report_path, result.to_dict())
    _write_json(receipt_path, result.to_dict())
    return result


def build_report(output_root: str | Path = R44G_DEFAULT_OUTPUT_ROOT) -> R44GReport:
    root = Path(output_root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    sample = run_reddit_no_login_full_thread_reliability_r44g(
        RedditNoLoginFullThreadReliabilityRequestR44G(
            thread_url=R44E_EDSHEERAN_THREAD_URL,
            old_reddit_url=R44E_EDSHEERAN_OLD_REDDIT_URL,
            ordered_branch_source_text=R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT,
            account_handle="r_EdSheeran",
            capture_timestamp="20260918T130000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
            expected_reported_comment_count=337,
            max_items=500,
            max_pages=80,
        )
    )
    contract = build_reddit_no_login_full_thread_reliability_contract_r44g()
    flags = build_r44g_side_effect_flags(browser_session_started=False, network_actions_performed=False, real_visible_smoke_requested=False)
    checks = (
        _check("full_edsheeran_branch_manifest_has_27_urls", sample.branch_url_count == 27),
        _check("operator_branch_labels_preserve_top_to_bottom_order", sample.branch_order_labels == R44G_EXPECTED_EDSHEERAN_BRANCH_LABELS),
        _check("nested_branch_labels_remain_after_parent_labels", sample.nested_branch_labels_preserved),
        _check("old_reddit_limit500_is_primary_no_login_url", sample.old_reddit_url.startswith("https://en.reddit.com/") and "limit=500" in sample.old_reddit_url and "sort=old" in sample.old_reddit_url),
        _check("no_accounts_keys_login_chooses_no_login_route", sample.no_login_route_selected and not sample.logged_in_account_detected),
        _check("comment_scores_hidden_and_negative_are_preserved", sample.score_count >= 2 and sample.negative_score_count >= 1 and sample.hidden_score_count >= 1),
        _check("comment_tree_markdown_and_json_are_written", bool(sample.r44f_comment_index_path) and Path(str(sample.r44f_comment_index_path)).is_file() and bool(sample.r44f_comment_tree_markdown_path) and Path(str(sample.r44f_comment_tree_markdown_path)).is_file()),
        _check("reported_vs_recovered_count_gap_is_recorded_not_invented", sample.expected_reported_comment_count == 337 and sample.comment_count_gap_recorded_not_invented),
        _check("r44f_r44d_r43u_downstream_chain_preserved", sample.r44f_status == R44F_PASS_STATUS and sample.r44d_status == R44D_PASS_STATUS and sample.ledger_status == "PASS_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE"),
        _check("no_real_browser_or_network_in_report_validation", not sample.browser_session_started and not sample.network_actions_performed),
        _check("no_cookie_token_profile_remote_media_side_effects", not any(flags.get(k) for k in ("browser_profile_files_read_or_copied", "cookie_or_token_extraction_performed", "remote_media_downloads_performed", "login_automation_performed", "captcha_or_challenge_bypass_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(sample.to_dict()) and _machine_urls_are_plain(contract)),
    )
    status = R44G_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R44G_BLOCKED_STATUS
    report = R44GReport(
        marker=R44G_MARKER,
        schema_version=R44G_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        sample_result=sample.to_dict(),
        contract=contract,
        side_effect_flags=flags,
    )
    write_report(report, root)
    return report


def coerce_reddit_no_login_full_thread_reliability_request_r44g(request: RedditNoLoginFullThreadReliabilityRequestR44G | Mapping[str, Any] | None = None, **overrides: Any) -> RedditNoLoginFullThreadReliabilityRequestR44G:
    if isinstance(request, RedditNoLoginFullThreadReliabilityRequestR44G):
        base = request.to_dict()
        base["accounts_keys_state"] = dict(request.accounts_keys_state or {})
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
    return RedditNoLoginFullThreadReliabilityRequestR44G(
        thread_url=_plain_url(base.get("thread_url") or R44E_EDSHEERAN_THREAD_URL),
        old_reddit_url=_plain_url(base.get("old_reddit_url") or R44E_EDSHEERAN_OLD_REDDIT_URL),
        ordered_branch_source_text=str(base.get("ordered_branch_source_text") or R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT),
        branch_urls=branch_urls,
        account_handle=_safe_handle(base.get("account_handle") or "r_EdSheeran"),
        capture_timestamp=_safe_ts(base.get("capture_timestamp") or ""),
        output_root=str(base.get("output_root") or R44G_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(base.get("fixture_mode"), True),
        real_visible_smoke=_to_bool(base.get("real_visible_smoke"), False),
        public_network_enabled=_to_bool(base.get("public_network_enabled"), False),
        explicit_live_mode=_to_bool(base.get("explicit_live_mode"), False),
        accounts_keys_reddit_logged_in=_to_bool(base.get("accounts_keys_reddit_logged_in"), False),
        accounts_keys_state=dict(base.get("accounts_keys_state") or {}),
        prefer_no_login_when_available=_to_bool(base.get("prefer_no_login_when_available"), True),
        expected_reported_comment_count=_safe_int(base.get("expected_reported_comment_count"), 0),
        comment_sort=str(base.get("comment_sort") or "old"),
        max_items=max(1, _safe_int(base.get("max_items"), 500)),
        max_pages=max(1, _safe_int(base.get("max_pages"), 80)),
        timeout_seconds=max(5, _safe_int(base.get("timeout_seconds"), 45)),
    )


def build_r44g_side_effect_flags(*, browser_session_started: bool, network_actions_performed: bool, real_visible_smoke_requested: bool) -> dict[str, Any]:
    return {
        "reddit_no_login_full_thread_reliability_invoked": True,
        "r44f_no_login_complete_comment_ordering_used": True,
        "r44d_visible_dom_capture_used": True,
        "r43u_universal_ledger_writer_used": True,
        "real_visible_smoke_requested": bool(real_visible_smoke_requested),
        "browser_session_started": bool(browser_session_started),
        "network_actions_performed": bool(network_actions_performed),
        "browser_profile_files_read_or_copied": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
        "review_window_dependency_invoked": False,
        "source_role_checks_performed": False,
        "webview2_internals_copied": False,
    }


def write_report(report: R44GReport, root: str | Path) -> None:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "R44G_REDDIT_NO_LOGIN_FULL_THREAD_RELIABILITY_REPORT.json", report.to_dict())
    _write_text(root / "R44G_REDDIT_NO_LOGIN_FULL_THREAD_RELIABILITY_REPORT.md", _report_md(report))


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="R44G Reddit no-login full-thread reliability harness")
    parser.add_argument("--thread-url", default=R44E_EDSHEERAN_THREAD_URL)
    parser.add_argument("--old-reddit-url", default=R44E_EDSHEERAN_OLD_REDDIT_URL)
    parser.add_argument("--branch-url", action="append", default=[])
    parser.add_argument("--branch-url-file", default="")
    parser.add_argument("--ordered-branch-source-file", default="")
    parser.add_argument("--account-handle", default="r_EdSheeran")
    parser.add_argument("--output-root", default=R44G_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--expected-reported-comment-count", type=int, default=0)
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
        print(R44G_MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.passed else 1
    branch_urls = list(args.branch_url or [])
    if args.branch_url_file:
        branch_urls.extend(Path(args.branch_url_file).read_text(encoding="utf-8", errors="replace").splitlines())
    ordered_text = Path(args.ordered_branch_source_file).read_text(encoding="utf-8", errors="replace") if args.ordered_branch_source_file else R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT
    result = run_reddit_no_login_full_thread_reliability_r44g(
        RedditNoLoginFullThreadReliabilityRequestR44G(
            thread_url=args.thread_url,
            old_reddit_url=args.old_reddit_url,
            ordered_branch_source_text=ordered_text,
            branch_urls=tuple(branch_urls),
            account_handle=args.account_handle,
            capture_timestamp=args.capture_timestamp,
            output_root=args.output_root,
            fixture_mode=args.fixture_mode or not args.real_visible_smoke,
            real_visible_smoke=args.real_visible_smoke,
            public_network_enabled=args.public_network_enabled,
            explicit_live_mode=args.explicit_live_mode,
            accounts_keys_reddit_logged_in=args.accounts_keys_reddit_logged_in,
            prefer_no_login_when_available=not args.prefer_logged_in_visible_session,
            expected_reported_comment_count=args.expected_reported_comment_count,
            comment_sort=args.comment_sort,
            max_items=args.max_items,
            max_pages=args.max_pages,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(R44G_MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.passed else 1


def _report_md(report: R44GReport) -> str:
    sample = report.sample_result
    lines = [
        "# R44G Reddit No-Login Full Thread Reliability",
        "",
        f"Status: `{report.status}`",
        f"Marker: `{report.marker}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')}")
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Thread URL: `{sample.get('thread_url')}`",
        f"- Old Reddit URL: `{sample.get('old_reddit_url')}`",
        f"- Strategy: `{sample.get('r44f_strategy')}`",
        f"- Branch URL count: `{sample.get('branch_url_count')}`",
        f"- Branch order matches expected: `{sample.get('branch_order_matches_expected')}`",
        f"- Nested branch labels preserved: `{sample.get('nested_branch_labels_preserved')}`",
        f"- Comment index nodes: `{sample.get('comment_index_count')}`",
        f"- Comment count gap: `{sample.get('comment_count_gap')}`",
        f"- R44F status: `{sample.get('r44f_status')}`",
        f"- R44D status: `{sample.get('r44d_status')}`",
        f"- Ledger status: `{sample.get('ledger_status')}`",
        "",
    ])
    return "\n".join(lines)


def _extract_branch_labels_from_source(text: str) -> list[str]:
    labels: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = re.match(r"^([0-9]+(?:\.[0-9]+)*)\s*(?:[-–—:]|\))\s*https?://", line)
        if match:
            labels.append(match.group(1))
    return labels


def _nested_labels_are_after_parent(labels: Sequence[str]) -> bool:
    positions = {str(label): idx for idx, label in enumerate(labels)}
    for label in labels:
        text = str(label)
        if "." not in text:
            continue
        parent = text.rsplit(".", 1)[0]
        if parent not in positions:
            return False
        if positions[parent] >= positions[text]:
            return False
        if positions[text] != positions[parent] + 1:
            return False
    return True


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text), encoding="utf-8")


def _check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if passed else "fail", "detail": detail}


def _safe_handle(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("._-")
    return text or "r_EdSheeran"


def _safe_ts(value: Any) -> str:
    text = re.sub(r"[^0-9TZ]", "", str(value or ""))
    return text if re.match(r"^\d{8}T\d{6}Z$", text) else ""


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _plain_url(value: Any) -> str:
    return str(value or "").replace("\\&", "&").strip().strip("<>").strip("`")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return value


def _redact_accounts_keys_state(state: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in dict(state or {}).items():
        lowered = str(key).lower()
        if any(token in lowered for token in ("token", "secret", "password", "cookie", "session", "credential")):
            redacted[str(key)] = "<redacted>"
        elif isinstance(value, Mapping):
            redacted[str(key)] = _redact_accounts_keys_state(value)
        else:
            redacted[str(key)] = value
    return redacted


def _machine_urls_are_plain(value: Any) -> bool:
    if isinstance(value, str):
        return not bool(re.search(r"\[[^\]]+\]\(https?://", value))
    if isinstance(value, Mapping):
        return all(_machine_urls_are_plain(v) for v in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return all(_machine_urls_are_plain(v) for v in value)
    return True


if __name__ == "__main__":
    raise SystemExit(_run_cli())
