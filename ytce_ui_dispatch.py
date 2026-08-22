from __future__ import annotations

"""Tk UI dispatcher modeled after AppWork/JDownloader EDT helpers.

V80M source pattern reviewed:
- org.appwork.utils.swing.EDT
- org.appwork.utils.swing.EDTHelper
- org.appwork.utils.swing.EDTRunner

Python/Tk implementation:
- Tk root.after(...) replaces SwingUtilities.invokeLater(...);
- call_sync mirrors EDTHelper.getReturnValue()/waitForEDT at a safe Python level;
- callbacks are exception-isolated and optionally logged.
"""

from dataclasses import dataclass, field
import threading
import time
import traceback
from typing import Any, Callable
from uuid import uuid4


@dataclass(slots=True)
class YTCEDispatchCall:
    label: str
    callback: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: f"ytce.ui.{uuid4().hex[:12]}")
    scheduled_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    finished_at: float | None = None
    result: Any = None
    error: BaseException | None = None
    error_text: str = ""
    done: threading.Event = field(default_factory=threading.Event, repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "label": self.label,
            "scheduled_at": self.scheduled_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error_text": self.error_text,
        }


class YTCEUiDispatcher:
    """Small, explicit UI-thread handoff for Tk code.

    The dispatcher is intentionally thin. It centralizes the rule that Tk widget mutation
    must be scheduled back through the Tk owner thread instead of being performed directly
    from arbitrary worker threads.
    """

    def __init__(self, root: Any | None = None, *, logger: Callable[[str], None] | None = None) -> None:
        self._root = root
        self._logger = logger
        self._ui_thread_id = threading.get_ident()
        self._last_calls: list[YTCEDispatchCall] = []
        self._last_calls_limit = 50

    def bind_root(self, root: Any) -> None:
        self._root = root
        self._ui_thread_id = threading.get_ident()

    @property
    def root(self) -> Any | None:
        return self._root

    def is_ui_thread(self) -> bool:
        return threading.get_ident() == self._ui_thread_id

    def call_soon(self, callback: Callable[..., Any], *args: Any, label: str | None = None, **kwargs: Any) -> YTCEDispatchCall:
        call = YTCEDispatchCall(label=label or getattr(callback, "__name__", "ui_callback"), callback=callback, args=tuple(args), kwargs=dict(kwargs))
        self._remember(call)
        root = self._root
        if root is None:
            self._run_call(call)
            return call
        root.after(0, lambda: self._run_call(call))
        return call

    def call_later(self, delay_ms: int, callback: Callable[..., Any], *args: Any, label: str | None = None, **kwargs: Any) -> YTCEDispatchCall:
        call = YTCEDispatchCall(label=label or getattr(callback, "__name__", "ui_callback"), callback=callback, args=tuple(args), kwargs=dict(kwargs))
        self._remember(call)
        root = self._root
        if root is None:
            self._run_call(call)
            return call
        root.after(max(0, int(delay_ms)), lambda: self._run_call(call))
        return call

    def call_sync(
        self,
        callback: Callable[..., Any],
        *args: Any,
        label: str | None = None,
        timeout: float | None = 5.0,
        **kwargs: Any,
    ) -> Any:
        if self.is_ui_thread() or self._root is None:
            call = YTCEDispatchCall(label=label or getattr(callback, "__name__", "ui_callback"), callback=callback, args=tuple(args), kwargs=dict(kwargs))
            self._remember(call)
            self._run_call(call)
        else:
            call = self.call_soon(callback, *args, label=label, **kwargs)
            if not call.done.wait(timeout):
                raise TimeoutError(f"Timed out waiting for UI dispatch: {call.label}")
        if call.error is not None:
            raise RuntimeError(call.error_text) from call.error
        return call.result

    def recent_calls(self) -> tuple[YTCEDispatchCall, ...]:
        return tuple(self._last_calls)

    def _run_call(self, call: YTCEDispatchCall) -> None:
        call.started_at = time.monotonic()
        try:
            call.result = call.callback(*call.args, **call.kwargs)
        except BaseException as exc:
            call.error = exc
            call.error_text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self._log(f"YTCE UI callback isolated: {call.label}: {call.error_text}")
        finally:
            call.finished_at = time.monotonic()
            call.done.set()

    def _remember(self, call: YTCEDispatchCall) -> None:
        self._last_calls.append(call)
        if len(self._last_calls) > self._last_calls_limit:
            del self._last_calls[: len(self._last_calls) - self._last_calls_limit]

    def _log(self, message: str) -> None:
        if self._logger is None:
            return
        try:
            self._logger(message)
        except BaseException:
            pass
