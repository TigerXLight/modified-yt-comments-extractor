from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from profile_media_bluesky_public_appview_import_r43w import (
    BLUESKY_PUBLIC_APPVIEW_BASE_R43W,
    R43W_PASS_STATUS,
    BlueskyPublicAppviewImportRequestR43W,
    build_bluesky_get_author_feed_url_r43w,
    build_bluesky_public_appview_import_r43w,
    build_fake_bluesky_public_appview_feed_response_r43w,
)

R43X_MARKER = "YTCE_R43X_BLUESKY_REAL_PUBLIC_APPVIEW_SMOKE"
R43X_PASS_STATUS = "PASS_R43X_BLUESKY_REAL_PUBLIC_APPVIEW_SMOKE"
R43X_BLOCKED_STATUS = "BLOCKED_R43X_BLUESKY_REAL_PUBLIC_APPVIEW_SMOKE"
R43X_SCHEMA_VERSION = "bluesky_real_public_appview_smoke.r43x.v1"
R43X_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43x_bluesky_real_public_appview_smoke"
R43X_MODE_ID = "bluesky_real_public_appview_smoke"
R43X_DEFAULT_ACTOR = "bsky.app"

FetcherR43X = Callable[[str], Mapping[str, Any]]

BAD_SIDE_EFFECT_FLAGS_R43X = (
    "browser_session_started",
    "webview2_session_started_by_r43w",
    "webview2_internals_copied",
    "hidden_platform_api_scraping_performed",
    "cookie_or_token_extraction_performed",
    "login_automation_performed",
    "captcha_or_challenge_bypass_performed",
    "remote_media_downloads_performed",
)


@dataclass(frozen=True)
class BlueskyRealPublicAppviewSmokeRequestR43X:
    actor: str = R43X_DEFAULT_ACTOR
    account_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    output_root: str = R43X_DEFAULT_OUTPUT_ROOT
    max_items: int = 3
    timeout_seconds: float = 20.0
    include_media: bool = True
    include_static_screenshots: bool = False
    require_screenshot_receipts: bool = False
    public_network_enabled: bool = False
    explicit_live_mode: bool = False
    live_mode: bool = False
    feed_filter: str = "posts_and_author_threads"
    include_pins: bool = True
    injected_fetcher_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class BlueskyRealPublicAppviewSmokeResultR43X:
    marker: str
    schema_version: str
    status: str
    actor: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    request_path: str
    receipt_path: str
    public_endpoint_base: str
    request_urls: tuple[str, ...] = ()
    appview_statuses: tuple[str, ...] = ()
    appview_payload_paths: tuple[str, ...] = ()
    public_network_requested: bool = False
    network_actions_performed: bool = False
    injected_fetcher_used: bool = False
    r43w_status: str = ""
    r43w_receipt_path: str = ""
    r43w_run_dir: str = ""
    adapter_status: str = ""
    ledger_status: str = ""
    account_capture_dir: str = ""
    account_record_path: str = ""
    manifest_path: str = ""
    account_timeline_path: str = ""
    media_index_path: str = ""
    progress_events_path: str = ""
    review_strings_path: str = ""
    post_view_count: int = 0
    record_count: int = 0
    media_count: int = 0
    post_folder_count: int = 0
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43X_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43XReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    blocked_gate_result: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43X_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class BlueskyRealPublicAppviewSmokeR43X:
    def __init__(self, output_root: str | Path = R43X_DEFAULT_OUTPUT_ROOT, *, fetcher: FetcherR43X | None = None) -> None:
        self.output_root = Path(output_root)
        self.fetcher = fetcher

    def run_smoke(self, request: BlueskyRealPublicAppviewSmokeRequestR43X | Mapping[str, Any] | None = None) -> BlueskyRealPublicAppviewSmokeResultR43X:
        return run_bluesky_real_public_appview_smoke_r43x(
            request,
            output_root=self.output_root,
            fetcher=self.fetcher,
        )


