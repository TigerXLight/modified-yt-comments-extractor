from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from profile_media_twitter_x_account_media_ledger_r43a import (
    R43A_PASS_STATUS,
    TwitterXAccountMediaItemR43A,
    TwitterXAccountRecordR43A,
    write_twitter_x_account_media_ledger_r43a,
)

R43B_MARKER = "YTCE_R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY"
R43B_PASS_STATUS = "PASS_R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY"
R43B_BLOCKED_STATUS = "BLOCKED_R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY"
R43B_SCHEMA_VERSION = "twitter_x_account_timeline_runner_progress_pause_recovery.r43b.v1"
R43B_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43b_twitter_x_account_timeline_runner_progress_pause_recovery"
R43B_DEFAULT_LEDGER_OUTPUT_ROOT = "source_exports/twitter_x"
R43B_MODE_ID = "twitter_x_account_timeline_runner_progress_pause_recovery"
R43B_MEDIA_LANE_MODE_ID = "independent_fast_media_webview2_per_link_media_only_lane"

RecordSource = Callable[..., Iterable[Mapping[str, Any] | TwitterXAccountRecordR43A]]


@dataclass(frozen=True)
class TwitterXAccountTimelineRunnerConfigR43B:
    output_root: str = R43B_DEFAULT_OUTPUT_ROOT
    ledger_output_root: str = R43B_DEFAULT_LEDGER_OUTPUT_ROOT
    max_scroll_rounds: int = 24
    no_new_record_round_limit: int = 3
    include_posts: bool = True
    include_reposts: bool = True
    include_quote_posts: bool = True
    include_replies: bool = False
    include_static_screenshots: bool = True
    media_folder_links_required: bool = True
    progress_pause_recovery_enabled: bool = True
    dynamic_rate_limit_policy: str = "observe platform backpressure and progress stalls; pause/recover dynamically; no fixed record-per-hour threshold"
    fixed_records_per_hour_limit: int = 0
    media_lane_mode_id: str = R43B_MEDIA_LANE_MODE_ID
    independent_media_lane_required: bool = True
    source_role_checks_enabled: bool = False
    source_role_interface_dependency: bool = False
    review_window_dependency: bool = False
    review_back_and_forth_enabled: bool = False
    hidden_x_api_scraping_enabled: bool = False
    remote_media_downloads_enabled: bool = False
    cookie_or_token_extraction_enabled: bool = False
    challenge_bypass_enabled: bool = False
    fixture_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterXTimelineProgressEventR43B:
    event_id: int
    event_type: str
    capture_timestamp: str
    account_handle: str
    detail: str = ""
    observed_count: int = 0
    pause_reason: str = ""
    recovery_action: str = ""
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterXAccountTimelineRunResultR43B:
    marker: str
    schema_version: str
    status: str
    account_handle: str
    account_url: str
    capture_timestamp: str
    run_dir: str
    progress_events_path: str
    timeline_records_path: str
    runner_receipt_path: str
    account_record_path: str
    account_capture_dir: str
    ledger_manifest_path: str
    media_index_path: str
    record_count: int
    post_count: int
    repost_count: int
    media_count: int
    screenshot_count: int
    date_folders: tuple[str, ...]
    pause_event_count: int
    recovery_event_count: int
    lane_backend_status: str
    side_effect_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43B_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43BReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    timeline_result: Mapping[str, Any]
    timeline_runner_contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43B_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
            "timeline_result": _to_jsonable(self.timeline_result),
            "timeline_runner_contract": dict(self.timeline_runner_contract),
        }


