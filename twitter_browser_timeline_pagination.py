from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

TWITTER_BROWSER_TIMELINE_PAGINATION_SCHEMA_VERSION = "twitter_browser_timeline_pagination.v74"
TIMELINE_PAGE_SCHEMA_VERSION = "twitter_browser_timeline_page.v74"
TIMELINE_ENTRY_SCHEMA_VERSION = "twitter_browser_timeline_entry.v74"
TIMELINE_STATE_SCHEMA_VERSION = "twitter_browser_timeline_pagination_state.v74"
TIMELINE_EXPORT_MANIFEST_SCHEMA_VERSION = "twitter_browser_timeline_export_manifest.v74"

TIMELINE_QUERY_NAMES = (
    "UserTweetsAndReplies",
    "UserRepliesTimeline",
    "UserTweetsTimeline",
    "UserTweets",
    "UserMedia",
    "ListLatestTweetsTimeline",
    "ListTimeline",
    "ListTweets",
    "SearchTimeline",
)

TIMELINE_OUTPUT_FILES = (
    "timeline_pages.jsonl",
    "timeline_entries.jsonl",
    "timeline_pagination_state.json",
    "timeline_export_manifest.json",
)

RXLIULI_BROWSER_SESSION_LIMITATION_NOTE = (
    "Browser-session export records only timeline/reply data that X returns to the logged-in web session. "
    "Algorithmically hidden, suppressed, or unreturned replies cannot be claimed complete by this exporter."
)


@dataclass(frozen=True)
class TwitterTimelineEntry:
    schema_version: str
    status_id: str
    canonical_url: str
    source_url: str
    source_query_name: str
    source_page_number: int
    author_name: str = ""
    screen_name: str = ""
    post_text: str = ""
    created_at: str = ""
    conversation_id: str = ""
    in_reply_to_status_id: str = ""
    in_reply_to_screen_name: str = ""
    reply_count: int | None = None
    retweet_count: int | None = None
    like_count: int | None = None
    quote_count: int | None = None
    bookmark_count: int | None = None
    view_count: str = ""
    links: tuple[str, ...] = ()
    media_urls: tuple[str, ...] = ()
    raw_entry_id: str = ""
    sort_index: str = ""
    provenance: str = "browser_session_graphql_timeline_entry_v74"
    needs_review: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterTimelinePage:
    schema_version: str
    query_name: str
    source_url: str
    page_number: int
    response_status: int = 0
    returned_items_count: int = 0
    cursor_in: str = ""
    cursor_out: str = ""
    top_cursor: str = ""
    bottom_cursor: str = ""
    rate_limited: bool = False
    page_boundary_state: str = ""
    body_sha256: str = ""
    raw_event_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterTimelinePaginationState:
    schema_version: str
    source_url: str
    canonical_url: str
    route_kind: str
    requested_profile_tab: str
    pages_count: int
    entries_count: int
    unique_entries_count: int
    cursor_history: tuple[str, ...]
    last_cursor_out: str = ""
    stop_reason: str = ""
    completeness_state: str = ""
    rate_limited: bool = False
    live_browser_session_required: bool = True
    api_access_required: bool = False
    limitation_notes: tuple[str, ...] = (RXLIULI_BROWSER_SESSION_LIMITATION_NOTE,)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterTimelineExportManifest:
    schema_version: str
    source_url: str
    canonical_url: str
    output_dir: str
    pages_path: str
    entries_path: str
    state_path: str
    network_events_path: str = ""
    api_pages_path: str = ""
    browser_session_manifest_path: str = ""
    capture_status: str = ""
    capture_manifest_path: str = ""
    rxliuli_method: str = "browser_session_web_interface_progressive_scroll"
    files_written: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterTimelinePaginationResult:
    schema_version: str
    status: str
    source_url: str
    canonical_url: str
    output_dir: str
    pages_count: int
    entries_count: int
    unique_entries_count: int
    pages_path: str
    entries_path: str
    state_path: str
    manifest_path: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)



def unwrap_source_url(source_url: str) -> str:
    raw = str(source_url or "").strip()
    markdown = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", raw)
    if markdown:
        return markdown.group(2).strip()
    angle = re.match(r"^<(https?://[^>]+)>$", raw)
    if angle:
        return angle.group(1).strip()
    return raw


