from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

R43E_MARKER = "YTCE_R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP"
R43E_PASS_STATUS = "PASS_R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP"
R43E_BLOCKED_STATUS = "BLOCKED_R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP"
R43E_SCHEMA_VERSION = "universal_social_account_tracking_contract_adapter_map.r43e.v1"
R43E_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43e_universal_social_account_tracking_contract_adapter_map"
R43E_MODE_ID = "universal_social_account_tracking_contract_adapter_map"

UNIVERSAL_RECORD_TYPES_R43E = (
    "account",
    "post",
    "repost_or_reshare",
    "quote",
    "reply",
    "thread_context",
    "media_image",
    "media_video",
    "media_manifest",
    "media_segment",
    "static_screenshot",
    "screenshot_receipt",
    "progress_event",
    "pause_event",
    "recovery_event",
)

UNIVERSAL_OUTPUT_FILES_R43E = (
    "account_tracking_request.json",
    "account_tracking_runbook.md",
    "account_tracking_surface_receipt.json",
    "adapter_map.json",
    "account_record.md",
    "account_timeline.ndjson",
    "media_index.json",
    "progress_events.ndjson",
    "screenshot_receipts_index.json",
)


@dataclass(frozen=True)
class UniversalSocialPlatformAdapterR43E:
    platform_id: str
    display_name: str
    url_hosts: tuple[str, ...]
    adapter_status: str
    account_url_examples: tuple[str, ...] = ()
    implementation_module: str = ""
    export_surface_attribute: str = ""
    account_record_kind: str = "social_account"
    record_type_map: Mapping[str, str] = field(default_factory=dict)
    capabilities: tuple[str, ...] = ()
    planned_from_twitter_x_contract: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialAccountTrackingRequestR43E:
    platform_id: str = ""
    account_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    include_posts: bool = True
    include_reposts: bool = True
    include_quote_posts: bool = True
    include_replies: bool = False
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    output_root: str = R43E_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""
    max_items: int = 3
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialAccountTrackingResultR43E:
    marker: str
    schema_version: str
    status: str
    platform_id: str
    adapter_status: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    run_dir: str
    request_path: str
    runbook_path: str
    adapter_map_path: str
    receipt_path: str
    downstream_status: str
    downstream_result: Mapping[str, Any]
    account_record_path: str
    manifest_path: str
    media_index_path: str
    screenshot_receipts_index_path: str
    record_count: int
    media_count: int
    screenshot_count: int
    date_folders: tuple[str, ...]
    universal_contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43E_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43EReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    universal_contract: Mapping[str, Any]
    adapter_map: Mapping[str, Any]
    sample_result: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43E_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_map": _to_jsonable(self.adapter_map),
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "sample_result": _to_jsonable(self.sample_result),
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
            "universal_contract": _to_jsonable(self.universal_contract),
        }


