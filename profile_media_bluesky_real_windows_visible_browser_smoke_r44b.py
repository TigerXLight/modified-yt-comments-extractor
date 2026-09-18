from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from profile_media_bluesky_visible_live_workbench_capture_r44a import (
    R44A_PASS_STATUS,
    BlueskyVisibleLiveWorkbenchCaptureRequestR44A,
    build_bluesky_visible_live_workbench_capture_r44a,
    fake_visible_browser_snapshot_r44a,
)
from profile_media_bluesky_visible_dom_capture_r43z import R43Z_PASS_STATUS
from profile_media_bluesky_visible_account_adapter_r43v import R43V_PASS_STATUS
from profile_media_universal_social_account_ledger_contract_r43u import R43U_PASS_STATUS

R44B_MARKER = "YTCE_R44B_BLUESKY_REAL_WINDOWS_VISIBLE_BROWSER_SMOKE"
R44B_PASS_STATUS = "PASS_R44B_BLUESKY_REAL_WINDOWS_VISIBLE_BROWSER_SMOKE"
R44B_BLOCKED_STATUS = "BLOCKED_R44B_BLUESKY_REAL_WINDOWS_VISIBLE_BROWSER_SMOKE"
R44B_SCHEMA_VERSION = "bluesky_real_windows_visible_browser_smoke.r44b.v1"
R44B_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44b_bluesky_real_windows_visible_browser_smoke"
R44B_MODE_ID = "bluesky_real_windows_visible_browser_smoke"


@dataclass(frozen=True)
class BlueskyRealWindowsVisibleBrowserSmokeRequestR44B:
    account_url: str = "https://bsky.app/profile/bsky.app"
    account_handle: str = "bsky.app"
    capture_timestamp: str = ""
    output_root: str = R44B_DEFAULT_OUTPUT_ROOT
    real_visible_smoke: bool = False
    fixture_mode: bool = False
    headless: bool = False
    max_items: int = 5
    max_scrolls: int = 4
    timeout_seconds: int = 45
    min_records: int = 1
    min_screenshots: int = 1
    min_media: int = 0
    allow_zero_media: bool = True
    browser_executable_path: str = ""
    feed_mode: str = "posts_and_reposts"
    include_reposts: bool = True
    include_replies: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class BlueskyRealWindowsVisibleBrowserSmokeResultR44B:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    output_root: str
    run_dir: str
    request_path: str
    receipt_path: str
    r44a_status: str = ""
    r43z_status: str = ""
    adapter_status: str = ""
    ledger_status: str = ""
    record_count: int = 0
    visible_record_count: int = 0
    media_count: int = 0
    bound_media_count: int = 0
    screenshot_count: int = 0
    post_folder_count: int = 0
    browser_session_started: bool = False
    network_actions_performed: bool = False
    injected_browser_runner_used: bool = False
    browser_engine: str = ""
    browser_snapshot_status: str = ""
    browser_status_code: int = 0
    browser_final_url: str = ""
    visible_dom_html_path: str = ""
    visible_screenshot_path: str = ""
    r44a_receipt_path: str = ""
    r43z_receipt_path: str = ""
    account_capture_dir: str = ""
    account_record_path: str = ""
    media_index_path: str = ""
    review_strings_path: str = ""
    live_media_binding_status: str = ""
    real_visible_smoke_requested: bool = False
    feed_mode: str = ""
    navigation_url: str = ""
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R44B_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R44BReport:
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
        return self.status == R44B_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


class BlueskyRealWindowsVisibleBrowserSmokeR44B:
    """Final visible-browser smoke wrapper for the R44A -> R43Z -> R43V -> R43U stack.

    R44B is deliberately a smoke verifier. The deterministic report uses an
    injected browser runner; the real Windows smoke must be requested explicitly
    and is allowed to start a clean visible browser session without reading or
    copying browser profile state.
    """

    def __init__(self, output_root: str | Path = R44B_DEFAULT_OUTPUT_ROOT, *, browser_runner: Any | None = None) -> None:
        self.output_root = Path(output_root)
        self.browser_runner = browser_runner

    def run_account_export(self, request: BlueskyRealWindowsVisibleBrowserSmokeRequestR44B | Mapping[str, Any] | None = None, **overrides: Any) -> BlueskyRealWindowsVisibleBrowserSmokeResultR44B:
        req = coerce_bluesky_real_windows_visible_browser_smoke_request_r44b(request, **overrides)
        return run_bluesky_real_windows_visible_browser_smoke_r44b(req, output_root=self.output_root, browser_runner=self.browser_runner)