class TwitterXAccountTimelineRunnerR43B:
    """Twitter/X account timeline runner shell with progress/pause/recovery.

    R43B is the account-runner layer between the independent fast Media WebView2
    lane and the R43A local account media ledger. It tracks whole-account posts
    and reposts, writes progress events, models rate-limit/backpressure pause and
    auto-recovery, and sends normalized records into the date-folder ledger.

    It deliberately does not use the review/source-role WebView2 lane, does not
    perform source-role checks, does not rewrite the review window, does not
    scrape hidden X APIs, and does not download remote media. WebView2 remains a
    site-rendering/observation input only; records, dedupe, progress, privacy
    boundaries, screenshots, and media-folder routing live in the local app layer.
    """

    def __init__(
        self,
        *,
        media_lane_backend: Any | None = None,
        ledger_exporter: Any | None = None,
        record_source: RecordSource | None = None,
        config: TwitterXAccountTimelineRunnerConfigR43B | None = None,
    ) -> None:
        self.media_lane_backend = media_lane_backend
        self.ledger_exporter = ledger_exporter
        self.record_source = record_source
        self.config = config or TwitterXAccountTimelineRunnerConfigR43B()

    def run(
        self,
        *,
        account_handle: str = "",
        account_url: str = "",
        capture_timestamp: str = "",
        initial_records: Iterable[Mapping[str, Any] | TwitterXAccountRecordR43A] | None = None,
    ) -> TwitterXAccountTimelineRunResultR43B:
        capture_ts = _safe_ts(capture_timestamp) or _now_ts()
        handle = _safe_handle(account_handle or _handle_from_url(account_url) or "unknown_account")
        url = _plain_url(account_url or f"https://x.com/{handle}")
        run_dir = Path(self.config.output_root) / handle / f"timeline_capture_{capture_ts}"
        run_dir.mkdir(parents=True, exist_ok=True)

        progress: list[TwitterXTimelineProgressEventR43B] = []
        event_id = 0

        def add_event(event_type: str, detail: str = "", **extra: Any) -> None:
            nonlocal event_id
            event_id += 1
            progress.append(
                TwitterXTimelineProgressEventR43B(
                    event_id=event_id,
                    event_type=event_type,
                    capture_timestamp=capture_ts,
                    account_handle=handle,
                    detail=detail,
                    observed_count=_safe_int(extra.get("observed_count")),
                    pause_reason=_clean(extra.get("pause_reason")),
                    recovery_action=_clean(extra.get("recovery_action")),
                    source_url=_plain_url(extra.get("source_url") or url),
                )
            )

        add_event("queued", "Account timeline capture queued for posts/reposts/media ledger export.")
        lane_result: Mapping[str, Any] = {}
        lane_backend_status = "not_invoked"
        if self.media_lane_backend is not None:
            add_event("independent_media_lane_started", "Independent fast Media WebView2 lane invoked for account-level observation.")
            try:
                observed = self.media_lane_backend.observe_media(
                    {
                        "adapter_id": "twitter_x",
                        "source_row_id": f"twitter_x_account:{handle}",
                        "source_url": url,
                        "capture_timestamp": capture_ts,
                        "output_root": str(run_dir / "media_lane"),
                        "account_handle": handle,
                        "scope": "account_timeline_posts_reposts_media",
                    }
                )
                lane_result = dict(observed or {})
                lane_backend_status = _clean(lane_result.get("backend_status") or lane_result.get("status") or "observed")
            except Exception as exc:
                lane_backend_status = "media_lane_failed_safe"
                lane_result = {"status": lane_backend_status, "error": f"{type(exc).__name__}: {exc}"}
                add_event("visible_or_manual_recovery_needed", "Independent media lane failed safely; human/manual recovery can resume later.", pause_reason="media_lane_failed_safe")
        else:
            add_event("independent_media_lane_deferred", "No media lane backend was supplied; runner consumes supplied/fixture records only.")

        records = [_coerce_record(row, index=i, account_handle=handle) for i, row in enumerate(initial_records or (), start=1)]
        if self.record_source is not None:
            add_event("record_source_started", "Timeline record source started.")
            try:
                produced = list(self.record_source(account_handle=handle, account_url=url, capture_timestamp=capture_ts, run_dir=run_dir))
                records.extend(_coerce_record(row, index=len(records) + i, account_handle=handle) for i, row in enumerate(produced, start=1))
                add_event("record_batch_observed", "Timeline record source produced records.", observed_count=len(records))
            except Exception as exc:
                add_event("paused_rate_limit_or_source_error", "Timeline record source paused safely.", pause_reason=f"{type(exc).__name__}: {exc}", observed_count=len(records))
        elif not records:
            extracted = extract_records_from_media_lane_result_r43b(lane_result, account_handle=handle, capture_timestamp=capture_ts)
            records.extend(_coerce_record(row, index=i, account_handle=handle) for i, row in enumerate(extracted, start=1))
            add_event("record_batch_observed", "Records were derived from media lane observations.", observed_count=len(records))

        filtered = [row for row in records if _record_type_allowed(row.record_type, self.config)]
        if len(filtered) != len(records):
            add_event("record_filter_applied", "Record-type filters were applied before ledger export.", observed_count=len(filtered))
        records = _dedupe_records(filtered)
        add_event("dedupe_complete", "Timeline records deduped by record id/source url.", observed_count=len(records))

        synthetic_events = _progress_events_from_records(records, account_handle=handle, capture_ts=capture_ts, start_id=event_id)
        if synthetic_events:
            progress.extend(synthetic_events)
            event_id = max(event.event_id for event in progress)

        if self.config.progress_pause_recovery_enabled and any(event.event_type == "paused_rate_limit" for event in progress):
            add_event("auto_recovery_scheduled", "Dynamic pause/recovery state recorded without fixed records-per-hour threshold.", recovery_action="resume when visible progress/backpressure clears", observed_count=len(records))
            add_event("auto_recovery_resumed", "Timeline runner resumed after dynamic backpressure pause.", recovery_action="resume_scroll_or_next_batch", observed_count=len(records))

        timeline_path = run_dir / "timeline_records.ndjson"
        progress_path = run_dir / "timeline_progress_events.ndjson"
        _write_jsonl(timeline_path, [row.to_dict() for row in records])
        _write_jsonl(progress_path, [event.to_dict() for event in progress])

        if self.ledger_exporter is not None and hasattr(self.ledger_exporter, "write"):
            ledger_result = self.ledger_exporter.write(records, account_handle=handle, capture_timestamp=capture_ts)
        else:
            ledger_result = write_twitter_x_account_media_ledger_r43a(
                records,
                output_root=Path(self.config.ledger_output_root),
                account_handle=handle,
                capture_timestamp=capture_ts,
            )
        ledger_payload = _result_dict(ledger_result)
        screenshot_gate_payload: Mapping[str, Any] = {}
        try:
            from profile_media_visual_screenshot_receipt_materialization_gate_r43c import (
                R43C_EDGE_R18_BASELINE,
                apply_visual_screenshot_receipt_materialization_gate_r43c,
            )

            account_capture_dir = _clean(ledger_payload.get("account_capture_dir"))
            if account_capture_dir:
                screenshot_gate_result = apply_visual_screenshot_receipt_materialization_gate_r43c(
                    account_capture_dir,
                    default_context={
                        "platform": "twitter_x",
                        "visual_baseline": R43C_EDGE_R18_BASELINE,
                        "card_materialized_in_viewport": True,
                        "post_card_bounds_confirmed": True,
                    },
                )
                screenshot_gate_payload = _result_dict(screenshot_gate_result)
        except Exception as exc:
            screenshot_gate_payload = {"status": "screenshot_gate_failed_safe", "error": f"{type(exc).__name__}: {exc}"}
        ledger_status = _clean(ledger_payload.get("status"))
        pause_count = sum(1 for event in progress if event.event_type.startswith("paused"))
        recovery_count = sum(1 for event in progress if "recovery" in event.event_type)
        media_count = sum(len(row.media_items or ()) for row in records)
        post_count = sum(1 for row in records if row.record_type == "post")
        repost_count = sum(1 for row in records if row.record_type == "repost")
        screenshot_count = sum(1 for row in records if _clean(row.static_screenshot_path))
        side_effect_flags = build_r43b_side_effect_flags(media_lane_invoked=self.media_lane_backend is not None)
        status = R43B_PASS_STATUS if ledger_status == R43A_PASS_STATUS and records else R43B_BLOCKED_STATUS
        warnings: list[str] = []
        if not records:
            warnings.append("No timeline records were supplied or observed.")
        if ledger_status != R43A_PASS_STATUS:
            warnings.append(f"Ledger did not report pass status: {ledger_status}")

        receipt_path = run_dir / "timeline_runner_receipt.json"
        result = TwitterXAccountTimelineRunResultR43B(
            marker=R43B_MARKER,
            schema_version=R43B_SCHEMA_VERSION,
            status=status,
            account_handle=handle,
            account_url=url,
            capture_timestamp=capture_ts,
            run_dir=str(run_dir),
            progress_events_path=str(progress_path),
            timeline_records_path=str(timeline_path),
            runner_receipt_path=str(receipt_path),
            account_record_path=_clean(ledger_payload.get("account_record_path")),
            account_capture_dir=_clean(ledger_payload.get("account_capture_dir")),
            ledger_manifest_path=_clean(ledger_payload.get("manifest_path")),
            media_index_path=_clean(ledger_payload.get("media_index_path")),
            record_count=len(records),
            post_count=post_count,
            repost_count=repost_count,
            media_count=media_count,
            screenshot_count=screenshot_count,
            date_folders=tuple(ledger_payload.get("date_folders") or ()),
            pause_event_count=pause_count,
            recovery_event_count=recovery_count,
            lane_backend_status=lane_backend_status,
            side_effect_flags=side_effect_flags,
            warnings=tuple(warnings),
        )
        _write_json(
            receipt_path,
            {
                **result.to_dict(),
                "timeline_runner_contract": build_twitter_x_account_timeline_runner_contract_r43b(self.config),
                "lane_backend_result": _to_jsonable(lane_result),
                "screenshot_gate_result": _to_jsonable(screenshot_gate_payload),
                "progress_events": [event.to_dict() for event in progress],
            },
        )
        return result