class UniversalSocialAccountTrackingRegistryR43E:
    """Platform-neutral account tracking registry.

    R43E makes the Twitter/X account tracker the first adapter implementation,
    not the architecture itself.  The shared account/post/repost/quote/reply/
    media/screenshot/progress contracts are kept in this local layer so Bluesky,
    Instagram, Facebook, Threads, Mastodon, TikTok, Reddit and later platforms
    can map into the same export surface without duplicating the whole system.

    Browser engines remain observation inputs only.  WebView2 internals are not
    copied.  The tracking, dedupe, folder routing, account_record.md generation,
    date-folder export map, screenshot receipts, and progress/pause/recovery
    state stay in local Python/app code.
    """

    def __init__(
        self,
        *,
        adapters: Mapping[str, UniversalSocialPlatformAdapterR43E] | None = None,
        twitter_x_surface: Any | None = None,
        output_root: str | Path = R43E_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.adapters: dict[str, UniversalSocialPlatformAdapterR43E] = dict(adapters or build_default_platform_adapter_map_r43e())
        self.twitter_x_surface = twitter_x_surface
        self.output_root = Path(output_root)

    def adapter_map_dict(self) -> dict[str, dict[str, Any]]:
        return {key: adapter.to_dict() for key, adapter in sorted(self.adapters.items())}

    def get_adapter(self, platform_id: str) -> UniversalSocialPlatformAdapterR43E | None:
        return self.adapters.get(_safe_platform_id(platform_id))

    def detect_platform_id(self, account_url: str, fallback: str = "") -> str:
        text = _clean(account_url).lower()
        host = _host_from_url(text)
        for platform_id, adapter in self.adapters.items():
            if host and any(host == h or host.endswith("." + h) for h in adapter.url_hosts):
                return platform_id
        return _safe_platform_id(fallback) or "unknown_platform"

    def run_account_export(
        self,
        request: UniversalSocialAccountTrackingRequestR43E | Mapping[str, Any] | None = None,
        *,
        platform_id: str = "",
        account_url: str = "",
        account_handle: str = "",
        capture_timestamp: str = "",
        initial_records: Iterable[Mapping[str, Any]] | None = None,
    ) -> UniversalSocialAccountTrackingResultR43E:
        req = coerce_universal_social_account_tracking_request_r43e(
            request,
            platform_id=platform_id,
            account_url=account_url,
            account_handle=account_handle,
            capture_timestamp=capture_timestamp,
            output_root=str(self.output_root),
        )
        detected_platform = _safe_platform_id(req.platform_id or self.detect_platform_id(req.account_url, req.platform_id))
        adapter = self.get_adapter(detected_platform)
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        handle = _safe_handle(req.account_handle or _handle_from_url(req.account_url) or "unknown_account")
        account_url_plain = _plain_url(req.account_url or _default_account_url(detected_platform, handle))

        run_dir = Path(req.output_root or self.output_root) / detected_platform / handle / f"universal_account_tracking_{capture_ts}"
        run_dir.mkdir(parents=True, exist_ok=True)
        request_path = run_dir / "universal_account_tracking_request.json"
        runbook_path = run_dir / "universal_account_tracking_runbook.md"
        adapter_map_path = run_dir / "adapter_map.json"
        receipt_path = run_dir / "universal_account_tracking_receipt.json"

        req_payload = {
            **req.to_dict(),
            "platform_id": detected_platform,
            "account_handle": handle,
            "account_url": account_url_plain,
            "marker": R43E_MARKER,
            "schema_version": R43E_SCHEMA_VERSION,
        }
        _write_json(request_path, req_payload)
        _write_json(adapter_map_path, self.adapter_map_dict())
        _write_text(runbook_path, _build_universal_runbook(req_payload, adapter))

        warnings: list[str] = []
        downstream_payload: dict[str, Any] = {}
        downstream_status = ""
        account_record_path = ""
        manifest_path = ""
        media_index_path = ""
        screenshot_receipts_index_path = ""
        record_count = 0
        media_count = 0
        screenshot_count = 0
        date_folders: tuple[str, ...] = ()

        if adapter is None:
            downstream_status = "unknown_platform"
            warnings.append(f"No platform adapter is registered for {detected_platform!r}.")
        elif detected_platform == "twitter_x":
            downstream_payload = self._run_twitter_x_downstream(
                account_url=account_url_plain,
                account_handle=handle,
                capture_timestamp=capture_ts,
                request=req,
                initial_records=initial_records,
                run_dir=run_dir,
            )
            downstream_status = _clean(downstream_payload.get("status"))
            account_record_path = _clean(downstream_payload.get("account_record_path"))
            manifest_path = _clean(downstream_payload.get("manifest_path") or downstream_payload.get("ledger_manifest_path"))
            media_index_path = _clean(downstream_payload.get("media_index_path"))
            screenshot_receipts_index_path = _clean(downstream_payload.get("screenshot_receipts_index_path"))
            record_count = _safe_int(downstream_payload.get("record_count"))
            media_count = _safe_int(downstream_payload.get("media_count"))
            screenshot_count = _safe_int(downstream_payload.get("screenshot_count"))
            date_folders = tuple(str(x) for x in downstream_payload.get("date_folders") or ())
            if not downstream_status.startswith("PASS_"):
                warnings.append(f"Twitter/X downstream adapter did not pass: {downstream_status!r}.")
        elif detected_platform == "bluesky":
            downstream_payload = self._run_bluesky_downstream(
                account_url=account_url_plain,
                account_handle=handle,
                capture_timestamp=capture_ts,
                request=req,
                initial_records=initial_records,
                run_dir=run_dir,
            )
            downstream_status = _clean(downstream_payload.get("status"))
            account_record_path = _clean(downstream_payload.get("account_record_path"))
            manifest_path = _clean(downstream_payload.get("manifest_path"))
            media_index_path = _clean(downstream_payload.get("media_index_path"))
            screenshot_receipts_index_path = _clean(downstream_payload.get("screenshot_receipts_index_path"))
            record_count = _safe_int(downstream_payload.get("record_count"))
            media_count = _safe_int(downstream_payload.get("media_count"))
            screenshot_count = _safe_int(downstream_payload.get("screenshot_count"))
            date_folders = tuple(str(x) for x in downstream_payload.get("date_folders") or ())
            if not downstream_status.startswith("PASS_"):
                warnings.append(f"Bluesky downstream adapter did not pass: {downstream_status!r}.")
        else:
            downstream_status = "contract_only_adapter_pending"
            warnings.append(f"{adapter.display_name} is mapped to the universal contract but does not yet have a live adapter implementation.")

        contract = build_universal_social_account_tracking_contract_r43e()
        side_effect_flags = build_r43e_side_effect_flags()
        status = R43E_PASS_STATUS if downstream_status.startswith("PASS_") and not warnings and record_count > 0 else R43E_BLOCKED_STATUS
        result = UniversalSocialAccountTrackingResultR43E(
            marker=R43E_MARKER,
            schema_version=R43E_SCHEMA_VERSION,
            status=status,
            platform_id=detected_platform,
            adapter_status=_clean(adapter.adapter_status if adapter else "missing_adapter"),
            account_handle=handle,
            account_url=account_url_plain,
            capture_timestamp=capture_ts,
            run_dir=str(run_dir),
            request_path=str(request_path),
            runbook_path=str(runbook_path),
            adapter_map_path=str(adapter_map_path),
            receipt_path=str(receipt_path),
            downstream_status=downstream_status,
            downstream_result=downstream_payload,
            account_record_path=account_record_path,
            manifest_path=manifest_path,
            media_index_path=media_index_path,
            screenshot_receipts_index_path=screenshot_receipts_index_path,
            record_count=record_count,
            media_count=media_count,
            screenshot_count=screenshot_count,
            date_folders=date_folders,
            universal_contract=contract,
            side_effect_flags=side_effect_flags,
            warnings=tuple(warnings),
        )
        _write_json(receipt_path, result.to_dict())
        return result

    def _run_twitter_x_downstream(
        self,
        *,
        account_url: str,
        account_handle: str,
        capture_timestamp: str,
        request: UniversalSocialAccountTrackingRequestR43E,
        initial_records: Iterable[Mapping[str, Any]] | None,
        run_dir: Path,
    ) -> dict[str, Any]:
        surface = self.twitter_x_surface
        twitter_request_payload = {
            "account_url": account_url,
            "account_handle": account_handle,
            "capture_timestamp": capture_timestamp,
            "include_posts": request.include_posts,
            "include_reposts": request.include_reposts,
            "include_quote_posts": request.include_quote_posts,
            "include_replies": request.include_replies,
            "include_media": request.include_media,
            "include_static_screenshots": request.include_static_screenshots,
            "require_screenshot_receipts": request.require_screenshot_receipts,
            "output_root": str(run_dir / "twitter_x_surface"),
            "fixture_mode": request.fixture_mode,
            "explicit_live_mode": request.explicit_live_mode,
            "run_visible_live": request.run_visible_live,
            "live_mode": request.live_mode,
            "live_capture_enabled": bool(request.explicit_live_mode or request.run_visible_live or request.live_mode),
            "capture_mode": "visible_live" if bool(request.explicit_live_mode or request.run_visible_live or request.live_mode) else "safe_local_records_or_fixture",
            "browser_user_data_dir": request.browser_user_data_dir,
            "browser_executable_path": request.browser_executable_path,
            "max_items": request.max_items,
            "max_scrolls": request.max_scrolls,
        }
        if surface is None:
            from profile_media_twitter_x_account_tracking_export_surface_r43d import (
                TwitterXAccountTrackingExportRequestR43D,
                build_twitter_x_account_tracking_export_surface_r43d,
            )

            surface = build_twitter_x_account_tracking_export_surface_r43d(output_root=run_dir / "twitter_x_surface")
            twitter_request = TwitterXAccountTrackingExportRequestR43D(**twitter_request_payload)
            result = surface.run_account_export(twitter_request, initial_records=initial_records)
        else:
            result = surface.run_account_export(
                twitter_request_payload,
                initial_records=initial_records,
            )
        return _result_dict(result)

    def _run_bluesky_downstream(
        self,
        *,
        account_url: str,
        account_handle: str,
        capture_timestamp: str,
        request: UniversalSocialAccountTrackingRequestR43E,
        initial_records: Iterable[Mapping[str, Any]] | None,
        run_dir: Path,
    ) -> dict[str, Any]:
        bluesky_live_requested = bool(request.explicit_live_mode or request.run_visible_live or request.live_mode)
        initial_rows = tuple(initial_records or ())
        if bluesky_live_requested and not request.fixture_mode and not initial_rows:
            from profile_media_bluesky_public_appview_import_r43w import (
                BlueskyPublicAppviewImportRequestR43W,
                build_bluesky_public_appview_import_r43w,
            )

            adapter = build_bluesky_public_appview_import_r43w(output_root=run_dir / "bluesky_public_appview")
            public_request = BlueskyPublicAppviewImportRequestR43W(
                account_url=account_url,
                account_handle=account_handle,
                actor=account_handle,
                capture_timestamp=capture_timestamp,
                output_root=str(run_dir / "bluesky_public_appview"),
                live_mode=True,
                explicit_live_mode=True,
                public_network_enabled=True,
                include_media=request.include_media,
                include_static_screenshots=request.include_static_screenshots,
                require_screenshot_receipts=request.require_screenshot_receipts,
                max_items=request.max_items,
            )
            result = adapter.run_account_export(public_request)
            payload = _result_dict(result)
            payload["screenshot_receipts_index_path"] = ""
            return payload

        from profile_media_bluesky_visible_account_adapter_r43v import (
            BlueskyVisibleAccountAdapterRequestR43V,
            build_bluesky_visible_account_adapter_r43v,
        )

        adapter = build_bluesky_visible_account_adapter_r43v(output_root=run_dir / "bluesky_adapter")
        bluesky_request = BlueskyVisibleAccountAdapterRequestR43V(
            account_url=account_url,
            account_handle=account_handle,
            capture_timestamp=capture_timestamp,
            output_root=str(run_dir / "bluesky_adapter"),
            fixture_mode=request.fixture_mode,
            initial_records=initial_rows,
            include_media=request.include_media,
            include_static_screenshots=request.include_static_screenshots,
            require_screenshot_receipts=request.require_screenshot_receipts,
            explicit_live_mode=request.explicit_live_mode,
            run_visible_live=request.run_visible_live,
            live_mode=request.live_mode,
            max_items=request.max_items,
            max_scrolls=request.max_scrolls,
        )
        result = adapter.run_account_export(bluesky_request)
        payload = _result_dict(result)
        payload["screenshot_receipts_index_path"] = ""
        return payload


def build_universal_social_account_tracking_registry_r43e(
    *,
    twitter_x_surface: Any | None = None,
    output_root: str | Path = R43E_DEFAULT_OUTPUT_ROOT,
) -> UniversalSocialAccountTrackingRegistryR43E:
    return UniversalSocialAccountTrackingRegistryR43E(
        twitter_x_surface=twitter_x_surface,
        output_root=output_root,
    )


def build_universal_social_account_tracking_contract_r43e() -> dict[str, Any]:
    return {
        "marker": R43E_MARKER,
        "schema_version": R43E_SCHEMA_VERSION,
        "mode_id": R43E_MODE_ID,
        "scope": "platform_neutral_social_account_posts_reposts_reshares_quotes_replies_media_screenshots",
        "twitter_x_is_first_adapter_not_architecture": True,
        "future_platforms_use_same_contract": True,
        "adapter_model": "platform adapter maps native platform terms into universal account/post/reshare/quote/reply/media/screenshot receipt records",
        "universal_record_types": list(UNIVERSAL_RECORD_TYPES_R43E),
        "universal_output_files": list(UNIVERSAL_OUTPUT_FILES_R43E),
        "date_folder_rule": "visible post date first; fallback capture date; unknown_date if ambiguous",
        "post_folder_rule": "platform-neutral post_<id>; repost/reshare_<id>__original_<original_id> where an original id exists",
        "media_folder_rule": "each record folder links media/images, media/videos, media/manifests, media/segments",
        "screenshot_receipt_rule": "static screenshots are not complete evidence unless a materialization receipt passes or marks human-check/missing",
        "progress_pause_recovery_rule": "platform adapters record progress, stalls, pauses and recovery without fixed record-per-hour thresholds",
        "local_tracking_layer": "tracking, dedupe, folder routing, account_record.md, screenshot receipts and manifests are local Python/app logic",
        "browser_engine_role": "site rendering and observation only; WebView2/CefSharp/manual import can feed observations but must not own ledger state",
        "browser_engine_adapter_future": ["webview2", "cefsharp_or_cef", "manual_receipt_import", "platform_specific_public_export_import"],
        "platforms": ["twitter_x", "bluesky", "instagram", "facebook", "threads", "mastodon", "tiktok", "reddit", "youtube", "news_comments"],
        "review_window_dependency": False,
        "source_role_checks_enabled": False,
        "hidden_api_scraping_enabled": False,
        "remote_media_downloads_enabled_by_contract": False,
        "challenge_bypass_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "webview2_internals_copied": False,
    }


def build_default_platform_adapter_map_r43e() -> dict[str, UniversalSocialPlatformAdapterR43E]:
    shared_capabilities = (
        "account_record_md",
        "date_folder_export_map",
        "post_repost_quote_reply_record_model",
        "media_index",
        "static_screenshot_receipt_gate",
        "progress_pause_recovery_events",
        "local_tracking_dedupe_ledger_layer",
        "no_source_role_or_review_window_dependency",
    )
    return {
        "twitter_x": UniversalSocialPlatformAdapterR43E(
            platform_id="twitter_x",
            display_name="Twitter/X",
            url_hosts=("x.com", "twitter.com", "mobile.twitter.com"),
            adapter_status="implemented_first_adapter_r43d_surface",
            account_url_examples=("https://x.com/example", "https://twitter.com/example"),
            implementation_module="profile_media_twitter_x_account_tracking_export_surface_r43d",
            export_surface_attribute="twitter_x_account_tracking_export_surface_r43d",
            record_type_map={"post": "post", "repost": "repost_or_reshare", "quote": "quote", "reply": "reply"},
            capabilities=shared_capabilities + ("independent_fast_media_webview2_lane",),
            planned_from_twitter_x_contract=False,
            notes="Current concrete implementation; establishes the first adapter against the universal contract.",
        ),
        "bluesky": UniversalSocialPlatformAdapterR43E(
            platform_id="bluesky",
            display_name="Bluesky",
            url_hosts=("bsky.app", "staging.bsky.app"),
            adapter_status="implemented_fixture_import_adapter_r43v_public_appview_lane_r43w",
            account_url_examples=("https://bsky.app/profile/example.bsky.social",),
            implementation_module="profile_media_bluesky_visible_account_adapter_r43v",
            export_surface_attribute="bluesky_visible_account_adapter_r43v",
            record_type_map={"post": "post", "repost": "repost_or_reshare", "quote": "quote", "reply": "reply"},
            capabilities=shared_capabilities + ("app_bsky_post_view_normalization", "bluesky_embed_media_mapping", "public_appview_import_r43w", "r43u_universal_ledger_writer"),
            planned_from_twitter_x_contract=False,
            notes="R43V maps imported/visible/public Bluesky post views into the universal account ledger; R43W adds an explicit public appview feed import lane. Live visible-browser capture remains a later step.",
        ),
        "instagram": UniversalSocialPlatformAdapterR43E(
            platform_id="instagram",
            display_name="Instagram",
            url_hosts=("instagram.com", "www.instagram.com"),
            adapter_status="mapped_contract_adapter_pending",
            account_url_examples=("https://www.instagram.com/example/",),
            record_type_map={"post": "post", "reel": "post", "story": "post", "reshare": "repost_or_reshare", "comment": "reply"},
            capabilities=shared_capabilities,
            notes="Posts/Reels/Stories map into universal records; ephemeral or login-gated material requires human-authorized visible handling.",
        ),
        "facebook": UniversalSocialPlatformAdapterR43E(
            platform_id="facebook",
            display_name="Facebook",
            url_hosts=("facebook.com", "www.facebook.com", "m.facebook.com"),
            adapter_status="mapped_contract_adapter_pending",
            account_url_examples=("https://www.facebook.com/example",),
            record_type_map={"post": "post", "share": "repost_or_reshare", "comment": "reply"},
            capabilities=shared_capabilities,
            notes="Posts/shares/comments map into universal record folders with receipts; no login automation or hidden token extraction.",
        ),
        "threads": UniversalSocialPlatformAdapterR43E(
            platform_id="threads",
            display_name="Threads",
            url_hosts=("threads.net", "www.threads.net"),
            adapter_status="mapped_contract_adapter_pending",
            account_url_examples=("https://www.threads.net/@example",),
            record_type_map={"post": "post", "repost": "repost_or_reshare", "quote": "quote", "reply": "reply"},
            capabilities=shared_capabilities,
            notes="Thread posts and reposts use the same account/date/media/screenshot receipt model.",
        ),
        "mastodon": UniversalSocialPlatformAdapterR43E(
            platform_id="mastodon",
            display_name="Mastodon/Fediverse",
            url_hosts=("mastodon.social",),
            adapter_status="mapped_contract_adapter_pending",
            account_url_examples=("https://mastodon.social/@example",),
            record_type_map={"toot": "post", "boost": "repost_or_reshare", "reply": "reply"},
            capabilities=shared_capabilities,
            notes="Instance-specific hosts are added by adapter configuration; boosts map to reshares.",
        ),
        "tiktok": UniversalSocialPlatformAdapterR43E(
            platform_id="tiktok",
            display_name="TikTok",
            url_hosts=("tiktok.com", "www.tiktok.com"),
            adapter_status="mapped_contract_adapter_pending",
            account_url_examples=("https://www.tiktok.com/@example",),
            record_type_map={"video": "post", "repost": "repost_or_reshare", "comment": "reply"},
            capabilities=shared_capabilities,
            notes="Video-first account captures still use date folders, static screenshots, media folders and receipts.",
        ),
        "reddit": UniversalSocialPlatformAdapterR43E(
            platform_id="reddit",
            display_name="Reddit",
            url_hosts=("reddit.com", "www.reddit.com", "old.reddit.com"),
            adapter_status="mapped_contract_adapter_pending",
            account_url_examples=("https://www.reddit.com/user/example/",),
            record_type_map={"submission": "post", "crosspost": "repost_or_reshare", "comment": "reply"},
            capabilities=shared_capabilities,
            notes="Submissions/comments/crossposts map into universal record folders; comments can be enabled per request.",
        ),
    }


def coerce_universal_social_account_tracking_request_r43e(
    request: UniversalSocialAccountTrackingRequestR43E | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> UniversalSocialAccountTrackingRequestR43E:
    if isinstance(request, UniversalSocialAccountTrackingRequestR43E):
        base = request.to_dict()
    elif isinstance(request, Mapping):
        base = dict(request)
    else:
        base = {}
    for key, value in overrides.items():
        if value not in (None, ""):
            base[key] = value
    return UniversalSocialAccountTrackingRequestR43E(
        platform_id=_safe_platform_id(base.get("platform_id")),
        account_url=_plain_url(base.get("account_url") or ""),
        account_handle=_safe_handle(base.get("account_handle") or ""),
        capture_timestamp=_safe_ts(base.get("capture_timestamp") or ""),
        include_posts=bool(base.get("include_posts", True)),
        include_reposts=bool(base.get("include_reposts", True)),
        include_quote_posts=bool(base.get("include_quote_posts", True)),
        include_replies=bool(base.get("include_replies", False)),
        include_media=bool(base.get("include_media", True)),
        include_static_screenshots=bool(base.get("include_static_screenshots", True)),
        require_screenshot_receipts=bool(base.get("require_screenshot_receipts", True)),
        output_root=_clean(base.get("output_root") or R43E_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(base.get("fixture_mode"), False),
        explicit_live_mode=_to_bool(base.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(base.get("run_visible_live"), False),
        live_mode=_to_bool(base.get("live_mode"), False),
        browser_user_data_dir=_clean(base.get("browser_user_data_dir")),
        browser_executable_path=_clean(base.get("browser_executable_path")),
        max_items=_safe_int(base.get("max_items"), 3),
        max_scrolls=_safe_int(base.get("max_scrolls"), 2),
    )


def build_r43e_side_effect_flags() -> dict[str, bool]:
    return {
        "universal_social_account_tracking_registry_invoked": True,
        "twitter_x_first_adapter_not_architecture": True,
        "platform_neutral_contract_recorded": True,
        "adapter_map_written": True,
        "local_tracking_dedupe_ledger_layer": True,
        "tracking_logic_outside_browser_engine": True,
        "browser_engine_observation_only": True,
        "webview2_internals_copied": False,
        "webview2_session_started_by_r43e": False,
        "cefsharp_session_started_by_r43e": False,
        "hidden_x_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "remote_media_downloads_performed": False,
        "review_window_dependency_invoked": False,
        "review_window_rewrite_performed": False,
        "source_role_assignment_performed": False,
        "source_role_checks_performed": False,
        "source_role_interface_loop_invoked": False,
        "youtube_capture_engine_changed": False,
    }


def build_report(output_root: str | Path = R43E_DEFAULT_OUTPUT_ROOT) -> R43EReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    registry = build_universal_social_account_tracking_registry_r43e(output_root=root / "sample")
    sample = registry.run_account_export(
        UniversalSocialAccountTrackingRequestR43E(
            platform_id="twitter_x",
            account_url="https://x.com/example",
            account_handle="example",
            capture_timestamp="20260915T040000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
        )
    )
    contract = build_universal_social_account_tracking_contract_r43e()
    adapter_map = registry.adapter_map_dict()
    side_effect_flags = build_r43e_side_effect_flags()
    checks = [
        _check("universal_contract_is_platform_neutral", contract.get("future_platforms_use_same_contract") is True and "bluesky" in contract.get("platforms", [])),
        _check("twitter_x_is_first_adapter_not_architecture", contract.get("twitter_x_is_first_adapter_not_architecture") is True and adapter_map.get("twitter_x", {}).get("planned_from_twitter_x_contract") is False),
        _check("major_social_platforms_are_mapped", all(k in adapter_map for k in ("twitter_x", "bluesky", "instagram", "facebook", "threads", "mastodon", "tiktok", "reddit"))),
        _check("universal_record_types_cover_posts_reshares_media_screenshots", all(k in contract.get("universal_record_types", []) for k in ("post", "repost_or_reshare", "media_image", "media_video", "screenshot_receipt", "progress_event"))),
        _check("twitter_x_routes_to_r43d_surface", sample.platform_id == "twitter_x" and sample.downstream_status.startswith("PASS_")),
        _check("request_runbook_adapter_map_and_receipt_written", all(Path(p).is_file() for p in (sample.request_path, sample.runbook_path, sample.adapter_map_path, sample.receipt_path))),
        _check("date_folders_account_record_media_and_screenshot_receipts_preserved", bool(sample.date_folders) and bool(sample.account_record_path) and bool(sample.media_index_path) and bool(sample.screenshot_receipts_index_path)),
        _check("browser_engine_observation_only_and_no_review_lane", side_effect_flags.get("browser_engine_observation_only") is True and side_effect_flags.get("review_window_dependency_invoked") is False and side_effect_flags.get("source_role_checks_performed") is False),
        _check("no_webview2_internal_copy_or_tracking_side_effects", side_effect_flags.get("webview2_internals_copied") is False and side_effect_flags.get("cookie_or_token_extraction_performed") is False and side_effect_flags.get("captcha_or_challenge_bypass_performed") is False),
        _check("plain_machine_urls", _machine_urls_are_plain({"contract": contract, "adapter_map": adapter_map, "sample": sample.to_dict()})),
    ]
    status = R43E_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R43E_BLOCKED_STATUS
    report = R43EReport(
        marker=R43E_MARKER,
        schema_version=R43E_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=tuple(checks),
        universal_contract=contract,
        adapter_map=adapter_map,
        sample_result=sample.to_dict(),
        side_effect_flags=side_effect_flags,
    )
    _write_json(root / "R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP_REPORT.json", report.to_dict())
    _write_text(root / "R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP_REPORT.md", _report_md(report))
    return report


def _build_universal_runbook(request_payload: Mapping[str, Any], adapter: UniversalSocialPlatformAdapterR43E | None) -> str:
    platform = _clean(request_payload.get("platform_id"))
    title = adapter.display_name if adapter else platform
    lines = [
        "# Universal social account tracking runbook",
        "",
        f"Marker: `{R43E_MARKER}`",
        f"Schema: `{R43E_SCHEMA_VERSION}`",
        f"Platform: `{platform}` ({title})",
        f"Account: `{_clean(request_payload.get('account_handle'))}`",
        f"Account URL: {_plain_url(request_payload.get('account_url') or '')}",
        "",
        "## Universal contract",
        "",
        "- Twitter/X is the first adapter implementation, not the architecture.",
        "- Bluesky, Instagram, Facebook, Threads, Mastodon, TikTok, Reddit and later platforms map into the same account/post/reshare/media/screenshot receipt model.",
        "- WebView2 or any later browser engine is only a rendering/observation input.",
        "- Tracking, dedupe, folder routing, date folders, account_record.md, media_index.json and screenshot receipts stay in the local app layer.",
        "- No source-role checks, review-window dependency, hidden API scraping, token/cookie extraction, or challenge bypass are enabled by this layer.",
        "",
        "## Shared outputs",
        "",
    ]
    for name in UNIVERSAL_OUTPUT_FILES_R43E:
        lines.append(f"- `{name}`")
    return "\n".join(lines) + "\n"


def _report_md(report: R43EReport) -> str:
    lines = [
        "# R43E Universal Social Account Tracking Contract And Adapter Map",
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
        "## Platforms",
        "",
        ", ".join(sorted(report.adapter_map.keys())),
        "",
    ])
    return "\n".join(lines)


def _result_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
        return dict(payload) if isinstance(payload, Mapping) else {}
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


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
    markdown = re.fullmatch(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", text)
    if markdown:
        return markdown.group(2)
    return text.replace("\\_", "_").replace("\\:", ":")


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _host_from_url(value: str) -> str:
    text = _plain_url(value).lower()
    match = re.match(r"https?://([^/]+)/?", text)
    return (match.group(1) if match else "").split(":", 1)[0]


def _handle_from_url(value: str) -> str:
    text = _plain_url(value)
    if not text:
        return ""
    match = re.search(r"(?:x\.com|twitter\.com|instagram\.com|threads\.net|reddit\.com/(?:user|u)|tiktok\.com/@|bsky\.app/profile|facebook\.com|mastodon\.social/@)/@?([^/?#]+)", text, re.I)
    if match:
        return _safe_handle(match.group(1))
    bits = [p for p in text.split("/") if p]
    return _safe_handle(bits[-1]) if bits else ""


def _default_account_url(platform_id: str, handle: str) -> str:
    if platform_id == "twitter_x":
        return f"https://x.com/{handle}"
    if platform_id == "bluesky":
        return f"https://bsky.app/profile/{handle}"
    if platform_id == "instagram":
        return f"https://www.instagram.com/{handle}/"
    if platform_id == "threads":
        return f"https://www.threads.net/@{handle}"
    if platform_id == "tiktok":
        return f"https://www.tiktok.com/@{handle}"
    if platform_id == "reddit":
        return f"https://www.reddit.com/user/{handle}/"
    return f"https://example.invalid/{platform_id}/{handle}"


def _safe_handle(value: Any) -> str:
    text = _clean(value).strip().lstrip("@")
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._-")
    return text or "unknown_account"


def _safe_platform_id(value: Any) -> str:
    text = _clean(value).lower().replace("twitter", "twitter_x") if _clean(value).lower() == "twitter" else _clean(value).lower()
    text = text.replace("x/twitter", "twitter_x").replace("twitter/x", "twitter_x")
    text = re.sub(r"[^a-z0-9_]+", "_", text).strip("_")
    if text in {"x", "twitterx", "twitter_x_com"}:
        return "twitter_x"
    return text


def _safe_ts(value: Any) -> str:
    text = _clean(value).replace(":", "").replace("-", "")
    return re.sub(r"[^0-9TZ]", "", text)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        return default


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    report = build_report()
    print(R43E_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
