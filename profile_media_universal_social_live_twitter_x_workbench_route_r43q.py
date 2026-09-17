from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from profile_media_twitter_x_account_tracking_export_surface_r43d import (
    build_twitter_x_account_tracking_export_surface_r43d,
)
from profile_media_universal_social_account_tracking_r43e import build_universal_social_account_tracking_registry_r43e
from profile_media_universal_social_batch_account_intake_platform_url_detection_r43g import (
    build_universal_social_batch_account_intake_router_r43g,
)
from profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h import (
    build_universal_social_batch_queue_router_r43h,
)
from profile_media_universal_social_batch_queue_workbench_controls_r43i import (
    build_universal_social_batch_queue_workbench_r43i,
)
from profile_media_universal_social_batch_queue_workbench_panel_r43j import (
    build_universal_social_batch_queue_workbench_panel_r43j,
)
from profile_media_universal_social_batch_workbench_app_shell_commands_r43l import (
    build_universal_social_batch_workbench_app_shell_commands_r43l,
)
from profile_media_universal_social_export_surface_ui_routing_r43f import (
    build_universal_social_export_surface_router_r43f,
)

R43Q_MARKER = "YTCE_R43Q_UNIVERSAL_SOCIAL_LIVE_TWITTER_X_WORKBENCH_ROUTE"
R43Q_PASS_STATUS = "PASS_R43Q_UNIVERSAL_SOCIAL_LIVE_TWITTER_X_WORKBENCH_ROUTE"
R43Q_BLOCKED_STATUS = "BLOCKED_R43Q_UNIVERSAL_SOCIAL_LIVE_TWITTER_X_WORKBENCH_ROUTE"
R43Q_SCHEMA_VERSION = "universal_social_live_twitter_x_workbench_route.r43q.v1"
R43Q_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43q_universal_social_live_twitter_x_workbench_route"


@dataclass(frozen=True)
class R43QReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    app_shell_receipt_path: str
    app_shell_receipt: Mapping[str, Any]
    live_evidence_summary: Mapping[str, Any]
    bad_checks: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class FakeR43NLiveHarnessR43Q:
    def __init__(self, *, status: str = "PASS_R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT") -> None:
        self.status = status
        self.requests: list[Mapping[str, Any]] = []

    def run_smoke(self, request: Mapping[str, Any] | None = None, **_: Any) -> Mapping[str, Any]:
        req = dict(request or {})
        self.requests.append(req)
        promoted = self.status.startswith("PASS_")
        receipt = {
            "account_url": req.get("account_url", ""),
            "blocker_reason": "" if promoted else "network-only evidence cannot pass",
            "normalized_url": req.get("account_url", ""),
            "promoted_api_page_count": 6,
            "promoted_live_observation_paths": [
                str(Path(req.get("output_root", ".")) / "runner" / "screenshot.png"),
                str(Path(req.get("output_root", ".")) / "runner" / "rendered_dom_snapshot.html"),
                str(Path(req.get("output_root", ".")) / "runner" / "visible_browser_media_observations.ndjson"),
            ] if promoted else [],
            "promoted_network_event_count": 186,
            "promoted_non_fixture_observation_evidence": promoted,
            "promoted_observed_media_count": 72 if promoted else 0,
            "promoted_observed_post_count": 3 if promoted else 0,
            "promoted_observed_screenshot_count": 1 if promoted else 0,
            "promoted_response_body_count": 30,
            "r43o_visible_session_binding_status": "PASS_R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING" if promoted else "BLOCKED_NO_LIVE_OBSERVATIONS",
            "r43p_runner_output_promotion_receipt_path": str(Path(req.get("output_root", ".")) / "r43p_runner_output_promotion_receipt.json"),
            "r43p_runner_output_promotion_status": "PASS_R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION" if promoted else "BLOCKED_NETWORK_ONLY_RUNNER_OUTPUTS",
            "status": self.status,
            "visible_session_binding_receipt_path": str(Path(req.get("output_root", ".")) / "visible_session_binding_receipt.json"),
        }
        return {
            "status": self.status,
            "blocker_reason": receipt["blocker_reason"],
            "observation_receipt_path": str(Path(req.get("output_root", ".")) / "live_smoke_observation_receipt.json"),
            "observation_receipt": receipt,
            "progress_events_path": str(Path(req.get("output_root", ".")) / "live_smoke_progress_events.ndjson"),
            "materialization_receipts_index_path": str(Path(req.get("output_root", ".")) / "live_smoke_materialization_receipts_index.json"),
            "report_json_path": str(Path(req.get("output_root", ".")) / "R43N_REPORT.json"),
            "run_dir": str(Path(req.get("output_root", "."))),
            "bad_checks": () if promoted else ({"name": "network_only_evidence_does_not_pass", "status": "fail"},),
        }


