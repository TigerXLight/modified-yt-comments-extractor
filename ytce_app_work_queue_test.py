from __future__ import annotations

import threading
import time

from ytce_app_work_queue import (
    YTCEQueuePriority,
    YTCEWorkError,
    YTCEWorkQueue,
    YTCEWorkStatus,
    coerce_priority,
    queue_snapshot,
)


def test_priority_order_and_lazy_worker() -> None:
    seen: list[str] = []
    queue = YTCEWorkQueue("test.priority", idle_timeout_seconds=0.05)
    try:
        blocker = threading.Event()
        queue.add("block", lambda: blocker.wait(1.0), priority=YTCEQueuePriority.NORM)
        queue.add("low", lambda: seen.append("low"), priority=YTCEQueuePriority.LOW)
        queue.add("high", lambda: seen.append("high"), priority=YTCEQueuePriority.HIGH)
        blocker.set()
        deadline = time.monotonic() + 2.0
        while len(seen) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        queue.shutdown(cancel_queued=True, wait=True)
    assert seen == ["high", "low"]
    assert queue.stats().finished >= 3


def test_supersede_key_cancels_stale_queued_work() -> None:
    seen: list[str] = []
    queue = YTCEWorkQueue("test.supersede", idle_timeout_seconds=0.05)
    blocker = threading.Event()
    try:
        queue.add("block", lambda: blocker.wait(1.0))
        first = queue.add("search=a", lambda: seen.append("a"), supersede_key="access-search")
        second = queue.add("search=ab", lambda: seen.append("ab"), supersede_key="access-search")
        blocker.set()
        deadline = time.monotonic() + 2.0
        while len(seen) < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        queue.shutdown(cancel_queued=True, wait=True)
    assert first.status is YTCEWorkStatus.SUPERSEDED
    assert second.status is YTCEWorkStatus.FINISHED
    assert seen == ["ab"]
    assert queue.stats().superseded >= 1


def test_add_wait_returns_result_and_raises_wrapped_error() -> None:
    queue = YTCEWorkQueue("test.wait", idle_timeout_seconds=0.05)
    try:
        assert queue.add_wait("sum", lambda a, b: a + b, 2, 3) == 5
        try:
            queue.add_wait("bad", lambda: (_ for _ in ()).throw(ValueError("boom")))
        except YTCEWorkError as exc:
            assert "ValueError" in str(exc)
            assert "boom" in str(exc)
        else:
            raise AssertionError("expected YTCEWorkError")
    finally:
        queue.shutdown(cancel_queued=True, wait=True)


def test_nested_queue_call_runs_inline_and_keeps_worker_alive() -> None:
    queue = YTCEWorkQueue("test.inline", idle_timeout_seconds=0.05)
    worker_thread_names: list[str] = []

    def outer() -> str:
        worker_thread_names.append(threading.current_thread().name)
        return queue.add_wait("inner", lambda: threading.current_thread().name)

    try:
        result = queue.add_wait("outer", outer)
    finally:
        queue.shutdown(cancel_queued=True, wait=True)
    assert result == worker_thread_names[0]
    assert queue.stats().ran_inline >= 1


def test_exception_callbacks_are_isolated_and_recorded() -> None:
    logs: list[str] = []
    queue = YTCEWorkQueue("test.callback", idle_timeout_seconds=0.05, logger=logs.append)
    done = threading.Event()

    def broken_callback(_result):
        done.set()
        raise RuntimeError("callback exploded")

    try:
        queue.add("ok", lambda: "done", on_done=broken_callback)
        assert done.wait(2.0)
    finally:
        queue.shutdown(cancel_queued=True, wait=True)
    assert any("callback isolated" in line for line in logs)
    assert queue.history()[-1].status is YTCEWorkStatus.FINISHED


def test_queue_snapshot_and_priority_coercion_are_stable() -> None:
    queue = YTCEWorkQueue("test.snapshot", idle_timeout_seconds=0.05)
    try:
        queue.add_wait("ok", lambda: 1)
        snapshot = queue_snapshot(queue)
    finally:
        queue.shutdown(cancel_queued=True, wait=True)
    assert snapshot["queue_id"] == "test.snapshot"
    assert snapshot["stats"]["finished"] >= 1
    assert coerce_priority("high") is YTCEQueuePriority.HIGH
    assert coerce_priority(None) is YTCEQueuePriority.NORM


def run_self_test() -> None:
    test_priority_order_and_lazy_worker()
    test_supersede_key_cancels_stale_queued_work()
    test_add_wait_returns_result_and_raises_wrapped_error()
    test_nested_queue_call_runs_inline_and_keeps_worker_alive()
    test_exception_callbacks_are_isolated_and_recorded()
    test_queue_snapshot_and_priority_coercion_are_stable()


if __name__ == "__main__":
    run_self_test()
    print("ytce_app_work_queue_test.py: OK")
