from __future__ import annotations

import threading
import time

from profile_media_database_runtime_queue import (
    ProfileMediaDatabaseRuntimeQueue,
    ProfileMediaQueuedOperationResult,
    default_profile_media_database_runtime_queue,
)
from ytce_app_work_queue import YTCEQueuePriority, YTCEWorkQueue, YTCEWorkStatus


def test_run_operation_wait_returns_uniform_payload() -> None:
    queue = ProfileMediaDatabaseRuntimeQueue(YTCEWorkQueue(idle_timeout_seconds=0.05))
    result = queue.run_operation_wait(
        label="Build fake materialize plan",
        operation_kind="build_materialize_plan",
        func=lambda: {"status": "planned_dry_run", "plan_id": "demo"},
        priority=YTCEQueuePriority.NORM,
        timeout=2.0,
    )
    assert isinstance(result, ProfileMediaQueuedOperationResult)
    assert result.ok()
    assert result.payload["status"] == "planned_dry_run"
    assert result.operation_kind == "build_materialize_plan"
    queue.shutdown()


def test_run_operation_wait_isolates_exception_as_failed_result() -> None:
    queue = ProfileMediaDatabaseRuntimeQueue(YTCEWorkQueue(idle_timeout_seconds=0.05))

    def boom() -> None:
        raise ValueError("bad reviewed operation")

    result = queue.run_operation_wait(
        label="Apply fake folder operation",
        operation_kind="apply_folder_operations_plan",
        func=boom,
        timeout=2.0,
    )
    assert not result.ok()
    assert result.status == "failed"
    assert "ValueError" in result.error_text
    assert "bad reviewed operation" in result.error_text
    queue.shutdown()


def test_async_submit_returns_ticket_and_converts_done_result() -> None:
    queue = ProfileMediaDatabaseRuntimeQueue(YTCEWorkQueue(idle_timeout_seconds=0.05))
    observed: list[ProfileMediaQueuedOperationResult] = []
    done = threading.Event()

    ticket = queue.submit_operation(
        label="Review fake database operation",
        operation_kind="review_database_operation",
        func=lambda: {"status": "ready"},
        supersede_key="review:demo",
        on_done=lambda result: (observed.append(result), done.set()),
    )

    assert ticket.operation_kind == "review_database_operation"
    assert ticket.supersede_key == "review:demo"
    assert done.wait(2.0)
    assert observed[0].ok()
    assert observed[0].work_id == ticket.work_id
    assert queue.result_for_work_id(ticket.work_id) == observed[0]
    queue.shutdown()


def test_supersede_key_cancels_stale_pending_review_work() -> None:
    base_queue = YTCEWorkQueue(idle_timeout_seconds=0.05)
    queue = ProfileMediaDatabaseRuntimeQueue(base_queue)
    release = threading.Event()
    ran: list[str] = []
    done = threading.Event()

    base_queue.add("Block profile media queue", lambda: release.wait(2.0), priority=YTCEQueuePriority.HIGH)
    stale = queue.submit_operation(
        label="Review stale folder plan",
        operation_kind="build_folder_operations_plan",
        func=lambda: ran.append("stale"),
        supersede_key="folder-review",
    )
    fresh = queue.submit_operation(
        label="Review fresh folder plan",
        operation_kind="build_folder_operations_plan",
        func=lambda: (ran.append("fresh"), "fresh-result")[-1],
        supersede_key="folder-review",
        on_done=lambda result: done.set(),
    )
    release.set()
    assert done.wait(2.0)
    assert ran == ["fresh"]
    history = {item.work_id: item for item in base_queue.history()}
    assert history[stale.work_id].status is YTCEWorkStatus.SUPERSEDED
    assert history[fresh.work_id].status is YTCEWorkStatus.FINISHED
    queue.shutdown()


def test_default_queue_is_singleton() -> None:
    one = default_profile_media_database_runtime_queue()
    two = default_profile_media_database_runtime_queue()
    assert one is two


def main() -> None:
    tests = [
        test_run_operation_wait_returns_uniform_payload,
        test_run_operation_wait_isolates_exception_as_failed_result,
        test_async_submit_returns_ticket_and_converts_done_result,
        test_supersede_key_cancels_stale_pending_review_work,
        test_default_queue_is_singleton,
    ]
    for test in tests:
        test()
    default_profile_media_database_runtime_queue().shutdown()
    print("profile_media_database_runtime_queue_test.py: OK")


if __name__ == "__main__":
    main()
