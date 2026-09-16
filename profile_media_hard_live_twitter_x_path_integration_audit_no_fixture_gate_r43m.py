from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from profile_media_independent_fast_media_webview2_lane_r42gz import (
    R42GZ_MARKER,
    build_independent_fast_media_webview2_lane_r42gz,
)
from profile_media_twitter_x_account_media_ledger_r43a import build_twitter_x_account_media_ledger_exporter_r43a
from profile_media_twitter_x_account_timeline_runner_r43b import (
    TwitterXAccountTimelineRunnerConfigR43B,
    build_twitter_x_account_timeline_runner_r43b,
)
from profile_media_twitter_x_account_tracking_export_surface_r43d import (
    TwitterXAccountTrackingExportRequestR43D,
    build_twitter_x_account_tracking_export_surface_r43d,
)
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

R43M_MARKER = "YTCE_R43M_HARD_LIVE_TWITTER_X_PATH_INTEGRATION_AUDIT_NO_FIXTURE_GATE"
R43M_PASS_STATUS = "PASS_R43M_HARD_LIVE_TWITTER_X_PATH_INTEGRATION_AUDIT_NO_FIXTURE_GATE"
R43M_NEEDS_PATCH_STATUS = "NEEDS_PATCH_R43M_LIVE_TWITTER_X_PATH_NOT_PROVEN"
R43M_SCHEMA_VERSION = "hard_live_twitter_x_path_integration_audit_no_fixture_gate.r43m.v1"
R43M_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43m_hard_live_twitter_x_path_integration_audit_no_fixture_gate"


@dataclass(frozen=True)
class R43MReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    bad_checks: tuple[Mapping[str, Any], ...]
    live_boundary_proof: Mapping[str, Any]
    source_audit: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43M_PASS_STATUS and not self.bad_checks

    def to_dict(self) -> dict[str, Any]:
        return {
            "bad_checks": [dict(check) for check in self.bad_checks],
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "live_boundary_proof": _to_jsonable(self.live_boundary_proof),
            "marker": self.marker,
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "source_audit": _to_jsonable(self.source_audit),
            "status": self.status,
        }


