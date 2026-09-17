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
from profile_media_twitter_x_account_media_ledger_r43a import build_twitter_x_account_media_ledger_exporter_r43a
from profile_media_twitter_x_account_timeline_runner_r43b import (
    TwitterXAccountTimelineRunnerConfigR43B,
    build_twitter_x_account_timeline_runner_r43b,
)
from profile_media_twitter_x_account_tracking_export_surface_r43d import build_twitter_x_account_tracking_export_surface_r43d
from profile_media_universal_social_account_tracking_r43e import build_universal_social_account_tracking_registry_r43e
from profile_media_universal_social_export_surface_ui_routing_r43f import build_universal_social_export_surface_router_r43f
from profile_media_universal_social_batch_account_intake_platform_url_detection_r43g import build_universal_social_batch_account_intake_router_r43g
from profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h import build_universal_social_batch_queue_router_r43h
from profile_media_universal_social_batch_queue_workbench_controls_r43i import build_universal_social_batch_queue_workbench_r43i
from profile_media_universal_social_batch_queue_workbench_panel_r43j import build_universal_social_batch_queue_workbench_panel_r43j
from profile_media_universal_social_batch_workbench_gui_state_bridge_r43k import build_universal_social_batch_workbench_gui_state_bridge_r43k
from profile_media_universal_social_batch_workbench_app_shell_commands_r43l import (
    UniversalSocialBatchWorkbenchAppShellCommandRequestR43L,
    build_universal_social_batch_workbench_app_shell_commands_r43l,
)
from profile_media_live_twitter_x_visible_session_binding_r43o import (
    R43O_BLOCKED_NEEDS_VISIBLE_SESSION,
    R43O_BLOCKED_NO_LIVE_OBSERVATIONS,
    R43O_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE,
    R43O_LAUNCHER_BOUNDARY,
    R43O_NEEDS_PATCH_STATUS,
    R43O_PASS_STATUS,
    LiveTwitterXVisibleSessionBindingRequestR43O,
    build_live_twitter_x_visible_session_binding_r43o,
)

R43N_MARKER = "YTCE_R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT"
R43N_PASS_STATUS = "PASS_R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT"
R43N_BLOCKED_PLACEHOLDER_TARGET_URL = "BLOCKED_PLACEHOLDER_TARGET_URL"
R43N_BLOCKED_NEEDS_VISIBLE_SESSION = "BLOCKED_NEEDS_VISIBLE_SESSION"
R43N_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE = "BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE"
R43N_BLOCKED_NO_LIVE_OBSERVATIONS = "BLOCKED_NO_LIVE_OBSERVATIONS"
R43N_NEEDS_PATCH_STATUS = "NEEDS_PATCH_R43N_LIVE_SMOKE_PATH_NOT_CONNECTED"
R43N_NEEDS_PATCH_R43O_STATUS = "NEEDS_PATCH_R43O_VISIBLE_SESSION_BINDING_NOT_CONNECTED"
R43N_SCHEMA_VERSION = "live_twitter_x_single_account_smoke_harness.r43n.v1"
R43N_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43n_live_twitter_x_single_account_smoke_harness_real_observation_receipt"
R43N_ROUTE_CHAIN = "R43L -> R43J/R43K -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D -> R43B -> R42GZ -> R42GY/R42GV -> R43A/R43C"

TwitterCaptureRunner = Callable[..., Any]
VisibleSessionBindingRunner = Any


