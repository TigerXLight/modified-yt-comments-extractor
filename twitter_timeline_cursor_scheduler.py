from __future__ import annotations

import base64
import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from twitter_browser_timeline_pagination import (
    RXLIULI_BROWSER_SESSION_LIMITATION_NOTE,
    TIMELINE_ENTRY_SCHEMA_VERSION,
    canonicalize_browser_capture_url,
    extract_timeline_cursors,
    extract_timeline_entries_from_body,
    is_timeline_query_name,
    timeline_rows_from_har,
)

TWITTER_CURSOR_SCHEDULER_SCHEMA_VERSION = "twitter_timeline_cursor_scheduler.v74d"
CURSOR_PAGE_SCHEMA_VERSION = "twitter_timeline_cursor_page.v74d"
CURSOR_STATE_SCHEMA_VERSION = "twitter_timeline_cursor_state.v74d"
CURSOR_MANIFEST_SCHEMA_VERSION = "twitter_timeline_cursor_manifest.v74d"
CURSOR_OUTPUT_FILES = (
    "cursor_pages.jsonl",
    "cursor_entries.jsonl",
    "cursor_scheduler_state.json",
    "cursor_export_manifest.json",
)

SAFE_REPLAY_HEADER_NAMES = {
    "accept",
    "authorization",
    "content-type",
    "x-client-transaction-id",
    "x-client-uuid",
    "x-csrf-token",
    "x-twitter-active-user",
    "x-twitter-auth-type",
    "x-twitter-client-language",
}