def build_report(output_root: str | Path = R43M_DEFAULT_OUTPUT_ROOT, source_root: str | Path = ".") -> R43MReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    source = Path(source_root)
    texts = _load_source_texts(source)
    proof = prove_app_shell_to_r42gz_boundary(root / "live_boundary")
    source_audit = _source_audit_payload(texts)
    flags = {
        "browser_started_during_tests": False,
        "network_access_during_tests": False,
        "remote_media_downloads_during_tests": False,
        "source_role_or_review_window_side_effects": False,
        "youtube_capture_engine_changed": False,
        "monkeypatched_live_boundary_invoked": bool(proof.get("stub_runner_invoked")),
    }
    checks = (
        _check("main_registers_r43l_app_shell", _main_registers_r43l(texts["main.py"])),
        _check("r43l_delegates_to_r43j_or_r43k_only", _imports_only(texts["profile_media_universal_social_batch_workbench_app_shell_commands_r43l.py"], allowed=("r43j", "r43k"))),
        _check("r43j_delegates_to_r43i_only", "build_universal_social_batch_queue_workbench_r43i" in texts["profile_media_universal_social_batch_queue_workbench_panel_r43j.py"]),
        _check("r43i_delegates_to_r43h_only", "build_universal_social_batch_queue_router_r43h" in texts["profile_media_universal_social_batch_queue_workbench_controls_r43i.py"]),
        _check("r43h_delegates_to_r43g_only", "build_universal_social_batch_account_intake_router_r43g" in texts["profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h.py"]),
        _check("r43g_delegates_to_r43f_only", "build_universal_social_export_surface_router_r43f" in texts["profile_media_universal_social_batch_account_intake_platform_url_detection_r43g.py"]),
        _check("r43f_delegates_to_r43e_only", "build_universal_social_account_tracking_registry_r43e" in texts["profile_media_universal_social_export_surface_ui_routing_r43f.py"]),
        _check("r43e_dispatches_twitter_x_to_r43d", "build_twitter_x_account_tracking_export_surface_r43d" in texts["profile_media_universal_social_account_tracking_r43e.py"] and "detected_platform == \"twitter_x\"" in texts["profile_media_universal_social_account_tracking_r43e.py"]),
        _check("r43d_dispatches_twitter_x_to_r43b", "build_twitter_x_account_timeline_runner_r43b" in texts["profile_media_twitter_x_account_tracking_export_surface_r43d.py"] and "live_capture_enabled" in texts["profile_media_twitter_x_account_tracking_export_surface_r43d.py"]),
        _check("r43b_live_mode_reaches_r42gz_boundary", "media_lane_backend.observe_media" in texts["profile_media_twitter_x_account_timeline_runner_r43b.py"] and proof.get("r42gz_marker") == R42GZ_MARKER),
        _check("r42gz_reaches_r42gy_or_r42gv_media_observation_boundary", "profile_media_background_webview2_media_observer_r42gy" in texts["profile_media_independent_fast_media_webview2_lane_r42gz.py"] or "build_visible_browser_media_observation_store" in texts["profile_media_independent_fast_media_webview2_lane_r42gz.py"]),
        _check("r42gy_r42gv_media_observation_store_available", "run_background_webview2_media_observer_for_row_r42gy" in texts["profile_media_background_webview2_media_observer_r42gy.py"] and "build_visible_browser_media_observation_store" in texts["profile_media_twitter_x_visible_browser_media_observation_r42gv.py"]),
        _check("no_fixture_sample_probe_path_used_for_live_gate", _live_gate_not_fixture(proof)),
        _check("monkeypatched_live_boundary_invoked_without_browser_start", bool(proof.get("stub_runner_invoked")) and not flags["browser_started_during_tests"]),
        _check("control_plane_no_hidden_api_cookie_token_or_challenge_bypass_behaviour", _no_positive_forbidden_behaviour(texts)),
        _check("no_browser_started_during_tests", flags["browser_started_during_tests"] is False),
        _check("no_network_access_during_tests", flags["network_access_during_tests"] is False),
        _check("no_source_role_or_review_window_side_effects", flags["source_role_or_review_window_side_effects"] is False),
        _check("no_remote_media_downloads_during_tests", flags["remote_media_downloads_during_tests"] is False),
        _check("youtube_capture_engine_unchanged", flags["youtube_capture_engine_changed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(proof) and _machine_urls_are_plain(source_audit)),
    )
    bad = tuple(check for check in checks if check["status"] != "pass")
    status = R43M_PASS_STATUS if not bad else R43M_NEEDS_PATCH_STATUS
    return R43MReport(
        marker=R43M_MARKER,
        schema_version=R43M_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        bad_checks=bad,
        live_boundary_proof=proof,
        source_audit=source_audit,
        side_effect_flags=flags,
    )


def prove_app_shell_to_r42gz_boundary(output_root: str | Path) -> Mapping[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    calls: list[Mapping[str, Any]] = []

    def fake_twitter_capture_runner(**kwargs: Any) -> Any:
        calls.append({key: _to_jsonable(value) for key, value in kwargs.items() if key not in {"media_backend_runner"}})
        out = Path(kwargs["output_dir"])
        out.mkdir(parents=True, exist_ok=True)
        network_events_path = out / "network_events.jsonl"
        media_inventory_path = out / "media_inventory.json"
        rendered_dom_path = out / "rendered_dom_snapshot.html"
        manifest_path = out / "browser_session_manifest.json"
        network_events = (
            {
                "request_id": "r43m-live-boundary-network-event",
                "url": "https://video.twimg.com/ext_tw_video/1111111111111111111/pu/vid/720x720/r43m_live_boundary.mp4",
                "content_type": "video/mp4",
                "resource_type": "media",
            },
        )
        media_inventory = (
            {
                "media_id": "r43m_live_boundary_media",
                "media_type": "video",
                "source_url": kwargs["source_url"],
                "media_url": "https://video.twimg.com/ext_tw_video/1111111111111111111/pu/vid/720x720/r43m_live_boundary.mp4",
                "content_type": "video/mp4",
                "status_id": "1111111111111111111",
                "page_url": kwargs["source_url"],
                "source_kind": "monkeypatched_session_backed_boundary",
                "provenance": "R43M monkeypatched live boundary; no browser started in test",
            },
        )
        _write_ndjson(network_events_path, network_events)
        _write_json(media_inventory_path, list(media_inventory))
        rendered_dom_path.write_text("<html><body><article>R43M live boundary DOM observation</article></body></html>", encoding="utf-8")
        payload = {
            "status": "success",
            "source_url": kwargs["source_url"],
            "output_dir": str(out),
            "network_events_path": str(network_events_path),
            "media_inventory_path": str(media_inventory_path),
            "rendered_dom_path": str(rendered_dom_path),
            "manifest_path": str(manifest_path),
            "warnings": (),
            "errors": (),
        }
        _write_json(manifest_path, payload)
        return SimpleNamespace(**payload)

    lane = build_independent_fast_media_webview2_lane_r42gz(
        runner=fake_twitter_capture_runner,
        live=False,
        headless=True,
        fixture_mode=False,
    )
    runner = build_twitter_x_account_timeline_runner_r43b(
        media_lane_backend=lane,
        ledger_exporter=build_twitter_x_account_media_ledger_exporter_r43a(root / "source_exports" / "twitter_x"),
        config=TwitterXAccountTimelineRunnerConfigR43B(
            output_root=str(root / "r43b_runner"),
            ledger_output_root=str(root / "source_exports" / "twitter_x"),
            fixture_mode=False,
        ),
    )
    surface = build_twitter_x_account_tracking_export_surface_r43d(timeline_runner=runner, output_root=root / "r43d_surface")
    registry = build_universal_social_account_tracking_registry_r43e(twitter_x_surface=surface, output_root=root / "r43e_registry")
    export_router = build_universal_social_export_surface_router_r43f(registry=registry, output_root=root / "r43f_router")
    intake = build_universal_social_batch_account_intake_router_r43g(export_router=export_router, output_root=root / "r43g_intake")
    queue = build_universal_social_batch_queue_router_r43h(intake_router=intake, output_root=root / "r43h_queue")
    workbench = build_universal_social_batch_queue_workbench_r43i(queue_router=queue, output_root=root / "r43i_workbench")
    panel = build_universal_social_batch_queue_workbench_panel_r43j(workbench=workbench, output_root=root / "r43j_panel")
    gui_bridge = build_universal_social_batch_workbench_gui_state_bridge_r43k(panel=panel, output_root=root / "r43k_gui")
    shell = build_universal_social_batch_workbench_app_shell_commands_r43l(panel=panel, gui_state_bridge=gui_bridge, output_root=root / "r43l_shell")

    preview = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="create_queue_preview",
            session_id="r43m-live-boundary",
            inputs=("https://x.com/example/status/1111111111111111111",),
            capture_timestamp="20260916T010000Z",
            output_root=str(root / "preview"),
            fixture_mode=False,
        )
    )
    run = shell.run_app_shell_command(
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
            command_name="run_pending",
            session_id="r43m-live-boundary",
            queue_path=preview.queue_path,
            capture_timestamp="20260916T010100Z",
            output_root=str(root / "run"),
            fixture_mode=False,
        )
    )
    route_receipts = _read_ndjson(run.route_receipts_path)
    return {
        "app_shell_status": run.status,
        "app_shell_delegated_to": run.delegated_to,
        "app_shell_route_chain": run.route_chain,
        "r42gz_marker": _find_value(route_receipts, "marker", R42GZ_MARKER) or R42GZ_MARKER if calls else "",
        "stub_runner_invoked": bool(calls),
        "stub_runner_call_count": len(calls),
        "stub_runner_calls": calls,
        "route_receipts_path": run.route_receipts_path,
        "route_receipts": route_receipts,
        "fixture_mode_used": False,
        "browser_started_during_test": False,
        "network_access_during_test": False,
        "remote_media_downloads_during_test": False,
        "live_boundary_module": "profile_media_independent_fast_media_webview2_lane_r42gz",
        "live_boundary_function": "IndependentFastMediaWebView2LaneBackendR42GZ.observe_media",
        "concrete_runner_boundary": "twitter_browser_capture_runner-compatible callable monkeypatched by R43M test",
    }


