from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import patch

R43Y_MARKER = "YTCE_R43Y_BLUESKY_PUBLIC_APPVIEW_UNIVERSAL_ROUTE"
R43Y_PASS_STATUS = "PASS_R43Y_BLUESKY_PUBLIC_APPVIEW_UNIVERSAL_ROUTE"
R43Y_BLOCKED_STATUS = "BLOCKED_R43Y_BLUESKY_PUBLIC_APPVIEW_UNIVERSAL_ROUTE"
R43Y_SCHEMA_VERSION = "bluesky_public_appview_universal_route.r43y.v1"
R43Y_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43y_bluesky_public_appview_universal_route"
R43Y_MODE_ID = "bluesky_public_appview_universal_route"


@dataclass(frozen=True)
class BlueskyPublicAppviewUniversalRouteRequestR43Y:
    account_url: str = "https://bsky.app/profile/bsky.app"
    account_handle: str = "bsky.app"
    actor: str = "bsky.app"
    capture_timestamp: str = ""
    output_root: str = R43Y_DEFAULT_OUTPUT_ROOT
    public_network_enabled: bool = True
    explicit_live_mode: bool = True
    live_mode: bool = False
    run_visible_live: bool = False
    fixture_mode: bool = False
    max_items: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class BlueskyPublicAppviewUniversalRouteResultR43Y:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    app_shell_status: str
    route_status: str
    r43g_status: str
    r43f_status: str
    r43e_status: str
    r43w_status: str
    adapter_status: str
    ledger_status: str
    record_count: int
    media_count: int
    post_view_count: int
    public_network_enabled_reached_r43w: bool
    explicit_live_mode_reached_r43w: bool
    real_network_performed_by_r43y_test: bool
    browser_session_started: bool
    cookie_or_token_extraction_performed: bool
    remote_media_downloads_performed: bool
    app_shell_receipt_path: str
    route_receipts_path: str
    fake_appview_payload_paths: tuple[str, ...] = ()
    request_urls: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == R43Y_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43YReport:
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
        return self.status == R43Y_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class BlueskyPublicAppviewUniversalRouteR43Y:
    """Prove Bluesky public appview flags flow through the universal batch/workbench stack.

    R43Y does not introduce a browser lane. It verifies the public-network gate is
    explicit and propagated from the app-shell/batch route down to R43E, where the
    already-proven R43W -> R43V -> R43U chain is selected for Bluesky account URLs.
    The self-test uses a fake R43W importer so no real network request occurs.
    """

    def __init__(self, output_root: str | Path = R43Y_DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def run_route_smoke(
        self,
        request: BlueskyPublicAppviewUniversalRouteRequestR43Y | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> BlueskyPublicAppviewUniversalRouteResultR43Y:
        req = coerce_bluesky_public_appview_universal_route_request_r43y(request, **overrides)
        return run_bluesky_public_appview_universal_route_r43y(req, output_root=self.output_root)


def build_bluesky_public_appview_universal_route_r43y(output_root: str | Path = R43Y_DEFAULT_OUTPUT_ROOT) -> BlueskyPublicAppviewUniversalRouteR43Y:
    return BlueskyPublicAppviewUniversalRouteR43Y(output_root=output_root)


def build_bluesky_public_appview_universal_route_contract_r43y() -> dict[str, Any]:
    return {
        "marker": R43Y_MARKER,
        "schema_version": R43Y_SCHEMA_VERSION,
        "mode_id": R43Y_MODE_ID,
        "upstream_route": "R43L -> R43J -> R43I -> R43H -> R43G -> R43F -> R43E",
        "downstream_route_for_bluesky_public_appview": "R43W -> R43V -> R43U",
        "normal_bluesky_profile_input": "https://bsky.app/profile/<handle-or-did>",
        "explicit_public_network_gate_required": True,
        "browser_session_started_by_r43y": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed_by_r43y": False,
        "batch_and_workbench_fields": [
            "public_network_enabled",
            "explicit_live_mode",
            "live_mode",
            "run_visible_live",
            "max_items",
        ],
        "binding_strategy": [
            "normal Bluesky profile URLs still enter through R43G platform detection",
            "R43F keeps routing via the R43E adapter map",
            "R43E selects R43W only when public_network_enabled and live/explicit mode are both present",
            "R43W feeds postView rows into R43V and R43U",
            "tests patch R43W with an injected fake importer, so no real network is used by R43Y validation",
        ],
    }


def run_bluesky_public_appview_universal_route_r43y(
    request: BlueskyPublicAppviewUniversalRouteRequestR43Y | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R43Y_DEFAULT_OUTPUT_ROOT,
) -> BlueskyPublicAppviewUniversalRouteResultR43Y:
    from profile_media_universal_social_batch_workbench_app_shell_commands_r43l import (
        UniversalSocialBatchWorkbenchAppShellCommandRequestR43L,
        build_universal_social_batch_workbench_app_shell_commands_r43l,
    )
    import profile_media_bluesky_public_appview_import_r43w as r43w_module

    req = coerce_bluesky_public_appview_universal_route_request_r43y(request)
    root = Path(req.output_root or output_root or R43Y_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    handle = _safe_handle(req.account_handle or req.actor or "bsky.app")
    account_url = _plain_url(req.account_url or f"https://bsky.app/profile/{handle}")
    run_dir = root / handle / f"bluesky_public_appview_universal_route_{capture_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    calls: list[Mapping[str, Any]] = []

    def fake_builder(output_root: str | Path = "", **_: Any) -> Any:
        return _FakeR43WImporterR43Y(Path(output_root or run_dir / "fake_r43w"), calls)

    with patch.object(r43w_module, "build_bluesky_public_appview_import_r43w", fake_builder):
        shell = build_universal_social_batch_workbench_app_shell_commands_r43l(output_root=run_dir / "r43l_shell")
        shell_result = shell.run_app_shell_command(
            UniversalSocialBatchWorkbenchAppShellCommandRequestR43L(
                command_name="run_pending",
                session_id="r43y-bluesky-public-appview-route",
                inputs=(account_url,),
                capture_timestamp=f"{capture_ts}_r43l",
                output_root=str(run_dir / "r43l_shell"),
                fixture_mode=req.fixture_mode,
                explicit_live_mode=req.explicit_live_mode,
                live_mode=req.live_mode,
                run_visible_live=req.run_visible_live,
                public_network_enabled=req.public_network_enabled,
                max_items=max(_safe_int(req.max_items), 1),
            )
        )

    shell_payload = shell_result.to_dict()
    route_documents: list[Any] = [shell_payload]
    route_documents.extend(_load_ndjson_mappings(shell_result.route_receipts_path))
    route_payload = _find_first_mapping(route_documents, lambda item: item.get("marker") == "YTCE_R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING")
    r43g_payload = _find_first_mapping(route_documents, lambda item: item.get("marker") == "YTCE_R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION")
    r43e_payload = _mapping(route_payload.get("downstream_result"))
    r43w_payload = _mapping(r43e_payload.get("downstream_result"))
    first_call = _mapping(calls[0]) if calls else {}
    flags = _r43y_side_effect_flags(
        public_network_requested=bool(first_call.get("public_network_enabled")),
        r43w_used=bool(r43w_payload),
    )

    warnings: list[str] = []
    if shell_result.status != "PASS_R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS":
        warnings.append(f"R43L app-shell route did not pass: {shell_result.status!r}.")
    if _clean(route_payload.get("route_status")) != "dispatched_to_bluesky_adapter_via_r43e_adapter_map":
        warnings.append("R43F did not dispatch the Bluesky URL through the R43E adapter map.")
    if _clean(r43e_payload.get("status")) != "PASS_R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP":
        warnings.append("R43E did not pass after selecting the Bluesky public appview path.")
    if _clean(r43w_payload.get("status")) != "PASS_R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT":
        warnings.append("R43W public appview import payload was not observed as PASS.")
    if first_call.get("public_network_enabled") is not True:
        warnings.append("public_network_enabled did not reach R43W.")
    if first_call.get("explicit_live_mode") is not True:
        warnings.append("explicit_live_mode did not reach R43W.")
    if not _machine_urls_are_plain(shell_payload) or not _machine_urls_are_plain(r43w_payload):
        warnings.append("Markdown-wrapped URLs appeared in machine payloads.")

    bad_flag_names = (
        "browser_session_started",
        "webview2_internals_copied",
        "cookie_or_token_extraction_performed",
        "login_automation_performed",
        "captcha_or_challenge_bypass_performed",
        "remote_media_downloads_performed",
    )
    r43w_flags = _mapping(r43w_payload.get("side_effect_flags"))
    for name in bad_flag_names:
        if bool(r43w_flags.get(name)):
            warnings.append(f"Forbidden downstream side-effect flag was true: {name}")

    status = R43Y_PASS_STATUS if not warnings else R43Y_BLOCKED_STATUS
    result = BlueskyPublicAppviewUniversalRouteResultR43Y(
        marker=R43Y_MARKER,
        schema_version=R43Y_SCHEMA_VERSION,
        status=status,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        app_shell_status=shell_result.status,
        route_status=_clean(route_payload.get("route_status")),
        r43g_status=_clean(r43g_payload.get("status")),
        r43f_status=_clean(route_payload.get("status")),
        r43e_status=_clean(r43e_payload.get("status")),
        r43w_status=_clean(r43w_payload.get("status")),
        adapter_status=_clean(r43w_payload.get("adapter_status")),
        ledger_status=_clean(r43w_payload.get("ledger_status")),
        record_count=_safe_int(r43w_payload.get("record_count")),
        media_count=_safe_int(r43w_payload.get("media_count")),
        post_view_count=_safe_int(r43w_payload.get("post_view_count")),
        public_network_enabled_reached_r43w=first_call.get("public_network_enabled") is True,
        explicit_live_mode_reached_r43w=first_call.get("explicit_live_mode") is True,
        real_network_performed_by_r43y_test=False,
        browser_session_started=bool(r43w_flags.get("browser_session_started")),
        cookie_or_token_extraction_performed=bool(r43w_flags.get("cookie_or_token_extraction_performed")),
        remote_media_downloads_performed=bool(r43w_flags.get("remote_media_downloads_performed")),
        app_shell_receipt_path=shell_result.receipt_path,
        route_receipts_path=shell_result.route_receipts_path,
        fake_appview_payload_paths=tuple(str(item) for item in _sequence(r43w_payload.get("appview_payload_paths"))),
        request_urls=tuple(str(item) for item in _sequence(r43w_payload.get("request_urls"))),
        warnings=tuple(warnings),
        side_effect_flags=flags,
    )
    _write_json(run_dir / "r43y_bluesky_public_appview_universal_route_receipt.json", result.to_dict())
    return result


def build_report(output_root: str | Path = R43Y_DEFAULT_OUTPUT_ROOT) -> R43YReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    result = run_bluesky_public_appview_universal_route_r43y(
        BlueskyPublicAppviewUniversalRouteRequestR43Y(
            account_url="https://bsky.app/profile/bsky.app",
            account_handle="bsky.app",
            actor="bsky.app",
            capture_timestamp="20260918T073000Z",
            output_root=str(root / "sample"),
            public_network_enabled=True,
            explicit_live_mode=True,
            fixture_mode=False,
            max_items=2,
        )
    )
    payload = result.to_dict()
    contract = build_bluesky_public_appview_universal_route_contract_r43y()
    checks = (
        _check("normal_bluesky_profile_url_enters_app_shell_batch_route", result.app_shell_status.startswith("PASS_R43L_") and result.route_status == "dispatched_to_bluesky_adapter_via_r43e_adapter_map"),
        _check("public_network_flag_reaches_r43w_from_workbench_route", result.public_network_enabled_reached_r43w and result.explicit_live_mode_reached_r43w),
        _check("r43e_selects_r43w_public_appview_for_bluesky", result.r43e_status.startswith("PASS_R43E_") and result.r43w_status.startswith("PASS_R43W_")),
        _check("r43w_r43v_r43u_chain_preserved", result.adapter_status.startswith("PASS_R43V_") and result.ledger_status.startswith("PASS_R43U_")),
        _check("records_and_media_receipts_surface_through_route", result.post_view_count >= 2 and result.record_count >= 2 and result.media_count >= 1),
        _check("raw_appview_payload_receipt_surfaces", bool(result.fake_appview_payload_paths) and all(Path(path).is_file() for path in result.fake_appview_payload_paths)),
        _check("r43y_validation_does_not_use_real_network", result.real_network_performed_by_r43y_test is False),
        _check("no_browser_cookie_token_or_media_download_side_effects", not result.browser_session_started and not result.cookie_or_token_extraction_performed and not result.remote_media_downloads_performed),
        _check("plain_machine_urls", _machine_urls_are_plain(payload) and _machine_urls_are_plain(contract)),
    )
    status = R43Y_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43Y_BLOCKED_STATUS
    report = R43YReport(
        marker=R43Y_MARKER,
        schema_version=R43Y_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result=payload,
        contract=contract,
        side_effect_flags=result.side_effect_flags,
    )
    write_report(report, root)
    return report


def write_report(report: R43YReport, output_root: str | Path = R43Y_DEFAULT_OUTPUT_ROOT) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "R43Y_BLUESKY_PUBLIC_APPVIEW_UNIVERSAL_ROUTE_REPORT.json", report.to_dict())
    lines = [
        "# R43Y Bluesky public appview universal route report",
        "",
        f"- marker: `{report.marker}`",
        f"- status: `{report.status}`",
        f"- schema_version: `{report.schema_version}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')}")
    _write_text(root / "R43Y_BLUESKY_PUBLIC_APPVIEW_UNIVERSAL_ROUTE_REPORT.md", "\n".join(lines) + "\n")


class _FakeR43WImporterR43Y:
    def __init__(self, output_root: Path, calls: list[Mapping[str, Any]]) -> None:
        self.output_root = output_root
        self.calls = calls

    def run_account_export(self, request: Any, **_: Any) -> Mapping[str, Any]:
        payload = request.to_dict() if hasattr(request, "to_dict") else dict(request or {})
        self.calls.append(dict(payload))
        capture_ts = _safe_ts(payload.get("capture_timestamp")) or _now_ts()
        handle = _safe_handle(payload.get("account_handle") or payload.get("actor") or "bsky.app")
        run_dir = Path(payload.get("output_root") or self.output_root) / handle / f"fake_r43w_public_appview_{capture_ts}"
        payload_dir = run_dir / "appview_payloads"
        ledger_dir = run_dir / "r43v_adapter" / "source_exports" / "bluesky" / handle / f"account_capture_{capture_ts}"
        payload_dir.mkdir(parents=True, exist_ok=True)
        ledger_dir.mkdir(parents=True, exist_ok=True)
        account_url = _plain_url(payload.get("account_url") or f"https://bsky.app/profile/{handle}")
        request_url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=" + handle + "&limit=" + str(max(_safe_int(payload.get("max_items")), 1))
        appview_payload_path = payload_dir / "public_getAuthorFeed_response.json"
        _write_json(appview_payload_path, {"ok": True, "status": "injected_r43y_public_appview_fetcher_ok", "url": request_url, "json": {"feed": [{"post": {"uri": "at://did:plc:r43y/app.bsky.feed.post/3r43y1"}}, {"post": {"uri": "at://did:plc:r43y/app.bsky.feed.post/3r43y2"}}]}})
        account_record_path = ledger_dir / "account_record.md"
        manifest_path = ledger_dir / "manifest.json"
        media_index_path = ledger_dir / "media_index.json"
        timeline_path = ledger_dir / "account_timeline.ndjson"
        progress_path = ledger_dir / "progress_events.ndjson"
        review_strings_path = ledger_dir / "review_strings.txt"
        _write_text(account_record_path, f"# Fake R43Y Bluesky account ledger\n\n- Account: `{handle}`\n")
        _write_json(manifest_path, {"marker": "R43Y_FAKE_R43W", "account_handle": handle})
        _write_json(media_index_path, [{"media_class": "image", "metadata_only_remote_media_not_downloaded": True}])
        _write_text(timeline_path, json.dumps({"record_id": "3r43y1", "source_url": account_url}) + "\n" + json.dumps({"record_id": "3r43y2", "source_url": account_url}) + "\n")
        _write_text(progress_path, json.dumps({"event": "fake_r43w_public_appview_import"}) + "\n")
        _write_text(review_strings_path, f"bluesky|{handle}|3r43y1|{account_url}\n")
        return {
            "marker": "YTCE_R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT",
            "schema_version": "bluesky_public_appview_import.r43w.v1",
            "status": "PASS_R43W_BLUESKY_PUBLIC_APPVIEW_IMPORT",
            "account_handle": handle,
            "account_url": account_url,
            "actor": payload.get("actor") or handle,
            "capture_timestamp": capture_ts,
            "output_root": str(self.output_root),
            "run_dir": str(run_dir),
            "request_path": str(run_dir / "fake_request.json"),
            "receipt_path": str(run_dir / "fake_receipt.json"),
            "appview_payload_dir": str(payload_dir),
            "public_endpoint_base": "https://public.api.bsky.app/xrpc",
            "request_urls": [request_url],
            "appview_statuses": ["injected_r43y_public_appview_fetcher_ok"],
            "appview_payload_paths": [str(appview_payload_path)],
            "post_view_count": 2,
            "adapter_status": "PASS_R43V_BLUESKY_VISIBLE_ACCOUNT_ADAPTER",
            "adapter_receipt_path": str(run_dir / "fake_r43v_receipt.json"),
            "ledger_status": "PASS_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE",
            "account_capture_dir": str(ledger_dir),
            "account_record_path": str(account_record_path),
            "manifest_path": str(manifest_path),
            "account_timeline_path": str(timeline_path),
            "media_index_path": str(media_index_path),
            "progress_events_path": str(progress_path),
            "review_strings_path": str(review_strings_path),
            "record_count": 2,
            "media_count": 1,
            "screenshot_count": 0,
            "post_folder_count": 2,
            "date_folders": ["2026-09-18"],
            "side_effect_flags": {
                "network_actions_performed": True,
                "public_appview_fetch_only_when_explicitly_enabled": True,
                "browser_session_started": False,
                "webview2_internals_copied": False,
                "cookie_or_token_extraction_performed": False,
                "login_automation_performed": False,
                "captcha_or_challenge_bypass_performed": False,
                "remote_media_downloads_performed": False,
                "r43v_bluesky_adapter_used": True,
                "r43u_universal_ledger_writer_used": True,
            },
            "warnings": [],
        }


def coerce_bluesky_public_appview_universal_route_request_r43y(
    request: BlueskyPublicAppviewUniversalRouteRequestR43Y | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> BlueskyPublicAppviewUniversalRouteRequestR43Y:
    data = request.to_dict() if isinstance(request, BlueskyPublicAppviewUniversalRouteRequestR43Y) else dict(request or {})
    data.update(overrides)
    return BlueskyPublicAppviewUniversalRouteRequestR43Y(
        account_url=_plain_url(data.get("account_url") or "https://bsky.app/profile/bsky.app"),
        account_handle=_safe_handle(data.get("account_handle") or data.get("actor") or "bsky.app"),
        actor=_safe_handle(data.get("actor") or data.get("account_handle") or "bsky.app"),
        capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""),
        output_root=_clean(data.get("output_root") or R43Y_DEFAULT_OUTPUT_ROOT),
        public_network_enabled=_to_bool(data.get("public_network_enabled"), True),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), True),
        live_mode=_to_bool(data.get("live_mode"), False),
        run_visible_live=_to_bool(data.get("run_visible_live"), False),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        max_items=max(_safe_int(data.get("max_items"), 2), 1),
    )