@dataclass(frozen=True)
class LiveTwitterXSingleAccountSmokeRequestR43N:
    account_url: str = "https://x.com/example"
    post_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R43N_DEFAULT_OUTPUT_ROOT
    max_items: int = 3
    max_scrolls: int = 2
    include_posts: bool = True
    include_reposts_or_reshares: bool = True
    include_quotes: bool = True
    include_replies: bool = False
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    explicit_live_mode: bool = True
    visible_session_required: bool = True
    allow_human_login_or_challenge: bool = True
    no_hidden_api: bool = True
    no_cookie_token_extraction: bool = True
    no_challenge_bypass: bool = True
    run_visible_live: bool = False
    automated_test_mode: bool = True
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveTwitterXSingleAccountSmokeResultR43N:
    marker: str
    schema_version: str
    smoke_run_id: str
    status: str
    blocker_reason: str
    run_dir: str
    request_path: str
    runbook_path: str
    progress_events_path: str
    observation_receipt_path: str
    observation_receipt_md_path: str
    materialization_receipts_index_path: str
    route_chain_path: str
    blockers_path: str
    summary_path: str
    report_json_path: str
    report_md_path: str
    observation_receipt: Mapping[str, Any]
    checks: tuple[Mapping[str, Any], ...]
    bad_checks: tuple[Mapping[str, Any], ...]

    @property
    def passed(self) -> bool:
        return self.status == R43N_PASS_STATUS and not self.bad_checks

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class LiveTwitterXSingleAccountSmokeHarnessR43N:
    """User-runnable Twitter/X live smoke harness.

    R43N is intentionally not a new control plane. It builds the existing
    R43L-to-R42GZ route with an explicit visible live media lane. Automated
    validation does not launch a browser; without an explicit visible run or an
    injected test runner the truthful status is BLOCKED_NEEDS_VISIBLE_SESSION.
    """

    def __init__(
        self,
        *,
        output_root: str | Path = R43N_DEFAULT_OUTPUT_ROOT,
        visible_session_binding: VisibleSessionBindingRunner | None = None,
    ) -> None:
        self.output_root = Path(output_root)
        self.visible_session_binding = visible_session_binding

    def run_smoke(
        self,
        request: LiveTwitterXSingleAccountSmokeRequestR43N | Mapping[str, Any] | None = None,
        *,
        live_runner: TwitterCaptureRunner | None = None,
        **overrides: Any,
    ) -> LiveTwitterXSingleAccountSmokeResultR43N:
        req = coerce_live_twitter_x_single_account_smoke_request_r43n(request, **overrides)
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        target_url = _plain_url(req.post_url or req.account_url)
        placeholder_reason = _placeholder_target_reason(req=req, target_url=target_url)
        handle = _safe_handle(req.account_handle or _handle_from_url(target_url) or "example")
        smoke_run_id = f"r43n_{capture_ts}_{_safe_part(handle)}"
        run_dir = Path(req.output_root or self.output_root) / smoke_run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        paths = _output_paths(run_dir)
        request_payload = {**req.to_dict(), "account_handle": handle, "normalized_url": target_url, "smoke_run_id": smoke_run_id, "marker": R43N_MARKER}
        _write_json(paths["request"], request_payload)
        _write_text(paths["runbook"], _build_runbook(request_payload))
        _write_json(paths["route_chain"], {"marker": R43N_MARKER, "route_chain": R43N_ROUTE_CHAIN, "normalized_url": target_url})
        _write_json(paths["materialization"], {"marker": R43N_MARKER, "materialization_receipts": [], "requires_real_visible_run": True})
        _write_ndjson(paths["progress"], ({"event": "smoke_requested", "at": capture_ts, "url": target_url},))

        started_at = _now_iso()
        status = R43N_BLOCKED_NEEDS_VISIBLE_SESSION
        blocker = ""
        app_shell_result: Mapping[str, Any] = {}
        route_receipts: tuple[Mapping[str, Any], ...] = ()
        boundary_invoked = False
        media_lane_present = True
        observation_store_path = ""
        observed_post_count = 0
        observed_media_count = 0
        observed_screenshot_count = 0
        materialization_receipt_count = 0
        non_fixture_evidence: list[Mapping[str, Any]] = []
        live_observation_paths: list[str] = []
        r43o_binding_payload: Mapping[str, Any] = {}
        r43o_receipt: Mapping[str, Any] = {}
        r43o_files_written: list[str] = []
        r43p_runner_output_promotion_invoked = False
        r43p_runner_output_promotion_status = ""
        r43p_runner_output_promotion_receipt_path = ""
        promoted_observed_post_count = 0
        promoted_observed_media_count = 0
        promoted_observed_screenshot_count = 0
        promoted_network_event_count = 0
        promoted_api_page_count = 0
        promoted_response_body_count = 0
        promoted_live_observation_paths: list[str] = []
        promoted_non_fixture_observation_evidence = False
        side_effect_flags = _side_effect_flags(req, browser_started=False, network_access=False, remote_downloads=False)

        if placeholder_reason:
            status = R43N_BLOCKED_PLACEHOLDER_TARGET_URL
            blocker = placeholder_reason
        elif not req.explicit_live_mode:
            status = R43N_NEEDS_PATCH_STATUS
            blocker = "explicit_live_mode must be true for R43N live smoke."
        elif req.visible_session_required and not req.run_visible_live and live_runner is None:
            status = R43N_BLOCKED_NEEDS_VISIBLE_SESSION
            blocker = "A visible local Twitter/X session is required. Re-run with --run-visible-live after opening/logging in through the app/browser profile."
        else:
            try:
                runner_calls: list[Mapping[str, Any]] = []
                if req.run_visible_live:
                    binding = self.visible_session_binding or build_live_twitter_x_visible_session_binding_r43o(
                        output_root=run_dir / "r43o_visible_session_binding"
                    )
                    r43o_result = binding.run_binding(
                        LiveTwitterXVisibleSessionBindingRequestR43O(
                            target_url=target_url,
                            account_handle=handle,
                            capture_timestamp=capture_ts,
                            output_root=str(run_dir / "r43o_visible_session_binding"),
                            max_items=req.max_items,
                            max_scrolls=req.max_scrolls,
                            run_visible_live=req.run_visible_live,
                            visible_session_required=req.visible_session_required,
                            automated_test_mode=req.automated_test_mode,
                            browser_user_data_dir=req.browser_user_data_dir,
                            browser_executable_path=req.browser_executable_path,
                        ),
                        runner=live_runner,
                    )
                    r43o_binding_payload = r43o_result.to_dict()
                    r43o_receipt = dict(r43o_result.receipt or {})
                    r43o_files_written = [_clean(path) for path in r43o_receipt.get("files_written") or () if _clean(path)]
                    _append_ndjson(paths["progress"], {"event": "r43o_visible_session_binding_finished", "at": _now_iso(), "status": r43o_result.status, "receipt_path": r43o_result.receipt_path})

                if live_runner is not None and not r43o_receipt:
                    chain = _build_live_app_shell_chain(run_dir, req=req, live_runner=live_runner)
                    runner_calls = list(chain["runner_calls"])
                    preview = chain["shell"].run_app_shell_command(
                        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
                            command_name="create_queue_preview",
                            session_id=smoke_run_id,
                            inputs=(target_url,),
                            capture_timestamp=capture_ts,
                            output_root=str(run_dir / "app_shell"),
                            fixture_mode=False,
                        )
                    )
                    run = chain["shell"].run_app_shell_command(
                        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
                            command_name="run_pending",
                            session_id=smoke_run_id,
                            queue_path=preview.queue_path,
                            capture_timestamp=f"{capture_ts}_run",
                            output_root=str(run_dir / "app_shell"),
                            fixture_mode=False,
                        )
                    )
                    app_shell_result = run.to_dict()
                    route_receipts = _read_ndjson(run.route_receipts_path)

                lane_payloads = tuple(_find_mappings(route_receipts, "marker", R42GZ_MARKER)) + _find_r42gz_result_payloads(run_dir)
                boundary_invoked = bool(lane_payloads) or bool(runner_calls)
                observed_post_count = _safe_int(_find_first_value(route_receipts, "record_count"))
                observed_media_count = max(_safe_int(_find_first_value(route_receipts, "media_count")), _media_count_from_payloads(lane_payloads))
                observed_screenshot_count = _safe_int(_find_first_value(route_receipts, "screenshot_count"))
                materialization_receipt_count = observed_screenshot_count
                observation_store_path = _clean(_find_first_value(route_receipts, "media_inventory_path") or _find_first_value(route_receipts, "media_index_path"))
                non_fixture_evidence = _non_fixture_evidence(lane_payloads, route_receipts)
                if r43o_receipt:
                    boundary_invoked = bool(boundary_invoked or r43o_receipt.get("r42gz_boundary_invoked"))
                    observed_post_count = max(observed_post_count, _safe_int(r43o_receipt.get("observed_post_count")))
                    observed_media_count = max(observed_media_count, _safe_int(r43o_receipt.get("observed_media_count")))
                    observed_screenshot_count = max(observed_screenshot_count, _safe_int(r43o_receipt.get("observed_screenshot_count")))
                    materialization_receipt_count = max(materialization_receipt_count, _safe_int(r43o_receipt.get("materialization_receipt_count")))
                    observation_store_path = observation_store_path or _clean(r43o_receipt.get("observation_store_path"))
                    r43p_runner_output_promotion_invoked = bool(r43o_receipt.get("r43p_runner_output_promotion_invoked"))
                    r43p_runner_output_promotion_status = _clean(r43o_receipt.get("r43p_runner_output_promotion_status"))
                    r43p_runner_output_promotion_receipt_path = _clean(r43o_receipt.get("r43p_runner_output_promotion_receipt_path"))
                    promoted_observed_post_count = _safe_int(r43o_receipt.get("promoted_observed_post_count"))
                    promoted_observed_media_count = _safe_int(r43o_receipt.get("promoted_observed_media_count"))
                    promoted_observed_screenshot_count = _safe_int(r43o_receipt.get("promoted_observed_screenshot_count"))
                    promoted_network_event_count = _safe_int(r43o_receipt.get("promoted_network_event_count"))
                    promoted_api_page_count = _safe_int(r43o_receipt.get("promoted_api_page_count"))
                    promoted_response_body_count = _safe_int(r43o_receipt.get("promoted_response_body_count"))
                    promoted_live_observation_paths = [
                        _clean(path)
                        for path in r43o_receipt.get("promoted_live_observation_paths") or ()
                        if _path_is_live_observation(_clean(path))
                    ]
                    promoted_non_fixture_observation_evidence = bool(r43o_receipt.get("promoted_non_fixture_observation_evidence"))
                    if r43o_receipt.get("status") == R43O_PASS_STATUS and r43o_files_written:
                        non_fixture_evidence.append(
                            {
                                "marker": R43O_LAUNCHER_BOUNDARY,
                                "status": _clean(r43o_receipt.get("status")),
                                "source_url": target_url,
                                "media_inventory_path": _clean(r43o_receipt.get("observation_store_path")),
                                "manifest_path": _first_existing_path(r43o_files_written),
                            }
                        )
                observed_total = observed_post_count + observed_media_count + observed_screenshot_count + materialization_receipt_count
                if observed_total <= 0:
                    # Diagnostic files from a browser/session attempt are useful R43O diagnostics,
                    # but they are not R43N live-observation evidence when the observed counts are zero.
                    non_fixture_evidence = []
                    live_observation_paths = []
                else:
                    live_observation_paths = _existing_live_observation_paths(non_fixture_evidence, observation_store_path)
                    live_observation_paths = sorted(set(live_observation_paths + [_clean(path) for path in r43o_files_written if _path_is_live_observation(_clean(path))]))
                    live_observation_paths = sorted(set(live_observation_paths + promoted_live_observation_paths))
                side_effect_flags = _side_effect_flags(
                    req,
                    browser_started=bool(req.run_visible_live and live_runner is None and not req.automated_test_mode),
                    network_access=bool(req.run_visible_live and live_runner is None and not req.automated_test_mode),
                    remote_downloads=False,
                )
                if r43o_receipt and r43o_receipt.get("status") == R43O_NEEDS_PATCH_STATUS:
                    status = R43N_NEEDS_PATCH_R43O_STATUS
                    blocker = _clean(r43o_receipt.get("blocker_reason")) or "R43O visible-session binding is not connected."
                elif r43o_receipt and r43o_receipt.get("status") == R43O_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE:
                    status = R43N_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE
                    blocker = _clean(r43o_receipt.get("blocker_reason")) or "Visible browser runtime/session is unavailable."
                elif r43o_receipt and r43o_receipt.get("status") == R43O_BLOCKED_NEEDS_VISIBLE_SESSION:
                    status = R43N_BLOCKED_NEEDS_VISIBLE_SESSION
                    blocker = _clean(r43o_receipt.get("blocker_reason")) or "A visible local Twitter/X session is required."
                elif not boundary_invoked:
                    status = R43N_NEEDS_PATCH_STATUS
                    blocker = "Explicit live route did not invoke the R42GZ boundary."
                elif _pass_gate_satisfied(
                    req=req,
                    target_url=target_url,
                    boundary_invoked=boundary_invoked,
                    non_fixture_evidence=non_fixture_evidence,
                    observed_post_count=observed_post_count,
                    observed_media_count=observed_media_count,
                    observed_screenshot_count=observed_screenshot_count,
                    materialization_receipt_count=materialization_receipt_count,
                    live_observation_paths=live_observation_paths,
                ):
                    status = R43N_PASS_STATUS
                    blocker = ""
                else:
                    status = R43N_BLOCKED_NO_LIVE_OBSERVATIONS
                    blocker = _clean(r43o_receipt.get("blocker_reason")) or "The explicit live route ran but produced no non-fixture observed post/media/screenshot material."
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                status = R43N_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE if "webview2" in message.lower() else R43N_BLOCKED_NO_LIVE_OBSERVATIONS
                blocker = message

        finished_at = _now_iso()
        receipt = {
            "account_handle": handle,
            "account_url": _plain_url(req.account_url),
            "post_url": _plain_url(req.post_url),
            "normalized_url": target_url,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "blocker_reason": blocker,
            "smoke_run_id": smoke_run_id,
            "explicit_live_mode": req.explicit_live_mode,
            "visible_session_required": req.visible_session_required,
            "route_chain": R43N_ROUTE_CHAIN,
            "r43d_live_mode_requested": req.explicit_live_mode,
            "r43b_media_lane_backend_present": media_lane_present,
            "r42gz_boundary_invoked": boundary_invoked,
            "r42gy_or_r42gv_observation_store_path": observation_store_path,
            "observed_post_count": observed_post_count,
            "observed_media_count": observed_media_count,
            "observed_screenshot_count": observed_screenshot_count,
            "materialization_receipt_count": materialization_receipt_count,
            "non_fixture_observation_evidence": non_fixture_evidence,
            "live_observation_paths": live_observation_paths,
            "r43p_runner_output_promotion_invoked": r43p_runner_output_promotion_invoked,
            "r43p_runner_output_promotion_status": r43p_runner_output_promotion_status,
            "r43p_runner_output_promotion_receipt_path": r43p_runner_output_promotion_receipt_path,
            "promoted_observed_post_count": promoted_observed_post_count,
            "promoted_observed_media_count": promoted_observed_media_count,
            "promoted_observed_screenshot_count": promoted_observed_screenshot_count,
            "promoted_network_event_count": promoted_network_event_count,
            "promoted_api_page_count": promoted_api_page_count,
            "promoted_response_body_count": promoted_response_body_count,
            "promoted_live_observation_paths": promoted_live_observation_paths,
            "promoted_non_fixture_observation_evidence": promoted_non_fixture_observation_evidence,
            "placeholder_target_detected": bool(placeholder_reason),
            "placeholder_target_reason": placeholder_reason,
            "r43o_visible_session_binding_invoked": bool(r43o_receipt),
            "r43o_visible_session_binding_status": _clean(r43o_receipt.get("status")),
            "visible_session_launched_or_attached": bool(r43o_receipt.get("visible_session_launched_or_attached")),
            "visible_navigation_attempted": bool(r43o_receipt.get("visible_navigation_attempted")),
            "observer_started": bool(r43o_receipt.get("observer_started")),
            "observation_store_path": _clean(r43o_receipt.get("observation_store_path") or observation_store_path),
            "visible_session_binding_receipt_path": _clean(r43o_binding_payload.get("receipt_path")),
            "visible_session_binding_blocker_reason": _clean(r43o_receipt.get("blocker_reason")),
            "visible_session_binding_files_written": r43o_files_written,
            "app_shell_result": app_shell_result,
            "route_receipts": route_receipts,
            "output_paths": {key: str(value) for key, value in paths.items()},
            "side_effect_flags": side_effect_flags,
        }
        _write_json(paths["receipt"], receipt)
        _write_text(paths["receipt_md"], _receipt_md(receipt))
        _write_json(paths["blockers"], {"marker": R43N_MARKER, "status": status, "blocker_reason": blocker})
        _write_text(paths["summary"], _summary_md(receipt))
        if status != R43N_PASS_STATUS:
            _append_ndjson(paths["progress"], {"event": "smoke_blocked", "at": finished_at, "status": status, "blocker_reason": blocker})
        else:
            _append_ndjson(paths["progress"], {"event": "smoke_passed", "at": finished_at, "status": status})

        checks = _build_checks(receipt, paths, req)
        bad = tuple(check for check in checks if check["status"] != "pass")
        result = LiveTwitterXSingleAccountSmokeResultR43N(
            marker=R43N_MARKER,
            schema_version=R43N_SCHEMA_VERSION,
            smoke_run_id=smoke_run_id,
            status=status,
            blocker_reason=blocker,
            run_dir=str(run_dir),
            request_path=str(paths["request"]),
            runbook_path=str(paths["runbook"]),
            progress_events_path=str(paths["progress"]),
            observation_receipt_path=str(paths["receipt"]),
            observation_receipt_md_path=str(paths["receipt_md"]),
            materialization_receipts_index_path=str(paths["materialization"]),
            route_chain_path=str(paths["route_chain"]),
            blockers_path=str(paths["blockers"]),
            summary_path=str(paths["summary"]),
            report_json_path=str(paths["report_json"]),
            report_md_path=str(paths["report_md"]),
            observation_receipt=receipt,
            checks=checks,
            bad_checks=bad,
        )
        write_report(result, run_dir)
        write_report(result, Path(req.output_root or self.output_root))
        _write_cmd_runner(run_dir)
        return result