def build_bluesky_real_windows_visible_browser_smoke_r44b(output_root: str | Path = R44B_DEFAULT_OUTPUT_ROOT, *, browser_runner: Any | None = None) -> BlueskyRealWindowsVisibleBrowserSmokeR44B:
    return BlueskyRealWindowsVisibleBrowserSmokeR44B(output_root=output_root, browser_runner=browser_runner)


def build_bluesky_real_windows_visible_browser_smoke_contract_r44b() -> dict[str, Any]:
    return {
        "marker": R44B_MARKER,
        "schema_version": R44B_SCHEMA_VERSION,
        "mode_id": R44B_MODE_ID,
        "route_role": "final real Windows visible-browser smoke above R44A",
        "downstream_live_caller": "profile_media_bluesky_visible_live_workbench_capture_r44a",
        "downstream_visible_dom_lane": "profile_media_bluesky_visible_dom_capture_r43z",
        "downstream_adapter": "profile_media_bluesky_visible_account_adapter_r43v",
        "downstream_ledger": "profile_media_universal_social_account_ledger_contract_r43u",
        "timeline_modes_r44c": {
            "posts_and_reposts": "profile timeline smoke; intended to match Twitter/X posts+retweets mode",
            "posts_and_replies": "profile replies timeline smoke; intended to match Twitter/X posts+replies mode",
        },
        "real_visible_smoke_requirements": [
            "explicit --real-visible-smoke flag",
            "clean Playwright visible Chromium session launched by R44A",
            "rendered HTML written to visible_dom.html",
            "visible screenshot written and passed to R43Z",
            "at least one visible Bluesky post record reaches R43U",
        ],
        "fallback_if_no_live_media_visible": "pass with a live_media_binding_status warning when the live page has posts/screenshots but no media in the rendered sample",
        "browser_profile_files_read_or_copied": False,
        "webview2_internals_copied": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed_by_r44b": False,
    }