@dataclass(frozen=True)
class TwitterCursorPage:
    schema_version: str
    query_name: str
    source_url: str
    page_number: int
    response_status: int
    returned_items_count: int
    unique_items_count: int
    cursor_in: str = ""
    cursor_out: str = ""
    top_cursor: str = ""
    bottom_cursor: str = ""
    rate_limited: bool = False
    page_boundary_state: str = ""
    request_url: str = ""
    body_sha256: str = ""
    delay_ms_after_page: int = 0
    replay_mode: str = "browser_fetch_cursor_page"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterCursorSchedulerState:
    schema_version: str
    source_url: str
    canonical_url: str
    requested_profile_tab: str
    pages_count: int
    entries_count: int
    unique_entries_count: int
    cursor_history: tuple[str, ...]
    last_cursor_out: str = ""
    next_cursor_url: str = ""
    stop_reason: str = ""
    completeness_state: str = "cursor_bounded_partial_browser_session_timeline_export"
    rate_limited: bool = False
    resume_supported: bool = True
    read_only: bool = True
    live_browser_session_required: bool = True
    api_access_required: bool = False
    limitation_notes: tuple[str, ...] = (RXLIULI_BROWSER_SESSION_LIMITATION_NOTE,)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterCursorSchedulerManifest:
    schema_version: str
    source_url: str
    canonical_url: str
    output_dir: str
    pages_path: str
    entries_path: str
    state_path: str
    request_templates_path: str = ""
    seed_capture_dir: str = ""
    har_path: str = ""
    rxliuli_method: str = "cursor_driven_browser_session_graphql_scheduler"
    rate_limit_policy: str = "bounded_sequential_read_only_cursor_requests_with_jitter_and_pause_on_rate_limit"
    files_written: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterCursorSchedulerResult:
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
    stop_reason: str = ""
    next_cursor_url: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(_value_for_dict(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: str | Path, rows: Iterable[Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8", errors="replace")).hexdigest() if text else ""


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


def _query_name_from_url(url: str) -> str:
    import re

    m = re.search(r"/graphql/[^/?#]+/([^/?#]+)", str(url or ""))
    return m.group(1) if m else ""


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


def _cursor_from_url(url: str) -> str:
    try:
        qs = parse_qs(urlsplit(str(url)).query)
        raw_vars = (qs.get("variables") or [""])[0]
        data = json.loads(raw_vars) if raw_vars else {}
        return str(data.get("cursor") or data.get("paginationToken") or "")
    except Exception:
        return ""


def _url_with_cursor(url: str, cursor: str) -> str:
    parsed = urlsplit(str(url or ""))
    qs = parse_qs(parsed.query, keep_blank_values=True)
    raw_vars = (qs.get("variables") or [""])[0]
    variables: dict[str, Any] = {}
    if raw_vars:
        try:
            loaded = json.loads(raw_vars)
            if isinstance(loaded, dict):
                variables = dict(loaded)
        except Exception:
            variables = {}
    variables["cursor"] = cursor
    qs["variables"] = [json.dumps(variables, ensure_ascii=False, separators=(",", ":"))]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(qs, doseq=True), parsed.fragment))


def _headers_for_replay(headers: Mapping[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (headers or {}).items():
        lower = str(key).lower()
        if lower in SAFE_REPLAY_HEADER_NAMES and value is not None:
            out[lower] = str(value)
    out.setdefault("accept", "*/*")
    return out


def _record_body(record: Mapping[str, Any]) -> dict[str, Any] | list[Any] | None:
    body = record.get("body_json")
    if body is not None:
        return body if isinstance(body, (dict, list)) else _load_json_text(body)
    return _load_json_text(record.get("body_text") or record.get("text") or "")


def _record_query_name(record: Mapping[str, Any]) -> str:
    return str(record.get("query_name") or _query_name_from_url(str(record.get("url") or record.get("request_url") or "")) or "")


def _timeline_records_from_capture(capture_dir: str | Path) -> list[dict[str, Any]]:
    capture = Path(capture_dir)
    records: list[dict[str, Any]] = []
    for filename in ("network_response_bodies.jsonl", "api_pages.jsonl", "network_events.jsonl"):
        for row in _read_jsonl(capture / filename):
            query_name = _record_query_name(row)
            if not is_timeline_query_name(query_name):
                continue
            body = _record_body(row)
            if body is None:
                continue
            rec = dict(row)
            rec["query_name"] = query_name
            rec["body_json"] = body
            rec.setdefault("url", row.get("url") or row.get("raw_event_url") or row.get("source_url") or "")
            rec.setdefault("status", row.get("response_status") or row.get("status") or 0)
            rec.setdefault("promotion_source", filename)
            records.append(rec)
    return records


def _timeline_records_from_har(har_path: str | Path) -> list[dict[str, Any]]:
    rows = timeline_rows_from_har(har_path)
    records: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        record.setdefault("url", row.get("raw_event_url") or row.get("source_url") or "")
        record.setdefault("status", row.get("response_status") or row.get("status") or 0)
        record.setdefault("promotion_source", "har_import_seed_v74d")
        records.append(record)
    return records


def _page_from_record(
    record: Mapping[str, Any],
    *,
    source_url: str,
    page_number: int,
    seen_ids: set[str],
    delay_ms_after_page: int = 0,
    replay_mode: str = "seed_record",
) -> tuple[TwitterCursorPage, tuple[Any, ...], str]:
    url = str(record.get("url") or record.get("request_url") or record.get("raw_event_url") or record.get("source_url") or "")
    query_name = _record_query_name(record)
    body = _record_body(record)
    response_status = int(record.get("response_status") or record.get("status") or 0)
    rate_limited = response_status in {403, 429} or bool(record.get("rate_limited"))
    cursors = extract_timeline_cursors(body)
    entries = extract_timeline_entries_from_body(
        body,
        source_url=source_url,
        query_name=query_name,
        page_number=page_number,
    ) if body is not None else ()
    unique_count = 0
    for entry in entries:
        status_id = getattr(entry, "status_id", "")
        if status_id and status_id not in seen_ids:
            seen_ids.add(status_id)
            unique_count += 1
    cursor_out = str(cursors.get("cursor_out") or record.get("cursor_out") or "")
    body_text = record.get("body_text")
    body_sha = str(record.get("body_sha256") or "")
    if not body_sha and body is not None:
        body_sha = _sha256_text(json.dumps(body, ensure_ascii=False, sort_keys=True))
    if not body_sha and body_text:
        body_sha = _sha256_text(str(body_text))
    state = "rate_limited" if rate_limited else ("returned_timeline_entries" if entries else "no_timeline_entries_found")
    page = TwitterCursorPage(
        schema_version=CURSOR_PAGE_SCHEMA_VERSION,
        query_name=query_name,
        source_url=source_url,
        page_number=page_number,
        response_status=response_status,
        returned_items_count=len(entries),
        unique_items_count=unique_count,
        cursor_in=str(record.get("cursor_in") or _cursor_from_url(url) or ""),
        cursor_out=cursor_out,
        top_cursor=str(cursors.get("top_cursor") or ""),
        bottom_cursor=str(cursors.get("bottom_cursor") or ""),
        rate_limited=rate_limited,
        page_boundary_state=state,
        request_url=url,
        body_sha256=body_sha,
        delay_ms_after_page=delay_ms_after_page,
        replay_mode=replay_mode,
    )
    return page, entries, cursor_out


def run_twitter_cursor_scheduler_from_records(
    *,
    records: Sequence[Mapping[str, Any]],
    source_url: str,
    output_dir: str | Path,
    profile_tab: str = "replies",
    max_pages: int = 10,
    max_records: int = 0,
    seed_capture_dir: str | Path = "",
    har_path: str | Path = "",
) -> TwitterCursorSchedulerResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    canonical_url = _profile_tab_url(source_url, profile_tab)
    pages: list[TwitterCursorPage] = []
    all_entries: list[Any] = []
    seen_ids: set[str] = set()
    cursor_history: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    stop_reason = "no_timeline_seed_records_found"
    next_cursor_url = ""

    filtered = [record for record in records if is_timeline_query_name(_record_query_name(record))]
    for index, record in enumerate(filtered, start=1):
        if max_pages and len(pages) >= int(max_pages):
            stop_reason = "max_pages_reached"
            break
        page, entries, cursor_out = _page_from_record(
            record,
            source_url=canonical_url,
            page_number=len(pages) + 1,
            seen_ids=seen_ids,
            replay_mode=str(record.get("promotion_source") or "seed_record"),
        )
        pages.append(page)
        all_entries.extend(entries)
        if cursor_out:
            if cursor_out in cursor_history:
                stop_reason = "repeated_cursor_boundary"
                break
            cursor_history.append(cursor_out)
            next_cursor_url = _url_with_cursor(page.request_url, cursor_out) if page.request_url else ""
        if page.rate_limited:
            stop_reason = "rate_limited_pause_boundary"
            break
        if max_records and len(seen_ids) >= int(max_records):
            stop_reason = "max_records_reached"
            break
        stop_reason = "seed_records_exhausted"

    if not pages:
        warnings.append("no_timeline_seed_records_found")
    elif not any(page.cursor_out for page in pages):
        stop_reason = "no_bottom_cursor_observed"

    return _write_scheduler_output(
        output=output,
        source_url=source_url,
        canonical_url=canonical_url,
        profile_tab=profile_tab,
        pages=pages,
        entries=all_entries,
        unique_count=len(seen_ids),
        cursor_history=cursor_history,
        stop_reason=stop_reason,
        next_cursor_url=next_cursor_url,
        warnings=warnings,
        errors=errors,
        seed_capture_dir=str(seed_capture_dir or ""),
        har_path=str(har_path or ""),
    )


def _write_scheduler_output(
    *,
    output: Path,
    source_url: str,
    canonical_url: str,
    profile_tab: str,
    pages: Sequence[TwitterCursorPage],
    entries: Sequence[Any],
    unique_count: int,
    cursor_history: Sequence[str],
    stop_reason: str,
    next_cursor_url: str,
    warnings: Sequence[str],
    errors: Sequence[str],
    seed_capture_dir: str = "",
    har_path: str = "",
) -> TwitterCursorSchedulerResult:
    pages_path = output / "cursor_pages.jsonl"
    entries_path = output / "cursor_entries.jsonl"
    state_path = output / "cursor_scheduler_state.json"
    manifest_path = output / "cursor_export_manifest.json"
    request_templates_path = output / "cursor_request_templates.json"

    _write_jsonl(pages_path, (page.to_dict() for page in pages))
    _write_jsonl(entries_path, (entry.to_dict() if hasattr(entry, "to_dict") else entry for entry in entries))
    _write_json(request_templates_path, {"next_cursor_url": next_cursor_url})
    state = TwitterCursorSchedulerState(
        schema_version=CURSOR_STATE_SCHEMA_VERSION,
        source_url=source_url,
        canonical_url=canonical_url,
        requested_profile_tab=profile_tab,
        pages_count=len(pages),
        entries_count=len(entries),
        unique_entries_count=unique_count,
        cursor_history=tuple(cursor_history),
        last_cursor_out=cursor_history[-1] if cursor_history else "",
        next_cursor_url=next_cursor_url,
        stop_reason=stop_reason,
        rate_limited=any(page.rate_limited for page in pages),
    )
    _write_json(state_path, state)
    manifest = TwitterCursorSchedulerManifest(
        schema_version=CURSOR_MANIFEST_SCHEMA_VERSION,
        source_url=source_url,
        canonical_url=canonical_url,
        output_dir=str(output),
        pages_path=str(pages_path),
        entries_path=str(entries_path),
        state_path=str(state_path),
        request_templates_path=str(request_templates_path),
        seed_capture_dir=seed_capture_dir,
        har_path=har_path,
        files_written=tuple(str(path) for path in (pages_path, entries_path, state_path, manifest_path, request_templates_path)),
        warnings=tuple(warnings),
    )
    _write_json(manifest_path, manifest)
    status = "success" if entries else ("needs_review" if pages else "planned")
    return TwitterCursorSchedulerResult(
        schema_version=TWITTER_CURSOR_SCHEDULER_SCHEMA_VERSION,
        status=status,
        source_url=source_url,
        canonical_url=canonical_url,
        output_dir=str(output),
        pages_count=len(pages),
        entries_count=len(entries),
        unique_entries_count=unique_count,
        pages_path=str(pages_path),
        entries_path=str(entries_path),
        state_path=str(state_path),
        manifest_path=str(manifest_path),
        stop_reason=stop_reason,
        next_cursor_url=next_cursor_url,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def run_twitter_cursor_scheduler_from_capture(
    *,
    capture_dir: str | Path,
    source_url: str,
    output_dir: str | Path,
    profile_tab: str = "replies",
    max_pages: int = 10,
    max_records: int = 0,
) -> TwitterCursorSchedulerResult:
    return run_twitter_cursor_scheduler_from_records(
        records=_timeline_records_from_capture(capture_dir),
        source_url=source_url,
        output_dir=output_dir,
        profile_tab=profile_tab,
        max_pages=max_pages,
        max_records=max_records,
        seed_capture_dir=capture_dir,
    )


def run_twitter_cursor_scheduler_from_har(
    *,
    har_path: str | Path,
    source_url: str,
    output_dir: str | Path,
    profile_tab: str = "replies",
    max_pages: int = 10,
    max_records: int = 0,
) -> TwitterCursorSchedulerResult:
    return run_twitter_cursor_scheduler_from_records(
        records=_timeline_records_from_har(har_path),
        source_url=source_url,
        output_dir=output_dir,
        profile_tab=profile_tab,
        max_pages=max_pages,
        max_records=max_records,
        har_path=har_path,
    )


def _capture_initial_timeline_records(
    *,
    page: Any,
    source_url: str,
    timeout_ms: int,
    initial_scroll_steps: int,
    initial_wait_ms: int,
    scroll_pixels: int,
    scroll_delay_ms: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def capture_response(response: Any) -> None:
        try:
            url = str(response.url)
            query_name = _query_name_from_url(url)
            if not is_timeline_query_name(query_name):
                return
            status = int(response.status or 0)
            headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
            req_headers: dict[str, str] = {}
            try:
                req_headers = {str(k).lower(): str(v) for k, v in response.request.all_headers().items()}
            except Exception:
                req_headers = {}
            body_text = ""
            try:
                body_text = response.text()
            except Exception:
                body_text = ""
            records.append(
                {
                    "schema_version": "twitter_cursor_initial_response.v74d",
                    "url": url,
                    "query_name": query_name,
                    "status": status,
                    "headers": headers,
                    "request_headers": req_headers,
                    "body_text": body_text,
                    "body_sha256": _sha256_text(body_text),
                    "promotion_source": "live_initial_browser_response_v74d",
                }
            )
        except Exception:
            return

    page.on("response", capture_response)
    page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(max(1000, int(initial_wait_ms)))
    for _ in range(max(0, int(initial_scroll_steps))):
        page.mouse.wheel(0, max(400, int(scroll_pixels)))
        page.wait_for_timeout(max(750, int(scroll_delay_ms)))
    return records


def _fetch_cursor_page(page: Any, *, url: str, request_headers: Mapping[str, Any]) -> dict[str, Any]:
    headers = _headers_for_replay(request_headers)
    payload = page.evaluate(
        """
        async ({url, headers}) => {
          const response = await fetch(url, {method: 'GET', credentials: 'include', headers});
          const bodyText = await response.text();
          const outHeaders = {};
          response.headers.forEach((value, key) => { outHeaders[key] = value; });
          return {url: response.url || url, status: response.status, headers: outHeaders, body_text: bodyText};
        }
        """,
        {"url": url, "headers": headers},
    )
    if not isinstance(payload, Mapping):
        payload = {}
    body_text = str(payload.get("body_text") or "")
    return {
        "schema_version": "twitter_cursor_fetch_response.v74d",
        "url": str(payload.get("url") or url),
        "query_name": _query_name_from_url(str(payload.get("url") or url)),
        "status": int(payload.get("status") or 0),
        "headers": payload.get("headers") if isinstance(payload.get("headers"), Mapping) else {},
        "request_headers": headers,
        "body_text": body_text,
        "body_sha256": _sha256_text(body_text),
        "promotion_source": "browser_fetch_cursor_page_v74d",
    }


def run_twitter_cursor_scheduler_live(
    *,
    source_url: str,
    output_dir: str | Path,
    browser_user_data_dir: str | Path,
    reuse_existing_profile: bool = False,
    profile_tab: str = "replies",
    headless: bool = False,
    timeout_ms: int = 120000,
    initial_scroll_steps: int = 1,
    initial_wait_ms: int = 4500,
    scroll_pixels: int = 1700,
    scroll_delay_ms: int = 2500,
    max_pages: int = 10,
    max_records: int = 0,
    page_delay_ms: int = 4500,
    page_jitter_ms: int = 1500,
    cooldown_ms: int = 180000,
    max_runtime_minutes: float = 0.0,
    stop_on_rate_limit: bool = True,
    max_no_new_pages: int = 2,
) -> TwitterCursorSchedulerResult:
    if not browser_user_data_dir:
        raise ValueError("browser_user_data_dir is required for live cursor scheduling; log in manually first and close Chromium before running")
    if not reuse_existing_profile:
        raise ValueError("reuse_existing_profile must be explicit for live cursor scheduling")

    from playwright.sync_api import sync_playwright

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    canonical_url = _profile_tab_url(source_url, profile_tab)
    pages: list[TwitterCursorPage] = []
    entries: list[Any] = []
    seen_ids: set[str] = set()
    cursor_history: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    request_templates: list[dict[str, Any]] = []
    stop_reason = "not_started"
    next_cursor_url = ""
    started = time.monotonic()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(user_data_dir=str(browser_user_data_dir), headless=headless)
        try:
            page = context.new_page()
            initial_records = _capture_initial_timeline_records(
                page=page,
                source_url=canonical_url,
                timeout_ms=timeout_ms,
                initial_scroll_steps=initial_scroll_steps,
                initial_wait_ms=initial_wait_ms,
                scroll_pixels=scroll_pixels,
                scroll_delay_ms=scroll_delay_ms,
            )
            timeline_records = [r for r in initial_records if is_timeline_query_name(_record_query_name(r)) and _record_body(r) is not None]
            if not timeline_records:
                warnings.append("no_initial_timeline_response_found")
                stop_reason = "no_initial_timeline_response_found"
            else:
                current_record = timeline_records[-1]
                request_headers = current_record.get("request_headers") if isinstance(current_record.get("request_headers"), Mapping) else {}
                while current_record:
                    if max_runtime_minutes and (time.monotonic() - started) >= float(max_runtime_minutes) * 60.0:
                        stop_reason = "max_runtime_reached"
                        break
                    if max_pages and len(pages) >= int(max_pages):
                        stop_reason = "max_pages_reached"
                        break
                    page_obj, page_entries, cursor_out = _page_from_record(
                        current_record,
                        source_url=canonical_url,
                        page_number=len(pages) + 1,
                        seen_ids=seen_ids,
                        delay_ms_after_page=0,
                        replay_mode=str(current_record.get("promotion_source") or "live_cursor_scheduler"),
                    )
                    pages.append(page_obj)
                    entries.extend(page_entries)
                    if page_obj.rate_limited:
                        warnings.append(f"rate_limited_status:{page_obj.response_status}")
                        stop_reason = "rate_limited_pause_boundary"
                        if stop_on_rate_limit and cooldown_ms > 0:
                            page.wait_for_timeout(max(0, min(int(cooldown_ms), 900000)))
                        break
                    if not cursor_out:
                        stop_reason = "no_bottom_cursor_observed"
                        break
                    if cursor_out in cursor_history:
                        stop_reason = "repeated_cursor_boundary"
                        break
                    cursor_history.append(cursor_out)
                    next_cursor_url = _url_with_cursor(page_obj.request_url, cursor_out)
                    request_templates.append(
                        {
                            "page_number_completed": page_obj.page_number,
                            "cursor_out": cursor_out,
                            "next_cursor_url": next_cursor_url,
                            "request_headers_used": _headers_for_replay(request_headers),
                        }
                    )
                    if max_records and len(seen_ids) >= int(max_records):
                        stop_reason = "max_records_reached"
                        break
                    if max_pages and len(pages) >= int(max_pages):
                        stop_reason = "max_pages_reached"
                        break
                    delay = max(0, int(page_delay_ms)) + (random.randint(0, max(0, int(page_jitter_ms))) if int(page_jitter_ms) > 0 else 0)
                    if delay:
                        page.wait_for_timeout(delay)
                    if next_cursor_url:
                        current_record = _fetch_cursor_page(page, url=next_cursor_url, request_headers=request_headers)
                    else:
                        stop_reason = "no_next_cursor_url"
                        break
                    if len(pages) >= 1 and int(max_no_new_pages) > 0:
                        recent = pages[-int(max_no_new_pages):]
                        if len(recent) == int(max_no_new_pages) and all(item.unique_items_count == 0 for item in recent):
                            stop_reason = "no_new_records_boundary"
                            break
                    stop_reason = "cursor_boundary_reached"
        except Exception as exc:
            errors.append(str(exc))
            stop_reason = "cursor_scheduler_exception"
        finally:
            context.close()

    templates_path = output / "cursor_request_templates.json"
    _write_json(templates_path, {"request_templates": request_templates, "next_cursor_url": next_cursor_url})
    result = _write_scheduler_output(
        output=output,
        source_url=source_url,
        canonical_url=canonical_url,
        profile_tab=profile_tab,
        pages=pages,
        entries=entries,
        unique_count=len(seen_ids),
        cursor_history=cursor_history,
        stop_reason=stop_reason,
        next_cursor_url=next_cursor_url,
        warnings=warnings,
        errors=errors,
    )
    # Preserve the richer request template file written before _write_scheduler_output overwrites the basic template.
    _write_json(templates_path, {"request_templates": request_templates, "next_cursor_url": next_cursor_url})
    return result


def run_twitter_cursor_scheduler(
    *,
    source_url: str,
    output_dir: str | Path,
    live: bool = False,
    browser_user_data_dir: str | Path = "",
    reuse_existing_profile: bool = False,
    seed_capture_dir: str | Path = "",
    har_path: str | Path = "",
    profile_tab: str = "replies",
    headless: bool = False,
    timeout_ms: int = 120000,
    initial_scroll_steps: int = 1,
    initial_wait_ms: int = 4500,
    scroll_pixels: int = 1700,
    scroll_delay_ms: int = 2500,
    max_pages: int = 10,
    max_records: int = 0,
    page_delay_ms: int = 4500,
    page_jitter_ms: int = 1500,
    cooldown_ms: int = 180000,
    max_runtime_minutes: float = 0.0,
    stop_on_rate_limit: bool = True,
    max_no_new_pages: int = 2,
) -> TwitterCursorSchedulerResult:
    if har_path:
        return run_twitter_cursor_scheduler_from_har(
            har_path=har_path,
            source_url=source_url,
            output_dir=output_dir,
            profile_tab=profile_tab,
            max_pages=max_pages,
            max_records=max_records,
        )
    if seed_capture_dir:
        return run_twitter_cursor_scheduler_from_capture(
            capture_dir=seed_capture_dir,
            source_url=source_url,
            output_dir=output_dir,
            profile_tab=profile_tab,
            max_pages=max_pages,
            max_records=max_records,
        )
    if live:
        return run_twitter_cursor_scheduler_live(
            source_url=source_url,
            output_dir=output_dir,
            browser_user_data_dir=browser_user_data_dir,
            reuse_existing_profile=reuse_existing_profile,
            profile_tab=profile_tab,
            headless=headless,
            timeout_ms=timeout_ms,
            initial_scroll_steps=initial_scroll_steps,
            initial_wait_ms=initial_wait_ms,
            scroll_pixels=scroll_pixels,
            scroll_delay_ms=scroll_delay_ms,
            max_pages=max_pages,
            max_records=max_records,
            page_delay_ms=page_delay_ms,
            page_jitter_ms=page_jitter_ms,
            cooldown_ms=cooldown_ms,
            max_runtime_minutes=max_runtime_minutes,
            stop_on_rate_limit=stop_on_rate_limit,
            max_no_new_pages=max_no_new_pages,
        )
    return run_twitter_cursor_scheduler_from_records(
        records=[],
        source_url=source_url,
        output_dir=output_dir,
        profile_tab=profile_tab,
        max_pages=max_pages,
        max_records=max_records,
    )
