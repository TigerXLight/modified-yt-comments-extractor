from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_twitter_x_account_media_ledger_r43a import (
    TwitterXAccountMediaItemR43A,
    TwitterXAccountRecordR43A,
)

R43D_MARKER = "YTCE_R43D_TWITTER_X_ACCOUNT_TRACKING_EXPORT_SURFACE"
R43D_PASS_STATUS = "PASS_R43D_TWITTER_X_ACCOUNT_TRACKING_EXPORT_SURFACE"
R43D_BLOCKED_STATUS = "BLOCKED_R43D_TWITTER_X_ACCOUNT_TRACKING_EXPORT_SURFACE"
R43D_SCHEMA_VERSION = "twitter_x_account_tracking_export_surface.r43d.v1"
R43D_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43d_twitter_x_account_tracking_export_surface"
R43D_MODE_ID = "twitter_x_account_tracking_export_surface"


@dataclass(frozen=True)
class TwitterXAccountTrackingExportRequestR43D:
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
    output_root: str = R43D_DEFAULT_OUTPUT_ROOT
    date_folder_rule: str = "visible post date first; fallback capture date; unknown_date if ambiguous"
    folder_contract: str = "account_record.md links date folders; each post/repost folder links static screenshot receipt and media folders"
    fixture_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class TwitterXAccountTrackingExportSurfaceResultR43D:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    surface_run_dir: str
    request_path: str
    runbook_path: str
    surface_receipt_path: str
    timeline_runner_receipt_path: str
    timeline_records_path: str
    progress_events_path: str
    account_capture_dir: str
    account_record_path: str
    manifest_path: str
    media_index_path: str
    screenshot_receipts_index_path: str
    record_count: int
    post_count: int
    repost_count: int
    media_count: int
    screenshot_count: int
    date_folders: tuple[str, ...]
    side_effect_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43D_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43DReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    surface_result: Mapping[str, Any]
    surface_contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43D_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
            "surface_contract": _to_jsonable(self.surface_contract),
            "surface_result": _to_jsonable(self.surface_result),
        }


