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

from profile_media_reddit_visible_dom_capture_r44d import (
    R44D_PASS_STATUS,
    RedditVisibleDomCaptureRequestR44D,
    run_reddit_visible_dom_capture_r44d,
)

R44E_MARKER = "YTCE_R44E_REDDIT_OLD_REDDIT_THREAD_BRANCH_EXPANSION"
R44E_PASS_STATUS = "PASS_R44E_REDDIT_OLD_REDDIT_THREAD_BRANCH_EXPANSION"
R44E_BLOCKED_STATUS = "BLOCKED_R44E_REDDIT_OLD_REDDIT_THREAD_BRANCH_EXPANSION"
R44E_SCHEMA_VERSION = "reddit_old_reddit_thread_branch_expansion.r44e.v1"
R44E_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44e_reddit_old_reddit_thread_branch_expansion"
R44E_MODE_ID = "reddit_old_reddit_thread_branch_expansion"

R44E_EDSHEERAN_THREAD_URL = "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/"
R44E_EDSHEERAN_OLD_REDDIT_URL = "https://en.reddit.com/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/?sort=old&screen_view_count=1&limit=500&ext-referrer=DIRECT"
R44E_EDSHEERAN_BRANCH_URLS = (
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa15vni/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa19tv2/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa18iy8/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1d4r7/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17z4o/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1bbed/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1hh1w/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17mb8/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1o7nd/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa207qo/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa2634c/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1efmx/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14jw3/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa18c1v/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14kee/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14guu/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa162nx/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa17wkq/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1ejdr/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14xsv/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa14iyr/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/paamt85/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa15jpo/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa168md/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1gsvr/?force-legacy-sct=1",
    "https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa158vo/?force-legacy-sct=1",
)

_TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
PageFetcher = Callable[[str, Path], Mapping[str, Any]]


@dataclass(frozen=True)
class RedditOldThreadExpansionRequestR44E:
    thread_url: str = R44E_EDSHEERAN_THREAD_URL
    old_reddit_url: str = R44E_EDSHEERAN_OLD_REDDIT_URL
    branch_urls: tuple[str, ...] = R44E_EDSHEERAN_BRANCH_URLS
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R44E_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    real_visible_smoke: bool = False
    public_network_enabled: bool = False
    explicit_live_mode: bool = False
    include_branch_urls: bool = True
    prefer_old_reddit: bool = True
    max_items: int = 500
    timeout_seconds: int = 45
    visible_dom_html_by_url: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["branch_urls"] = list(self.branch_urls)
        data["visible_dom_html_by_url"] = {str(k): str(v) for k, v in self.visible_dom_html_by_url.items()}
        return _to_jsonable(data)


