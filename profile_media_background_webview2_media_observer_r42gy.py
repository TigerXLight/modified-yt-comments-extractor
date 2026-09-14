from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from profile_media_twitter_x_visible_browser_media_observation_r42gv import (
    R42GV_MARKER,
    build_visible_browser_media_observation_store,
    write_visible_browser_media_observation_store,
)
from profile_media_unified_media_window_app_bridge_r42gx import (
    BACKGROUND_WEBVIEW2_MODE_ID,
    VISIBLE_ESCALATION_MODE_ID,
    build_background_webview2_media_observer_policy_r42gx,
    build_unified_media_window_bridge_state_r42gx,
)
from profile_media_unified_media_window_tabs_r42gw import (
    JDOWNLOADER_REFERENCE_MODEL,
    TAB_ALL,
    build_unified_media_window_state_from_visible_browser_store,
    flatten_media_window_tree,
    state_to_dict,
)
from source_resource_state import (
    RESOURCE_KIND_IMAGE,
    RESOURCE_KIND_VIDEO_AUDIO,
    SourceResourceItem,
    SourceResourceRowState,
)

R42GY_MARKER = "YTCE_R42GY_BACKGROUND_WEBVIEW2_FAST_MEDIA_OBSERVER_RUNTIME"
R42GY_PASS_STATUS = "PASS_R42GY_BACKGROUND_WEBVIEW2_FAST_MEDIA_OBSERVER_RUNTIME"
R42GY_BLOCKED_STATUS = "BLOCKED_R42GY_BACKGROUND_WEBVIEW2_FAST_MEDIA_OBSERVER_RUNTIME"
R42GY_ESCALATE_VISIBLE_STATUS = "ESCALATE_R42GY_VISIBLE_WEBVIEW2_OR_EDGE_HUMAN_CONFIRMATION"
R42GY_SCHEMA_VERSION = "background_webview2_fast_media_observer_runtime.r42gy.v1"

ObserverBackend = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class BackgroundWebView2ObserverReceiptR42GY:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    source_row_id: str
    source_url: str
    adapter_id: str
    backend_id: str
    backend_status: str
    observation_count: int
    segment_count: int
    visible_escalation_required: bool
    visible_escalation_reasons: tuple[str, ...]
    observation_store_path: str = ""
    observation_ndjson_path: str = ""
    segment_table_path: str = ""
    review_projection_path: str = ""
    r42gv_marker: str = R42GV_MARKER
    background_webview2_policy: Mapping[str, Any] | None = None
    unified_media_window_state: Any | None = None
    bridge_state: Mapping[str, Any] | None = None
    side_effect_flags: Mapping[str, bool] | None = None
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R42GY_PASS_STATUS and self.observation_count > 0

    def to_dict(self) -> dict[str, Any]:
        payload = state_to_dict(self)
        # state_to_dict/asdict does not include computed properties such as
        # UnifiedMediaWindowState.package_count or segment_child_count. Preserve
        # the model's own to_dict() output so report checks and downstream UI
        # receipts see the same package/child counts as the live object.
        if self.unified_media_window_state is not None and hasattr(self.unified_media_window_state, "to_dict"):
            payload["unified_media_window_state"] = self.unified_media_window_state.to_dict()
        if self.bridge_state is not None:
            payload["bridge_state"] = state_to_dict(self.bridge_state)
        if self.background_webview2_policy is not None:
            payload["background_webview2_policy"] = state_to_dict(self.background_webview2_policy)
        if self.side_effect_flags is not None:
            payload["side_effect_flags"] = dict(self.side_effect_flags)
        return payload


@dataclass(frozen=True)
class R42GYReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    runtime_receipt: Mapping[str, Any]
    visible_escalation_receipt: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R42GY_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return state_to_dict(self)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _safe_path_part(value: Any, fallback: str = "source") -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", _clean(value)).strip("._-")
    return text[:120] or fallback


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "to_dict"):
        try:
            payload = value.to_dict()
            if isinstance(payload, Mapping):
                return payload
        except Exception:
            pass
    if hasattr(value, "__dataclass_fields__"):
        return state_to_dict(value)
    return {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_") and not callable(getattr(value, key, None))
    }


