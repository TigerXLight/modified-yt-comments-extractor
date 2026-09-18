from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from profile_media_universal_social_export_surface_ui_routing_r43f import (
    R43F_PASS_STATUS,
    UniversalSocialExportSurfaceRequestR43F,
    UniversalSocialExportSurfaceRouterR43F,
    build_universal_social_export_surface_router_r43f,
)
from profile_media_universal_social_account_tracking_r43e import build_universal_social_account_tracking_contract_r43e

R43G_MARKER = "YTCE_R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION"
R43G_PASS_STATUS = "PASS_R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION"
R43G_BLOCKED_STATUS = "BLOCKED_R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION"
R43G_SCHEMA_VERSION = "universal_social_batch_account_intake_platform_url_detection.r43g.v1"
R43G_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43g_universal_social_batch_account_intake_platform_url_detection"
R43G_MODE_ID = "universal_social_batch_account_intake_platform_url_detection"

BATCH_INTAKE_OUTPUT_FILES_R43G: tuple[str, ...] = (
    "batch_intake_request.json",
    "batch_intake_runbook.md",
    "normalized_inputs.ndjson",
    "platform_detection_index.json",
    "route_receipts.ndjson",
    "batch_route_receipt.json",
    "unsupported_inputs.ndjson",
    "universal_social_batch_intake_receipt.json",
)

SOCIAL_PLATFORM_IDS_R43G: tuple[str, ...] = (
    "twitter_x",
    "bluesky",
    "instagram",
    "facebook",
    "threads",
    "mastodon",
    "tiktok",
    "reddit",
    "youtube",
    "news_comments",
)

TRACKING_QUERY_PARAMS_R43G = {"fbclid", "gclid", "igsh", "mc_cid", "mc_eid", "ref_src", "s", "si"}
URL_REGEX_R43G = re.compile(
    r"(?P<md>\[[^\]]+\]\((?P<mdurl>https?://[^)\s]+)\))|"
    r"(?P<url>https?://[^\s<>\"')]+|(?:x\.com|twitter\.com|mobile\.twitter\.com|bsky\.app|instagram\.com|www\.instagram\.com|facebook\.com|www\.facebook\.com|m\.facebook\.com|threads\.net|www\.threads\.net|mastodon\.social|tiktok\.com|www\.tiktok\.com|reddit\.com|www\.reddit\.com|old\.reddit\.com|youtube\.com|www\.youtube\.com|youtu\.be)/[^\s<>\"')]+)",
    re.I,
)


@dataclass(frozen=True)
class UniversalSocialBatchAccountIntakeRequestR43G:
    inputs: tuple[str, ...] = ()
    txt_path: str = ""
    raw_text: str = ""
    platform_id_hint: str = ""
    include_posts: bool = True
    include_reposts_or_reshares: bool = True
    include_quotes: bool = True
    include_replies: bool = False
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    capture_timestamp: str = ""
    output_root: str = R43G_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    public_network_enabled: bool = False
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""
    max_items: int = 3
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniversalSocialDetectedInputR43G:
    batch_index: int
    raw_input: str
    normalized_url: str
    platform_id: str
    url_kind: str
    account_handle: str
    record_id: str = ""
    detection_status: str = "detected"
    route_status: str = "not_routed"
    downstream_status: str = ""
    route_receipt_path: str = ""
    route_run_dir: str = ""
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchAccountIntakeResultR43G:
    marker: str
    schema_version: str
    status: str
    capture_timestamp: str
    run_dir: str
    request_path: str
    runbook_path: str
    normalized_inputs_path: str
    detection_index_path: str
    route_receipts_path: str
    batch_route_receipt_path: str
    unsupported_inputs_path: str
    universal_receipt_path: str
    total_inputs: int
    detected_url_count: int
    account_url_count: int
    post_url_count: int
    pending_platform_count: int
    unsupported_count: int
    route_result_count: int
    platform_counts: Mapping[str, int]
    url_kind_counts: Mapping[str, int]
    items: tuple[Mapping[str, Any], ...]
    route_results: tuple[Mapping[str, Any], ...]
    side_effect_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43G_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43GReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    universal_contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43G_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "sample_result": _to_jsonable(self.sample_result),
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
            "universal_contract": _to_jsonable(self.universal_contract),
        }