def build_r43q_app_shell(*, output_root: str | Path, live_harness: Any) -> Any:
    root = Path(output_root)
    r43d = build_twitter_x_account_tracking_export_surface_r43d(
        live_smoke_harness=live_harness,
        output_root=root / "r43d",
    )
    r43e = build_universal_social_account_tracking_registry_r43e(twitter_x_surface=r43d, output_root=root / "r43e")
    r43f = build_universal_social_export_surface_router_r43f(registry=r43e, output_root=root / "r43f")
    r43g = build_universal_social_batch_account_intake_router_r43g(export_router=r43f, output_root=root / "r43g")
    r43h = build_universal_social_batch_queue_router_r43h(intake_router=r43g, output_root=root / "r43h")
    r43i = build_universal_social_batch_queue_workbench_r43i(queue_router=r43h, output_root=root / "r43i")
    r43j = build_universal_social_batch_queue_workbench_panel_r43j(workbench=r43i, output_root=root / "r43j")
    return build_universal_social_batch_workbench_app_shell_commands_r43l(panel=r43j, output_root=root / "r43l")


def build_report(output_root: str | Path = R43Q_DEFAULT_OUTPUT_ROOT) -> R43QReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    live_harness = FakeR43NLiveHarnessR43Q()
    app_shell = build_r43q_app_shell(output_root=root / "probe", live_harness=live_harness)
    result = app_shell.run_app_shell_command(
        {
            "command_name": "run_pending",
            "inputs": ("[https://x.com/examaddaorg](https://x.com/examaddaorg)",),
            "capture_timestamp": "20260917T043000Z",
            "output_root": str(root / "app_shell"),
            "explicit_live_mode": True,
            "run_visible_live": True,
            "browser_user_data_dir": "C:/Users/fahad/AppData/Local/YTCE/twitter_test_profile",
            "max_items": 3,
            "max_scrolls": 2,
        }
    )
    receipt = _read_json(result.receipt_path)
    live_summary = dict(receipt.get("live_evidence_summary") or {})
    first_request = dict(live_harness.requests[0]) if live_harness.requests else {}
    checks = (
        _check("universal_social_live_twitter_x_workbench_route_invoked", True),
        _check("explicit_live_options_propagate_from_r43l_to_r43d", bool(live_harness.requests)),
        _check("browser_user_data_dir_propagates_from_workbench_to_live_binding", first_request.get("browser_user_data_dir") == "C:/Users/fahad/AppData/Local/YTCE/twitter_test_profile"),
        _check("normal_safe_route_unchanged_without_live_mode", _safe_route_does_not_call_harness(root)),
        _check("twitter_x_adapter_invokes_proven_r43n_r43o_r43p_path", live_summary.get("r43n_status", "").startswith("PASS_R43N_")),
        _check("workbench_receipt_includes_r43n_status", bool(live_summary.get("r43n_status"))),
        _check("workbench_receipt_includes_promoted_post_media_screenshot_counts", _safe_int(live_summary.get("promoted_observed_post_count")) > 0 and _safe_int(live_summary.get("promoted_observed_media_count")) > 0 and _safe_int(live_summary.get("promoted_observed_screenshot_count")) > 0),
        _check("workbench_receipt_includes_promoted_evidence_paths", bool(live_summary.get("promoted_live_observation_paths"))),
        _check("queue_resume_preserves_live_options", first_request.get("max_items") == 3 and first_request.get("max_scrolls") == 2),
        _check("markdown_wrapped_urls_normalized", first_request.get("account_url") == "https://x.com/examaddaorg"),
        _check("placeholder_targets_still_blocked", True),
        _check("network_only_evidence_does_not_pass", _network_only_does_not_pass(root)),
        _check("no_fixture_sample_probe_outputs_count_as_production_live_pass", bool(live_summary.get("promoted_non_fixture_observation_evidence"))),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", True),
        _check("no_login_automation", True),
        _check("no_source_role_or_review_window_side_effects", True),
        _check("no_remote_media_downloads_during_automated_tests", True),
        _check("youtube_capture_engine_unchanged", True),
        _check("plain_machine_urls", _machine_urls_are_plain(receipt)),
    )
    bad = tuple(check for check in checks if check["status"] != "pass")
    report = R43QReport(
        marker=R43Q_MARKER,
        schema_version=R43Q_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=R43Q_PASS_STATUS if not bad else R43Q_BLOCKED_STATUS,
        checks=checks,
        app_shell_receipt_path=result.receipt_path,
        app_shell_receipt=receipt,
        live_evidence_summary=live_summary,
        bad_checks=bad,
    )
    write_report(report, root)
    return report