def build_live_twitter_x_single_account_smoke_harness_r43n(
    *,
    output_root: str | Path = R43N_DEFAULT_OUTPUT_ROOT,
    visible_session_binding: VisibleSessionBindingRunner | None = None,
) -> LiveTwitterXSingleAccountSmokeHarnessR43N:
    return LiveTwitterXSingleAccountSmokeHarnessR43N(output_root=output_root, visible_session_binding=visible_session_binding)


def build_report(output_root: str | Path = R43N_DEFAULT_OUTPUT_ROOT) -> LiveTwitterXSingleAccountSmokeResultR43N:
    harness = build_live_twitter_x_single_account_smoke_harness_r43n(output_root=output_root)
    return harness.run_smoke(
        LiveTwitterXSingleAccountSmokeRequestR43N(
            account_url="https://x.com/example",
            output_root=str(output_root),
            capture_timestamp="20260916T020000Z",
            run_visible_live=False,
            automated_test_mode=True,
        )
    )


def write_report(result: LiveTwitterXSingleAccountSmokeResultR43N, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT_REPORT.json"
    md_path = root / "R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT_REPORT.md"
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
    lines = [f"# {R43N_MARKER}", "", f"- Status: `{result.status}`", f"- Bad checks: `{len(result.bad_checks)}`", "", "## Checks"]
    lines.extend(f"- {check['status'].upper()}: {check['name']}" for check in result.checks)
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def coerce_live_twitter_x_single_account_smoke_request_r43n(
    request: LiveTwitterXSingleAccountSmokeRequestR43N | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> LiveTwitterXSingleAccountSmokeRequestR43N:
    data = request.to_dict() if isinstance(request, LiveTwitterXSingleAccountSmokeRequestR43N) else dict(request or {})
    data.update({key: value for key, value in overrides.items() if value is not None})
    return LiveTwitterXSingleAccountSmokeRequestR43N(
        account_url=_clean(data.get("account_url") or "https://x.com/example"),
        post_url=_clean(data.get("post_url")),
        account_handle=_safe_handle(data.get("account_handle")),
        capture_timestamp=_clean(data.get("capture_timestamp")),
        output_root=_clean(data.get("output_root") or R43N_DEFAULT_OUTPUT_ROOT),
        max_items=max(1, _safe_int(data.get("max_items"), 3)),
        max_scrolls=max(1, _safe_int(data.get("max_scrolls"), 2)),
        include_posts=bool(data.get("include_posts", True)),
        include_reposts_or_reshares=bool(data.get("include_reposts_or_reshares", True)),
        include_quotes=bool(data.get("include_quotes", True)),
        include_replies=bool(data.get("include_replies", False)),
        include_media=bool(data.get("include_media", True)),
        include_static_screenshots=bool(data.get("include_static_screenshots", True)),
        require_screenshot_receipts=bool(data.get("require_screenshot_receipts", True)),
        explicit_live_mode=bool(data.get("explicit_live_mode", True)),
        visible_session_required=bool(data.get("visible_session_required", True)),
        allow_human_login_or_challenge=bool(data.get("allow_human_login_or_challenge", True)),
        no_hidden_api=bool(data.get("no_hidden_api", True)),
        no_cookie_token_extraction=bool(data.get("no_cookie_token_extraction", True)),
        no_challenge_bypass=bool(data.get("no_challenge_bypass", True)),
        run_visible_live=bool(data.get("run_visible_live", False)),
        automated_test_mode=bool(data.get("automated_test_mode", True)),
        browser_user_data_dir=_clean(data.get("browser_user_data_dir")),
        browser_executable_path=_clean(data.get("browser_executable_path")),
    )


def _build_live_app_shell_chain(run_dir: Path, *, req: LiveTwitterXSingleAccountSmokeRequestR43N, live_runner: TwitterCaptureRunner | None) -> Mapping[str, Any]:
    runner_calls: list[Mapping[str, Any]] = []

    def recording_runner(**kwargs: Any) -> Any:
        runner_calls.append({key: _to_jsonable(value) for key, value in kwargs.items() if key != "media_backend_runner"})
        if live_runner is None:
            raise RuntimeError("Visible WebView2 live runner was not provided.")
        return live_runner(**kwargs)

    lane = build_independent_fast_media_webview2_lane_r42gz(
        runner=recording_runner,
        live=True,
        headless=False,
        fixture_mode=False,
    )
    r43b_runner = build_twitter_x_account_timeline_runner_r43b(
        media_lane_backend=lane,
        ledger_exporter=build_twitter_x_account_media_ledger_exporter_r43a(run_dir / "source_exports" / "twitter_x"),
        config=TwitterXAccountTimelineRunnerConfigR43B(
            output_root=str(run_dir / "r43b_timeline_runner"),
            ledger_output_root=str(run_dir / "source_exports" / "twitter_x"),
            max_scroll_rounds=req.max_scrolls,
            include_posts=req.include_posts,
            include_reposts=req.include_reposts_or_reshares,
            include_quote_posts=req.include_quotes,
            include_replies=req.include_replies,
            include_static_screenshots=req.include_static_screenshots,
            media_folder_links_required=req.include_media,
            fixture_mode=False,
        ),
    )
    r43d_surface = build_twitter_x_account_tracking_export_surface_r43d(timeline_runner=r43b_runner, output_root=run_dir / "r43d_surface")
    registry = build_universal_social_account_tracking_registry_r43e(twitter_x_surface=r43d_surface, output_root=run_dir / "r43e_registry")
    export_router = build_universal_social_export_surface_router_r43f(registry=registry, output_root=run_dir / "r43f_router")
    intake = build_universal_social_batch_account_intake_router_r43g(export_router=export_router, output_root=run_dir / "r43g_intake")
    queue = build_universal_social_batch_queue_router_r43h(intake_router=intake, output_root=run_dir / "r43h_queue")
    workbench = build_universal_social_batch_queue_workbench_r43i(queue_router=queue, output_root=run_dir / "r43i_workbench")
    panel = build_universal_social_batch_queue_workbench_panel_r43j(workbench=workbench, output_root=run_dir / "r43j_panel")
    gui_bridge = build_universal_social_batch_workbench_gui_state_bridge_r43k(panel=panel, output_root=run_dir / "r43k_gui_state")
    shell = build_universal_social_batch_workbench_app_shell_commands_r43l(panel=panel, gui_state_bridge=gui_bridge, output_root=run_dir / "r43l_app_shell")
    return {"shell": shell, "runner_calls": runner_calls}


def _build_checks(receipt: Mapping[str, Any], paths: Mapping[str, Path], req: LiveTwitterXSingleAccountSmokeRequestR43N) -> tuple[Mapping[str, Any], ...]:
    status = _clean(receipt.get("status"))
    pass_status = status == R43N_PASS_STATUS
    blocked_status = status in {R43N_BLOCKED_PLACEHOLDER_TARGET_URL, R43N_BLOCKED_NEEDS_VISIBLE_SESSION, R43N_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE, R43N_BLOCKED_NO_LIVE_OBSERVATIONS}
    side_effects = dict(receipt.get("side_effect_flags") or {})
    evidence = receipt.get("non_fixture_observation_evidence") or []
    live_paths = tuple(_clean(path) for path in receipt.get("live_observation_paths") or () if _clean(path))
    observed_total = (
        _safe_int(receipt.get("observed_post_count"))
        + _safe_int(receipt.get("observed_media_count"))
        + _safe_int(receipt.get("observed_screenshot_count"))
        + _safe_int(receipt.get("materialization_receipt_count"))
    )
    checks = (
        _check("live_twitter_x_single_account_smoke_harness_invoked", True),
        _check("explicit_live_mode_required_for_live_smoke", receipt.get("explicit_live_mode") is True),
        _check("visible_session_required_for_real_smoke", receipt.get("visible_session_required") is True),
        _check("app_shell_route_reaches_r43d_live_mode", receipt.get("r43d_live_mode_requested") is True and "R43D" in _clean(receipt.get("route_chain"))),
        _check("r43d_live_mode_constructs_r42gz_media_lane", receipt.get("r43b_media_lane_backend_present") is True),
        _check("r43b_media_lane_backend_present_in_live_mode", receipt.get("r43b_media_lane_backend_present") is True),
        _check("r42gz_boundary_available_for_real_observation", True),
        _check("r42gy_or_r42gv_observation_store_available", True),
        _check("live_smoke_receipt_written", paths["receipt"].is_file()),
        _check("live_smoke_runbook_written", paths["runbook"].is_file()),
        _check("live_smoke_progress_events_written", paths["progress"].is_file() and paths["progress"].stat().st_size > 0),
        _check("live_smoke_route_chain_written", paths["route_chain"].is_file()),
        _check("placeholder_urls_blocked", not receipt.get("placeholder_target_detected") or status == R43N_BLOCKED_PLACEHOLDER_TARGET_URL),
        _check("run_visible_live_flag_alone_does_not_create_pass", not (receipt.get("placeholder_target_detected") and pass_status)),
        _check("pass_requires_non_fixture_observation_evidence", not pass_status or _evidence_is_non_fixture(evidence)),
        _check("pass_requires_observed_counts_or_materialization_receipts", not pass_status or observed_total > 0),
        _check("pass_requires_existing_live_observation_paths", not pass_status or bool(live_paths)),
        _check("blocked_placeholder_target_url_receipt_written", status != R43N_BLOCKED_PLACEHOLDER_TARGET_URL or (paths["receipt"].is_file() and receipt.get("placeholder_target_detected") is True)),
        _check("no_fixture_sample_probe_outputs_count_as_live_evidence", _evidence_is_non_fixture(evidence) if pass_status else True),
        _check("blocked_status_does_not_fake_success", not blocked_status or not evidence),
        _check("fixture_sample_probe_outputs_do_not_count_as_live_pass", not pass_status or _evidence_is_non_fixture(evidence)),
        _check("non_fixture_live_observation_required_for_pass", not pass_status or bool(evidence)),
        _check("materialization_receipts_required_when_screenshots_enabled", not (pass_status and req.require_screenshot_receipts) or _safe_int(receipt.get("materialization_receipt_count")) > 0),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", side_effects.get("hidden_api_scraping_performed") is False and side_effects.get("cookie_or_token_extraction_performed") is False and side_effects.get("challenge_bypass_performed") is False),
        _check("no_login_automation", side_effects.get("login_automation_performed") is False),
        _check("no_browser_started_during_automated_tests", not req.automated_test_mode or side_effects.get("browser_started_during_automated_tests") is False),
        _check("no_network_access_during_automated_tests", not req.automated_test_mode or side_effects.get("network_access_during_automated_tests") is False),
        _check("no_source_role_or_review_window_side_effects", side_effects.get("source_role_or_review_window_side_effects") is False),
        _check("no_remote_media_downloads_during_automated_tests", side_effects.get("remote_media_downloads_performed") is False),
        _check("youtube_capture_engine_unchanged", side_effects.get("youtube_capture_engine_changed") is False),
        _check("plain_machine_urls", _machine_urls_are_plain(receipt)),
    )
    return checks


def _output_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "request": run_dir / "live_smoke_request.json",
        "runbook": run_dir / "live_smoke_runbook.md",
        "progress": run_dir / "live_smoke_progress_events.ndjson",
        "receipt": run_dir / "live_smoke_observation_receipt.json",
        "receipt_md": run_dir / "live_smoke_observation_receipt.md",
        "materialization": run_dir / "live_smoke_materialization_receipts_index.json",
        "route_chain": run_dir / "live_smoke_route_chain.json",
        "blockers": run_dir / "live_smoke_blockers.json",
        "summary": run_dir / "live_smoke_summary.md",
        "report_json": run_dir / "R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT_REPORT.json",
        "report_md": run_dir / "R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT_REPORT.md",
    }


def _build_runbook(payload: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            f"# {R43N_MARKER}",
            "",
            "This smoke harness is user-runnable and must use explicit visible live mode for a real PASS.",
            "",
            f"- Target URL: `{payload.get('normalized_url', '')}`",
            "- Default automated validation does not start a browser and should return a truthful blocked receipt.",
            "- Human login or challenge handling is allowed only by visible human action.",
            "- No hidden API scraping, cookie/token extraction, login automation, challenge bypass, or remote media downloads are allowed.",
            "",
        )
    )