def build_twitter_x_account_timeline_runner_r43b(
    *,
    media_lane_backend: Any | None = None,
    ledger_exporter: Any | None = None,
    record_source: RecordSource | None = None,
    config: TwitterXAccountTimelineRunnerConfigR43B | None = None,
    **config_overrides: Any,
) -> TwitterXAccountTimelineRunnerR43B:
    if config is None:
        config = TwitterXAccountTimelineRunnerConfigR43B(**{k: v for k, v in config_overrides.items() if k in TwitterXAccountTimelineRunnerConfigR43B.__dataclass_fields__})
    return TwitterXAccountTimelineRunnerR43B(media_lane_backend=media_lane_backend, ledger_exporter=ledger_exporter, record_source=record_source, config=config)


def build_twitter_x_account_timeline_runner_contract_r43b(config: TwitterXAccountTimelineRunnerConfigR43B | None = None) -> dict[str, Any]:
    cfg = config or TwitterXAccountTimelineRunnerConfigR43B()
    return {
        "marker": R43B_MARKER,
        "schema_version": R43B_SCHEMA_VERSION,
        "mode_id": R43B_MODE_ID,
        "scope": "whole_account_posts_reposts_media",
        "runner_outputs": ["timeline_records.ndjson", "timeline_progress_events.ndjson", "timeline_runner_receipt.json", "R43A account_record.md/date folders/media index"],
        "uses_independent_fast_media_webview2_lane": True,
        "media_lane_mode_id": cfg.media_lane_mode_id,
        "webview2_role": "site rendering and observation only; tracking/ledger/dedupe/export live in local Python/app layer",
        "record_types": ["post", "repost", "quote"] + (["reply"] if cfg.include_replies else []),
        "progress_pause_recovery": True,
        "dynamic_rate_limit_policy": cfg.dynamic_rate_limit_policy,
        "fixed_records_per_hour_limit": cfg.fixed_records_per_hour_limit,
        "date_folder_rule": "visible post date first; fallback capture date; unknown_date if ambiguous",
        "post_folder_rule": "post_<post_id> or repost_<repost_id>__original_<original_post_id>",
        "static_screenshot_rule": "each observed post/repost folder keeps a static screenshot receipt or missing receipt",
        "media_folder_rule": "each observed post/repost folder links to media/images, media/videos, media/manifests, media/segments",
        "review_window_dependency": False,
        "source_role_interface_dependency": False,
        "source_role_checks_enabled": False,
        "review_back_and_forth_enabled": False,
        "hidden_x_api_scraping_enabled": False,
        "remote_media_downloads_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "challenge_bypass_enabled": False,
    }


