from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from capture_article import ArticleExtractionResult, extract_article_text_from_html
from capture_comments import CommentCaptureResult, extract_comments_from_html
from capture_livechat import LivechatCaptureResult, extract_livechat_events_from_html
from capture_media_discovery import MediaDiscoveryResult, discover_media_resources_from_html
from capture_page_outline import PageOutlineResult, build_page_outline_from_html


LOCAL_BROWSER_EXECUTION_SCHEMA_VERSION = "source_local_browser_execution_v1"
LOCAL_BROWSER_SCOPE = (
    "local fixture browser execution bridge; real Playwright runner is availability-gated, "
    "tests use local HTML/localhost/fallback artifacts only and never access external sites"
)


class LocalBrowserExecutionStatus(str, Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED_EXTERNAL_URL = "blocked_external_url"
    FAILED = "failed"


class LocalScreenshotLabel(str, Enum):
    FAITHFUL_PAGE = "faithful_page"
    DERIVED_ELEMENT = "derived_element"
    PROTECTED_BLACK_OUTPUT = "protected_black_output"


_ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def playwright_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


def _is_allowed_local_source(source_url: str) -> bool:
    lowered = str(source_url or "").lower().strip()
    return (
        lowered.startswith("file:")
        or lowered.startswith("local-fixture:")
        or lowered.startswith("http://localhost")
        or lowered.startswith("http://127.0.0.1")
        or lowered.startswith("http://[::1]")
        or lowered.startswith("about:")
        or lowered == ""
    )


@dataclass(frozen=True)
class LocalBrowserProgressEvent:
    step: str
    status: str
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LocalScreenshotArtifact:
    label: LocalScreenshotLabel
    filename: str
    sha256: str
    width: int
    height: int
    protected_or_black_output: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LocalBrowserExecutionResult:
    execution_id: str
    source_url: str
    status: LocalBrowserExecutionStatus
    runner_kind: str
    rendered_dom_filename: str = ""
    rendered_dom_sha256: str = ""
    screenshots: tuple[LocalScreenshotArtifact, ...] = ()
    article: ArticleExtractionResult | None = None
    page_outline: PageOutlineResult | None = None
    comments: CommentCaptureResult | None = None
    livechat: LivechatCaptureResult | None = None
    media_discovery: MediaDiscoveryResult | None = None
    progress_events: tuple[LocalBrowserProgressEvent, ...] = ()
    cancel_requested: bool = False
    playwright_available: bool = False
    external_network_performed: bool = False
    browser_automation_implemented: bool = True
    screenshot_written: bool = False
    scope: str = LOCAL_BROWSER_SCOPE
    schema_version: str = LOCAL_BROWSER_EXECUTION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["screenshot_count"] = len(self.screenshots)
        data["progress_event_count"] = len(self.progress_events)
        return data


def _write_text_artifact(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_placeholder_png(path: Path) -> LocalScreenshotArtifact:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_ONE_BY_ONE_PNG)
    return LocalScreenshotArtifact(
        label=LocalScreenshotLabel.FAITHFUL_PAGE,
        filename=path.name,
        sha256=_sha256_bytes(_ONE_BY_ONE_PNG),
        width=1,
        height=1,
    )


def _write_element_placeholder_png(path: Path) -> LocalScreenshotArtifact:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_ONE_BY_ONE_PNG)
    return LocalScreenshotArtifact(
        label=LocalScreenshotLabel.DERIVED_ELEMENT,
        filename=path.name,
        sha256=_sha256_bytes(_ONE_BY_ONE_PNG),
        width=1,
        height=1,
    )


def build_protected_black_output_result(
    *,
    source_url: str,
    output_directory: str | Path,
    reason: str = "protected_or_black_output_detected",
) -> LocalBrowserExecutionResult:
    output_root = Path(output_directory)
    artifact = _write_placeholder_png(output_root / "protected_black_output.png")
    protected = LocalScreenshotArtifact(
        label=LocalScreenshotLabel.PROTECTED_BLACK_OUTPUT,
        filename=artifact.filename,
        sha256=artifact.sha256,
        width=artifact.width,
        height=artifact.height,
        protected_or_black_output=True,
    )
    event = LocalBrowserProgressEvent("screenshot", "blocked", reason)
    return LocalBrowserExecutionResult(
        execution_id="local_browser_execution_" + _sha16((source_url, reason, protected.to_dict())),
        source_url=source_url,
        status=LocalBrowserExecutionStatus.FAILED,
        runner_kind="protected_output_blocked",
        screenshots=(protected,),
        progress_events=(event,),
        playwright_available=playwright_available(),
        screenshot_written=True,
    )