def build_bluesky_real_public_appview_smoke_r43x(
    output_root: str | Path = R43X_DEFAULT_OUTPUT_ROOT,
    *,
    fetcher: FetcherR43X | None = None,
) -> BlueskyRealPublicAppviewSmokeR43X:
    return BlueskyRealPublicAppviewSmokeR43X(output_root=output_root, fetcher=fetcher)


def build_bluesky_real_public_appview_smoke_contract_r43x() -> dict[str, Any]:
    return {
        "marker": R43X_MARKER,
        "schema_version": R43X_SCHEMA_VERSION,
        "mode_id": R43X_MODE_ID,
        "default_actor": R43X_DEFAULT_ACTOR,
        "public_endpoint_base": BLUESKY_PUBLIC_APPVIEW_BASE_R43W,
        "public_endpoints_used": [
            "app.bsky.feed.getAuthorFeed",
        ],
        "downstream_import_lane": "profile_media_bluesky_public_appview_import_r43w",
        "downstream_adapter": "profile_media_bluesky_visible_account_adapter_r43v",
        "downstream_ledger": "profile_media_universal_social_account_ledger_contract_r43u",
        "explicit_public_network_gate_required": True,
        "remote_media_downloads_performed_by_r43x": False,
        "browser_session_started_by_r43x": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "binding_strategy": [
            "request explicit public network mode from the operator",
            "fetch public app.bsky.feed.getAuthorFeed through R43W",
            "write raw public appview JSON receipts",
            "feed postView rows through R43W to R43V and R43U",
            "assert no browser state, cookies, tokens, login automation, or remote media downloads",
        ],
    }