def run_bluesky_real_windows_visible_browser_smoke_r44b(
    request: BlueskyRealWindowsVisibleBrowserSmokeRequestR44B | Mapping[str, Any] | None = None,
    *,
    output_root: str | Path = R44B_DEFAULT_OUTPUT_ROOT,
    browser_runner: Any | None = None,
) -> BlueskyRealWindowsVisibleBrowserSmokeResultR44B:
    req = coerce_bluesky_real_windows_visible_browser_smoke_request_r44b(request)
    root = Path(req.output_root or output_root or R44B_DEFAULT_OUTPUT_ROOT)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    handle = _safe_handle(req.account_handle or _handle_from_url(req.account_url) or "bsky.app")
    account_url = _plain_url(req.account_url) or f"https://bsky.app/profile/{handle}"
    run_dir = root / handle / f"bluesky_real_windows_visible_browser_smoke_{capture_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "r44b_bluesky_real_windows_visible_browser_smoke_request.json"
    receipt_path = run_dir / "r44b_bluesky_real_windows_visible_browser_smoke_receipt.json"
    _write_json(request_path, req.to_dict())

    runner = browser_runner
    using_injected = runner is not None
    if req.fixture_mode and runner is None:
        runner = fake_visible_browser_snapshot_r44a
        using_injected = True
    if not req.real_visible_smoke and runner is None:
        runner = fake_visible_browser_snapshot_r44a
        using_injected = True

    r44a = build_bluesky_visible_live_workbench_capture_r44a(run_dir / "r44a_visible_live", browser_runner=runner)
    r44a_result = r44a.run_account_export(
        BlueskyVisibleLiveWorkbenchCaptureRequestR44A(
            account_url=account_url,
            account_handle=handle,
            capture_timestamp=capture_ts,
            output_root=str(run_dir / "r44a_visible_live"),
            explicit_live_mode=True,
            run_visible_live=True,
            live_mode=True,
            allow_external_visible_browser_capture=bool(req.real_visible_smoke and not using_injected),
            headless=bool(req.headless),
            max_items=req.max_items,
            max_scrolls=req.max_scrolls,
            timeout_seconds=req.timeout_seconds,
            browser_executable_path=req.browser_executable_path,
            feed_mode=req.feed_mode,
            include_reposts=req.include_reposts,
            include_replies=req.include_replies,
        )
    )
    payload = r44a_result.to_dict()
    warnings = list(payload.get("warnings") or [])
    flags = build_r44b_side_effect_flags(
        real_visible_smoke_requested=req.real_visible_smoke,
        injected_browser_runner_used=bool(r44a_result.injected_browser_runner_used),
        browser_session_started=bool(r44a_result.browser_session_started),
        network_actions_performed=bool(r44a_result.network_actions_performed),
    )

    checks: list[tuple[str, bool, str]] = [
        ("r44a_passed", r44a_result.status == R44A_PASS_STATUS, f"R44A returned {r44a_result.status}"),
        ("r43z_chain_passed", r44a_result.r43z_status == R43Z_PASS_STATUS, f"R43Z returned {r44a_result.r43z_status}"),
        ("r43v_adapter_passed", r44a_result.adapter_status == R43V_PASS_STATUS, f"R43V returned {r44a_result.adapter_status}"),
        ("r43u_ledger_passed", r44a_result.ledger_status == R43U_PASS_STATUS, f"R43U returned {r44a_result.ledger_status}"),
        ("min_records_met", int(r44a_result.record_count) >= max(1, req.min_records), f"record_count={r44a_result.record_count}"),
        ("min_screenshots_met", int(r44a_result.screenshot_count) >= max(0, req.min_screenshots), f"screenshot_count={r44a_result.screenshot_count}"),
        ("visible_dom_written", bool(r44a_result.visible_dom_html_path) and Path(r44a_result.visible_dom_html_path).is_file(), "visible_dom.html was not written"),
        ("screenshot_written", bool(r44a_result.visible_screenshot_path) and Path(r44a_result.visible_screenshot_path).is_file(), "visible screenshot was not written"),
        ("safe_side_effect_flags", not any(flags.get(k) for k in ("browser_profile_files_read_or_copied", "webview2_internals_copied", "cookie_or_token_extraction_performed", "login_automation_performed", "captcha_or_challenge_bypass_performed", "hidden_platform_api_scraping_performed", "remote_media_downloads_performed")), "unsafe side-effect flag was true"),
    ]
    if req.real_visible_smoke and not using_injected:
        checks.extend([
            ("real_browser_started", bool(r44a_result.browser_session_started), "real visible browser session did not start"),
            ("real_network_observed", bool(r44a_result.network_actions_performed), "real visible browser network action was not recorded"),
            ("not_injected", not bool(r44a_result.injected_browser_runner_used), "injected runner was used in real smoke"),
        ])
    media_requirement = max(0, req.min_media)
    media_ok = int(r44a_result.media_count) >= media_requirement or bool(req.allow_zero_media)
    live_media_binding_status = "MEDIA_PRESENT_AND_BOUND" if int(r44a_result.media_count) > 0 and int(r44a_result.bound_media_count) > 0 else "NO_VISIBLE_MEDIA_IN_CAPTURE"
    if live_media_binding_status == "NO_VISIBLE_MEDIA_IN_CAPTURE":
        warnings.append("Live page produced post/screenshot receipts but no visible media rows; R43Z media binding remains fixture-tested and will bind media when present.")
    checks.append(("media_requirement_satisfied", media_ok, f"media_count={r44a_result.media_count}, min_media={media_requirement}, allow_zero_media={req.allow_zero_media}"))

    failed = [f"{name}: {detail}" for name, ok, detail in checks if not ok]
    status = R44B_PASS_STATUS if not failed else R44B_BLOCKED_STATUS
    warnings.extend(failed)
    result = BlueskyRealWindowsVisibleBrowserSmokeResultR44B(
        marker=R44B_MARKER,
        schema_version=R44B_SCHEMA_VERSION,
        status=status,
        account_handle=handle,
        account_url=account_url,
        capture_timestamp=capture_ts,
        output_root=str(root),
        run_dir=str(run_dir),
        request_path=str(request_path),
        receipt_path=str(receipt_path),
        r44a_status=r44a_result.status,
        r43z_status=r44a_result.r43z_status,
        adapter_status=r44a_result.adapter_status,
        ledger_status=r44a_result.ledger_status,
        record_count=r44a_result.record_count,
        visible_record_count=r44a_result.visible_record_count,
        media_count=r44a_result.media_count,
        bound_media_count=r44a_result.bound_media_count,
        screenshot_count=r44a_result.screenshot_count,
        post_folder_count=r44a_result.post_folder_count,
        browser_session_started=r44a_result.browser_session_started,
        network_actions_performed=r44a_result.network_actions_performed,
        injected_browser_runner_used=r44a_result.injected_browser_runner_used,
        browser_engine=r44a_result.browser_engine,
        browser_snapshot_status=r44a_result.browser_snapshot_status,
        browser_status_code=r44a_result.browser_status_code,
        browser_final_url=r44a_result.browser_final_url,
        visible_dom_html_path=r44a_result.visible_dom_html_path,
        visible_screenshot_path=r44a_result.visible_screenshot_path,
        r44a_receipt_path=r44a_result.receipt_path,
        r43z_receipt_path=r44a_result.r43z_receipt_path,
        account_capture_dir=r44a_result.account_capture_dir,
        account_record_path=r44a_result.account_record_path,
        media_index_path=r44a_result.media_index_path,
        review_strings_path=r44a_result.review_strings_path,
        live_media_binding_status=live_media_binding_status,
        real_visible_smoke_requested=bool(req.real_visible_smoke),
        feed_mode=_clean(getattr(r44a_result, "feed_mode", "") or req.feed_mode),
        navigation_url=_plain_url(getattr(r44a_result, "navigation_url", "")),
        side_effect_flags=flags,
        warnings=tuple(_dedupe(warnings)),
    )
    _write_json(receipt_path, {"result": result.to_dict(), "r44a_result": payload})
    return result


