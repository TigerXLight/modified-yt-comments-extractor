from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from twitter_browser_capture_strategy import (
    TwitterBrowserCapturePlan,
    TwitterNetworkPageBoundary,
    build_twitter_browser_capture_plan,
    record_browser_network_page_boundary,
)
from twitter_media_backend import run_twitter_media_download_via_shared_backend


TWITTER_BROWSER_CAPTURE_RUNNER_SCHEMA_VERSION = "twitter_browser_capture_runner.v71"
MAX_CAPTURED_BODY_CHARS = 2_000_000
TWITTER_API_QUERY_NAMES = (
    "TweetDetail",
    "TweetResultByRestId",
    "TweetResultsByRestIds",
    "UserTweets",
    "UserTweetsAndReplies",
    "UserMedia",
    "ListLatestTweetsTimeline",
    "ListTimeline",
    "ListTweets",
    "Bookmarks",
    "BookmarkTimeline",
    "Favorites",
    "Likes",
    "UserLikes",
    "Article",
    "ArticleByRestId",
    "SearchTimeline",
)


@dataclass(frozen=True)
class TwitterCapturedNetworkEvent:
    url: str
    method: str = "GET"
    status: int = 0
    resource_type: str = ""
    content_type: str = ""
    query_name: str = ""
    body_text: str = ""
    body_sha256: str = ""
    captured_at_unix: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        if data.get("body_text") and len(str(data["body_text"])) > 2000:
            data["body_text"] = str(data["body_text"])[:2000] + "...[truncated]"
        return data


