from __future__ import annotations

import threading

from media_operation_watchdog import (
    MediaOperationStatus,
    MediaOperationWatchdog,
    default_media_operation_watchdog,
)
from ytce_app_work_queue import YTCEWorkQueue


class FakeClock:
    def __init__(self) -> None:
        self.value = 1000.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def test_register_heartbeat_finish_snapshot() -> None:
    clock = FakeClock()
    watchdog = MediaOperationWatchdog(YTCEWorkQueue(idle_timeout_seconds=0.05), clock=clock, default_stall_seconds=5.0)
    ticket = watchdog.register_operation(label="Image discovery", operation_kind="webpage_image_discovery", start=True)
    clock.advance(1.0)
    heartbeat = watchdog.heartbeat(ticket.operation_id, message="found candidates", progress=0.5, metadata={"candidates": 12})
    assert heartbeat.status == MediaOperationStatus.RUNNING.value
    assert heartbeat.progress == 0.5
    assert heartbeat.metadata["candidates"] == 12
    clock.advance(1.0)
    finished = watchdog.finish(ticket.operation_id, message="done")
    assert finished.ok()
    assert finished.elapsed_seconds == 2.0
    watchdog.shutdown()


def test_scan_marks_stalled_then_timeout_and_isolates_cancel_callback() -> None:
    clock = FakeClock()
    calls: list[str] = []

    def cancel() -> None:
        calls.append("cancel")

    watchdog = MediaOperationWatchdog(
        YTCEWorkQueue(idle_timeout_seconds=0.05),
        clock=clock,
        default_stall_seconds=3.0,
        default_timeout_seconds=10.0,
    )
    ticket = watchdog.register_operation(
        label="Browser probe",
        operation_kind="webpage_video_probe",
        cancel_callback=cancel,
        start=True,
    )
    clock.advance(3.1)
    stalled = watchdog.scan()
    assert [item.operation_id for item in stalled] == [ticket.operation_id]
    assert stalled[0].status == MediaOperationStatus.STALLED.value
    assert calls == []
    clock.advance(7.0)
    timed_out = watchdog.scan()
    assert timed_out[0].status == MediaOperationStatus.TIMED_OUT.value
    assert timed_out[0].cancel_requested
    assert calls == ["cancel"]
    clock.advance(1.0)
    assert watchdog.scan() == []
    watchdog.shutdown()


def test_run_operation_wait_finishes_through_queue() -> None:
    watchdog = MediaOperationWatchdog(YTCEWorkQueue(idle_timeout_seconds=0.05), default_timeout_seconds=10.0)
    snapshot = watchdog.run_operation_wait(
        label="Download selected image",
        operation_kind="image_download_to_files",
        func=lambda: {"added": 1},
        timeout=2.0,
        metadata={"source": "browser-grid"},
    )
    assert snapshot.ok()
    assert snapshot.status == MediaOperationStatus.FINISHED.value
    assert snapshot.metadata["source"] == "browser-grid"
    assert snapshot.metadata["result_type"] == "dict"
    watchdog.shutdown()


def test_run_operation_wait_records_failed_operation_without_raising() -> None:
    watchdog = MediaOperationWatchdog(YTCEWorkQueue(idle_timeout_seconds=0.05))

    def boom() -> None:
        raise RuntimeError("probe failed")

    snapshot = watchdog.run_operation_wait(
        label="Rendered probe",
        operation_kind="rendered_video_probe",
        func=boom,
        timeout=2.0,
    )
    assert snapshot.status == MediaOperationStatus.FAILED.value
    assert "RuntimeError: probe failed" in snapshot.error_text
    watchdog.shutdown()


def test_submit_operation_returns_ticket_and_done_snapshot() -> None:
    watchdog = MediaOperationWatchdog(YTCEWorkQueue(idle_timeout_seconds=0.05))
    done = threading.Event()
    observed = []
    ticket = watchdog.submit_operation(
        label="Build preview cache",
        operation_kind="preview_cache_build",
        func=lambda: "cached",
        supersede_key="preview:demo",
        on_done=lambda snapshot: (observed.append(snapshot), done.set()),
    )
    assert ticket.supersede_key == "preview:demo"
    assert done.wait(2.0)
    assert observed[0].ok()
    assert watchdog.snapshot_for_work_id(observed[0].queue_work_id) == observed[0]
    assert watchdog.purge_finished(older_than_seconds=0.0) >= 1
    watchdog.shutdown()


def test_default_watchdog_is_singleton() -> None:
    assert default_media_operation_watchdog() is default_media_operation_watchdog()


def main() -> None:
    tests = [
        test_register_heartbeat_finish_snapshot,
        test_scan_marks_stalled_then_timeout_and_isolates_cancel_callback,
        test_run_operation_wait_finishes_through_queue,
        test_run_operation_wait_records_failed_operation_without_raising,
        test_submit_operation_returns_ticket_and_done_snapshot,
        test_default_watchdog_is_singleton,
    ]
    for test in tests:
        test()
    default_media_operation_watchdog().shutdown()
    print("media_operation_watchdog_test.py: OK")


if __name__ == "__main__":
    main()