class TwitterXAccountTrackingExportSurfaceR43D:
    """User-facing Twitter/X account media tracking export surface.

    R43D is the launch/export surface above R43B/R43A/R43C.  It turns a whole
    account URL or handle into a concrete local export job, records the selected
    posts/reposts/media/screenshot options, writes a local runbook, and then
    invokes the timeline runner.  It deliberately keeps tracking, dedupe, folder
    routing, screenshot receipt status, and ledger writing outside WebView2.

    WebView2 remains an optional observation engine below the runner.  This
    surface does not copy WebView2 internals, does not require the review/source-
    role WebView2 lane, and does not perform source-role checks.
    """

    def __init__(
        self,
        *,
        timeline_runner: Any | None = None,
        screenshot_gate: Any | None = None,
        output_root: str | Path = R43D_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.timeline_runner = timeline_runner
        self.screenshot_gate = screenshot_gate
        self.output_root = Path(output_root)

    def run_account_export(
        self,
        request: TwitterXAccountTrackingExportRequestR43D | Mapping[str, Any] | None = None,
        *,
        account_url: str = "",
        account_handle: str = "",
        capture_timestamp: str = "",
        initial_records: Iterable[Mapping[str, Any] | TwitterXAccountRecordR43A] | None = None,
    ) -> TwitterXAccountTrackingExportSurfaceResultR43D:
        req = coerce_account_tracking_export_request_r43d(
            request,
            account_url=account_url,
            account_handle=account_handle,
            capture_timestamp=capture_timestamp,
            output_root=str(self.output_root),
        )
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        handle = _safe_handle(req.account_handle or _handle_from_url(req.account_url) or "unknown_account")
        account_url_plain = _plain_url(req.account_url or f"https://x.com/{handle}")
        surface_run_dir = Path(req.output_root or self.output_root) / handle / f"account_tracking_export_{capture_ts}"
        surface_run_dir.mkdir(parents=True, exist_ok=True)

        request_path = surface_run_dir / "account_tracking_request.json"
        runbook_path = surface_run_dir / "account_tracking_runbook.md"
        receipt_path = surface_run_dir / "account_tracking_surface_receipt.json"

        _write_json(request_path, {**req.to_dict(), "account_handle": handle, "account_url": account_url_plain, "marker": R43D_MARKER})

        records = list(initial_records or ())
        if not records and req.fixture_mode:
            records = build_fixture_account_records_r43d(surface_run_dir, account_handle=handle, capture_timestamp=capture_ts)

        runner = self.timeline_runner
        if runner is None:
            from profile_media_twitter_x_account_media_ledger_r43a import build_twitter_x_account_media_ledger_exporter_r43a
            from profile_media_twitter_x_account_timeline_runner_r43b import (
                TwitterXAccountTimelineRunnerConfigR43B,
                build_twitter_x_account_timeline_runner_r43b,
            )

            ledger_root = surface_run_dir / "source_exports" / "twitter_x"
            runner = build_twitter_x_account_timeline_runner_r43b(
                ledger_exporter=build_twitter_x_account_media_ledger_exporter_r43a(ledger_root),
                config=TwitterXAccountTimelineRunnerConfigR43B(
                    output_root=str(surface_run_dir / "timeline_runner"),
                    ledger_output_root=str(ledger_root),
                    include_posts=req.include_posts,
                    include_reposts=req.include_reposts,
                    include_quote_posts=req.include_quote_posts,
                    include_replies=req.include_replies,
                    include_static_screenshots=req.include_static_screenshots,
                    media_folder_links_required=req.include_media,
                    fixture_mode=req.fixture_mode,
                ),
            )

        timeline_result = runner.run(
            account_handle=handle,
            account_url=account_url_plain,
            capture_timestamp=capture_ts,
            initial_records=records,
        )
        timeline_payload = _result_dict(timeline_result)
        account_capture_dir = Path(_clean(timeline_payload.get("account_capture_dir")))
        screenshot_index = account_capture_dir / "screenshot_receipts_index.json" if str(account_capture_dir) else Path("")
        account_record = Path(_clean(timeline_payload.get("account_record_path")))
        manifest = Path(_clean(timeline_payload.get("ledger_manifest_path") or timeline_payload.get("manifest_path")))
        media_index = Path(_clean(timeline_payload.get("media_index_path")))
        runner_receipt = Path(_clean(timeline_payload.get("runner_receipt_path")))

        warnings: list[str] = []
        if req.require_screenshot_receipts and not screenshot_index.is_file():
            warnings.append("Screenshot receipt index was not found; screenshot evidence remains gated.")
        if not account_record.is_file():
            warnings.append("Account record markdown was not written.")
        if _clean(timeline_payload.get("status")) != "PASS_R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY":
            warnings.append(f"Timeline runner status was {_clean(timeline_payload.get('status'))!r}.")

        status = R43D_PASS_STATUS if not warnings and int(timeline_payload.get("record_count") or 0) > 0 else R43D_BLOCKED_STATUS
        side_effect_flags = build_r43d_side_effect_flags()

        result = TwitterXAccountTrackingExportSurfaceResultR43D(
            marker=R43D_MARKER,
            schema_version=R43D_SCHEMA_VERSION,
            status=status,
            account_handle=handle,
            account_url=account_url_plain,
            capture_timestamp=capture_ts,
            surface_run_dir=str(surface_run_dir),
            request_path=str(request_path),
            runbook_path=str(runbook_path),
            surface_receipt_path=str(receipt_path),
            timeline_runner_receipt_path=str(runner_receipt),
            timeline_records_path=_clean(timeline_payload.get("timeline_records_path")),
            progress_events_path=_clean(timeline_payload.get("progress_events_path")),
            account_capture_dir=str(account_capture_dir),
            account_record_path=str(account_record),
            manifest_path=str(manifest),
            media_index_path=str(media_index),
            screenshot_receipts_index_path=str(screenshot_index),
            record_count=_safe_int(timeline_payload.get("record_count")),
            post_count=_safe_int(timeline_payload.get("post_count")),
            repost_count=_safe_int(timeline_payload.get("repost_count")),
            media_count=_safe_int(timeline_payload.get("media_count")),
            screenshot_count=_safe_int(timeline_payload.get("screenshot_count")),
            date_folders=tuple(str(x) for x in timeline_payload.get("date_folders") or ()),
            side_effect_flags=side_effect_flags,
            warnings=tuple(warnings),
        )
        _write_runbook(runbook_path, request=req, result=result)
        _write_json(
            receipt_path,
            {
                **result.to_dict(),
                "request": req.to_dict(),
                "timeline_result": _to_jsonable(timeline_payload),
                "surface_contract": build_twitter_x_account_tracking_export_surface_contract_r43d(req),
            },
        )
        return result


def build_twitter_x_account_tracking_export_surface_r43d(
    *,
    timeline_runner: Any | None = None,
    screenshot_gate: Any | None = None,
    output_root: str | Path = R43D_DEFAULT_OUTPUT_ROOT,
) -> TwitterXAccountTrackingExportSurfaceR43D:
    return TwitterXAccountTrackingExportSurfaceR43D(
        timeline_runner=timeline_runner,
        screenshot_gate=screenshot_gate,
        output_root=output_root,
    )


def coerce_account_tracking_export_request_r43d(
    request: TwitterXAccountTrackingExportRequestR43D | Mapping[str, Any] | None = None,
    *,
    account_url: str = "",
    account_handle: str = "",
    capture_timestamp: str = "",
    output_root: str = R43D_DEFAULT_OUTPUT_ROOT,
) -> TwitterXAccountTrackingExportRequestR43D:
    if isinstance(request, TwitterXAccountTrackingExportRequestR43D):
        data = request.to_dict()
    elif isinstance(request, Mapping):
        data = dict(request)
    else:
        data = {}
    if account_url:
        data["account_url"] = account_url
    if account_handle:
        data["account_handle"] = account_handle
    if capture_timestamp:
        data["capture_timestamp"] = capture_timestamp
    if not data.get("output_root"):
        data["output_root"] = output_root
    allowed = {field.name for field in TwitterXAccountTrackingExportRequestR43D.__dataclass_fields__.values()}
    return TwitterXAccountTrackingExportRequestR43D(**{k: v for k, v in data.items() if k in allowed})


def build_twitter_x_account_tracking_export_surface_contract_r43d(
    request: TwitterXAccountTrackingExportRequestR43D | None = None,
) -> dict[str, Any]:
    req = request or TwitterXAccountTrackingExportRequestR43D()
    return {
        "marker": R43D_MARKER,
        "schema_version": R43D_SCHEMA_VERSION,
        "mode_id": R43D_MODE_ID,
        "scope": "whole_twitter_x_account_posts_reposts_quotes_media_screenshots",
        "entry_inputs": ["account_url", "account_handle", "posts", "reposts", "quotes", "replies optional"],
        "export_outputs": [
            "account_tracking_request.json",
            "account_tracking_runbook.md",
            "account_tracking_surface_receipt.json",
            "R43B timeline runner outputs",
            "R43A account_record.md/date folders/media index",
            "R43C screenshot receipt index",
        ],
        "document_contract": "single account_record.md links date folders, post/repost folders, static screenshot receipts, and media folders",
        "date_folder_rule": req.date_folder_rule,
        "post_folder_rule": "post_<post_id> or repost_<repost_id>__original_<original_post_id>",
        "static_screenshot_receipt_required": bool(req.require_screenshot_receipts),
        "webview2_role": "site rendering and observation only; account tracking/dedupe/ledger/export live in local Python/app layer",
        "webview2_internals_copied": False,
        "edge_or_webview2_install_assumption": "R43D is a local export surface and does not itself start or require a WebView2 session",
        "independent_fast_media_lane": True,
        "review_window_dependency": False,
        "source_role_interface_dependency": False,
        "source_role_checks_enabled": False,
        "review_back_and_forth_enabled": False,
        "hidden_x_api_scraping_enabled": False,
        "remote_media_downloads_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "challenge_bypass_enabled": False,
    }


def build_r43d_side_effect_flags() -> dict[str, bool]:
    return {
        "twitter_x_account_tracking_export_surface_invoked": True,
        "timeline_runner_invoked": True,
        "account_ledger_export_invoked": True,
        "screenshot_receipt_gate_required": True,
        "local_tracking_dedupe_ledger_layer": True,
        "webview2_session_started_by_r43d": False,
        "webview2_internals_copied": False,
        "remote_media_downloads_performed": False,
        "hidden_x_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "source_role_checks_performed": False,
        "source_role_assignment_performed": False,
        "source_role_interface_loop_invoked": False,
        "review_window_dependency_invoked": False,
        "review_window_rewrite_performed": False,
        "youtube_capture_engine_changed": False,
    }


def build_fixture_account_records_r43d(
    fixture_root: str | Path,
    *,
    account_handle: str = "example",
    capture_timestamp: str = "20260915T030000Z",
) -> list[TwitterXAccountRecordR43A]:
    root = Path(fixture_root) / "_fixture_bytes"
    image = root / "images" / "r43d_image.jpg"
    video = root / "videos" / "r43d_video.mp4"
    screenshot1 = root / "screenshots" / "post_4444444444444444444.png"
    screenshot2 = root / "screenshots" / "repost_5555555555555555555.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    video.parent.mkdir(parents=True, exist_ok=True)
    screenshot1.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"R43D fixture image bytes\n")
    video.write_bytes(b"R43D fixture video bytes\n")
    screenshot1.write_bytes(_minimal_png_bytes())
    screenshot2.write_bytes(_minimal_png_bytes())
    return [
        TwitterXAccountRecordR43A(
            record_id="4444444444444444444",
            record_type="post",
            source_url=f"https://x.com/{account_handle}/status/4444444444444444444",
            visible_text="R43D fixture account post with image media.",
            visible_timestamp="2026-09-15T03:00:00Z",
            capture_timestamp=capture_timestamp,
            author_handle=account_handle,
            account_handle=account_handle,
            static_screenshot_path=str(screenshot1),
            media_items=(
                TwitterXAccountMediaItemR43A(
                    media_id="r43d_image_1",
                    media_class="image",
                    source_url=f"https://x.com/{account_handle}/status/4444444444444444444",
                    media_url="https://pbs.twimg.com/media/r43d_image.jpg",
                    local_path=str(image),
                    filename="r43d_image.jpg",
                    mime_type="image/jpeg",
                    provenance="R43D fixture local media byte",
                ),
            ),
            review_strings=("R43D account tracking export surface fixture post",),
            observed_order=1,
        ),
        TwitterXAccountRecordR43A(
            record_id="5555555555555555555",
            record_type="repost",
            source_url=f"https://x.com/{account_handle}/status/5555555555555555555",
            visible_text="R43D fixture repost with video media.",
            visible_timestamp="2026-09-15T03:05:00Z",
            capture_timestamp=capture_timestamp,
            author_handle="original_author",
            account_handle=account_handle,
            original_post_id="9999999999999999999",
            reposted_by_handle=account_handle,
            repost_context={"original_post_id": "9999999999999999999", "reposted_by_handle": account_handle},
            static_screenshot_path=str(screenshot2),
            media_items=(
                TwitterXAccountMediaItemR43A(
                    media_id="r43d_video_1",
                    media_class="video",
                    source_url=f"https://x.com/{account_handle}/status/5555555555555555555",
                    media_url="https://video.twimg.com/ext_tw_video/5555555555555555555/pu/vid/720x720/r43d_video.mp4",
                    local_path=str(video),
                    filename="r43d_video.mp4",
                    mime_type="video/mp4",
                    provenance="R43D fixture local media byte",
                ),
            ),
            review_strings=("R43D account tracking export surface fixture repost",),
            observed_order=2,
        ),
    ]