@dataclass(frozen=True)
class TwitterApiPage:
    query_name: str
    source_url: str
    page_number: int
    returned_items_count: int
    cursor_in: str = ""
    cursor_out: str = ""
    response_status: int = 0
    rate_limited: bool = False
    body_json: dict[str, Any] | list[Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterMediaInventoryItem:
    media_id: str
    media_type: str
    source_url: str
    media_url: str
    preview_url: str = ""
    content_type: str = ""
    bitrate: int = 0
    width: int = 0
    height: int = 0
    from_query_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class BrowserCapturePayload:
    events: tuple[TwitterCapturedNetworkEvent, ...]
    final_url: str = ""
    final_dom: str = ""
    screenshot_bytes_b64: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterBrowserCaptureRunResult:
    schema_version: str
    status: str
    source_url: str
    canonical_url: str
    output_dir: str
    plan: TwitterBrowserCapturePlan
    network_events_path: str = ""
    api_pages_path: str = ""
    cursor_boundaries_path: str = ""
    media_inventory_path: str = ""
    manifest_path: str = ""
    rendered_dom_path: str = ""
    screenshot_path: str = ""
    api_page_count: int = 0
    network_event_count: int = 0
    media_item_count: int = 0
    boundaries: tuple[TwitterNetworkPageBoundary, ...] = ()
    media_backend_result_paths: tuple[str, ...] = ()
    completion_state: str = ""
    evidence_completion_claim: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


BrowserCaptureExecutor = Callable[[TwitterBrowserCapturePlan], BrowserCapturePayload]


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def extract_twitter_api_query_name(url: str) -> str:
    raw = str(url or "")
    path = urlsplit(raw).path
    match = re.search(r"/graphql/[^/]+/([^/?#]+)", path)
    if match:
        return match.group(1)
    for name in TWITTER_API_QUERY_NAMES:
        if name.lower() in raw.lower():
            return name
    if "/i/api/" in raw or "api.x.com" in raw or "api.twitter.com" in raw:
        return "twitter_api"
    return ""


def is_twitter_network_url(url: str) -> bool:
    host = urlsplit(str(url or "")).netloc.lower()
    return any(part in host for part in ("x.com", "twitter.com", "twimg.com"))


def _json_loads_maybe(text: str) -> Any | None:
    stripped = str(text or "").strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _walk_json(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def _find_bottom_cursor(value: Any) -> str:
    for node in _walk_json(value):
        if not isinstance(node, Mapping):
            continue
        cursor_type = str(node.get("cursorType") or node.get("cursor_type") or "").lower()
        entry_id = str(node.get("entryId") or node.get("entry_id") or "").lower()
        if cursor_type == "bottom" or "cursor-bottom" in entry_id or entry_id.endswith("bottom-0"):
            cursor_value = node.get("value") or node.get("cursor") or node.get("cursorValue")
            if cursor_value:
                return str(cursor_value)
        content = node.get("content")
        if isinstance(content, Mapping):
            ctype = str(content.get("cursorType") or "").lower()
            if ctype == "bottom" and content.get("value"):
                return str(content["value"])
    return ""


def _count_tweet_like_items(value: Any) -> int:
    count = 0
    for node in _walk_json(value):
        if not isinstance(node, Mapping):
            continue
        typename = str(node.get("__typename") or node.get("type") or "").lower()
        if typename in {"tweet", "tweetwithvisibilityresults"}:
            count += 1
            continue
        if "tweet_results" in node or "tweetResult" in node:
            count += 1
    return count


def build_api_pages_from_events(events: Sequence[TwitterCapturedNetworkEvent], *, source_url: str) -> tuple[TwitterApiPage, ...]:
    pages: list[TwitterApiPage] = []
    query_counts: dict[str, int] = {}
    for event in events:
        query = event.query_name or extract_twitter_api_query_name(event.url)
        if not query or ("api" not in query.lower() and query not in TWITTER_API_QUERY_NAMES):
            continue
        body = _json_loads_maybe(event.body_text)
        if body is None:
            continue
        query_counts[query] = query_counts.get(query, 0) + 1
        pages.append(
            TwitterApiPage(
                query_name=query,
                source_url=source_url,
                page_number=query_counts[query],
                returned_items_count=_count_tweet_like_items(body),
                cursor_out=_find_bottom_cursor(body),
                response_status=int(event.status or 0),
                rate_limited=int(event.status or 0) in {403, 429},
                body_json=body,
            )
        )
    return tuple(pages)


def build_boundaries_from_api_pages(pages: Sequence[TwitterApiPage]) -> tuple[TwitterNetworkPageBoundary, ...]:
    boundaries: list[TwitterNetworkPageBoundary] = []
    by_query: dict[str, list[TwitterApiPage]] = {}
    for page in pages:
        by_query.setdefault(page.query_name, []).append(page)
    for query, query_pages in by_query.items():
        for index, page in enumerate(query_pages):
            has_next_page = index + 1 < len(query_pages)
            boundaries.append(
                record_browser_network_page_boundary(
                    query_name=query,
                    source_url=page.source_url,
                    page_number=page.page_number,
                    returned_items_count=page.returned_items_count,
                    cursor_in=page.cursor_in,
                    cursor_out=page.cursor_out,
                    next_page_requested=bool(page.cursor_out),
                    next_page_returned_data=has_next_page,
                    rate_limited=page.rate_limited,
                    http_status=page.response_status,
                )
            )
    return tuple(boundaries)


def _media_id(node: Mapping[str, Any]) -> str:
    for key in ("id_str", "media_id_string", "media_key", "id", "media_id"):
        if node.get(key):
            return str(node[key])
    return ""


def extract_media_inventory_from_api_pages(pages: Sequence[TwitterApiPage]) -> tuple[TwitterMediaInventoryItem, ...]:
    items: list[TwitterMediaInventoryItem] = []
    seen: set[tuple[str, str]] = set()
    for page in pages:
        body = page.body_json
        for node in _walk_json(body):
            if not isinstance(node, Mapping):
                continue
            media_type = str(node.get("type") or node.get("media_type") or "")
            preview = str(node.get("media_url_https") or node.get("media_url") or "")
            media_id = _media_id(node)
            if preview:
                key = (media_id, preview)
                if key not in seen:
                    seen.add(key)
                    items.append(
                        TwitterMediaInventoryItem(
                            media_id=media_id,
                            media_type=media_type or "image",
                            source_url=page.source_url,
                            media_url=preview,
                            preview_url=preview,
                            from_query_name=page.query_name,
                        )
                    )
            video_info = node.get("video_info")
            if isinstance(video_info, Mapping):
                for variant in video_info.get("variants", ()) or ():
                    if not isinstance(variant, Mapping) or not variant.get("url"):
                        continue
                    variant_url = str(variant["url"])
                    key = (media_id, variant_url)
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append(
                        TwitterMediaInventoryItem(
                            media_id=media_id,
                            media_type=media_type or "video",
                            source_url=page.source_url,
                            media_url=variant_url,
                            preview_url=preview,
                            content_type=str(variant.get("content_type") or ""),
                            bitrate=int(variant.get("bitrate") or 0),
                            from_query_name=page.query_name,
                        )
                    )
    return tuple(items)


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _playwright_browser_capture_executor(plan: TwitterBrowserCapturePlan, *, headless: bool = False, timeout_ms: int = 60000, scroll_steps: int = 3) -> BrowserCapturePayload:
    from playwright.sync_api import sync_playwright

    events: list[TwitterCapturedNetworkEvent] = []
    warnings: list[str] = []
    errors: list[str] = []
    final_url = ""
    final_dom = ""
    screenshot_b64 = ""

    def capture_response(response: Any) -> None:
        try:
            url = str(response.url)
            if not is_twitter_network_url(url):
                return
            headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
            content_type = headers.get("content-type", "")
            query_name = extract_twitter_api_query_name(url)
            body_text = ""
            if query_name or "json" in content_type:
                try:
                    body_text = response.text()
                except Exception as exc:  # pragma: no cover - depends on browser runtime
                    warnings.append(f"response_body_unavailable:{url}:{exc}")
                if len(body_text) > MAX_CAPTURED_BODY_CHARS:
                    body_text = body_text[:MAX_CAPTURED_BODY_CHARS]
            events.append(
                TwitterCapturedNetworkEvent(
                    url=url,
                    method=str(getattr(response.request, "method", "GET")),
                    status=int(response.status or 0),
                    resource_type=str(getattr(response.request, "resource_type", "")),
                    content_type=content_type,
                    query_name=query_name,
                    body_text=body_text,
                    body_sha256=_sha256_text(body_text) if body_text else "",
                    captured_at_unix=time.time(),
                )
            )
        except Exception as exc:  # pragma: no cover - defensive browser hook
            warnings.append(f"capture_response_failed:{exc}")

    with sync_playwright() as playwright:
        if plan.browser_session.user_data_dir:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=plan.browser_session.user_data_dir,
                headless=headless,
            )
            browser = None
        else:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context()
        try:
            page = context.new_page()
            page.on("response", capture_response)
            page.goto(plan.canonical_url, wait_until="domcontentloaded", timeout=timeout_ms)
            for _ in range(max(0, int(scroll_steps))):
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(1200)
            final_url = str(page.url)
            try:
                final_dom = page.content()
            except Exception as exc:  # pragma: no cover
                warnings.append(f"dom_capture_failed:{exc}")
            try:
                screenshot_b64 = base64.b64encode(page.screenshot(full_page=True)).decode("ascii")
            except Exception as exc:  # pragma: no cover
                warnings.append(f"screenshot_failed:{exc}")
        except Exception as exc:
            errors.append(str(exc))
        finally:
            context.close()
            if browser is not None:
                browser.close()

    return BrowserCapturePayload(
        events=tuple(events),
        final_url=final_url,
        final_dom=final_dom,
        screenshot_bytes_b64=screenshot_b64,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def run_twitter_browser_capture(
    *,
    source_url: str,
    output_dir: str | Path,
    capture_goal: str = "",
    list_workaround_url: str = "",
    browser_executor: BrowserCaptureExecutor | None = None,
    live: bool = False,
    headless: bool = False,
    timeout_ms: int = 60000,
    scroll_steps: int = 3,
    download_media: bool = False,
    media_backend_runner: Any | None = None,
) -> TwitterBrowserCaptureRunResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    plan = build_twitter_browser_capture_plan(
        source_url,
        capture_goal=capture_goal,
        list_workaround_url=list_workaround_url,
    )
    warnings: list[str] = []
    errors: list[str] = []
    if browser_executor is not None:
        payload = browser_executor(plan)
    elif live:
        try:
            payload = _playwright_browser_capture_executor(plan, headless=headless, timeout_ms=timeout_ms, scroll_steps=scroll_steps)
        except ModuleNotFoundError as exc:
            payload = BrowserCapturePayload(events=(), errors=(f"playwright_unavailable:{exc}",))
    else:
        payload = BrowserCapturePayload(events=(), warnings=("live_browser_capture_not_requested",))

    warnings.extend(payload.warnings)
    errors.extend(payload.errors)
    pages = build_api_pages_from_events(payload.events, source_url=plan.canonical_url)
    boundaries = build_boundaries_from_api_pages(pages)
    media_items = extract_media_inventory_from_api_pages(pages)

    network_path = output / "network_events.jsonl"
    api_pages_path = output / "api_pages.jsonl"
    boundaries_path = output / "cursor_boundaries.json"
    media_path = output / "media_inventory.json"
    manifest_path = output / "browser_session_manifest.json"
    dom_path = output / "rendered_dom_snapshot.html"
    screenshot_path = output / "screenshot.png"

    _write_jsonl(network_path, (event.to_dict() for event in payload.events))
    _write_jsonl(api_pages_path, (page.to_dict() for page in pages))
    _write_json(boundaries_path, [boundary.to_dict() for boundary in boundaries])
    _write_json(media_path, [item.to_dict() for item in media_items])
    if payload.final_dom:
        dom_path.write_text(payload.final_dom, encoding="utf-8")
    if payload.screenshot_bytes_b64:
        screenshot_path.write_bytes(base64.b64decode(payload.screenshot_bytes_b64))

    backend_paths: list[str] = []
    if download_media and media_items:
        try:
            backend_result = run_twitter_media_download_via_shared_backend(
                source_url=plan.canonical_url,
                output_dir=output / "media_downloads",
                shared_backend_runner=media_backend_runner,
            )
            backend_result_path = output / "shared_media_backend_result.json"
            _write_json(backend_result_path, backend_result.to_dict())
            backend_paths.append(str(backend_result_path))
        except Exception as exc:
            errors.append(f"shared_media_backend_failed:{exc}")

    if errors:
        status = "failed"
        completion = "failed"
        claim = "not_completed"
    elif payload.events:
        status = "success"
        if boundaries:
            completion = "captured_with_boundaries"
        else:
            completion = "captured_without_api_page_boundary"
        claim = "completed" if media_items or pages else "needs_review"
    else:
        status = "planned"
        completion = "not_run"
        claim = "not_completed"

    result = TwitterBrowserCaptureRunResult(
        schema_version=TWITTER_BROWSER_CAPTURE_RUNNER_SCHEMA_VERSION,
        status=status,
        source_url=source_url,
        canonical_url=plan.canonical_url,
        output_dir=str(output),
        plan=plan,
        network_events_path=str(network_path),
        api_pages_path=str(api_pages_path),
        cursor_boundaries_path=str(boundaries_path),
        media_inventory_path=str(media_path),
        manifest_path=str(manifest_path),
        rendered_dom_path=str(dom_path) if payload.final_dom else "",
        screenshot_path=str(screenshot_path) if payload.screenshot_bytes_b64 else "",
        api_page_count=len(pages),
        network_event_count=len(payload.events),
        media_item_count=len(media_items),
        boundaries=tuple(boundaries),
        media_backend_result_paths=tuple(backend_paths),
        completion_state=completion,
        evidence_completion_claim=claim,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )
    _write_json(manifest_path, result.to_dict())
    return result
