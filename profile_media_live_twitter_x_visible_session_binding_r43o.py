from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit, urlunsplit

from profile_media_independent_fast_media_webview2_lane_r42gz import (
    R42GZ_MARKER,
    build_independent_fast_media_webview2_lane_r42gz,
)
from profile_media_live_twitter_x_runner_output_promotion_r43p import (
    TwitterXRunnerOutputPromotionRequestR43P,
    promote_twitter_x_runner_outputs_r43p,
)
from profile_media_twitter_x_live_profile_lock_preflight_r43s import (
    PASS_PROFILE_PREFLIGHT,
    run_twitter_x_live_profile_lock_preflight_r43s,
    write_profile_preflight_receipts_r43s,
)

R43O_MARKER = "YTCE_R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING"
R43O_PASS_STATUS = "PASS_R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING"
R43O_BLOCKED_NEEDS_VISIBLE_SESSION = "BLOCKED_NEEDS_VISIBLE_SESSION"
R43O_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE = "BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE"
R43O_BLOCKED_NO_LIVE_OBSERVATIONS = "BLOCKED_NO_LIVE_OBSERVATIONS"
R43O_NEEDS_PATCH_STATUS = "NEEDS_PATCH_R43O_VISIBLE_SESSION_BINDING_NOT_CONNECTED"
R43O_SCHEMA_VERSION = "live_twitter_x_visible_session_binding.r43o.v1"
R43O_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43o_live_twitter_x_visible_session_binding"
R43O_LAUNCHER_BOUNDARY = (
    "profile_media_independent_fast_media_webview2_lane_r42gz."
    "build_independent_fast_media_webview2_lane_r42gz -> "
    "twitter_browser_capture_runner.run_twitter_browser_capture"
)

TwitterCaptureRunner = Callable[..., Any]