@dataclass(frozen=True)
class RedditOldThreadExpansionResultR44E:
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
    capture_plan_path: str
    combined_visible_dom_html_path: str
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
    browser_session_started: bool = False
    network_actions_performed: bool = False
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R44E_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R44EReport:
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
        return self.status == R44E_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class RedditOldRedditThreadExpansionR44E:
    """Old/en Reddit thread expansion coordinator above R44D.

    R44E prefers old/en Reddit for thread captures because old Reddit can expose
    a large `limit=500` comment page without the current Reddit multi-page UI.
    When branch/continue URLs are supplied or discovered, R44E queues them as
    additional visible pages, merges their visible DOM receipts, dedupes by
    Reddit id downstream through R44D/R43U, and preserves screenshots. It never
    uses credentials, browser profile files, cookies, token extraction, login
    automation, hidden APIs, challenge bypass, or remote media downloads.
    """

    def __init__(self, output_root: str | Path = R44E_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def run_thread_expansion(
        self,
        request: RedditOldThreadExpansionRequestR44E | Mapping[str, Any] | None = None,
        *,
        page_fetcher: PageFetcher | None = None,
        **overrides: Any,
    ) -> RedditOldThreadExpansionResultR44E:
        req = coerce_reddit_old_thread_expansion_request_r44e(request, **overrides)
        return run_reddit_old_reddit_thread_expansion_r44e(req, output_root=self.output_root, page_fetcher=page_fetcher)


def build_reddit_old_reddit_thread_expansion_r44e(output_root: str | Path = R44E_DEFAULT_OUTPUT_ROOT) -> RedditOldRedditThreadExpansionR44E:
    return RedditOldRedditThreadExpansionR44E(output_root=output_root)


def build_reddit_old_reddit_thread_expansion_contract_r44e() -> dict[str, Any]:
    return {
        "marker": R44E_MARKER,
        "schema_version": R44E_SCHEMA_VERSION,
        "mode_id": R44E_MODE_ID,
        "primary_strategy": "prefer old/en Reddit thread HTML with sort=old, limit=500, screen_view_count=1 before falling back to current Reddit multi-page branch capture",
        "old_reddit_thread_url_rule": "https://en.reddit.com/r/<subreddit>/comments/<post_id>/?sort=old&screen_view_count=1&limit=500&ext-referrer=DIRECT",
        "branch_url_rule": "preserve supplied /comment/<comment_id> URLs and add force-legacy-sct=1 for legacy branch pages",
        "current_reddit_caveat": "current Reddit may hide deep branches behind separate comment pages; those branch pages must be queued rather than assumed captured",
        "twitter_old_caveat": "this old-Reddit preference is Reddit-specific; it does not imply old Twitter works without login",
        "downstream_adapter": "profile_media_reddit_visible_dom_capture_r44d",
        "downstream_ledger": "profile_media_universal_social_account_ledger_contract_r43u",
        "record_mapping": {"thread submission": "post", "thread comments": "reply", "crossposts": "repost_or_reshare"},
        "no_cookie_token_or_browser_profile_copying": True,
        "no_remote_media_downloads": True,
        "hidden_platform_api_scraping_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
    }


def run_reddit_old_reddit_thread_expansion_r44e(
    request: RedditOldThreadExpansionRequestR44E | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R44E_DEFAULT_OUTPUT_ROOT,
    page_fetcher: PageFetcher | None = None,
) -> RedditOldThreadExpansionResultR44E:
    req = coerce_reddit_old_thread_expansion_request_r44e(request)
    root = Path(req.output_root or output_root or R44E_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    thread_url = _plain_url(req.thread_url or R44E_EDSHEERAN_THREAD_URL)
    old_url = canonicalize_old_reddit_thread_url_r44e(req.old_reddit_url or thread_url)
    account_handle = _safe_handle(req.account_handle or _subreddit_handle_from_url(thread_url) or "reddit_thread")
    run_dir = root / account_handle / f"reddit_old_reddit_thread_expansion_{capture_ts}"
    evidence_dir = run_dir / "visible_old_reddit_evidence"
    screenshot_dir = run_dir / "visible_old_reddit_screenshots"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    request_path = run_dir / "r44e_reddit_old_reddit_thread_expansion_request.json"
    receipt_path = run_dir / "r44e_reddit_old_reddit_thread_expansion_receipt.json"
    capture_plan_path = run_dir / "old_reddit_capture_plan.json"
    combined_html_path = evidence_dir / "combined_visible_old_reddit_dom.html"
    _write_json(request_path, req.to_dict())

    branch_urls = normalize_reddit_branch_urls_r44e(req.branch_urls if req.include_branch_urls else ())
    planned_urls = build_old_reddit_capture_plan_urls_r44e(thread_url=thread_url, old_reddit_url=old_url, branch_urls=branch_urls)
    _write_json(capture_plan_path, {"thread_url": thread_url, "old_reddit_url": old_url, "branch_urls": branch_urls, "planned_urls": planned_urls})

    warnings: list[str] = []
    pages: list[dict[str, Any]] = []
    browser_started = False
    network_actions = False
    supplied_pages = {_plain_url(k): str(v) for k, v in dict(req.visible_dom_html_by_url or {}).items()}

    if supplied_pages:
        for index, url in enumerate(planned_urls, start=1):
            html = supplied_pages.get(url) or supplied_pages.get(_plain_url(url)) or ""
            if not html:
                continue
            shot = _write_fixture_screenshot(screenshot_dir / f"page_{index:03d}.png")
            pages.append({"url": url, "final_url": url, "status_code": 200, "html": html, "screenshot_path": str(shot), "capture_mode": "supplied_visible_dom_html"})
    elif req.fixture_mode:
        fake_pages = build_fake_old_reddit_pages_r44e()
        for index, url in enumerate(planned_urls, start=1):
            html = fake_pages.get(url) or fake_pages.get(old_url) or (next(iter(fake_pages.values())) if fake_pages else "")
            if not html:
                continue
            shot = _write_fixture_screenshot(screenshot_dir / f"page_{index:03d}.png")
            pages.append({"url": url, "final_url": url, "status_code": 200, "html": html, "screenshot_path": str(shot), "capture_mode": "fixture_old_reddit_dom"})
    elif req.real_visible_smoke and req.public_network_enabled and req.explicit_live_mode:
        if page_fetcher is not None:
            for index, url in enumerate(planned_urls, start=1):
                fetched = dict(page_fetcher(url, screenshot_dir / f"page_{index:03d}.png"))
                fetched.setdefault("url", url)
                fetched.setdefault("final_url", url)
                fetched.setdefault("capture_mode", "injected_page_fetcher")
                pages.append(fetched)
            browser_started = any(bool(p.get("browser_session_started")) for p in pages)
            network_actions = any(bool(p.get("network_actions_performed")) for p in pages)
        else:
            pages = _capture_old_reddit_pages_visible_playwright(planned_urls, screenshot_dir=screenshot_dir, timeout_seconds=req.timeout_seconds)
            browser_started = True
            network_actions = True
    else:
        warnings.append("R44E did not start real browser/network because real-visible smoke requires --real-visible-smoke --public-network-enabled --explicit-live-mode.")

    discovered = normalize_reddit_branch_urls_r44e(_discover_continue_urls_from_pages(pages))
    for url in discovered:
        if url not in planned_urls:
            planned_urls.append(url)
    _write_json(capture_plan_path, {"thread_url": thread_url, "old_reddit_url": old_url, "branch_urls": branch_urls, "discovered_continue_urls": discovered, "planned_urls": planned_urls})

    combined = _combine_visible_pages(pages)
    combined_html_path.write_text(combined, encoding="utf-8")
    if not pages:
        warnings.append("No old Reddit pages were captured or supplied.")
        result = _blocked_result(req, root, run_dir, request_path, receipt_path, capture_plan_path, combined_html_path, thread_url, old_url, account_handle, capture_ts, planned_urls, branch_urls, 0, warnings, browser_started, network_actions)
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
    status = R44E_PASS_STATUS if r44d.status == R44D_PASS_STATUS and r44d.record_count > 0 else R44E_BLOCKED_STATUS
    if status != R44E_PASS_STATUS:
        warnings.append(f"R44D downstream old Reddit visible DOM capture did not pass: {r44d.status!r}")

    result = RedditOldThreadExpansionResultR44E(
        marker=R44E_MARKER,
        schema_version=R44E_SCHEMA_VERSION,
        status=status,
        thread_url=thread_url,
        old_reddit_url=old_url,
        account_handle=account_handle,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        capture_plan_path=str(capture_plan_path),
        combined_visible_dom_html_path=str(combined_html_path),
        r44d_receipt_path=str(r44d.receipt_path),
        r44d_status=r44d.status,
        ledger_status=r44d.ledger_status,
        account_capture_dir=str(r44d.account_capture_dir),
        account_record_path=str(r44d.account_record_path),
        account_timeline_path=str(r44d.account_timeline_path),
        media_index_path=str(r44d.media_index_path),
        review_strings_path=str(r44d.review_strings_path),
        planned_url_count=len(planned_urls),
        branch_url_count=len(branch_urls),
        captured_page_count=len(pages),
        discovered_continue_url_count=len(discovered),
        dom_record_block_count=r44d.dom_record_block_count,
        visible_record_count=r44d.visible_record_count,
        record_count=r44d.record_count,
        media_count=r44d.media_count,
        screenshot_count=r44d.screenshot_count,
        browser_session_started=browser_started,
        network_actions_performed=network_actions,
        side_effect_flags=build_r44e_side_effect_flags(browser_session_started=browser_started, network_actions_performed=network_actions),
        warnings=tuple(warnings + list(r44d_payload.get("warnings") or ())),
    )
    _write_json(receipt_path, result.to_dict())
    return result


def build_report(output_root: str | Path = R44E_DEFAULT_OUTPUT_ROOT) -> R44EReport:
    root = Path(output_root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    sample = run_reddit_old_reddit_thread_expansion_r44e(
        RedditOldThreadExpansionRequestR44E(
            thread_url=R44E_EDSHEERAN_THREAD_URL,
            old_reddit_url=R44E_EDSHEERAN_OLD_REDDIT_URL,
            branch_urls=R44E_EDSHEERAN_BRANCH_URLS,
            account_handle="r_EdSheeran",
            capture_timestamp="20260918T110000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
            max_items=500,
        )
    )
    contract = build_reddit_old_reddit_thread_expansion_contract_r44e()
    flags = build_r44e_side_effect_flags(browser_session_started=False, network_actions_performed=False)
    plan_urls = build_old_reddit_capture_plan_urls_r44e(R44E_EDSHEERAN_THREAD_URL, R44E_EDSHEERAN_OLD_REDDIT_URL, R44E_EDSHEERAN_BRANCH_URLS)
    checks = (
        _check("old_reddit_is_preferred_thread_url", sample.old_reddit_url.startswith("https://en.reddit.com/") and "limit=500" in sample.old_reddit_url and "sort=old" in sample.old_reddit_url),
        _check("current_reddit_branch_urls_are_preserved_as_legacy_queue", sample.branch_url_count == len(R44E_EDSHEERAN_BRANCH_URLS) and all("force-legacy-sct=1" in u for u in plan_urls[1:])),
        _check("old_reddit_fixture_extracts_submission_and_comments", sample.status == R44E_PASS_STATUS and sample.record_count >= 3 and sample.visible_record_count >= 3),
        _check("old_reddit_media_metadata_reaches_ledger", sample.media_count >= 1 and bool(sample.media_index_path)),
        _check("r44d_r43u_downstream_chain_preserved", sample.r44d_status == R44D_PASS_STATUS and sample.ledger_status == "PASS_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE"),
        _check("real_network_not_used_in_report_validation", not sample.browser_session_started and not sample.network_actions_performed),
        _check("no_cookie_token_profile_or_remote_media_side_effects", not any(flags.get(k) for k in ("browser_profile_files_read_or_copied", "cookie_or_token_extraction_performed", "remote_media_downloads_performed", "login_automation_performed", "captcha_or_challenge_bypass_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(sample.to_dict()) and _machine_urls_are_plain(contract)),
    )
    status = R44E_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R44E_BLOCKED_STATUS
    report = R44EReport(
        marker=R44E_MARKER,
        schema_version=R44E_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        sample_result=sample.to_dict(),
        contract=contract,
        side_effect_flags=flags,
    )
    write_report(report, root)
    return report


def canonicalize_old_reddit_thread_url_r44e(url: str) -> str:
    text = _plain_url(url)
    if not text:
        text = R44E_EDSHEERAN_THREAD_URL
    split = urlsplit(text)
    netloc = split.netloc.lower()
    path = split.path or "/"
    if "reddit.com" in netloc:
        netloc = "en.reddit.com"
    elif not netloc:
        netloc = "en.reddit.com"
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query.update({"sort": "old", "screen_view_count": "1", "limit": "500", "ext-referrer": "DIRECT"})
    return urlunsplit(("https", netloc, path, urlencode(query), ""))


def normalize_reddit_branch_urls_r44e(urls: Sequence[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in urls or ():
        url = _plain_url(raw)
        if not url:
            continue
        split = urlsplit(url)
        netloc = split.netloc.lower()
        if "reddit.com" in netloc:
            netloc = "en.reddit.com"
        path = split.path
        query = dict(parse_qsl(split.query, keep_blank_values=True))
        query["force-legacy-sct"] = "1"
        normalized = urlunsplit(("https", netloc or "en.reddit.com", path, urlencode(query), ""))
        if normalized not in seen:
            seen.add(normalized)
            output.append(normalized)
    return output


def build_old_reddit_capture_plan_urls_r44e(thread_url: str, old_reddit_url: str = "", branch_urls: Sequence[str] = ()) -> list[str]:
    first = canonicalize_old_reddit_thread_url_r44e(old_reddit_url or thread_url)
    output = [first]
    for url in normalize_reddit_branch_urls_r44e(branch_urls):
        if url not in output:
            output.append(url)
    return output


def extract_continue_thread_urls_from_old_reddit_html_r44e(html_text: str) -> list[str]:
    urls: list[str] = []
    text = html_text or ""
    for match in re.finditer(r"<a\b[^>]+href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", text, re.I | re.S):
        href = html_lib.unescape(match.group(1))
        label = _clean(re.sub(r"<[^>]+>", " ", html_lib.unescape(match.group(2)))).lower()
        if "continue this thread" in label or "more comments" in label:
            urls.append(_normalize_reddit_url(href))
    return normalize_reddit_branch_urls_r44e(urls)


def build_fake_old_reddit_pages_r44e() -> dict[str, str]:
    old = R44E_EDSHEERAN_OLD_REDDIT_URL
    branch = normalize_reddit_branch_urls_r44e([R44E_EDSHEERAN_BRANCH_URLS[0]])[0]
    thread_html = f"""
<html><body>
<div class="thing link" id="thing_t3_1whbgzk" data-fullname="t3_1whbgzk" data-author="Stonerthrowaway710" data-type="link">
  <p class="title"><a class="title" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/">Ed's got a show in 4 days. No band. No openers. What the plan here?</a></p>
  <time datetime="2026-09-15T20:12:09Z">15 Sept 2026</time>
  <div class="usertext-body"><p>Do we think the tour will be canceled?</p><a href="https://i.redd.it/thread_image.jpg">image</a></div>
</div>
<div class="thing comment" id="thing_t1_pa1fs0p" data-fullname="t1_pa1fs0p" data-author="Hassaan18" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa1fs0p/">permalink</a>
  <a class="author">Hassaan18</a>
  <time datetime="2026-09-15T20:20:00Z">1d ago</time>
  <div class="usertext-body"><p>He can do the show. He's done stripped back shows before.</p></div>
  <a href="{branch}">continue this thread</a>
</div>
<div class="thing comment" id="thing_t1_pa15vni" data-fullname="t1_pa15vni" data-author="Wetnorthwest" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa15vni/">permalink</a>
  <a class="author">Wetnorthwest</a>
  <time datetime="2026-09-15T20:22:00Z">1d ago</time>
  <div class="usertext-body"><p>He can absolutely loop the whole show.</p></div>
</div>
</body></html>
""".strip()
    branch_html = """
<html><body>
<div class="thing comment" id="thing_t1_pa1branch" data-fullname="t1_pa1branch" data-author="ertri" data-type="comment">
  <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa1branch/">permalink</a>
  <a class="author">ertri</a>
  <time datetime="2026-09-15T20:23:00Z">1d ago</time>
  <div class="usertext-body"><p>Stripped down stadium gig.</p></div>
</div>
</body></html>
""".strip()
    return {old: thread_html, branch: branch_html}


def build_r44e_side_effect_flags(*, browser_session_started: bool, network_actions_performed: bool) -> dict[str, bool]:
    return {
        "reddit_old_reddit_thread_expansion_invoked": True,
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


def write_report(report: R44EReport, output_root: str | Path) -> None:
    root = Path(output_root)
    _write_json(root / "R44E_REDDIT_OLD_REDDIT_THREAD_BRANCH_EXPANSION_REPORT.json", report.to_dict())
    _write_text(root / "R44E_REDDIT_OLD_REDDIT_THREAD_BRANCH_EXPANSION_REPORT.md", _report_md(report))


def coerce_reddit_old_thread_expansion_request_r44e(request: RedditOldThreadExpansionRequestR44E | Mapping[str, Any] | None = None, **overrides: Any) -> RedditOldThreadExpansionRequestR44E:
    if isinstance(request, RedditOldThreadExpansionRequestR44E):
        base = request.to_dict()
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
    return RedditOldThreadExpansionRequestR44E(
        thread_url=_plain_url(base.get("thread_url") or base.get("account_url") or R44E_EDSHEERAN_THREAD_URL),
        old_reddit_url=_plain_url(base.get("old_reddit_url") or ""),
        branch_urls=tuple(branch_urls),
        account_handle=_safe_handle(base.get("account_handle") or ""),
        capture_timestamp=_safe_ts(base.get("capture_timestamp") or ""),
        output_root=_clean(base.get("output_root") or R44E_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(base.get("fixture_mode"), False),
        real_visible_smoke=_to_bool(base.get("real_visible_smoke"), False),
        public_network_enabled=_to_bool(base.get("public_network_enabled"), False),
        explicit_live_mode=_to_bool(base.get("explicit_live_mode"), False),
        include_branch_urls=_to_bool(base.get("include_branch_urls"), True),
        prefer_old_reddit=_to_bool(base.get("prefer_old_reddit"), True),
        max_items=max(1, _safe_int(base.get("max_items"), 500)),
        timeout_seconds=max(5, _safe_int(base.get("timeout_seconds"), 45)),
        visible_dom_html_by_url=dict(base.get("visible_dom_html_by_url") or {}),
    )


def _capture_old_reddit_pages_visible_playwright(urls: Sequence[str], *, screenshot_dir: Path, timeout_seconds: int) -> list[dict[str, Any]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(f"Playwright is not installed or importable: {exc!r}") from exc

    pages: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        for index, url in enumerate(urls, start=1):
            response = page.goto(url, wait_until="domcontentloaded", timeout=max(5, int(timeout_seconds)) * 1000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            screenshot_path = screenshot_dir / f"page_{index:03d}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            pages.append({
                "url": url,
                "final_url": page.url,
                "status_code": response.status if response is not None else 0,
                "html": page.content(),
                "screenshot_path": str(screenshot_path),
                "capture_mode": "playwright_visible_chromium_old_reddit",
                "browser_session_started": True,
                "network_actions_performed": True,
            })
        context.close()
        browser.close()
    return pages


def _discover_continue_urls_from_pages(pages: Sequence[Mapping[str, Any]]) -> list[str]:
    urls: list[str] = []
    for page in pages:
        urls.extend(extract_continue_thread_urls_from_old_reddit_html_r44e(str(page.get("html") or "")))
    return urls


def _combine_visible_pages(pages: Sequence[Mapping[str, Any]]) -> str:
    parts = ["<html><body data-r44e-combined-old-reddit-pages='true'>"]
    for index, page in enumerate(pages, start=1):
        url = html_lib.escape(_plain_url(page.get("final_url") or page.get("url") or ""), quote=True)
        parts.append(f"<!-- R44E_PAGE_{index:03d}: {url} -->")
        parts.append(f"<section data-r44e-page-index='{index}' data-r44e-page-url='{url}'>")
        parts.append(str(page.get("html") or ""))
        parts.append("</section>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _first_screenshot_path(pages: Sequence[Mapping[str, Any]]) -> str:
    for page in pages:
        path = _clean(page.get("screenshot_path") or "")
        if path and Path(path).is_file():
            return path
    return ""


def _write_fixture_screenshot(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(_TINY_PNG_B64))
    return path


def _blocked_result(req: RedditOldThreadExpansionRequestR44E, root: Path, run_dir: Path, request_path: Path, receipt_path: Path, capture_plan_path: Path, combined_html_path: Path, thread_url: str, old_url: str, account_handle: str, capture_ts: str, planned_urls: Sequence[str], branch_urls: Sequence[str], discovered_count: int, warnings: Sequence[str], browser_started: bool, network_actions: bool) -> RedditOldThreadExpansionResultR44E:
    return RedditOldThreadExpansionResultR44E(
        marker=R44E_MARKER,
        schema_version=R44E_SCHEMA_VERSION,
        status=R44E_BLOCKED_STATUS,
        thread_url=thread_url,
        old_reddit_url=old_url,
        account_handle=account_handle,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        capture_plan_path=str(capture_plan_path),
        combined_visible_dom_html_path=str(combined_html_path),
        planned_url_count=len(planned_urls),
        branch_url_count=len(branch_urls),
        discovered_continue_url_count=discovered_count,
        browser_session_started=browser_started,
        network_actions_performed=network_actions,
        side_effect_flags=build_r44e_side_effect_flags(browser_session_started=browser_started, network_actions_performed=network_actions),
        warnings=tuple(warnings),
    )


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="R44E old/en Reddit thread branch expansion")
    parser.add_argument("--thread-url", default=R44E_EDSHEERAN_THREAD_URL)
    parser.add_argument("--old-reddit-url", default=R44E_EDSHEERAN_OLD_REDDIT_URL)
    parser.add_argument("--branch-url", action="append", default=[])
    parser.add_argument("--branch-url-file", default="")
    parser.add_argument("--account-handle", default="")
    parser.add_argument("--output-root", default=R44E_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--max-items", type=int, default=500)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--real-visible-smoke", action="store_true")
    parser.add_argument("--public-network-enabled", action="store_true")
    parser.add_argument("--explicit-live-mode", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.report:
        report = build_report(args.output_root)
        print(R44E_MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.passed else 1
    branch_urls = list(args.branch_url or [])
    if args.branch_url_file:
        branch_urls.extend(Path(args.branch_url_file).read_text(encoding="utf-8", errors="replace").splitlines())
    if not branch_urls:
        branch_urls = list(R44E_EDSHEERAN_BRANCH_URLS)
    result = run_reddit_old_reddit_thread_expansion_r44e(
        RedditOldThreadExpansionRequestR44E(
            thread_url=args.thread_url,
            old_reddit_url=args.old_reddit_url,
            branch_urls=tuple(branch_urls),
            account_handle=args.account_handle,
            capture_timestamp=args.capture_timestamp,
            output_root=args.output_root,
            fixture_mode=args.fixture_mode or not args.real_visible_smoke,
            real_visible_smoke=args.real_visible_smoke,
            public_network_enabled=args.public_network_enabled,
            explicit_live_mode=args.explicit_live_mode,
            max_items=args.max_items,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(R44E_MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.passed else 1


def _report_md(report: R44EReport) -> str:
    lines = [
        "# R44E Reddit Old Reddit Thread Branch Expansion",
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
        f"- Old Reddit URL: `{sample.get('old_reddit_url')}`",
        f"- Branch URLs: `{sample.get('branch_url_count')}`",
        f"- Records: `{sample.get('record_count')}`",
        f"- Media: `{sample.get('media_count')}`",
        f"- Screenshots: `{sample.get('screenshot_count')}`",
        "",
    ])
    return "\n".join(lines)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail if not ok else ""}


def _machine_urls_are_plain(payload: Any) -> bool:
    blob = json.dumps(_to_jsonable(payload), sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def _plain_url(value: Any) -> str:
    text = _clean(value)
    match = re.fullmatch(r"\[[^\]]+\]\((https?://[^\s)]+)\)", text)
    if match:
        return match.group(1)
    return text.replace("\\_", "_").replace("\\:", ":")


def _normalize_reddit_url(url: str) -> str:
    text = _plain_url(url)
    if text.startswith("/"):
        return "https://www.reddit.com" + text
    return text


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_ts(value: Any) -> str:
    text = _clean(value).replace(":", "").replace("-", "")
    return re.sub(r"[^0-9TZ]", "", text)


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_handle(value: Any) -> str:
    text = _clean(value).replace("u/", "").strip("/")
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._-")
    return text or "unknown_reddit_thread"


def _subreddit_handle_from_url(url: str) -> str:
    match = re.search(r"reddit\.com/r/([^/?#]+)", _plain_url(url), re.I)
    return _safe_handle("r_" + match.group(1)) if match else ""


if __name__ == "__main__":
    raise SystemExit(_run_cli())