def run_bluesky_real_public_appview_smoke_r43x(
    request: BlueskyRealPublicAppviewSmokeRequestR43X | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R43X_DEFAULT_OUTPUT_ROOT,
    fetcher: FetcherR43X | None = None,
) -> BlueskyRealPublicAppviewSmokeResultR43X:
    req = coerce_bluesky_real_public_appview_smoke_request_r43x(request)
    root = Path(req.output_root or output_root or R43X_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    actor = _safe_actor(req.actor or req.account_handle or R43X_DEFAULT_ACTOR)
    handle = _safe_handle(req.account_handle or actor)
    account_url = _plain_url(req.account_url or f"https://bsky.app/profile/{actor}")
    run_dir = root / handle / f"bluesky_real_public_appview_smoke_{capture_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "r43x_bluesky_real_public_appview_smoke_request.json"
    receipt_path = run_dir / "r43x_bluesky_real_public_appview_smoke_receipt.json"
    _write_json(request_path, req.to_dict())

    public_network_requested = bool(req.public_network_enabled or req.explicit_live_mode or req.live_mode)
    injected_fetcher_used = fetcher is not None or bool(req.injected_fetcher_label)
    warnings: list[str] = []
    r43w_payload: dict[str, Any] = {}

    if not public_network_requested:
        warnings.append("R43X real public appview smoke requires public_network_enabled, explicit_live_mode, or live_mode.")
        flags = build_r43x_side_effect_flags(
            public_network_requested=False,
            network_actions_performed=False,
            injected_fetcher_used=injected_fetcher_used,
        )
        result = _build_result(
            status=R43X_BLOCKED_STATUS,
            req=req,
            actor=actor,
            handle=handle,
            account_url=account_url,
            capture_ts=capture_ts,
            root=root,
            run_dir=run_dir,
            request_path=request_path,
            receipt_path=receipt_path,
            public_network_requested=False,
            network_actions_performed=False,
            injected_fetcher_used=injected_fetcher_used,
            r43w_payload={},
            warnings=warnings,
            side_effect_flags=flags,
        )
        _write_json(receipt_path, result.to_dict())
        return result

    importer = build_bluesky_public_appview_import_r43w(output_root=run_dir / "r43w_import", fetcher=fetcher)
    r43w_request = BlueskyPublicAppviewImportRequestR43W(
        account_url=account_url,
        account_handle=handle,
        actor=actor,
        capture_timestamp=capture_ts,
        output_root=str(run_dir / "r43w_import"),
        live_mode=True,
        explicit_live_mode=True,
        public_network_enabled=True,
        include_media=req.include_media,
        include_static_screenshots=req.include_static_screenshots,
        require_screenshot_receipts=req.require_screenshot_receipts,
        max_items=max(_safe_int(req.max_items), 1),
        timeout_seconds=max(float(req.timeout_seconds or 20.0), 1.0),
        include_pins=req.include_pins,
        feed_filter=req.feed_filter,
    )
    r43w_result = importer.run_account_export(r43w_request)
    r43w_payload = r43w_result.to_dict()
    r43w_flags = _mapping(r43w_payload.get("side_effect_flags"))
    network_actions_performed = bool(r43w_flags.get("network_actions_performed"))
    flags = build_r43x_side_effect_flags(
        public_network_requested=True,
        network_actions_performed=network_actions_performed,
        injected_fetcher_used=injected_fetcher_used,
    )

    bad_flags = [name for name in BAD_SIDE_EFFECT_FLAGS_R43X if bool(r43w_flags.get(name))]
    if bad_flags:
        warnings.append("Unexpected forbidden side-effect flags from R43W: " + ", ".join(sorted(bad_flags)))
    if _clean(r43w_payload.get("status")) != R43W_PASS_STATUS:
        warnings.append("R43W public appview import did not pass: " + (_clean(r43w_payload.get("status")) or "unknown"))
    if not _sequence(r43w_payload.get("request_urls")):
        warnings.append("R43W did not record a public getAuthorFeed request URL.")
    if _safe_int(r43w_payload.get("post_view_count")) < 1:
        warnings.append("R43W did not import any public postView rows.")
    if _safe_int(r43w_payload.get("record_count")) < 1:
        warnings.append("R43W/R43V/R43U did not write any ledger records.")
    if not all(Path(path).is_file() for path in _sequence(r43w_payload.get("appview_payload_paths"))):
        warnings.append("One or more raw public appview payload receipt files were not written.")
    if not _machine_urls_are_plain(r43w_payload):
        warnings.append("R43W payload contains markdown-formatted URLs; expected plain machine URLs.")

    status = R43X_PASS_STATUS if not warnings else R43X_BLOCKED_STATUS
    result = _build_result(
        status=status,
        req=req,
        actor=actor,
        handle=handle,
        account_url=account_url,
        capture_ts=capture_ts,
        root=root,
        run_dir=run_dir,
        request_path=request_path,
        receipt_path=receipt_path,
        public_network_requested=True,
        network_actions_performed=network_actions_performed,
        injected_fetcher_used=injected_fetcher_used,
        r43w_payload=r43w_payload,
        warnings=warnings,
        side_effect_flags=flags,
    )
    _write_json(receipt_path, result.to_dict())
    return result


def _build_result(
    *,
    status: str,
    req: BlueskyRealPublicAppviewSmokeRequestR43X,
    actor: str,
    handle: str,
    account_url: str,
    capture_ts: str,
    root: Path,
    run_dir: Path,
    request_path: Path,
    receipt_path: Path,
    public_network_requested: bool,
    network_actions_performed: bool,
    injected_fetcher_used: bool,
    r43w_payload: Mapping[str, Any],
    warnings: list[str],
    side_effect_flags: Mapping[str, bool],
) -> BlueskyRealPublicAppviewSmokeResultR43X:
    payload = _mapping(r43w_payload)
    return BlueskyRealPublicAppviewSmokeResultR43X(
        marker=R43X_MARKER,
        schema_version=R43X_SCHEMA_VERSION,
        status=status,
        actor=actor,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        public_endpoint_base=BLUESKY_PUBLIC_APPVIEW_BASE_R43W,
        request_urls=tuple(str(item) for item in _sequence(payload.get("request_urls"))),
        appview_statuses=tuple(str(item) for item in _sequence(payload.get("appview_statuses"))),
        appview_payload_paths=tuple(str(item) for item in _sequence(payload.get("appview_payload_paths"))),
        public_network_requested=public_network_requested,
        network_actions_performed=network_actions_performed,
        injected_fetcher_used=injected_fetcher_used,
        r43w_status=_clean(payload.get("status")),
        r43w_receipt_path=_clean(payload.get("receipt_path")),
        r43w_run_dir=_clean(payload.get("run_dir")),
        adapter_status=_clean(payload.get("adapter_status")),
        ledger_status=_clean(payload.get("ledger_status")),
        account_capture_dir=_clean(payload.get("account_capture_dir")),
        account_record_path=_clean(payload.get("account_record_path")),
        manifest_path=_clean(payload.get("manifest_path")),
        account_timeline_path=_clean(payload.get("account_timeline_path")),
        media_index_path=_clean(payload.get("media_index_path")),
        progress_events_path=_clean(payload.get("progress_events_path")),
        review_strings_path=_clean(payload.get("review_strings_path")),
        post_view_count=_safe_int(payload.get("post_view_count")),
        record_count=_safe_int(payload.get("record_count")),
        media_count=_safe_int(payload.get("media_count")),
        post_folder_count=_safe_int(payload.get("post_folder_count")),
        side_effect_flags=side_effect_flags,
        warnings=tuple(warnings),
    )


def build_r43x_side_effect_flags(
    *,
    public_network_requested: bool = False,
    network_actions_performed: bool = False,
    injected_fetcher_used: bool = False,
) -> dict[str, bool]:
    return {
        "bluesky_real_public_appview_smoke_invoked": True,
        "public_network_requested": bool(public_network_requested),
        "network_actions_performed": bool(network_actions_performed),
        "injected_fetcher_used": bool(injected_fetcher_used),
        "browser_session_started": False,
        "webview2_session_started_by_r43x": False,
        "webview2_internals_copied": False,
        "hidden_platform_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "remote_media_downloads_performed": False,
        "r43w_public_appview_import_used": bool(public_network_requested),
        "r43v_bluesky_adapter_used": bool(public_network_requested),
        "r43u_universal_ledger_writer_used": bool(public_network_requested),
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
    }


def build_report(output_root: str | Path = R43X_DEFAULT_OUTPUT_ROOT) -> R43XReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    blocked_result = run_bluesky_real_public_appview_smoke_r43x(
        BlueskyRealPublicAppviewSmokeRequestR43X(
            actor=R43X_DEFAULT_ACTOR,
            account_handle=R43X_DEFAULT_ACTOR,
            account_url=f"https://bsky.app/profile/{R43X_DEFAULT_ACTOR}",
            capture_timestamp="20260918T071500Z",
            output_root=str(root / "blocked_gate_sample"),
            max_items=2,
        ),
        fetcher=_build_fake_r43x_fetcher(actor=R43X_DEFAULT_ACTOR),
    )
    sample_result = run_bluesky_real_public_appview_smoke_r43x(
        BlueskyRealPublicAppviewSmokeRequestR43X(
            actor=R43X_DEFAULT_ACTOR,
            account_handle=R43X_DEFAULT_ACTOR,
            account_url=f"https://bsky.app/profile/{R43X_DEFAULT_ACTOR}",
            capture_timestamp="20260918T071600Z",
            output_root=str(root / "injected_fetcher_sample"),
            public_network_enabled=True,
            explicit_live_mode=True,
            max_items=2,
            timeout_seconds=5.0,
            injected_fetcher_label="r43x_fixture_fetcher_no_external_network",
        ),
        fetcher=_build_fake_r43x_fetcher(actor=R43X_DEFAULT_ACTOR),
    )
    sample = sample_result.to_dict()
    blocked = blocked_result.to_dict()
    contract = build_bluesky_real_public_appview_smoke_contract_r43x()
    expected_url = build_bluesky_get_author_feed_url_r43w(actor=R43X_DEFAULT_ACTOR, limit=2)
    checks = (
        _check("explicit_public_network_gate_blocks_accidental_fetch", blocked_result.status == R43X_BLOCKED_STATUS and blocked_result.network_actions_performed is False and not blocked_result.request_urls),
        _check("injected_fetcher_exercises_public_appview_smoke_path", sample_result.status == R43X_PASS_STATUS and sample_result.public_network_requested and sample_result.injected_fetcher_used),
        _check("request_url_is_public_get_author_feed", any(url.startswith(BLUESKY_PUBLIC_APPVIEW_BASE_R43W + "/app.bsky.feed.getAuthorFeed?") for url in sample_result.request_urls) and "actor=bsky.app" in expected_url),
        _check("r43w_r43v_r43u_downstream_chain_passes", sample_result.r43w_status == R43W_PASS_STATUS and sample_result.adapter_status.startswith("PASS_R43V_") and sample_result.ledger_status.startswith("PASS_R43U_")),
        _check("raw_appview_payload_receipts_written", sample_result.appview_payload_paths and all(Path(path).is_file() for path in sample_result.appview_payload_paths)),
        _check("ledger_records_written", sample_result.post_view_count >= 1 and sample_result.record_count >= 1 and sample_result.post_folder_count >= 1),
        _check("no_browser_cookie_token_or_media_download_side_effects", not any(sample["side_effect_flags"].get(name) for name in ("browser_session_started", "webview2_internals_copied", "cookie_or_token_extraction_performed", "login_automation_performed", "remote_media_downloads_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(sample) and _machine_urls_are_plain(blocked) and _machine_urls_are_plain(contract)),
    )
    status = R43X_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43X_BLOCKED_STATUS
    report = R43XReport(
        marker=R43X_MARKER,
        schema_version=R43X_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        sample_result=sample,
        blocked_gate_result=blocked,
        contract=contract,
        side_effect_flags=build_r43x_side_effect_flags(public_network_requested=True, network_actions_performed=True, injected_fetcher_used=True),
    )
    write_report(report, root)
    return report


def write_report(report: R43XReport, output_root: str | Path = R43X_DEFAULT_OUTPUT_ROOT) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "R43X_BLUESKY_REAL_PUBLIC_APPVIEW_SMOKE_REPORT.json", report.to_dict())
    lines = [
        "# R43X Bluesky real public appview smoke report",
        "",
        f"- marker: `{report.marker}`",
        f"- status: `{report.status}`",
        f"- schema_version: `{report.schema_version}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- {check['status']}: {check['name']} {check.get('detail', '')}".rstrip())
    lines.extend(
        [
            "",
            "## Boundary",
            "- The default report uses an injected fetcher so unit validation does not perform external network access.",
            "- A real run requires `--public-network-enabled` or `--explicit-live-mode`.",
            "- R43X delegates public getAuthorFeed JSON to R43W, then R43V and R43U for ledger output.",
            "- It does not start a browser, read cookies or tokens, copy WebView2 internals, automate login, bypass challenges, or download remote media.",
        ]
    )
    _write_text(root / "R43X_BLUESKY_REAL_PUBLIC_APPVIEW_SMOKE_REPORT.md", "\n".join(lines) + "\n")


def coerce_bluesky_real_public_appview_smoke_request_r43x(
    value: BlueskyRealPublicAppviewSmokeRequestR43X | Mapping[str, Any] | None,
) -> BlueskyRealPublicAppviewSmokeRequestR43X:
    if isinstance(value, BlueskyRealPublicAppviewSmokeRequestR43X):
        return value
    data = _mapping(value)
    return BlueskyRealPublicAppviewSmokeRequestR43X(
        actor=_clean(data.get("actor") or R43X_DEFAULT_ACTOR),
        account_url=_plain_url(data.get("account_url")),
        account_handle=_clean(data.get("account_handle")),
        capture_timestamp=_safe_ts(data.get("capture_timestamp")),
        output_root=_clean(data.get("output_root") or R43X_DEFAULT_OUTPUT_ROOT),
        max_items=max(_safe_int(data.get("max_items") or 3), 1),
        timeout_seconds=float(data.get("timeout_seconds") or 20.0),
        include_media=_to_bool(data.get("include_media"), True),
        include_static_screenshots=_to_bool(data.get("include_static_screenshots"), False),
        require_screenshot_receipts=_to_bool(data.get("require_screenshot_receipts"), False),
        public_network_enabled=_to_bool(data.get("public_network_enabled"), False),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        feed_filter=_clean(data.get("feed_filter") or "posts_and_author_threads"),
        include_pins=_to_bool(data.get("include_pins"), True),
        injected_fetcher_label=_clean(data.get("injected_fetcher_label")),
    )


def _build_fake_r43x_fetcher(*, actor: str = R43X_DEFAULT_ACTOR) -> FetcherR43X:
    def fetcher(url: str) -> Mapping[str, Any]:
        return {
            "ok": True,
            "status": "injected_r43x_public_appview_fetcher_ok",
            "status_code": 200,
            "url": url,
            "json": build_fake_bluesky_public_appview_feed_response_r43w(actor=actor, limit=3),
        }

    return fetcher


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return ()


def _safe_actor(value: Any) -> str:
    raw = _clean(value)
    raw = raw.removeprefix("@")
    raw = raw.replace("https://bsky.app/profile/", "")
    raw = raw.split("/", 1)[0]
    return re.sub(r"[^A-Za-z0-9._:-]+", "_", raw).strip("._-") or R43X_DEFAULT_ACTOR


def _safe_handle(value: Any) -> str:
    return _safe_actor(value)


def _safe_ts(value: Any) -> str:
    raw = _clean(value)
    return raw if re.fullmatch(r"\d{8}T\d{6}Z", raw) else ""


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    return _clean(value).lower() in {"1", "true", "yes", "y", "on"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _plain_url(value: Any) -> str:
    raw = _clean(value)
    match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", raw)
    if match:
        return match.group(2)
    return raw


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _check(name: str, passed: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if passed else "fail", "detail": detail}


def _machine_urls_are_plain(value: Any) -> bool:
    if isinstance(value, str):
        return "](" not in value and not value.startswith("[http")
    if isinstance(value, Mapping):
        return all(_machine_urls_are_plain(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(_machine_urls_are_plain(v) for v in value)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the R43X Bluesky real public appview smoke harness.")
    parser.add_argument("--actor", default=R43X_DEFAULT_ACTOR)
    parser.add_argument("--account-url", default="")
    parser.add_argument("--account-handle", default="")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--output-root", default=R43X_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--max-items", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--public-network-enabled", action="store_true")
    parser.add_argument("--explicit-live-mode", action="store_true")
    parser.add_argument("--live-mode", action="store_true")
    parser.add_argument("--include-static-screenshots", action="store_true")
    parser.add_argument("--require-screenshot-receipts", action="store_true")
    parser.add_argument("--feed-filter", default="posts_and_author_threads")
    parser.add_argument("--no-include-pins", action="store_true")
    args = parser.parse_args(argv)

    if args.public_network_enabled or args.explicit_live_mode or args.live_mode:
        result = run_bluesky_real_public_appview_smoke_r43x(
            BlueskyRealPublicAppviewSmokeRequestR43X(
                actor=args.actor,
                account_url=args.account_url,
                account_handle=args.account_handle or args.actor,
                capture_timestamp=args.capture_timestamp,
                output_root=args.output_root,
                max_items=args.max_items,
                timeout_seconds=args.timeout_seconds,
                include_static_screenshots=args.include_static_screenshots,
                require_screenshot_receipts=args.require_screenshot_receipts,
                public_network_enabled=args.public_network_enabled,
                explicit_live_mode=args.explicit_live_mode,
                live_mode=args.live_mode,
                feed_filter=args.feed_filter,
                include_pins=not args.no_include_pins,
            )
        )
        print(R43X_MARKER)
        print(result.status)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.passed else 1

    report = build_report(args.output_root)
    print(R43X_MARKER)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
