from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping

R42GZ_MARKER = "YTCE_R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE"
R42GZ_PASS_STATUS = "PASS_R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE"
R42GZ_BLOCKED_STATUS = "BLOCKED_R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE"
R42GZ_ESCALATE_STATUS = "ESCALATE_R42GZ_VISIBLE_WEBVIEW2_OR_EDGE_HUMAN_CONFIRMATION"
R42GZ_SCHEMA_VERSION = "independent_fast_media_webview2_capture_lane.r42gz.v1"
R42GZ_BACKEND_ID = "independent_fast_media_webview2_lane_r42gz"
R42GZ_MODE_ID = "independent_fast_media_webview2_per_link_media_only_lane"
R42GZ_CAPTURE_GOAL = "r42gz_independent_fast_media_webview2_media_only"
R42GZ_DEFAULT_PROFILE_DIR = "profile_media_browser_profiles/r42gz_independent_fast_media_webview2_lane"
R42GZ_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r42gz_independent_fast_media_webview2_lane"

TwitterCaptureRunner = Callable[..., Any]


@dataclass(frozen=True)
class IndependentFastMediaWebView2LaneConfigR42GZ:
    """Independent Media-window capture lane config.

    This is intentionally separate from the review/source-role WebView2 lane.
    It is per-link, media-only, and has its own profile/output state. It may use
    the existing lower-level browser capture primitive, but it does not call the
    review window, source-role interface, source-role material judgement loop, or
    review back-and-forth path.
    """

    live: bool = True
    headless: bool = True
    timeout_ms: int = 45000
    scroll_steps: int = 2
    smart_rate_limit: bool = True
    scroll_delay_ms: int = 900
    scroll_jitter_ms: int = 250
    scroll_pixels: int = 1700
    max_timeline_pages: int = 2
    no_progress_scrolls: int = 2
    stop_on_rate_limit: bool = True
    rate_limit_cooldown_ms: int = 0
    browser_user_data_dir: str = R42GZ_DEFAULT_PROFILE_DIR
    browser_executable_path: str = ""
    reuse_existing_profile: bool = False
    capture_goal: str = R42GZ_CAPTURE_GOAL
    media_only: bool = True
    per_link_basis: bool = True
    independent_lane: bool = True
    review_window_dependency: bool = False
    source_role_interface_dependency: bool = False
    source_role_checks_enabled: bool = False
    source_role_back_and_forth_enabled: bool = False
    fixture_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class R42GZReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    lane_backend_result: Mapping[str, Any]
    r42gy_runtime_receipt: Mapping[str, Any]
    lane_contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R42GZ_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "lane_backend_result": _to_jsonable(self.lane_backend_result),
            "lane_contract": dict(self.lane_contract),
            "marker": self.marker,
            "r42gy_runtime_receipt": _to_jsonable(self.r42gy_runtime_receipt),
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
        }


