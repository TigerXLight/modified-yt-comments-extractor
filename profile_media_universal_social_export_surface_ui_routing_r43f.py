from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from profile_media_universal_social_account_tracking_r43e import (
    R43E_PASS_STATUS,
    UniversalSocialAccountTrackingRegistryR43E,
    UniversalSocialAccountTrackingRequestR43E,
    build_universal_social_account_tracking_contract_r43e,
    build_universal_social_account_tracking_registry_r43e,
)

R43F_MARKER = "YTCE_R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING"
R43F_PASS_STATUS = "PASS_R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING"
R43F_BLOCKED_STATUS = "BLOCKED_R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING"
R43F_SCHEMA_VERSION = "universal_social_export_surface_ui_routing.r43f.v1"
R43F_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43f_universal_social_export_surface_ui_routing"
R43F_MODE_ID = "universal_social_export_surface_ui_routing"

UNIVERSAL_EXPORT_FILES_R43F: tuple[str, ...] = (
    "account_record.md",
    "account_timeline.ndjson",
    "media_index.json",
    "progress_events.ndjson",
    "screenshot_receipts_index.json",
    "account_tracking_request.json",
    "account_tracking_runbook.md",
    "account_tracking_surface_receipt.json",
    "adapter_map.json",
    "universal_routing_receipt.json",
)

PENDING_CONTRACT_PLATFORMS_R43F = {
    "instagram",
    "facebook",
    "threads",
    "mastodon",
    "tiktok",
    "youtube",
    "news_comments",
}

TRACKING_QUERY_PARAMS_R43F = {"fbclid", "gclid", "igsh", "mc_cid", "mc_eid", "ref_src", "s", "si"}


@dataclass(frozen=True)
class UniversalSocialExportSurfaceRequestR43F:
    platform_id: str = ""
    account_url: str = ""
    account_handle: str = ""
    include_posts: bool = True
    include_reposts_or_reshares: bool = True
    include_quotes: bool = True
    include_replies: bool = False
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    capture_timestamp: str = ""
    output_root: str = R43F_DEFAULT_OUTPUT_ROOT
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
class UniversalSocialExportSurfaceRouteResultR43F:
    marker: str
    schema_version: str
    status: str
    route_status: str
    platform_id: str
    adapter_status: str
    account_url: str
    account_handle: str
    capture_timestamp: str
    run_dir: str
    request_path: str
    runbook_path: str
    surface_receipt_path: str
    adapter_map_path: str
    universal_routing_receipt_path: str
    account_record_path: str
    account_timeline_path: str
    media_index_path: str
    progress_events_path: str
    screenshot_receipts_index_path: str
    downstream_marker: str = ""
    downstream_status: str = ""
    downstream_receipt_path: str = ""
    downstream_result: Mapping[str, Any] = field(default_factory=dict)
    universal_record_contract_preserved: bool = True
    screenshot_receipt_gate_required_when_requested: bool = True
    browser_engine_observation_only: bool = True
    no_source_role_or_review_window_side_effects: bool = True
    no_webview2_internal_copy_or_tracking_side_effects: bool = True
    no_remote_media_downloads: bool = True
    plain_machine_urls: bool = True
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43F_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43FReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_results: tuple[Mapping[str, Any], ...]
    adapter_map: Mapping[str, Any]
    universal_contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43F_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_map": _to_jsonable(self.adapter_map),
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "sample_results": [_to_jsonable(item) for item in self.sample_results],
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
            "universal_contract": _to_jsonable(self.universal_contract),
        }


