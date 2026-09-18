from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

from profile_media_bluesky_visible_account_adapter_r43v import (
    R43V_PASS_STATUS,
    BlueskyVisibleAccountAdapterRequestR43V,
    build_bluesky_visible_account_adapter_r43v,
    build_fake_bluesky_post_views_r43v,
    parse_bluesky_app_url_r43v,
)

R43W_MARKER = "YTCE_R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT"
R43W_PASS_STATUS = "PASS_R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT"
R43W_BLOCKED_STATUS = "BLOCKED_R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT"
R43W_SCHEMA_VERSION = "bluesky_public_appview_import.r43w.v1"
R43W_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43w_bluesky_public_appview_import"
R43W_MODE_ID = "bluesky_public_appview_import"
BLUESKY_PUBLIC_APPVIEW_BASE_R43W = "https://public.api.bsky.app/xrpc"

BLUESKY_PUBLIC_REFERENCE_PATHS_R43W = (
    "atproto/lexicons/app/bsky/feed/getAuthorFeed.json",
    "atproto/lexicons/app/bsky/feed/getPosts.json",
    "atproto/lexicons/app/bsky/feed/getPostThread.json",
    "atproto/lexicons/app/bsky/feed/defs.json",
    "atproto/lexicons/app/bsky/embed/images.json",
    "atproto/lexicons/app/bsky/embed/video.json",
    "social-app/src/lib/api/feed/author.ts",
    "social-app/src/state/queries/post.ts",
    "social-app/bskyweb/templates/post.html",
)

FetcherR43W = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class BlueskyPublicAppviewImportRequestR43W:
    account_url: str = ""
    account_handle: str = ""
    actor: str = ""
    capture_timestamp: str = ""
    output_root: str = R43W_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    live_mode: bool = False
    explicit_live_mode: bool = False
    public_network_enabled: bool = False
    imported_feed_response: Mapping[str, Any] = field(default_factory=dict)
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = False
    max_items: int = 5
    timeout_seconds: float = 20.0
    include_pins: bool = True
    feed_filter: str = "posts_and_author_threads"
    feed_mode: str = "posts_and_reposts"
    include_reposts: bool = True
    include_replies: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class BlueskyPublicAppviewImportResultR43W:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    actor: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    request_path: str
    receipt_path: str
    appview_payload_dir: str
    public_endpoint_base: str
    request_urls: tuple[str, ...] = ()
    appview_statuses: tuple[str, ...] = ()
    appview_payload_paths: tuple[str, ...] = ()
    post_view_count: int = 0
    feed_mode: str = ""
    feed_filter: str = ""
    repost_record_count: int = 0
    reply_record_count: int = 0
    adapter_status: str = ""
    adapter_receipt_path: str = ""
    ledger_status: str = ""
    account_capture_dir: str = ""
    account_record_path: str = ""
    manifest_path: str = ""
    account_timeline_path: str = ""
    media_index_path: str = ""
    progress_events_path: str = ""
    review_strings_path: str = ""
    record_count: int = 0
    media_count: int = 0
    screenshot_count: int = 0
    post_folder_count: int = 0
    date_folders: tuple[str, ...] = ()
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43W_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43WReport:
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
        return self.status == R43W_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class BlueskyPublicAppviewImportR43W:
    """Fetch public Bluesky appview account feed JSON and pass postView rows into R43V."""

    def __init__(self, output_root: str | Path = R43W_DEFAULT_OUTPUT_ROOT, *, fetcher: FetcherR43W | None = None) -> None:
        self.output_root = Path(output_root)
        self.fetcher = fetcher

    def run_account_export(
        self,
        request: BlueskyPublicAppviewImportRequestR43W | Mapping[str, Any] | None = None,
        *,
        fetcher: FetcherR43W | None = None,
        **overrides: Any,
    ) -> BlueskyPublicAppviewImportResultR43W:
        req = coerce_bluesky_public_appview_import_request_r43w(request, **overrides)
        return run_bluesky_public_appview_import_r43w(req, output_root=self.output_root, fetcher=fetcher or self.fetcher)


def build_bluesky_public_appview_import_r43w(
    output_root: str | Path = R43W_DEFAULT_OUTPUT_ROOT,
    *,
    fetcher: FetcherR43W | None = None,
) -> BlueskyPublicAppviewImportR43W:
    return BlueskyPublicAppviewImportR43W(output_root=output_root, fetcher=fetcher)


