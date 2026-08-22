from __future__ import annotations

"""Queued runtime bridge for Profile/Media Database file operations.

V80N: JDownloader/AppWork-style file/database operation queue bridge.

Source patterns reviewed from the uploaded JDownloader/AppWork reference set:
- org.appwork.utils.event.queue.Queue / QueueAction / QueueThread
- jd.controlling.downloadcontroller.DownloadWatchDogJob
- jd.controlling.downloadcontroller.DownloadWatchDog

Python/YTCE implementation notes:
- Profile/Media Database file-management actions are wrapped as named queue jobs;
- dry-run/review jobs use stable supersede keys so stale GUI refreshes are skipped;
- apply/execute jobs are not superseded by default, matching the safer watchdog/job model;
- callable failures are isolated by YTCEWorkQueue and converted into reviewable result payloads;
- convenience methods lazily import Profile/Media modules so this bridge remains lightweight at startup.

This module is a native Python implementation of the same queue/job/watchdog roles,
with explicit provenance labels retained for the JDownloader/AppWork source patterns.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping
from uuid import uuid4
import time

from ytce_app_work_queue import (
    YTCEQueuePriority,
    YTCEWorkItem,
    YTCEWorkQueue,
    YTCEWorkResult,
    YTCEWorkStatus,
)

PROFILE_MEDIA_DATABASE_RUNTIME_QUEUE_SCHEMA_VERSION = "profile-media-database-runtime-queue-v80n"


def _utc_now_iso() -> str:
    try:
        from profile_media_database import utc_now_iso

        return str(utc_now_iso())
    except Exception:
        import datetime as _dt

        return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coerce_priority(value: YTCEQueuePriority | str | None) -> YTCEQueuePriority:
    if value is None:
        return YTCEQueuePriority.NORM
    if isinstance(value, YTCEQueuePriority):
        return value
    return YTCEQueuePriority[str(value).strip().upper()]


def _payload_to_dict(payload: Any) -> Any:
    if hasattr(payload, "to_dict") and callable(getattr(payload, "to_dict")):
        try:
            return payload.to_dict()
        except Exception:
            pass
    if dataclass_is_instance(payload):
        try:
            return asdict(payload)
        except Exception:
            pass
    return payload


def dataclass_is_instance(value: Any) -> bool:
    return hasattr(value, "__dataclass_fields__") and not isinstance(value, type)


@dataclass(frozen=True, slots=True)
class ProfileMediaQueuedOperationTicket:
    """Returned immediately when a Profile/Media operation is queued."""

    operation_id: str
    label: str
    operation_kind: str
    work_id: str
    supersede_key: str = ""
    priority: str = "NORM"
    queued_at_utc: str = field(default_factory=_utc_now_iso)
    schema_version: str = PROFILE_MEDIA_DATABASE_RUNTIME_QUEUE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProfileMediaQueuedOperationResult:
    """Reviewable result converted from a queued Profile/Media operation."""

    operation_id: str
    label: str
    operation_kind: str
    status: str
    work_id: str
    work_status: str
    payload: Any = None
    error_text: str = ""
    supersede_key: str = ""
    queue_wait_seconds: float | None = None
    run_seconds: float | None = None
    created_at_utc: str = field(default_factory=_utc_now_iso)
    schema_version: str = PROFILE_MEDIA_DATABASE_RUNTIME_QUEUE_SCHEMA_VERSION
    source_pattern: str = "JDownloader/AppWork QueueAction + DownloadWatchDogJob-style operation"

    def ok(self) -> bool:
        return self.status == "finished"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProfileMediaDatabaseRuntimeQueue:
    """Queue bridge for guarded Profile/Media file/database operations.

    The existing Profile/Media modules already implement the safety model: dry-run first,
    explicit confirmations, no folder scans unless stated, and reviewed operation plans.
    This bridge adds the live-runtime layer: jobs are named, queued, superseded where
    safe, and converted to uniform result payloads.
    """

    def __init__(
        self,
        queue: YTCEWorkQueue | None = None,
        *,
        queue_id: str = "profile.media.database.runtime",
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.queue = queue or YTCEWorkQueue(queue_id=queue_id, logger=logger)
        self._logger = logger
        self._tickets_by_work_id: dict[str, ProfileMediaQueuedOperationTicket] = {}
        self._results_by_work_id: dict[str, ProfileMediaQueuedOperationResult] = {}

    def submit_operation(
        self,
        *,
        label: str,
        operation_kind: str,
        func: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: Mapping[str, Any] | None = None,
        priority: YTCEQueuePriority | str | None = YTCEQueuePriority.NORM,
        supersede_key: str | None = None,
        on_done: Callable[[ProfileMediaQueuedOperationResult], None] | None = None,
    ) -> ProfileMediaQueuedOperationTicket:
        """Submit a named operation and return a ticket immediately.

        Review/build operations should pass a supersede_key so repeated GUI refreshes do
        not keep stale work. Confirmed apply operations should normally leave
        supersede_key empty so execution requests are never silently replaced.
        """

        operation_id = f"pmd.op.{uuid4().hex[:12]}"
        priority_value = _coerce_priority(priority)
        call_kwargs = dict(kwargs or {})

        def _run_operation() -> Any:
            return func(*args, **call_kwargs)

        def _remember_result(work_result: YTCEWorkResult) -> None:
            converted = self._convert_result(operation_id, operation_kind, work_result)
            self._results_by_work_id[work_result.work_id] = converted
            if on_done is not None:
                try:
                    on_done(converted)
                except Exception as exc:
                    self._log(f"Profile/Media queued callback isolated: {label}: {exc!r}")

        item = self.queue.add(
            label,
            _run_operation,
            priority=priority_value,
            supersede_key=supersede_key,
            on_done=_remember_result,
        )
        ticket = ProfileMediaQueuedOperationTicket(
            operation_id=operation_id,
            label=label,
            operation_kind=operation_kind,
            work_id=item.work_id,
            supersede_key=supersede_key or "",
            priority=priority_value.name,
        )
        self._tickets_by_work_id[item.work_id] = ticket
        return ticket

    def run_operation_wait(
        self,
        *,
        label: str,
        operation_kind: str,
        func: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: Mapping[str, Any] | None = None,
        priority: YTCEQueuePriority | str | None = YTCEQueuePriority.NORM,
        supersede_key: str | None = None,
        timeout: float | None = None,
    ) -> ProfileMediaQueuedOperationResult:
        """Run an operation through the queue and wait for a uniform result payload."""

        operation_id = f"pmd.op.{uuid4().hex[:12]}"
        priority_value = _coerce_priority(priority)
        call_kwargs = dict(kwargs or {})

        def _run_operation() -> Any:
            return func(*args, **call_kwargs)

        start = time.monotonic()
        try:
            payload = self.queue.add_wait(
                label,
                _run_operation,
                priority=priority_value,
                supersede_key=supersede_key,
                timeout=timeout,
                raise_on_error=True,
            )
            elapsed = max(0.0, time.monotonic() - start)
            return ProfileMediaQueuedOperationResult(
                operation_id=operation_id,
                label=label,
                operation_kind=operation_kind,
                status="finished",
                work_id="wait-inline-or-queued",
                work_status=YTCEWorkStatus.FINISHED.value,
                payload=_payload_to_dict(payload),
                supersede_key=supersede_key or "",
                run_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = max(0.0, time.monotonic() - start)
            return ProfileMediaQueuedOperationResult(
                operation_id=operation_id,
                label=label,
                operation_kind=operation_kind,
                status="failed",
                work_id="wait-inline-or-queued",
                work_status=YTCEWorkStatus.FAILED.value,
                error_text=f"{type(exc).__name__}: {exc}",
                supersede_key=supersede_key or "",
                run_seconds=elapsed,
            )

    def build_materialize_plan_async(
        self,
        *,
        database_root: str,
        batch_json_files: Any,
        execute: bool = False,
        confirmation_phrase: str = "",
        on_done: Callable[[ProfileMediaQueuedOperationResult], None] | None = None,
    ) -> ProfileMediaQueuedOperationTicket:
        def _work() -> Any:
            from profile_media_database_materialize_workflow import build_database_materialize_plan

            return build_database_materialize_plan(
                database_root=database_root,
                batch_json_files=batch_json_files,
                execute=execute,
                confirmation_phrase=confirmation_phrase,
            )

        return self.submit_operation(
            label="Build Profile/Media materialize plan",
            operation_kind="build_materialize_plan",
            func=_work,
            priority=YTCEQueuePriority.NORM,
            supersede_key=f"pmd.materialize.review:{database_root}",
            on_done=on_done,
        )

    def apply_materialize_plan_async(
        self,
        plan: Any,
        *,
        on_done: Callable[[ProfileMediaQueuedOperationResult], None] | None = None,
    ) -> ProfileMediaQueuedOperationTicket:
        def _work() -> Any:
            from profile_media_database_materialize_workflow import apply_database_materialize_plan

            return apply_database_materialize_plan(plan)

        return self.submit_operation(
            label="Apply Profile/Media materialize plan",
            operation_kind="apply_materialize_plan",
            func=_work,
            priority=YTCEQueuePriority.HIGH,
            supersede_key=None,
            on_done=on_done,
        )

    def build_folder_operations_plan_async(
        self,
        *,
        database_root: str,
        operations_payload: Mapping[str, Any] | None = None,
        operations_json_path: str | None = None,
        execute: bool = False,
        confirmation_phrase: str = "",
        on_done: Callable[[ProfileMediaQueuedOperationResult], None] | None = None,
    ) -> ProfileMediaQueuedOperationTicket:
        def _work() -> Any:
            from profile_media_database_folder_operations import build_folder_operations_plan

            return build_folder_operations_plan(
                database_root=database_root,
                operations_payload=operations_payload,
                operations_json_path=operations_json_path,
                execute=execute,
                confirmation_phrase=confirmation_phrase,
            )

        return self.submit_operation(
            label="Build Profile/Media folder operation plan",
            operation_kind="build_folder_operations_plan",
            func=_work,
            priority=YTCEQueuePriority.NORM,
            supersede_key=f"pmd.folderops.review:{database_root}",
            on_done=on_done,
        )

    def apply_folder_operations_plan_async(
        self,
        plan: Any,
        *,
        on_done: Callable[[ProfileMediaQueuedOperationResult], None] | None = None,
    ) -> ProfileMediaQueuedOperationTicket:
        def _work() -> Any:
            from profile_media_database_folder_operations import apply_folder_operations_plan

            return apply_folder_operations_plan(plan)

        return self.submit_operation(
            label="Apply Profile/Media folder operation plan",
            operation_kind="apply_folder_operations_plan",
            func=_work,
            priority=YTCEQueuePriority.HIGH,
            supersede_key=None,
            on_done=on_done,
        )

    def result_for_work_id(self, work_id: str) -> ProfileMediaQueuedOperationResult | None:
        return self._results_by_work_id.get(work_id)

    def ticket_for_work_id(self, work_id: str) -> ProfileMediaQueuedOperationTicket | None:
        return self._tickets_by_work_id.get(work_id)

    def recent_results(self) -> tuple[ProfileMediaQueuedOperationResult, ...]:
        return tuple(self._results_by_work_id.values())

    def shutdown(self) -> None:
        self.queue.shutdown(cancel_queued=True, wait=False)

    def _convert_result(
        self,
        operation_id: str,
        operation_kind: str,
        work_result: YTCEWorkResult,
    ) -> ProfileMediaQueuedOperationResult:
        status = "finished" if work_result.status is YTCEWorkStatus.FINISHED else work_result.status.value
        return ProfileMediaQueuedOperationResult(
            operation_id=operation_id,
            label=work_result.label,
            operation_kind=operation_kind,
            status=status,
            work_id=work_result.work_id,
            work_status=work_result.status.value,
            payload=_payload_to_dict(work_result.result),
            error_text=work_result.error_text,
            supersede_key=work_result.supersede_key or "",
            queue_wait_seconds=work_result.queue_wait_seconds,
            run_seconds=work_result.run_seconds,
        )

    def _log(self, message: str) -> None:
        if self._logger is None:
            return
        try:
            self._logger(message)
        except Exception:
            pass


_DEFAULT_PROFILE_MEDIA_DATABASE_RUNTIME_QUEUE: ProfileMediaDatabaseRuntimeQueue | None = None


def default_profile_media_database_runtime_queue() -> ProfileMediaDatabaseRuntimeQueue:
    global _DEFAULT_PROFILE_MEDIA_DATABASE_RUNTIME_QUEUE
    if _DEFAULT_PROFILE_MEDIA_DATABASE_RUNTIME_QUEUE is None:
        _DEFAULT_PROFILE_MEDIA_DATABASE_RUNTIME_QUEUE = ProfileMediaDatabaseRuntimeQueue()
    return _DEFAULT_PROFILE_MEDIA_DATABASE_RUNTIME_QUEUE