def canonicalize_browser_capture_url(source_url: str) -> str:
    raw = unwrap_source_url(source_url)
    if not raw:
        return ""
    parsed = urlsplit(raw)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    if netloc in {"twitter.com", "www.twitter.com", "mobile.twitter.com"}:
        netloc = "x.com"
    if netloc == "www.x.com":
        netloc = "x.com"
    return urlunsplit((scheme, netloc, parsed.path.rstrip("/") or "/", parsed.query, parsed.fragment))



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


def _write_json(path: str | Path, data: Any) -> None:
    Path(path).write_text(json.dumps(_value_for_dict(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: str | Path, rows: Iterable[Any]) -> None:
    with Path(path).open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(_value_for_dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _load_json_text(value: Any) -> dict[str, Any] | list[Any] | None:
    if isinstance(value, (dict, list)):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _walk_json(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def _extract_query_name_from_url(url: str) -> str:
    m = re.search(r"/graphql/[^/?#]+/([^/?#]+)", str(url or ""))
    return m.group(1) if m else ""


def is_timeline_query_name(query_name: str) -> bool:
    name = str(query_name or "")
    if name in TIMELINE_QUERY_NAMES:
        return True
    lower = name.lower()
    if lower.startswith("user") and any(token in lower for token in ("tweet", "repl", "media")) and "timeline" in lower:
        return True
    if lower.startswith("list") and "timeline" in lower:
        return True
    return lower == "searchtimeline"


def _cursor_from_url(url: str) -> str:
    try:
        qs = parse_qs(urlsplit(str(url)).query)
        raw_vars = (qs.get("variables") or [""])[0]
        data = json.loads(raw_vars) if raw_vars else {}
        cursor = data.get("cursor") or data.get("paginationToken") or ""
        return str(cursor or "")
    except Exception:
        return ""


def _cursor_value(node: Mapping[str, Any]) -> str:
    value = node.get("value") or node.get("cursor") or node.get("cursorValue") or ""
    return str(value or "")


def extract_timeline_cursors(body: Any) -> dict[str, str]:
    top = ""
    bottom = ""
    all_values: list[str] = []
    for node in _walk_json(body):
        if not isinstance(node, Mapping):
            continue
        cursor_type = str(node.get("cursorType") or node.get("cursor_type") or "").lower()
        value = _cursor_value(node)
        if not value:
            continue
        all_values.append(value)
        if cursor_type == "top" and not top:
            top = value
        if cursor_type == "bottom" and not bottom:
            bottom = value
    if not bottom and all_values:
        bottom = all_values[-1]
    if not top and all_values:
        top = all_values[0]
    return {"top_cursor": top, "bottom_cursor": bottom, "cursor_out": bottom or top}


def _unwrap_tweet_candidate(node: Mapping[str, Any]) -> Mapping[str, Any] | None:
    candidates: list[Any] = [node]
    if isinstance(node.get("itemContent"), Mapping):
        candidates.append(node["itemContent"])
    if isinstance(node.get("tweet"), Mapping):
        candidates.append(node["tweet"])
    if isinstance(node.get("tweet_results"), Mapping):
        candidates.append(node["tweet_results"])
    for item in list(candidates):
        if isinstance(item, Mapping) and isinstance(item.get("result"), Mapping):
            candidates.append(item["result"])
    for item in list(candidates):
        if not isinstance(item, Mapping):
            continue
        if str(item.get("__typename") or "").lower().endswith("tombstone"):
            continue
        if "tweet" in item and isinstance(item["tweet"], Mapping):
            candidates.append(item["tweet"])
        legacy = item.get("legacy")
        if isinstance(legacy, Mapping):
            status_id = str(item.get("rest_id") or legacy.get("id_str") or legacy.get("id") or "")
            if status_id:
                return item
    return None


def _entry_id_for_node(node: Mapping[str, Any]) -> str:
    return str(node.get("entryId") or node.get("entry_id") or "")


def _sort_index_for_node(node: Mapping[str, Any]) -> str:
    return str(node.get("sortIndex") or node.get("sort_index") or "")


def _user_legacy(tweet: Mapping[str, Any]) -> Mapping[str, Any]:
    core = tweet.get("core")
    if isinstance(core, Mapping):
        user_results = core.get("user_results")
        if isinstance(user_results, Mapping):
            result = user_results.get("result")
            if isinstance(result, Mapping):
                legacy = result.get("legacy")
                if isinstance(legacy, Mapping):
                    return legacy
    user = tweet.get("user")
    if isinstance(user, Mapping):
        legacy = user.get("legacy")
        if isinstance(legacy, Mapping):
            return legacy
    return {}


def _legacy_int(legacy: Mapping[str, Any], key: str) -> int | None:
    value = legacy.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _legacy_links(legacy: Mapping[str, Any]) -> tuple[str, ...]:
    urls: list[str] = []
    entities = legacy.get("entities")
    if isinstance(entities, Mapping):
        for item in entities.get("urls") or ():
            if isinstance(item, Mapping):
                url = str(item.get("expanded_url") or item.get("url") or "")
                if url and url not in urls:
                    urls.append(url)
    return tuple(urls)


def _legacy_media_urls(legacy: Mapping[str, Any]) -> tuple[str, ...]:
    urls: list[str] = []
    entities = legacy.get("extended_entities") or legacy.get("entities")
    if isinstance(entities, Mapping):
        for item in entities.get("media") or ():
            if not isinstance(item, Mapping):
                continue
            for key in ("media_url_https", "media_url", "url"):
                url = str(item.get(key) or "")
                if url and url.startswith(("https://pbs.twimg.com/", "https://video.twimg.com/")) and url not in urls:
                    urls.append(url)
            video_info = item.get("video_info")
            if isinstance(video_info, Mapping):
                for variant in video_info.get("variants") or ():
                    if isinstance(variant, Mapping):
                        url = str(variant.get("url") or "")
                        if url and url.startswith("https://video.twimg.com/") and url not in urls:
                            urls.append(url)
    return tuple(urls)


def _canonical_tweet_url(tweet: Mapping[str, Any], source_url: str, status_id: str, screen_name: str) -> str:
    if screen_name and status_id:
        return f"https://x.com/{screen_name}/status/{status_id}"
    if status_id:
        parsed = urlsplit(canonicalize_browser_capture_url(source_url))
        handle = parsed.path.strip("/").split("/", 1)[0]
        if handle:
            return f"https://x.com/{handle}/status/{status_id}"
    return ""


def extract_timeline_entries_from_body(
    body: Any,
    *,
    source_url: str,
    query_name: str,
    page_number: int,
) -> tuple[TwitterTimelineEntry, ...]:
    entries: list[TwitterTimelineEntry] = []
    seen: set[str] = set()
    for node in _walk_json(body):
        if not isinstance(node, Mapping):
            continue
        tweet = _unwrap_tweet_candidate(node)
        if not tweet:
            continue
        legacy = tweet.get("legacy")
        if not isinstance(legacy, Mapping):
            continue
        status_id = str(tweet.get("rest_id") or legacy.get("id_str") or legacy.get("id") or "")
        if not status_id or status_id in seen:
            continue
        seen.add(status_id)
        user_legacy = _user_legacy(tweet)
        screen_name = str(user_legacy.get("screen_name") or user_legacy.get("screen_name_lower") or "")
        author_name = str(user_legacy.get("name") or "")
        entry_id = _entry_id_for_node(node)
        sort_index = _sort_index_for_node(node)
        views = ""
        views_obj = tweet.get("views")
        if isinstance(views_obj, Mapping):
            views = str(views_obj.get("count") or views_obj.get("state") or "")
        entries.append(
            TwitterTimelineEntry(
                schema_version=TIMELINE_ENTRY_SCHEMA_VERSION,
                status_id=status_id,
                canonical_url=_canonical_tweet_url(tweet, source_url, status_id, screen_name),
                source_url=source_url,
                source_query_name=query_name,
                source_page_number=page_number,
                author_name=author_name,
                screen_name=screen_name,
                post_text=str(legacy.get("full_text") or legacy.get("text") or ""),
                created_at=str(legacy.get("created_at") or ""),
                conversation_id=str(legacy.get("conversation_id_str") or legacy.get("conversation_id") or ""),
                in_reply_to_status_id=str(legacy.get("in_reply_to_status_id_str") or ""),
                in_reply_to_screen_name=str(legacy.get("in_reply_to_screen_name") or ""),
                reply_count=_legacy_int(legacy, "reply_count"),
                retweet_count=_legacy_int(legacy, "retweet_count"),
                like_count=_legacy_int(legacy, "favorite_count"),
                quote_count=_legacy_int(legacy, "quote_count"),
                bookmark_count=_legacy_int(legacy, "bookmark_count"),
                view_count=views,
                links=_legacy_links(legacy),
                media_urls=_legacy_media_urls(legacy),
                raw_entry_id=entry_id,
                sort_index=sort_index,
            )
        )
    return tuple(entries)


def _timeline_rows_from_capture(capture_dir: str | Path) -> tuple[list[dict[str, Any]], str, str]:
    capture = Path(capture_dir)
    api_pages_path = capture / "api_pages.jsonl"
    network_events_path = capture / "network_events.jsonl"
    rows = _read_jsonl(api_pages_path)
    if rows:
        return rows, str(api_pages_path), str(network_events_path if network_events_path.exists() else "")
    events = _read_jsonl(network_events_path)
    converted: list[dict[str, Any]] = []
    for index, event in enumerate(events, start=1):
        query_name = str(event.get("query_name") or _extract_query_name_from_url(str(event.get("url") or "")))
        if not is_timeline_query_name(query_name):
            continue
        converted.append(
            {
                "query_name": query_name,
                "source_url": event.get("url") or "",
                "page_number": index,
                "returned_items_count": 0,
                "cursor_in": _cursor_from_url(str(event.get("url") or "")),
                "response_status": int(event.get("status") or 0),
                "rate_limited": int(event.get("status") or 0) == 429,
                "body_json": _load_json_text(event.get("body_text")),
                "body_sha256": event.get("body_sha256") or "",
                "raw_event_url": event.get("url") or "",
            }
        )
    return converted, str(api_pages_path if api_pages_path.exists() else ""), str(network_events_path)


def _read_capture_manifest(capture_dir: str | Path) -> dict[str, Any]:
    path = Path(capture_dir) / "browser_session_manifest.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _profile_tab_url(source_url: str, profile_tab: str) -> str:
    clean = canonicalize_browser_capture_url(source_url)
    tab = str(profile_tab or "").strip().lower()
    if not tab or tab in {"default", "tweets"}:
        return clean
    parsed = urlsplit(clean)
    path = parsed.path.rstrip("/")
    if "/status/" in path:
        return clean
    suffix = {
        "replies": "with_replies",
        "tweets_replies": "with_replies",
        "tweets_and_replies": "with_replies",
        "media": "media",
        "likes": "likes",
    }.get(tab, tab)
    if path.endswith("/" + suffix):
        return clean
    return urlunsplit((parsed.scheme, parsed.netloc, path + "/" + suffix, parsed.query, parsed.fragment))


def export_twitter_timeline_from_capture(
    *,
    capture_dir: str | Path,
    output_dir: str | Path = "",
    source_url: str = "",
    profile_tab: str = "replies",
    max_pages: int = 0,
) -> TwitterTimelinePaginationResult:
    capture = Path(capture_dir)
    output = Path(output_dir) if output_dir else capture
    output.mkdir(parents=True, exist_ok=True)
    capture_manifest = _read_capture_manifest(capture)
    raw_source_url = source_url or str(capture_manifest.get("canonical_url") or capture_manifest.get("source_url") or "")
    canonical_url = _profile_tab_url(raw_source_url, profile_tab) if raw_source_url else ""
    rows, api_pages_path, network_events_path = _timeline_rows_from_capture(capture)
    rows = [row for row in rows if is_timeline_query_name(str(row.get("query_name") or ""))]
    if max_pages and max_pages > 0:
        rows = rows[:max_pages]

    pages: list[TwitterTimelinePage] = []
    entries: list[TwitterTimelineEntry] = []
    unique: dict[str, TwitterTimelineEntry] = {}
    cursor_history: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    for index, row in enumerate(rows, start=1):
        query_name = str(row.get("query_name") or "")
        page_number = int(row.get("page_number") or index)
        body = row.get("body_json")
        if body is None and row.get("body_text"):
            body = _load_json_text(row.get("body_text"))
        cursors = extract_timeline_cursors(body)
        page_entries = extract_timeline_entries_from_body(
            body,
            source_url=canonical_url or raw_source_url,
            query_name=query_name,
            page_number=page_number,
        )
        if cursors.get("cursor_out"):
            cursor_history.append(str(cursors["cursor_out"]))
        response_status = int(row.get("response_status") or row.get("status") or 0)
        rate_limited = bool(row.get("rate_limited")) or response_status == 429
        returned = len(page_entries)
        page_state = "rate_limited" if rate_limited else ("returned_timeline_entries" if returned else "no_timeline_entries_found")
        pages.append(
            TwitterTimelinePage(
                schema_version=TIMELINE_PAGE_SCHEMA_VERSION,
                query_name=query_name,
                source_url=canonical_url or raw_source_url,
                page_number=page_number,
                response_status=response_status,
                returned_items_count=returned,
                cursor_in=str(row.get("cursor_in") or _cursor_from_url(str(row.get("raw_event_url") or row.get("source_url") or ""))),
                cursor_out=str(cursors.get("cursor_out") or row.get("cursor_out") or ""),
                top_cursor=str(cursors.get("top_cursor") or ""),
                bottom_cursor=str(cursors.get("bottom_cursor") or ""),
                rate_limited=rate_limited,
                page_boundary_state=page_state,
                body_sha256=str(row.get("body_sha256") or ""),
                raw_event_url=str(row.get("raw_event_url") or row.get("source_url") or ""),
            )
        )
        for entry in page_entries:
            entries.append(entry)
            unique.setdefault(entry.status_id, entry)

    if not rows:
        warnings.append("no_browser_timeline_graphql_pages_found")
    rate_limited = any(page.rate_limited for page in pages)
    stop_reason = "rate_limited" if rate_limited else ("no_timeline_pages_found" if not pages else "browser_session_capture_boundary")
    if pages and not any(page.cursor_out for page in pages):
        stop_reason = "no_bottom_cursor_observed"
    completeness = "partial_browser_session_timeline_export"
    if pages and any(page.cursor_out for page in pages):
        completeness = "cursor_bounded_partial_browser_session_timeline_export"

    pages_path = output / "timeline_pages.jsonl"
    entries_path = output / "timeline_entries.jsonl"
    state_path = output / "timeline_pagination_state.json"
    manifest_path = output / "timeline_export_manifest.json"

    _write_jsonl(pages_path, (page.to_dict() for page in pages))
    _write_jsonl(entries_path, (entry.to_dict() for entry in entries))
    state = TwitterTimelinePaginationState(
        schema_version=TIMELINE_STATE_SCHEMA_VERSION,
        source_url=raw_source_url,
        canonical_url=canonical_url or raw_source_url,
        route_kind="browser_session_account_timeline_pagination",
        requested_profile_tab=profile_tab,
        pages_count=len(pages),
        entries_count=len(entries),
        unique_entries_count=len(unique),
        cursor_history=tuple(cursor_history),
        last_cursor_out=cursor_history[-1] if cursor_history else "",
        stop_reason=stop_reason,
        completeness_state=completeness,
        rate_limited=rate_limited,
    )
    _write_json(state_path, state)
    manifest = TwitterTimelineExportManifest(
        schema_version=TIMELINE_EXPORT_MANIFEST_SCHEMA_VERSION,
        source_url=raw_source_url,
        canonical_url=canonical_url or raw_source_url,
        output_dir=str(output),
        pages_path=str(pages_path),
        entries_path=str(entries_path),
        state_path=str(state_path),
        network_events_path=network_events_path,
        api_pages_path=api_pages_path,
        browser_session_manifest_path=str(capture / "browser_session_manifest.json") if (capture / "browser_session_manifest.json").exists() else "",
        capture_status=str(capture_manifest.get("status") or ""),
        capture_manifest_path=str(capture / "browser_session_manifest.json") if capture_manifest else "",
        files_written=tuple(str(path) for path in (pages_path, entries_path, state_path, manifest_path)),
        warnings=tuple(warnings),
    )
    _write_json(manifest_path, manifest)

    status = "success" if entries else ("needs_review" if pages else "planned")
    return TwitterTimelinePaginationResult(
        schema_version=TWITTER_BROWSER_TIMELINE_PAGINATION_SCHEMA_VERSION,
        status=status,
        source_url=raw_source_url,
        canonical_url=canonical_url or raw_source_url,
        output_dir=str(output),
        pages_count=len(pages),
        entries_count=len(entries),
        unique_entries_count=len(unique),
        pages_path=str(pages_path),
        entries_path=str(entries_path),
        state_path=str(state_path),
        manifest_path=str(manifest_path),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def run_twitter_browser_timeline_pagination(
    *,
    source_url: str,
    output_dir: str | Path,
    capture_dir: str | Path = "",
    live: bool = False,
    headless: bool = False,
    timeout_ms: int = 90000,
    scroll_steps: int = 8,
    browser_user_data_dir: str | Path = "",
    reuse_existing_profile: bool = False,
    profile_tab: str = "replies",
    max_pages: int = 0,
) -> TwitterTimelinePaginationResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    canonical_url = _profile_tab_url(source_url, profile_tab)
    working_capture = Path(capture_dir) if capture_dir else output
    if live:
        from twitter_browser_capture_runner import run_twitter_browser_capture

        run_twitter_browser_capture(
            source_url=canonical_url,
            output_dir=working_capture,
            capture_goal="browser_session_account_timeline_pagination",
            live=True,
            headless=headless,
            timeout_ms=timeout_ms,
            scroll_steps=scroll_steps,
            browser_user_data_dir=browser_user_data_dir,
            reuse_existing_profile=reuse_existing_profile,
            download_media=False,
        )
    return export_twitter_timeline_from_capture(
        capture_dir=working_capture,
        output_dir=output,
        source_url=canonical_url,
        profile_tab=profile_tab,
        max_pages=max_pages,
    )

# --- V74B response promotion and HAR import ---

NETWORK_RESPONSE_BODIES_FILE = "network_response_bodies.jsonl"


def _timeline_row_from_response_record(record: Mapping[str, Any], *, index: int, default_source_url: str = "") -> dict[str, Any] | None:
    url = str(record.get("url") or record.get("request_url") or record.get("source_url") or "")
    query_name = str(record.get("query_name") or _extract_query_name_from_url(url) or "")
    if not is_timeline_query_name(query_name):
        return None
    body = record.get("body_json")
    if body is None:
        body = _load_json_text(record.get("body_text") or record.get("text") or "")
    status = int(record.get("response_status") or record.get("status") or 0)
    return {
        "query_name": query_name,
        "source_url": url or default_source_url,
        "page_number": int(record.get("page_number") or index),
        "returned_items_count": 0,
        "cursor_in": str(record.get("cursor_in") or _cursor_from_url(url)),
        "cursor_out": str(record.get("cursor_out") or ""),
        "response_status": status,
        "rate_limited": bool(record.get("rate_limited")) or status == 429,
        "body_json": body,
        "body_sha256": str(record.get("body_sha256") or ""),
        "raw_event_url": url,
        "promotion_source": str(record.get("promotion_source") or record.get("schema_version") or "network_or_body_record"),
    }


def _timeline_rows_from_records(records: Sequence[Mapping[str, Any]], *, default_source_url: str = "") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        row = _timeline_row_from_response_record(record, index=index, default_source_url=default_source_url)
        if row is not None:
            rows.append(row)
    return rows


def _read_timeline_rows_from_response_bodies(capture: Path, *, default_source_url: str = "") -> tuple[list[dict[str, Any]], str]:
    path = capture / NETWORK_RESPONSE_BODIES_FILE
    rows = _timeline_rows_from_records(_read_jsonl(path), default_source_url=default_source_url)
    return rows, str(path if path.exists() else "")


def _timeline_rows_from_capture(capture_dir: str | Path) -> tuple[list[dict[str, Any]], str, str]:
    """Read timeline rows from api_pages, raw response bodies, or compact network events.

    V74 returned early when api_pages.jsonl existed, even if it only contained
    unrelated JSON such as hashflags.  V74B first filters to timeline operation
    names and falls back to the raw browser-session body file and then compact
    network_events.jsonl.
    """
    capture = Path(capture_dir)
    api_pages_path = capture / "api_pages.jsonl"
    network_events_path = capture / "network_events.jsonl"
    response_bodies_path = capture / NETWORK_RESPONSE_BODIES_FILE

    api_rows = _timeline_rows_from_records(_read_jsonl(api_pages_path))
    if api_rows:
        return api_rows, str(api_pages_path), str(network_events_path if network_events_path.exists() else "")

    body_rows, body_path = _read_timeline_rows_from_response_bodies(capture)
    if body_rows:
        return body_rows, str(response_bodies_path), str(network_events_path if network_events_path.exists() else "")

    event_rows = _timeline_rows_from_records(_read_jsonl(network_events_path))
    if event_rows:
        return event_rows, str(api_pages_path if api_pages_path.exists() else ""), str(network_events_path)
    return [], str(api_pages_path if api_pages_path.exists() else ""), str(network_events_path if network_events_path.exists() else "")


def _har_content_text(content: Mapping[str, Any]) -> str:
    text = str(content.get("text") or "")
    if content.get("encoding") == "base64" and text:
        try:
            import base64
            return base64.b64decode(text).decode("utf-8", errors="replace")
        except Exception:
            return ""
    return text


def timeline_rows_from_har(har_path: str | Path) -> list[dict[str, Any]]:
    path = Path(har_path)
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    entries = (((data or {}).get("log") or {}).get("entries") or []) if isinstance(data, Mapping) else []
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, Mapping):
            continue
        request = entry.get("request") if isinstance(entry.get("request"), Mapping) else {}
        response = entry.get("response") if isinstance(entry.get("response"), Mapping) else {}
        content = response.get("content") if isinstance(response.get("content"), Mapping) else {}
        url = str(request.get("url") or entry.get("request_url") or "")
        query_name = _extract_query_name_from_url(url)
        if not is_timeline_query_name(query_name):
            continue
        body_text = _har_content_text(content)
        record = {
            "schema_version": "twitter_har_response_body.v74b",
            "url": url,
            "status": int(response.get("status") or 0),
            "content_type": str(content.get("mimeType") or ""),
            "query_name": query_name,
            "body_text": body_text,
            "body_sha256": "",
            "promotion_source": "firefox_or_browser_har_import_v74b",
        }
        row = _timeline_row_from_response_record(record, index=index)
        if row is not None:
            rows.append(row)
    return rows


def write_timeline_capture_from_har(
    *,
    har_path: str | Path,
    capture_dir: str | Path,
    source_url: str,
    profile_tab: str = "replies",
) -> Path:
    capture = Path(capture_dir)
    capture.mkdir(parents=True, exist_ok=True)
    canonical_url = _profile_tab_url(source_url, profile_tab)
    rows = timeline_rows_from_har(har_path)
    _write_jsonl(capture / "api_pages.jsonl", rows)
    _write_jsonl(capture / "network_events.jsonl", [])
    _write_json(
        capture / "browser_session_manifest.json",
        {
            "schema_version": "twitter_browser_capture_runner.v74b.har_import",
            "status": "success" if rows else "needs_review",
            "source_url": source_url,
            "canonical_url": canonical_url,
            "completion_state": "firefox_har_timeline_responses_imported" if rows else "firefox_har_no_timeline_responses_found",
            "har_path": str(har_path),
            "api_page_count": len(rows),
            "rxliuli_method": "browser_session_web_interface_har_import",
            "api_access_required": False,
            "live_browser_session_required": True,
        },
    )
    return capture


def export_twitter_timeline_from_har(
    *,
    har_path: str | Path,
    output_dir: str | Path,
    source_url: str,
    profile_tab: str = "replies",
    max_pages: int = 0,
) -> TwitterTimelinePaginationResult:
    output = Path(output_dir)
    capture = output / "har_import_capture"
    write_timeline_capture_from_har(
        har_path=har_path,
        capture_dir=capture,
        source_url=source_url,
        profile_tab=profile_tab,
    )
    return export_twitter_timeline_from_capture(
        capture_dir=capture,
        output_dir=output,
        source_url=source_url,
        profile_tab=profile_tab,
        max_pages=max_pages,
    )


_v74b_original_run_twitter_browser_timeline_pagination = run_twitter_browser_timeline_pagination


def run_twitter_browser_timeline_pagination(
    *,
    source_url: str,
    output_dir: str | Path,
    capture_dir: str | Path = "",
    live: bool = False,
    headless: bool = False,
    timeout_ms: int = 90000,
    scroll_steps: int = 8,
    browser_user_data_dir: str | Path = "",
    reuse_existing_profile: bool = False,
    profile_tab: str = "replies",
    max_pages: int = 0,
    har_path: str | Path = "",
) -> TwitterTimelinePaginationResult:
    if har_path:
        return export_twitter_timeline_from_har(
            har_path=har_path,
            output_dir=output_dir,
            source_url=source_url,
            profile_tab=profile_tab,
            max_pages=max_pages,
        )
    return _v74b_original_run_twitter_browser_timeline_pagination(
        source_url=source_url,
        output_dir=output_dir,
        capture_dir=capture_dir,
        live=live,
        headless=headless,
        timeout_ms=timeout_ms,
        scroll_steps=scroll_steps,
        browser_user_data_dir=browser_user_data_dir,
        reuse_existing_profile=reuse_existing_profile,
        profile_tab=profile_tab,
        max_pages=max_pages,
    )