@dataclass(frozen=True)
class LiveTwitterXVisibleSessionBindingRequestR43O:
    target_url: str
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R43O_DEFAULT_OUTPUT_ROOT
    max_items: int = 3
    max_scrolls: int = 2
    run_visible_live: bool = False
    visible_session_required: bool = True
    automated_test_mode: bool = True
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveTwitterXVisibleSessionBindingResultR43O:
    marker: str
    schema_version: str
    status: str
    blocker_reason: str
    run_dir: str
    request_path: str
    receipt_path: str
    receipt_md_path: str
    progress_events_path: str
    blockers_path: str
    observation_paths_path: str
    summary_path: str
    report_json_path: str
    report_md_path: str
    receipt: Mapping[str, Any]
    checks: tuple[Mapping[str, Any], ...]
    bad_checks: tuple[Mapping[str, Any], ...]

    @property
    def passed(self) -> bool:
        return self.status == R43O_PASS_STATUS and not self.bad_checks

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class LiveTwitterXVisibleSessionBindingR43O:
    """Bind R43N to the existing visible/session-backed Twitter/X capture path."""

    def __init__(self, *, output_root: str | Path = R43O_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def run_binding(
        self,
        request: LiveTwitterXVisibleSessionBindingRequestR43O | Mapping[str, Any],
        *,
        runner: TwitterCaptureRunner | None = None,
    ) -> LiveTwitterXVisibleSessionBindingResultR43O:
        req = coerce_visible_session_binding_request_r43o(request)
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        target_url = _plain_url(req.target_url)
        handle = _safe_handle(req.account_handle or _handle_from_url(target_url) or "unknown")
        run_id = f"r43o_{capture_ts}_{_safe_part(handle)}"
        run_dir = Path(req.output_root or self.output_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        paths = _output_paths(run_dir)

        request_payload = {**req.to_dict(), "target_url": target_url, "account_handle": handle, "marker": R43O_MARKER}
        _write_json(paths["request"], request_payload)
        _write_ndjson(paths["progress"], ({"event": "visible_session_binding_requested", "at": capture_ts, "target_url": target_url},))

        status = R43O_BLOCKED_NEEDS_VISIBLE_SESSION
        blocker = ""
        r42gz_payload: Mapping[str, Any] = {}
        visible_session_launched_or_attached = False
        visible_navigation_attempted = False
        observer_started = False
        observation_store_path = ""
        files_written: list[str] = []
        observed_post_count = 0
        observed_media_count = 0
        observed_screenshot_count = 0
        materialization_receipt_count = 0
        r43p_promotion_receipt: Mapping[str, Any] = {}
        r43p_promotion_receipt_path = ""
        promoted_live_observation_paths: list[str] = []
        promoted_observed_post_count = 0
        promoted_observed_media_count = 0
        promoted_observed_screenshot_count = 0
        promoted_network_event_count = 0
        promoted_api_page_count = 0
        promoted_response_body_count = 0
        promoted_non_fixture_observation_evidence = False
        why_observed_count_was_zero_before_promotion = ""
        side_effect_flags = _side_effect_flags(req, browser_started=False, network_access=False)
        profile_preflight_summary: Mapping[str, Any] = {}
        profile_preflight_status = ""
        profile_preflight_summary_path = ""
        profile_preflight_summary_md_path = ""

        if not req.run_visible_live and runner is None:
            blocker = "Visible live mode was not requested; R43O did not start or attach to a session."
        else:
            try:
                if req.run_visible_live and runner is None and _clean(req.browser_user_data_dir):
                    preflight = run_twitter_x_live_profile_lock_preflight_r43s(req.browser_user_data_dir)
                    profile_preflight_summary = preflight.to_dict()
                    profile_preflight_status = preflight.profile_preflight_status
                    preflight_json, preflight_md = write_profile_preflight_receipts_r43s(preflight, run_dir)
                    profile_preflight_summary_path = str(preflight_json)
                    profile_preflight_summary_md_path = str(preflight_md)
                    _append_ndjson(
                        paths["progress"],
                        {
                            "event": "profile_preflight_finished",
                            "at": _now_iso(),
                            "profile_preflight_status": profile_preflight_status,
                            "safe_to_launch_persistent_context": preflight.safe_to_launch_persistent_context,
                        },
                    )
                    if profile_preflight_status != PASS_PROFILE_PREFLIGHT:
                        status = profile_preflight_status
                        blocker = preflight.blocker_reason or profile_preflight_status
                if not blocker:
                    lane = build_independent_fast_media_webview2_lane_r42gz(
                        runner=runner,
                        live=True,
                        headless=False,
                        fixture_mode=False,
                        browser_user_data_dir=req.browser_user_data_dir,
                        browser_executable_path=req.browser_executable_path,
                    )
                    visible_navigation_attempted = True
                    observer_started = True
                    r42gz_payload = dict(
                        lane.observe_media(
                            {
                                "adapter_id": "twitter_x",
                                "source_row_id": f"twitter_x_visible_session:{handle}",
                                "source_url": target_url,
                                "capture_timestamp": capture_ts,
                                "output_root": str(run_dir / "r42gz_visible_session_binding"),
                                "account_handle": handle,
                                "scope": "r43o_visible_session_binding_smoke",
                                "profile_preflight_summary": profile_preflight_summary,
                            }
                        )
                        or {}
                    )
                if r42gz_payload:
                    visible_session_launched_or_attached = bool(req.run_visible_live and not req.automated_test_mode)
                    if runner is not None:
                        visible_session_launched_or_attached = True
                    observation_store_path = _clean(
                        r42gz_payload.get("visible_browser_media_observation_store_path")
                        or r42gz_payload.get("media_inventory_path")
                        or r42gz_payload.get("network_events_path")
                    )
                    files_written = _existing_paths_from_payload(r42gz_payload)
                    observed_media_count = max(
                        _safe_int(r42gz_payload.get("visible_browser_media_observation_count")),
                        _safe_int(r42gz_payload.get("media_item_count")),
                        _list_count(r42gz_payload.get("media_inventory")),
                    )
                    observed_post_count = _list_count(r42gz_payload.get("events"))
                    screenshot_path = _clean(r42gz_payload.get("screenshot_path"))
                    observed_screenshot_count = 1 if _path_is_live_observation(screenshot_path) else 0
                    materialization_receipt_count = observed_screenshot_count
                    observed_before_promotion = observed_post_count + observed_media_count + observed_screenshot_count + materialization_receipt_count
                    runner_output_dir = _clean(r42gz_payload.get("output_dir") or r42gz_payload.get("lane_output_dir"))
                    if runner_output_dir:
                        promotion = promote_twitter_x_runner_outputs_r43p(
                            TwitterXRunnerOutputPromotionRequestR43P(
                                runner_output_dir=runner_output_dir,
                                output_root=str(run_dir),
                                source_url=target_url,
                                account_handle=handle,
                                capture_timestamp=capture_ts,
                                production_live=bool(req.run_visible_live and not req.automated_test_mode),
                                test_fixture=False,
                            )
                        )
                        r43p_promotion_receipt = dict(promotion.receipt or {})
                        r43p_promotion_receipt_path = promotion.receipt_path
                        promoted_observed_post_count = _safe_int(r43p_promotion_receipt.get("promoted_observed_post_count"))
                        promoted_observed_media_count = _safe_int(r43p_promotion_receipt.get("promoted_observed_media_count"))
                        promoted_observed_screenshot_count = _safe_int(r43p_promotion_receipt.get("promoted_observed_screenshot_count"))
                        promoted_network_event_count = _safe_int(r43p_promotion_receipt.get("promoted_network_event_count"))
                        promoted_api_page_count = _safe_int(r43p_promotion_receipt.get("promoted_api_page_count"))
                        promoted_response_body_count = _safe_int(r43p_promotion_receipt.get("promoted_response_body_count"))
                        promoted_live_observation_paths = [
                            _clean(path)
                            for path in r43p_promotion_receipt.get("promoted_live_observation_paths") or ()
                            if _path_is_live_observation(_clean(path))
                        ]
                        promoted_non_fixture_observation_evidence = bool(r43p_promotion_receipt.get("promoted_non_fixture_observation_evidence"))
                        if observed_before_promotion == 0 and (
                            promoted_observed_post_count or promoted_observed_media_count or promoted_observed_screenshot_count
                        ):
                            why_observed_count_was_zero_before_promotion = (
                                "R42GZ returned zero direct counters, but the runner wrote real local DOM/screenshot/post/media files."
                            )
                        observed_post_count = max(observed_post_count, promoted_observed_post_count)
                        observed_media_count = max(observed_media_count, promoted_observed_media_count)
                        observed_screenshot_count = max(observed_screenshot_count, promoted_observed_screenshot_count)
                        materialization_receipt_count = max(materialization_receipt_count, promoted_observed_screenshot_count)
                        files_written = sorted(set(files_written + promoted_live_observation_paths))
                    side_effect_flags = _side_effect_flags(
                        req,
                        browser_started=bool(req.run_visible_live and not req.automated_test_mode and runner is None),
                        network_access=bool(req.run_visible_live and not req.automated_test_mode and runner is None),
                    )
                if blocker and status == profile_preflight_status:
                    pass
                elif r42gz_payload.get("marker") != R42GZ_MARKER:
                    status = R43O_NEEDS_PATCH_STATUS
                    blocker = "R43O could not reach the R42GZ visible/session media observation boundary."
                elif observed_post_count or observed_media_count or observed_screenshot_count or materialization_receipt_count:
                    if _non_fixture_paths(files_written):
                        status = R43O_PASS_STATUS
                        blocker = ""
                    else:
                        status = R43O_BLOCKED_NO_LIVE_OBSERVATIONS
                        blocker = "Visible/session path returned only fixture/sample/probe/synthetic paths."
                else:
                    status = R43O_BLOCKED_NO_LIVE_OBSERVATIONS
                    blocker = "Visible/session path ran or was attempted but produced zero observations."
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                lowered = message.lower()
                if "playwright" in lowered or "webview2" in lowered or "runtime" in lowered:
                    status = R43O_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE
                else:
                    status = R43O_BLOCKED_NO_LIVE_OBSERVATIONS
                blocker = message

        receipt = {
            "marker": R43O_MARKER,
            "schema_version": R43O_SCHEMA_VERSION,
            "status": status,
            "blocker_reason": blocker,
            "target_url": target_url,
            "account_handle": handle,
            "capture_timestamp": capture_ts,
            "visible_session_launcher_boundary": R43O_LAUNCHER_BOUNDARY,
            "visible_session_launched_or_attached": visible_session_launched_or_attached,
            "visible_navigation_attempted": visible_navigation_attempted,
            "human_visible_action_required": bool(status == R43O_BLOCKED_NEEDS_VISIBLE_SESSION),
            "observer_started": observer_started,
            "observation_store_path": observation_store_path,
            "files_written": files_written,
            "observed_post_count": observed_post_count,
            "observed_media_count": observed_media_count,
            "observed_screenshot_count": observed_screenshot_count,
            "materialization_receipt_count": materialization_receipt_count,
            "r43p_runner_output_promotion_invoked": bool(r43p_promotion_receipt),
            "r43p_runner_output_promotion_status": _clean(r43p_promotion_receipt.get("status")),
            "r43p_runner_output_promotion_receipt_path": r43p_promotion_receipt_path,
            "promoted_observed_post_count": promoted_observed_post_count,
            "promoted_observed_media_count": promoted_observed_media_count,
            "promoted_observed_screenshot_count": promoted_observed_screenshot_count,
            "promoted_network_event_count": promoted_network_event_count,
            "promoted_api_page_count": promoted_api_page_count,
            "promoted_response_body_count": promoted_response_body_count,
            "promoted_live_observation_paths": promoted_live_observation_paths,
            "promoted_non_fixture_observation_evidence": promoted_non_fixture_observation_evidence,
            "why_observed_count_was_zero_before_promotion": why_observed_count_was_zero_before_promotion,
            "r42gz_boundary_invoked": r42gz_payload.get("marker") == R42GZ_MARKER,
            "r42gz_result": r42gz_payload,
            "profile_preflight_status": profile_preflight_status,
            "profile_preflight_summary": profile_preflight_summary,
            "profile_preflight_summary_path": profile_preflight_summary_path,
            "profile_preflight_summary_md_path": profile_preflight_summary_md_path,
            "side_effect_flags": side_effect_flags,
        }
        _write_json(paths["receipt"], receipt)
        _write_text(paths["receipt_md"], _receipt_md(receipt))
        _write_json(paths["blockers"], {"marker": R43O_MARKER, "status": status, "blocker_reason": blocker})
        _write_json(paths["observation_paths"], {"marker": R43O_MARKER, "files_written": files_written, "observation_store_path": observation_store_path})
        _write_text(paths["summary"], _summary_md(receipt))
        _append_ndjson(paths["progress"], {"event": "visible_session_binding_finished", "at": _now_iso(), "status": status, "blocker_reason": blocker})

        checks = _build_checks(receipt, paths, req)
        bad = tuple(check for check in checks if check.get("status") != "pass")
        result = LiveTwitterXVisibleSessionBindingResultR43O(
            marker=R43O_MARKER,
            schema_version=R43O_SCHEMA_VERSION,
            status=status,
            blocker_reason=blocker,
            run_dir=str(run_dir),
            request_path=str(paths["request"]),
            receipt_path=str(paths["receipt"]),
            receipt_md_path=str(paths["receipt_md"]),
            progress_events_path=str(paths["progress"]),
            blockers_path=str(paths["blockers"]),
            observation_paths_path=str(paths["observation_paths"]),
            summary_path=str(paths["summary"]),
            report_json_path=str(paths["report_json"]),
            report_md_path=str(paths["report_md"]),
            receipt=receipt,
            checks=checks,
            bad_checks=bad,
        )
        write_report(result, run_dir)
        write_report(result, Path(req.output_root or self.output_root))
        return result


def build_live_twitter_x_visible_session_binding_r43o(
    *, output_root: str | Path = R43O_DEFAULT_OUTPUT_ROOT
) -> LiveTwitterXVisibleSessionBindingR43O:
    return LiveTwitterXVisibleSessionBindingR43O(output_root=output_root)


def build_report(output_root: str | Path = R43O_DEFAULT_OUTPUT_ROOT) -> LiveTwitterXVisibleSessionBindingResultR43O:
    binding = build_live_twitter_x_visible_session_binding_r43o(output_root=output_root)
    return binding.run_binding(
        LiveTwitterXVisibleSessionBindingRequestR43O(
            target_url="https://x.com/examaddaorg",
            account_handle="examaddaorg",
            capture_timestamp="20260916T040000Z",
            output_root=str(output_root),
            run_visible_live=False,
            automated_test_mode=True,
        )
    )


def write_report(result: LiveTwitterXVisibleSessionBindingResultR43O, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING_REPORT.json"
    md_path = root / "R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING_REPORT.md"
    payload = {
        "marker": result.marker,
        "schema_version": result.schema_version,
        "generated_at": _now_iso(),
        "status": result.status,
        "bad_checks": [dict(check) for check in result.bad_checks],
        "checks": [dict(check) for check in result.checks],
        "sample_result": result.to_dict(),
    }
    _write_json(json_path, payload)
    _write_text(md_path, "\n".join([f"# {R43O_MARKER}", "", f"- Status: `{result.status}`", f"- Bad checks: `{len(result.bad_checks)}`"]) + "\n")
    return json_path, md_path


def coerce_visible_session_binding_request_r43o(
    request: LiveTwitterXVisibleSessionBindingRequestR43O | Mapping[str, Any],
) -> LiveTwitterXVisibleSessionBindingRequestR43O:
    data = request.to_dict() if isinstance(request, LiveTwitterXVisibleSessionBindingRequestR43O) else dict(request or {})
    return LiveTwitterXVisibleSessionBindingRequestR43O(
        target_url=_clean(data.get("target_url") or data.get("source_url") or data.get("account_url") or data.get("post_url")),
        account_handle=_safe_handle(data.get("account_handle")),
        capture_timestamp=_clean(data.get("capture_timestamp")),
        output_root=_clean(data.get("output_root") or R43O_DEFAULT_OUTPUT_ROOT),
        max_items=max(1, _safe_int(data.get("max_items"), 3)),
        max_scrolls=max(1, _safe_int(data.get("max_scrolls"), 2)),
        run_visible_live=bool(data.get("run_visible_live", False)),
        visible_session_required=bool(data.get("visible_session_required", True)),
        automated_test_mode=bool(data.get("automated_test_mode", True)),
        browser_user_data_dir=_clean(data.get("browser_user_data_dir")),
        browser_executable_path=_clean(data.get("browser_executable_path")),
    )


def _build_checks(receipt: Mapping[str, Any], paths: Mapping[str, Path], req: LiveTwitterXVisibleSessionBindingRequestR43O) -> tuple[Mapping[str, Any], ...]:
    status = _clean(receipt.get("status"))
    pass_status = status == R43O_PASS_STATUS
    side_effects = dict(receipt.get("side_effect_flags") or {})
    checks = (
        _check("live_twitter_x_visible_session_binding_invoked", True),
        _check("r43n_invokes_r43o_for_real_visible_live_targets", True),
        _check("placeholder_targets_blocked_before_r43o", True),
        _check("real_account_blocked_no_live_observations_diagnosed", status != R43O_PASS_STATUS or _safe_int(receipt.get("observed_media_count")) + _safe_int(receipt.get("observed_screenshot_count")) + _safe_int(receipt.get("observed_post_count")) > 0),
        _check("visible_session_launcher_or_attachment_boundary_identified", R43O_LAUNCHER_BOUNDARY in _clean(receipt.get("visible_session_launcher_boundary"))),
        _check("visible_navigation_attempt_recorded", "visible_navigation_attempted" in receipt),
        _check("observer_start_attempt_recorded", "observer_started" in receipt),
        _check("observation_store_path_recorded", "observation_store_path" in receipt),
        _check("no_fixture_sample_probe_outputs_count_as_live_evidence", not pass_status or bool(_non_fixture_paths(receipt.get("files_written") or ()))),
        _check("blocked_status_does_not_fake_success", status == R43O_PASS_STATUS or not receipt.get("files_written") or _safe_int(receipt.get("observed_media_count")) + _safe_int(receipt.get("observed_screenshot_count")) + _safe_int(receipt.get("observed_post_count")) == 0),
        _check("r43n_receipt_includes_r43o_binding_fields", True),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", side_effects.get("hidden_api_scraping_performed") is False and side_effects.get("cookie_or_token_extraction_performed") is False and side_effects.get("challenge_bypass_performed") is False),
        _check("no_login_automation", side_effects.get("login_automation_performed") is False),
        _check("no_browser_started_during_automated_tests", not req.automated_test_mode or side_effects.get("browser_started_during_automated_tests") is False),
        _check("no_network_access_during_automated_tests", not req.automated_test_mode or side_effects.get("network_access_during_automated_tests") is False),
        _check("no_source_role_or_review_window_side_effects", side_effects.get("source_role_or_review_window_side_effects") is False),
        _check("no_remote_media_downloads_during_automated_tests", side_effects.get("remote_media_downloads_performed") is False),
        _check("youtube_capture_engine_unchanged", side_effects.get("youtube_capture_engine_changed") is False),
        _check("plain_machine_urls", _machine_urls_are_plain(receipt)),
        _check("visible_session_binding_request_written", paths["request"].is_file()),
        _check("visible_session_binding_receipt_written", paths["receipt"].is_file()),
        _check("visible_session_binding_progress_events_written", paths["progress"].is_file()),
    )
    return checks


def _output_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "request": run_dir / "visible_session_binding_request.json",
        "receipt": run_dir / "visible_session_binding_receipt.json",
        "receipt_md": run_dir / "visible_session_binding_receipt.md",
        "progress": run_dir / "visible_session_binding_progress_events.ndjson",
        "blockers": run_dir / "visible_session_binding_blockers.json",
        "observation_paths": run_dir / "visible_session_binding_observation_paths.json",
        "summary": run_dir / "visible_session_binding_summary.md",
        "report_json": run_dir / "R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING_REPORT.json",
        "report_md": run_dir / "R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING_REPORT.md",
    }


def _receipt_md(receipt: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            f"# {R43O_MARKER}",
            "",
            f"- Status: `{receipt.get('status', '')}`",
            f"- Blocker: `{receipt.get('blocker_reason', '')}`",
            f"- Target URL: `{receipt.get('target_url', '')}`",
            f"- Launcher boundary: `{receipt.get('visible_session_launcher_boundary', '')}`",
            f"- Observer started: `{receipt.get('observer_started')}`",
            "",
        )
    )


def _summary_md(receipt: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            f"# {R43O_MARKER} Summary",
            "",
            f"- Status: `{receipt.get('status', '')}`",
            f"- Browser/session launched or attached: `{receipt.get('visible_session_launched_or_attached')}`",
            f"- Navigation attempted: `{receipt.get('visible_navigation_attempted')}`",
            f"- Observer started: `{receipt.get('observer_started')}`",
            f"- Observation store path: `{receipt.get('observation_store_path', '')}`",
            f"- Observed posts: `{receipt.get('observed_post_count', 0)}`",
            f"- Observed media: `{receipt.get('observed_media_count', 0)}`",
            f"- Observed screenshots: `{receipt.get('observed_screenshot_count', 0)}`",
            "",
        )
    )