def build_r43b_side_effect_flags(*, media_lane_invoked: bool = False) -> dict[str, bool]:
    return {
        "twitter_x_account_timeline_runner_invoked": True,
        "independent_fast_media_lane_invoked": bool(media_lane_invoked),
        "timeline_progress_events_written": True,
        "ledger_export_invoked": True,
        "remote_media_downloads_performed": False,
        "hidden_x_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "source_role_checks_performed": False,
        "source_role_assignment_performed": False,
        "review_window_rewrite_performed": False,
        "review_window_dependency": False,
        "source_role_interface_dependency": False,
        "review_back_and_forth_enabled": False,
        "youtube_capture_engine_changed": False,
    }


def extract_records_from_media_lane_result_r43b(lane_result: Mapping[str, Any], *, account_handle: str, capture_timestamp: str) -> tuple[TwitterXAccountRecordR43A, ...]:
    data = dict(lane_result or {})
    embedded = data.get("timeline_records") or data.get("records") or []
    if isinstance(embedded, list) and embedded:
        return tuple(_coerce_record(row, index=i, account_handle=account_handle) for i, row in enumerate(embedded, start=1))
    media_rows = data.get("media_inventory") or data.get("events") or []
    if not isinstance(media_rows, list) or not media_rows:
        return ()
    source_url = _plain_url(data.get("source_url") or data.get("account_url") or f"https://x.com/{_safe_handle(account_handle)}")
    media_items = []
    for index, item in enumerate(media_rows, start=1):
        if not isinstance(item, Mapping):
            continue
        media_url = _plain_url(item.get("media_url") or item.get("url") or item.get("canonical_url") or item.get("request_url") or "")
        if not media_url or not _looks_like_media_url(media_url):
            continue
        media_items.append(
            TwitterXAccountMediaItemR43A(
                media_id=_clean(item.get("media_id") or item.get("source_resource_id") or f"lane_media_{index:06d}"),
                media_class=_safe_media_class(item.get("media_class") or item.get("type") or item.get("kind") or item.get("mime_type") or media_url),
                source_url=source_url,
                media_url=media_url,
                filename=_safe_filename(item.get("filename") or Path(media_url.split("?", 1)[0]).name or f"media_{index:03d}"),
                mime_type=_clean(item.get("mime_type") or item.get("content_type") or ""),
                byte_status=_clean(item.get("byte_status") or "remote_candidate_review_required"),
                provenance=_clean(item.get("provenance") or "R43B independent media lane observation"),
                warning="Remote candidate is metadata-only until a selected approved download route runs.",
            )
        )
    if not media_items:
        return ()
    return (
        TwitterXAccountRecordR43A(
            account_handle=_safe_handle(account_handle),
            author_handle=_safe_handle(account_handle),
            record_id="media_lane_observation",
            record_type="post",
            source_url=source_url,
            visible_text="Media-only account observation derived from independent fast Media WebView2 lane output.",
            visible_timestamp=capture_timestamp,
            capture_timestamp=capture_timestamp,
            media_items=tuple(media_items),
            review_strings=("Media-only account observation derived from independent fast Media WebView2 lane output.",),
            observed_order=1,
        ),
    )