def build_report(output_root: str | Path = R43D_DEFAULT_OUTPUT_ROOT) -> R43DReport:
    root = Path(output_root)
    capture_ts = "20260915T030000Z"
    req = TwitterXAccountTrackingExportRequestR43D(
        account_url="https://x.com/example",
        account_handle="example",
        capture_timestamp=capture_ts,
        output_root=str(root),
        include_posts=True,
        include_reposts=True,
        include_quote_posts=True,
        include_replies=False,
        include_media=True,
        include_static_screenshots=True,
        require_screenshot_receipts=True,
        fixture_mode=True,
    )
    surface = build_twitter_x_account_tracking_export_surface_r43d(output_root=root)
    result = surface.run_account_export(req)
    payload = result.to_dict()
    account_record_text = _read_text(result.account_record_path)
    post_md_text = ""
    try:
        for p in Path(result.account_capture_dir).glob("dates/*/*/post.md"):
            post_md_text += "\n" + p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        post_md_text = ""
    side_effect_flags = build_r43d_side_effect_flags()
    checks = (
        _check("account_tracking_export_surface_invoked", result.passed),
        _check("request_and_runbook_written", Path(result.request_path).is_file() and Path(result.runbook_path).is_file()),
        _check("timeline_runner_invoked_and_passed", _clean(payload.get("timeline_runner_receipt_path")) and Path(result.timeline_runner_receipt_path).is_file()),
        _check("r43a_account_record_written", Path(result.account_record_path).is_file() and "Twitter/X Account Media Ledger" in account_record_text),
        _check("date_folders_and_post_repost_folders_linked", "post_4444444444444444444" in account_record_text and "repost_5555555555555555555__original_9999999999999999999" in account_record_text),
        _check("media_images_and_videos_linked", "media/images" in account_record_text and "media/videos" in account_record_text),
        _check("static_screenshot_receipts_linked", Path(result.screenshot_receipts_index_path).is_file() and "static_screenshot_receipt" in (account_record_text + post_md_text)),
        _check("tracking_logic_outside_webview2", side_effect_flags["local_tracking_dedupe_ledger_layer"] and not side_effect_flags["webview2_session_started_by_r43d"]),
        _check("no_source_role_or_review_window_side_effects", not any(side_effect_flags[name] for name in ("source_role_checks_performed", "source_role_assignment_performed", "review_window_dependency_invoked", "review_window_rewrite_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(payload) and _machine_urls_are_plain(build_twitter_x_account_tracking_export_surface_contract_r43d(req))),
    )
    status = R43D_PASS_STATUS if result.passed and all(check.get("status") == "pass" for check in checks) else R43D_BLOCKED_STATUS
    report = R43DReport(
        marker=R43D_MARKER,
        schema_version=R43D_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        surface_result=payload,
        surface_contract=build_twitter_x_account_tracking_export_surface_contract_r43d(req),
        side_effect_flags=side_effect_flags,
    )
    write_report(report, root)
    return report


def write_report(report: R43DReport, output_root: str | Path = R43D_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43D_TWITTER_X_ACCOUNT_TRACKING_EXPORT_SURFACE_REPORT.json"
    md_path = root / "R43D_TWITTER_X_ACCOUNT_TRACKING_EXPORT_SURFACE_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [
        f"# {R43D_MARKER}",
        "",
        f"- Status: `{report.status}`",
        f"- Schema: `{report.schema_version}`",
        f"- Generated: `{report.generated_at}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- `{check.get('status')}` {check.get('name')}: {check.get('detail') or ''}".rstrip())
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def _write_runbook(path: Path, *, request: TwitterXAccountTrackingExportRequestR43D, result: TwitterXAccountTrackingExportSurfaceResultR43D) -> None:
    lines = [
        f"# Twitter/X Account Tracking Export: @{result.account_handle}",
        "",
        f"- Marker: `{R43D_MARKER}`",
        f"- Status: `{result.status}`",
        f"- Account URL: `{result.account_url}`",
        f"- Capture timestamp: `{result.capture_timestamp}`",
        f"- Records: `{result.record_count}`",
        f"- Posts: `{result.post_count}`",
        f"- Reposts: `{result.repost_count}`",
        f"- Media items: `{result.media_count}`",
        f"- Screenshots: `{result.screenshot_count}`",
        "",
        "## Local outputs",
        "",
        f"- Account record: [{Path(result.account_record_path).name}]({_quote_md_path(_rel(path.parent, Path(result.account_record_path)))})",
        f"- Manifest: [{Path(result.manifest_path).name}]({_quote_md_path(_rel(path.parent, Path(result.manifest_path)))})",
        f"- Media index: [{Path(result.media_index_path).name}]({_quote_md_path(_rel(path.parent, Path(result.media_index_path)))})",
        f"- Screenshot receipts index: [{Path(result.screenshot_receipts_index_path).name}]({_quote_md_path(_rel(path.parent, Path(result.screenshot_receipts_index_path)))})",
        f"- Timeline runner receipt: [{Path(result.timeline_runner_receipt_path).name}]({_quote_md_path(_rel(path.parent, Path(result.timeline_runner_receipt_path)))})",
        "",
        "## Contract",
        "",
        "- Whole-account posts/reposts/quotes feed into the date-folder ledger.",
        "- Each post/repost folder keeps post.md, post.json, static screenshot receipt, media folders, and optional repost context.",
        "- WebView2 is only a site-rendering/observation engine below this layer.",
        "- Tracking, dedupe, ledger writing, media index, and receipt gating stay in the local app layer.",
        "- No source-role interface loop or review-window WebView2 dependency is invoked by this surface.",
        "",
        "## Selected options",
        "",
        f"- include_posts: `{request.include_posts}`",
        f"- include_reposts: `{request.include_reposts}`",
        f"- include_quote_posts: `{request.include_quote_posts}`",
        f"- include_replies: `{request.include_replies}`",
        f"- include_media: `{request.include_media}`",
        f"- require_screenshot_receipts: `{request.require_screenshot_receipts}`",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _minimal_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _result_dict(value: Any) -> dict[str, Any]:
    data = _to_jsonable(value)
    return dict(data) if isinstance(data, Mapping) else {"result": data}


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(_to_jsonable(v) for v in value)
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict"):
        return _to_jsonable(value.to_dict())
    return _clean(value)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _read_text(path: Any) -> str:
    try:
        p = Path(_clean(path))
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    except Exception:
        return ""


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_ts(value: Any) -> str:
    text = _clean(value).strip()
    return re.sub(r"[^0-9TZ_-]", "", text)[:40]


def _plain_url(value: Any) -> str:
    text = _clean(value).strip().replace("\\_", "_")
    md = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", text)
    if md:
        return md.group(2)
    text = text.strip("<>").strip()
    return text


def _handle_from_url(url: Any) -> str:
    text = _plain_url(url)
    m = re.search(r"(?:https?://)?(?:www\.)?(?:x|twitter)\.com/([^/?#]+)", text, re.I)
    return _safe_handle(m.group(1)) if m else ""


def _safe_handle(value: Any) -> str:
    text = _clean(value).strip().lstrip("@")
    text = re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_")
    return text[:80] or "unknown_account"


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _clean(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.replace("\\_", "_")
    return value


def _rel(start: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(start.resolve()).as_posix()
    except Exception:
        try:
            return Path(target).relative_to(start).as_posix()
        except Exception:
            return str(target).replace("\\", "/")


def _quote_md_path(path: Any) -> str:
    return str(path).replace("\\", "/").replace(" ", "%20")


def _scrub_markdown_machine_urls(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _scrub_markdown_machine_urls(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(_scrub_markdown_machine_urls(v) for v in value)
    if isinstance(value, list):
        return [_scrub_markdown_machine_urls(v) for v in value]
    if isinstance(value, str) and ("http://" in value or "https://" in value):
        return _plain_url(value)
    return value


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_scrub_markdown_machine_urls(_to_jsonable(value)), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=R43D_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(report.marker)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
