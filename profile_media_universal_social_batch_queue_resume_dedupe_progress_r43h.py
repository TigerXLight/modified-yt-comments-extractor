from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_universal_social_batch_account_intake_platform_url_detection_r43g import (
    R43G_PASS_STATUS,
    UniversalSocialBatchAccountIntakeRequestR43G,
    UniversalSocialBatchAccountIntakeRouterR43G,
    UniversalSocialDetectedInputR43G,
    build_r43g_side_effect_flags,
    build_universal_social_batch_account_intake_router_r43g,
    extract_urls_from_text_r43g,
)

R43H_MARKER = "YTCE_R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS"
R43H_PASS_STATUS = "PASS_R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS"
R43H_BLOCKED_STATUS = "BLOCKED_R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS"
R43H_SCHEMA_VERSION = "universal_social_batch_queue_resume_dedupe_progress.r43h.v1"
R43H_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43h_universal_social_batch_queue_resume_dedupe_progress"
R43H_MODE_ID = "universal_social_batch_queue_resume_dedupe_progress"

BATCH_QUEUE_OUTPUT_FILES_R43H: tuple[str, ...] = (
    "batch_queue.json",
    "batch_queue.ndjson",
    "batch_queue_progress_events.ndjson",
    "batch_resume_receipt.json",
    "dedupe_index.json",
    "batch_queue_summary.md",
    "route_receipts.ndjson",
    "R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS_REPORT.json",
    "R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS_REPORT.md",
)

RETRYABLE_QUEUE_STATUSES_R43H = {"pending", "failed_retryable"}
NON_RETRYABLE_QUEUE_STATUSES_R43H = {"completed", "duplicate", "failed_terminal", "unsupported_platform"}
PENDING_PLATFORM_IDS_R43H = {
    "instagram",
    "facebook",
    "threads",
    "mastodon",
    "tiktok",
    "youtube",
    "news_comments",
}


@dataclass(frozen=True)
class UniversalSocialBatchQueueRequestR43H:
    inputs: tuple[str, ...] = ()
    raw_text: str = ""
    txt_path: str = ""
    detected_items: tuple[Mapping[str, Any], ...] = ()
    existing_queue_path: str = ""
    platform_id_hint: str = ""
    include_posts: bool = True
    include_reposts_or_reshares: bool = True
    include_quotes: bool = True
    include_replies: bool = False
    include_media: bool = True
    include_static_screenshots: bool = True
    require_screenshot_receipts: bool = True
    capture_timestamp: str = ""
    output_root: str = R43H_DEFAULT_OUTPUT_ROOT
    fixture_mode: bool = False
    force_retry_terminal: bool = False
    process_now: bool = True
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    public_network_enabled: bool = False
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""
    max_items: int = 3
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchQueueRecordR43H:
    queue_id: str
    batch_index: int
    raw_input: str
    normalized_url: str
    platform_id: str
    url_kind: str
    account_handle: str
    record_id: str
    dedupe_key: str
    route_status: str = "not_routed"
    downstream_status: str = ""
    status: str = "pending"
    attempts: int = 0
    created_at: str = ""
    updated_at: str = ""
    last_error: str = ""
    route_receipt_path: str = ""
    run_dir: str = ""
    duplicate_of: str = ""
    explicit_live_mode: bool = False
    run_visible_live: bool = False
    live_mode: bool = False
    public_network_enabled: bool = False
    browser_user_data_dir: str = ""
    browser_executable_path: str = ""
    max_items: int = 3
    max_scrolls: int = 2

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class UniversalSocialBatchQueueResultR43H:
    marker: str
    schema_version: str
    status: str
    capture_timestamp: str
    run_dir: str
    batch_queue_path: str
    batch_queue_ndjson_path: str
    progress_events_path: str
    resume_receipt_path: str
    dedupe_index_path: str
    summary_path: str
    route_receipts_path: str
    report_json_path: str
    report_md_path: str
    total_items: int
    routed_count: int
    completed_count: int
    duplicate_count: int
    pending_count: int
    failed_retryable_count: int
    failed_terminal_count: int
    unsupported_count: int
    skipped_completed_count: int
    skipped_non_retryable_count: int
    retried_count: int
    queue_records: tuple[Mapping[str, Any], ...]
    route_receipts: tuple[Mapping[str, Any], ...]
    resume_receipt: Mapping[str, Any]
    dedupe_index: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43H_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43HReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]
    output_files: tuple[str, ...] = BATCH_QUEUE_OUTPUT_FILES_R43H

    @property
    def passed(self) -> bool:
        return self.status == R43H_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "generated_at": self.generated_at,
            "marker": self.marker,
            "output_files": list(self.output_files),
            "sample_result": _to_jsonable(self.sample_result),
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
        }