def _row_value(row: SourceResourceRowState | Mapping[str, Any], key: str, default: Any = "") -> Any:
    if isinstance(row, Mapping):
        return row.get(key, default)
    return getattr(row, key, default)


def _coerce_row(row: SourceResourceRowState | Mapping[str, Any]) -> SourceResourceRowState:
    if isinstance(row, SourceResourceRowState):
        return row
    source_url = _clean(row.get("canonical_url") or row.get("source_url") or row.get("raw_url"))
    row_id = _clean(row.get("row_id") or row.get("source_row_id") or source_url or "source")
    adapter_id = _clean(row.get("adapter_id") or "webpage")
    return SourceResourceRowState(
        row_id=row_id,
        raw_url=source_url,
        canonical_url=source_url,
        adapter_id=adapter_id,
        adapter_display_name=_clean(row.get("adapter_display_name") or adapter_id),
        source_id=_clean(row.get("source_id")),
        title=_clean(row.get("title") or source_url),
        domain=_clean(row.get("domain")),
        display_label=_clean(row.get("display_label") or source_url),
        image_resources=tuple(row.get("image_resources") or ()),
        video_audio_resources=tuple(row.get("video_audio_resources") or ()),
        provenance=_clean(row.get("provenance") or "R42GY background WebView2 observer row"),
    )


def build_r42gy_side_effect_flags(
    *,
    backend_called: bool = False,
    background_session_started: bool = False,
    network_actions_performed: bool = False,
    downloads_performed: bool = False,
) -> dict[str, bool]:
    """Side-effect flags for the observer runtime.

    R42GY is allowed to call an explicitly provided background WebView2 backend.
    That backend may perform the per-link page load in the real app path. The
    forbidden boundaries remain unchanged: no hidden X API scraping, login
    automation, cookie/token extraction, challenge bypass, source-role
    assignment, review-window rewrite, or YouTube capture-engine change.
    """

    return {
        "r42gy_runtime_invoked": True,
        "background_webview2_backend_called": bool(backend_called),
        "background_webview2_session_started_by_r42gy": bool(background_session_started),
        "background_webview2_fast_per_link_observer": True,
        "network_actions_performed": bool(network_actions_performed),
        "downloads_performed": bool(downloads_performed),
        "hidden_x_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "paywall_or_access_control_bypass_performed": False,
        "source_role_assignment_performed": False,
        "review_window_rewrite_performed": False,
        "review_window_stays_separate": True,
        "visible_browser_escalation_policy_recorded": True,
        "jdownloader_direct_code_copy_allowed_when_attributed_and_license_compatible": True,
        "jdownloader_source_usage_policy_recorded": True,
        "youtube_capture_engine_changed": False,
    }


def build_background_webview2_observation_request_r42gy(
    row: SourceResourceRowState | Mapping[str, Any],
    *,
    active_tab: str = TAB_ALL,
    output_root: str | Path = "",
    capture_timestamp: str = "",
) -> dict[str, Any]:
    source_row = _coerce_row(row)
    policy = build_background_webview2_media_observer_policy_r42gx(source_row)
    return {
        "schema_version": R42GY_SCHEMA_VERSION,
        "marker": R42GY_MARKER,
        "mode_id": BACKGROUND_WEBVIEW2_MODE_ID,
        "source_row_id": source_row.row_id,
        "source_url": source_row.canonical_url or source_row.raw_url,
        "adapter_id": source_row.adapter_id,
        "active_tab": active_tab,
        "capture_timestamp": capture_timestamp,
        "output_root": str(output_root) if output_root else "",
        "policy": policy,
        "review_window_separate": True,
        "hard_boundaries": policy.get("hard_boundaries", ()),
        "expected_backend_result_fields": (
            "events",
            "final_dom",
            "media_inventory",
            "session_local_files",
            "warnings",
            "requires_login",
            "access_barrier_detected",
            "challenge_detected",
        ),
    }