def _receipt_md(receipt: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            f"# {R43N_MARKER}",
            "",
            f"- Status: `{receipt.get('status', '')}`",
            f"- Blocker: `{receipt.get('blocker_reason', '')}`",
            f"- URL: `{receipt.get('normalized_url', '')}`",
            f"- Route: `{receipt.get('route_chain', '')}`",
            f"- Boundary invoked: `{receipt.get('r42gz_boundary_invoked')}`",
            "",
        )
    )


def _summary_md(receipt: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            f"# {R43N_MARKER} Summary",
            "",
            f"- Status: `{receipt.get('status', '')}`",
            f"- Observed posts: `{receipt.get('observed_post_count', 0)}`",
            f"- Observed media: `{receipt.get('observed_media_count', 0)}`",
            f"- Observed screenshots: `{receipt.get('observed_screenshot_count', 0)}`",
            f"- Materialization receipts: `{receipt.get('materialization_receipt_count', 0)}`",
            "",
        )
    )


def _write_cmd_runner(run_dir: Path) -> None:
    cmd = run_dir / "RUN_R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE.cmd"
    cmd.write_text(
        "@echo off\r\n"
        "REM Replace https://x.com/example with the public Twitter/X account or post to smoke test.\r\n"
        "REM This command starts an explicit visible live smoke and may require human login/challenge action.\r\n"
        "\"C:\\Users\\fahad\\AppData\\Local\\Programs\\Python\\Python311\\python.exe\" profile_media_live_twitter_x_single_account_smoke_harness_r43n.py --account-url https://x.com/example --run-visible-live\r\n",
        encoding="utf-8",
    )


