from __future__ import annotations

import argparse
import base64
import json
import re
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

from profile_media_bluesky_visible_dom_capture_r43z import (
    R43Z_PASS_STATUS,
    BlueskyVisibleDomCaptureRequestR43Z,
    build_bluesky_visible_dom_capture_r43z,
    build_fake_bluesky_visible_dom_html_r43z,
)
from profile_media_bluesky_visible_account_adapter_r43v import R43V_PASS_STATUS, parse_bluesky_app_url_r43v
from profile_media_universal_social_account_ledger_contract_r43u import R43U_PASS_STATUS

R44A_MARKER = "YTCE_R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE"
R44A_PASS_STATUS = "PASS_R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE"
R44A_BLOCKED_STATUS = "BLOCKED_R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE"
R44A_SCHEMA_VERSION = "bluesky_visible_live_workbench_capture.r44a.v1"
R44A_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44a_bluesky_visible_live_workbench_capture"
R44A_MODE_ID = "bluesky_visible_live_workbench_capture"

_TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="

VisibleBrowserRunnerR44A = Callable[["BlueskyVisibleLiveWorkbenchCaptureRequestR44A"], Mapping[str, Any]]


@dataclass(frozen=True)
class BlueskyVisibleLiveWorkbenchCaptureRequestR44A:
    account_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R44A_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    public_network_enabled: bool = False
    allow_external_visible_browser_capture: bool = False
    visible_dom_html: str = ""
    visible_dom_html_path: str = ""
    static_screenshot_path: str = ""
    observed_media: tuple[Mapping[str, Any], ...] = ()
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    max_items: int = 5
    max_scrolls: int = 2
    timeout_seconds: int = 30
    viewport_width: int = 1280
    viewport_height: int = 900
    screenshot_full_page: bool = True
    headless: bool = False
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""
    feed_mode: str = "posts_and_reposts"
    include_reposts: bool = True
    include_replies: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class BlueskyVisibleLiveWorkbenchCaptureResultR44A:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    request_path: str
    receipt_path: str
    browser_snapshot_path: str = ""
    visible_dom_html_path: str = ""
    visible_screenshot_path: str = ""
    r43z_status: str = ""
    r43z_receipt_path: str = ""
    r43z_run_dir: str = ""
    adapter_status: str = ""
    ledger_status: str = ""
    account_capture_dir: str = ""
    account_record_path: str = ""
    manifest_path: str = ""
    account_timeline_path: str = ""
    media_index_path: str = ""
    progress_events_path: str = ""
    review_strings_path: str = ""
    screenshot_receipts_index_path: str = ""
    visible_record_count: int = 0
    dom_article_count: int = 0
    media_candidate_count: int = 0
    bound_media_count: int = 0
    unbound_media_count: int = 0
    record_count: int = 0
    media_count: int = 0
    screenshot_count: int = 0
    post_folder_count: int = 0
    date_folders: tuple[str, ...] = ()
    browser_engine: str = ""
    browser_snapshot_status: str = ""
    browser_final_url: str = ""
    browser_status_code: int = 0
    injected_browser_runner_used: bool = False
    browser_session_started: bool = False
    network_actions_performed: bool = False
    feed_mode: str = ""
    navigation_url: str = ""
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R44A_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R44AReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    workbench_route_result: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R44A_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class BlueskyVisibleLiveWorkbenchCaptureR44A:
    """Visible live Bluesky capture handoff for the universal workbench route.

    R44A is the live-browser caller above R43Z. It can accept caller-supplied DOM
    and screenshots, or, when explicitly requested, launch a clean visible browser
    session to a public bsky.app profile and hand the resulting page HTML and
    screenshot to R43Z. It never reads/copies browser profiles, cookies, tokens,
    cache, local storage, login databases, or remote media bytes.
    """

    def __init__(self, output_root: str | Path = R44A_DEFAULT_OUTPUT_ROOT, *, browser_runner: VisibleBrowserRunnerR44A | None = None) -> None:
        self.output_root = Path(output_root)
        self.browser_runner = browser_runner

    def run_account_export(
        self,
        request: BlueskyVisibleLiveWorkbenchCaptureRequestR44A | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> BlueskyVisibleLiveWorkbenchCaptureResultR44A:
        req = coerce_bluesky_visible_live_workbench_capture_request_r44a(request, **overrides)
        return run_bluesky_visible_live_workbench_capture_r44a(req, output_root=self.output_root, browser_runner=self.browser_runner)


def build_bluesky_visible_live_workbench_capture_r44a(
    output_root: str | Path = R44A_DEFAULT_OUTPUT_ROOT,
    *,
    browser_runner: VisibleBrowserRunnerR44A | None = None,
) -> BlueskyVisibleLiveWorkbenchCaptureR44A:
    return BlueskyVisibleLiveWorkbenchCaptureR44A(output_root=output_root, browser_runner=browser_runner)


def build_bluesky_visible_live_workbench_capture_contract_r44a() -> dict[str, Any]:
    return {
        "marker": R44A_MARKER,
        "schema_version": R44A_SCHEMA_VERSION,
        "mode_id": R44A_MODE_ID,
        "route_role": "visible browser/workbench live capture caller above R43Z",
        "downstream_visible_dom_lane": "profile_media_bluesky_visible_dom_capture_r43z",
        "downstream_adapter": "profile_media_bluesky_visible_account_adapter_r43v",
        "downstream_ledger": "profile_media_universal_social_account_ledger_contract_r43u",
        "timeline_modes_r44c": {
            "posts_and_reposts": "navigate to the profile Posts/Reposts timeline and preserve text/media/repost evidence where visible",
            "posts_and_replies": "navigate to the profile Replies timeline and preserve text/media/reply evidence where visible",
        },
        "visible_capture_strategy": [
            "require operator live flags before launching an external visible browser session",
            "capture only rendered page HTML and caller/browser screenshot receipts",
            "hand DOM HTML and screenshot bytes to R43Z for post/media/screenshot receipt materialization",
            "let R43Z delegate normalized records to R43V and R43U",
            "record a blocker rather than reading a browser profile or bypassing a challenge",
        ],
        "accepted_inputs": [
            "caller-supplied visible_dom_html or visible_dom_html_path",
            "caller-supplied static_screenshot_path",
            "injected visible browser runner for tests and app-shell probes",
            "explicit clean public bsky.app browser capture when run_visible_live and explicit_live_mode are both true",
        ],
        "browser_user_data_dir_policy": "accepted for compatibility but not read, copied, or used by R44A",
        "browser_executable_path_policy": "optional browser executable hint only; no profile state is read or copied",
        "bluesky_timeline_mode_aliases": ["posts_and_reposts", "posts_and_retweets", "posts_and_replies", "posts_replies"],
        "browser_profile_files_read_or_copied": False,
        "webview2_internals_copied": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed_by_r44a": False,
    }


def run_bluesky_visible_live_workbench_capture_r44a(
    request: BlueskyVisibleLiveWorkbenchCaptureRequestR44A | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R44A_DEFAULT_OUTPUT_ROOT,
    browser_runner: VisibleBrowserRunnerR44A | None = None,
) -> BlueskyVisibleLiveWorkbenchCaptureResultR44A:
    req = coerce_bluesky_visible_live_workbench_capture_request_r44a(request)
    root = Path(req.output_root or output_root or R44A_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    account_url = _plain_url(req.account_url)
    parsed = parse_bluesky_app_url_r43v(account_url)
    handle = _safe_handle(req.account_handle or parsed.get("handle") or "bsky.app")
    if not account_url:
        account_url = f"https://bsky.app/profile/{handle}"
    feed_mode = normalize_bluesky_live_feed_mode_r44c(req.feed_mode, include_reposts=req.include_reposts, include_replies=req.include_replies)
    navigation_url = build_bluesky_visible_navigation_url_r44c(account_url, handle, feed_mode)
    run_dir = root / handle / f"bluesky_visible_live_workbench_capture_{capture_ts}"
    evidence_dir = run_dir / "visible_browser_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "r44a_bluesky_visible_live_workbench_capture_request.json"
    receipt_path = run_dir / "r44a_bluesky_visible_live_workbench_capture_receipt.json"
    browser_snapshot_path = evidence_dir / "visible_browser_snapshot.json"
    html_path = evidence_dir / "visible_dom.html"
    screenshot_path = evidence_dir / "visible_browser_screenshot.png"
    _write_json(request_path, req.to_dict())

    warnings: list[str] = []
    html_text = _load_text(req.visible_dom_html_path) or req.visible_dom_html
    injected_runner_used = browser_runner is not None
    browser_session_started = False
    network_actions = False
    snapshot: dict[str, Any] = {}

    if req.fixture_mode and not html_text:
        html_text = build_fake_bluesky_visible_dom_html_r43z(handle)
        screenshot_path.write_bytes(base64.b64decode(_TINY_PNG_B64))
        snapshot = {
            "status": "fixture_visible_dom",
            "engine": "r44a_fixture",
            "final_url": account_url,
            "status_code": 0,
            "html_length": len(html_text),
            "screenshot_bytes": screenshot_path.stat().st_size,
            "injected_browser_runner_used": False,
            "browser_session_started": False,
            "network_actions_performed": False,
        }
    elif not html_text:
        live_gate = bool(req.explicit_live_mode and (req.run_visible_live or req.live_mode))
        if not live_gate:
            warnings.append("R44A requires visible DOM evidence or explicit live visible-browser flags.")
            result = _blocked_result(req, root, run_dir, request_path, receipt_path, handle, account_url, capture_ts, warnings, browser_snapshot_path=str(browser_snapshot_path))
            _write_json(receipt_path, result.to_dict())
            return result
        if not _is_allowed_bluesky_url(account_url):
            warnings.append("R44A visible live browser capture is restricted to bsky.app profile/post URLs.")
            result = _blocked_result(req, root, run_dir, request_path, receipt_path, handle, account_url, capture_ts, warnings, browser_snapshot_path=str(browser_snapshot_path))
            _write_json(receipt_path, result.to_dict())
            return result
        if browser_runner is None and not req.allow_external_visible_browser_capture:
            warnings.append("R44A external browser capture requires allow_external_visible_browser_capture when no injected runner/DOM is supplied.")
            result = _blocked_result(req, root, run_dir, request_path, receipt_path, handle, account_url, capture_ts, warnings, browser_snapshot_path=str(browser_snapshot_path))
            _write_json(receipt_path, result.to_dict())
            return result
        snapshot = _coerce_snapshot((browser_runner or capture_visible_browser_snapshot_r44a)(req))
        injected_runner_used = bool(snapshot.get("injected_browser_runner_used") or browser_runner is not None)
        browser_session_started = bool(snapshot.get("browser_session_started", not injected_runner_used))
        network_actions = bool(snapshot.get("network_actions_performed", browser_session_started))
        html_text = _clean(snapshot.get("html"))
        screenshot_bytes = snapshot.get("screenshot_png") or b""
        if isinstance(screenshot_bytes, str):
            screenshot_bytes = base64.b64decode(screenshot_bytes) if screenshot_bytes else b""
        if screenshot_bytes:
            screenshot_path.write_bytes(bytes(screenshot_bytes))
        if not html_text:
            warnings.append("R44A visible browser snapshot did not return rendered HTML.")
            _write_json(browser_snapshot_path, _redacted_snapshot(snapshot))
            result = _blocked_result(req, root, run_dir, request_path, receipt_path, handle, account_url, capture_ts, warnings, browser_snapshot_path=str(browser_snapshot_path), browser_session_started=browser_session_started, network_actions_performed=network_actions, injected_browser_runner_used=injected_runner_used)
            _write_json(receipt_path, result.to_dict())
            return result
    elif req.static_screenshot_path and Path(req.static_screenshot_path).is_file():
        _copy_bytes(Path(req.static_screenshot_path), screenshot_path)
        snapshot = {
            "status": "caller_supplied_visible_dom_and_screenshot",
            "engine": "caller_supplied_evidence",
            "final_url": account_url,
            "status_code": 0,
            "html_length": len(html_text),
            "screenshot_bytes": screenshot_path.stat().st_size if screenshot_path.is_file() else 0,
            "injected_browser_runner_used": False,
            "browser_session_started": False,
            "network_actions_performed": False,
        }
    else:
        snapshot = {
            "status": "caller_supplied_visible_dom_without_screenshot",
            "engine": "caller_supplied_evidence",
            "final_url": account_url,
            "status_code": 0,
            "html_length": len(html_text),
            "screenshot_bytes": 0,
            "injected_browser_runner_used": False,
            "browser_session_started": False,
            "network_actions_performed": False,
        }

    html_path.write_text(html_text, encoding="utf-8")
    _write_json(browser_snapshot_path, _redacted_snapshot(snapshot))

    r43z = build_bluesky_visible_dom_capture_r43z(output_root=run_dir / "r43z_visible_dom")
    r43z_result = r43z.run_account_export(
        BlueskyVisibleDomCaptureRequestR43Z(
            account_url=account_url,
            account_handle=handle,
            capture_timestamp=capture_ts,
            output_root=str(run_dir / "r43z_visible_dom"),
            fixture_mode=False,
            explicit_live_mode=req.explicit_live_mode,
            run_visible_live=req.run_visible_live,
            live_mode=req.live_mode,
            visible_dom_html_path=str(html_path),
            static_screenshot_path=str(screenshot_path) if screenshot_path.is_file() else "",
            observed_media=req.observed_media,
            include_media=req.include_media,
            include_static_screenshots=req.include_static_screenshots,
            require_screenshot_receipts=req.require_screenshot_receipts,
            max_items=req.max_items,
            max_scrolls=req.max_scrolls,
        )
    )
    r43z_payload = r43z_result.to_dict()
    flags = build_r44a_side_effect_flags(
        injected_browser_runner_used=injected_runner_used,
        browser_session_started=browser_session_started,
        network_actions_performed=network_actions,
    )
    status = R44A_PASS_STATUS if r43z_result.status == R43Z_PASS_STATUS and r43z_result.adapter_status == R43V_PASS_STATUS and r43z_result.ledger_status == R43U_PASS_STATUS and r43z_result.record_count > 0 else R44A_BLOCKED_STATUS
    if r43z_result.status != R43Z_PASS_STATUS:
        warnings.append(f"R43Z downstream visible DOM lane returned {r43z_result.status}.")

    result = BlueskyVisibleLiveWorkbenchCaptureResultR44A(
        marker=R44A_MARKER,
        schema_version=R44A_SCHEMA_VERSION,
        status=status,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        browser_snapshot_path=str(browser_snapshot_path),
        visible_dom_html_path=str(html_path),
        visible_screenshot_path=str(screenshot_path) if screenshot_path.is_file() else "",
        r43z_status=r43z_result.status,
        r43z_receipt_path=r43z_result.receipt_path,
        r43z_run_dir=r43z_result.run_dir,
        adapter_status=r43z_result.adapter_status,
        ledger_status=r43z_result.ledger_status,
        account_capture_dir=r43z_result.account_capture_dir,
        account_record_path=r43z_result.account_record_path,
        manifest_path=r43z_result.manifest_path,
        account_timeline_path=r43z_result.account_timeline_path,
        media_index_path=r43z_result.media_index_path,
        progress_events_path=r43z_result.progress_events_path,
        review_strings_path=r43z_result.review_strings_path,
        screenshot_receipts_index_path=r43z_result.visible_screenshot_receipts_path,
        visible_record_count=r43z_result.visible_record_count,
        dom_article_count=r43z_result.dom_article_count,
        media_candidate_count=r43z_result.media_candidate_count,
        bound_media_count=r43z_result.bound_media_count,
        unbound_media_count=r43z_result.unbound_media_count,
        record_count=r43z_result.record_count,
        media_count=r43z_result.media_count,
        screenshot_count=r43z_result.screenshot_count,
        post_folder_count=r43z_result.post_folder_count,
        date_folders=r43z_result.date_folders,
        browser_engine=_clean(snapshot.get("engine")),
        browser_snapshot_status=_clean(snapshot.get("status")),
        browser_final_url=_plain_url(snapshot.get("final_url") or navigation_url),
        browser_status_code=_safe_int(snapshot.get("status_code"), 0),
        feed_mode=feed_mode,
        navigation_url=navigation_url,
        injected_browser_runner_used=injected_runner_used,
        browser_session_started=browser_session_started,
        network_actions_performed=network_actions,
        side_effect_flags=flags,
        warnings=tuple(warnings),
    )
    _write_json(receipt_path, result.to_dict())
    return result




def normalize_bluesky_live_feed_mode_r44c(value: Any = "", *, include_reposts: bool = True, include_replies: bool = False) -> str:
    raw = _clean(value).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "posts_reposts": "posts_and_reposts",
        "posts_and_retweets": "posts_and_reposts",
        "posts_retweets": "posts_and_reposts",
        "with_reposts": "posts_and_reposts",
        "profile_posts": "posts_and_reposts",
        "posts_replies": "posts_and_replies",
        "posts_and_replies": "posts_and_replies",
        "with_replies": "posts_and_replies",
        "replies": "posts_and_replies",
        "posts_only": "posts_only",
    }
    if raw in aliases:
        return aliases[raw]
    if include_replies:
        return "posts_and_replies"
    if include_reposts:
        return "posts_and_reposts"
    return "posts_only"


def build_bluesky_visible_navigation_url_r44c(account_url: str, account_handle: str, feed_mode: str = "posts_and_reposts") -> str:
    url = _plain_url(account_url)
    handle = _safe_handle(account_handle or parse_bluesky_app_url_r43v(url).get("handle") or "bsky.app")
    if "/post/" in url:
        return url
    mode = normalize_bluesky_live_feed_mode_r44c(feed_mode)
    if mode == "posts_and_replies":
        return f"https://bsky.app/profile/{handle}/replies"
    return f"https://bsky.app/profile/{handle}"

def capture_visible_browser_snapshot_r44a(req: BlueskyVisibleLiveWorkbenchCaptureRequestR44A) -> Mapping[str, Any]:
    """Launch a clean Playwright browser and return rendered HTML/screenshot.

    This deliberately does not pass storage_state, user_data_dir, cookies, tokens,
    local storage, cached profile paths, or download handlers. A missing Playwright
    install returns a safe blocker payload. R44B adds a rendered-post readiness wait
    so real Bluesky pages have time to expose post links before R43Z parses HTML.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {
            "status": "dependency_missing_playwright",
            "engine": "playwright_visible_chromium",
            "html": "",
            "screenshot_png": b"",
            "final_url": req.account_url,
            "status_code": 0,
            "browser_session_started": False,
            "network_actions_performed": False,
            "render_wait_status": "not_started_dependency_missing_playwright",
            "post_link_count": 0,
            "media_url_count": 0,
            "warnings": [f"Playwright is not installed or importable: {type(exc).__name__}"],
        }

    browser = None
    try:
        with sync_playwright() as playwright:
            launch_kwargs: dict[str, Any] = {"headless": bool(req.headless)}
            if req.browser_executable_path:
                launch_kwargs["executable_path"] = req.browser_executable_path
            browser = playwright.chromium.launch(**launch_kwargs)
            context = browser.new_context(viewport={"width": req.viewport_width, "height": req.viewport_height})
            page = context.new_page()
            response = page.goto(req.account_url, wait_until="domcontentloaded", timeout=max(1, req.timeout_seconds) * 1000)
            render_wait_status = _wait_for_bluesky_rendered_post_links_r44a(page, req)
            page.wait_for_timeout(1200)
            for _ in range(max(0, req.max_scrolls)):
                page.evaluate("() => window.scrollBy(0, Math.max(600, window.innerHeight || 800))")
                page.wait_for_timeout(900)
            html_text = page.content()
            post_link_count = len(re.findall(r"/profile/[^\s\"'<>?#)]+/post/[^\s\"'<>?#)]+", html_text or "", re.I))
            media_url_count = len(re.findall(r"https?://(?:cdn|video)\.bsky\.app/[^\s\"'<>]+", html_text or "", re.I))
            if post_link_count <= 0:
                retry_status = _wait_for_bluesky_rendered_post_links_r44a(page, req, retry=True)
                page.wait_for_timeout(800)
                html_text = page.content()
                post_link_count = len(re.findall(r"/profile/[^\s\"'<>?#)]+/post/[^\s\"'<>?#)]+", html_text or "", re.I))
                media_url_count = len(re.findall(r"https?://(?:cdn|video)\.bsky\.app/[^\s\"'<>]+", html_text or "", re.I))
                render_wait_status = f"{render_wait_status};retry={retry_status}"
            screenshot = page.screenshot(full_page=req.screenshot_full_page)
            final_url = page.url
            status_code = int(response.status if response is not None else 0)
            context.close()
            return {
                "status": "visible_browser_snapshot_captured",
                "engine": "playwright_visible_chromium",
                "html": html_text,
                "screenshot_png": bytes(screenshot or b""),
                "final_url": final_url,
                "status_code": status_code,
                "browser_session_started": True,
                "network_actions_performed": True,
                "render_wait_status": render_wait_status,
                "post_link_count": post_link_count,
                "media_url_count": media_url_count,
                "html_length": len(html_text or ""),
                "warnings": [],
            }
    except Exception as exc:
        return {
            "status": "visible_browser_snapshot_failed",
            "engine": "playwright_visible_chromium",
            "html": "",
            "screenshot_png": b"",
            "final_url": req.account_url,
            "status_code": 0,
            "browser_session_started": False,
            "network_actions_performed": False,
            "render_wait_status": "failed_before_rendered_post_wait_completed",
            "post_link_count": 0,
            "media_url_count": 0,
            "warnings": [f"Visible browser capture failed safely: {type(exc).__name__}"],
        }
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass


def _wait_for_bluesky_rendered_post_links_r44a(page: Any, req: BlueskyVisibleLiveWorkbenchCaptureRequestR44A, *, retry: bool = False) -> str:
    selectors = (
        "a[href*='/post/']",
        "[data-testid^='feedItem-by-']",
        "[data-testid='postText']",
        "article",
    )
    per_selector_timeout = max(500, min(4500, max(1, req.timeout_seconds) * 250))
    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=per_selector_timeout)
            return f"selector:{selector}"
        except Exception:
            pass
    deadline = time.time() + max(2, min(12 if not retry else 8, req.timeout_seconds))
    while time.time() < deadline:
        try:
            html_text = page.content() or ""
            if re.search(r"/profile/[^\s\"'<>?#)]+/post/[^\s\"'<>?#)]+", html_text, re.I):
                return "html_post_link_detected"
            page.wait_for_timeout(500)
        except Exception:
            break
    return "no_rendered_post_link_detected"


def fake_visible_browser_snapshot_r44a(req: BlueskyVisibleLiveWorkbenchCaptureRequestR44A | Mapping[str, Any]) -> Mapping[str, Any]:
    request = coerce_bluesky_visible_live_workbench_capture_request_r44a(req)
    handle = _safe_handle(request.account_handle or parse_bluesky_app_url_r43v(request.account_url).get("handle") or "bsky.app")
    return {
        "status": "injected_visible_browser_snapshot_captured",
        "engine": "injected_r44a_visible_browser_runner",
        "html": build_fake_bluesky_visible_dom_html_r43z(handle),
        "screenshot_png": base64.b64decode(_TINY_PNG_B64),
        "final_url": request.account_url or f"https://bsky.app/profile/{handle}",
        "status_code": 200,
        "browser_session_started": False,
        "network_actions_performed": False,
        "injected_browser_runner_used": True,
        "warnings": [],
    }


def build_r44a_side_effect_flags(*, injected_browser_runner_used: bool = False, browser_session_started: bool = False, network_actions_performed: bool = False) -> dict[str, bool]:
    return {
        "bluesky_visible_live_workbench_capture_invoked": True,
        "r43z_visible_dom_capture_used": True,
        "r43v_bluesky_adapter_used": True,
        "r43u_universal_ledger_writer_used": True,
        "injected_browser_runner_used": bool(injected_browser_runner_used),
        "browser_session_started": bool(browser_session_started),
        "network_actions_performed": bool(network_actions_performed),
        "external_visible_browser_capture_requires_explicit_live_flags": True,
        "browser_profile_files_read_or_copied": False,
        "webview2_internals_copied": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
    }


def build_report(output_root: str | Path = R44A_DEFAULT_OUTPUT_ROOT) -> R44AReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    sample = build_bluesky_visible_live_workbench_capture_r44a(root / "sample", browser_runner=fake_visible_browser_snapshot_r44a).run_account_export(
        BlueskyVisibleLiveWorkbenchCaptureRequestR44A(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T090000Z",
            output_root=str(root / "sample"),
            explicit_live_mode=True,
            run_visible_live=True,
            max_items=5,
        )
    )
    blocked = build_bluesky_visible_live_workbench_capture_r44a(root / "blocked").run_account_export(
        BlueskyVisibleLiveWorkbenchCaptureRequestR44A(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T090100Z",
            output_root=str(root / "blocked"),
            explicit_live_mode=True,
            run_visible_live=True,
            max_items=2,
        )
    )
    workbench = _run_workbench_route_probe_r44a(root / "workbench_probe")
    payload = sample.to_dict()
    contract = build_bluesky_visible_live_workbench_capture_contract_r44a()
    flags = sample.side_effect_flags
    workbench_downstream = (((workbench.get("live_evidence_summary") or {}).get("bluesky_visible_live_summary") or {}) if isinstance(workbench, Mapping) else {})
    checks = (
        _check("injected_visible_browser_capture_feeds_r43z", sample.status == R44A_PASS_STATUS and sample.injected_browser_runner_used is True),
        _check("visible_dom_post_cards_and_media_bound", sample.visible_record_count == 2 and sample.bound_media_count >= 3 and sample.unbound_media_count >= 1),
        _check("screenshot_receipts_materialized", sample.screenshot_count >= 2 and Path(sample.visible_screenshot_path).is_file()),
        _check("r43z_r43v_r43u_chain_passes", sample.r43z_status == R43Z_PASS_STATUS and sample.adapter_status == R43V_PASS_STATUS and sample.ledger_status == R43U_PASS_STATUS),
        _check("external_browser_gate_blocks_without_allow_flag_or_injected_runner", blocked.status == R44A_BLOCKED_STATUS and blocked.network_actions_performed is False and blocked.browser_session_started is False),
        _check("universal_workbench_route_reaches_r44a_without_real_network_in_validation", workbench_downstream.get("r44a_status") == R44A_PASS_STATUS and workbench_downstream.get("injected_browser_runner_used") is True),
        _check("metadata_only_media_no_remote_downloads", _media_index_metadata_only(sample.media_index_path)),
        _check("no_browser_cookie_token_profile_or_media_download_side_effects", not any(flags.get(k) for k in ("browser_profile_files_read_or_copied", "webview2_internals_copied", "cookie_or_token_extraction_performed", "login_automation_performed", "captcha_or_challenge_bypass_performed", "hidden_platform_api_scraping_performed", "remote_media_downloads_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(payload) and _machine_urls_are_plain(contract) and _machine_urls_are_plain(workbench)),
    )
    status = R44A_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R44A_BLOCKED_STATUS
    report = R44AReport(R44A_MARKER, R44A_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), status, checks, payload, workbench, contract, flags)
    write_report(report, root)
    return report


def write_report(report: R44AReport, output_root: str | Path = R44A_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE_REPORT.json"
    md_path = root / "R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE_REPORT.md"
    _write_json(json_path, report.to_dict())
    md_path.write_text(
        "\n".join([
            f"# {R44A_MARKER}",
            "",
            f"- Status: `{report.status}`",
            f"- Schema: `{report.schema_version}`",
            f"- Generated: `{report.generated_at}`",
            "",
            "## Checks",
            *[f"- `{c.get('status')}` {c.get('name')}: {c.get('detail') or ''}".rstrip() for c in report.checks],
        ]).rstrip() + "\n",
        encoding="utf-8",
    )
    return json_path, md_path


def coerce_bluesky_visible_live_workbench_capture_request_r44a(
    request: BlueskyVisibleLiveWorkbenchCaptureRequestR44A | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> BlueskyVisibleLiveWorkbenchCaptureRequestR44A:
    if isinstance(request, BlueskyVisibleLiveWorkbenchCaptureRequestR44A):
        data = request.to_dict()
    elif hasattr(request, "to_dict"):
        data = dict(request.to_dict())
    elif isinstance(request, Mapping):
        data = dict(request)
    else:
        data = dict(request or {})
    for key, value in overrides.items():
        if value not in (None, ""):
            data[key] = value
    return BlueskyVisibleLiveWorkbenchCaptureRequestR44A(
        account_url=_plain_url(data.get("account_url") or ""),
        account_handle=_safe_handle(data.get("account_handle") or ""),
        capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""),
        output_root=str(data.get("output_root") or R44A_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(data.get("run_visible_live"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        public_network_enabled=_to_bool(data.get("public_network_enabled"), False),
        allow_external_visible_browser_capture=_to_bool(data.get("allow_external_visible_browser_capture"), False),
        visible_dom_html=str(data.get("visible_dom_html") or ""),
        visible_dom_html_path=str(data.get("visible_dom_html_path") or data.get("html_path") or ""),
        static_screenshot_path=str(data.get("static_screenshot_path") or data.get("screenshot_path") or ""),
        observed_media=tuple(item for item in (data.get("observed_media") or ()) if isinstance(item, Mapping)),
        include_media=_to_bool(data.get("include_media"), True),
        include_static_screenshots=_to_bool(data.get("include_static_screenshots"), True),
        require_screenshot_receipts=_to_bool(data.get("require_screenshot_receipts"), True),
        max_items=_safe_int(data.get("max_items"), 5),
        max_scrolls=_safe_int(data.get("max_scrolls"), 2),
        timeout_seconds=_safe_int(data.get("timeout_seconds"), 30),
        viewport_width=_safe_int(data.get("viewport_width"), 1280),
        viewport_height=_safe_int(data.get("viewport_height"), 900),
        screenshot_full_page=_to_bool(data.get("screenshot_full_page"), True),
        headless=_to_bool(data.get("headless"), False),
        browser_user_data_dir=_clean(data.get("browser_user_data_dir")),
        browser_executable_path=_clean(data.get("browser_executable_path")),
        feed_mode=normalize_bluesky_live_feed_mode_r44c(data.get("feed_mode") or data.get("timeline_mode") or "", include_reposts=_to_bool(data.get("include_reposts"), True), include_replies=_to_bool(data.get("include_replies"), False)),
        include_reposts=_to_bool(data.get("include_reposts"), True),
        include_replies=_to_bool(data.get("include_replies"), False),
    )


def _run_workbench_route_probe_r44a(root: Path) -> Mapping[str, Any]:
    import profile_media_bluesky_visible_live_workbench_capture_r44a as self_module
    from profile_media_universal_social_batch_workbench_app_shell_commands_r43l import (
        build_universal_social_batch_workbench_app_shell_commands_r43l,
    )
    old_runner = self_module.capture_visible_browser_snapshot_r44a
    self_module.capture_visible_browser_snapshot_r44a = fake_visible_browser_snapshot_r44a
    try:
        shell = build_universal_social_batch_workbench_app_shell_commands_r43l(output_root=root / "shell")
        result = shell.run_app_shell_command(
            {
                "command_name": "run_pending",
                "inputs": ("https://bsky.app/profile/example.bsky.social",),
                "capture_timestamp": "20260918T090200Z",
                "output_root": str(root / "app_shell"),
                "explicit_live_mode": True,
                "run_visible_live": True,
                "public_network_enabled": False,
                "fixture_mode": False,
                "max_items": 5,
                "max_scrolls": 2,
            }
        )
        return result.to_dict()
    finally:
        self_module.capture_visible_browser_snapshot_r44a = old_runner


def _blocked_result(req: BlueskyVisibleLiveWorkbenchCaptureRequestR44A, root: Path, run_dir: Path, request_path: Path, receipt_path: Path, handle: str, account_url: str, capture_ts: str, warnings: Sequence[str], *, browser_snapshot_path: str = "", browser_session_started: bool = False, network_actions_performed: bool = False, injected_browser_runner_used: bool = False) -> BlueskyVisibleLiveWorkbenchCaptureResultR44A:
    flags = build_r44a_side_effect_flags(injected_browser_runner_used=injected_browser_runner_used, browser_session_started=browser_session_started, network_actions_performed=network_actions_performed)
    return BlueskyVisibleLiveWorkbenchCaptureResultR44A(
        marker=R44A_MARKER,
        schema_version=R44A_SCHEMA_VERSION,
        status=R44A_BLOCKED_STATUS,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        browser_snapshot_path=browser_snapshot_path,
        injected_browser_runner_used=injected_browser_runner_used,
        browser_session_started=browser_session_started,
        network_actions_performed=network_actions_performed,
        side_effect_flags=flags,
        warnings=tuple(warnings),
    )


def _media_index_metadata_only(path: str) -> bool:
    rows = _read_json(path, [])
    if not isinstance(rows, list) or not rows:
        return False
    return all(bool(row.get("metadata_only_remote_media_not_downloaded")) and row.get("remote_download_performed_by_r43u") is False for row in rows if isinstance(row, Mapping))


def _coerce_snapshot(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return {}


def _redacted_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    payload = {k: v for k, v in dict(snapshot).items() if k not in {"html", "screenshot_png"}}
    payload["html_length"] = len(_clean(snapshot.get("html")))
    raw = snapshot.get("screenshot_png") or b""
    payload["screenshot_bytes"] = len(raw) if isinstance(raw, (bytes, bytearray)) else len(_clean(raw))
    payload["redaction_note"] = "HTML is saved separately as visible_dom.html; screenshot bytes are saved separately as visible_browser_screenshot.png."
    return _to_jsonable(payload)


def _is_allowed_bluesky_url(url: str) -> bool:
    parsed = urlsplit(_plain_url(url))
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host in {"bsky.app", "www.bsky.app", "staging.bsky.app"} and parsed.path.startswith("/profile/")


def _load_text(path: str) -> str:
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _copy_bytes(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())


def _safe_handle(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", _clean(value).strip().lstrip("@")).strip("._-") or "unknown_account"


def _safe_ts(value: Any) -> str:
    return re.sub(r"[^0-9TZ]", "", _clean(value).replace(":", "").replace("-", ""))


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _plain_url(value: Any) -> str:
    text = _clean(value).strip("<>").replace("\\_", "_").replace("\\/", "/")
    md = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", text)
    return md.group(1).replace("\\&", "&") if md else text


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return {"bytes": len(value), "encoding": "redacted"}
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    return value


def _write_json(path: str | Path, value: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _check(name: str, ok: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": "" if ok else detail}


def _machine_urls_are_plain(value: Any) -> bool:
    text = json.dumps(_to_jsonable(value), ensure_ascii=False)
    return not bool(re.search(r"\[[^\]]*https?://[^\]]+\]\(https?://", text))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R44A Bluesky visible live workbench capture")
    parser.add_argument("--account-url", default="https://bsky.app/profile/bsky.app")
    parser.add_argument("--account-handle", default="bsky.app")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--output-root", default=R44A_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--html-path", default="")
    parser.add_argument("--screenshot-path", default="")
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--explicit-live-mode", action="store_true")
    parser.add_argument("--run-visible-live", action="store_true")
    parser.add_argument("--live-mode", action="store_true")
    parser.add_argument("--allow-external-visible-browser-capture", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--max-scrolls", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--feed-mode", default="posts_and_reposts", choices=("posts_and_reposts", "posts_and_retweets", "posts_retweets", "posts_and_replies", "posts_replies", "posts_only"))
    parser.add_argument("--timeline-mode", default="")
    parser.add_argument("--include-replies", action="store_true")
    parser.add_argument("--exclude-reposts", action="store_true")
    args = parser.parse_args(argv)
    if args.fixture_mode or (not args.html_path and not args.allow_external_visible_browser_capture):
        report = build_report(args.output_root)
        print(R44A_MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report.passed else 1
    result = run_bluesky_visible_live_workbench_capture_r44a(
        BlueskyVisibleLiveWorkbenchCaptureRequestR44A(
            account_url=args.account_url,
            account_handle=args.account_handle,
            capture_timestamp=args.capture_timestamp,
            output_root=args.output_root,
            visible_dom_html_path=args.html_path,
            static_screenshot_path=args.screenshot_path,
            explicit_live_mode=args.explicit_live_mode,
            run_visible_live=args.run_visible_live,
            live_mode=args.live_mode,
            allow_external_visible_browser_capture=args.allow_external_visible_browser_capture,
            headless=args.headless,
            max_items=args.max_items,
            max_scrolls=args.max_scrolls,
            timeout_seconds=args.timeout_seconds,
            feed_mode=args.timeline_mode or args.feed_mode,
            include_reposts=not bool(args.exclude_reposts),
            include_replies=bool(args.include_replies) or (args.timeline_mode or args.feed_mode) in {"posts_and_replies", "posts_replies"},
        )
    )
    print(R44A_MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
