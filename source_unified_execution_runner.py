from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from source_archive_execution_bridge import (
    ArchiveHttpResult,
    build_wayback_availability_request,
    execute_archive_http_request,
)
from source_local_browser_execution import (
    LocalBrowserExecutionResult,
    run_local_fixture_browser_execution,
)
from source_media_execution_bridge import (
    MediaCollisionPolicy,
    SelectedMediaExecutionQueue,
    copy_selected_local_media_files,
)
from source_offline_bundle_writer import (
    OfflineEvidenceBundleWriteResult,
    write_offline_evidence_bundle,
)
from source_operator_approval_gateway import (
    OperatorApprovalDecision,
    OperatorApprovalStatus,
    OperatorApprovalToken,
    OperatorExecutionAction,
    OperatorExecutionScope,
    evaluate_operator_approval,
)


SOURCE_UNIFIED_EXECUTION_RUNNER_SCHEMA_VERSION = "source_unified_execution_runner_v1"


class UnifiedExecutionJobStatus(str, Enum):
    PREVIEW_ONLY = "preview_only"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"


class UnifiedExecutionProgressStatus(str, Enum):
    STARTED = "started"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(_value_for_dict(value), sort_keys=True, separators=(",", ":"))


def _sha16(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:16]


def _safe_names(paths: Sequence[str | Path]) -> tuple[str, ...]:
    return tuple(Path(path).name for path in paths if str(path))


@dataclass(frozen=True)
class UnifiedExecutionProgressEvent:
    step: str
    status: UnifiedExecutionProgressStatus
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class UnifiedExecutionJobOptions:
    run_browser_capture: bool = False
    run_media_copy: bool = False
    run_archive_check: bool = False
    write_offline_bundle: bool = False
    selected_media_resource_ids: tuple[str, ...] = ()
    element_selector: str = ""
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class UnifiedExecutionJobResult:
    job_id: str
    status: UnifiedExecutionJobStatus
    source_url: str
    requested_actions: tuple[OperatorExecutionAction, ...]
    approval_decisions: tuple[OperatorApprovalDecision, ...]
    progress_events: tuple[UnifiedExecutionProgressEvent, ...]
    browser_result: LocalBrowserExecutionResult | None = None
    media_copy_queue: SelectedMediaExecutionQueue | None = None
    archive_result: ArchiveHttpResult | None = None
    offline_bundle_result: OfflineEvidenceBundleWriteResult | None = None
    artifact_names: tuple[str, ...] = ()
    artifact_hashes: tuple[tuple[str, str], ...] = ()
    behavior_event_labels: tuple[str, ...] = ()
    failure_receipts: tuple[str, ...] = ()
    redaction_applied: bool = True
    external_network_performed: bool = False
    browser_live_site_performed: bool = False
    archive_provider_real_call_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    asr_job_run: bool = False
    schema_version: str = SOURCE_UNIFIED_EXECUTION_RUNNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["progress_event_count"] = len(self.progress_events)
        data["artifact_count"] = len(self.artifact_names)
        data["failure_receipt_count"] = len(self.failure_receipts)
        return data


HttpClient = Callable[[Any], Mapping[str, Any]]


def _actions_from_options(options: UnifiedExecutionJobOptions) -> tuple[OperatorExecutionAction, ...]:
    actions: list[OperatorExecutionAction] = []
    if options.run_browser_capture:
        actions.extend(
            (
                OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
                OperatorExecutionAction.SCREENSHOT_CAPTURE,
                OperatorExecutionAction.ARTICLE_CAPTURE,
                OperatorExecutionAction.PAGE_OUTLINE_CAPTURE,
                OperatorExecutionAction.COMMENTS_CAPTURE,
                OperatorExecutionAction.LIVECHAT_CAPTURE,
            )
        )
    if options.run_media_copy:
        actions.append(OperatorExecutionAction.MEDIA_DOWNLOAD_COPY)
    if options.run_archive_check:
        actions.append(OperatorExecutionAction.ARCHIVE_CHECK)
    if options.write_offline_bundle:
        actions.append(OperatorExecutionAction.OFFLINE_BUNDLE_WRITE)
    return tuple(sorted(set(actions), key=lambda item: item.value))