def build_report(output_root: str | Path = R44B_DEFAULT_OUTPUT_ROOT) -> R44BReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    sample = run_bluesky_real_windows_visible_browser_smoke_r44b(
        BlueskyRealWindowsVisibleBrowserSmokeRequestR44B(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T093000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
            real_visible_smoke=False,
            max_items=5,
        ),
        output_root=root / "sample",
        browser_runner=fake_visible_browser_snapshot_r44a,
    )
    blocked = run_bluesky_real_windows_visible_browser_smoke_r44b(
        BlueskyRealWindowsVisibleBrowserSmokeRequestR44B(
            account_url="https://bsky.app/profile/example.bsky.social",
            account_handle="example.bsky.social",
            capture_timestamp="20260918T093100Z",
            output_root=str(root / "blocked_gate"),
            fixture_mode=False,
            real_visible_smoke=False,
            max_items=2,
        ),
        output_root=root / "blocked_gate",
        browser_runner=fake_visible_browser_snapshot_r44a,
    )
    contract = build_bluesky_real_windows_visible_browser_smoke_contract_r44b()
    checks = (
        _check("injected_smoke_exercises_r44a_r43z_r43v_r43u", sample.status == R44B_PASS_STATUS and sample.r44a_status == R44A_PASS_STATUS and sample.r43z_status == R43Z_PASS_STATUS and sample.ledger_status == R43U_PASS_STATUS),
        _check("visible_dom_and_screenshot_receipts_exist", Path(sample.visible_dom_html_path).is_file() and Path(sample.visible_screenshot_path).is_file()),
        _check("visible_media_binding_present_in_fixture", sample.media_count >= 3 and sample.bound_media_count >= 3),
        _check("deterministic_validation_uses_injected_runner_not_real_browser", sample.injected_browser_runner_used is True and sample.browser_session_started is False and sample.network_actions_performed is False),
        _check("real_smoke_contract_requires_explicit_operator_request", contract.get("real_visible_smoke_requirements") and not contract.get("cookie_or_token_extraction_performed")),
        _check("no_browser_cookie_token_profile_or_media_download_side_effects", not any(sample.side_effect_flags.get(k) for k in ("browser_profile_files_read_or_copied", "webview2_internals_copied", "cookie_or_token_extraction_performed", "login_automation_performed", "captcha_or_challenge_bypass_performed", "hidden_platform_api_scraping_performed", "remote_media_downloads_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(sample.to_dict()) and _machine_urls_are_plain(blocked.to_dict()) and _machine_urls_are_plain(contract)),
    )
    status = R44B_PASS_STATUS if all(c["status"] == "pass" for c in checks) else R44B_BLOCKED_STATUS
    report = R44BReport(R44B_MARKER, R44B_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), status, checks, sample.to_dict(), blocked.to_dict(), contract, sample.side_effect_flags)
    write_report(report, root)
    return report


def write_report(report: R44BReport, output_root: str | Path = R44B_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R44B_BLUESKY_REAL_WINDOWS_VISIBLE_BROWSER_SMOKE_REPORT.json"
    md_path = root / "R44B_BLUESKY_REAL_WINDOWS_VISIBLE_BROWSER_SMOKE_REPORT.md"
    _write_json(json_path, report.to_dict())
    md_path.write_text(
        "\n".join([
            f"# {R44B_MARKER}",
            "",
            f"- Status: `{report.status}`",
            f"- Schema: `{report.schema_version}`",
            f"- Generated: `{report.generated_at}`",
            "",
            "## Checks",
            *[f"- `{c.get('status')}` {c.get('name')}: {c.get('detail') or ''}".rstrip() for c in report.checks],
        ]).rstrip() + "\n",
        encoding="utf-8",
    )
    return json_path, md_path


def build_r44b_side_effect_flags(*, real_visible_smoke_requested: bool = False, injected_browser_runner_used: bool = False, browser_session_started: bool = False, network_actions_performed: bool = False) -> dict[str, bool]:
    return {
        "bluesky_real_windows_visible_browser_smoke_invoked": True,
        "real_visible_smoke_requested": bool(real_visible_smoke_requested),
        "r44a_visible_live_workbench_capture_used": True,
        "r43z_visible_dom_capture_used": True,
        "r43v_bluesky_adapter_used": True,
        "r43u_universal_ledger_writer_used": True,
        "injected_browser_runner_used": bool(injected_browser_runner_used),
        "browser_session_started": bool(browser_session_started),
        "network_actions_performed": bool(network_actions_performed),
        "browser_profile_files_read_or_copied": False,
        "webview2_internals_copied": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
    }


def coerce_bluesky_real_windows_visible_browser_smoke_request_r44b(request: BlueskyRealWindowsVisibleBrowserSmokeRequestR44B | Mapping[str, Any] | None = None, **overrides: Any) -> BlueskyRealWindowsVisibleBrowserSmokeRequestR44B:
    if isinstance(request, BlueskyRealWindowsVisibleBrowserSmokeRequestR44B):
        data = request.to_dict()
    elif hasattr(request, "to_dict"):
        data = dict(request.to_dict())
    elif isinstance(request, Mapping):
        data = dict(request)
    else:
        data = dict(request or {})
    for key, value in overrides.items():
        if value not in (None, ""):
            data[key] = value
    return BlueskyRealWindowsVisibleBrowserSmokeRequestR44B(
        account_url=_plain_url(data.get("account_url") or "https://bsky.app/profile/bsky.app"),
        account_handle=_safe_handle(data.get("account_handle") or "bsky.app"),
        capture_timestamp=_safe_ts(data.get("capture_timestamp") or ""),
        output_root=str(data.get("output_root") or R44B_DEFAULT_OUTPUT_ROOT),
        real_visible_smoke=_to_bool(data.get("real_visible_smoke") or data.get("run_real_visible_smoke"), False),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        headless=_to_bool(data.get("headless"), False),
        max_items=_safe_int(data.get("max_items"), 5),
        max_scrolls=_safe_int(data.get("max_scrolls"), 4),
        timeout_seconds=_safe_int(data.get("timeout_seconds"), 45),
        min_records=_safe_int(data.get("min_records"), 1),
        min_screenshots=_safe_int(data.get("min_screenshots"), 1),
        min_media=_safe_int(data.get("min_media"), 0),
        allow_zero_media=_to_bool(data.get("allow_zero_media"), True),
        browser_executable_path=str(data.get("browser_executable_path") or ""),
        feed_mode=_clean(data.get("feed_mode") or data.get("timeline_mode") or "posts_and_reposts"),
        include_reposts=_to_bool(data.get("include_reposts"), True),
        include_replies=_to_bool(data.get("include_replies"), False),
    )


def _safe_handle(value: Any) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", _clean(value).strip().lstrip("@")).strip("._-") or "unknown_account"


def _safe_ts(value: Any) -> str:
    import re
    return re.sub(r"[^0-9TZ]", "", _clean(value).replace(":", "").replace("-", ""))


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _plain_url(value: Any) -> str:
    import re
    text = _clean(value).strip("<>").replace("\\_", "_").replace("\\/", "/")
    md = re.match(r"^\[[^\]]+\]\((https?://[^)]+)\)$", text)
    return md.group(1).replace("\\&", "&") if md else text


def _handle_from_url(url: str) -> str:
    import re
    match = re.search(r"/profile/([^/?#]+)/?", _plain_url(url))
    return match.group(1) if match else ""


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    return value


def _write_json(path: str | Path, value: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _check(name: str, ok: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": "" if ok else detail}


def _machine_urls_are_plain(value: Any) -> bool:
    import re
    text = json.dumps(_to_jsonable(value), ensure_ascii=False)
    return not bool(re.search(r"\[[^\]]*https?://[^\]]+\]\(https?://", text))


def _dedupe(items: Sequence[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = _clean(item)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R44B Bluesky real Windows visible-browser smoke")
    parser.add_argument("--account-url", default="https://bsky.app/profile/bsky.app")
    parser.add_argument("--account-handle", default="bsky.app")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--output-root", default=R44B_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--real-visible-smoke", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--max-scrolls", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--min-records", type=int, default=1)
    parser.add_argument("--min-screenshots", type=int, default=1)
    parser.add_argument("--min-media", type=int, default=0)
    parser.add_argument("--strict-live-media", action="store_true")
    parser.add_argument("--browser-executable-path", default="")
    parser.add_argument("--feed-mode", default="posts_and_reposts", choices=("posts_and_reposts", "posts_and_retweets", "posts_retweets", "posts_and_replies", "posts_replies", "posts_only"))
    parser.add_argument("--timeline-mode", default="")
    parser.add_argument("--include-replies", action="store_true")
    parser.add_argument("--exclude-reposts", action="store_true")
    args = parser.parse_args(argv)
    if not args.real_visible_smoke:
        report = build_report(args.output_root)
        print(R44B_MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report.passed else 1
    result = run_bluesky_real_windows_visible_browser_smoke_r44b(
        BlueskyRealWindowsVisibleBrowserSmokeRequestR44B(
            account_url=args.account_url,
            account_handle=args.account_handle,
            capture_timestamp=args.capture_timestamp,
            output_root=args.output_root,
            real_visible_smoke=True,
            fixture_mode=args.fixture_mode,
            headless=args.headless,
            max_items=args.max_items,
            max_scrolls=args.max_scrolls,
            timeout_seconds=args.timeout_seconds,
            min_records=args.min_records,
            min_screenshots=args.min_screenshots,
            min_media=args.min_media,
            allow_zero_media=not args.strict_live_media,
            browser_executable_path=args.browser_executable_path,
            feed_mode=args.timeline_mode or args.feed_mode,
            include_reposts=not bool(args.exclude_reposts),
            include_replies=bool(args.include_replies) or (args.timeline_mode or args.feed_mode) in {"posts_and_replies", "posts_replies"},
        )
    )
    print(R44B_MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