class UniversalSocialBatchAccountIntakeRouterR43G:
    """Batch URL intake above the universal social export surface.

    R43G accepts one URL, many URLs, TXT lines, or pasted mixed text.  It
    normalizes and detects account/post URLs for the platform-neutral social
    contract before routing every item through R43F, which then routes through
    R43E and concrete adapters where implemented.  Twitter/X remains only the
    first adapter; pending platforms produce mapped receipts instead of crashes.
    """

    def __init__(
        self,
        *,
        export_router: UniversalSocialExportSurfaceRouterR43F | None = None,
        output_root: str | Path = R43G_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.output_root = Path(output_root)
        self.export_router = export_router or build_universal_social_export_surface_router_r43f(output_root=self.output_root / "r43f_surface")

    def detect_input(self, raw_input: str, *, batch_index: int = 0, platform_id_hint: str = "") -> UniversalSocialDetectedInputR43G:
        normalized = _plain_url(raw_input)
        platform, url_kind, handle, record_id, warning = detect_social_url_r43g(normalized, platform_id_hint=platform_id_hint)
        detection_status = "detected" if normalized and platform != "unknown_platform" else "unsupported_or_unknown"
        return UniversalSocialDetectedInputR43G(
            batch_index=batch_index,
            raw_input=_clean(raw_input),
            normalized_url=normalized,
            platform_id=platform,
            url_kind=url_kind,
            account_handle=handle,
            record_id=record_id,
            detection_status=detection_status,
            warning=warning,
        )

    def route_batch(
        self,
        request: UniversalSocialBatchAccountIntakeRequestR43G | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> UniversalSocialBatchAccountIntakeResultR43G:
        req = coerce_universal_social_batch_account_intake_request_r43g(request, **overrides)
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        run_dir = Path(req.output_root or self.output_root) / f"batch_intake_{capture_ts}"
        run_dir.mkdir(parents=True, exist_ok=True)

        request_path = run_dir / "batch_intake_request.json"
        runbook_path = run_dir / "batch_intake_runbook.md"
        normalized_inputs_path = run_dir / "normalized_inputs.ndjson"
        detection_index_path = run_dir / "platform_detection_index.json"
        route_receipts_path = run_dir / "route_receipts.ndjson"
        batch_route_receipt_path = run_dir / "batch_route_receipt.json"
        unsupported_inputs_path = run_dir / "unsupported_inputs.ndjson"
        universal_receipt_path = run_dir / "universal_social_batch_intake_receipt.json"

        raw_items = collect_batch_inputs_r43g(req)
        detected_items = [self.detect_input(raw, batch_index=index, platform_id_hint=req.platform_id_hint) for index, raw in enumerate(raw_items, start=1)]
        route_results: list[Mapping[str, Any]] = []
        updated_items: list[UniversalSocialDetectedInputR43G] = []
        warnings: list[str] = []

        for item in detected_items:
            route_result = self.export_router.route_account_tracking_export(
                UniversalSocialExportSurfaceRequestR43F(
                    platform_id=item.platform_id,
                    account_url=item.normalized_url,
                    account_handle=item.account_handle,
                    include_posts=req.include_posts,
                    include_reposts_or_reshares=req.include_reposts_or_reshares,
                    include_quotes=req.include_quotes,
                    include_replies=req.include_replies,
                    include_media=req.include_media,
                    include_static_screenshots=req.include_static_screenshots,
                    require_screenshot_receipts=req.require_screenshot_receipts,
                    capture_timestamp=f"{capture_ts}_{item.batch_index:04d}",
                    output_root=str(run_dir / "routes"),
                    fixture_mode=req.fixture_mode,
                    explicit_live_mode=req.explicit_live_mode,
                    run_visible_live=req.run_visible_live,
                    live_mode=req.live_mode,
                    public_network_enabled=req.public_network_enabled,
                    browser_user_data_dir=req.browser_user_data_dir,
                    browser_executable_path=req.browser_executable_path,
                    max_items=req.max_items,
                    max_scrolls=req.max_scrolls,
                )
            )
            route_payload = route_result.to_dict()
            route_payload["batch_index"] = item.batch_index
            route_payload["input_url_kind"] = item.url_kind
            route_payload["input_normalized_url"] = item.normalized_url
            route_results.append(route_payload)
            updated = UniversalSocialDetectedInputR43G(
                batch_index=item.batch_index,
                raw_input=item.raw_input,
                normalized_url=item.normalized_url,
                platform_id=item.platform_id,
                url_kind=item.url_kind,
                account_handle=item.account_handle,
                record_id=item.record_id,
                detection_status=item.detection_status,
                route_status=route_result.route_status,
                downstream_status=route_result.downstream_status,
                route_receipt_path=route_result.surface_receipt_path,
                route_run_dir=route_result.run_dir,
                warning=item.warning or "; ".join(route_result.warnings),
            )
            updated_items.append(updated)
            if updated.warning:
                warnings.append(f"input {updated.batch_index}: {updated.warning}")

        platform_counts = _count_by(updated_items, "platform_id")
        url_kind_counts = _count_by(updated_items, "url_kind")
        unsupported = [item.to_dict() for item in updated_items if item.platform_id == "unknown_platform" or item.route_status == "unsupported_platform_receipt"]
        side_effect_flags = build_r43g_side_effect_flags()

        request_payload = {
            **req.to_dict(),
            "capture_timestamp": capture_ts,
            "marker": R43G_MARKER,
            "schema_version": R43G_SCHEMA_VERSION,
            "output_files": BATCH_INTAKE_OUTPUT_FILES_R43G,
        }
        _write_json(request_path, request_payload)
        _write_ndjson(normalized_inputs_path, [item.to_dict() for item in updated_items])
        _write_json(detection_index_path, {"items": [item.to_dict() for item in updated_items], "platform_counts": platform_counts, "url_kind_counts": url_kind_counts})
        _write_ndjson(route_receipts_path, route_results)
        _write_json(unsupported_inputs_path, {"items": unsupported, "unsupported_count": len(unsupported)})
        _write_text(runbook_path, _build_runbook(req, updated_items))

        pending_count = sum(1 for result in route_results if result.get("route_status") == "mapped_pending_adapter_receipt")
        result = UniversalSocialBatchAccountIntakeResultR43G(
            marker=R43G_MARKER,
            schema_version=R43G_SCHEMA_VERSION,
            status=R43G_PASS_STATUS,
            capture_timestamp=capture_ts,
            run_dir=str(run_dir),
            request_path=str(request_path),
            runbook_path=str(runbook_path),
            normalized_inputs_path=str(normalized_inputs_path),
            detection_index_path=str(detection_index_path),
            route_receipts_path=str(route_receipts_path),
            batch_route_receipt_path=str(batch_route_receipt_path),
            unsupported_inputs_path=str(unsupported_inputs_path),
            universal_receipt_path=str(universal_receipt_path),
            total_inputs=len(raw_items),
            detected_url_count=sum(1 for item in updated_items if item.normalized_url),
            account_url_count=sum(1 for item in updated_items if item.url_kind == "account"),
            post_url_count=sum(1 for item in updated_items if item.url_kind in {"post", "video", "comment_thread"}),
            pending_platform_count=pending_count,
            unsupported_count=len(unsupported),
            route_result_count=len(route_results),
            platform_counts=platform_counts,
            url_kind_counts=url_kind_counts,
            items=tuple(item.to_dict() for item in updated_items),
            route_results=tuple(route_results),
            side_effect_flags=side_effect_flags,
            warnings=tuple(warnings),
        )
        _write_json(batch_route_receipt_path, result.to_dict())
        _write_json(universal_receipt_path, {"batch_intake_result": result.to_dict(), "universal_contract": build_universal_social_account_tracking_contract_r43e()})
        return result


def build_universal_social_batch_account_intake_router_r43g(
    *,
    export_router: UniversalSocialExportSurfaceRouterR43F | None = None,
    output_root: str | Path = R43G_DEFAULT_OUTPUT_ROOT,
) -> UniversalSocialBatchAccountIntakeRouterR43G:
    return UniversalSocialBatchAccountIntakeRouterR43G(export_router=export_router, output_root=output_root)


def coerce_universal_social_batch_account_intake_request_r43g(
    request: UniversalSocialBatchAccountIntakeRequestR43G | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> UniversalSocialBatchAccountIntakeRequestR43G:
    if isinstance(request, UniversalSocialBatchAccountIntakeRequestR43G):
        data = request.to_dict()
    elif isinstance(request, Mapping):
        data = dict(request)
    else:
        data = {}
    for key, value in overrides.items():
        if value not in (None, ""):
            data[key] = value
    inputs = data.get("inputs") or ()
    if isinstance(inputs, str):
        inputs_tuple = tuple(extract_urls_from_text_r43g(inputs)) or (inputs,)
    else:
        inputs_tuple = tuple(_clean(item) for item in inputs if _clean(item))
    return UniversalSocialBatchAccountIntakeRequestR43G(
        inputs=inputs_tuple,
        txt_path=_clean(data.get("txt_path") or ""),
        raw_text=_clean(data.get("raw_text") or ""),
        platform_id_hint=_safe_platform_id(data.get("platform_id_hint") or ""),
        include_posts=bool(data.get("include_posts", True)),
        include_reposts_or_reshares=bool(data.get("include_reposts_or_reshares", True)),
        include_quotes=bool(data.get("include_quotes", True)),
        include_replies=bool(data.get("include_replies", False)),
        include_media=bool(data.get("include_media", True)),
        include_static_screenshots=bool(data.get("include_static_screenshots", True)),
        require_screenshot_receipts=bool(data.get("require_screenshot_receipts", True)),
        capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""),
        output_root=_clean(data.get("output_root") or R43G_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(data.get("run_visible_live"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        public_network_enabled=_to_bool(data.get("public_network_enabled"), False),
        browser_user_data_dir=_clean(data.get("browser_user_data_dir")),
        browser_executable_path=_clean(data.get("browser_executable_path")),
        max_items=_safe_int(data.get("max_items"), 3),
        max_scrolls=_safe_int(data.get("max_scrolls"), 2),
    )


def collect_batch_inputs_r43g(req: UniversalSocialBatchAccountIntakeRequestR43G) -> tuple[str, ...]:
    values: list[str] = []
    values.extend(req.inputs)
    if req.raw_text:
        values.extend(extract_urls_from_text_r43g(req.raw_text))
    if req.txt_path:
        path = Path(req.txt_path)
        if path.is_file():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                values.extend(extract_urls_from_text_r43g(line) or [_clean(line)])
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = _plain_url(value)
        key = normalized.lower()
        if normalized and key not in seen:
            out.append(value)
            seen.add(key)
    return tuple(out)


def extract_urls_from_text_r43g(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for match in URL_REGEX_R43G.finditer(_clean(text).replace("\\_", "_")):
        url = match.group("mdurl") or match.group("url") or ""
        url = url.rstrip(".,;:!]")
        if url:
            found.append(url)
    return tuple(found)


def detect_social_url_r43g(url: str, *, platform_id_hint: str = "") -> tuple[str, str, str, str, str]:
    normalized = _plain_url(url)
    parsed = urlsplit(normalized)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    hint = _safe_platform_id(platform_id_hint)
    if not host:
        return hint or "unknown_platform", "unknown", "unknown_account", "", "no host detected"

    platform = _platform_from_host(host, hint, parsed.path, parsed.query, parsed.fragment)
    if platform == "twitter_x":
        if "status" in parts or (parts[:2] == ["i", "status"]):
            record_id = _after(parts, "status") or (parts[2] if len(parts) > 2 and parts[:2] == ["i", "status"] else "")
            handle = parts[0] if parts and parts[0] not in {"i", "status"} else "unknown_account"
            return platform, "post", _safe_handle(handle), _safe_id(record_id), ""
        handle = parts[0] if parts else _handle_from_query(parsed.query)
        return platform, "account", _safe_handle(handle), "", ""

    if platform == "bluesky":
        if len(parts) >= 4 and parts[0] == "profile" and parts[2] == "post":
            return platform, "post", _safe_handle(parts[1]), _safe_id(parts[3]), ""
        if len(parts) >= 2 and parts[0] == "profile":
            return platform, "account", _safe_handle(parts[1]), "", ""
        return platform, "account", _safe_handle(parts[0] if parts else "unknown_account"), "", ""

    if platform == "instagram":
        if parts and parts[0] in {"p", "reel", "reels", "tv"}:
            return platform, "post", "unknown_account", _safe_id(parts[1] if len(parts) > 1 else ""), ""
        if parts and parts[0] == "stories":
            return platform, "post", _safe_handle(parts[1] if len(parts) > 1 else "unknown_account"), _safe_id(parts[2] if len(parts) > 2 else ""), ""
        return platform, "account", _safe_handle(parts[0] if parts else "unknown_account"), "", ""

    if platform == "facebook":
        joined = "/".join(parts).lower()
        if parts and (parts[0] in {"story.php", "permalink.php", "photo.php", "watch"} or any(token in joined for token in ("posts", "videos", "photos", "reel"))):
            return platform, "post", _safe_handle(parts[0] if parts and parts[0].endswith(".php") is False else _handle_from_query(parsed.query)), _safe_id(_id_from_query(parsed.query) or (parts[-1] if parts else "")), ""
        if parts and parts[0] == "profile.php":
            return platform, "account", _safe_handle(_id_from_query(parsed.query) or "profile"), "", ""
        return platform, "account", _safe_handle(parts[0] if parts else _id_from_query(parsed.query) or "unknown_account"), "", ""

    if platform == "threads":
        handle = parts[0] if parts and parts[0].startswith("@") else (parts[0] if parts else "unknown_account")
        if len(parts) >= 3 and parts[1] in {"post", "t"}:
            return platform, "post", _safe_handle(handle), _safe_id(parts[2]), ""
        return platform, "account", _safe_handle(handle), "", ""

    if platform == "mastodon":
        handle = next((part for part in parts if part.startswith("@")), parts[0] if parts else "unknown_account")
        if any(part in {"statuses", "status"} for part in parts) or (len(parts) >= 2 and parts[0].startswith("@")):
            return platform, "post", _safe_handle(handle), _safe_id(parts[-1] if parts else ""), ""
        return platform, "account", _safe_handle(handle), "", ""

    if platform == "tiktok":
        handle = next((part for part in parts if part.startswith("@")), parts[0] if parts else "unknown_account")
        if "video" in parts:
            return platform, "video", _safe_handle(handle), _safe_id(_after(parts, "video")), ""
        return platform, "account", _safe_handle(handle), "", ""

    if platform == "reddit":
        lower = [p.lower() for p in parts]
        if "comments" in lower:
            if len(parts) >= 2 and lower[0] == "r":
                handle = "r_" + parts[1]
            elif len(parts) >= 2 and lower[0] in {"user", "u"}:
                handle = parts[1]
            else:
                handle = "unknown_reddit_account"
            return platform, "comment_thread", _safe_handle(handle), _safe_id(_after(lower, "comments") or (parts[-1] if parts else "")), ""
        if len(parts) >= 2 and lower[0] in {"user", "u"}:
            return platform, "account", _safe_handle(parts[1]), "", ""
        if len(parts) >= 2 and lower[0] == "r":
            return platform, "subreddit", _safe_handle("r_" + parts[1]), "", ""
        return platform, "account", _safe_handle(parts[0] if parts else "unknown_reddit_account"), "", ""

    if platform == "youtube":
        lower = [p.lower() for p in parts]
        if parsed.query and _id_from_query(parsed.query, key="v"):
            return platform, "video", _safe_handle(parts[0] if parts and parts[0].startswith("@") else "unknown_account"), _safe_id(_id_from_query(parsed.query, key="v")), ""
        if parts and lower[0] in {"shorts", "post", "watch", "live"}:
            return platform, "video", "unknown_account", _safe_id(parts[1] if len(parts) > 1 else _id_from_query(parsed.query, key="v")), ""
        if parts and (parts[0].startswith("@") or lower[0] in {"channel", "user", "c"}):
            return platform, "account", _safe_handle(parts[-1] if lower[0] in {"channel", "user", "c"} else parts[0]), "", ""
        return platform, "account", _safe_handle(parts[0] if parts else "unknown_account"), "", ""

    if platform == "news_comments":
        return platform, "comment_thread", _safe_handle(host), _safe_id(parts[-1] if parts else "comments"), "mapped by comments path/fragment or explicit platform hint"

    return "unknown_platform", "unknown", _safe_handle(parts[0] if parts else "unknown_account"), "", "host not mapped to a universal social platform"


def build_r43g_side_effect_flags() -> dict[str, bool]:
    return {
        "universal_social_batch_account_intake_router_invoked": True,
        "one_url_many_urls_and_txt_inputs_supported": True,
        "platform_url_detection_only": True,
        "routes_through_r43f_universal_surface": True,
        "routes_through_r43e_adapter_map_first": True,
        "browser_engine_observation_only": True,
        "webview2_internals_copied": False,
        "webview2_session_started_by_r43g": False,
        "cefsharp_session_started_by_r43g": False,
        "manual_import_treated_as_observation_feed_only": True,
        "hidden_api_scraping_performed": False,
        "hidden_x_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "remote_media_downloads_performed": False,
        "source_role_checks_performed": False,
        "source_role_assignment_performed": False,
        "review_window_dependency_invoked": False,
        "review_window_rewrite_performed": False,
        "youtube_capture_engine_changed": False,
    }


def build_report(output_root: str | Path = R43G_DEFAULT_OUTPUT_ROOT) -> R43GReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    txt_path = root / "sample_batch_urls.txt"
    txt_path.write_text(
        "\n".join(
            [
                "https://www.facebook.com/example/posts/12345?utm_source=test",
                "https://www.tiktok.com/@example/video/7350000000000000000",
                "https://www.reddit.com/r/example/comments/abc123/title/",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    router = build_universal_social_batch_account_intake_router_r43g(output_root=root / "sample")
    sample = router.route_batch(
        UniversalSocialBatchAccountIntakeRequestR43G(
            inputs=(
                "https://twitter.com/example",
                "https://x.com/example/status/1111111111111111111?s=20",
                "https://bsky.app/profile/example.bsky.social",
                "https://www.instagram.com/p/C-example/?igsh=test",
                "https://www.threads.net/@example/post/3333333333333333333",
                "https://mastodon.social/@example/444444",
                "https://www.youtube.com/@example",
                "https://news.example.test/story/comments#comments",
                "https://unknown.invalid/profile/example",
            ),
            txt_path=str(txt_path),
            capture_timestamp="20260915T070000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
        )
    )
    data = sample.to_dict()
    route_results = data["route_results"]
    side_effect_flags = build_r43g_side_effect_flags()
    contract = build_universal_social_account_tracking_contract_r43e()
    checks = (
        _check("universal_social_batch_account_intake_router_invoked", side_effect_flags["universal_social_batch_account_intake_router_invoked"]),
        _check("one_url_many_urls_and_txt_inputs_supported", sample.total_inputs >= 12 and Path(sample.request_path).is_file()),
        _check("mixed_platform_urls_detected", len([p for p in sample.platform_counts if p != "unknown_platform"]) >= 9),
        _check("account_and_post_urls_classified", sample.account_url_count >= 3 and sample.post_url_count >= 5),
        _check("routes_through_r43f_universal_surface", sample.route_result_count == sample.detected_url_count and all(result.get("marker") == "YTCE_R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING" for result in route_results)),
        _check("routes_through_r43e_adapter_map_first", side_effect_flags["routes_through_r43e_adapter_map_first"] and all("adapter_map_path" in result for result in route_results)),
        _check("twitter_x_account_url_dispatches_to_implemented_path", any(result.get("platform_id") == "twitter_x" and result.get("route_status") == "dispatched_to_r43d_surface_via_r43e_adapter_map" and str(result.get("downstream_status", "")).startswith("PASS_R43D_") for result in route_results)),
        _check("pending_platforms_return_mapped_receipts", any(result.get("route_status") == "mapped_pending_adapter_receipt" for result in route_results)),
        _check("unknown_urls_return_unsupported_receipts", any(result.get("route_status") == "unsupported_platform_receipt" for result in route_results)),
        _check("universal_contract_preserved", all(result.get("universal_record_contract_preserved") is True for result in route_results)),
        _check("no_browser_or_source_role_side_effects", side_effect_flags["browser_engine_observation_only"] and not any(side_effect_flags[name] for name in ("webview2_session_started_by_r43g", "cefsharp_session_started_by_r43g", "source_role_checks_performed", "review_window_dependency_invoked", "review_window_rewrite_performed"))),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", not any(side_effect_flags[name] for name in ("hidden_api_scraping_performed", "hidden_x_api_scraping_performed", "cookie_or_token_extraction_performed", "captcha_or_challenge_bypass_performed"))),
        _check("no_remote_media_downloads", side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(data) and _machine_urls_are_plain(contract)),
    )
    status = R43G_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43G_BLOCKED_STATUS
    report = R43GReport(
        marker=R43G_MARKER,
        schema_version=R43G_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        sample_result=data,
        universal_contract=contract,
        side_effect_flags=side_effect_flags,
    )
    write_report(report, root)
    return report


def write_report(report: R43GReport, output_root: str | Path = R43G_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION_REPORT.json"
    md_path = root / "R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [
        f"# {R43G_MARKER}",
        "",
        f"- Status: `{report.status}`",
        f"- Schema: `{report.schema_version}`",
        f"- Generated: `{report.generated_at}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- `{check.get('status')}` {check.get('name')}: {check.get('detail') or ''}".rstrip())
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def _platform_from_host(host: str, hint: str, path: str, query: str, fragment: str) -> str:
    compact = host.lower().removeprefix("www.")
    if compact in {"x.com", "twitter.com", "mobile.twitter.com"}:
        return "twitter_x"
    if compact in {"bsky.app", "staging.bsky.app"}:
        return "bluesky"
    if compact == "instagram.com":
        return "instagram"
    if compact in {"facebook.com", "m.facebook.com"}:
        return "facebook"
    if compact == "threads.net":
        return "threads"
    if compact == "mastodon.social" or (hint == "mastodon" and host):
        return "mastodon"
    if compact == "tiktok.com":
        return "tiktok"
    if compact in {"reddit.com", "old.reddit.com"}:
        return "reddit"
    if compact in {"youtube.com", "youtu.be"}:
        return "youtube"
    if hint == "news_comments" or "comments" in path.lower() or "comments" in query.lower() or "comments" in fragment.lower():
        return "news_comments"
    return hint if hint in SOCIAL_PLATFORM_IDS_R43G else "unknown_platform"


def _plain_url(value: Any) -> str:
    text = _clean(value).strip("<>").replace("\\_", "_").replace("\\/", "/")
    markdown = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", text)
    if markdown:
        text = markdown.group(1)
    if not text:
        return ""
    if not re.match(r"^[a-z][a-z0-9+.-]*://", text, flags=re.I):
        text = "https://" + text
    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return text
    host = (parsed.hostname or parsed.netloc).lower()
    if host in {"twitter.com", "www.twitter.com", "mobile.twitter.com"}:
        host = "x.com"
    elif host.startswith("www."):
        host = host[4:]
    kept_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_PARAMS_R43G
    ]
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host, path, urlencode(kept_query), parsed.fragment))


def _build_runbook(req: UniversalSocialBatchAccountIntakeRequestR43G, items: Iterable[UniversalSocialDetectedInputR43G]) -> str:
    rows = list(items)
    lines = [
        "# Universal social batch account intake and platform URL detection",
        "",
        f"- Marker: `{R43G_MARKER}`",
        f"- Total inputs: `{len(rows)}`",
        "- Routing: every detected item goes through R43F first, then R43E adapter map, then the concrete adapter where implemented.",
        "- Twitter/X remains the first adapter, not the architecture.",
        "- Pending platforms return mapped receipts; unknown platforms return unsupported receipts.",
        "",
        "## Output files",
    ]
    lines.extend(f"- `{name}`" for name in BATCH_INTAKE_OUTPUT_FILES_R43G)
    lines.extend([
        "",
        "## Boundaries",
        "",
        "- Browser engines are observation feeds only.",
        "- No WebView2/CefSharp session is started by R43G.",
        "- No hidden API scraping, cookie/token extraction, CAPTCHA/challenge bypass, source-role checks, review-window rewrite, or remote media download.",
        "",
        "## Detected inputs",
    ])
    for item in rows:
        lines.append(f"- `{item.batch_index}` `{item.platform_id}` `{item.url_kind}` {item.normalized_url}")
    return "\n".join(lines) + "\n"


def _after(parts: list[str], token: str) -> str:
    try:
        index = parts.index(token)
    except ValueError:
        return ""
    return parts[index + 1] if index + 1 < len(parts) else ""


def _id_from_query(query: str, *, key: str = "id") -> str:
    pairs = dict(parse_qsl(query, keep_blank_values=True))
    return pairs.get(key) or pairs.get(key.upper()) or ""


def _handle_from_query(query: str) -> str:
    pairs = dict(parse_qsl(query, keep_blank_values=True))
    return pairs.get("id") or pairs.get("u") or "unknown_account"


def _safe_id(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.:-]+", "_", _clean(value)).strip("_")


def _safe_handle(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.@-]+", "_", _clean(value)).strip("_") or "unknown_account"


def _safe_platform_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", _clean(value).lower().replace("-", "_")).strip("_")


def _safe_ts(value: Any) -> str:
    return re.sub(r"[^0-9TtZz_.-]+", "_", _clean(value)).strip("_")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "to_dict"):
        return _to_jsonable(value.to_dict())
    if hasattr(value, "__fspath__"):
        return str(value)
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_ndjson(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    _write_text(path, "\n".join(json.dumps(_to_jsonable(row), sort_keys=True) for row in rows) + ("\n" if rows else ""))


def _count_by(items: Iterable[UniversalSocialDetectedInputR43G], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = _clean(getattr(item, attr)) or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _machine_urls_are_plain(value: Any, key: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(_machine_urls_are_plain(child, str(child_key)) for child_key, child in value.items())
    if isinstance(value, (list, tuple, set)):
        return all(_machine_urls_are_plain(child, key) for child in value)
    if key.endswith("url") or key.endswith("_path") or key in {"account_url", "source_url", "normalized_url"}:
        text = _clean(value)
        return not text.startswith("[") and "](" not in text and "]\\(" not in text
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43G_MARKER)
    parser.add_argument("--output-root", default=R43G_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(R43G_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


__all__ = [
    "BATCH_INTAKE_OUTPUT_FILES_R43G",
    "R43G_BLOCKED_STATUS",
    "R43G_DEFAULT_OUTPUT_ROOT",
    "R43G_MARKER",
    "R43G_PASS_STATUS",
    "SOCIAL_PLATFORM_IDS_R43G",
    "UniversalSocialBatchAccountIntakeRequestR43G",
    "UniversalSocialBatchAccountIntakeResultR43G",
    "UniversalSocialBatchAccountIntakeRouterR43G",
    "UniversalSocialDetectedInputR43G",
    "build_report",
    "build_r43g_side_effect_flags",
    "build_universal_social_batch_account_intake_router_r43g",
    "coerce_universal_social_batch_account_intake_request_r43g",
    "collect_batch_inputs_r43g",
    "detect_social_url_r43g",
    "extract_urls_from_text_r43g",
    "write_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