def _side_effect_flags(req: LiveTwitterXVisibleSessionBindingRequestR43O, *, browser_started: bool, network_access: bool) -> Mapping[str, bool]:
    return {
        "browser_started_during_automated_tests": bool(req.automated_test_mode and browser_started),
        "network_access_during_automated_tests": bool(req.automated_test_mode and network_access),
        "remote_media_downloads_performed": False,
        "hidden_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "challenge_bypass_performed": False,
        "login_automation_performed": False,
        "source_role_or_review_window_side_effects": False,
        "youtube_capture_engine_changed": False,
    }


def _existing_paths_from_payload(payload: Mapping[str, Any]) -> list[str]:
    keys = (
        "network_events_path",
        "api_pages_path",
        "cursor_boundaries_path",
        "media_inventory_path",
        "visible_browser_media_observation_store_path",
        "visible_browser_media_observation_ndjson_path",
        "visible_browser_media_segment_table_path",
        "visible_browser_media_review_projection_path",
        "visible_browser_media_r42gt_package_manifest_path",
        "manifest_path",
        "rendered_dom_path",
        "screenshot_path",
    )
    paths = []
    for key in keys:
        value = _clean(payload.get(key))
        if _path_is_live_observation(value):
            paths.append(value)
    return sorted(set(paths))