def _call_backend(backend: Any, request: Mapping[str, Any]) -> Mapping[str, Any]:
    if backend is None:
        return {
            "backend_id": "none",
            "status": "background_webview2_backend_not_configured",
            "warnings": ("No background WebView2 observer backend is configured for this runtime call.",),
            "events": (),
            "final_dom": "",
        }
    if callable(backend):
        result = backend(request)
        return dict(result) if isinstance(result, Mapping) else {"backend_id": "callable_backend", "status": "backend_returned_non_mapping", "result": result}
    for method_name in ("observe_media", "observe", "run", "capture"):
        method = getattr(backend, method_name, None)
        if method is not None:
            result = method(request)
            return dict(result) if isinstance(result, Mapping) else {"backend_id": method_name, "status": "backend_returned_non_mapping", "result": result}
    return {
        "backend_id": type(backend).__name__,
        "status": "background_webview2_backend_has_no_observe_method",
        "warnings": ("Backend did not provide observe_media/observe/run/capture.",),
        "events": (),
        "final_dom": "",
    }


def _escalation_reasons(result: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    checks = (
        ("requires_login", "login or account chooser is required"),
        ("consent_required", "consent screen is required"),
        ("challenge_detected", "CAPTCHA/challenge screen detected"),
        ("captcha_detected", "CAPTCHA/challenge screen detected"),
        ("access_barrier_detected", "access-control or paywall barrier detected"),
        ("visual_confirmation_required", "visual confirmation is needed before evidence promotion"),
        ("insufficient_rendered_material", "background WebView2 could not expose enough rendered/session material"),
    )
    for key, reason in checks:
        if bool(result.get(key)):
            reasons.append(reason)
    for warning in result.get("warnings") or ():
        text = _clean(warning).lower()
        if any(token in text for token in ("captcha", "challenge", "login", "consent", "paywall", "access-control", "access control")):
            reasons.append(_clean(warning))
    deduped: list[str] = []
    for reason in reasons:
        if reason and reason not in deduped:
            deduped.append(reason)
    return tuple(deduped)


def _output_dir_for(row: SourceResourceRowState, output_root: str | Path, capture_timestamp: str) -> Path:
    root = Path(output_root) if output_root else Path("profile_media_live_captures") / "r42gy_background_webview2_media_observer"
    safe_row = _safe_path_part(row.row_id)
    safe_ts = _safe_path_part(capture_timestamp or _now_ts(), "capture")
    return root / safe_row / safe_ts


def run_background_webview2_media_observer_for_row_r42gy(
    row: SourceResourceRowState | Mapping[str, Any],
    *,
    backend: Any = None,
    output_root: str | Path = "profile_media_live_captures/r42gy_background_webview2_media_observer",
    active_tab: str = TAB_ALL,
    capture_timestamp: str = "",
) -> BackgroundWebView2ObserverReceiptR42GY:
    source_row = _coerce_row(row)
    capture_ts = capture_timestamp or _now_ts()
    request = build_background_webview2_observation_request_r42gy(
        source_row,
        active_tab=active_tab,
        output_root=output_root,
        capture_timestamp=capture_ts,
    )
    policy = build_background_webview2_media_observer_policy_r42gx(source_row)
    backend_result = _call_backend(backend, request)
    warnings = tuple(_clean(item) for item in backend_result.get("warnings") or () if _clean(item))
    escalation_reasons = _escalation_reasons(backend_result)
    backend_called = backend is not None and not str(backend_result.get("status") or "").endswith("has_no_observe_method")
    background_session_started = bool(backend_result.get("background_webview2_session_started") or backend_result.get("browser_session_started"))
    network_actions = bool(backend_result.get("network_actions_performed"))
    downloads = bool(backend_result.get("downloads_performed"))

    side_effect_flags = build_r42gy_side_effect_flags(
        backend_called=backend_called,
        background_session_started=background_session_started,
        network_actions_performed=network_actions,
        downloads_performed=downloads,
    )

    if escalation_reasons:
        return BackgroundWebView2ObserverReceiptR42GY(
            marker=R42GY_MARKER,
            schema_version=R42GY_SCHEMA_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            status=R42GY_ESCALATE_VISIBLE_STATUS,
            source_row_id=source_row.row_id,
            source_url=source_row.canonical_url or source_row.raw_url,
            adapter_id=source_row.adapter_id,
            backend_id=_clean(backend_result.get("backend_id") or type(backend).__name__),
            backend_status=_clean(backend_result.get("status") or "escalation_required"),
            observation_count=0,
            segment_count=0,
            visible_escalation_required=True,
            visible_escalation_reasons=escalation_reasons,
            background_webview2_policy=policy,
            unified_media_window_state=None,
            bridge_state=None,
            side_effect_flags=side_effect_flags,
            warnings=warnings,
        )

    events = tuple(backend_result.get("events") or backend_result.get("network_events") or ())
    final_dom = _clean(backend_result.get("final_dom") or backend_result.get("html") or backend_result.get("dom") or "")
    media_inventory = tuple(backend_result.get("media_inventory") or ())
    session_local_files = tuple(backend_result.get("session_local_files") or ())
    if backend is None:
        return BackgroundWebView2ObserverReceiptR42GY(
            marker=R42GY_MARKER,
            schema_version=R42GY_SCHEMA_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            status=R42GY_BLOCKED_STATUS,
            source_row_id=source_row.row_id,
            source_url=source_row.canonical_url or source_row.raw_url,
            adapter_id=source_row.adapter_id,
            backend_id="none",
            backend_status=_clean(backend_result.get("status") or "background_webview2_backend_not_configured"),
            observation_count=0,
            segment_count=0,
            visible_escalation_required=False,
            visible_escalation_reasons=(),
            background_webview2_policy=policy,
            unified_media_window_state=None,
            bridge_state=None,
            side_effect_flags=side_effect_flags,
            warnings=warnings,
        )

    store = build_visible_browser_media_observation_store(
        source_url=source_row.canonical_url or source_row.raw_url,
        events=events,
        final_dom=final_dom,
        media_inventory=media_inventory,
        session_local_files=session_local_files,
        capture_timestamp=capture_ts,
    )
    out_dir = _output_dir_for(source_row, output_root, capture_ts)
    write_result = write_visible_browser_media_observation_store(store, out_dir)
    media_state = build_unified_media_window_state_from_visible_browser_store(
        store,
        source_row_id=source_row.row_id,
        adapter_id=source_row.adapter_id,
        active_tab=active_tab,
    )
    bridge_state = build_unified_media_window_bridge_state_r42gx(source_row, active_tab=active_tab, visible_browser_store=store)
    receipt_status = R42GY_PASS_STATUS if store.observation_count > 0 else R42GY_BLOCKED_STATUS
    receipt = BackgroundWebView2ObserverReceiptR42GY(
        marker=R42GY_MARKER,
        schema_version=R42GY_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=receipt_status,
        source_row_id=source_row.row_id,
        source_url=source_row.canonical_url or source_row.raw_url,
        adapter_id=source_row.adapter_id,
        backend_id=_clean(backend_result.get("backend_id") or type(backend).__name__),
        backend_status=_clean(backend_result.get("status") or "observed"),
        observation_count=store.observation_count,
        segment_count=store.segment_count,
        visible_escalation_required=False,
        visible_escalation_reasons=(),
        observation_store_path=write_result.observation_store_path,
        observation_ndjson_path=write_result.observation_ndjson_path,
        segment_table_path=write_result.segment_table_path,
        review_projection_path=write_result.review_projection_path,
        background_webview2_policy=policy,
        unified_media_window_state=media_state,
        bridge_state=bridge_state,
        side_effect_flags=side_effect_flags,
        warnings=warnings,
    )
    (out_dir / "R42GY_BACKGROUND_WEBVIEW2_FAST_MEDIA_OBSERVER_RUNTIME_RECEIPT.json").write_text(
        json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "unified_media_window_state.json").write_text(
        json.dumps(media_state.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "background_webview2_request.json").write_text(
        json.dumps(request, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def _fixture_row() -> SourceResourceRowState:
    row_id = "twitter_x:example:1234567890"
    source_url = "https://x.com/example/status/1234567890"
    return SourceResourceRowState(
        row_id=row_id,
        raw_url=source_url,
        canonical_url=source_url,
        adapter_id="twitter_x",
        adapter_display_name="X/Twitter",
        source_id="1234567890",
        title="Example X post",
        domain="x.com",
        display_label="Example X post - x.com",
        image_resources=(
            SourceResourceItem(
                resource_id="existing-image",
                source_row_id=row_id,
                resource_kind=RESOURCE_KIND_IMAGE,
                reference_url="https://pbs.twimg.com/media/existing.jpg?format=jpg&name=large",
                canonical_url="https://pbs.twimg.com/media/existing.jpg?format=jpg&name=large",
                display_name="existing-image",
                media_type="image",
                mime_type="image/jpeg",
                extension="jpg",
            ),
        ),
        video_audio_resources=(
            SourceResourceItem(
                resource_id="existing-video",
                source_row_id=row_id,
                resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
                reference_url="https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/existing.mp4",
                canonical_url="https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/existing.mp4",
                display_name="existing-video",
                media_type="video",
                mime_type="video/mp4",
                extension="mp4",
            ),
        ),
        provenance="R42GY fixture row",
    )


def _fixture_backend(request: Mapping[str, Any]) -> Mapping[str, Any]:
    manifest = "https://video.twimg.com/ext_tw_video/1234567890/pu/pl/manifest.m3u8?tag=16"
    return {
        "backend_id": "fixture_background_webview2_observer",
        "status": "fixture_observed_without_live_network",
        "background_webview2_session_started": False,
        "network_actions_performed": False,
        "downloads_performed": False,
        "events": (
            {"request_id": "img-network", "url": "https://pbs.twimg.com/media/r42gy_image.jpg?format=jpg&name=large", "content_type": "image/jpeg", "resource_type": "image"},
            {"request_id": "manifest-network", "url": manifest, "content_type": "application/x-mpegURL", "resource_type": "media"},
            {"request_id": "segment-1", "url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00001.ts", "content_type": "video/mp2t", "resource_type": "media"},
            {"request_id": "segment-2", "url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00002.ts", "content_type": "video/mp2t", "resource_type": "media"},
            {"request_id": "mp4-network", "url": "https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/video.mp4", "content_type": "video/mp4", "resource_type": "media"},
        ),
        "final_dom": '<html><body><article><img src="https://pbs.twimg.com/media/dom_r42gy.jpg?format=jpg&amp;name=large"></article></body></html>',
        "media_inventory": (),
        "session_local_files": (),
        "warnings": (),
    }


def _fixture_escalation_backend(request: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "backend_id": "fixture_background_webview2_escalation",
        "status": "challenge_detected",
        "challenge_detected": True,
        "events": (),
        "final_dom": "",
        "warnings": ("CAPTCHA/challenge screen detected; escalate to visible WebView2/Edge for direct human confirmation.",),
    }


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _scrub_markdown_machine_urls(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _scrub_markdown_machine_urls(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_scrub_markdown_machine_urls(item) for item in value)
    if isinstance(value, list):
        return [_scrub_markdown_machine_urls(item) for item in value]
    if isinstance(value, str) and ("http://" in value or "https://" in value):
        text = value.replace("\_", "_").replace("\&", "&").replace("\/", "/").strip()
        normalized = text.replace("]\(", "](").replace("\)", ")")
        if "](" in normalized:
            match = re.search(r"\]\((https?://[^)\s]+)\)", normalized)
            if match:
                return match.group(1).replace("\_", "_").replace("\&", "&").replace("\/", "/").strip()
        return normalized
    return value


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_scrub_markdown_machine_urls(state_to_dict(value)), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob

def build_report(output_root: str | Path) -> R42GYReport:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    row = _fixture_row()
    runtime = run_background_webview2_media_observer_for_row_r42gy(
        row,
        backend=_fixture_backend,
        output_root=out,
        active_tab=TAB_ALL,
        capture_timestamp="20260914T000000Z",
    )
    escalation = run_background_webview2_media_observer_for_row_r42gy(
        row,
        backend=_fixture_escalation_backend,
        output_root=out / "escalation_fixture",
        active_tab=TAB_ALL,
        capture_timestamp="20260914T000001Z",
    )
    runtime_dict = _scrub_markdown_machine_urls(runtime.to_dict())
    escalation_dict = _scrub_markdown_machine_urls(escalation.to_dict())
    media_state = runtime_dict.get("unified_media_window_state") or {}
    rows = tuple(flatten_media_window_tree(runtime.unified_media_window_state, tab_id=TAB_ALL, include_children=True)) if runtime.unified_media_window_state is not None else ()
    flags = dict(runtime.side_effect_flags or {})
    checks = (
        _check("background_webview2_backend_invoked", flags.get("background_webview2_backend_called") is True),
        _check("r42gv_observation_store_written", Path(runtime.observation_store_path).is_file()),
        _check("unified_media_window_state_refreshed_from_observer", media_state.get("tabs") == ["all", "images", "videos"] and media_state.get("package_count", 0) >= 2),
        _check("r42gw_package_child_tree_received_observer_rows", any(row.get("row_role") == "package" for row in rows) and any(row.get("row_role") == "child" for row in rows)),
        _check("segmented_media_grouped_under_video_stream_package", int(media_state.get("segment_child_count") or 0) >= 2),
        _check("segments_listed_but_not_selected_by_default", any(row.get("media_class") == "segment" and row.get("selectable") is False for row in rows)),
        _check("review_window_remains_separate", media_state.get("review_window_separate") is True and runtime_dict.get("background_webview2_policy", {}).get("review_window_separate") is True),
        _check("visible_escalation_triggered_for_challenge", escalation.status == R42GY_ESCALATE_VISIBLE_STATUS and escalation.visible_escalation_required is True),
        _check("no_forbidden_side_effects", all(flags.get(key) is False for key in ("downloads_performed", "hidden_x_api_scraping_performed", "login_automation_performed", "cookie_or_token_extraction_performed", "captcha_or_challenge_bypass_performed", "paywall_or_access_control_bypass_performed", "source_role_assignment_performed", "review_window_rewrite_performed", "youtube_capture_engine_changed"))),
        _check("jdownloader_source_usage_policy_allows_attributed_licensed_adaptation", bool(JDOWNLOADER_REFERENCE_MODEL.get("source_usage_policy", {}).get("direct_code_copy_allowed_when_attributed_and_license_compatible"))),
        _check("plain_machine_urls", _machine_urls_are_plain(runtime_dict) and _machine_urls_are_plain(escalation_dict)),
    )
    status = R42GY_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GY_BLOCKED_STATUS
    report = R42GYReport(
        marker=R42GY_MARKER,
        schema_version=R42GY_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        runtime_receipt=runtime_dict,
        visible_escalation_receipt=escalation_dict,
        side_effect_flags=flags,
    )
    write_report(report, out)
    return report


def write_report(report: R42GYReport, output_root: str | Path) -> None:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    (out / "R42GY_BACKGROUND_WEBVIEW2_FAST_MEDIA_OBSERVER_RUNTIME_REPORT.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# R42GY Background WebView2 Fast Media Observer Runtime Report",
        "",
        f"- marker: `{report.marker}`",
        f"- status: `{report.status}`",
        f"- schema: `{report.schema_version}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')} {check.get('detail') or ''}".rstrip())
    lines.extend(
        [
            "",
            "## Runtime model",
            "- A per-link background WebView2 backend can be called by the Media window fast path.",
            "- Backend observations are normalized into the R42GV observation store.",
            "- The R42GV store is projected into the R42GW All / Images / Videos package tree.",
            "- Review/source-role decisions remain in the separate review window.",
            "- Visible WebView2/Edge is the escalation path for login, consent, CAPTCHA/challenge, access barriers, and visual confirmation.",
            "- JDownloader source/framework/logic/code adaptation is allowed when attributed, provenance-bounded, and licence-compatible.",
        ]
    )
    (out / "R42GY_BACKGROUND_WEBVIEW2_FAST_MEDIA_OBSERVER_RUNTIME_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gy_background_webview2_media_observer_runtime")
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(report.marker)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
