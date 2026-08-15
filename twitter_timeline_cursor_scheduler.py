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

from twitter_rate_limit_policy import (
    build_rate_limit_state,
    decide_rate_limit_action,
    observe_rate_limit,
)

from twitter_browser_timeline_pagination import (
    RXLIULI_BROWSER_SESSION_LIMITATION_NOTE,
    TIMELINE_ENTRY_SCHEMA_VERSION,
    canonicalize_browser_capture_url,
    extract_timeline_cursors,
    extract_timeline_entries_from_body,
    is_timeline_query_name,
    timeline_rows_from_har,
)

TWITTER_CURSOR_SCHEDULER_SCHEMA_VERSION = "twitter_timeline_cursor_scheduler.v74f2"
CURSOR_PAGE_SCHEMA_VERSION = "twitter_timeline_cursor_page.v74f2"
CURSOR_STATE_SCHEMA_VERSION = "twitter_timeline_cursor_state.v74f2"
CURSOR_MANIFEST_SCHEMA_VERSION = "twitter_timeline_cursor_manifest.v74f2"
CURSOR_OUTPUT_FILES = (
    "cursor_pages.jsonl",
    "cursor_entries.jsonl",
    "cursor_scheduler_state.json",
    "cursor_export_manifest.json",
    "cursor_rate_limit_state.json",
    "cursor_errors.jsonl",
)