def _side_effect_flags(req: LiveTwitterXSingleAccountSmokeRequestR43N, *, browser_started: bool, network_access: bool, remote_downloads: bool) -> Mapping[str, bool]:
    return {
        "browser_started_during_automated_tests": bool(req.automated_test_mode and browser_started),
        "network_access_during_automated_tests": bool(req.automated_test_mode and network_access),
        "remote_media_downloads_performed": bool(remote_downloads),
        "hidden_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "challenge_bypass_performed": False,
        "login_automation_performed": False,
        "source_role_or_review_window_side_effects": False,
        "youtube_capture_engine_changed": False,
    }


def _find_mappings(value: Any, key: str, expected: str) -> tuple[Mapping[str, Any], ...]:
    found: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        if value.get(key) == expected:
            found.append(dict(value))
        for item in value.values():
            found.extend(_find_mappings(item, key, expected))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_find_mappings(item, key, expected))
    return tuple(found)


def _find_r42gz_result_payloads(run_dir: Path) -> tuple[Mapping[str, Any], ...]:
    payloads: list[Mapping[str, Any]] = []
    for path in run_dir.rglob("r42gz_independent_fast_media_webview2_lane_result.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, Mapping) and payload.get("marker") == R42GZ_MARKER:
            payloads.append(dict(payload))
    return tuple(payloads)


def _find_first_value(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        if key in value and value.get(key) not in (None, ""):
            return value.get(key)
        for item in value.values():
            found = _find_first_value(item, key)
            if found not in (None, ""):
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _find_first_value(item, key)
            if found not in (None, ""):
                return found
    return ""


def _media_count_from_payloads(payloads: tuple[Mapping[str, Any], ...]) -> int:
    count = 0
    for payload in payloads:
        media = payload.get("media_inventory")
        if isinstance(media, list):
            count += len(media)
    return count


def _first_existing_path(paths: list[str]) -> str:
    for path in paths:
        if _path_is_live_observation(path):
            return path
    return ""


def _placeholder_target_reason(*, req: LiveTwitterXSingleAccountSmokeRequestR43N, target_url: str) -> str:
    values = (_clean(req.account_url), _clean(req.post_url), _clean(target_url), _clean(req.account_handle))
    combined = " ".join(values).replace("\\_", "_").lower()
    placeholder_tokens = (
        "put_handle_here",
        "put_status_id_here",
        "real_handle",
        "real_status_id",
        "handle_here",
        "status_id_here",
        "replace_me",
        "your_handle",
        "your_status_id",
        "placeholder",
    )
    if any(token in combined for token in placeholder_tokens):
        return "Target URL contains placeholder text; replace it with a real public Twitter/X account or post URL."
    parsed = urlsplit(_plain_url(target_url))
    host = parsed.netloc.lower()
    parts = tuple(part.lower() for part in parsed.path.strip("/").split("/") if part)
    if host in {"x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}:
        if parts and parts[0] in {"example", "test", "sample", "placeholder"}:
            return "Target URL uses an example/test-only Twitter/X account placeholder."
        if len(parts) >= 3 and parts[1] == "status" and parts[2] in {"example", "test", "sample", "placeholder", "real_status_id"}:
            return "Target URL uses an example/test-only Twitter/X status placeholder."
    return ""


def _pass_gate_satisfied(
    *,
    req: LiveTwitterXSingleAccountSmokeRequestR43N,
    target_url: str,
    boundary_invoked: bool,
    non_fixture_evidence: list[Mapping[str, Any]],
    observed_post_count: int,
    observed_media_count: int,
    observed_screenshot_count: int,
    materialization_receipt_count: int,
    live_observation_paths: list[str],
) -> bool:
    if _placeholder_target_reason(req=req, target_url=target_url):
        return False
    if not (req.explicit_live_mode and req.visible_session_required and boundary_invoked):
        return False
    if not _evidence_is_non_fixture(non_fixture_evidence):
        return False
    if not (observed_post_count or observed_media_count or observed_screenshot_count or materialization_receipt_count):
        return False
    return bool(live_observation_paths)


def _existing_live_observation_paths(evidence: Any, *extra_paths: Any) -> list[str]:
    candidates: list[str] = []
    for item in evidence if isinstance(evidence, list) else []:
        if isinstance(item, Mapping):
            for key in ("media_inventory_path", "rendered_dom_path", "network_events_path", "manifest_path"):
                value = _clean(item.get(key))
                if value:
                    candidates.append(value)
    candidates.extend(_clean(path) for path in extra_paths if _clean(path))
    existing: list[str] = []
    for candidate in candidates:
        if _path_is_live_observation(candidate):
            existing.append(candidate)
    return sorted(set(existing))


def _path_is_live_observation(path_value: str) -> bool:
    lowered = path_value.replace("\\", "/").lower()
    if any(token in lowered for token in ("/fixture", "_fixture", "/sample", "_sample", "/probe", "_probe", "/synthetic", "_synthetic")):
        return False
    return Path(path_value).is_file()


def _non_fixture_evidence(lane_payloads: tuple[Mapping[str, Any], ...], route_receipts: tuple[Mapping[str, Any], ...]) -> list[Mapping[str, Any]]:
    evidence: list[Mapping[str, Any]] = []
    for payload in lane_payloads:
        status = _clean(payload.get("status") or payload.get("backend_status"))
        paths = {
            "media_inventory_path": _clean(payload.get("media_inventory_path")),
            "rendered_dom_path": _clean(payload.get("rendered_dom_path")),
            "network_events_path": _clean(payload.get("network_events_path")),
            "manifest_path": _clean(payload.get("manifest_path")),
        }
        if status and not _text_mentions_fixture(status) and any(_path_is_live_observation(path) for path in paths.values() if path):
            evidence.append(
                {
                    "marker": payload.get("marker", ""),
                    "status": status,
                    "source_url": _plain_url(payload.get("source_url")),
                    **paths,
                }
            )
    return evidence


def _evidence_is_non_fixture(evidence: Any) -> bool:
    blob = json.dumps(_to_jsonable(evidence), sort_keys=True).lower()
    return bool(evidence) and "fixture" not in blob and "sample" not in blob and "probe" not in blob and "synthetic" not in blob


def _text_mentions_fixture(text: str) -> bool:
    lowered = _clean(text).lower()
    return any(token in lowered for token in ("fixture", "sample", "probe", "synthetic"))


def _read_ndjson(path_value: Any) -> tuple[Mapping[str, Any], ...]:
    path = Path(_clean(path_value))
    if not path.is_file():
        return ()
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, Mapping):
                rows.append(dict(item))
    return tuple(rows)


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
    parser = argparse.ArgumentParser(description=R43N_MARKER)
    parser.add_argument("--account-url", default="https://x.com/example")
    parser.add_argument("--post-url", default="")
    parser.add_argument("--account-handle", default="")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--output-root", default=R43N_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--max-items", type=int, default=3)
    parser.add_argument("--max-scrolls", type=int, default=2)
    parser.add_argument("--run-visible-live", action="store_true")
    parser.add_argument("--browser-user-data-dir", default="")
    parser.add_argument("--browser-executable-path", default="")
    args = parser.parse_args(argv)
    harness = build_live_twitter_x_single_account_smoke_harness_r43n(output_root=args.output_root)
    result = harness.run_smoke(
        account_url=args.account_url,
        post_url=args.post_url,
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
    print(R43N_MARKER)
    print(result.status)
    print(result.report_json_path)
    print(result.report_md_path)
    return 0 if not result.bad_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "R43N_BLOCKED_NEEDS_VISIBLE_SESSION",
    "R43N_BLOCKED_NO_LIVE_OBSERVATIONS",
    "R43N_BLOCKED_PLACEHOLDER_TARGET_URL",
    "R43N_BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE",
    "R43N_DEFAULT_OUTPUT_ROOT",
    "R43N_MARKER",
    "R43N_NEEDS_PATCH_STATUS",
    "R43N_PASS_STATUS",
    "LiveTwitterXSingleAccountSmokeHarnessR43N",
    "LiveTwitterXSingleAccountSmokeRequestR43N",
    "LiveTwitterXSingleAccountSmokeResultR43N",
    "build_live_twitter_x_single_account_smoke_harness_r43n",
    "build_report",
    "coerce_live_twitter_x_single_account_smoke_request_r43n",
    "write_report",
]
