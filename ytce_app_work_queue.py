from __future__ import annotations

"""YTCE runtime work queue.

V80M: AppWork/JDownloader-style live runtime work queue.

Source pattern reviewed from the uploaded JDownloader/AppWork reference set:
- org.appwork.utils.event.queue.Queue
- org.appwork.utils.event.queue.QueueAction
- org.appwork.utils.event.queue.QueueThread

Python/Tk implementation notes:
- priority buckets mirror AppWork's HIGH/NORM/LOW queue priority split;
- the worker thread is lazy and exits after an idle timeout;
- nested queue calls from the active queue thread can run inline to avoid deadlocks;
- queued work can be deduped/superseded by a stable key;
- callbacks and exception handlers are isolated so a bad observer does not kill the queue.

The Java source headers in the reviewed AppWork files identify the upstream project as
AppWork Utilities/JDownloader with dual commercial/AGPL-style terms. This Python module
is a native YTCE implementation of the same runtime semantics and keeps the provenance
label in source.
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import traceback
from typing import Any, Callable, Deque, Iterable, Mapping
from uuid import uuid4


class YTCEQueuePriority(Enum):
    """Priority buckets, ordered like AppWork QueuePriority."""

    HIGH = 0
    NORM = 1
    LOW = 2


class YTCEWorkStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class YTCEWorkError(RuntimeError):
    """Raised by add_wait when a queued callable fails and raising is requested."""


@dataclass(slots=True)
class YTCEWorkResult:
    work_id: str
    label: str
    status: YTCEWorkStatus
    result: Any = None
    error: BaseException | None = None
    error_text: str = ""
    started_at: float | None = None
    finished_at: float | None = None
    queue_wait_seconds: float | None = None
    run_seconds: float | None = None
    supersede_key: str | None = None

    def ok(self) -> bool:
        return self.status is YTCEWorkStatus.FINISHED

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "label": self.label,
            "status": self.status.value,
            "error_text": self.error_text,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "queue_wait_seconds": self.queue_wait_seconds,
            "run_seconds": self.run_seconds,
            "supersede_key": self.supersede_key,
        }


@dataclass(slots=True)
class YTCEWorkItem:
    label: str
    func: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: Mapping[str, Any] = field(default_factory=dict)
    priority: YTCEQueuePriority = YTCEQueuePriority.NORM
    supersede_key: str | None = None
    work_id: str = field(default_factory=lambda: f"ytce.work.{uuid4().hex[:12]}")
    allow_inline_from_queue: bool = True
    on_success: Callable[[YTCEWorkResult], None] | None = None
    on_error: Callable[[YTCEWorkResult], None] | None = None
    on_done: Callable[[YTCEWorkResult], None] | None = None
    created_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    finished_at: float | None = None
    status: YTCEWorkStatus = YTCEWorkStatus.PENDING
    result: Any = None
    error: BaseException | None = None
    error_text: str = ""
    caller_thread_name: str = ""
    _done_event: threading.Event = field(default_factory=threading.Event, init=False, repr=False)

    def reset_for_queue(self) -> None:
        self.started_at = None
        self.finished_at = None
        self.status = YTCEWorkStatus.PENDING
        self.result = None
        self.error = None
        self.error_text = ""
        self.caller_thread_name = threading.current_thread().name
        self._done_event.clear()

    def cancel(self, status: YTCEWorkStatus = YTCEWorkStatus.CANCELLED) -> bool:
        if self.status in {YTCEWorkStatus.FINISHED, YTCEWorkStatus.FAILED, YTCEWorkStatus.CANCELLED, YTCEWorkStatus.SUPERSEDED}:
            return False
        self.status = status
        self.finished_at = time.monotonic()
        self._done_event.set()
        return True

    def is_done(self) -> bool:
        return self._done_event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._done_event.wait(timeout)

    def as_result(self) -> YTCEWorkResult:
        queue_wait = None
        run_seconds = None
        if self.started_at is not None:
            queue_wait = max(0.0, self.started_at - self.created_at)
        if self.started_at is not None and self.finished_at is not None:
            run_seconds = max(0.0, self.finished_at - self.started_at)
        return YTCEWorkResult(
            work_id=self.work_id,
            label=self.label,
            status=self.status,
            result=self.result,
            error=self.error,
            error_text=self.error_text,
            started_at=self.started_at,
            finished_at=self.finished_at,
            queue_wait_seconds=queue_wait,
            run_seconds=run_seconds,
            supersede_key=self.supersede_key,
        )


@dataclass(slots=True)
class YTCEQueueStats:
    added: int = 0
    add_wait: int = 0
    ran_inline: int = 0
    finished: int = 0
    failed: int = 0
    cancelled: int = 0
    superseded: int = 0
    rescued: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "added": self.added,
            "add_wait": self.add_wait,
            "ran_inline": self.ran_inline,
            "finished": self.finished,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "superseded": self.superseded,
            "rescued": self.rescued,
        }


class YTCEWorkQueue:
    """Single-worker priority queue with AppWork-style action semantics.

    The queue deliberately runs one item at a time. That gives FILES/media/database code a
    predictable serialized runtime surface, while allowing expensive work to leave the Tk
    thread. For fan-out work, callers can create several named queues rather than making
    each GUI callback start its own untracked thread.
    """

    def __init__(
        self,
        queue_id: str = "ytce.runtime",
        *,
        idle_timeout_seconds: float = 10.0,
        logger: Callable[[str], None] | None = None,
        history_limit: int = 30,
    ) -> None:
        self.queue_id = queue_id
        self.idle_timeout_seconds = max(0.0, float(idle_timeout_seconds))
        self._logger = logger
        self._lock = threading.Condition(threading.RLock())
        self._queues: dict[YTCEQueuePriority, Deque[YTCEWorkItem]] = {
            YTCEQueuePriority.HIGH: deque(),
            YTCEQueuePriority.NORM: deque(),
            YTCEQueuePriority.LOW: deque(),
        }
        self._thread: threading.Thread | None = None
        self._stop_requested = False
        self._current_item: YTCEWorkItem | None = None
        self._history: Deque[YTCEWorkResult] = deque(maxlen=max(1, history_limit))
        self._stats = YTCEQueueStats()
        self._local = threading.local()

    def add(
        self,
        label: str,
        func: Callable[..., Any],
        *args: Any,
        priority: YTCEQueuePriority = YTCEQueuePriority.NORM,
        supersede_key: str | None = None,
        allow_inline_from_queue: bool = True,
        on_success: Callable[[YTCEWorkResult], None] | None = None,
        on_error: Callable[[YTCEWorkResult], None] | None = None,
        on_done: Callable[[YTCEWorkResult], None] | None = None,
        **kwargs: Any,
    ) -> YTCEWorkItem:
        item = YTCEWorkItem(
            label=label,
            func=func,
            args=tuple(args),
            kwargs=dict(kwargs),
            priority=priority,
            supersede_key=supersede_key,
            allow_inline_from_queue=allow_inline_from_queue,
            on_success=on_success,
            on_error=on_error,
            on_done=on_done,
        )
        return self.add_item(item)

    def add_item(self, item: YTCEWorkItem) -> YTCEWorkItem:
        item.reset_for_queue()
        if self.is_queue_thread() and item.allow_inline_from_queue:
            source = self._current_item
            if source is not None:
                item.priority = source.priority
            self._stats.ran_inline += 1
            self._run_item(item)
            return item
        with self._lock:
            self._stats.added += 1
            if item.supersede_key:
                self._supersede_locked(item.supersede_key)
            self._queues[item.priority].append(item)
            self._ensure_thread_locked()
            self._lock.notify_all()
        return item

    def add_wait(
        self,
        label: str,
        func: Callable[..., Any],
        *args: Any,
        priority: YTCEQueuePriority = YTCEQueuePriority.NORM,
        supersede_key: str | None = None,
        timeout: float | None = None,
        raise_on_error: bool = True,
        **kwargs: Any,
    ) -> Any:
        if self.is_queue_thread():
            self._stats.ran_inline += 1
            item = YTCEWorkItem(label=label, func=func, args=tuple(args), kwargs=dict(kwargs), priority=priority, supersede_key=supersede_key)
            self._run_item(item)
        else:
            with self._lock:
                self._stats.add_wait += 1
            item = self.add(label, func, *args, priority=priority, supersede_key=supersede_key, **kwargs)
            if not item.wait(timeout):
                raise TimeoutError(f"Timed out waiting for queued work: {label}")
        result = item.as_result()
        if result.status is YTCEWorkStatus.FINISHED:
            return result.result
        if raise_on_error:
            if result.error is not None:
                raise YTCEWorkError(result.error_text) from result.error
            raise YTCEWorkError(result.error_text or f"Queued work did not finish: {result.status.value}")
        return result

    def cancel_queued(self, supersede_key: str | None = None) -> int:
        cancelled = 0
        with self._lock:
            for bucket in self._queues.values():
                kept: Deque[YTCEWorkItem] = deque()
                while bucket:
                    item = bucket.popleft()
                    if supersede_key is None or item.supersede_key == supersede_key:
                        if item.cancel(YTCEWorkStatus.CANCELLED):
                            cancelled += 1
                            self._stats.cancelled += 1
                            self._remember(item.as_result())
                    else:
                        kept.append(item)
                bucket.extend(kept)
        return cancelled

    def kill_queue(self) -> int:
        """Cancel queued work, but do not interrupt the currently running callable."""

        return self.cancel_queued(None)

    def shutdown(self, *, cancel_queued: bool = True, wait: bool = False, timeout: float | None = 2.0) -> None:
        if cancel_queued:
            self.kill_queue()
        thread: threading.Thread | None
        with self._lock:
            self._stop_requested = True
            self._lock.notify_all()
            thread = self._thread
        if wait and thread is not None and thread is not threading.current_thread():
            thread.join(timeout)

    def is_queue_thread(self) -> bool:
        return getattr(self._local, "queue", None) is self

    def is_empty(self) -> bool:
        with self._lock:
            return all(not bucket for bucket in self._queues.values())

    def size(self) -> int:
        with self._lock:
            return sum(len(bucket) for bucket in self._queues.values())

    def current_label(self) -> str:
        item = self._current_item
        return item.label if item is not None else ""

    def stats(self) -> YTCEQueueStats:
        stats = self._stats
        return YTCEQueueStats(**stats.to_dict())

    def history(self) -> tuple[YTCEWorkResult, ...]:
        with self._lock:
            return tuple(self._history)

    def _supersede_locked(self, supersede_key: str) -> None:
        for bucket in self._queues.values():
            kept: Deque[YTCEWorkItem] = deque()
            while bucket:
                old = bucket.popleft()
                if old.supersede_key == supersede_key:
                    if old.cancel(YTCEWorkStatus.SUPERSEDED):
                        self._stats.superseded += 1
                        self._remember(old.as_result())
                else:
                    kept.append(old)
            bucket.extend(kept)

    def _ensure_thread_locked(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_requested = False
        self._thread = threading.Thread(target=self._run_loop, name=f"YTCEWorkQueue[{self.queue_id}]", daemon=True)
        self._thread.start()

    def _poll_locked(self) -> YTCEWorkItem | None:
        for priority in (YTCEQueuePriority.HIGH, YTCEQueuePriority.NORM, YTCEQueuePriority.LOW):
            bucket = self._queues[priority]
            if bucket:
                return bucket.popleft()
        return None

    def _run_loop(self) -> None:
        self._local.queue = self
        try:
            while True:
                with self._lock:
                    item = self._poll_locked()
                    if item is None:
                        if self._stop_requested:
                            self._thread = None
                            return
                        self._lock.wait(self.idle_timeout_seconds)
                        item = self._poll_locked()
                        if item is None:
                            self._thread = None
                            return
                try:
                    self._run_item(item)
                except BaseException as exc:  # rescue the queue loop itself
                    self._stats.rescued += 1
                    self._log(f"YTCE work queue rescued after unexpected loop error: {exc!r}")
        finally:
            self._current_item = None
            self._local.queue = None
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None

    def _run_item(self, item: YTCEWorkItem) -> None:
        previous_item = self._current_item
        self._current_item = item
        item.started_at = time.monotonic()
        item.status = YTCEWorkStatus.RUNNING
        try:
            item.result = item.func(*item.args, **dict(item.kwargs))
            item.status = YTCEWorkStatus.FINISHED
            self._stats.finished += 1
        except BaseException as exc:
            item.error = exc
            item.error_text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            item.status = YTCEWorkStatus.FAILED
            self._stats.failed += 1
        finally:
            item.finished_at = time.monotonic()
            item._done_event.set()
            result = item.as_result()
            self._remember(result)
            self._dispatch_callbacks(item, result)
            self._current_item = previous_item

    def _dispatch_callbacks(self, item: YTCEWorkItem, result: YTCEWorkResult) -> None:
        callbacks: list[Callable[[YTCEWorkResult], None]] = []
        if result.status is YTCEWorkStatus.FINISHED and item.on_success is not None:
            callbacks.append(item.on_success)
        if result.status is YTCEWorkStatus.FAILED and item.on_error is not None:
            callbacks.append(item.on_error)
        if item.on_done is not None:
            callbacks.append(item.on_done)
        for callback in callbacks:
            try:
                callback(result)
            except BaseException as exc:
                self._log(f"YTCE work callback isolated: {item.label}: {exc!r}")

    def _remember(self, result: YTCEWorkResult) -> None:
        with self._lock:
            self._history.append(result)

    def _log(self, message: str) -> None:
        if self._logger is None:
            return
        try:
            self._logger(message)
        except BaseException:
            pass


def coerce_priority(value: YTCEQueuePriority | str | None) -> YTCEQueuePriority:
    if value is None:
        return YTCEQueuePriority.NORM
    if isinstance(value, YTCEQueuePriority):
        return value
    normalized = str(value).strip().upper()
    return YTCEQueuePriority[normalized]


def queue_snapshot(queue: YTCEWorkQueue) -> dict[str, Any]:
    return {
        "queue_id": queue.queue_id,
        "size": queue.size(),
        "current_label": queue.current_label(),
        "stats": queue.stats().to_dict(),
        "history": [result.to_dict() for result in queue.history()],
    }