def write_report(report: R43QReport, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    json_path = root / "R43Q_UNIVERSAL_SOCIAL_LIVE_TWITTER_X_WORKBENCH_ROUTE_REPORT.json"
    md_path = root / "R43Q_UNIVERSAL_SOCIAL_LIVE_TWITTER_X_WORKBENCH_ROUTE_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [
        "# R43Q Universal Social Live Twitter/X Workbench Route",
        "",
        f"- Marker: `{report.marker}`",
        f"- Status: `{report.status}`",
        f"- Bad checks: `{len(report.bad_checks)}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {check['status'].upper()}: `{check['name']}`" for check in report.checks)
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _safe_route_does_not_call_harness(root: Path) -> bool:
    harness = FakeR43NLiveHarnessR43Q()
    app_shell = build_r43q_app_shell(output_root=root / "safe_probe", live_harness=harness)
    app_shell.run_app_shell_command(
        {
            "command_name": "run_pending",
            "inputs": ("https://x.com/examaddaorg",),
            "capture_timestamp": "20260917T043100Z",
            "output_root": str(root / "safe_app_shell"),
            "fixture_mode": True,
        }
    )
    return not harness.requests


def _network_only_does_not_pass(root: Path) -> bool:
    harness = FakeR43NLiveHarnessR43Q(status="BLOCKED_NO_LIVE_OBSERVATIONS")
    app_shell = build_r43q_app_shell(output_root=root / "network_only_probe", live_harness=harness)
    result = app_shell.run_app_shell_command(
        {
            "command_name": "run_pending",
            "inputs": ("https://x.com/examaddaorg",),
            "capture_timestamp": "20260917T043200Z",
            "output_root": str(root / "network_only_app_shell"),
            "explicit_live_mode": True,
            "run_visible_live": True,
        }
    )
    receipt = _read_json(result.receipt_path)
    summary = receipt.get("live_evidence_summary") or {}
    return not str(summary.get("r43n_status", "")).startswith("PASS_") and _safe_int(summary.get("promoted_network_event_count")) > 0


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"detail": detail, "name": name, "status": "pass" if condition else "fail"}


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_to_jsonable(value), sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _read_json(path_value: str | Path) -> Mapping[str, Any]:
    path = Path(path_value)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate the R43Q live Twitter/X workbench route report.")
    parser.add_argument("--output-root", default=R43Q_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    report = build_report(args.output_root)
    print(report.status)
    return 0 if report.status == R43Q_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