CURSOR_FETCH_HEADER_NAMES = {
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

SENSITIVE_CURSOR_HEADER_NAMES = {
    "authorization",
    "cookie",
    "x-client-transaction-id",
    "x-client-uuid",
    "x-csrf-token",
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
    rate_limit_limit: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset_epoch: int | None = None
    retry_after_seconds: int | None = None
    rate_limit_decision: str = ""
    rate_limit_reason: str = ""
    cooldown_until_epoch: int | None = None
    cooldown_until_utc: str = ""
    body_error_codes: tuple[str, ...] = ()
    body_error_messages: tuple[str, ...] = ()
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
    latest_rate_limit_decision: str = ""
    latest_rate_limit_reason: str = ""
    rate_limit_remaining: int | None = None
    rate_limit_reset_epoch: int | None = None
    cooldown_until_epoch: int | None = None
    cooldown_until_utc: str = ""
    rate_limit_safety_floor: int = 1
    soft_page_budget: int = 0
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
    rate_limit_state_path: str = ""
    errors_path: str = ""
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
    """Return request headers allowed for in-memory cursor fetches.

    These values may include session-bound authorization/CSRF material captured
    from the user's already logged-in browser profile.  They must not be written
    to output files without redaction.
    """
    out: dict[str, str] = {}
    for key, value in (headers or {}).items():
        lower = str(key).lower()
        if lower in CURSOR_FETCH_HEADER_NAMES and value is not None:
            value_text = str(value)
            if value_text:
                out[lower] = value_text
    out.setdefault("accept", "*/*")
    return out


def _merge_replay_headers(*header_sets: Mapping[str, Any] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for header_set in header_sets:
        for key, value in _headers_for_replay(header_set).items():
            if value:
                merged[str(key).lower()] = str(value)
    merged.setdefault("accept", "*/*")
    return merged


def _redacted_headers_for_output(headers: Mapping[str, Any] | None) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in _headers_for_replay(headers).items():
        lower = str(key).lower()
        if lower in SENSITIVE_CURSOR_HEADER_NAMES or "token" in lower or "auth" in lower or "csrf" in lower or lower == "cookie":
            redacted[lower] = "[redacted]"
        else:
            redacted[lower] = str(value)
    return redacted


def _request_headers_are_authenticated(headers: Mapping[str, Any] | None) -> bool:
    replay_headers = _headers_for_replay(headers)
    return bool(replay_headers.get("authorization")) and bool(replay_headers.get("x-csrf-token"))


def _record_body(record: Mapping[str, Any]) -> dict[str, Any] | list[Any] | None:
    body = record.get("body_json")
    if body is not None:
        return body if isinstance(body, (dict, list)) else _load_json_text(body)
    return _load_json_text(record.get("body_text") or record.get("text") or "")


def _rate_limit_observation_for_record(record: Mapping[str, Any], body: Any = None) -> Any:
    if body is None:
        body = _record_body(record)
    headers = record.get("headers") if isinstance(record.get("headers"), Mapping) else {}
    return observe_rate_limit(
        response_status=int(record.get("response_status") or record.get("status") or 0),
        headers=headers,
        body=body,
    )


def _rate_limit_decision_from_record(record: Mapping[str, Any]) -> Mapping[str, Any]:
    decision = record.get("rate_limit_decision")
    return decision if isinstance(decision, Mapping) else {}


def _record_retryable_error(record: Mapping[str, Any]) -> dict[str, Any]:
    observation = _rate_limit_observation_for_record(record)
    decision = _rate_limit_decision_from_record(record)
    return {
        "schema_version": "twitter_cursor_error.v74e",
        "query_name": _record_query_name(record),
        "request_url": _record_url(record),
        "response_status": int(record.get("response_status") or record.get("status") or 0),
        "rate_limit_observation": observation.to_dict(),
        "rate_limit_decision": dict(decision),
        "body_sha256": str(record.get("body_sha256") or ""),
    }


def _record_query_name(record: Mapping[str, Any]) -> str:
    return str(record.get("query_name") or _query_name_from_url(str(record.get("url") or record.get("request_url") or "")) or "")


def _record_url(record: Mapping[str, Any]) -> str:
    return str(record.get("url") or record.get("request_url") or record.get("raw_event_url") or record.get("source_url") or "")


def _entry_mapping(entry: Any) -> Mapping[str, Any]:
    if isinstance(entry, Mapping):
        return entry
    if hasattr(entry, "to_dict"):
        try:
            mapped = entry.to_dict()
            if isinstance(mapped, Mapping):
                return mapped
        except Exception:
            pass
    return {}


def _status_id_from_url(value: Any) -> str:
    import re

    match = re.search(r"/(?:status|statuses)/(\d+)", str(value or ""))
    return match.group(1) if match else ""


def _entry_status_id(entry: Any) -> str:
    if hasattr(entry, "status_id"):
        direct = str(getattr(entry, "status_id", "") or "")
        if direct:
            return direct
    mapped = _entry_mapping(entry)
    for key in ("status_id", "id_str", "rest_id", "id"):
        value = str(mapped.get(key) or "")
        if value:
            return value
    for key in ("canonical_url", "url", "tweet_url"):
        value = _status_id_from_url(mapped.get(key))
        if value:
            return value
    if hasattr(entry, "canonical_url"):
        value = _status_id_from_url(getattr(entry, "canonical_url", ""))
        if value:
            return value
    return ""


def _entry_dedupe_key(entry: Any) -> str:
    status_id = _entry_status_id(entry)
    if status_id:
        return "status:" + status_id
    mapped = _entry_mapping(entry)
    if mapped:
        for key in ("canonical_url", "post_text", "created_at", "conversation_id"):
            value = str(mapped.get(key) or "")
            if value:
                # Use a content fallback only when an upstream representation omitted status_id.
                payload = {k: str(mapped.get(k) or "") for k in ("canonical_url", "post_text", "created_at", "conversation_id", "source_query_name")}
                return "fallback:" + _sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return "fallback:" + _sha256_text(json.dumps(_value_for_dict(entry), ensure_ascii=False, sort_keys=True))


def _record_fingerprint(record: Mapping[str, Any]) -> str:
    """Return a stable page fingerprint across V74B promotion sources.

    The same X response may be present in both network_response_bodies.jsonl and
    api_pages.jsonl.  Fingerprinting by query, cursor boundary, and status IDs
    prevents seed replay from double-counting the same page while still allowing
    distinct cursor pages with overlapping tweets to be kept.
    """
    query_name = _record_query_name(record)
    url = _record_url(record)
    body = _record_body(record)
    status = int(record.get("response_status") or record.get("status") or 0)
    cursor_in = str(record.get("cursor_in") or _cursor_from_url(url) or "")
    cursor_out = str(record.get("cursor_out") or "")
    ids: tuple[str, ...] = ()
    body_sha = str(record.get("body_sha256") or "")
    if body is not None:
        cursors = extract_timeline_cursors(body)
        cursor_out = cursor_out or str(cursors.get("cursor_out") or "")
        extracted = extract_timeline_entries_from_body(
            body,
            source_url="https://x.com/",
            query_name=query_name,
            page_number=0,
        )
        ids = tuple(_entry_status_id(entry) for entry in extracted if _entry_status_id(entry))
        body_sha = body_sha or _sha256_text(json.dumps(body, ensure_ascii=False, sort_keys=True))
    if ids or cursor_out or cursor_in:
        return "|".join([query_name, str(status), cursor_in, cursor_out, ",".join(ids)])
    return "|".join([query_name, str(status), body_sha or url])


def _dedupe_timeline_records(records: Sequence[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], int]:
    deduped: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    duplicates = 0
    for record in records:
        fingerprint = _record_fingerprint(record)
        if fingerprint in seen:
            duplicates += 1
            continue
        seen.add(fingerprint)
        deduped.append(record)
    return deduped, duplicates


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
            rec.setdefault("url", row.get("url") or row.get("request_url") or row.get("raw_event_url") or row.get("source_url") or "")
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
    url = _record_url(record)
    query_name = _record_query_name(record)
    body = _record_body(record)
    response_status = int(record.get("response_status") or record.get("status") or 0)
    observation = _rate_limit_observation_for_record(record, body)
    decision_map = _rate_limit_decision_from_record(record)
    rate_limited = response_status == 429 or bool(record.get("rate_limited")) or bool(decision_map.get("rate_limited"))
    cursors = extract_timeline_cursors(body)
    entries = extract_timeline_entries_from_body(
        body,
        source_url=source_url,
        query_name=query_name,
        page_number=page_number,
    ) if body is not None else ()
    unique_count = 0
    unique_entries: list[Any] = []
    for entry in entries:
        dedupe_key = _entry_dedupe_key(entry)
        if dedupe_key not in seen_ids:
            seen_ids.add(dedupe_key)
            unique_count += 1
            unique_entries.append(entry)
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
        rate_limit_limit=observation.rate_limit_limit,
        rate_limit_remaining=observation.rate_limit_remaining,
        rate_limit_reset_epoch=observation.rate_limit_reset_epoch,
        retry_after_seconds=observation.retry_after_seconds,
        rate_limit_decision=str(decision_map.get("decision") or ""),
        rate_limit_reason=str(decision_map.get("reason") or ""),
        cooldown_until_epoch=decision_map.get("cooldown_until_epoch") if isinstance(decision_map.get("cooldown_until_epoch"), int) else None,
        cooldown_until_utc=str(decision_map.get("cooldown_until_utc") or ""),
        body_error_codes=observation.body_error_codes,
        body_error_messages=observation.body_error_messages,
        page_boundary_state=state,
        request_url=url,
        body_sha256=body_sha,
        delay_ms_after_page=delay_ms_after_page,
        replay_mode=replay_mode,
    )
    return page, tuple(unique_entries), cursor_out




def _seed_state_from_records(
    *,
    records: Sequence[Mapping[str, Any]],
    source_url: str,
    profile_tab: str = "replies",
    max_pages: int = 10,
    max_records: int = 0,
) -> dict[str, Any]:
    """Prepare a cursor scheduler state from existing browser/HAR records.

    This is used both by offline seed replay and by V74F live continuation.
    Keeping seed preparation separate lets the live scheduler continue from an
    already-captured bottom cursor without forcing another scroll-first capture.
    """
    canonical_url = _profile_tab_url(source_url, profile_tab)
    pages: list[TwitterCursorPage] = []
    all_entries: list[Any] = []
    seen_ids: set[str] = set()
    cursor_history: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    stop_reason = "no_timeline_seed_records_found"
    next_cursor_url = ""
    request_headers: dict[str, str] = {}

    filtered = [record for record in records if is_timeline_query_name(_record_query_name(record))]
    filtered, duplicate_records = _dedupe_timeline_records(filtered)
    if duplicate_records:
        warnings.append(f"deduped_seed_records:{duplicate_records}")
    for record in filtered:
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
        if cursor_out and cursor_out in cursor_history and not entries:
            warnings.append(f"deduped_seed_page_repeated_cursor:{cursor_out}")
            stop_reason = "repeated_cursor_boundary"
            break
        pages.append(page)
        all_entries.extend(entries)
        if isinstance(record.get("request_headers"), Mapping):
            request_headers = {str(k).lower(): str(v) for k, v in record.get("request_headers", {}).items() if v is not None}
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

    return {
        "canonical_url": canonical_url,
        "pages": pages,
        "entries": all_entries,
        "seen_ids": seen_ids,
        "cursor_history": cursor_history,
        "warnings": warnings,
        "errors": errors,
        "stop_reason": stop_reason,
        "next_cursor_url": next_cursor_url,
        "request_headers": request_headers,
    }

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
    prepared = _seed_state_from_records(
        records=records,
        source_url=source_url,
        profile_tab=profile_tab,
        max_pages=max_pages,
        max_records=max_records,
    )
    return _write_scheduler_output(
        output=output,
        source_url=source_url,
        canonical_url=str(prepared["canonical_url"]),
        profile_tab=profile_tab,
        pages=prepared["pages"],
        entries=prepared["entries"],
        unique_count=len(prepared["seen_ids"]),
        cursor_history=prepared["cursor_history"],
        stop_reason=str(prepared["stop_reason"]),
        next_cursor_url=str(prepared["next_cursor_url"]),
        warnings=prepared["warnings"],
        errors=prepared["errors"],
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
    rate_limit_state: Mapping[str, Any] | None = None,
    error_rows: Sequence[Mapping[str, Any]] = (),
) -> TwitterCursorSchedulerResult:
    pages_path = output / "cursor_pages.jsonl"
    entries_path = output / "cursor_entries.jsonl"
    state_path = output / "cursor_scheduler_state.json"
    manifest_path = output / "cursor_export_manifest.json"
    request_templates_path = output / "cursor_request_templates.json"
    rate_limit_state_path = output / "cursor_rate_limit_state.json"
    errors_path = output / "cursor_errors.jsonl"

    _write_jsonl(pages_path, (page.to_dict() for page in pages))
    _write_jsonl(entries_path, (entry.to_dict() if hasattr(entry, "to_dict") else entry for entry in entries))
    _write_json(request_templates_path, {"next_cursor_url": next_cursor_url})
    latest_page = pages[-1] if pages else None
    computed_rate_limit_state = rate_limit_state or build_rate_limit_state(
        observation=None,
        decision=None,
        safety_floor=1,
        soft_page_budget=0,
        pages_since_cooldown=len(pages),
        transient_error_count=0,
    ).to_dict()
    _write_json(rate_limit_state_path, computed_rate_limit_state)
    _write_jsonl(errors_path, error_rows)
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
        latest_rate_limit_decision=str((computed_rate_limit_state or {}).get("latest_decision") or (latest_page.rate_limit_decision if latest_page else "")),
        latest_rate_limit_reason=str((computed_rate_limit_state or {}).get("latest_reason") or (latest_page.rate_limit_reason if latest_page else "")),
        rate_limit_remaining=(latest_page.rate_limit_remaining if latest_page else None),
        rate_limit_reset_epoch=(latest_page.rate_limit_reset_epoch if latest_page else None),
        cooldown_until_epoch=(computed_rate_limit_state or {}).get("cooldown_until_epoch"),
        cooldown_until_utc=str((computed_rate_limit_state or {}).get("cooldown_until_utc") or ""),
        rate_limit_safety_floor=int((computed_rate_limit_state or {}).get("safety_floor") or 1),
        soft_page_budget=int((computed_rate_limit_state or {}).get("soft_page_budget") or 0),
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
        rate_limit_state_path=str(rate_limit_state_path),
        errors_path=str(errors_path),
        seed_capture_dir=seed_capture_dir,
        har_path=har_path,
        files_written=tuple(str(path) for path in (pages_path, entries_path, state_path, manifest_path, request_templates_path, rate_limit_state_path, errors_path)),
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




def run_twitter_cursor_scheduler_live_from_seed(
    *,
    seed_records: Sequence[Mapping[str, Any]],
    source_url: str,
    output_dir: str | Path,
    browser_user_data_dir: str | Path,
    reuse_existing_profile: bool = False,
    profile_tab: str = "replies",
    headless: bool = False,
    timeout_ms: int = 120000,
    initial_wait_ms: int = 2500,
    max_pages: int = 2,
    max_records: int = 0,
    page_delay_ms: int = 4500,
    page_jitter_ms: int = 1500,
    cooldown_ms: int = 180000,
    max_runtime_minutes: float = 0.0,
    stop_on_rate_limit: bool = True,
    max_no_new_pages: int = 2,
    rate_limit_safety_floor: int = 1,
    soft_page_budget: int = 0,
    max_transient_retries: int = 2,
    transient_base_delay_ms: int = 15000,
    sleep_on_rate_limit: bool = False,
    auth_probe_scroll_steps: int = 0,
    auth_probe_scroll_pixels: int = 900,
    auth_probe_wait_ms: int = 1500,
    seed_capture_dir: str | Path = "",
    har_path: str | Path = "",
) -> TwitterCursorSchedulerResult:
    """Continue from a seed cursor using the logged-in browser context.

    V74F deliberately avoids another scroll-first discovery pass when a seed
    capture/HAR already contains a usable bottom cursor.  It replays the seed
    page(s), opens the manually logged-in Chromium profile, waits on the X page
    origin, then performs read-only fetches for subsequent cursor URLs with the
    V74E rate-limit policy applied to every response.
    """
    if not browser_user_data_dir:
        raise ValueError("browser_user_data_dir is required for live cursor continuation; log in manually first and close Chromium before running")
    if not reuse_existing_profile:
        raise ValueError("reuse_existing_profile must be explicit for live cursor continuation")

    from playwright.sync_api import sync_playwright

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    prepared = _seed_state_from_records(
        records=seed_records,
        source_url=source_url,
        profile_tab=profile_tab,
        max_pages=max_pages,
        max_records=max_records,
    )
    canonical_url = str(prepared["canonical_url"])
    pages: list[TwitterCursorPage] = list(prepared["pages"])
    entries: list[Any] = list(prepared["entries"])
    seen_ids: set[str] = set(prepared["seen_ids"])
    cursor_history: list[str] = list(prepared["cursor_history"])
    warnings: list[str] = list(prepared["warnings"])
    errors: list[str] = list(prepared["errors"])
    stop_reason = str(prepared["stop_reason"])
    next_cursor_url = str(prepared["next_cursor_url"] or "")
    request_headers = prepared["request_headers"] if isinstance(prepared.get("request_headers"), Mapping) else {}
    request_templates: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    latest_rate_limit_observation: Any = None
    latest_rate_limit_decision: Any = None
    transient_error_count = 0
    pages_since_cooldown = len(pages)
    started = time.monotonic()

    if not pages:
        stop_reason = "no_timeline_seed_records_found"
    elif not next_cursor_url:
        stop_reason = "no_seed_bottom_cursor_observed"
    elif max_pages and len(pages) >= int(max_pages):
        stop_reason = "max_pages_reached"
    else:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(user_data_dir=str(browser_user_data_dir), headless=headless)
            try:
                page = context.new_page()
                # Establish the x.com origin and harvest the web app's own GraphQL
                # auth header envelope.  A cookie-only fetch can return HTTP 403.
                auth_probe = _capture_live_cursor_auth_headers(
                    page,
                    canonical_url=canonical_url,
                    timeout_ms=timeout_ms,
                    initial_wait_ms=initial_wait_ms,
                    auth_probe_scroll_steps=auth_probe_scroll_steps,
                    auth_probe_scroll_pixels=auth_probe_scroll_pixels,
                    auth_probe_wait_ms=auth_probe_wait_ms,
                )
                live_headers = auth_probe.get("headers") if isinstance(auth_probe.get("headers"), Mapping) else {}
                request_headers = _merge_replay_headers(request_headers, live_headers)
                if live_headers:
                    warnings.append(f"live_request_headers_captured:{auth_probe.get('query_name') or 'graphql'}:{auth_probe.get('candidate_count') or 1}")
                else:
                    warnings.append("live_request_headers_not_captured")
                while next_cursor_url and (not max_pages or len(pages) < int(max_pages)):
                    if max_runtime_minutes and (time.monotonic() - started) >= float(max_runtime_minutes) * 60.0:
                        stop_reason = "max_runtime_reached"
                        break
                    normal_delay = max(0, int(page_delay_ms)) + (random.randint(0, max(0, int(page_jitter_ms))) if int(page_jitter_ms) > 0 else 0)
                    if normal_delay:
                        page.wait_for_timeout(normal_delay)
                    current_record = _fetch_cursor_page(page, url=next_cursor_url, request_headers=request_headers)
                    latest_rate_limit_observation = _rate_limit_observation_for_record(current_record)
                    latest_rate_limit_decision = decide_rate_limit_action(
                        observation=latest_rate_limit_observation,
                        normal_delay_ms=0,
                        pages_since_cooldown=pages_since_cooldown + 1,
                        safety_floor=rate_limit_safety_floor,
                        soft_page_budget=soft_page_budget,
                        transient_error_count=transient_error_count,
                        max_transient_retries=max_transient_retries,
                        transient_base_delay_ms=transient_base_delay_ms,
                    )
                    current_record = dict(current_record)
                    current_record["rate_limit_observation"] = latest_rate_limit_observation.to_dict()
                    current_record["rate_limit_decision"] = latest_rate_limit_decision.to_dict()
                    page_obj, page_entries, cursor_out = _page_from_record(
                        current_record,
                        source_url=canonical_url,
                        page_number=len(pages) + 1,
                        seen_ids=seen_ids,
                        delay_ms_after_page=latest_rate_limit_decision.delay_ms,
                        replay_mode="browser_fetch_cursor_continuation_v74f",
                    )
                    pages.append(page_obj)
                    entries.extend(page_entries)
                    pages_since_cooldown += 1

                    if latest_rate_limit_decision.transient_error:
                        transient_error_count += 1
                        error_rows.append(_record_retryable_error(current_record))
                    else:
                        transient_error_count = 0

                    request_templates.append(
                        {
                            "page_number_completed": page_obj.page_number,
                            "cursor_in": page_obj.cursor_in,
                            "cursor_out": cursor_out,
                            "next_cursor_url": _url_with_cursor(page_obj.request_url, cursor_out) if cursor_out and page_obj.request_url else "",
                            "request_headers_used": _redacted_headers_for_output(request_headers),
                            "rate_limit_observation": latest_rate_limit_observation.to_dict(),
                            "rate_limit_decision": latest_rate_limit_decision.to_dict(),
                        }
                    )

                    if latest_rate_limit_decision.should_stop and latest_rate_limit_decision.decision != "continue_after_delay":
                        warnings.append(f"rate_limit_decision:{latest_rate_limit_decision.decision}")
                        if latest_rate_limit_decision.rate_limited:
                            stop_reason = "rate_limited_pause_boundary"
                        elif latest_rate_limit_decision.auth_or_access_boundary:
                            stop_reason = "auth_or_access_boundary"
                        elif latest_rate_limit_decision.soft_page_budget_reached:
                            stop_reason = "soft_page_budget_pause_boundary"
                        elif latest_rate_limit_decision.transient_error:
                            stop_reason = "transient_retry_pause_boundary"
                        else:
                            stop_reason = latest_rate_limit_decision.decision
                        if sleep_on_rate_limit and latest_rate_limit_decision.delay_ms > 0:
                            page.wait_for_timeout(max(0, min(int(latest_rate_limit_decision.delay_ms), 900000)))
                        break
                    if page_obj.rate_limited:
                        warnings.append(f"rate_limited_status:{page_obj.response_status}")
                        stop_reason = "rate_limited_pause_boundary"
                        if sleep_on_rate_limit and cooldown_ms > 0:
                            page.wait_for_timeout(max(0, min(int(cooldown_ms), 900000)))
                        break
                    if not cursor_out:
                        stop_reason = "no_bottom_cursor_observed"
                        break
                    if cursor_out in cursor_history:
                        stop_reason = "repeated_cursor_boundary"
                        break
                    cursor_history.append(cursor_out)
                    next_cursor_url = _url_with_cursor(page_obj.request_url, cursor_out) if page_obj.request_url else ""
                    if max_records and len(seen_ids) >= int(max_records):
                        stop_reason = "max_records_reached"
                        break
                    if max_pages and len(pages) >= int(max_pages):
                        stop_reason = "max_pages_reached"
                        break
                    if int(max_no_new_pages) > 0:
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
        seed_capture_dir=str(seed_capture_dir or ""),
        har_path=str(har_path or ""),
        rate_limit_state=build_rate_limit_state(
            observation=latest_rate_limit_observation,
            decision=latest_rate_limit_decision,
            safety_floor=rate_limit_safety_floor,
            soft_page_budget=soft_page_budget,
            pages_since_cooldown=pages_since_cooldown,
            transient_error_count=transient_error_count,
        ).to_dict(),
        error_rows=error_rows,
    )
    _write_json(templates_path, {"request_templates": request_templates, "next_cursor_url": next_cursor_url})
    return result

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


def _capture_live_cursor_auth_headers(
    page: Any,
    *,
    canonical_url: str,
    timeout_ms: int,
    initial_wait_ms: int,
    auth_probe_scroll_steps: int = 0,
    auth_probe_scroll_pixels: int = 900,
    auth_probe_wait_ms: int = 1500,
) -> dict[str, Any]:
    """Capture the X web app's own GraphQL request header envelope.

    A bare browser fetch with cookies can receive HTTP 403 because X's web
    GraphQL calls are normally sent with an authorization bearer and ct0-derived
    CSRF header.  V74F2 observes those headers from the already logged-in browser
    page and reuses only the allowlisted headers in memory.  Output files only
    receive redacted header summaries.
    """
    candidates: list[dict[str, Any]] = []

    def capture_request(request: Any) -> None:
        try:
            request_url = str(request.url or "")
            query_name = _query_name_from_url(request_url)
            if "/graphql/" not in request_url:
                return
            try:
                raw_headers = request.all_headers()
            except Exception:
                raw_headers = getattr(request, "headers", {}) or {}
            headers = _headers_for_replay(raw_headers if isinstance(raw_headers, Mapping) else {})
            if not headers:
                return
            score = 0
            if is_timeline_query_name(query_name):
                score += 10
            if query_name == "UserRepliesTimeline":
                score += 10
            if _request_headers_are_authenticated(headers):
                score += 20
            if headers.get("x-client-transaction-id"):
                score += 3
            candidates.append(
                {
                    "query_name": query_name,
                    "request_url": request_url,
                    "headers": headers,
                    "score": score,
                }
            )
        except Exception:
            return

    page.on("request", capture_request)
    page.goto(canonical_url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(max(1000, int(initial_wait_ms)))
    for _ in range(max(0, int(auth_probe_scroll_steps))):
        page.mouse.wheel(0, max(200, int(auth_probe_scroll_pixels)))
        page.wait_for_timeout(max(500, int(auth_probe_wait_ms)))

    if not candidates:
        return {"headers": {}, "query_name": "", "request_url": "", "captured": False, "candidate_count": 0}
    best = sorted(candidates, key=lambda item: int(item.get("score") or 0), reverse=True)[0]
    return {
        "headers": best.get("headers") if isinstance(best.get("headers"), Mapping) else {},
        "query_name": str(best.get("query_name") or ""),
        "request_url": str(best.get("request_url") or ""),
        "captured": True,
        "candidate_count": len(candidates),
    }


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
    rate_limit_safety_floor: int = 1,
    soft_page_budget: int = 0,
    max_transient_retries: int = 2,
    transient_base_delay_ms: int = 15000,
    sleep_on_rate_limit: bool = False,
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
    error_rows: list[dict[str, Any]] = []
    latest_rate_limit_observation: Any = None
    latest_rate_limit_decision: Any = None
    transient_error_count = 0
    pages_since_cooldown = 0
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
                    normal_delay = max(0, int(page_delay_ms)) + (random.randint(0, max(0, int(page_jitter_ms))) if int(page_jitter_ms) > 0 else 0)
                    latest_rate_limit_observation = _rate_limit_observation_for_record(current_record)
                    latest_rate_limit_decision = decide_rate_limit_action(
                        observation=latest_rate_limit_observation,
                        normal_delay_ms=normal_delay,
                        pages_since_cooldown=pages_since_cooldown + 1,
                        safety_floor=rate_limit_safety_floor,
                        soft_page_budget=soft_page_budget,
                        transient_error_count=transient_error_count,
                        max_transient_retries=max_transient_retries,
                        transient_base_delay_ms=transient_base_delay_ms,
                    )
                    current_record = dict(current_record)
                    current_record["rate_limit_observation"] = latest_rate_limit_observation.to_dict()
                    current_record["rate_limit_decision"] = latest_rate_limit_decision.to_dict()

                    page_obj, page_entries, cursor_out = _page_from_record(
                        current_record,
                        source_url=canonical_url,
                        page_number=len(pages) + 1,
                        seen_ids=seen_ids,
                        delay_ms_after_page=latest_rate_limit_decision.delay_ms,
                        replay_mode=str(current_record.get("promotion_source") or "live_cursor_scheduler"),
                    )
                    pages.append(page_obj)
                    entries.extend(page_entries)
                    pages_since_cooldown += 1

                    if latest_rate_limit_decision.transient_error:
                        transient_error_count += 1
                        error_rows.append(_record_retryable_error(current_record))
                    else:
                        transient_error_count = 0

                    if latest_rate_limit_decision.should_stop and latest_rate_limit_decision.decision != "continue_after_delay":
                        warnings.append(f"rate_limit_decision:{latest_rate_limit_decision.decision}")
                        if latest_rate_limit_decision.rate_limited:
                            stop_reason = "rate_limited_pause_boundary"
                        elif latest_rate_limit_decision.auth_or_access_boundary:
                            stop_reason = "auth_or_access_boundary"
                        elif latest_rate_limit_decision.soft_page_budget_reached:
                            stop_reason = "soft_page_budget_pause_boundary"
                        elif latest_rate_limit_decision.transient_error:
                            stop_reason = "transient_retry_pause_boundary"
                        else:
                            stop_reason = latest_rate_limit_decision.decision
                        if sleep_on_rate_limit and latest_rate_limit_decision.delay_ms > 0:
                            page.wait_for_timeout(max(0, min(int(latest_rate_limit_decision.delay_ms), 900000)))
                        break

                    if page_obj.rate_limited:
                        warnings.append(f"rate_limited_status:{page_obj.response_status}")
                        stop_reason = "rate_limited_pause_boundary"
                        if sleep_on_rate_limit and cooldown_ms > 0:
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
                            "request_headers_used": _redacted_headers_for_output(request_headers),
                            "rate_limit_observation": latest_rate_limit_observation.to_dict(),
                            "rate_limit_decision": latest_rate_limit_decision.to_dict(),
                        }
                    )
                    if max_records and len(seen_ids) >= int(max_records):
                        stop_reason = "max_records_reached"
                        break
                    if max_pages and len(pages) >= int(max_pages):
                        stop_reason = "max_pages_reached"
                        break
                    if latest_rate_limit_decision.delay_ms:
                        page.wait_for_timeout(max(0, int(latest_rate_limit_decision.delay_ms)))
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
        rate_limit_state=build_rate_limit_state(
            observation=latest_rate_limit_observation,
            decision=latest_rate_limit_decision,
            safety_floor=rate_limit_safety_floor,
            soft_page_budget=soft_page_budget,
            pages_since_cooldown=pages_since_cooldown,
            transient_error_count=transient_error_count,
        ).to_dict(),
        error_rows=error_rows,
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
    rate_limit_safety_floor: int = 1,
    soft_page_budget: int = 0,
    max_transient_retries: int = 2,
    transient_base_delay_ms: int = 15000,
    sleep_on_rate_limit: bool = False,
    auth_probe_scroll_steps: int = 0,
    auth_probe_scroll_pixels: int = 900,
    auth_probe_wait_ms: int = 1500,
) -> TwitterCursorSchedulerResult:
    if live and seed_capture_dir:
        return run_twitter_cursor_scheduler_live_from_seed(
            seed_records=_timeline_records_from_capture(seed_capture_dir),
            source_url=source_url,
            output_dir=output_dir,
            browser_user_data_dir=browser_user_data_dir,
            reuse_existing_profile=reuse_existing_profile,
            profile_tab=profile_tab,
            headless=headless,
            timeout_ms=timeout_ms,
            initial_wait_ms=initial_wait_ms,
            max_pages=max_pages,
            max_records=max_records,
            page_delay_ms=page_delay_ms,
            page_jitter_ms=page_jitter_ms,
            cooldown_ms=cooldown_ms,
            max_runtime_minutes=max_runtime_minutes,
            stop_on_rate_limit=stop_on_rate_limit,
            max_no_new_pages=max_no_new_pages,
            rate_limit_safety_floor=rate_limit_safety_floor,
            soft_page_budget=soft_page_budget,
            max_transient_retries=max_transient_retries,
            transient_base_delay_ms=transient_base_delay_ms,
            sleep_on_rate_limit=sleep_on_rate_limit,
            auth_probe_scroll_steps=auth_probe_scroll_steps,
            auth_probe_scroll_pixels=auth_probe_scroll_pixels,
            auth_probe_wait_ms=auth_probe_wait_ms,
            seed_capture_dir=seed_capture_dir,
        )
    if live and har_path:
        return run_twitter_cursor_scheduler_live_from_seed(
            seed_records=_timeline_records_from_har(har_path),
            source_url=source_url,
            output_dir=output_dir,
            browser_user_data_dir=browser_user_data_dir,
            reuse_existing_profile=reuse_existing_profile,
            profile_tab=profile_tab,
            headless=headless,
            timeout_ms=timeout_ms,
            initial_wait_ms=initial_wait_ms,
            max_pages=max_pages,
            max_records=max_records,
            page_delay_ms=page_delay_ms,
            page_jitter_ms=page_jitter_ms,
            cooldown_ms=cooldown_ms,
            max_runtime_minutes=max_runtime_minutes,
            stop_on_rate_limit=stop_on_rate_limit,
            max_no_new_pages=max_no_new_pages,
            rate_limit_safety_floor=rate_limit_safety_floor,
            soft_page_budget=soft_page_budget,
            max_transient_retries=max_transient_retries,
            transient_base_delay_ms=transient_base_delay_ms,
            sleep_on_rate_limit=sleep_on_rate_limit,
            auth_probe_scroll_steps=auth_probe_scroll_steps,
            auth_probe_scroll_pixels=auth_probe_scroll_pixels,
            auth_probe_wait_ms=auth_probe_wait_ms,
            har_path=har_path,
        )
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
            rate_limit_safety_floor=rate_limit_safety_floor,
            soft_page_budget=soft_page_budget,
            max_transient_retries=max_transient_retries,
            transient_base_delay_ms=transient_base_delay_ms,
            sleep_on_rate_limit=sleep_on_rate_limit,
        )
    return run_twitter_cursor_scheduler_from_records(
        records=[],
        source_url=source_url,
        output_dir=output_dir,
        profile_tab=profile_tab,
        max_pages=max_pages,
        max_records=max_records,
    )
