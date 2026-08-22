from __future__ import annotations

"""Media/download/probe operation watchdog for YTCE.

V80O: JDownloader/AppWork-style media operation watchdog.

Source patterns reviewed from the uploaded JDownloader/AppWork reference set:
- jd.controlling.downloadcontroller.DownloadWatchDog
- jd.controlling.downloadcontroller.DownloadWatchDogJob
- org.appwork.utils.event.queue.Queue / QueueAction / QueueThread

Python/YTCE implementation notes:
- media/browser/file operations register a ticket immediately;
- long-running operations can send heartbeats/progress without touching Tk directly;
- scan/watchdog logic marks stalled and timed-out operations with uniform snapshots;
- cancel callbacks are isolated so a failing observer does not break watchdog state;
- optional YTCEWorkQueue integration executes watched jobs off the UI thread.

This module is a native Python implementation of the same watchdog/job/queue roles,
with explicit provenance labels retained for the JDownloader/AppWork source patterns.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping
from uuid import uuid4
import threading
import time

from ytce_app_work_queue import YTCEQueuePriority, YTCEWorkQueue, YTCEWorkResult, YTCEWorkStatus

MEDIA_OPERATION_WATCHDOG_SCHEMA_VERSION = "media-operation-watchdog-v80o"


def _utc_now_iso() -> str:
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coerce_priority(value: YTCEQueuePriority | str | None) -> YTCEQueuePriority:
    if value is None:
        return YTCEQueuePriority.NORM
    if isinstance(value, YTCEQueuePriority):
        return value
    return YTCEQueuePriority[str(value).strip().upper()]


class MediaOperationStatus(Enum):
    REGISTERED = "registered"
    RUNNING = "running"
    STALLED = "stalled"
    TIMED_OUT = "timed_out"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATUSES = {
    MediaOperationStatus.FINISHED,
    MediaOperationStatus.FAILED,
    MediaOperationStatus.CANCELLED,
}


@dataclass(frozen=True, slots=True)
class MediaOperationTicket:
    """Returned immediately when a media/probe/download operation is registered."""

    operation_id: str
    label: str
    operation_kind: str
    queue_work_id: str = ""
    supersede_key: str = ""
    created_at_utc: str = field(default_factory=_utc_now_iso)
    schema_version: str = MEDIA_OPERATION_WATCHDOG_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MediaOperationSnapshot:
    operation_id: str
    label: str
    operation_kind: str
    status: str
    message: str = ""
    progress: float | None = None
    queue_work_id: str = ""
    supersede_key: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    error_text: str = ""
    created_at_monotonic: float = 0.0
    started_at_monotonic: float | None = None
    last_heartbeat_monotonic: float | None = None
    finished_at_monotonic: float | None = None
    elapsed_seconds: float = 0.0
    idle_seconds: float = 0.0
    timeout_seconds: float | None = None
    stall_seconds: float | None = None
    cancel_requested: bool = False
    schema_version: str = MEDIA_OPERATION_WATCHDOG_SCHEMA_VERSION
    source_pattern: str = "JDownloader DownloadWatchDog + AppWork QueueAction-style operation"

    def ok(self) -> bool:
        return self.status == MediaOperationStatus.FINISHED.value

    def is_terminal(self) -> bool:
        return self.status in {status.value for status in _TERMINAL_STATUSES}

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["metadata"] = dict(self.metadata)
        return data


@dataclass(slots=True)
class _MediaOperationRecord:
    operation_id: str
    label: str
    operation_kind: str
    status: MediaOperationStatus
    created_at: float
    started_at: float | None = None
    last_heartbeat_at: float | None = None
    finished_at: float | None = None
    timeout_seconds: float | None = None
    stall_seconds: float | None = None
    queue_work_id: str = ""
    supersede_key: str = ""
    message: str = ""
    progress: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error_text: str = ""
    cancel_callback: Callable[[], Any] | None = None
    cancel_requested: bool = False
    cancel_callback_called: bool = False


class MediaOperationWatchdog:
    """Track and protect long-running media/browser/file operations.

    The watchdog is intentionally independent from any one media backend. Image discovery,
    video probing, browser-grid serving, FILES materialization, and profile/media database
    tasks can all register operations, heartbeat progress, and let the watchdog mark stale
    operations without freezing the UI thread.
    """

    def __init__(
        self,
        queue: YTCEWorkQueue | None = None,
        *,
        queue_id: str = "media.operation.watchdog",
        default_timeout_seconds: float | None = 120.0,
        default_stall_seconds: float | None = 30.0,
        clock: Callable[[], float] | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.queue = queue or YTCEWorkQueue(queue_id=queue_id, logger=logger)
        self.default_timeout_seconds = default_timeout_seconds
        self.default_stall_seconds = default_stall_seconds
        self._clock = clock or time.monotonic
        self._logger = logger
        self._lock = threading.RLock()
        self._records: dict[str, _MediaOperationRecord] = {}
        self._by_work_id: dict[str, str] = {}

    def register_operation(
        self,
        *,
        label: str,
        operation_kind: str,
        timeout_seconds: float | None = None,
        stall_seconds: float | None = None,
        cancel_callback: Callable[[], Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        supersede_key: str | None = None,
        queue_work_id: str = "",
        start: bool = False,
    ) -> MediaOperationTicket:
        operation_id = f"media.op.{uuid4().hex[:12]}"
        now = self._clock()
        record = _MediaOperationRecord(
            operation_id=operation_id,
            label=label,
            operation_kind=operation_kind,
            status=MediaOperationStatus.RUNNING if start else MediaOperationStatus.REGISTERED,
            created_at=now,
            started_at=now if start else None,
            last_heartbeat_at=now if start else None,
            timeout_seconds=self.default_timeout_seconds if timeout_seconds is None else timeout_seconds,
            stall_seconds=self.default_stall_seconds if stall_seconds is None else stall_seconds,
            cancel_callback=cancel_callback,
            metadata=dict(metadata or {}),
            supersede_key=supersede_key or "",
            queue_work_id=queue_work_id,
        )
        with self._lock:
            self._records[operation_id] = record
            if queue_work_id:
                self._by_work_id[queue_work_id] = operation_id
        return self._ticket(record)

    def start(self, operation_id: str, message: str = "") -> MediaOperationSnapshot:
        with self._lock:
            record = self._require(operation_id)
            if record.status not in _TERMINAL_STATUSES:
                now = self._clock()
                record.status = MediaOperationStatus.RUNNING
                record.started_at = record.started_at or now
                record.last_heartbeat_at = now
                if message:
                    record.message = message
            return self._snapshot_locked(record)

    def heartbeat(
        self,
        operation_id: str,
        *,
        message: str = "",
        progress: float | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> MediaOperationSnapshot:
        with self._lock:
            record = self._require(operation_id)
            if record.status not in _TERMINAL_STATUSES:
                record.status = MediaOperationStatus.RUNNING
                now = self._clock()
                record.started_at = record.started_at or now
                record.last_heartbeat_at = now
                if message:
                    record.message = message
                if progress is not None:
                    record.progress = max(0.0, min(1.0, float(progress)))
                if metadata:
                    record.metadata.update(dict(metadata))
            return self._snapshot_locked(record)

    def finish(self, operation_id: str, *, message: str = "", metadata: Mapping[str, Any] | None = None) -> MediaOperationSnapshot:
        return self._complete(operation_id, MediaOperationStatus.FINISHED, message=message, metadata=metadata)

    def fail(self, operation_id: str, *, error_text: str = "", message: str = "", metadata: Mapping[str, Any] | None = None) -> MediaOperationSnapshot:
        return self._complete(operation_id, MediaOperationStatus.FAILED, message=message, error_text=error_text, metadata=metadata)

    def cancel(self, operation_id: str, *, message: str = "cancelled") -> MediaOperationSnapshot:
        callback: Callable[[], Any] | None = None
        with self._lock:
            record = self._require(operation_id)
            if record.status not in _TERMINAL_STATUSES:
                record.cancel_requested = True
                callback = record.cancel_callback if not record.cancel_callback_called else None
                record.cancel_callback_called = record.cancel_callback_called or callback is not None
                record.status = MediaOperationStatus.CANCELLED
                record.finished_at = self._clock()
                record.message = message or record.message
            snapshot = self._snapshot_locked(record)
        self._call_cancel_callback(callback, record.label)
        return snapshot

    def submit_operation(
        self,
        *,
        label: str,
        operation_kind: str,
        func: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: Mapping[str, Any] | None = None,
        priority: YTCEQueuePriority | str | None = YTCEQueuePriority.NORM,
        timeout_seconds: float | None = None,
        stall_seconds: float | None = None,
        supersede_key: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        on_done: Callable[[MediaOperationSnapshot], None] | None = None,
    ) -> MediaOperationTicket:
        """Submit a watched operation to the runtime queue and return a ticket."""

        ticket = self.register_operation(
            label=label,
            operation_kind=operation_kind,
            timeout_seconds=timeout_seconds,
            stall_seconds=stall_seconds,
            metadata=metadata,
            supersede_key=supersede_key,
        )
        call_kwargs = dict(kwargs or {})

        def _run_watched() -> Any:
            self.start(ticket.operation_id, "running")
            try:
                payload = func(*args, **call_kwargs)
            except BaseException as exc:
                self.fail(ticket.operation_id, error_text=f"{type(exc).__name__}: {exc}", message="failed")
                raise
            self.finish(ticket.operation_id, message="finished", metadata={"result_type": type(payload).__name__})
            return payload

        def _done(work_result: YTCEWorkResult) -> None:
            if work_result.status is YTCEWorkStatus.SUPERSEDED:
                snapshot = self.cancel(ticket.operation_id, message="superseded")
            elif work_result.status is YTCEWorkStatus.CANCELLED:
                snapshot = self.cancel(ticket.operation_id, message="cancelled")
            else:
                snapshot = self.snapshot(ticket.operation_id)
            if on_done is not None:
                try:
                    on_done(snapshot)
                except Exception as exc:
                    self._log(f"Media watchdog callback isolated: {label}: {exc!r}")

        item = self.queue.add(
            label,
            _run_watched,
            priority=_coerce_priority(priority),
            supersede_key=supersede_key,
            on_done=_done,
        )
        with self._lock:
            record = self._require(ticket.operation_id)
            record.queue_work_id = item.work_id
            self._by_work_id[item.work_id] = ticket.operation_id
            return self._ticket(record)

    def run_operation_wait(
        self,
        *,
        label: str,
        operation_kind: str,
        func: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: Mapping[str, Any] | None = None,
        priority: YTCEQueuePriority | str | None = YTCEQueuePriority.NORM,
        timeout: float | None = None,
        timeout_seconds: float | None = None,
        stall_seconds: float | None = None,
        supersede_key: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> MediaOperationSnapshot:
        """Run a watched operation through the runtime queue and return its snapshot."""

        ticket = self.register_operation(
            label=label,
            operation_kind=operation_kind,
            timeout_seconds=timeout_seconds,
            stall_seconds=stall_seconds,
            metadata=metadata,
            supersede_key=supersede_key,
        )
        call_kwargs = dict(kwargs or {})

        def _run_watched() -> Any:
            self.start(ticket.operation_id, "running")
            try:
                payload = func(*args, **call_kwargs)
            except BaseException as exc:
                self.fail(ticket.operation_id, error_text=f"{type(exc).__name__}: {exc}", message="failed")
                raise
            self.finish(ticket.operation_id, message="finished", metadata={"result_type": type(payload).__name__})
            return payload

        work_result = self.queue.add_wait(
            label,
            _run_watched,
            priority=_coerce_priority(priority),
            supersede_key=supersede_key,
            timeout=timeout,
            raise_on_error=False,
        )
        if isinstance(work_result, YTCEWorkResult):
            with self._lock:
                record = self._require(ticket.operation_id)
                record.queue_work_id = work_result.work_id
                self._by_work_id[work_result.work_id] = ticket.operation_id
                if work_result.status is YTCEWorkStatus.CANCELLED:
                    record.status = MediaOperationStatus.CANCELLED
                    record.finished_at = self._clock()
                elif work_result.status is YTCEWorkStatus.SUPERSEDED:
                    record.status = MediaOperationStatus.CANCELLED
                    record.message = "superseded"
                    record.finished_at = self._clock()
        return self.snapshot(ticket.operation_id)

    def scan(self) -> list[MediaOperationSnapshot]:
        """Mark stalled/timed-out live operations and return the changed snapshots."""

        callbacks: list[tuple[Callable[[], Any], str]] = []
        changed: list[MediaOperationSnapshot] = []
        now = self._clock()
        with self._lock:
            for record in self._records.values():
                if record.status in _TERMINAL_STATUSES:
                    continue
                baseline = record.last_heartbeat_at or record.started_at or record.created_at
                elapsed = max(0.0, now - record.created_at)
                idle = max(0.0, now - baseline)
                new_status: MediaOperationStatus | None = None
                if record.timeout_seconds is not None and elapsed >= record.timeout_seconds:
                    new_status = MediaOperationStatus.TIMED_OUT
                    record.cancel_requested = True
                    if record.cancel_callback is not None and not record.cancel_callback_called:
                        callbacks.append((record.cancel_callback, record.label))
                        record.cancel_callback_called = True
                elif record.stall_seconds is not None and idle >= record.stall_seconds:
                    new_status = MediaOperationStatus.STALLED
                if new_status is not None and record.status is not new_status:
                    record.status = new_status
                    if new_status is MediaOperationStatus.TIMED_OUT:
                        record.message = record.message or "operation timed out"
                    elif new_status is MediaOperationStatus.STALLED:
                        record.message = record.message or "operation stalled"
                    changed.append(self._snapshot_locked(record, now=now))
        for callback, label in callbacks:
            self._call_cancel_callback(callback, label)
        return changed

    def snapshot(self, operation_id: str) -> MediaOperationSnapshot:
        with self._lock:
            return self._snapshot_locked(self._require(operation_id))

    def snapshot_for_work_id(self, work_id: str) -> MediaOperationSnapshot | None:
        with self._lock:
            operation_id = self._by_work_id.get(work_id)
            if not operation_id:
                return None
            return self._snapshot_locked(self._records[operation_id])

    def snapshots(self, *, include_finished: bool = True) -> list[MediaOperationSnapshot]:
        with self._lock:
            records = list(self._records.values())
            if not include_finished:
                records = [record for record in records if record.status not in _TERMINAL_STATUSES]
            return [self._snapshot_locked(record) for record in records]

    def purge_finished(self, *, older_than_seconds: float = 0.0) -> int:
        now = self._clock()
        removed = 0
        with self._lock:
            for operation_id, record in list(self._records.items()):
                if record.status not in _TERMINAL_STATUSES or record.finished_at is None:
                    continue
                if now - record.finished_at >= older_than_seconds:
                    removed += 1
                    self._records.pop(operation_id, None)
                    if record.queue_work_id:
                        self._by_work_id.pop(record.queue_work_id, None)
        return removed

    def shutdown(self) -> None:
        self.queue.shutdown(cancel_queued=False, wait=False)

    def _complete(
        self,
        operation_id: str,
        status: MediaOperationStatus,
        *,
        message: str = "",
        error_text: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> MediaOperationSnapshot:
        with self._lock:
            record = self._require(operation_id)
            record.status = status
            record.finished_at = self._clock()
            if message:
                record.message = message
            if error_text:
                record.error_text = error_text
            if metadata:
                record.metadata.update(dict(metadata))
            return self._snapshot_locked(record)

    def _ticket(self, record: _MediaOperationRecord) -> MediaOperationTicket:
        return MediaOperationTicket(
            operation_id=record.operation_id,
            label=record.label,
            operation_kind=record.operation_kind,
            queue_work_id=record.queue_work_id,
            supersede_key=record.supersede_key,
        )

    def _snapshot_locked(self, record: _MediaOperationRecord, *, now: float | None = None) -> MediaOperationSnapshot:
        if now is None and record.status in _TERMINAL_STATUSES and record.finished_at is not None:
            current = record.finished_at
        else:
            current = self._clock() if now is None else now
        baseline = record.last_heartbeat_at or record.started_at or record.created_at
        finished = record.finished_at if record.finished_at is not None else current
        return MediaOperationSnapshot(
            operation_id=record.operation_id,
            label=record.label,
            operation_kind=record.operation_kind,
            status=record.status.value,
            message=record.message,
            progress=record.progress,
            queue_work_id=record.queue_work_id,
            supersede_key=record.supersede_key,
            metadata=dict(record.metadata),
            error_text=record.error_text,
            created_at_monotonic=record.created_at,
            started_at_monotonic=record.started_at,
            last_heartbeat_monotonic=record.last_heartbeat_at,
            finished_at_monotonic=record.finished_at,
            elapsed_seconds=max(0.0, finished - record.created_at),
            idle_seconds=max(0.0, current - baseline),
            timeout_seconds=record.timeout_seconds,
            stall_seconds=record.stall_seconds,
            cancel_requested=record.cancel_requested,
        )

    def _require(self, operation_id: str) -> _MediaOperationRecord:
        try:
            return self._records[operation_id]
        except KeyError as exc:
            raise KeyError(f"Unknown media operation: {operation_id}") from exc

    def _call_cancel_callback(self, callback: Callable[[], Any] | None, label: str) -> None:
        if callback is None:
            return
        try:
            callback()
        except Exception as exc:
            self._log(f"Media watchdog cancel callback isolated: {label}: {exc!r}")

    def _log(self, message: str) -> None:
        if self._logger is None:
            return
        try:
            self._logger(message)
        except Exception:
            pass


_default_watchdog: MediaOperationWatchdog | None = None


def default_media_operation_watchdog() -> MediaOperationWatchdog:
    global _default_watchdog
    if _default_watchdog is None:
        _default_watchdog = MediaOperationWatchdog()
    return _default_watchdog