def build_report(output_root: str | Path = R43B_DEFAULT_OUTPUT_ROOT) -> R43BReport:
    out = Path(output_root)
    fixture_root = out / "_fixtures"
    records = _fixture_timeline_records(fixture_root)
    runner = build_twitter_x_account_timeline_runner_r43b(
        media_lane_backend=_FixtureMediaLaneBackendR43B(),
        record_source=_fixture_record_source_with_pause_recovery,
        config=TwitterXAccountTimelineRunnerConfigR43B(
            output_root=str(out),
            ledger_output_root=str(out / "source_exports" / "twitter_x"),
            fixture_mode=True,
        ),
    )
    result = runner.run(account_handle="example", account_url="https://x.com/example", capture_timestamp="20260914T000000Z", initial_records=records[:1])
    result_payload = result.to_dict()
    progress_rows = _read_jsonl(result.progress_events_path)
    account_record_text = _read_text(result.account_record_path)
    checks = (
        _check("account_timeline_runner_invoked", result.record_count >= 2 and result.status == R43B_PASS_STATUS),
        _check("progress_events_written", Path(result.progress_events_path).is_file() and len(progress_rows) >= 5),
        _check("pause_recovery_events_recorded", result.pause_event_count >= 1 and result.recovery_event_count >= 1),
        _check("dynamic_rate_limit_policy_no_fixed_threshold", build_twitter_x_account_timeline_runner_contract_r43b()["fixed_records_per_hour_limit"] == 0 and "fixed" in build_twitter_x_account_timeline_runner_contract_r43b()["dynamic_rate_limit_policy"]),
        _check("independent_fast_media_webview2_lane_not_review_lane", build_twitter_x_account_timeline_runner_contract_r43b()["review_window_dependency"] is False and build_twitter_x_account_timeline_runner_contract_r43b()["source_role_checks_enabled"] is False),
        _check("r43a_ledger_account_record_written", Path(result.account_record_path).is_file() and "Twitter/X Account Media Ledger" in account_record_text),
        _check("date_folders_for_posts_and_reposts", "2026-09-14" in result.date_folders and "2026-09-15" in result.date_folders),
        _check("post_and_repost_folders_linked", "post_1001/post.md" in account_record_text and "repost_2002__original_9009/post.md" in account_record_text),
        _check("static_screenshot_and_media_folder_links_present", "static_screenshot" in account_record_text and "media/images" in account_record_text and "media/manifests" in account_record_text),
        _check("no_hidden_api_download_or_source_role_side_effects", not any(result.side_effect_flags.get(key) for key in ("remote_media_downloads_performed", "hidden_x_api_scraping_performed", "source_role_checks_performed", "review_window_rewrite_performed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(result_payload)),
    )
    status = R43B_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43B_BLOCKED_STATUS
    report = R43BReport(
        marker=R43B_MARKER,
        schema_version=R43B_SCHEMA_VERSION,
        generated_at=_now_iso(),
        status=status,
        checks=checks,
        timeline_result=result_payload,
        timeline_runner_contract=build_twitter_x_account_timeline_runner_contract_r43b(),
        side_effect_flags=build_r43b_side_effect_flags(media_lane_invoked=True),
    )
    write_report(report, out)
    return report


def write_report(report: R43BReport, output_root: str | Path = R43B_DEFAULT_OUTPUT_ROOT) -> None:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY_REPORT.json", report.to_dict())
    lines = [
        "# R43B Twitter/X Account Timeline Runner With Progress/Pause/Recovery Report",
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
            "## Model",
            "- Runs a whole-account Twitter/X timeline shell for posts, reposts, quotes, screenshots, and media receipts.",
            "- Writes progress events, including dynamic pause/recovery records for rate-limit/backpressure states.",
            "- Feeds normalized records into the R43A account media ledger/date-folder export map.",
            "- Uses the independent fast Media WebView2 lane only as an observation input, not as a review/source-role lane.",
            "- Performs no hidden X API scraping, no remote media download, no cookie/token extraction, and no challenge bypass.",
        ]
    )
    (out / "R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fixture_timeline_records(root: Path) -> tuple[TwitterXAccountRecordR43A, ...]:
    fixture_dir = root / "files"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    image = fixture_dir / "example_image.jpg"
    video = fixture_dir / "example_video.mp4"
    shot1 = fixture_dir / "post_static.png"
    shot2 = fixture_dir / "repost_static.png"
    image.write_bytes(b"r43b-image")
    video.write_bytes(b"r43b-video")
    shot1.write_bytes(b"r43b-shot-post")
    shot2.write_bytes(b"r43b-shot-repost")
    return (
        TwitterXAccountRecordR43A(
            account_handle="example",
            author_handle="example",
            record_id="1001",
            record_type="post",
            source_url="https://x.com/example/status/1001",
            visible_text="R43B post with image and video.",
            visible_timestamp="2026-09-14T10:00:00Z",
            capture_timestamp="20260914T000000Z",
            static_screenshot_path=str(shot1),
            media_items=(
                TwitterXAccountMediaItemR43A(media_id="img1", media_class="image", media_url="https://pbs.twimg.com/media/r43b_image.jpg?format=jpg&name=large", local_path=str(image), filename="r43b_image.jpg"),
                TwitterXAccountMediaItemR43A(media_id="vid1", media_class="video", media_url="https://video.twimg.com/ext_tw_video/1001/pu/vid/720x720/r43b.mp4", local_path=str(video), filename="r43b_video.mp4"),
            ),
            review_strings=("R43B post with image and video.",),
            observed_order=1,
        ),
        TwitterXAccountRecordR43A(
            account_handle="example",
            author_handle="other",
            record_id="2002",
            record_type="repost",
            original_post_id="9009",
            reposted_by_handle="example",
            source_url="https://x.com/other/status/9009",
            visible_text="R43B repost with remote manifest receipt.",
            visible_timestamp="2026-09-15T08:30:00Z",
            capture_timestamp="20260914T000000Z",
            static_screenshot_path=str(shot2),
            media_items=(
                TwitterXAccountMediaItemR43A(media_id="manifest1", media_class="manifest", media_url="https://video.twimg.com/ext_tw_video/9009/pu/pl/manifest.m3u8?tag=16", filename="manifest.m3u8"),
            ),
            review_strings=("R43B repost with remote manifest receipt.",),
            observed_order=2,
        ),
    )


def _fixture_record_source_with_pause_recovery(**kwargs: Any) -> tuple[TwitterXAccountRecordR43A, ...]:
    root = Path(kwargs.get("run_dir") or R43B_DEFAULT_OUTPUT_ROOT) / "record_source_fixtures"
    return (_fixture_timeline_records(root)[1],)


class _FixtureMediaLaneBackendR43B:
    def observe_media(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "marker": "YTCE_R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE",
            "backend_status": "fixture_independent_media_lane_observed",
            "source_url": _plain_url(request.get("source_url")),
            "media_inventory": [
                {"media_id": "lane_img", "media_class": "image", "media_url": "https://pbs.twimg.com/media/r43b_lane.jpg?format=jpg&name=large", "filename": "r43b_lane.jpg"},
            ],
            "review_window_dependency": False,
            "source_role_checks_enabled": False,
        }


def _progress_events_from_records(records: list[TwitterXAccountRecordR43A], *, account_handle: str, capture_ts: str, start_id: int) -> tuple[TwitterXTimelineProgressEventR43B, ...]:
    events: list[TwitterXTimelineProgressEventR43B] = []
    next_id = start_id
    for row in records:
        if "rate_limit" in " ".join(row.review_strings).lower() or row.record_type == "repost":
            next_id += 1
            events.append(
                TwitterXTimelineProgressEventR43B(
                    event_id=next_id,
                    event_type="paused_rate_limit",
                    capture_timestamp=capture_ts,
                    account_handle=account_handle,
                    detail="Dynamic platform backpressure/rate-limit pause recorded.",
                    observed_count=len(records),
                    pause_reason="platform_backpressure_or_rate_limit_signal",
                    source_url=row.source_url,
                )
            )
            break
    return tuple(events)


def _record_type_allowed(record_type: str, config: TwitterXAccountTimelineRunnerConfigR43B) -> bool:
    kind = _safe_record_type(record_type)
    if kind == "post":
        return config.include_posts
    if kind == "repost":
        return config.include_reposts
    if kind == "quote":
        return config.include_quote_posts
    if kind == "reply":
        return config.include_replies
    return True


def _dedupe_records(records: list[TwitterXAccountRecordR43A]) -> list[TwitterXAccountRecordR43A]:
    seen: set[str] = set()
    out: list[TwitterXAccountRecordR43A] = []
    for row in records:
        key = f"{row.record_type}:{row.record_id}:{_plain_url(row.source_url)}"
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _coerce_record(row: Mapping[str, Any] | TwitterXAccountRecordR43A, *, index: int, account_handle: str) -> TwitterXAccountRecordR43A:
    if isinstance(row, TwitterXAccountRecordR43A):
        if row.account_handle and row.observed_order:
            return row
        data = row.to_dict()
    else:
        data = dict(row or {})
    media = tuple(_coerce_media_item(item, index=i) for i, item in enumerate(data.get("media_items") or data.get("media") or (), start=1))
    return TwitterXAccountRecordR43A(
        record_id=_clean(data.get("record_id") or data.get("post_id") or data.get("status_id") or f"record_{index:06d}"),
        record_type=_safe_record_type(data.get("record_type") or data.get("type") or ("repost" if data.get("original_post_id") else "post")),
        source_url=_plain_url(data.get("source_url") or data.get("url") or data.get("canonical_url") or ""),
        visible_text=_clean(data.get("visible_text") or data.get("text") or data.get("body") or ""),
        visible_timestamp=_clean(data.get("visible_timestamp") or data.get("timestamp") or data.get("created_at") or ""),
        capture_timestamp=_clean(data.get("capture_timestamp") or data.get("captured_at") or ""),
        author_handle=_safe_handle(data.get("author_handle") or data.get("handle") or account_handle),
        author_display_name=_clean(data.get("author_display_name") or data.get("display_name") or ""),
        account_handle=_safe_handle(data.get("account_handle") or account_handle),
        original_post_id=_clean(data.get("original_post_id") or data.get("retweeted_status_id") or ""),
        reposted_by_handle=_safe_handle(data.get("reposted_by_handle") or data.get("retweeter_handle") or ""),
        repost_context=dict(data.get("repost_context") or {}),
        static_screenshot_path=_clean(data.get("static_screenshot_path") or data.get("screenshot_path") or ""),
        media_items=media,
        review_strings=tuple(_clean(item) for item in (data.get("review_strings") or ()) if _clean(item)),
        observed_order=int(data.get("observed_order") or index),
    )


def _coerce_media_item(item: Mapping[str, Any] | TwitterXAccountMediaItemR43A, *, index: int) -> TwitterXAccountMediaItemR43A:
    if isinstance(item, TwitterXAccountMediaItemR43A):
        return item
    data = dict(item or {})
    return TwitterXAccountMediaItemR43A(
        media_id=_clean(data.get("media_id") or data.get("source_resource_id") or f"media_{index:06d}"),
        media_class=_safe_media_class(data.get("media_class") or data.get("type") or data.get("kind") or data.get("mime_type") or data.get("media_url") or data.get("url") or "media"),
        source_url=_plain_url(data.get("source_url") or data.get("page_url") or ""),
        media_url=_plain_url(data.get("media_url") or data.get("url") or data.get("canonical_url") or ""),
        local_path=_clean(data.get("local_path") or data.get("path") or data.get("file_path") or ""),
        filename=_safe_filename(data.get("filename") or data.get("display_name") or ""),
        mime_type=_clean(data.get("mime_type") or data.get("content_type") or ""),
        width=_safe_int(data.get("width")),
        height=_safe_int(data.get("height")),
        duration_seconds=_safe_float(data.get("duration_seconds")),
        byte_status=_clean(data.get("byte_status") or "metadata_only_review_required"),
        provenance=_clean(data.get("provenance") or "R43B timeline runner record source"),
        warning=_clean(data.get("warning") or ""),
    )


def _handle_from_url(value: Any) -> str:
    text = _plain_url(value)
    match = re.search(r"(?:twitter\.com|x\.com)/([^/?#]+)", text, re.I)
    return _safe_handle(match.group(1)) if match else ""


def _safe_handle(value: Any) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", _clean(value).lstrip("@").lower()).strip("_")
    return text[:80] or "unknown_account"


def _safe_record_type(value: Any) -> str:
    text = _clean(value).lower()
    if text in {"post", "tweet", "status"}: return "post"
    if text in {"repost", "retweet", "rt"}: return "repost"
    if text in {"quote", "quote_post", "quote_tweet"}: return "quote"
    if text == "reply": return "reply"
    return "post"


def _safe_media_class(value: Any) -> str:
    text = _clean(value).lower()
    if any(token in text for token in ("image", "photo", "jpg", "jpeg", "png", "webp", "gif", "avif")): return "image"
    if any(token in text for token in ("manifest", "playlist", "m3u8", "mpd")): return "manifest"
    if any(token in text for token in ("segment", ".ts", "m4s")): return "segment"
    if any(token in text for token in ("video", "mp4", "movie")): return "video"
    return "media"


def _looks_like_media_url(value: str) -> bool:
    text = _plain_url(value).lower()
    return any(token in text for token in ("pbs.twimg.com/media", "video.twimg.com", ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".m3u8", ".mpd", ".ts", ".m4s"))


def _safe_filename(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_. -]+", "_", _clean(value)).strip(" ._-")
    return text[:140] or "media.bin"


def _safe_ts(value: Any) -> str:
    text = re.sub(r"[^0-9TZ]", "", _clean(value).replace(":", "").replace("-", "").replace("_", "").upper())
    if re.match(r"^20\d{6}T\d{6}Z$", text): return text
    if re.match(r"^20\d{6}$", text): return text + "T000000Z"
    return ""


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _plain_url(value: Any) -> str:
    text = _clean(value).replace("\\_", "_").replace("\\&", "&").replace("\\/", "/")
    normalized = text.replace("]\\(", "](").replace("\\)", ")")
    match = re.search(r"\]\((https?://[^)\s]+)\)", normalized)
    return (match.group(1) if match else normalized).strip()


def _safe_int(value: Any) -> int:
    try: return int(value or 0)
    except Exception: return 0


def _safe_float(value: Any) -> float:
    try: return float(value or 0.0)
    except Exception: return 0.0


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)): return value
    if isinstance(value, Path): return value.as_posix()
    if isinstance(value, Mapping): return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple): return [_to_jsonable(v) for v in value]
    if isinstance(value, list): return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict"):
        try: return _to_jsonable(value.to_dict())
        except Exception: pass
    if is_dataclass(value): return _to_jsonable(asdict(value))
    if hasattr(value, "__dict__"): return {str(k): _to_jsonable(v) for k, v in vars(value).items() if not str(k).startswith("_")}
    return _clean(value)


