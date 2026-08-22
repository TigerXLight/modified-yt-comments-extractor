from __future__ import annotations

"""Slow Tk-main-thread detector.

V80M source pattern reviewed:
- org.appwork.utils.swing.SlowEDTDetector
- org.appwork.utils.swing.EDTRunner

Python/Tk implementation:
- Tk root.after(...) schedules a periodic heartbeat on the UI thread;
- if the heartbeat arrives late beyond threshold_ms, the detector logs a single stall;
- the log re-arms after a healthy heartbeat, matching the AppWork doLog gating idea.
"""

from dataclasses import dataclass
import threading
import time
from typing import Callable, Any


@dataclass(frozen=True, slots=True)
class YTCETkStallEvent:
    label: str
    expected_at: float
    observed_at: float
    delay_ms: float
    threshold_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "expected_at": self.expected_at,
            "observed_at": self.observed_at,
            "delay_ms": self.delay_ms,
            "threshold_ms": self.threshold_ms,
        }


class YTCESlowTkDetector:
    """Detect delayed Tk heartbeats without touching widgets from a worker thread."""

    def __init__(
        self,
        root: Any,
        *,
        label: str = "YTCE Tk main thread",
        threshold_ms: int = 750,
        interval_ms: int = 250,
        logger: Callable[[str], None] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.root = root
        self.label = label
        self.threshold_ms = max(1, int(threshold_ms))
        self.interval_ms = max(1, int(interval_ms))
        self._logger = logger
        self._clock = clock or time.monotonic
        self._running = False
        self._after_id: Any | None = None
        self._expected_at: float | None = None
        self._log_enabled = True
        self._last_event: YTCETkStallEvent | None = None
        self._owner_thread_id = threading.get_ident()

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_event(self) -> YTCETkStallEvent | None:
        return self._last_event

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._schedule_next()

    def stop(self) -> None:
        self._running = False
        after_id = self._after_id
        self._after_id = None
        if after_id is not None and hasattr(self.root, "after_cancel"):
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass

    def pulse_now_for_test(self) -> None:
        self._tick()

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._expected_at = self._clock() + (self.interval_ms / 1000.0)
        self._after_id = self.root.after(self.interval_ms, self._tick)

    def _tick(self) -> None:
        if not self._running:
            return
        now = self._clock()
        expected = self._expected_at if self._expected_at is not None else now
        delay_ms = max(0.0, (now - expected) * 1000.0)
        if delay_ms >= self.threshold_ms:
            event = YTCETkStallEvent(
                label=self.label,
                expected_at=expected,
                observed_at=now,
                delay_ms=delay_ms,
                threshold_ms=self.threshold_ms,
            )
            self._last_event = event
            if self._log_enabled:
                self._log_enabled = False
                self._log(
                    f"Slow Tk main-thread heartbeat: {self.label}: "
                    f"delay={delay_ms:.1f}ms threshold={self.threshold_ms}ms"
                )
        else:
            self._log_enabled = True
        self._schedule_next()

    def _log(self, message: str) -> None:
        if self._logger is None:
            return
        try:
            self._logger(message)
        except Exception:
            pass