def build_bluesky_public_appview_import_contract_r43w() -> dict[str, Any]:
    return {
        "marker": R43W_MARKER,
        "schema_version": R43W_SCHEMA_VERSION,
        "mode_id": R43W_MODE_ID,
        "public_endpoint_base": BLUESKY_PUBLIC_APPVIEW_BASE_R43W,
        "public_endpoints_used": [
            "app.bsky.feed.getAuthorFeed",
        ],
        "accepted_inputs": [
            "explicit live/public appview account-feed fetch",
            "injected appview feed JSON for tests/import",
            "fixture_mode appview feed JSON for contract validation",
        ],
        "downstream_adapter": "profile_media_bluesky_visible_account_adapter_r43v",
        "downstream_ledger": "profile_media_universal_social_account_ledger_contract_r43u",
        "network_requests_require_explicit_live_or_public_network_flag": True,
        "remote_media_downloads_performed_by_r43w": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "browser_session_started": False,
        "binding_strategy": [
            "fetch public app.bsky.feed.getAuthorFeed postView rows",
            "write raw public appview JSON receipt payloads",
            "pass postView rows into R43V imported_post_views",
            "let R43V/R43U map account/date/post/media ledger outputs",
            "preserve metadata-only media receipts without downloading remote media",
        ],
        "repo_reference_paths": list(BLUESKY_PUBLIC_REFERENCE_PATHS_R43W),
    }