def run_unified_local_execution_job(
    *,
    source_url: str,
    fixture_html: str,
    output_directory: str | Path,
    options: UnifiedExecutionJobOptions,
    approval_token: OperatorApprovalToken | None = None,
    media_resources: Sequence[Mapping[str, Any]] = (),
    archive_http_client: HttpClient | None = None,
) -> UnifiedExecutionJobResult:
    output_root = Path(output_directory)
    actions = _actions_from_options(options)
    decisions = tuple(
        evaluate_operator_approval(
            action,
            token=approval_token,
            requested_scope=OperatorExecutionScope.LOCAL_TEMP,
        )
        for action in actions
    )
    progress: list[UnifiedExecutionProgressEvent] = [
        UnifiedExecutionProgressEvent("job", UnifiedExecutionProgressStatus.STARTED, "operator execution job started")
    ]
    if options.cancel_requested:
        progress.append(UnifiedExecutionProgressEvent("job", UnifiedExecutionProgressStatus.CANCELLED, "operator cancellation requested"))
        return UnifiedExecutionJobResult(
            job_id="unified_execution_job_" + _sha16((source_url, options.to_dict(), "cancelled")),
            status=UnifiedExecutionJobStatus.CANCELLED,
            source_url=source_url,
            requested_actions=actions,
            approval_decisions=decisions,
            progress_events=tuple(progress),
            failure_receipts=("operator_cancelled",),
        )
    blocked = [decision for decision in decisions if not decision.allowed_to_execute]
    if blocked:
        progress.append(UnifiedExecutionProgressEvent("gateway", UnifiedExecutionProgressStatus.BLOCKED, "one or more requested actions lack approval"))
        return UnifiedExecutionJobResult(
            job_id="unified_execution_job_" + _sha16((source_url, options.to_dict(), [item.to_dict() for item in decisions])),
            status=UnifiedExecutionJobStatus.BLOCKED,
            source_url=source_url,
            requested_actions=actions,
            approval_decisions=decisions,
            progress_events=tuple(progress),
            failure_receipts=tuple(reason for decision in blocked for reason in decision.reasons),
        )

    browser_result: LocalBrowserExecutionResult | None = None
    media_queue: SelectedMediaExecutionQueue | None = None
    archive_result: ArchiveHttpResult | None = None
    offline_bundle_result: OfflineEvidenceBundleWriteResult | None = None
    behavior_events: list[str] = ["source_url_entered"]
    artifact_names: list[str] = []
    artifact_hashes: list[tuple[str, str]] = []

    output_root.mkdir(parents=True, exist_ok=True)
    if options.run_browser_capture:
        browser_result = run_local_fixture_browser_execution(
            html=fixture_html,
            output_directory=output_root / "browser",
            source_url=source_url,
            element_selector=options.element_selector,
        )
        progress.append(UnifiedExecutionProgressEvent("browser", UnifiedExecutionProgressStatus.COMPLETED, browser_result.status.value))
        behavior_events.extend(("browser_local_capture_started", "article_capture_completed", "screenshot_capture_completed", "comments_livechat_capture_completed"))
        if browser_result.rendered_dom_filename:
            artifact_names.append(browser_result.rendered_dom_filename)
            artifact_hashes.append((browser_result.rendered_dom_filename, browser_result.rendered_dom_sha256))
        for screenshot in browser_result.screenshots:
            artifact_names.append(screenshot.filename)
            artifact_hashes.append((screenshot.filename, screenshot.sha256))

    if options.run_media_copy:
        media_queue = copy_selected_local_media_files(
            resources=media_resources,
            output_directory=output_root / "media",
            selected_resource_ids=options.selected_media_resource_ids,
            collision_policy=MediaCollisionPolicy.KEEP_BOTH,
        )
        progress.append(UnifiedExecutionProgressEvent("media_copy", UnifiedExecutionProgressStatus.COMPLETED, media_queue.status.value))
        behavior_events.append("media_selected_downloaded")
        for receipt in media_queue.local_copy_receipts:
            if receipt.output_name:
                artifact_names.append(receipt.output_name)
                artifact_hashes.append((receipt.output_name, receipt.sha256))

    if options.run_archive_check:
        if archive_http_client is None:
            archive_http_client = lambda request: {"status": 200, "body": "{}", "archive_url": ""}
        archive_result = execute_archive_http_request(
            build_wayback_availability_request(source_url),
            http_client=archive_http_client,
        )
        progress.append(UnifiedExecutionProgressEvent("archive_check", UnifiedExecutionProgressStatus.COMPLETED, archive_result.status.value))
        behavior_events.append("archive_check_requested")

    if options.write_offline_bundle:
        article_text = browser_result.article.text if browser_result and browser_result.article else ""
        outline_text = "\n".join(browser_result.page_outline.outline_lines) if browser_result and browser_result.page_outline else ""
        html_snapshot = fixture_html
        comments = tuple(comment.to_dict() for comment in browser_result.comments.comments) if browser_result and browser_result.comments else ()
        livechat = tuple(event.to_dict() for event in browser_result.livechat.events) if browser_result and browser_result.livechat else ()
        selected_media_metadata = tuple(receipt.to_dict() for receipt in media_queue.local_copy_receipts) if media_queue else ()
        archive_results = (archive_result.to_dict(),) if archive_result else ()
        screenshot_paths = tuple((output_root / "browser" / name) for name in _safe_names(artifact_names) if name.endswith(".png"))
        offline_bundle_result = write_offline_evidence_bundle(
            output_zip_path=output_root / "offline_bundle.zip",
            source_url=source_url,
            source_label="Local fixture source",
            article_text=article_text,
            page_outline_text=outline_text,
            html_snapshot=html_snapshot,
            comments=comments,
            livechat=livechat,
            selected_media_metadata=selected_media_metadata,
            archive_results=archive_results,
            screenshot_paths=screenshot_paths,
        )
        progress.append(UnifiedExecutionProgressEvent("offline_bundle", UnifiedExecutionProgressStatus.COMPLETED, offline_bundle_result.status.value))
        behavior_events.append("offline_bundle_written")
        artifact_names.append(offline_bundle_result.output_name)
        artifact_hashes.append((offline_bundle_result.output_name, offline_bundle_result.sha256))

    payload = (
        source_url,
        options.to_dict(),
        [decision.to_dict() for decision in decisions],
        artifact_hashes,
    )
    return UnifiedExecutionJobResult(
        job_id="unified_execution_job_" + _sha16(payload),
        status=UnifiedExecutionJobStatus.COMPLETED,
        source_url=source_url,
        requested_actions=actions,
        approval_decisions=decisions,
        progress_events=tuple(progress),
        browser_result=browser_result,
        media_copy_queue=media_queue,
        archive_result=archive_result,
        offline_bundle_result=offline_bundle_result,
        artifact_names=tuple(artifact_names),
        artifact_hashes=tuple(artifact_hashes),
        behavior_event_labels=tuple(behavior_events),
    )


def unified_execution_job_result_to_json(result: UnifiedExecutionJobResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)