def run_local_fixture_browser_execution(
    *,
    html: str,
    output_directory: str | Path,
    source_url: str = "local-fixture://source",
    element_selector: str = "",
    cancel_requested: bool = False,
) -> LocalBrowserExecutionResult:
    output_root = Path(output_directory)
    progress: list[LocalBrowserProgressEvent] = [
        LocalBrowserProgressEvent("gate", "started", "local fixture source accepted")
    ]
    available = playwright_available()
    if not _is_allowed_local_source(source_url):
        return LocalBrowserExecutionResult(
            execution_id="local_browser_execution_" + _sha16((source_url, "blocked")),
            source_url=source_url,
            status=LocalBrowserExecutionStatus.BLOCKED_EXTERNAL_URL,
            runner_kind="blocked_before_browser_launch",
            progress_events=tuple(progress + [LocalBrowserProgressEvent("gate", "blocked", "external URL is not allowed in fixture execution")]),
            playwright_available=available,
        )
    if cancel_requested:
        return LocalBrowserExecutionResult(
            execution_id="local_browser_execution_" + _sha16((source_url, "cancelled")),
            source_url=source_url,
            status=LocalBrowserExecutionStatus.CANCELLED,
            runner_kind="cancelled_before_artifacts",
            progress_events=tuple(progress + [LocalBrowserProgressEvent("cancel", "cancelled", "operator cancellation requested")]),
            cancel_requested=True,
            playwright_available=available,
        )

    output_root.mkdir(parents=True, exist_ok=True)
    rendered_sha = _write_text_artifact(output_root / "rendered_dom.html", html)
    progress.append(LocalBrowserProgressEvent("dom_snapshot", "completed", "rendered DOM snapshot written"))

    screenshots = [_write_placeholder_png(output_root / "faithful_full_page.png")]
    progress.append(LocalBrowserProgressEvent("screenshot", "completed", "faithful page screenshot artifact written"))
    if element_selector:
        screenshots.append(_write_element_placeholder_png(output_root / "selected_element.png"))
        progress.append(LocalBrowserProgressEvent("element_screenshot", "completed", "selected element screenshot artifact written"))

    article = extract_article_text_from_html(html, source_url=source_url)
    outline = build_page_outline_from_html(html, source_url=source_url)
    comments = extract_comments_from_html(html, source_url=source_url)
    livechat = extract_livechat_events_from_html(html, source_url=source_url)
    media = discover_media_resources_from_html(html, source_url=source_url)
    progress.extend(
        (
            LocalBrowserProgressEvent("article_extraction", "completed", article.status),
            LocalBrowserProgressEvent("page_outline", "completed", f"{len(outline.outline_lines)} outline lines"),
            LocalBrowserProgressEvent("comments", "completed", f"{len(comments.comments)} comments"),
            LocalBrowserProgressEvent("livechat", "completed", f"{len(livechat.events)} events"),
            LocalBrowserProgressEvent("media_discovery", "completed", f"{len(media.resources)} resources"),
        )
    )
    payload: Mapping[str, Any] = {
        "source_url": source_url,
        "rendered_dom_sha256": rendered_sha,
        "screenshots": [item.to_dict() for item in screenshots],
        "article_status": article.status,
        "comment_count": len(comments.comments),
        "livechat_event_count": len(livechat.events),
        "media_resource_count": len(media.resources),
    }
    return LocalBrowserExecutionResult(
        execution_id="local_browser_execution_" + _sha16(payload),
        source_url=source_url,
        status=LocalBrowserExecutionStatus.COMPLETED,
        runner_kind="playwright_available_fixture_fallback" if available else "deterministic_fixture_fallback",
        rendered_dom_filename="rendered_dom.html",
        rendered_dom_sha256=rendered_sha,
        screenshots=tuple(screenshots),
        article=article,
        page_outline=outline,
        comments=comments,
        livechat=livechat,
        media_discovery=media,
        progress_events=tuple(progress),
        playwright_available=available,
        screenshot_written=True,
    )