def run_bluesky_public_appview_import_r43w(
    request: BlueskyPublicAppviewImportRequestR43W | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R43W_DEFAULT_OUTPUT_ROOT,
    fetcher: FetcherR43W | None = None,
) -> BlueskyPublicAppviewImportResultR43W:
    req = coerce_bluesky_public_appview_import_request_r43w(request)
    root = Path(req.output_root or output_root or R43W_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    account_url = _plain_url(req.account_url)
    parsed = parse_bluesky_app_url_r43v(account_url)
    actor = _safe_actor(req.actor or req.account_handle or parsed.get("handle") or "example.bsky.social")
    handle = _safe_handle(req.account_handle or parsed.get("handle") or actor)
    if not account_url:
        account_url = f"https://bsky.app/profile/{handle}"
    run_dir = root / handle / f"bluesky_public_appview_import_{capture_ts}"
    payload_dir = run_dir / "appview_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "r43w_bluesky_public_appview_import_request.json"
    receipt_path = run_dir / "r43w_bluesky_public_appview_import_receipt.json"
    _write_json(request_path, req.to_dict())

    warnings: list[str] = []
    request_urls: list[str] = []
    statuses: list[str] = []
    payload_paths: list[str] = []
    feed_response: Mapping[str, Any] = {}

    network_enabled = bool(req.public_network_enabled or req.live_mode or req.explicit_live_mode)
    if req.imported_feed_response:
        feed_response = _mapping(req.imported_feed_response)
        statuses.append("imported_feed_response")
        payload_path = payload_dir / "imported_getAuthorFeed_response.json"
        _write_json(payload_path, feed_response)
        payload_paths.append(str(payload_path))
    elif req.fixture_mode:
        feed_response = build_fake_bluesky_public_appview_feed_response_r43w(actor=actor, limit=max(_safe_int(req.max_items), 1))
        statuses.append("fixture_feed_response_no_network")
        payload_path = payload_dir / "fixture_getAuthorFeed_response.json"
        _write_json(payload_path, feed_response)
        payload_paths.append(str(payload_path))
    elif network_enabled:
        url = build_bluesky_get_author_feed_url_r43w(
            actor=actor,
            limit=max(_safe_int(req.max_items), 1),
            include_pins=req.include_pins,
            feed_filter=bluesky_public_feed_filter_for_mode_r44c(req.feed_mode, req.feed_filter, include_replies=req.include_replies),
        )
        request_urls.append(url)
        fetch_result = _fetch_json_r43w(url, fetcher=fetcher, timeout_seconds=req.timeout_seconds)
        statuses.append(_clean(fetch_result.get("status")) or "unknown_fetch_status")
        payload_path = payload_dir / "public_getAuthorFeed_response.json"
        _write_json(payload_path, fetch_result)
        payload_paths.append(str(payload_path))
        if fetch_result.get("ok") and isinstance(fetch_result.get("json"), Mapping):
            feed_response = _mapping(fetch_result.get("json"))
        else:
            warnings.append(_clean(fetch_result.get("error")) or "Public Bluesky appview fetch did not return JSON.")
    else:
        warnings.append("No fixture/imported feed was supplied and public network access was not explicitly enabled.")

    post_views = extract_post_views_from_author_feed_r43w(
        feed_response,
        max_items=max(_safe_int(req.max_items), 1),
        feed_mode=req.feed_mode,
    )
    r43v_payload: dict[str, Any] = {}
    if post_views:
        from profile_media_bluesky_visible_account_adapter_r43v import R43V_PASS_STATUS as _R43V_PASS_STATUS

        adapter = build_bluesky_visible_account_adapter_r43v(output_root=run_dir / "r43v_adapter")
        r43v_request = BlueskyVisibleAccountAdapterRequestR43V(
            account_url=account_url,
            account_handle=handle,
            capture_timestamp=capture_ts,
            output_root=str(run_dir / "r43v_adapter"),
            fixture_mode=False,
            imported_post_views=tuple(post_views),
            include_media=req.include_media,
            include_static_screenshots=req.include_static_screenshots,
            require_screenshot_receipts=req.require_screenshot_receipts,
            max_items=max(_safe_int(req.max_items), 1),
        )
        r43v_result = adapter.run_account_export(r43v_request, imported_post_views=post_views)
        r43v_payload = r43v_result.to_dict()
        if r43v_result.status != _R43V_PASS_STATUS:
            warnings.append(f"R43V downstream adapter did not pass: {r43v_result.status!r}.")
    else:
        warnings.append("No app.bsky.feed.defs#postView rows were available to import.")

    flags = build_r43w_side_effect_flags(network_actions_performed=network_enabled)
    status = R43W_PASS_STATUS if r43v_payload.get("status") == R43V_PASS_STATUS and _safe_int(r43v_payload.get("record_count")) > 0 and not warnings else R43W_BLOCKED_STATUS
    result = BlueskyPublicAppviewImportResultR43W(
        marker=R43W_MARKER,
        schema_version=R43W_SCHEMA_VERSION,
        status=status,
        account_handle=handle,
        account_url=account_url,
        actor=actor,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        appview_payload_dir=str(payload_dir),
        public_endpoint_base=BLUESKY_PUBLIC_APPVIEW_BASE_R43W,
        request_urls=tuple(request_urls),
        appview_statuses=tuple(statuses),
        appview_payload_paths=tuple(payload_paths),
        post_view_count=len(post_views),
        feed_mode=normalize_bluesky_feed_mode_r44c(req.feed_mode, include_reposts=req.include_reposts, include_replies=req.include_replies),
        feed_filter=bluesky_public_feed_filter_for_mode_r44c(req.feed_mode, req.feed_filter, include_replies=req.include_replies),
        repost_record_count=sum(1 for row in post_views if _is_repost_post_view_r44c(row)),
        reply_record_count=sum(1 for row in post_views if _is_reply_post_view_r44c(row)),
        adapter_status=_clean(r43v_payload.get("status")),
        adapter_receipt_path=_clean(r43v_payload.get("receipt_path")),
        ledger_status=_clean(r43v_payload.get("ledger_status")),
        account_capture_dir=_clean(r43v_payload.get("account_capture_dir")),
        account_record_path=_clean(r43v_payload.get("account_record_path")),
        manifest_path=_clean(r43v_payload.get("manifest_path")),
        account_timeline_path=_clean(r43v_payload.get("account_timeline_path")),
        media_index_path=_clean(r43v_payload.get("media_index_path")),
        progress_events_path=_clean(r43v_payload.get("progress_events_path")),
        review_strings_path=_clean(r43v_payload.get("review_strings_path")),
        record_count=_safe_int(r43v_payload.get("record_count")),
        media_count=_safe_int(r43v_payload.get("media_count")),
        screenshot_count=_safe_int(r43v_payload.get("screenshot_count")),
        post_folder_count=_safe_int(r43v_payload.get("post_folder_count")),
        date_folders=tuple(str(item) for item in (r43v_payload.get("date_folders") or ())),
        side_effect_flags=flags,
        warnings=tuple(warnings),
    )
    _write_json(receipt_path, result.to_dict())
    return result


def build_bluesky_get_author_feed_url_r43w(
    *,
    actor: str,
    limit: int = 5,
    cursor: str = "",
    include_pins: bool = True,
    feed_filter: str = "posts_and_author_threads",
) -> str:
    params: dict[str, str] = {
        "actor": _safe_actor(actor),
        "limit": str(max(1, min(_safe_int(limit), 100))),
        "filter": _clean(feed_filter or "posts_and_author_threads"),
        "includePins": "true" if include_pins else "false",
    }
    if cursor:
        params["cursor"] = _clean(cursor)
    return f"{BLUESKY_PUBLIC_APPVIEW_BASE_R43W}/app.bsky.feed.getAuthorFeed?{urllib.parse.urlencode(params)}"


def extract_post_views_from_author_feed_r43w(feed_response: Mapping[str, Any], *, max_items: int = 5, feed_mode: str = "posts_and_reposts") -> tuple[Mapping[str, Any], ...]:
    payload = _mapping(feed_response)
    rows = _sequence(payload.get("feed"))
    post_views: list[Mapping[str, Any]] = []
    limit = max(_safe_int(max_items), 0) or len(rows)
    for row in rows:
        item = _mapping(row)
        post = _mapping(item.get("post") or item)
        if post.get("uri") and post.get("author"):
            enriched_post = dict(post)
            if isinstance(row, Mapping):
                if item.get("reason"):
                    enriched_post["r43w_feed_reason"] = _mapping(item.get("reason"))
                if item.get("reply"):
                    enriched_post["r43w_feed_reply"] = _mapping(item.get("reply"))
            enriched_post["r44c_feed_mode"] = normalize_bluesky_feed_mode_r44c(feed_mode)
            post_views.append(enriched_post)
        if len(post_views) >= limit:
            break
    return tuple(post_views)


def build_fake_bluesky_public_appview_feed_response_r43w(*, actor: str = "example.bsky.social", limit: int = 5) -> dict[str, Any]:
    rows = []
    for post in build_fake_bluesky_post_views_r43v(account_handle=_safe_handle(actor) or "example.bsky.social")[:max(1, limit)]:
        rows.append({"post": post, "reason": {"$type": "app.bsky.feed.defs#reasonRepost", "by": post.get("author", {})}})
    return {
        "feed": rows,
        "cursor": "r43w-fixture-cursor",
        "r43w_fixture": True,
    }


def coerce_bluesky_public_appview_import_request_r43w(
    request: BlueskyPublicAppviewImportRequestR43W | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> BlueskyPublicAppviewImportRequestR43W:
    if isinstance(request, BlueskyPublicAppviewImportRequestR43W):
        data = request.to_dict()
    elif isinstance(request, Mapping):
        data = dict(request)
    else:
        data = {}
    for key, value in overrides.items():
        if value not in (None, ""):
            data[key] = value
    return BlueskyPublicAppviewImportRequestR43W(
        account_url=_plain_url(data.get("account_url") or ""),
        account_handle=_safe_handle(data.get("account_handle") or ""),
        actor=_safe_actor(data.get("actor") or ""),
        capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""),
        output_root=_clean(data.get("output_root") or R43W_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        public_network_enabled=_to_bool(data.get("public_network_enabled"), False),
        imported_feed_response=_mapping(data.get("imported_feed_response")),
        include_media=_to_bool(data.get("include_media"), True),
        include_static_screenshots=_to_bool(data.get("include_static_screenshots"), True),
        require_screenshot_receipts=_to_bool(data.get("require_screenshot_receipts"), False),
        max_items=_safe_int(data.get("max_items"), 5),
        timeout_seconds=float(data.get("timeout_seconds") or 20.0),
        include_pins=_to_bool(data.get("include_pins"), True),
        feed_filter=_clean(data.get("feed_filter") or "posts_and_author_threads"),
        feed_mode=normalize_bluesky_feed_mode_r44c(data.get("feed_mode") or data.get("timeline_mode") or "", include_reposts=_to_bool(data.get("include_reposts"), True), include_replies=_to_bool(data.get("include_replies"), False)),
        include_reposts=_to_bool(data.get("include_reposts"), True),
        include_replies=_to_bool(data.get("include_replies"), False),
    )




def normalize_bluesky_feed_mode_r44c(value: Any = "", *, include_reposts: bool = True, include_replies: bool = False) -> str:
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


def bluesky_public_feed_filter_for_mode_r44c(feed_mode: Any = "", explicit_feed_filter: str = "", *, include_replies: bool = False) -> str:
    mode = normalize_bluesky_feed_mode_r44c(feed_mode, include_replies=include_replies)
    explicit = _clean(explicit_feed_filter)
    if mode == "posts_and_replies":
        return "posts_with_replies"
    if explicit and explicit != "posts_and_author_threads":
        return explicit
    if mode == "posts_only":
        return "posts_no_replies"
    return "posts_and_author_threads"


def _is_repost_post_view_r44c(post_view: Mapping[str, Any]) -> bool:
    reason = _mapping(post_view.get("r43w_feed_reason") or post_view.get("reason"))
    reason_type = _clean(reason.get("$type") or reason.get("type"))
    return "reasonRepost" in reason_type or reason_type.endswith("#reasonRepost")


def _is_reply_post_view_r44c(post_view: Mapping[str, Any]) -> bool:
    record = _mapping(post_view.get("record"))
    return bool(_mapping(record.get("reply") or post_view.get("reply")))

def build_r43w_side_effect_flags(*, network_actions_performed: bool = False) -> dict[str, bool]:
    return {
        "bluesky_public_appview_import_invoked": True,
        "network_actions_performed": bool(network_actions_performed),
        "public_appview_fetch_only_when_explicitly_enabled": True,
        "browser_session_started": False,
        "webview2_session_started_by_r43w": False,
        "webview2_internals_copied": False,
        "hidden_platform_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "remote_media_downloads_performed": False,
        "r43v_bluesky_adapter_used": True,
        "r43u_universal_ledger_writer_used": True,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
    }


def build_report(output_root: str | Path = R43W_DEFAULT_OUTPUT_ROOT) -> R43WReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    result = run_bluesky_public_appview_import_r43w(
        BlueskyPublicAppviewImportRequestR43W(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            actor="example.bsky.social",
            capture_timestamp="20260918T064000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
            max_items=5,
        )
    )
    payload = result.to_dict()
    contract = build_bluesky_public_appview_import_contract_r43w()
    flags = build_r43w_side_effect_flags(network_actions_performed=False)
    media_index = _read_json(result.media_index_path, default=[])
    checks = (
        _check("fixture_import_passes_without_network", result.status == R43W_PASS_STATUS and payload["side_effect_flags"]["network_actions_performed"] is False),
        _check("public_appview_endpoint_contract_recorded", "app.bsky.feed.getAuthorFeed" in contract["public_endpoints_used"]),
        _check("public_feed_post_views_feed_into_r43v", result.adapter_status == R43V_PASS_STATUS and result.post_view_count == result.record_count and result.record_count >= 2),
        _check("r43u_ledger_output_written", Path(result.account_record_path).is_file() and Path(result.media_index_path).is_file() and result.ledger_status.startswith("PASS_R43U_")),
        _check("metadata_only_media_receipts", result.media_count >= 3 and all(row.get("metadata_only_remote_media_not_downloaded") is True for row in _sequence(media_index))),
        _check("raw_public_appview_payload_receipt_written", all(Path(path).is_file() for path in result.appview_payload_paths)),
        _check("no_remote_media_downloads_or_browser_state", not any(payload["side_effect_flags"].get(name) for name in ("remote_media_downloads_performed", "browser_session_started", "webview2_internals_copied", "cookie_or_token_extraction_performed", "login_automation_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(payload) and _machine_urls_are_plain(contract)),
    )
    status = R43W_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43W_BLOCKED_STATUS
    report = R43WReport(
        marker=R43W_MARKER,
        schema_version=R43W_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        sample_result=payload,
        contract=contract,
        side_effect_flags=flags,
    )
    write_report(report, root)
    return report


def write_report(report: R43WReport, output_root: str | Path = R43W_DEFAULT_OUTPUT_ROOT) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT_REPORT.json", report.to_dict())
    lines = [
        "# R43W Bluesky public appview import report",
        "",
        f"- marker: `{report.marker}`",
        f"- status: `{report.status}`",
        f"- schema_version: `{report.schema_version}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')}")
    _write_text(root / "R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT_REPORT.md", "\n".join(lines) + "\n")


def _fetch_json_r43w(url: str, *, fetcher: FetcherR43W | None, timeout_seconds: float) -> dict[str, Any]:
    if fetcher is not None:
        try:
            data = _mapping(fetcher(url))
            if "json" not in data and "feed" in data:
                data = {"ok": True, "status": "injected_fetcher_ok", "status_code": 200, "url": url, "json": data}
            return _to_jsonable(data)
        except Exception as exc:
            return {"ok": False, "status": "injected_fetcher_exception", "status_code": 0, "url": url, "error": f"{type(exc).__name__}: {exc}"}
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "YTCE-R43W-Bluesky-Public-Appview-Import/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(float(timeout_seconds or 20.0), 1.0)) as response:
            status_code = int(getattr(response, "status", 0) or 0)
            raw = response.read(3_000_000)
            text = raw.decode("utf-8", errors="replace")
            return {
                "ok": 200 <= status_code < 300,
                "status": f"http_{status_code}",
                "status_code": status_code,
                "url": url,
                "json": json.loads(text),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(2000).decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return {"ok": False, "status": f"http_{exc.code}", "status_code": int(exc.code), "url": url, "error": body or str(exc)}
    except Exception as exc:
        return {"ok": False, "status": "fetch_exception", "status_code": 0, "url": url, "error": f"{type(exc).__name__}: {exc}"}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()


def _safe_actor(value: Any) -> str:
    text = _clean(value)
    if text.startswith("https://"):
        parsed = parse_bluesky_app_url_r43v(text)
        text = parsed.get("handle") or text
    return text.strip().strip("@")[:256]


def _safe_handle(value: Any) -> str:
    text = _safe_actor(value)
    text = text.replace("/", "_").replace("\\", "_").replace(":", "_").strip("._ ")
    return text[:160] or "unknown_account"


def _safe_ts(value: Any) -> str:
    text = _clean(value)
    return text if text and all(ch.isalnum() or ch in "._-TZ" for ch in text) else ""


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _plain_url(value: Any) -> str:
    text = _clean(value)
    if text.startswith("[") and "](" in text and text.endswith(")"):
        match = re_match_markdown_url_r43w(text)
        if match:
            text = match
    if not text:
        return ""
    parsed = urlsplit(text)
    if parsed.scheme in {"http", "https", "at"} or text.startswith("at://"):
        return text
    return text


def re_match_markdown_url_r43w(text: str) -> str:
    # Keep this separate from the report checker so generated machine JSON never
    # deliberately emits Markdown-wrapped URLs.
    import re

    match = re.match(r"^\[[^\]]+\]\(([^)]+)\)$", text)
    return match.group(1) if match else ""


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _check(name: str, ok: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def _machine_urls_are_plain(value: Any) -> bool:
    text = json.dumps(_to_jsonable(value), sort_keys=True)
    return "](" not in text and "%5Bhttp" not in text


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R43W Bluesky public appview import lane")
    parser.add_argument("--output-root", default=R43W_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--account-url", default="")
    parser.add_argument("--account-handle", default="")
    parser.add_argument("--actor", default="")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--live", action="store_true", help="perform explicit public appview network fetch")
    parser.add_argument("--fixture", action="store_true", help="use fixture public appview payload")
    args = parser.parse_args(argv)
    if args.live or args.account_url or args.account_handle or args.actor:
        result = run_bluesky_public_appview_import_r43w(
            BlueskyPublicAppviewImportRequestR43W(
                account_url=args.account_url,
                account_handle=args.account_handle,
                actor=args.actor,
                capture_timestamp=args.capture_timestamp,
                output_root=args.output_root,
                fixture_mode=args.fixture,
                live_mode=args.live,
                public_network_enabled=args.live,
                max_items=args.max_items,
            )
        )
        print(R43W_MARKER)
        print(result.status)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.passed else 1
    report = build_report(args.output_root)
    print(R43W_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