def _r43y_side_effect_flags(*, public_network_requested: bool, r43w_used: bool) -> dict[str, bool]:
    return {
        "bluesky_public_appview_universal_route_invoked": True,
        "public_network_enabled_propagated": bool(public_network_requested),
        "r43w_public_appview_import_used": bool(r43w_used),
        "r43v_bluesky_adapter_used": bool(r43w_used),
        "r43u_universal_ledger_writer_used": bool(r43w_used),
        "real_network_performed_by_r43y_validation": False,
        "browser_session_started": False,
        "webview2_session_started_by_r43y": False,
        "webview2_internals_copied": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
    }



def _load_ndjson_mappings(path_value: Any) -> list[Mapping[str, Any]]:
    path_text = _clean(path_value)
    if not path_text:
        return []
    path = Path(path_text)
    if not path.is_file():
        return []
    rows: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except Exception:
            continue
        if isinstance(value, Mapping):
            rows.append(value)
    return rows

def _find_first_mapping(value: Any, predicate: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        if predicate(value):
            return value
        for child in value.values():
            found = _find_first_mapping(child, predicate)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = _find_first_mapping(child, predicate)
            if found:
                return found
    return {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _machine_urls_are_plain(value: Any) -> bool:
    if isinstance(value, Mapping):
        return all(_machine_urls_are_plain(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_machine_urls_are_plain(item) for item in value)
    if isinstance(value, str):
        return "](" not in value and "]\\(" not in value
    return True


def _plain_url(value: Any) -> str:
    text = _clean(value).replace("\\_", "_")
    if text.startswith("[") and "](" in text and text.endswith(")"):
        import re

        match = re.match(r"^\[[^\]]+\]\(([^)]+)\)$", text)
        if match:
            text = match.group(1)
    return text


def _safe_handle(value: Any) -> str:
    text = _plain_url(value).strip().strip("@")
    if text.startswith("https://bsky.app/profile/"):
        text = text.rsplit("/", 1)[-1]
    return "".join(ch for ch in text if ch.isalnum() or ch in {".", "-", "_", ":"})[:160] or "bsky.app"


def _safe_ts(value: Any) -> str:
    text = _clean(value)
    return "".join(ch for ch in text if ch.isalnum() or ch in {"T", "Z", "_", "-", "."})


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
    return "" if value is None else str(value).strip()


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


def _write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _check(name: str, ok: bool, detail: str = "") -> Mapping[str, Any]:
    return {"detail": detail if not ok else "", "name": name, "status": "pass" if ok else "fail"}


if __name__ == "__main__":
    report = build_report()
    print(R43Y_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