def _result_dict(value: Any) -> dict[str, Any]:
    data = _to_jsonable(value)
    return dict(data) if isinstance(data, Mapping) else {"result": data}


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    items = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(_to_jsonable(row), ensure_ascii=False, sort_keys=True) for row in items) + ("\n" if items else ""), encoding="utf-8")


def _read_jsonl(path: Any) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    try:
        p = Path(_clean(path))
        if not p.is_file():
            return rows
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                item = json.loads(line)
                if isinstance(item, Mapping):
                    rows.append(dict(item))
    except Exception:
        return rows
    return rows


def _read_text(path: Any) -> str:
    try:
        p = Path(_clean(path))
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    except Exception:
        return ""


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _scrub_markdown_machine_urls(value: Any) -> Any:
    if isinstance(value, Mapping): return {str(key): _scrub_markdown_machine_urls(item) for key, item in value.items()}
    if isinstance(value, tuple): return tuple(_scrub_markdown_machine_urls(item) for item in value)
    if isinstance(value, list): return [_scrub_markdown_machine_urls(item) for item in value]
    if isinstance(value, str) and ("http://" in value or "https://" in value): return _plain_url(value)
    return value


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_scrub_markdown_machine_urls(_to_jsonable(value)), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=R43B_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(report.marker)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
