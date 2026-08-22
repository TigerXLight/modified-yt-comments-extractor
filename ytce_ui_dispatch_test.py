from __future__ import annotations

import threading

from ytce_ui_dispatch import YTCEUiDispatcher


class FakeTkRoot:
    def __init__(self) -> None:
        self.calls: list[tuple[int, object]] = []
        self.next_id = 1

    def after(self, delay_ms: int, callback):
        call_id = f"after-{self.next_id}"
        self.next_id += 1
        self.calls.append((delay_ms, callback))
        return call_id

    def run_next(self) -> None:
        _delay, callback = self.calls.pop(0)
        callback()

    def run_all(self) -> None:
        while self.calls:
            self.run_next()


def test_call_soon_uses_tk_after_and_isolates_errors() -> None:
    root = FakeTkRoot()
    logs: list[str] = []
    dispatcher = YTCEUiDispatcher(root, logger=logs.append)
    seen: list[str] = []

    call = dispatcher.call_soon(lambda value: seen.append(value), "ok", label="append")
    assert root.calls[0][0] == 0
    root.run_next()
    assert call.done.is_set()
    assert seen == ["ok"]

    bad = dispatcher.call_soon(lambda: (_ for _ in ()).throw(ValueError("bad ui")), label="bad")
    root.run_next()
    assert bad.error is not None
    assert any("bad ui" in line for line in logs)


def test_call_later_preserves_delay() -> None:
    root = FakeTkRoot()
    dispatcher = YTCEUiDispatcher(root)
    dispatcher.call_later(35, lambda: None, label="later")
    assert root.calls[0][0] == 35


def test_call_sync_runs_immediately_on_ui_thread() -> None:
    dispatcher = YTCEUiDispatcher()
    assert dispatcher.call_sync(lambda: "value", label="sync") == "value"
    assert dispatcher.recent_calls()[-1].label == "sync"


def test_call_sync_from_worker_waits_for_after_callback() -> None:
    root = FakeTkRoot()
    dispatcher = YTCEUiDispatcher(root)
    result: list[str] = []
    error: list[BaseException] = []

    def worker() -> None:
        try:
            result.append(dispatcher.call_sync(lambda: "worker-ok", label="worker-sync", timeout=2.0))
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    while not root.calls:
        pass
    root.run_next()
    thread.join(2.0)
    assert not error
    assert result == ["worker-ok"]


def run_self_test() -> None:
    test_call_soon_uses_tk_after_and_isolates_errors()
    test_call_later_preserves_delay()
    test_call_sync_runs_immediately_on_ui_thread()
    test_call_sync_from_worker_waits_for_after_callback()


if __name__ == "__main__":
    run_self_test()
    print("ytce_ui_dispatch_test.py: OK")