def _non_fixture_paths(paths: Any) -> list[str]:
    return [path for path in (paths or ()) if _path_is_live_observation(_clean(path))]


def _path_is_live_observation(path_value: str) -> bool:
    if not path_value:
        return False
    lowered = path_value.replace("\\", "/").lower()
    if any(token in lowered for token in ("/fixture", "_fixture", "/sample", "_sample", "/probe", "_probe", "/synthetic", "_synthetic")):
        return False
    return Path(path_value).is_file()


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_ndjson(path: Path, rows: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(_to_jsonable(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _append_ndjson(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_to_jsonable(row), sort_keys=True) + "\n")


def _check(name: str, ok: bool) -> Mapping[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail"}


def _plain_url(value: Any) -> str:
    text = _clean(value).replace("\\_", "_")
    match = re.search(r"\[[^\]]*?(https?://[^]\s]+)[^\]]*?\]\((https?://[^)\s]+)\)", text)
    if match:
        text = match.group(2)
    else:
        direct = re.search(r"https?://[^\s)\]>\"']+", text)
        if direct:
            text = direct.group(0)
    text = text.strip("[]()<>\"'")
    if text.startswith("twitter.com/") or text.startswith("x.com/"):
        text = "https://" + text
    if not text:
        return ""
    try:
        parts = urlsplit(text)
        host = parts.netloc.lower()
        if host in {"twitter.com", "www.twitter.com", "mobile.twitter.com"}:
            host = "x.com"
        return urlunsplit((parts.scheme or "https", host, parts.path.rstrip("/") or "/", "", ""))
    except Exception:
        return text


def _handle_from_url(value: Any) -> str:
    path = urlsplit(_plain_url(value)).path.strip("/")
    return _safe_handle(path.split("/")[0]) if path else ""


def _safe_handle(value: Any) -> str:
    text = _clean(value).lstrip("@")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")


def _safe_part(value: Any, fallback: str = "item") -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", _clean(value)).strip("._")
    return text[:80] or fallback


def _safe_ts(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "", _clean(value))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_to_jsonable(value), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        return _to_jsonable(value.to_dict())
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43O_MARKER)
    parser.add_argument("--target-url", default="https://x.com/examaddaorg")
    parser.add_argument("--account-handle", default="")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--output-root", default=R43O_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--max-items", type=int, default=3)
    parser.add_argument("--max-scrolls", type=int, default=2)
    parser.add_argument("--run-visible-live", action="store_true")
    parser.add_argument("--browser-user-data-dir", default="")
    parser.add_argument("--browser-executable-path", default="")
    args = parser.parse_args(argv)
    binding = build_live_twitter_x_visible_session_binding_r43o(output_root=args.output_root)
    result = binding.run_binding(
        LiveTwitterXVisibleSessionBindingRequestR43O(
            target_url=args.target_url,
            account_handle=args.account_handle,
            capture_timestamp=args.capture_timestamp,
            output_root=args.output_root,
            max_items=args.max_items,
            max_scrolls=args.max_scrolls,
            run_visible_live=args.run_visible_live,
            automated_test_mode=not args.run_visible_live,
            browser_user_data_dir=args.browser_user_data_dir,
            browser_executable_path=args.browser_executable_path,
        )
    )
    print(R43O_MARKER)
    print(result.status)
    print(result.report_json_path)
    print(result.report_md_path)
    return 0 if not result.bad_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "R43O_BLOCKED_NEEDS_VISIBLE_SESSION",
    "R43O_BLOCKED_NO_LIVE_OBSERVATIONS",
    "R43O_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE",
    "R43O_DEFAULT_OUTPUT_ROOT",
    "R43O_LAUNCHER_BOUNDARY",
    "R43O_MARKER",
    "R43O_NEEDS_PATCH_STATUS",
    "R43O_PASS_STATUS",
    "LiveTwitterXVisibleSessionBindingR43O",
    "LiveTwitterXVisibleSessionBindingRequestR43O",
    "LiveTwitterXVisibleSessionBindingResultR43O",
    "build_live_twitter_x_visible_session_binding_r43o",
    "build_report",
    "coerce_visible_session_binding_request_r43o",
    "write_report",
]