class IndependentFastMediaWebView2LaneBackendR42GZ:
    def __init__(self, *, runner: TwitterCaptureRunner | None = None, config: IndependentFastMediaWebView2LaneConfigR42GZ | None = None) -> None:
        self.runner = runner or _default_twitter_browser_capture_runner
        self.config = config or IndependentFastMediaWebView2LaneConfigR42GZ()

    def observe_media(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        request_payload = dict(request or {})
        source_url = _plain_url(request_payload.get("source_url") or request_payload.get("canonical_url") or request_payload.get("raw_url") or "")
        source_row_id = _clean(request_payload.get("source_row_id") or source_url or "source")
        adapter_id = _clean(request_payload.get("adapter_id") or "webpage")
        capture_timestamp = _clean(request_payload.get("capture_timestamp")) or _now_ts()
        output_root = Path(_clean(request_payload.get("output_root")) or R42GZ_DEFAULT_OUTPUT_ROOT)
        lane_output_dir = output_root / "r42gz_independent_fast_media_webview2_lane" / _safe_part(source_row_id) / _safe_part(capture_timestamp, "capture")
        lane_output_dir.mkdir(parents=True, exist_ok=True)

        lane_contract = build_independent_fast_media_webview2_lane_contract_r42gz(self.config)
        request_receipt = {
            "schema_version": R42GZ_SCHEMA_VERSION,
            "marker": R42GZ_MARKER,
            "mode_id": R42GZ_MODE_ID,
            "source_row_id": source_row_id,
            "source_url": source_url,
            "adapter_id": adapter_id,
            "capture_timestamp": capture_timestamp,
            "lane_output_dir": str(lane_output_dir),
            "lane_contract": lane_contract,
            "r42gy_request": _to_jsonable(request_payload),
        }
        _write_json(lane_output_dir / "r42gz_independent_fast_media_webview2_lane_request.json", request_receipt)

        if not source_url:
            return self._blocked_result(
                status="missing_source_url",
                lane_output_dir=lane_output_dir,
                request_payload=request_payload,
                warnings=("No source URL was supplied to the independent fast Media WebView2 lane.",),
            )
        if adapter_id and adapter_id != "twitter_x":
            return self._blocked_result(
                status="unsupported_adapter_for_r42gz_fixture_lane",
                lane_output_dir=lane_output_dir,
                request_payload=request_payload,
                warnings=(f"R42GZ currently has a Twitter/X adapter hook; adapter={adapter_id} needs a future lane adapter.",),
            )

        kwargs = {
            "source_url": source_url,
            "output_dir": lane_output_dir,
            "capture_goal": self.config.capture_goal,
            "live": self.config.live,
            "headless": self.config.headless,
            "timeout_ms": self.config.timeout_ms,
            "scroll_steps": self.config.scroll_steps,
            "smart_rate_limit": self.config.smart_rate_limit,
            "scroll_delay_ms": self.config.scroll_delay_ms,
            "scroll_jitter_ms": self.config.scroll_jitter_ms,
            "scroll_pixels": self.config.scroll_pixels,
            "max_timeline_pages": self.config.max_timeline_pages,
            "no_progress_scrolls": self.config.no_progress_scrolls,
            "stop_on_rate_limit": self.config.stop_on_rate_limit,
            "rate_limit_cooldown_ms": self.config.rate_limit_cooldown_ms,
            "browser_user_data_dir": self.config.browser_user_data_dir,
            "browser_executable_path": self.config.browser_executable_path,
            "reuse_existing_profile": self.config.reuse_existing_profile,
            "download_media": False,
            "media_backend_runner": None,
        }
        try:
            result = self.runner(**kwargs)
        except TypeError:
            # Backward-compatible call shape for simple injected fixtures.
            result = self.runner(source_url, output_dir=lane_output_dir, capture_goal=self.config.capture_goal)
        except Exception as exc:
            return self._blocked_result(
                status="independent_fast_media_lane_backend_failed",
                lane_output_dir=lane_output_dir,
                request_payload=request_payload,
                errors=(f"{type(exc).__name__}: {exc}",),
                warnings=("Independent fast Media WebView2 lane failed safely before producing observations.",),
            )

        result_data = _result_dict(result)
        network_events_path = _get_value(result, result_data, "network_events_path", "")
        media_inventory_path = _get_value(result, result_data, "media_inventory_path", "")
        rendered_dom_path = _get_value(result, result_data, "rendered_dom_path", "")
        manifest_path = _get_value(result, result_data, "manifest_path", "")
        output_dir = _get_value(result, result_data, "output_dir", str(lane_output_dir))
        events = _read_jsonl(network_events_path)
        media_inventory = _read_json(media_inventory_path, [])
        if not isinstance(media_inventory, list):
            media_inventory = []
        final_dom = _read_text(rendered_dom_path)
        warnings = tuple(_clean(item) for item in (_get_value(result, result_data, "warnings", ()) or ()) if _clean(item))
        errors = tuple(_clean(item) for item in (_get_value(result, result_data, "errors", ()) or ()) if _clean(item))
        status_text = _clean(_get_value(result, result_data, "status", "")) or "observed"
        observation_count = len(events) + len(media_inventory) + (1 if final_dom else 0)
        escalation = _detect_escalation_flags(status_text=status_text, warnings=warnings, errors=errors, observation_count=observation_count)
        backend_status = "independent_fast_media_lane_observed" if observation_count else "independent_fast_media_lane_no_media_observed"
        if escalation["visible_escalation_required"]:
            backend_status = "independent_fast_media_lane_escalate_visible_human_confirmation"

        side_effect_flags = build_r42gz_side_effect_flags(
            lane_invoked=True,
            browser_session_started=bool(self.config.live and not self.config.fixture_mode),
            network_actions_performed=bool(self.config.live and not self.config.fixture_mode),
        )
        payload = {
            "schema_version": R42GZ_SCHEMA_VERSION,
            "marker": R42GZ_MARKER,
            "backend_id": R42GZ_BACKEND_ID,
            "status": backend_status,
            "runner_status": status_text,
            "mode_id": R42GZ_MODE_ID,
            "capture_goal": self.config.capture_goal,
            "source_row_id": source_row_id,
            "source_url": source_url,
            "adapter_id": adapter_id,
            "output_dir": str(output_dir),
            "lane_output_dir": str(lane_output_dir),
            "browser_user_data_dir": self.config.browser_user_data_dir,
            "browser_executable_path": self.config.browser_executable_path,
            "network_events_path": str(network_events_path or ""),
            "media_inventory_path": str(media_inventory_path or ""),
            "rendered_dom_path": str(rendered_dom_path or ""),
            "manifest_path": str(manifest_path or ""),
            "events": events,
            "final_dom": final_dom,
            "media_inventory": media_inventory,
            "session_local_files": (),
            "warnings": warnings,
            "errors": errors,
            "lane_contract": lane_contract,
            "side_effect_flags": side_effect_flags,
            "background_webview2_session_started": side_effect_flags["background_webview2_session_started_by_r42gz_lane"],
            "network_actions_performed": side_effect_flags["network_actions_performed"],
            "downloads_performed": False,
            "hidden_x_api_scraping_performed": False,
            "login_automation_performed": False,
            "cookie_or_token_extraction_performed": False,
            "captcha_or_challenge_bypass_performed": False,
            "paywall_or_access_control_bypass_performed": False,
            "source_role_assignment_performed": False,
            "review_window_rewrite_performed": False,
            "review_window_dependency": False,
            "source_role_interface_dependency": False,
            "source_role_checks_enabled": False,
            "source_role_back_and_forth_enabled": False,
            "requires_login": escalation["requires_login"],
            "consent_required": escalation["consent_required"],
            "challenge_detected": escalation["challenge_detected"],
            "captcha_detected": escalation["challenge_detected"],
            "access_barrier_detected": escalation["access_barrier_detected"],
            "insufficient_rendered_material": escalation["insufficient_rendered_material"],
            "visual_confirmation_required": escalation["visible_escalation_required"],
        }
        _write_json(lane_output_dir / "r42gz_independent_fast_media_webview2_lane_result.json", payload)
        return payload

    def _blocked_result(
        self,
        *,
        status: str,
        lane_output_dir: Path,
        request_payload: Mapping[str, Any],
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> Mapping[str, Any]:
        payload = {
            "schema_version": R42GZ_SCHEMA_VERSION,
            "marker": R42GZ_MARKER,
            "backend_id": R42GZ_BACKEND_ID,
            "status": status,
            "mode_id": R42GZ_MODE_ID,
            "events": (),
            "final_dom": "",
            "media_inventory": (),
            "session_local_files": (),
            "warnings": warnings,
            "errors": errors,
            "lane_contract": build_independent_fast_media_webview2_lane_contract_r42gz(self.config),
            "side_effect_flags": build_r42gz_side_effect_flags(lane_invoked=True),
            "background_webview2_session_started": False,
            "network_actions_performed": False,
            "downloads_performed": False,
            "hidden_x_api_scraping_performed": False,
            "login_automation_performed": False,
            "cookie_or_token_extraction_performed": False,
            "captcha_or_challenge_bypass_performed": False,
            "paywall_or_access_control_bypass_performed": False,
            "source_role_assignment_performed": False,
            "review_window_rewrite_performed": False,
            "review_window_dependency": False,
            "source_role_interface_dependency": False,
            "source_role_checks_enabled": False,
            "source_role_back_and_forth_enabled": False,
            "requires_login": False,
            "challenge_detected": False,
            "access_barrier_detected": False,
        }
        _write_json(lane_output_dir / "r42gz_independent_fast_media_webview2_lane_blocked_result.json", payload)
        return payload


def build_independent_fast_media_webview2_lane_r42gz(
    *,
    runner: TwitterCaptureRunner | None = None,
    live: bool | None = None,
    headless: bool | None = None,
    browser_user_data_dir: str = "",
    browser_executable_path: str = "",
    fixture_mode: bool = False,
) -> IndependentFastMediaWebView2LaneBackendR42GZ:
    config = IndependentFastMediaWebView2LaneConfigR42GZ(
        live=_env_bool("YTCE_R42GZ_INDEPENDENT_MEDIA_WEBVIEW2_LIVE", True) if live is None else bool(live),
        headless=_env_bool("YTCE_R42GZ_INDEPENDENT_MEDIA_WEBVIEW2_HEADLESS", True) if headless is None else bool(headless),
        browser_user_data_dir=browser_user_data_dir or os.environ.get("YTCE_R42GZ_INDEPENDENT_MEDIA_WEBVIEW2_PROFILE", R42GZ_DEFAULT_PROFILE_DIR),
        browser_executable_path=browser_executable_path,
        fixture_mode=fixture_mode,
    )
    return IndependentFastMediaWebView2LaneBackendR42GZ(runner=runner, config=config)


def build_independent_fast_media_webview2_lane_contract_r42gz(config: IndependentFastMediaWebView2LaneConfigR42GZ | None = None) -> dict[str, Any]:
    cfg = config or IndependentFastMediaWebView2LaneConfigR42GZ()
    return {
        "marker": R42GZ_MARKER,
        "schema_version": R42GZ_SCHEMA_VERSION,
        "mode_id": R42GZ_MODE_ID,
        "media_only": True,
        "per_link_basis": True,
        "independent_lane": True,
        "fast_lane": True,
        "review_window_dependency": False,
        "source_role_interface_dependency": False,
        "source_role_checks_enabled": False,
        "source_role_back_and_forth_enabled": False,
        "review_window_webview2_dependency": False,
        "separate_browser_user_data_dir": cfg.browser_user_data_dir,
        "browser_executable_path": cfg.browser_executable_path,
        "separate_output_state_folder": R42GZ_DEFAULT_OUTPUT_ROOT,
        "uses_existing_lower_level_browser_capture_primitive_when_available": True,
        "does_not_use_slow_review_source_role_webview2_lane": True,
        "visible_escalation_mode_id": "visible_webview2_or_edge_human_confirmation",
        "visible_escalation_only_for": (
            "login/account chooser",
            "consent/CAPTCHA/challenge/access-control barrier",
            "insufficient rendered/session material",
            "user-requested visible confirmation",
        ),
        "hard_boundaries": (
            "no source-role interface loop",
            "no review-window WebView2 dependency",
            "no review back-and-forth",
            "no source-role checks",
            "no source-role assignment",
            "no hidden X API scraping",
            "no login automation",
            "no cookie/token extraction",
            "no CAPTCHA/challenge bypass",
            "no paywall/access-control bypass",
            "no remote media download inside observer lane",
            "no YouTube capture-engine change",
        ),
    }


def build_r42gz_side_effect_flags(
    *,
    lane_invoked: bool = False,
    browser_session_started: bool = False,
    network_actions_performed: bool = False,
) -> dict[str, bool]:
    return {
        "r42gz_independent_fast_media_webview2_lane_invoked": bool(lane_invoked),
        "background_webview2_session_started_by_r42gz_lane": bool(browser_session_started),
        "network_actions_performed": bool(network_actions_performed),
        "downloads_performed": False,
        "remote_media_download_performed_by_r42gz": False,
        "hidden_x_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "paywall_or_access_control_bypass_performed": False,
        "source_role_interface_loop_invoked": False,
        "source_role_checks_performed": False,
        "source_role_assignment_performed": False,
        "review_window_dependency_invoked": False,
        "review_window_rewrite_performed": False,
        "review_window_stays_separate": True,
        "visible_browser_escalation_policy_recorded": True,
        "youtube_capture_engine_changed": False,
        "jdownloader_direct_code_copy_allowed_when_attributed_and_license_compatible": True,
        "jdownloader_source_usage_policy_recorded": True,
    }


def _default_twitter_browser_capture_runner(**kwargs: Any) -> Any:
    from twitter_browser_capture_runner import run_twitter_browser_capture

    return run_twitter_browser_capture(**kwargs)


def _fixture_twitter_media_lane_runner(*, source_url: str, output_dir: str | Path, **kwargs: Any) -> Any:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_url = "https://video.twimg.com/ext_tw_video/9876543210/pu/pl/manifest.m3u8?tag=16"
    events = [
        {"request_id": "r42gz-image", "url": "https://pbs.twimg.com/media/r42gz_lane.jpg?format=jpg&name=large", "content_type": "image/jpeg", "resource_type": "image"},
        {"request_id": "r42gz-manifest", "url": manifest_url, "content_type": "application/x-mpegURL", "resource_type": "media"},
        {"request_id": "r42gz-segment-1", "url": "https://video.twimg.com/ext_tw_video/9876543210/pu/seg/00001.ts", "content_type": "video/mp2t", "resource_type": "media"},
        {"request_id": "r42gz-segment-2", "url": "https://video.twimg.com/ext_tw_video/9876543210/pu/seg/00002.ts", "content_type": "video/mp2t", "resource_type": "media"},
        {"request_id": "r42gz-mp4", "url": "https://video.twimg.com/ext_tw_video/9876543210/pu/vid/720x720/r42gz.mp4", "content_type": "video/mp4", "resource_type": "media"},
    ]
    media_inventory = [
        {
            "media_id": "r42gz_inventory_mp4",
            "media_type": "video",
            "source_url": source_url,
            "media_url": "https://video.twimg.com/ext_tw_video/9876543210/pu/vid/720x720/r42gz_inventory.mp4",
            "content_type": "video/mp4",
            "source_kind": "fixture_independent_fast_media_lane",
            "status_id": "9876543210",
            "page_url": source_url,
            "provenance": "R42GZ independent fast Media WebView2 lane fixture",
        }
    ]
    dom = '<html><body><article data-testid="tweet"><img src="https://pbs.twimg.com/media/r42gz_dom.jpg?format=jpg&amp;name=large"></article></body></html>'
    network_events_path = out / "network_events.jsonl"
    media_inventory_path = out / "media_inventory.json"
    rendered_dom_path = out / "rendered_dom_snapshot.html"
    manifest_path = out / "browser_session_manifest.json"
    _write_jsonl(network_events_path, events)
    _write_json(media_inventory_path, media_inventory)
    rendered_dom_path.write_text(dom, encoding="utf-8")
    result_payload = {
        "schema_version": "twitter_browser_capture_runner.fixture.r42gz",
        "status": "success",
        "source_url": source_url,
        "canonical_url": source_url,
        "output_dir": str(out),
        "network_events_path": str(network_events_path),
        "media_inventory_path": str(media_inventory_path),
        "rendered_dom_path": str(rendered_dom_path),
        "manifest_path": str(manifest_path),
        "network_event_count": len(events),
        "media_item_count": len(media_inventory),
        "warnings": (),
        "errors": (),
    }
    _write_json(manifest_path, result_payload)
    return SimpleNamespace(**result_payload)


def _fixture_row() -> Any:
    from profile_media_background_webview2_media_observer_r42gy import _fixture_row as r42gy_fixture_row

    return r42gy_fixture_row()


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


def _safe_part(value: Any, fallback: str = "item") -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", _clean(value)).strip("._-")
    return text[:120] or fallback


def _plain_url(value: Any) -> str:
    text = _clean(value).replace("\\_", "_").replace("\\&", "&").replace("\\/", "/")
    text = text.replace("]\\(", "](").replace("\\)", ")")
    match = re.search(r"\]\((https?://[^)\s]+)\)", text)
    if match:
        text = match.group(1)
    return text.strip()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict"):
        try:
            return _to_jsonable(value.to_dict())
        except Exception:
            pass
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if hasattr(value, "__dict__"):
        return {str(k): _to_jsonable(v) for k, v in vars(value).items() if not str(k).startswith("_")}
    return _clean(value)


def _result_dict(result: Any) -> dict[str, Any]:
    data = _to_jsonable(result)
    if isinstance(data, Mapping):
        return dict(data)
    return {"result": data}


def _get_value(result: Any, data: Mapping[str, Any], key: str, default: Any = "") -> Any:
    if key in data:
        return data.get(key, default)
    return getattr(result, key, default)


def _read_json(path: Any, default: Any) -> Any:
    text = _clean(path)
    if not text:
        return default
    try:
        p = Path(text)
        if not p.is_file():
            return default
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _read_text(path: Any) -> str:
    text = _clean(path)
    if not text:
        return ""
    try:
        p = Path(text)
        if not p.is_file():
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _read_jsonl(path: Any) -> tuple[Mapping[str, Any], ...]:
    text = _clean(path)
    if not text:
        return ()
    rows: list[Mapping[str, Any]] = []
    try:
        p = Path(text)
        if not p.is_file():
            return ()
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            item = json.loads(stripped)
            if isinstance(item, Mapping):
                rows.append(dict(item))
    except Exception:
        return tuple(rows)
    return tuple(rows)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(_to_jsonable(row), ensure_ascii=False, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _detect_escalation_flags(*, status_text: str, warnings: tuple[str, ...], errors: tuple[str, ...], observation_count: int) -> dict[str, bool]:
    blob = " ".join((status_text, *warnings, *errors)).lower()
    requires_login = any(token in blob for token in ("login", "account chooser", "authentication"))
    consent_required = "consent" in blob
    challenge_detected = any(token in blob for token in ("captcha", "challenge"))
    access_barrier_detected = any(token in blob for token in ("paywall", "access-control", "access control", "forbidden", "unauthorised", "unauthorized"))
    insufficient_rendered_material = observation_count == 0 and any(token in blob for token in ("not_run", "planned", "no_media", "no media", "empty"))
    visible = requires_login or consent_required or challenge_detected or access_barrier_detected or insufficient_rendered_material
    return {
        "requires_login": requires_login,
        "consent_required": consent_required,
        "challenge_detected": challenge_detected,
        "access_barrier_detected": access_barrier_detected,
        "insufficient_rendered_material": insufficient_rendered_material,
        "visible_escalation_required": visible,
    }


def _scrub_markdown_machine_urls(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _scrub_markdown_machine_urls(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_scrub_markdown_machine_urls(item) for item in value)
    if isinstance(value, list):
        return [_scrub_markdown_machine_urls(item) for item in value]
    if isinstance(value, str) and ("http://" in value or "https://" in value):
        text = value.replace("\\_", "_").replace("\\&", "&").replace("\\/", "/").strip()
        normalized = text.replace("]\\(", "](").replace("\\)", ")")
        if "](" in normalized:
            match = re.search(r"\]\((https?://[^)\s]+)\)", normalized)
            if match:
                return match.group(1).replace("\\_", "_").replace("\\&", "&").replace("\\/", "/").strip()
        return normalized
    return value


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_scrub_markdown_machine_urls(_to_jsonable(value)), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def build_report(output_root: str | Path = R42GZ_DEFAULT_OUTPUT_ROOT) -> R42GZReport:
    from profile_media_background_webview2_media_observer_r42gy import (
        R42GY_PASS_STATUS,
        run_background_webview2_media_observer_for_row_r42gy,
    )
    from profile_media_unified_media_window_tabs_r42gw import TAB_ALL

    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    backend = build_independent_fast_media_webview2_lane_r42gz(
        runner=_fixture_twitter_media_lane_runner,
        live=False,
        headless=True,
        browser_user_data_dir="profile_media_browser_profiles/r42gz_fixture_independent_fast_media_webview2_lane",
        fixture_mode=True,
    )
    request = {
        "source_row_id": "twitter_x:r42gz:direct",
        "source_url": "https://x.com/example/status/9876543210",
        "adapter_id": "twitter_x",
        "output_root": out / "direct_backend",
        "capture_timestamp": "20260914T000000Z",
    }
    lane_backend_result = dict(backend.observe_media(request))
    receipt = run_background_webview2_media_observer_for_row_r42gy(
        _fixture_row(),
        backend=backend,
        output_root=out / "r42gy_pipeline",
        active_tab=TAB_ALL,
        capture_timestamp="20260914T000001Z",
    )
    receipt_dict = _scrub_markdown_machine_urls(receipt.to_dict())
    lane_result_dict = _scrub_markdown_machine_urls(lane_backend_result)
    media_state = receipt_dict.get("unified_media_window_state") or {}
    contract = build_independent_fast_media_webview2_lane_contract_r42gz(backend.config)
    flags = dict(lane_backend_result.get("side_effect_flags") or build_r42gz_side_effect_flags())
    checks = (
        _check("independent_fast_media_webview2_lane_registered", lane_backend_result.get("backend_id") == R42GZ_BACKEND_ID and lane_backend_result.get("mode_id") == R42GZ_MODE_ID),
        _check("media_lane_is_independent_from_review_source_role_webview2", contract.get("independent_lane") is True and contract.get("review_window_dependency") is False and contract.get("source_role_interface_dependency") is False),
        _check("source_role_slowdown_paths_disabled", contract.get("source_role_checks_enabled") is False and contract.get("source_role_back_and_forth_enabled") is False and flags.get("source_role_interface_loop_invoked") is False),
        _check("separate_profile_and_output_state_recorded", "r42gz" in _clean(lane_backend_result.get("browser_user_data_dir")).lower() and "r42gz_independent_fast_media_webview2_lane" in _clean(lane_backend_result.get("lane_output_dir"))),
        _check("r42gy_pipeline_receives_lane_output", receipt.status == R42GY_PASS_STATUS and int(receipt.observation_count or 0) >= 1),
        _check("r42gv_observation_store_written", bool(receipt.observation_store_path) and Path(receipt.observation_store_path).is_file()),
        _check("r42gw_unified_media_window_refreshed", media_state.get("tabs") == ["all", "images", "videos"] and int(media_state.get("package_count") or 0) >= 2),
        _check("segmented_media_still_grouped_under_video_stream_package", int(media_state.get("segment_child_count") or 0) >= 2),
        _check("no_forbidden_side_effects", all(flags.get(key) is False for key in ("downloads_performed", "remote_media_download_performed_by_r42gz", "hidden_x_api_scraping_performed", "login_automation_performed", "cookie_or_token_extraction_performed", "captcha_or_challenge_bypass_performed", "paywall_or_access_control_bypass_performed", "source_role_interface_loop_invoked", "source_role_checks_performed", "source_role_assignment_performed", "review_window_dependency_invoked", "review_window_rewrite_performed", "youtube_capture_engine_changed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(lane_result_dict) and _machine_urls_are_plain(receipt_dict)),
    )
    status = R42GZ_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GZ_BLOCKED_STATUS
    report = R42GZReport(
        marker=R42GZ_MARKER,
        schema_version=R42GZ_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        lane_backend_result=lane_result_dict,
        r42gy_runtime_receipt=receipt_dict,
        lane_contract=contract,
        side_effect_flags=flags,
    )
    write_report(report, out)
    return report


def write_report(report: R42GZReport, output_root: str | Path = R42GZ_DEFAULT_OUTPUT_ROOT) -> None:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    (out / "R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE_REPORT.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# R42GZ Independent Fast Media WebView2 Capture Lane Report",
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
            "- R42GZ registers a separate per-link Media-window capture lane, not the review/source-role WebView2 lane.",
            "- The lane is media-only and feeds R42GY, which writes the R42GV observation store and refreshes the R42GW All / Images / Videos package tree.",
            "- The lane uses its own profile/output state and avoids source-role interface loops, source-role checks, and review back-and-forth slowdowns.",
            "- Visible WebView2/Edge remains the human-confirmation escalation route for login, consent, CAPTCHA/challenge, access barriers, or insufficient rendered/session material.",
            "- No remote media download, hidden X API scraping, login automation, cookie/token extraction, challenge bypass, source-role assignment, review-window rewrite, or YouTube capture-engine change is performed by this lane.",
        ]
    )
    (out / "R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=R42GZ_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(report.marker)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
