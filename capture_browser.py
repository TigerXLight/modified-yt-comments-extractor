from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from capture_status import (
    CAPTURE_STATUS_DEPENDENCY_MISSING,
    CAPTURE_STATUS_FAILED,
    CAPTURE_STATUS_SUCCESS,
    CAPTURE_STATUS_UNSUPPORTED,
)


BROWSER_RUNTIME_SCOPE = (
    "optional browser runtime; allowed for localhost fixtures only by default; "
    "no external site access, credential access, archive action, download, provider call, "
    "or GUI behavior"
)

BrowserCaptureRunner = Callable[["BrowserCaptureRequest"], Mapping[str, Any]]


@dataclass(frozen=True)
class BrowserCaptureRequest:
    url: str
    wait_until: str = "networkidle"
    timeout_ms: int = 30000
    viewport_width: int = 1280
    viewport_height: int = 720
    screenshot_full_page: bool = True
    allowed_hostnames: tuple[str, ...] = ("127.0.0.1", "localhost", "::1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_hostnames": list(self.allowed_hostnames),
            "screenshot_full_page": self.screenshot_full_page,
            "timeout_ms": self.timeout_ms,
            "url": self.url,
            "viewport_height": self.viewport_height,
            "viewport_width": self.viewport_width,
            "wait_until": self.wait_until,
        }


@dataclass(frozen=True)
class BrowserPageSnapshot:
    status: str
    url: str
    final_url: str = ""
    title: str = ""
    html: str = ""
    text: str = ""
    screenshot_png: bytes = b""
    status_code: int = 0
    engine: str = ""
    warnings: tuple[str, ...] = ()
    scope: str = BROWSER_RUNTIME_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "final_url": self.final_url,
            "html": self.html,
            "scope": self.scope,
            "screenshot_bytes": len(self.screenshot_png),
            "status": self.status,
            "status_code": self.status_code,
            "text": self.text,
            "title": self.title,
            "url": self.url,
            "warnings": list(self.warnings),
        }


def is_allowed_browser_capture_url(url: str, allowed_hostnames: tuple[str, ...]) -> bool:
    parsed = urlsplit(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname in {host.lower() for host in allowed_hostnames}


def _snapshot_from_runner_result(
    request: BrowserCaptureRequest,
    result: Mapping[str, Any],
) -> BrowserPageSnapshot:
    status = str(result.get("status") or CAPTURE_STATUS_SUCCESS)
    warnings = tuple(str(warning) for warning in result.get("warnings", ()) if str(warning))
    return BrowserPageSnapshot(
        status=status,
        url=request.url,
        final_url=str(result.get("final_url") or request.url),
        title=str(result.get("title") or ""),
        html=str(result.get("html") or ""),
        text=str(result.get("text") or ""),
        screenshot_png=bytes(result.get("screenshot_png") or b""),
        status_code=int(result.get("status_code") or 0),
        engine=str(result.get("engine") or "injected_runner"),
        warnings=warnings,
    )


def capture_browser_page(
    request: BrowserCaptureRequest,
    *,
    runner: BrowserCaptureRunner | None = None,
) -> BrowserPageSnapshot:
    if not is_allowed_browser_capture_url(request.url, request.allowed_hostnames):
        return BrowserPageSnapshot(
            status=CAPTURE_STATUS_UNSUPPORTED,
            url=request.url,
            warnings=("Browser capture is restricted to allowed localhost fixture hosts by default.",),
        )

    if runner is not None:
        try:
            return _snapshot_from_runner_result(request, runner(request))
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except Exception:
            return BrowserPageSnapshot(
                status=CAPTURE_STATUS_FAILED,
                url=request.url,
                engine="injected_runner",
                warnings=("Injected browser runner failed with a non-secret exception.",),
            )

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return BrowserPageSnapshot(
            status=CAPTURE_STATUS_DEPENDENCY_MISSING,
            url=request.url,
            engine="playwright",
            warnings=("Playwright is not installed or not importable in this environment.",),
        )

    try:
        return _capture_browser_page_with_playwright(request, sync_playwright)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        raise
    except Exception:
        return BrowserPageSnapshot(
            status=CAPTURE_STATUS_FAILED,
            url=request.url,
            engine="playwright",
            warnings=("Playwright browser capture failed with a non-secret exception.",),
        )


def _capture_browser_page_with_playwright(
    request: BrowserCaptureRequest,
    sync_playwright_factory: Callable[[], Any],
) -> BrowserPageSnapshot:
    with sync_playwright_factory() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(
                viewport={
                    "width": request.viewport_width,
                    "height": request.viewport_height,
                }
            )
            try:
                page = context.new_page()
                response = page.goto(
                    request.url,
                    wait_until=request.wait_until,
                    timeout=request.timeout_ms,
                )
                html = page.content()
                title = page.title()
                text = page.locator("body").inner_text(timeout=request.timeout_ms)
                screenshot = page.screenshot(full_page=request.screenshot_full_page)
                return BrowserPageSnapshot(
                    status=CAPTURE_STATUS_SUCCESS,
                    url=request.url,
                    final_url=page.url,
                    title=title,
                    html=html,
                    text=text,
                    screenshot_png=bytes(screenshot or b""),
                    status_code=int(response.status if response is not None else 0),
                    engine="playwright_chromium",
                    warnings=(),
                )
            finally:
                context.close()
        finally:
            browser.close()
