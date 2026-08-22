from __future__ import annotations

from ytce_slow_tk_detector import YTCESlowTkDetector


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance_ms(self, ms: int) -> None:
        self.value += ms / 1000.0


class FakeTkRoot:
    def __init__(self) -> None:
        self.calls: list[tuple[int, object]] = []
        self.cancelled: list[object] = []
        self.next_id = 1

    def after(self, delay_ms: int, callback):
        call_id = f"after-{self.next_id}"
        self.next_id += 1
        self.calls.append((delay_ms, callback))
        return call_id

    def after_cancel(self, after_id):
        self.cancelled.append(after_id)

    def pop_callback(self):
        return self.calls.pop(0)[1]


def test_detector_logs_only_once_until_heartbeat_recovers() -> None:
    clock = FakeClock()
    root = FakeTkRoot()
    logs: list[str] = []
    detector = YTCESlowTkDetector(root, threshold_ms=100, interval_ms=50, logger=logs.append, clock=clock)
    detector.start()

    assert root.calls[0][0] == 50
    clock.advance_ms(250)
    root.pop_callback()()
    assert len(logs) == 1
    assert "delay=" in logs[0]
    assert detector.last_event is not None
    assert detector.last_event.delay_ms >= 100

    clock.advance_ms(250)
    root.pop_callback()()
    assert len(logs) == 1

    clock.advance_ms(50)
    root.pop_callback()()
    assert len(logs) == 1

    clock.advance_ms(250)
    root.pop_callback()()
    assert len(logs) == 2


def test_detector_stop_cancels_scheduled_after() -> None:
    clock = FakeClock()
    root = FakeTkRoot()
    detector = YTCESlowTkDetector(root, clock=clock)
    detector.start()
    scheduled_id = detector._after_id
    detector.stop()
    assert detector.running is False
    assert scheduled_id in root.cancelled


def run_self_test() -> None:
    test_detector_logs_only_once_until_heartbeat_recovers()
    test_detector_stop_cancels_scheduled_after()


if __name__ == "__main__":
    run_self_test()
    print("ytce_slow_tk_detector_test.py: OK")