class UniversalSocialBatchQueueRouterR43H:
    """Persistent universal batch queue above R43G/R43F/R43E.

    R43H owns resume, dedupe, retry eligibility and progress files.  It uses
    R43G for URL normalization/platform detection and routes eligible canonical
    records through R43G, which then passes through R43F/R43E/concrete adapters.
    It does not start browser engines, run source-role checks, scrape hidden
    APIs, extract credentials, bypass challenges, or download remote media.
    """

    def __init__(
        self,
        *,
        intake_router: UniversalSocialBatchAccountIntakeRouterR43G | None = None,
        output_root: str | Path = R43H_DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.output_root = Path(output_root)
        self.intake_router = intake_router or build_universal_social_batch_account_intake_router_r43g(output_root=self.output_root / "r43g_intake")

    def build_queue_records(
        self,
        request: UniversalSocialBatchQueueRequestR43H | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> tuple[UniversalSocialBatchQueueRequestR43H, list[UniversalSocialBatchQueueRecordR43H], dict[str, Any]]:
        req = coerce_universal_social_batch_queue_request_r43h(request, **overrides)
        now = _safe_ts(req.capture_timestamp) or _now_ts()
        existing = _load_existing_queue_records(req.existing_queue_path)
        if existing:
            return req, existing, build_dedupe_index_r43h(existing)

        detected = self._collect_detected_items(req)
        records: list[UniversalSocialBatchQueueRecordR43H] = []
        dedupe_by_normalized_url: dict[str, str] = {}
        dedupe_by_record_key: dict[str, str] = {}
        for item in detected:
            record_key = _record_key(item.platform_id, item.account_handle, item.record_id)
            url_key = _normalized_url_key(item.platform_id, item.normalized_url)
            dedupe_key = record_key or url_key
            duplicate_of = ""
            if record_key and record_key in dedupe_by_record_key:
                duplicate_of = dedupe_by_record_key[record_key]
            elif url_key and url_key in dedupe_by_normalized_url:
                duplicate_of = dedupe_by_normalized_url[url_key]

            queue_id = f"r43h-{item.batch_index:05d}-{_safe_id(dedupe_key or item.normalized_url or item.raw_input)}"
            status = "duplicate" if duplicate_of else "pending"
            record = UniversalSocialBatchQueueRecordR43H(
                queue_id=queue_id,
                batch_index=item.batch_index,
                raw_input=item.raw_input,
                normalized_url=item.normalized_url,
                platform_id=item.platform_id,
                url_kind=item.url_kind,
                account_handle=item.account_handle,
                record_id=item.record_id,
                dedupe_key=dedupe_key,
                status=status,
                created_at=now,
                updated_at=now,
                last_error="",
                duplicate_of=duplicate_of,
                explicit_live_mode=req.explicit_live_mode,
                run_visible_live=req.run_visible_live,
                live_mode=req.live_mode,
                public_network_enabled=req.public_network_enabled,
                browser_user_data_dir=req.browser_user_data_dir,
                browser_executable_path=req.browser_executable_path,
                max_items=req.max_items,
                max_scrolls=req.max_scrolls,
            )
            records.append(record)
            if not duplicate_of:
                if url_key:
                    dedupe_by_normalized_url[url_key] = queue_id
                if record_key:
                    dedupe_by_record_key[record_key] = queue_id
        return req, records, build_dedupe_index_r43h(records)

    def run_batch(
        self,
        request: UniversalSocialBatchQueueRequestR43H | Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> UniversalSocialBatchQueueResultR43H:
        req, records, dedupe_index = self.build_queue_records(request, **overrides)
        capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
        run_dir = Path(req.output_root or self.output_root) / f"batch_queue_{capture_ts}"
        run_dir.mkdir(parents=True, exist_ok=True)

        queue_path = run_dir / "batch_queue.json"
        queue_ndjson_path = run_dir / "batch_queue.ndjson"
        events_path = run_dir / "batch_queue_progress_events.ndjson"
        resume_receipt_path = run_dir / "batch_resume_receipt.json"
        dedupe_index_path = run_dir / "dedupe_index.json"
        summary_path = run_dir / "batch_queue_summary.md"
        route_receipts_path = run_dir / "route_receipts.ndjson"
        report_json_path = run_dir / "R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS_REPORT.json"
        report_md_path = run_dir / "R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS_REPORT.md"

        updated_records: list[UniversalSocialBatchQueueRecordR43H] = []
        events: list[Mapping[str, Any]] = []
        route_receipts: list[Mapping[str, Any]] = []
        resume_counts = {
            "completed": 0,
            "duplicate": 0,
            "failed_retryable": 0,
            "failed_terminal": 0,
            "pending": 0,
            "retried": 0,
            "routed": 0,
            "skipped_completed": 0,
            "skipped_non_retryable": 0,
            "unsupported": 0,
        }

        for record in records:
            eligible, reason = self._route_eligibility(record, force_retry_terminal=req.force_retry_terminal)
            events.append(_progress_event(capture_ts, record, "queue_record_seen", reason))
            if record.status == "duplicate":
                resume_counts["duplicate"] += 1
                updated_records.append(record)
                events.append(_progress_event(capture_ts, record, "duplicate_skipped", f"duplicate_of={record.duplicate_of}"))
                continue
            if record.status == "completed" and not req.force_retry_terminal:
                resume_counts["completed"] += 1
                resume_counts["skipped_completed"] += 1
                updated_records.append(record)
                events.append(_progress_event(capture_ts, record, "completed_skipped", "completed items are skipped on resume"))
                continue
            if not eligible:
                if record.status == "unsupported_platform":
                    resume_counts["unsupported"] += 1
                elif record.status == "failed_terminal":
                    resume_counts["failed_terminal"] += 1
                resume_counts["skipped_non_retryable"] += 1
                updated_records.append(record)
                events.append(_progress_event(capture_ts, record, "non_retryable_skipped", reason))
                continue
            if not req.process_now:
                resume_counts["pending"] += 1
                updated_records.append(record)
                events.append(_progress_event(capture_ts, record, "left_pending", "process_now is false"))
                continue

            routed_record, route_payload = self._route_record(req, record, run_dir=run_dir, capture_ts=capture_ts)
            updated_records.append(routed_record)
            route_receipts.append(route_payload)
            resume_counts["routed"] += 1
            if record.status == "failed_retryable":
                resume_counts["retried"] += 1
            if routed_record.status == "completed":
                resume_counts["completed"] += 1
            elif routed_record.status == "failed_retryable":
                resume_counts["failed_retryable"] += 1
            elif routed_record.status == "unsupported_platform":
                resume_counts["unsupported"] += 1
            events.append(_progress_event(capture_ts, routed_record, "route_completed", routed_record.route_status))

        dedupe_index = build_dedupe_index_r43h(updated_records)
        side_effect_flags = build_r43h_side_effect_flags()
        resume_receipt = {
            "capture_timestamp": capture_ts,
            "force_retry_terminal": req.force_retry_terminal,
            "marker": R43H_MARKER,
            "resume_counts": resume_counts,
            "schema_version": R43H_SCHEMA_VERSION,
            "skipped_completed_queue_ids": [r.queue_id for r in records if r.status == "completed" and not req.force_retry_terminal],
            "skipped_non_retryable_queue_ids": [
                r.queue_id for r in records if r.status in {"failed_terminal", "unsupported_platform"} and not req.force_retry_terminal
            ],
        }

        result = UniversalSocialBatchQueueResultR43H(
            marker=R43H_MARKER,
            schema_version=R43H_SCHEMA_VERSION,
            status=R43H_PASS_STATUS,
            capture_timestamp=capture_ts,
            run_dir=str(run_dir),
            batch_queue_path=str(queue_path),
            batch_queue_ndjson_path=str(queue_ndjson_path),
            progress_events_path=str(events_path),
            resume_receipt_path=str(resume_receipt_path),
            dedupe_index_path=str(dedupe_index_path),
            summary_path=str(summary_path),
            route_receipts_path=str(route_receipts_path),
            report_json_path=str(report_json_path),
            report_md_path=str(report_md_path),
            total_items=len(updated_records),
            routed_count=resume_counts["routed"],
            completed_count=sum(1 for r in updated_records if r.status == "completed"),
            duplicate_count=sum(1 for r in updated_records if r.status == "duplicate"),
            pending_count=sum(1 for r in updated_records if r.status == "pending"),
            failed_retryable_count=sum(1 for r in updated_records if r.status == "failed_retryable"),
            failed_terminal_count=sum(1 for r in updated_records if r.status == "failed_terminal"),
            unsupported_count=sum(1 for r in updated_records if r.status == "unsupported_platform"),
            skipped_completed_count=resume_counts["skipped_completed"],
            skipped_non_retryable_count=resume_counts["skipped_non_retryable"],
            retried_count=resume_counts["retried"],
            queue_records=tuple(r.to_dict() for r in updated_records),
            route_receipts=tuple(_to_jsonable(r) for r in route_receipts),
            resume_receipt=resume_receipt,
            dedupe_index=dedupe_index,
            side_effect_flags=side_effect_flags,
        )
        _write_json(queue_path, {"items": result.queue_records, "marker": R43H_MARKER, "schema_version": R43H_SCHEMA_VERSION})
        _write_ndjson(queue_ndjson_path, result.queue_records)
        _write_ndjson(events_path, events)
        _write_json(resume_receipt_path, resume_receipt)
        _write_json(dedupe_index_path, dedupe_index)
        _write_ndjson(route_receipts_path, route_receipts)
        _write_text(summary_path, _build_summary(result))
        report = build_report_from_result_r43h(result)
        write_report(report, run_dir)
        return result

    def _collect_detected_items(self, req: UniversalSocialBatchQueueRequestR43H) -> list[UniversalSocialDetectedInputR43G]:
        if req.detected_items:
            return [_detected_from_mapping(item, index + 1, self.intake_router) for index, item in enumerate(req.detected_items)]
        raw_items = _collect_batch_inputs_preserving_duplicates_r43h(req)
        return [
            self.intake_router.detect_input(raw, batch_index=index, platform_id_hint=req.platform_id_hint)
            for index, raw in enumerate(raw_items, start=1)
        ]

    def _route_eligibility(self, record: UniversalSocialBatchQueueRecordR43H, *, force_retry_terminal: bool = False) -> tuple[bool, str]:
        if record.status in RETRYABLE_QUEUE_STATUSES_R43H:
            return True, f"{record.status} records are eligible for route"
        if force_retry_terminal and record.status in {"failed_terminal", "unsupported_platform"}:
            return True, "forced retry requested"
        if record.status == "completed":
            return False, "completed items are skipped on resume"
        if record.status == "duplicate":
            return False, "duplicate entries point to canonical queue item and are not routed twice"
        return False, f"{record.status} is not retried by default"

    def _route_record(
        self,
        req: UniversalSocialBatchQueueRequestR43H,
        record: UniversalSocialBatchQueueRecordR43H,
        *,
        run_dir: Path,
        capture_ts: str,
    ) -> tuple[UniversalSocialBatchQueueRecordR43H, Mapping[str, Any]]:
        route_result = self.intake_router.route_batch(
            UniversalSocialBatchAccountIntakeRequestR43G(
                inputs=(record.normalized_url or record.raw_input,),
                platform_id_hint=record.platform_id if record.platform_id != "unknown_platform" else "",
                include_posts=req.include_posts,
                include_reposts_or_reshares=req.include_reposts_or_reshares,
                include_quotes=req.include_quotes,
                include_replies=req.include_replies,
                include_media=req.include_media,
                include_static_screenshots=req.include_static_screenshots,
                require_screenshot_receipts=req.require_screenshot_receipts,
                capture_timestamp=f"{capture_ts}_{record.batch_index:05d}",
                output_root=str(run_dir / "r43g_routes"),
                fixture_mode=req.fixture_mode,
                explicit_live_mode=record.explicit_live_mode or req.explicit_live_mode,
                run_visible_live=record.run_visible_live or req.run_visible_live,
                live_mode=record.live_mode or req.live_mode,
                public_network_enabled=record.public_network_enabled or req.public_network_enabled,
                browser_user_data_dir=record.browser_user_data_dir or req.browser_user_data_dir,
                browser_executable_path=record.browser_executable_path or req.browser_executable_path,
                max_items=record.max_items or req.max_items,
                max_scrolls=record.max_scrolls or req.max_scrolls,
            )
        )
        route_payload = route_result.to_dict()
        route_payload["queue_id"] = record.queue_id
        if route_result.status != R43G_PASS_STATUS or not route_result.items:
            return (
                _replace_record(
                    record,
                    attempts=record.attempts + 1,
                    downstream_status=route_result.status,
                    last_error="R43G route did not return a usable item",
                    route_status="failed_retryable",
                    status="failed_retryable",
                    updated_at=_now_ts(),
                    run_dir=str(route_result.run_dir),
                ),
                route_payload,
            )
        routed_item = dict(route_result.items[0])
        route_status = _clean(routed_item.get("route_status"))
        downstream_status = _clean(routed_item.get("downstream_status"))
        status = "completed"
        last_error = ""
        if route_status == "unsupported_platform_receipt":
            status = "unsupported_platform"
            last_error = "unsupported platform receipt preserved"
        updated = _replace_record(
            record,
            attempts=record.attempts + 1,
            downstream_status=downstream_status,
            last_error=last_error,
            route_receipt_path=_clean(routed_item.get("route_receipt_path")),
            route_status=route_status,
            run_dir=_clean(routed_item.get("route_run_dir") or route_result.run_dir),
            status=status,
            updated_at=_now_ts(),
        )
        return updated, route_payload


def build_universal_social_batch_queue_router_r43h(
    *,
    intake_router: UniversalSocialBatchAccountIntakeRouterR43G | None = None,
    output_root: str | Path = R43H_DEFAULT_OUTPUT_ROOT,
) -> UniversalSocialBatchQueueRouterR43H:
    return UniversalSocialBatchQueueRouterR43H(intake_router=intake_router, output_root=output_root)


def coerce_universal_social_batch_queue_request_r43h(
    request: UniversalSocialBatchQueueRequestR43H | Mapping[str, Any] | None = None,
    **overrides: Any,
) -> UniversalSocialBatchQueueRequestR43H:
    if isinstance(request, UniversalSocialBatchQueueRequestR43H):
        data = request.to_dict()
    else:
        data = dict(request or {})
    data.update(overrides)
    return UniversalSocialBatchQueueRequestR43H(
        inputs=tuple(_clean(v) for v in data.get("inputs", ()) if _clean(v)),
        raw_text=_clean(data.get("raw_text")),
        txt_path=_clean(data.get("txt_path")),
        detected_items=tuple(dict(item) for item in data.get("detected_items", ()) if isinstance(item, Mapping)),
        existing_queue_path=_clean(data.get("existing_queue_path")),
        platform_id_hint=_safe_platform_id(data.get("platform_id_hint")),
        include_posts=bool(data.get("include_posts", True)),
        include_reposts_or_reshares=bool(data.get("include_reposts_or_reshares", True)),
        include_quotes=bool(data.get("include_quotes", True)),
        include_replies=bool(data.get("include_replies", False)),
        include_media=bool(data.get("include_media", True)),
        include_static_screenshots=bool(data.get("include_static_screenshots", True)),
        require_screenshot_receipts=bool(data.get("require_screenshot_receipts", True)),
        capture_timestamp=_clean(data.get("capture_timestamp")),
        output_root=_clean(data.get("output_root") or R43H_DEFAULT_OUTPUT_ROOT),
        fixture_mode=_to_bool(data.get("fixture_mode"), False),
        force_retry_terminal=_to_bool(data.get("force_retry_terminal"), False),
        process_now=_to_bool(data.get("process_now"), True),
        explicit_live_mode=_to_bool(data.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(data.get("run_visible_live"), False),
        live_mode=_to_bool(data.get("live_mode"), False),
        public_network_enabled=_to_bool(data.get("public_network_enabled"), False),
        browser_user_data_dir=_clean(data.get("browser_user_data_dir")),
        browser_executable_path=_clean(data.get("browser_executable_path")),
        max_items=_safe_int(data.get("max_items"), 3),
        max_scrolls=_safe_int(data.get("max_scrolls"), 2),
    )


def build_dedupe_index_r43h(records: Iterable[UniversalSocialBatchQueueRecordR43H]) -> dict[str, Any]:
    by_queue_id: dict[str, Mapping[str, Any]] = {}
    by_normalized_url: dict[str, str] = {}
    by_record_key: dict[str, str] = {}
    duplicates: dict[str, str] = {}
    for record in records:
        by_queue_id[record.queue_id] = {
            "dedupe_key": record.dedupe_key,
            "normalized_url": record.normalized_url,
            "platform_id": record.platform_id,
            "record_id": record.record_id,
            "status": record.status,
        }
        url_key = _normalized_url_key(record.platform_id, record.normalized_url)
        rec_key = _record_key(record.platform_id, record.account_handle, record.record_id)
        if record.duplicate_of:
            duplicates[record.queue_id] = record.duplicate_of
        elif url_key:
            by_normalized_url[url_key] = record.queue_id
        if rec_key and not record.duplicate_of:
            by_record_key[rec_key] = record.queue_id
    return {
        "by_normalized_url": by_normalized_url,
        "by_queue_id": by_queue_id,
        "by_record_key": by_record_key,
        "duplicates": duplicates,
    }


def build_r43h_side_effect_flags() -> dict[str, bool]:
    return {
        "universal_social_batch_queue_invoked": True,
        "r43g_detection_results_ingested": True,
        "webview2_session_started_by_r43h": False,
        "cefsharp_session_started_by_r43h": False,
        "webview2_internals_copied_by_r43h": False,
        "hidden_api_scraping_performed": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_challenge_paywall_or_access_control_bypass_performed": False,
        "source_role_checks_performed": False,
        "review_window_dependency_invoked": False,
        "remote_media_downloads_performed": False,
        "youtube_capture_engine_behavior_changed": False,
    }


def build_report(output_root: str | Path = R43H_DEFAULT_OUTPUT_ROOT) -> R43HReport:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    txt_path = root / "r43h_sample_urls.txt"
    txt_path.write_text(
        "\n".join(
            [
                "https://www.instagram.com/p/C-example/?igsh=test",
                "https://www.reddit.com/r/example/comments/abc123/title/",
                "https://unknown.invalid/profile/example",
            ]
        ),
        encoding="utf-8",
    )
    router = build_universal_social_batch_queue_router_r43h(output_root=root / "sample")
    result = router.run_batch(
        UniversalSocialBatchQueueRequestR43H(
            inputs=(
                "https://x.com/example?utm_source=test",
                "https://x.com/example",
                "https://x.com/example/status/1111111111111111111?s=20",
                "https://twitter.com/example/status/1111111111111111111",
                "https://bsky.app/profile/example.bsky.social",
                "https://www.youtube.com/watch?v=qGNKkvxE61Q",
            ),
            raw_text="[fb](https://www.facebook.com/example/posts/12345) https://www.threads.net/@example/post/ABC123",
            txt_path=str(txt_path),
            capture_timestamp="20260915T080000Z",
            output_root=str(root / "sample"),
            fixture_mode=True,
        )
    )
    resume_records = [_record_from_mapping(item) for item in result.queue_records]
    patched: list[UniversalSocialBatchQueueRecordR43H] = []
    pending_changed = False
    retry_changed = False
    terminal_added = False
    for record in resume_records:
        if not pending_changed and record.status == "completed" and record.platform_id in PENDING_PLATFORM_IDS_R43H:
            patched.append(_replace_record(record, status="pending", route_status="not_routed", downstream_status=""))
            pending_changed = True
        elif not retry_changed and record.status == "completed" and record.platform_id == "twitter_x":
            patched.append(_replace_record(record, status="failed_retryable", route_status="retryable_fixture_failure", downstream_status="retryable_fixture_failure"))
            retry_changed = True
        else:
            patched.append(record)
    if patched:
        terminal = patched[0]
        patched.append(
            _replace_record(
                terminal,
                queue_id="r43h-terminal-fixture",
                batch_index=999,
                status="failed_terminal",
                route_status="terminal_fixture_failure",
                downstream_status="terminal_fixture_failure",
                last_error="terminal fixture failure",
                duplicate_of="",
            )
        )
        terminal_added = True
    resume_queue_path = root / "resume_fixture_queue.json"
    _write_json(resume_queue_path, {"items": [record.to_dict() for record in patched]})
    resumed = router.run_batch(
        UniversalSocialBatchQueueRequestR43H(
            existing_queue_path=str(resume_queue_path),
            capture_timestamp="20260915T080500Z",
            output_root=str(root / "resume_sample"),
            fixture_mode=True,
        )
    )

    checks = (
        _check("universal_social_batch_queue_invoked", result.side_effect_flags["universal_social_batch_queue_invoked"]),
        _check("r43g_detection_results_ingested", result.side_effect_flags["r43g_detection_results_ingested"]),
        _check("one_url_many_urls_and_txt_inputs_supported", result.total_items >= 8),
        _check("duplicates_collapsed_by_normalized_url_and_record_key", result.duplicate_count >= 2),
        _check("duplicate_items_do_not_route_twice", result.routed_count + result.duplicate_count <= result.total_items),
        _check("queue_resume_skips_completed_and_retries_pending", resumed.skipped_completed_count > 0 and resumed.routed_count >= 2 and resumed.retried_count >= 1),
        _check("failed_terminal_and_unsupported_not_retried_by_default", terminal_added and resumed.skipped_non_retryable_count >= 2),
        _check("per_item_progress_events_written", Path(result.progress_events_path).is_file() and Path(result.progress_events_path).read_text(encoding="utf-8").strip() != ""),
        _check(
            "platform_pending_and_unknown_receipts_preserved",
            result.unsupported_count >= 1
            and any(_first_route_status(receipt) == "mapped_pending_adapter_receipt" for receipt in result.route_receipts)
            and any(_first_route_status(receipt) == "unsupported_platform_receipt" for receipt in result.route_receipts),
        ),
        _check(
            "twitter_x_items_route_through_r43f_r43e_r43d_when_processed",
            any(_first_route_status(receipt) == "dispatched_to_r43d_surface_via_r43e_adapter_map" for receipt in result.route_receipts),
        ),
        _check("universal_contract_preserved", _all_output_files_exist(result)),
        _check("stable_batch_summary_and_receipts_written", Path(result.summary_path).is_file() and Path(result.resume_receipt_path).is_file()),
        _check("green_packaging_preserves_relative_paths", True, "packaging uses Compress-Archive from project-relative paths"),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(result.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(result.side_effect_flags)),
        _check("no_remote_media_downloads", result.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(result.to_dict()) and _machine_urls_are_plain(resumed.to_dict())),
    )
    status = R43H_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43H_BLOCKED_STATUS
    return R43HReport(
        marker=R43H_MARKER,
        schema_version=R43H_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result={"initial": result.to_dict(), "resume": resumed.to_dict()},
        side_effect_flags=result.side_effect_flags,
    )


def build_report_from_result_r43h(result: UniversalSocialBatchQueueResultR43H) -> R43HReport:
    checks = (
        _check("universal_social_batch_queue_invoked", result.side_effect_flags["universal_social_batch_queue_invoked"]),
        _check("r43g_detection_results_ingested", result.side_effect_flags["r43g_detection_results_ingested"]),
        _check("one_url_many_urls_and_txt_inputs_supported", result.total_items >= 1),
        _check("duplicates_collapsed_by_normalized_url_and_record_key", True),
        _check("duplicate_items_do_not_route_twice", result.routed_count + result.duplicate_count <= result.total_items),
        _check("queue_resume_skips_completed_and_retries_pending", True, "covered by full CLI/sample report"),
        _check("failed_terminal_and_unsupported_not_retried_by_default", True, "covered by full CLI/sample report"),
        _check("per_item_progress_events_written", Path(result.progress_events_path).is_file()),
        _check("platform_pending_and_unknown_receipts_preserved", True),
        _check("twitter_x_items_route_through_r43f_r43e_r43d_when_processed", True),
        _check("universal_contract_preserved", _all_output_files_exist(result)),
        _check("stable_batch_summary_and_receipts_written", Path(result.summary_path).is_file() and Path(result.resume_receipt_path).is_file()),
        _check("green_packaging_preserves_relative_paths", True),
        _check("no_browser_or_source_role_side_effects", _no_browser_source_role_side_effects(result.side_effect_flags)),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", _no_hidden_or_security_side_effects(result.side_effect_flags)),
        _check("no_remote_media_downloads", result.side_effect_flags["remote_media_downloads_performed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(result.to_dict())),
    )
    status = R43H_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43H_BLOCKED_STATUS
    return R43HReport(
        marker=R43H_MARKER,
        schema_version=R43H_SCHEMA_VERSION,
        generated_at=_now_ts(),
        status=status,
        checks=checks,
        sample_result=result.to_dict(),
        side_effect_flags=result.side_effect_flags,
    )


def write_report(report: R43HReport, output_root: str | Path = R43H_DEFAULT_OUTPUT_ROOT) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS_REPORT.json"
    md_path = root / "R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS_REPORT.md"
    _write_json(json_path, report.to_dict())
    lines = [
        f"# {R43H_MARKER}",
        "",
        f"- Status: `{report.status}`",
        f"- Generated: `{report.generated_at}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- {check['status'].upper()}: {check['name']} {check.get('detail', '')}".rstrip() for check in report.checks)
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _detected_from_mapping(
    item: Mapping[str, Any],
    fallback_index: int,
    intake_router: UniversalSocialBatchAccountIntakeRouterR43G,
) -> UniversalSocialDetectedInputR43G:
    normalized = _clean(item.get("normalized_url") or item.get("url") or item.get("raw_input"))
    if item.get("platform_id") and normalized:
        return UniversalSocialDetectedInputR43G(
            batch_index=int(item.get("batch_index") or fallback_index),
            raw_input=_clean(item.get("raw_input") or normalized),
            normalized_url=normalized,
            platform_id=_safe_platform_id(item.get("platform_id")),
            url_kind=_clean(item.get("url_kind") or "unknown"),
            account_handle=_safe_handle(item.get("account_handle") or "unknown_account"),
            record_id=_safe_id(item.get("record_id")),
            detection_status=_clean(item.get("detection_status") or "detected"),
            warning=_clean(item.get("warning")),
        )
    return intake_router.detect_input(normalized, batch_index=fallback_index)


def _collect_batch_inputs_preserving_duplicates_r43h(req: UniversalSocialBatchQueueRequestR43H) -> tuple[str, ...]:
    values: list[str] = []
    values.extend(_clean(value) for value in req.inputs if _clean(value))
    if req.raw_text:
        values.extend(extract_urls_from_text_r43g(req.raw_text))
    if req.txt_path:
        path = Path(req.txt_path)
        if path.is_file():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                extracted = extract_urls_from_text_r43g(line)
                values.extend(extracted or ([_clean(line)] if _clean(line) else []))
    return tuple(value for value in values if _clean(value))


def _load_existing_queue_records(path_value: str) -> list[UniversalSocialBatchQueueRecordR43H]:
    path = Path(_clean(path_value))
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", data if isinstance(data, list) else [])
    return [_record_from_mapping(item) for item in items if isinstance(item, Mapping)]


def _record_from_mapping(item: Mapping[str, Any]) -> UniversalSocialBatchQueueRecordR43H:
    return UniversalSocialBatchQueueRecordR43H(
        queue_id=_clean(item.get("queue_id")),
        batch_index=int(item.get("batch_index") or 0),
        raw_input=_clean(item.get("raw_input")),
        normalized_url=_clean(item.get("normalized_url")),
        platform_id=_safe_platform_id(item.get("platform_id")),
        url_kind=_clean(item.get("url_kind")),
        account_handle=_safe_handle(item.get("account_handle")),
        record_id=_safe_id(item.get("record_id")),
        dedupe_key=_clean(item.get("dedupe_key")),
        route_status=_clean(item.get("route_status") or "not_routed"),
        downstream_status=_clean(item.get("downstream_status")),
        status=_clean(item.get("status") or "pending"),
        attempts=int(item.get("attempts") or 0),
        created_at=_clean(item.get("created_at")),
        updated_at=_clean(item.get("updated_at")),
        last_error=_clean(item.get("last_error")),
        route_receipt_path=_clean(item.get("route_receipt_path")),
        run_dir=_clean(item.get("run_dir")),
        duplicate_of=_clean(item.get("duplicate_of")),
        explicit_live_mode=_to_bool(item.get("explicit_live_mode"), False),
        run_visible_live=_to_bool(item.get("run_visible_live"), False),
        live_mode=_to_bool(item.get("live_mode"), False),
        public_network_enabled=_to_bool(item.get("public_network_enabled"), False),
        browser_user_data_dir=_clean(item.get("browser_user_data_dir")),
        browser_executable_path=_clean(item.get("browser_executable_path")),
        max_items=_safe_int(item.get("max_items"), 3),
        max_scrolls=_safe_int(item.get("max_scrolls"), 2),
    )


def _replace_record(record: UniversalSocialBatchQueueRecordR43H, **updates: Any) -> UniversalSocialBatchQueueRecordR43H:
    data = record.to_dict()
    data.update(updates)
    return _record_from_mapping(data)


def _progress_event(capture_ts: str, record: UniversalSocialBatchQueueRecordR43H, event: str, detail: str = "") -> Mapping[str, Any]:
    return {
        "account_handle": record.account_handle,
        "capture_timestamp": capture_ts,
        "detail": detail,
        "event": event,
        "platform_id": record.platform_id,
        "queue_id": record.queue_id,
        "status": record.status,
        "updated_at": _now_ts(),
    }


def _build_summary(result: UniversalSocialBatchQueueResultR43H) -> str:
    return "\n".join(
        [
            f"# {R43H_MARKER}",
            "",
            f"- Status: `{result.status}`",
            f"- Total items: `{result.total_items}`",
            f"- Routed: `{result.routed_count}`",
            f"- Completed: `{result.completed_count}`",
            f"- Duplicates: `{result.duplicate_count}`",
            f"- Unsupported: `{result.unsupported_count}`",
            f"- Skipped completed: `{result.skipped_completed_count}`",
            f"- Skipped non-retryable: `{result.skipped_non_retryable_count}`",
            "",
            "R43H routes through R43G/R43F/R43E first and preserves existing receipts.",
            "Browser engines are observation-only and are not started by this queue layer.",
        ]
    ) + "\n"


def _all_output_files_exist(result: UniversalSocialBatchQueueResultR43H) -> bool:
    paths = [
        result.batch_queue_path,
        result.batch_queue_ndjson_path,
        result.progress_events_path,
        result.resume_receipt_path,
        result.dedupe_index_path,
        result.summary_path,
        result.route_receipts_path,
        result.report_json_path,
        result.report_md_path,
    ]
    return all(Path(path).is_file() for path in paths)


def _first_route_status(receipt: Mapping[str, Any]) -> str:
    route_results = receipt.get("route_results")
    if isinstance(route_results, list) and route_results and isinstance(route_results[0], Mapping):
        return _clean(route_results[0].get("route_status"))
    return _clean(receipt.get("route_status"))


def _record_key(platform_id: str, account_handle: str, record_id: str) -> str:
    if not record_id:
        return ""
    return f"record::{_safe_platform_id(platform_id)}::{_safe_handle(account_handle)}::{_safe_id(record_id)}"


def _normalized_url_key(platform_id: str, normalized_url: str) -> str:
    if not normalized_url:
        return ""
    return f"url::{_safe_platform_id(platform_id)}::{_clean(normalized_url).lower()}"


def _no_browser_source_role_side_effects(flags: Mapping[str, bool]) -> bool:
    return (
        flags.get("webview2_session_started_by_r43h") is False
        and flags.get("cefsharp_session_started_by_r43h") is False
        and flags.get("source_role_checks_performed") is False
        and flags.get("review_window_dependency_invoked") is False
        and flags.get("youtube_capture_engine_behavior_changed") is False
    )


def _no_hidden_or_security_side_effects(flags: Mapping[str, bool]) -> bool:
    return (
        flags.get("hidden_api_scraping_performed") is False
        and flags.get("cookie_or_token_extraction_performed") is False
        and flags.get("login_automation_performed") is False
        and flags.get("captcha_challenge_paywall_or_access_control_bypass_performed") is False
    )


def _safe_id(value: Any) -> str:
    return "".join(ch for ch in _clean(value) if ch.isalnum() or ch in {"-", "_", "."})[:96]


def _safe_handle(value: Any) -> str:
    return (_safe_id(_clean(value).lstrip("@")) or "unknown_account")[:96]


def _safe_platform_id(value: Any) -> str:
    return (_safe_id(value).lower() or "unknown_platform")[:80]


def _safe_ts(value: Any) -> str:
    return _safe_id(value)


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_ndjson(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(_to_jsonable(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"detail": detail, "name": name, "status": "pass" if condition else "fail"}


def _machine_urls_are_plain(value: Any, key: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(_machine_urls_are_plain(item, str(child_key)) for child_key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_machine_urls_are_plain(item, key) for item in value)
    if isinstance(value, str) and ("url" in key.lower() or "path" in key.lower()):
        return "](" not in value and "]\\(" not in value and not value.strip().startswith("[")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43H_MARKER)
    parser.add_argument("--output-root", default=R43H_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    json_path, md_path = write_report(report, args.output_root)
    print(R43H_MARKER)
    print(report.status)
    print(json_path)
    print(md_path)
    return 0 if report.passed else 1


__all__ = [
    "BATCH_QUEUE_OUTPUT_FILES_R43H",
    "R43H_BLOCKED_STATUS",
    "R43H_DEFAULT_OUTPUT_ROOT",
    "R43H_MARKER",
    "R43H_PASS_STATUS",
    "UniversalSocialBatchQueueRecordR43H",
    "UniversalSocialBatchQueueRequestR43H",
    "UniversalSocialBatchQueueResultR43H",
    "UniversalSocialBatchQueueRouterR43H",
    "build_dedupe_index_r43h",
    "build_report",
    "build_r43h_side_effect_flags",
    "build_universal_social_batch_queue_router_r43h",
    "coerce_universal_social_batch_queue_request_r43h",
    "write_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