class UniversalSocialExportSurfaceRouterR43F:
    """UI/export routing surface for platform-neutral social account requests.

    R43F is intentionally thin.  It accepts the user-facing platform-neutral
    request shape, resolves the platform through the R43E adapter map first, and
    dispatches to the concrete platform adapter only where one exists.  Browser
    engines are observation feeds below platform adapters; this router does not
    start or copy WebView2/CefSharp internals.
    """

    def __init__(
        self,
        *,
        registry: UniversalSocialAccountTrackingRegistryR43E | None = None,
        output_root: str | Path = R43F_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.output_root = Path(output_root)
        self.registry = registry or build_universal_social_account_tracking_registry_r43e(output_root=self.output_root / "r43e_registry")

    def adapter_map_dict(self) -> dict[str, Any]:
        adapter_map = dict(self.registry.adapter_map_dict())
        contract = build_universal_social_account_tracking_contract_r43e()
        for platform_id in contract.get("platforms", []):
            safe_platform = _safe_platform_id(platform_id)
            if safe_platform and safe_platform not in adapter_map:
                adapter_map[safe_platform] = _pending_contract_adapter_entry(safe_platform)
        return adapter_map

    def route_account_tracking_export(
        self,
        request: UniversalSocialExportSurfaceRequestR43F | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> UniversalSocialExportSurfaceRouteResultR43F:
        req = coerce_universal_social_export_surface_request_r43f(request, **overrides)
        contract = build_universal_social_account_tracking_contract_r43e()
        adapter_map = self.adapter_map_dict()
        platform = _safe_platform_id(req.platform_id or self.registry.detect_platform_id(req.account_url, req.platform_id))
        if not platform or platform == "unknown_platform":
            platform = _safe_platform_id(req.platform_id) or self.registry.detect_platform_id(req.account_url, req.platform_id)
        adapter = adapter_map.get(platform)
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        handle = _safe_handle(req.account_handle or _handle_from_url(req.account_url) or "unknown_account")
        account_url = _plain_url(req.account_url or _default_account_url(platform, handle))
        run_dir = Path(req.output_root or self.output_root) / platform / handle / f"universal_social_export_surface_{capture_ts}"
        run_dir.mkdir(parents=True, exist_ok=True)

        request_path = run_dir / "account_tracking_request.json"
        runbook_path = run_dir / "account_tracking_runbook.md"
        receipt_path = run_dir / "account_tracking_surface_receipt.json"
        adapter_map_path = run_dir / "adapter_map.json"
        universal_receipt_path = run_dir / "universal_routing_receipt.json"
        account_record_path = run_dir / "account_record.md"
        account_timeline_path = run_dir / "account_timeline.ndjson"
        media_index_path = run_dir / "media_index.json"
        progress_events_path = run_dir / "progress_events.ndjson"
        screenshot_receipts_path = run_dir / "screenshot_receipts_index.json"

        request_payload = {
            **req.to_dict(),
            "account_handle": handle,
            "account_url": account_url,
            "capture_timestamp": capture_ts,
            "marker": R43F_MARKER,
            "platform_id": platform,
            "schema_version": R43F_SCHEMA_VERSION,
        }
        _write_json(request_path, request_payload)
        _write_json(adapter_map_path, adapter_map)

        downstream_payload: dict[str, Any] = {}
        downstream_status = ""
        downstream_marker = ""
        downstream_receipt_path = ""
        warnings: list[str] = []
        route_status = ""
        adapter_status = _clean(adapter.get("adapter_status")) if adapter else "unsupported_platform"

        if platform in {"twitter_x", "bluesky", "reddit"} and adapter:
            r43e_request = UniversalSocialAccountTrackingRequestR43E(
                platform_id=platform,
                account_url=account_url,
                account_handle=handle,
                capture_timestamp=capture_ts,
                include_posts=req.include_posts,
                include_reposts=req.include_reposts_or_reshares,
                include_quote_posts=req.include_quotes,
                include_replies=req.include_replies,
                include_media=req.include_media,
                include_static_screenshots=req.include_static_screenshots,
                require_screenshot_receipts=req.require_screenshot_receipts,
                output_root=str(run_dir / "r43e_dispatch"),
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
            r43e_result = self.registry.run_account_export(r43e_request)
            downstream_payload = r43e_result.to_dict()
            downstream_status = r43e_result.downstream_status
            downstream_marker = _clean(downstream_payload.get("marker"))
            downstream_receipt_path = r43e_result.receipt_path
            if platform == "twitter_x":
                route_status = "dispatched_to_r43d_surface_via_r43e_adapter_map"
            elif platform == "bluesky":
                route_status = "dispatched_to_bluesky_adapter_via_r43e_adapter_map"
            else:
                route_status = "dispatched_to_reddit_adapter_via_r43e_adapter_map"
            if r43e_result.status != R43E_PASS_STATUS:
                warnings.append(f"R43E registry returned {r43e_result.status}.")
            _write_pointer_account_record(account_record_path, platform, handle, account_url, r43e_result.account_record_path)
            _write_pointer_timeline(account_timeline_path, platform, handle, account_url, r43e_result.downstream_result)
            _write_json(media_index_path, _pointer_index("media_index", r43e_result.media_index_path, r43e_result.media_count))
            _write_progress(progress_events_path, route_status, downstream_status)
            _write_json(screenshot_receipts_path, _pointer_index("screenshot_receipts_index", r43e_result.screenshot_receipts_index_path, r43e_result.screenshot_count))
        elif adapter:
            route_status = "mapped_pending_adapter_receipt"
            downstream_status = "contract_only_adapter_pending"
            warnings.append(f"{platform} is mapped through R43E but has no R43F concrete export adapter yet.")
            _write_pending_contract_files(
                run_dir=run_dir,
                request_payload=request_payload,
                adapter=adapter,
                route_status=route_status,
            )
        else:
            route_status = "unsupported_platform_receipt"
            downstream_status = "unsupported_platform"
            adapter_status = "unsupported_platform"
            warnings.append(f"{platform!r} is not in the R43E adapter map or contract platform list.")
            _write_unsupported_contract_files(run_dir=run_dir, request_payload=request_payload, route_status=route_status)

        _write_text(runbook_path, _build_runbook(request_payload, adapter, route_status, downstream_status))

        side_effect_flags = build_r43f_side_effect_flags()
        result = UniversalSocialExportSurfaceRouteResultR43F(
            marker=R43F_MARKER,
            schema_version=R43F_SCHEMA_VERSION,
            status=R43F_PASS_STATUS,
            route_status=route_status,
            platform_id=platform,
            adapter_status=adapter_status,
            account_url=account_url,
            account_handle=handle,
            capture_timestamp=capture_ts,
            run_dir=str(run_dir),
            request_path=str(request_path),
            runbook_path=str(runbook_path),
            surface_receipt_path=str(receipt_path),
            adapter_map_path=str(adapter_map_path),
            universal_routing_receipt_path=str(universal_receipt_path),
            account_record_path=str(account_record_path),
            account_timeline_path=str(account_timeline_path),
            media_index_path=str(media_index_path),
            progress_events_path=str(progress_events_path),
            screenshot_receipts_index_path=str(screenshot_receipts_path),
            downstream_marker=downstream_marker,
            downstream_status=downstream_status,
            downstream_receipt_path=downstream_receipt_path,
            downstream_result=downstream_payload,
            universal_record_contract_preserved=True,
            screenshot_receipt_gate_required_when_requested=bool(req.require_screenshot_receipts),
            browser_engine_observation_only=side_effect_flags["browser_engine_observation_only"],
            no_source_role_or_review_window_side_effects=not (
                side_effect_flags["source_role_checks_performed"]
                or side_effect_flags["review_window_dependency_invoked"]
                or side_effect_flags["review_window_rewrite_performed"]
            ),
            no_webview2_internal_copy_or_tracking_side_effects=not (
                side_effect_flags["webview2_internals_copied"]
                or side_effect_flags["webview2_session_started_by_r43f"]
            ),
            no_remote_media_downloads=not side_effect_flags["remote_media_downloads_performed"],
            plain_machine_urls=_machine_urls_are_plain(
                {
                    "request": request_payload,
                    "adapter_map": adapter_map,
                    "contract": contract,
                    "downstream": downstream_payload,
                }
            ),
            warnings=tuple(warnings),
        )
        _write_json(receipt_path, result.to_dict())
        _write_json(universal_receipt_path, {"routing_result": result.to_dict(), "universal_contract": contract})
        return result


def build_universal_social_export_surface_router_r43f(
    *,
    registry: UniversalSocialAccountTrackingRegistryR43E | None = None,
    output_root: str | Path = R43F_DEFAULT_OUTPUT_ROOT,
) -> UniversalSocialExportSurfaceRouterR43F:
    return UniversalSocialExportSurfaceRouterR43F(registry=registry, output_root=output_root)


def coerce_universal_social_export_surface_request_r43f(
    request: UniversalSocialExportSurfaceRequestR43F | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> UniversalSocialExportSurfaceRequestR43F:
    if isinstance(request, UniversalSocialExportSurfaceRequestR43F):
        data = request.to_dict()
    elif isinstance(request, Mapping):
        data = dict(request)
    else:
        data = {}
    for key, value in overrides.items():
        if value not in (None, ""):
            data[key] = value
    if "include_reposts" in data and "include_reposts_or_reshares" not in data:
        data["include_reposts_or_reshares"] = data["include_reposts"]
    if "include_quote_posts" in data and "include_quotes" not in data:
        data["include_quotes"] = data["include_quote_posts"]
    return UniversalSocialExportSurfaceRequestR43F(
        platform_id=_safe_platform_id(data.get("platform_id")),
        account_url=_plain_url(data.get("account_url") or ""),
        account_handle=_safe_handle(data.get("account_handle") or ""),
        include_posts=bool(data.get("include_posts", True)),
        include_reposts_or_reshares=bool(data.get("include_reposts_or_reshares", True)),
        include_quotes=bool(data.get("include_quotes", True)),
        include_replies=bool(data.get("include_replies", False)),
        include_media=bool(data.get("include_media", True)),
        include_static_screenshots=bool(data.get("include_static_screenshots", True)),
        require_screenshot_receipts=bool(data.get("require_screenshot_receipts", True)),
        capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""),
        output_root=_clean(data.get("output_root") or R43F_DEFAULT_OUTPUT_ROOT),
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


def build_r43f_side_effect_flags() -> dict[str, bool]:
    return {
        "universal_social_export_surface_router_invoked": True,
        "routes_through_r43e_adapter_map_first": True,
        "browser_engine_observation_only": True,
        "webview2_internals_copied": False,
        "webview2_session_started_by_r43f": False,
        "cefsharp_session_started_by_r43f": False,
        "manual_import_treated_as_observation_feed_only": True,
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


def build_report(output_root: str | Path = R43F_DEFAULT_OUTPUT_ROOT) -> R43FReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    router = build_universal_social_export_surface_router_r43f(output_root=root / "sample")
    twitter = router.route_account_tracking_export(
        UniversalSocialExportSurfaceRequestR43F(
            platform_id="twitter_x",
            account_url="https://x.com/example",
            account_handle="example",
            capture_timestamp="20260915T050000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
        )
    )
    bluesky = router.route_account_tracking_export(
        UniversalSocialExportSurfaceRequestR43F(
            platform_id="bluesky",
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260915T050010Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
            max_items=5,
        )
    )
    pending_results = [
        router.route_account_tracking_export(
            UniversalSocialExportSurfaceRequestR43F(
                platform_id=platform,
                account_url=_default_account_url(platform, "example"),
                account_handle="example",
                capture_timestamp=f"20260915T0500{index:02d}Z",
                output_root=str(root / "sample"),
            )
        )
        for index, platform in enumerate(("instagram", "facebook", "threads", "mastodon", "tiktok", "youtube", "news_comments"), start=1)
    ]
    unknown = router.route_account_tracking_export(
        UniversalSocialExportSurfaceRequestR43F(
            platform_id="unknown_social",
            account_url="https://example.invalid/account",
            account_handle="example",
            capture_timestamp="20260915T050099Z",
            output_root=str(root / "sample"),
        )
    )
    sample_results = (twitter, bluesky, *pending_results, unknown)
    adapter_map = router.adapter_map_dict()
    contract = build_universal_social_account_tracking_contract_r43e()
    side_effect_flags = build_r43f_side_effect_flags()
    checks = (
        _check("universal_social_export_surface_router_invoked", side_effect_flags["universal_social_export_surface_router_invoked"]),
        _check("routes_through_r43e_adapter_map_first", side_effect_flags["routes_through_r43e_adapter_map_first"] and "twitter_x" in adapter_map),
        _check("twitter_x_dispatches_to_r43d_surface", twitter.route_status == "dispatched_to_r43d_surface_via_r43e_adapter_map" and twitter.downstream_status.startswith("PASS_R43D_")),
        _check("bluesky_dispatches_to_r43v_adapter", bluesky.route_status in {"dispatched_to_r43v_adapter_via_r43e_adapter_map", "dispatched_to_bluesky_adapter_via_r43e_adapter_map"} and bluesky.downstream_status.startswith("PASS_R43V_")),
        _check("pending_platforms_return_mapped_receipts_not_crashes", all(result.route_status == "mapped_pending_adapter_receipt" and result.status == R43F_PASS_STATUS for result in pending_results)),
        _check("unknown_platform_returns_unsupported_receipt", unknown.route_status == "unsupported_platform_receipt" and unknown.downstream_status == "unsupported_platform"),
        _check("universal_record_contract_preserved", all(result.universal_record_contract_preserved for result in sample_results)),
        _check("screenshot_receipt_gate_required_when_requested", all(result.screenshot_receipt_gate_required_when_requested for result in sample_results)),
        _check("browser_engine_observation_only", side_effect_flags["browser_engine_observation_only"]),
        _check("no_source_role_or_review_window_side_effects", not any(side_effect_flags[name] for name in ("source_role_checks_performed", "source_role_assignment_performed", "review_window_dependency_invoked", "review_window_rewrite_performed"))),
        _check("no_webview2_internal_copy_or_tracking_side_effects", not any(side_effect_flags[name] for name in ("webview2_internals_copied", "webview2_session_started_by_r43f", "cefsharp_session_started_by_r43f"))),
        _check("no_remote_media_downloads", side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", all(result.plain_machine_urls for result in sample_results) and _machine_urls_are_plain({"adapter_map": adapter_map, "contract": contract})),
    )
    status = R43F_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43F_BLOCKED_STATUS
    report = R43FReport(
        marker=R43F_MARKER,
        schema_version=R43F_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        sample_results=tuple(result.to_dict() for result in sample_results),
        adapter_map=adapter_map,
        universal_contract=contract,
        side_effect_flags=side_effect_flags,
    )
    write_report(report, root)
    return report


def write_report(report: R43FReport, output_root: str | Path = R43F_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING_REPORT.json"
    md_path = root / "R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [
        f"# {R43F_MARKER}",
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


def _pending_contract_adapter_entry(platform_id: str) -> dict[str, Any]:
    return {
        "account_record_kind": "social_account",
        "account_url_examples": [_default_account_url(platform_id, "example")],
        "adapter_status": "mapped_contract_adapter_pending",
        "capabilities": [
            "account_record_md",
            "date_folder_export_map",
            "post_repost_quote_reply_record_model",
            "media_index",
            "static_screenshot_receipt_gate",
            "progress_pause_recovery_events",
            "local_tracking_dedupe_ledger_layer",
            "no_source_role_or_review_window_dependency",
        ],
        "display_name": platform_id.replace("_", " ").title(),
        "export_surface_attribute": "",
        "implementation_module": "",
        "notes": "Declared in the R43E universal contract; concrete adapter remains pending.",
        "planned_from_twitter_x_contract": True,
        "platform_id": platform_id,
        "record_type_map": {"post": "post", "reshare": "repost_or_reshare", "quote": "quote", "reply": "reply"},
        "url_hosts": [_default_host(platform_id)],
    }


def _write_pending_contract_files(*, run_dir: Path, request_payload: Mapping[str, Any], adapter: Mapping[str, Any], route_status: str) -> None:
    _write_text(run_dir / "account_record.md", _pending_account_record(request_payload, adapter, route_status))
    _write_text(run_dir / "account_timeline.ndjson", "")
    _write_json(run_dir / "media_index.json", {"media": [], "route_status": route_status, "promotion_status": "not_promoted_pending_adapter_receipt_only"})
    _write_progress(run_dir / "progress_events.ndjson", route_status, "contract_only_adapter_pending")
    _write_json(run_dir / "screenshot_receipts_index.json", {"screenshots": [], "receipt_gate": "required_when_requested", "route_status": route_status})


def _write_unsupported_contract_files(*, run_dir: Path, request_payload: Mapping[str, Any], route_status: str) -> None:
    adapter = {"display_name": "Unsupported platform", "adapter_status": "unsupported_platform"}
    _write_text(run_dir / "account_record.md", _pending_account_record(request_payload, adapter, route_status))
    _write_text(run_dir / "account_timeline.ndjson", "")
    _write_json(run_dir / "media_index.json", {"media": [], "route_status": route_status, "promotion_status": "unsupported_platform_no_promotion"})
    _write_progress(run_dir / "progress_events.ndjson", route_status, "unsupported_platform")
    _write_json(run_dir / "screenshot_receipts_index.json", {"screenshots": [], "receipt_gate": "required_when_requested", "route_status": route_status})


def _write_pointer_account_record(path: Path, platform: str, handle: str, account_url: str, downstream_account_record: str) -> None:
    lines = [
        "# Universal social account export surface",
        "",
        f"- Platform: `{platform}`",
        f"- Account: `{handle}`",
        f"- Account URL: {account_url}",
        f"- Downstream account record: `{downstream_account_record}`",
        "- Source-role/review-window routing: not invoked by R43F",
        "- Browser engine: observation feed only",
    ]
    _write_text(path, "\n".join(lines) + "\n")


def _write_pointer_timeline(path: Path, platform: str, handle: str, account_url: str, downstream_payload: Mapping[str, Any]) -> None:
    row = {
        "account_handle": handle,
        "account_url": account_url,
        "downstream_status": _clean(downstream_payload.get("status")),
        "platform_id": platform,
        "record_count": downstream_payload.get("record_count", 0),
        "route": "r43e_to_r43d",
    }
    _write_text(path, json.dumps(row, sort_keys=True) + "\n")


def _pointer_index(kind: str, downstream_path: str, count: int) -> dict[str, Any]:
    return {
        "count": count,
        "downstream_path": downstream_path,
        "kind": kind,
        "promotion_status": "not_promoted_universal_route_pointer_only",
    }


def _write_progress(path: Path, route_status: str, downstream_status: str) -> None:
    rows = [
        {
            "event": "universal_social_export_surface_routing",
            "route_status": route_status,
            "downstream_status": downstream_status,
            "webview2_session_started": False,
            "remote_media_downloads": False,
        }
    ]
    _write_text(path, "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")


def _pending_account_record(request_payload: Mapping[str, Any], adapter: Mapping[str, Any], route_status: str) -> str:
    return "\n".join(
        [
            "# Universal social account export surface",
            "",
            f"- Platform: `{request_payload.get('platform_id')}`",
            f"- Adapter: `{adapter.get('display_name')}`",
            f"- Route status: `{route_status}`",
            f"- Account: `{request_payload.get('account_handle')}`",
            f"- Account URL: {request_payload.get('account_url')}",
            "- Concrete adapter: pending",
            "- This is a mapped receipt, not captured evidence.",
            "- Source-role/review-window routing: not invoked by R43F",
            "- Browser engine: observation feed only",
            "",
        ]
    )


def _build_runbook(request_payload: Mapping[str, Any], adapter: Mapping[str, Any] | None, route_status: str, downstream_status: str) -> str:
    lines = [
        "# Universal social export surface UI routing runbook",
        "",
        f"- Marker: `{R43F_MARKER}`",
        f"- Platform: `{request_payload.get('platform_id')}`",
        f"- Account: `{request_payload.get('account_handle')}`",
        f"- Account URL: {request_payload.get('account_url')}",
        f"- Route status: `{route_status}`",
        f"- Downstream status: `{downstream_status}`",
        "",
        "## Universal output contract",
        "",
    ]
    lines.extend(f"- `{name}`" for name in UNIVERSAL_EXPORT_FILES_R43F)
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Route through R43E adapter map first.",
            "- WebView2/CefSharp/manual import are observation feeds only.",
            "- No WebView2 internals are copied and no browser session is started by R43F.",
            "- No cookie/token extraction, hidden X API scraping, CAPTCHA/challenge bypass, source-role checks, review-window rewrite, or remote media download.",
        ]
    )
    if adapter:
        lines.extend(["", "## Adapter", "", f"- Status: `{adapter.get('adapter_status')}`", f"- Module: `{adapter.get('implementation_module') or 'pending'}`"])
    return "\n".join(lines) + "\n"


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


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


def _safe_platform_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", _clean(value).lower().replace("-", "_")).strip("_")


def _safe_handle(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.@-]+", "_", _clean(value)).strip("_") or "unknown_account"


def _safe_ts(value: Any) -> str:
    return re.sub(r"[^0-9TtZz_.-]+", "_", _clean(value)).strip("_")


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _plain_url(value: Any) -> str:
    text = _clean(value).strip("<>")
    markdown = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", text)
    if markdown:
        text = markdown.group(1)
    if not text:
        return ""
    if not re.match(r"^[a-z][a-z0-9+.-]*://", text, flags=re.I):
        text = "https://" + text
    parsed = urlsplit(text.replace("\\_", "_").replace("\\/", "/"))
    if not parsed.scheme or not parsed.netloc:
        return text
    host = (parsed.hostname or parsed.netloc).lower()
    if host in {"twitter.com", "www.twitter.com"}:
        host = "x.com"
    elif host.startswith("www."):
        host = host[4:]
    kept_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_PARAMS_R43F
    ]
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host, path, urlencode(kept_query), ""))


def _handle_from_url(url: str) -> str:
    path = [part for part in urlsplit(_plain_url(url)).path.split("/") if part]
    if not path:
        return ""
    if path[0].startswith("@"):
        return path[0]
    if path[0] in {"user", "profile", "c"} and len(path) > 1:
        return path[1]
    return path[0]


def _default_host(platform: str) -> str:
    return {
        "bluesky": "bsky.app",
        "instagram": "instagram.com",
        "facebook": "facebook.com",
        "threads": "threads.net",
        "mastodon": "mastodon.social",
        "tiktok": "tiktok.com",
        "reddit": "reddit.com",
        "youtube": "youtube.com",
        "news_comments": "example.com",
        "twitter_x": "x.com",
    }.get(platform, "example.invalid")


def _default_account_url(platform: str, handle: str) -> str:
    handle = _safe_handle(handle)
    if platform == "twitter_x":
        return f"https://x.com/{handle.lstrip('@')}"
    if platform == "bluesky":
        return f"https://bsky.app/profile/{handle.lstrip('@') or 'example.bsky.social'}"
    if platform == "instagram":
        return f"https://instagram.com/{handle.lstrip('@')}"
    if platform == "facebook":
        return f"https://facebook.com/{handle.lstrip('@')}"
    if platform == "threads":
        return f"https://threads.net/@{handle.lstrip('@')}"
    if platform == "mastodon":
        return f"https://mastodon.social/@{handle.lstrip('@')}"
    if platform == "tiktok":
        return f"https://tiktok.com/@{handle.lstrip('@')}"
    if platform == "reddit":
        return f"https://reddit.com/user/{handle.lstrip('@')}"
    if platform == "youtube":
        return f"https://youtube.com/@{handle.lstrip('@')}"
    if platform == "news_comments":
        return f"https://example.com/users/{handle.lstrip('@')}"
    return f"https://example.invalid/{handle.lstrip('@')}"


def _machine_urls_are_plain(value: Any, key: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(_machine_urls_are_plain(child, str(child_key)) for child_key, child in value.items())
    if isinstance(value, (list, tuple, set)):
        return all(_machine_urls_are_plain(child, key) for child in value)
    if key.endswith("url") or key.endswith("_path") or key in {"account_url", "source_url"}:
        text = _clean(value)
        return not text.startswith("[") and "](" not in text and "]\\(" not in text
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43F_MARKER)
    parser.add_argument("--output-root", default=R43F_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(R43F_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


__all__ = [
    "R43F_BLOCKED_STATUS",
    "R43F_DEFAULT_OUTPUT_ROOT",
    "R43F_MARKER",
    "R43F_PASS_STATUS",
    "UNIVERSAL_EXPORT_FILES_R43F",
    "UniversalSocialExportSurfaceRequestR43F",
    "UniversalSocialExportSurfaceRouteResultR43F",
    "UniversalSocialExportSurfaceRouterR43F",
    "build_report",
    "build_r43f_side_effect_flags",
    "build_universal_social_export_surface_router_r43f",
    "coerce_universal_social_export_surface_request_r43f",
    "write_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