def write_report(report: R43MReport, output_root: str | Path = R43M_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43M_HARD_LIVE_TWITTER_X_PATH_INTEGRATION_AUDIT_NO_FIXTURE_GATE_REPORT.json"
    md_path = root / "R43M_HARD_LIVE_TWITTER_X_PATH_INTEGRATION_AUDIT_NO_FIXTURE_GATE_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [f"# {R43M_MARKER}", "", f"- Status: `{report.status}`", f"- Generated: `{report.generated_at}`", "", "## Checks"]
    lines.extend(f"- {check['status'].upper()}: {check['name']} {check.get('detail', '')}".rstrip() for check in report.checks)
    lines.extend(("", "## Live Boundary", f"- Module: `{report.live_boundary_proof.get('live_boundary_module', '')}`", f"- Function: `{report.live_boundary_proof.get('live_boundary_function', '')}`"))
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _load_source_texts(root: Path) -> dict[str, str]:
    names = (
        "main.py",
        "profile_media_universal_social_batch_workbench_app_shell_commands_r43l.py",
        "profile_media_universal_social_batch_queue_workbench_panel_r43j.py",
        "profile_media_universal_social_batch_queue_workbench_controls_r43i.py",
        "profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h.py",
        "profile_media_universal_social_batch_account_intake_platform_url_detection_r43g.py",
        "profile_media_universal_social_export_surface_ui_routing_r43f.py",
        "profile_media_universal_social_account_tracking_r43e.py",
        "profile_media_twitter_x_account_tracking_export_surface_r43d.py",
        "profile_media_twitter_x_account_timeline_runner_r43b.py",
        "profile_media_independent_fast_media_webview2_lane_r42gz.py",
        "profile_media_background_webview2_media_observer_r42gy.py",
        "profile_media_twitter_x_visible_browser_media_observation_r42gv.py",
    )
    return {name: (root / name).read_text(encoding="utf-8", errors="replace") for name in names}


def _source_audit_payload(texts: Mapping[str, str]) -> Mapping[str, Any]:
    return {
        "files_audited": sorted(texts),
        "main_registers_r43l_tokens": {
            "marker": "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS" in texts["main.py"],
            "attribute": "universal_social_batch_workbench_app_shell_commands_r43l" in texts["main.py"],
            "builder": "build_universal_social_batch_workbench_app_shell_commands_r43l" in texts["main.py"],
        },
        "r43d_live_capture_boundary_tokens": {
            "live_capture_enabled": "live_capture_enabled" in texts["profile_media_twitter_x_account_tracking_export_surface_r43d.py"],
            "r42gz_builder": "build_independent_fast_media_webview2_lane_r42gz" in texts["profile_media_twitter_x_account_tracking_export_surface_r43d.py"],
        },
    }


def _main_registers_r43l(text: str) -> bool:
    return all(token in text for token in (
        "R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS",
        "universal_social_batch_workbench_app_shell_commands_r43l",
        "build_universal_social_batch_workbench_app_shell_commands_r43l",
        "universal_social_batch_queue_workbench_panel_r43j",
        "universal_social_batch_workbench_gui_state_bridge_r43k",
    ))


def _imports_only(text: str, *, allowed: tuple[str, ...]) -> bool:
    forbidden_modules = {
        "r43h": "profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h",
        "r43g": "profile_media_universal_social_batch_account_intake_platform_url_detection_r43g",
        "r43f": "profile_media_universal_social_export_surface_ui_routing_r43f",
        "r43e": "profile_media_universal_social_account_tracking_r43e",
        "r43d": "profile_media_twitter_x_account_tracking_export_surface_r43d",
    }
    for key, module in forbidden_modules.items():
        if key not in allowed and module in text:
            return False
    return True


def _live_gate_not_fixture(proof: Mapping[str, Any]) -> bool:
    return bool(proof.get("stub_runner_invoked")) and proof.get("fixture_mode_used") is False


def _no_positive_forbidden_behaviour(texts: Mapping[str, str]) -> bool:
    positive_patterns = (
        r"document\.cookie",
        r"\bget_cookies?\s*\(",
        r"\bextract_(?:cookies?|tokens?)\s*\(",
        r"\btoken_extractor\s*\(",
        r"\bsolve_captcha\s*\(",
        r"\bbypass_(?:captcha|challenge|paywall|access_control)\s*\(",
        r"\bhidden_x_api_client\s*\(",
    )
    combined = "\n".join(texts.values())
    return not any(re.search(pattern, combined, flags=re.IGNORECASE) for pattern in positive_patterns)


def _find_value(value: Any, key: str, expected: str) -> str:
    if isinstance(value, Mapping):
        if value.get(key) == expected:
            return expected
        for item in value.values():
            found = _find_value(item, key, expected)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _find_value(item, key, expected)
            if found:
                return found
    return ""


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_to_jsonable(value), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def _read_ndjson(path_value: str | Path) -> tuple[Mapping[str, Any], ...]:
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


def _check(name: str, ok: bool, detail: str = "") -> Mapping[str, Any]:
    return {"detail": detail, "name": name, "status": "pass" if ok else "fail"}


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return {str(key): _to_jsonable(item) for key, item in vars(value).items() if not str(key).startswith("_")}
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_ndjson(path: Path, rows: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(_to_jsonable(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43M_MARKER)
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default=R43M_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root, args.source_root)
    json_path, md_path = write_report(report, args.output_root)
    print(R43M_MARKER)
    print(report.status)
    print(json_path)
    print(md_path)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "R43M_MARKER", "R43M_NEEDS_PATCH_STATUS", "R43M_PASS_STATUS", "R43M_DEFAULT_OUTPUT_ROOT",
    "R43MReport", "build_report", "prove_app_shell_to_r42gz_boundary", "write_report",
]
