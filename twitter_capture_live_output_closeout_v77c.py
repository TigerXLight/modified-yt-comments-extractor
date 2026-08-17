from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from twitter_browser_capture_strategy import canonicalize_browser_capture_url


TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_SCHEMA_VERSION = "twitter-capture-live-output-closeout-v77c"
WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C = "WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C"


@dataclass(frozen=True)
class TwitterCloseoutFileReference:
    filename: str
    path: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterCycleCloseout:
    cycle_name: str
    cycle_path: str
    exists: bool
    entries_count: int
    unique_status_ids: int
    new_unique_status_ids: int
    pages_count: int
    stop_reason: str
    response_status: int | None
    rate_limit_remaining: int | None
    cooldown_until_utc: str
    latest_decision: str
    replay_modes: tuple[str, ...]
    page_cursor_out: tuple[str, ...]
    state_last_cursor_out: str
    state_next_cursor_url_blank: bool
    templates_next_cursor_url_blank: bool
    next_cursor_url_available: bool
    cursor_template_repair: Mapping[str, Any]
    blank_author_count: int
    blank_screen_count: int
    with_media_count: int
    reply_count: int
    file_hashes: tuple[TwitterCloseoutFileReference, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["file_hashes"] = [item.to_dict() for item in self.file_hashes]
        payload["replay_modes"] = list(self.replay_modes)
        payload["page_cursor_out"] = list(self.page_cursor_out)
        payload["cursor_template_repair"] = dict(self.cursor_template_repair)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass(frozen=True)
class TwitterLiveOutputCloseout:
    source_url: str
    canonical_url: str
    profile_tab: str
    output_root: str
    cycle_count: int
    total_unique_status_ids: int
    cycles: tuple[TwitterCycleCloseout, ...]
    auth_or_access_boundary: Mapping[str, Any]
    profile_media_bridge: Mapping[str, Any]
    preservation_status: Mapping[str, Any]
    safety_flags: Mapping[str, Any]
    warnings: tuple[str, ...] = ()
    profile_media_records_path: str = ""
    schema_version: str = TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    offline_closeout_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["cycles"] = [cycle.to_dict() for cycle in self.cycles]
        payload["auth_or_access_boundary"] = dict(self.auth_or_access_boundary)
        payload["profile_media_bridge"] = dict(self.profile_media_bridge)
        payload["preservation_status"] = dict(self.preservation_status)
        payload["safety_flags"] = dict(self.safety_flags)
        payload["warnings"] = list(self.warnings)
        return payload


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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except Exception:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _write_json(path: str | Path, data: Mapping[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_value_for_dict(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_value_for_dict(row), ensure_ascii=False, sort_keys=True) + "\n")
    return output


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_reference(path: Path) -> TwitterCloseoutFileReference:
    return TwitterCloseoutFileReference(
        filename=path.name,
        path=str(path),
        size_bytes=path.stat().st_size,
        sha256=_sha256_file(path),
    )


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _dedupe(values: Iterable[object]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return tuple(output)


def account_context_from_source_url(source_url: str) -> str:
    parsed = urlsplit(str(source_url or ""))
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0].lower() not in {"i", "intent", "share"}:
        return parts[0]
    return ""


def canonical_timeline_url(source_url: str, profile_tab: str = "replies") -> str:
    canonical = canonicalize_browser_capture_url(source_url)
    if str(profile_tab or "").lower() == "replies" and not canonical.rstrip("/").endswith("/with_replies"):
        return canonical.rstrip("/") + "/with_replies"
    return canonical


def discover_cycle_folders(output_root: str | Path = "", cycle_folders: Sequence[str | Path] = ()) -> tuple[Path, ...]:
    if cycle_folders:
        return tuple(Path(path).expanduser().resolve() for path in cycle_folders)
    root = Path(os.path.expandvars(str(output_root or ""))).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Twitter/X output root does not exist: {root}")
    candidates = [path for path in root.iterdir() if path.is_dir() and (path / "cursor_entries.jsonl").exists()]
    return tuple(sorted(candidates, key=lambda path: path.name.lower()))


def _query_name_from_url(url: str) -> str:
    match = re.search(r"/graphql/[^/?#]+/([^/?#]+)", str(url or ""))
    return match.group(1) if match else ""


def _is_timeline_request_url(url: str) -> bool:
    parsed = urlsplit(str(url or ""))
    host = (parsed.hostname or "").lower()
    query_name = _query_name_from_url(url).lower()
    return host in {"x.com", "twitter.com", "api.x.com", "api.twitter.com"} and "/graphql/" in parsed.path and "timeline" in query_name


def build_repaired_next_cursor_url(request_url: str, cursor_out: str) -> tuple[str, str]:
    if not request_url:
        return "", "missing_request_url"
    if not cursor_out:
        return "", "missing_cursor_out"
    if not _is_timeline_request_url(request_url):
        return "", "unsupported_request_shape"
    parsed = urlsplit(request_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    variables_text = (qs.get("variables") or [""])[0]
    if not variables_text:
        return "", "missing_variables"
    try:
        variables = json.loads(variables_text)
    except Exception:
        return "", "variables_json_parse_failed"
    if not isinstance(variables, dict):
        return "", "variables_not_object"
    variables["cursor"] = cursor_out
    qs["variables"] = [json.dumps(variables, separators=(",", ":"), ensure_ascii=False)]
    repaired_query = urlencode(qs, doseq=True)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, repaired_query, parsed.fragment)), ""


def _build_cursor_template_repair(
    *,
    pages: Sequence[Mapping[str, Any]],
    state: Mapping[str, Any],
    templates: Mapping[str, Any],
) -> dict[str, Any]:
    next_cursor_url = str(templates.get("next_cursor_url") or state.get("next_cursor_url") or "")
    if next_cursor_url:
        return {
            "needed": False,
            "performed_in_manifest_only": True,
            "already_available": True,
            "repaired_next_cursor_url_available": True,
            "reason": "existing_next_cursor_url_available",
            "warnings": [],
        }
    state_last = str(state.get("last_cursor_out") or "")
    source_page = next((page for page in reversed(tuple(pages)) if str(page.get("cursor_out") or "")), {})
    cursor_out = str(source_page.get("cursor_out") or "")
    request_url = str(source_page.get("request_url") or "")
    needed = bool(cursor_out and not state_last and not next_cursor_url)
    repaired, reason = build_repaired_next_cursor_url(request_url, cursor_out)
    return {
        "needed": needed,
        "performed_in_manifest_only": True,
        "source_page_number": int(source_page.get("page_number") or 0) if source_page else 0,
        "cursor_out": cursor_out,
        "repaired_next_cursor_url_available": bool(repaired),
        "repaired_next_cursor_url": repaired,
        "reason": reason or ("repaired_from_page_cursor_out" if repaired else "not_needed"),
        "warnings": [] if repaired or not needed else [reason or "cursor_template_repair_not_available"],
    }


def _cycle_file_hashes(cycle_path: Path) -> tuple[TwitterCloseoutFileReference, ...]:
    names = (
        "cursor_entries.jsonl",
        "cursor_pages.jsonl",
        "cursor_scheduler_state.json",
        "cursor_rate_limit_state.json",
        "cursor_export_manifest.json",
        "cursor_request_templates.json",
        "cursor_errors.jsonl",
    )
    return tuple(_file_reference(cycle_path / name) for name in names if (cycle_path / name).is_file())


def summarize_cycle(cycle_path: Path, previous_unique_ids: set[str]) -> tuple[TwitterCycleCloseout, set[str], list[dict[str, Any]]]:
    entries = _read_jsonl(cycle_path / "cursor_entries.jsonl")
    pages = _read_jsonl(cycle_path / "cursor_pages.jsonl")
    state = _read_json(cycle_path / "cursor_scheduler_state.json")
    rate = _read_json(cycle_path / "cursor_rate_limit_state.json")
    templates = _read_json(cycle_path / "cursor_request_templates.json")
    ids = {str(row.get("status_id") or "") for row in entries if str(row.get("status_id") or "")}
    new_ids = ids - previous_unique_ids
    response_status = _int_or_none(rate.get("response_status"))
    if response_status is None:
        response_status = _int_or_none(next((page.get("response_status") for page in reversed(pages) if page.get("response_status") not in (None, "")), None))
    page_cursor_out = tuple(str(page.get("cursor_out") or "") for page in pages)
    latest_decision = str(rate.get("latest_decision") or state.get("latest_rate_limit_decision") or next((page.get("rate_limit_decision") for page in reversed(pages) if page.get("rate_limit_decision")), "") or "")
    cooldown_until = str(rate.get("cooldown_until_utc") or state.get("cooldown_until_utc") or next((page.get("cooldown_until_utc") for page in reversed(pages) if page.get("cooldown_until_utc")), "") or "")
    blank_author = sum(1 for row in entries if not str(row.get("author_name") or "").strip())
    blank_screen = sum(1 for row in entries if not str(row.get("screen_name") or "").strip())
    with_media = sum(1 for row in entries if row.get("media_urls"))
    replies = sum(1 for row in entries if str(row.get("in_reply_to_status_id") or row.get("in_reply_to_screen_name") or "").strip())
    next_cursor_url_available = bool(str(templates.get("next_cursor_url") or state.get("next_cursor_url") or "").strip())
    warnings: list[str] = []
    if not entries:
        warnings.append("cursor_entries_missing_or_empty")
    if not pages:
        warnings.append("cursor_pages_missing_or_empty")
    if response_status == 403 or latest_decision == "stop_auth_or_access_boundary":
        warnings.append("auth_or_access_boundary")
    repair = _build_cursor_template_repair(pages=pages, state=state, templates=templates)
    cycle = TwitterCycleCloseout(
        cycle_name=cycle_path.name,
        cycle_path=str(cycle_path),
        exists=cycle_path.exists(),
        entries_count=len(entries),
        unique_status_ids=len(ids),
        new_unique_status_ids=len(new_ids),
        pages_count=len(pages) or int(state.get("pages_count") or 0),
        stop_reason=str(state.get("stop_reason") or ""),
        response_status=response_status,
        rate_limit_remaining=_int_or_none(rate.get("rate_limit_remaining") if "rate_limit_remaining" in rate else state.get("rate_limit_remaining")),
        cooldown_until_utc=cooldown_until,
        latest_decision=latest_decision,
        replay_modes=_dedupe(page.get("replay_mode") for page in pages),
        page_cursor_out=page_cursor_out,
        state_last_cursor_out=str(state.get("last_cursor_out") or ""),
        state_next_cursor_url_blank=not bool(str(state.get("next_cursor_url") or "").strip()),
        templates_next_cursor_url_blank=not bool(str(templates.get("next_cursor_url") or "").strip()),
        next_cursor_url_available=next_cursor_url_available,
        cursor_template_repair=repair,
        blank_author_count=blank_author,
        blank_screen_count=blank_screen,
        with_media_count=with_media,
        reply_count=replies,
        file_hashes=_cycle_file_hashes(cycle_path),
        warnings=tuple(warnings + list(repair.get("warnings") or [])),
    )
    return cycle, ids, entries


def build_profile_media_records(
    entries_by_id: Mapping[str, Mapping[str, Any]],
    *,
    source_url: str,
    canonical_url: str,
    account_context_candidate: str,
    source_cycles_by_id: Mapping[str, str],
    source_cycle_dirs_by_id: Mapping[str, str],
    replay_modes_by_id: Mapping[str, str],
) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for status_id in sorted(entries_by_id):
        row = dict(entries_by_id[status_id])
        media_urls = tuple(str(url) for url in (row.get("media_urls") or []) if str(url))
        author_missing = not bool(str(row.get("author_name") or "").strip())
        screen_missing = not bool(str(row.get("screen_name") or "").strip())
        review_lanes = ["twitter_x_author_identity_review", "claim_subject_affiliation_review", "source_role_review"]
        if media_urls:
            review_lanes.append("social_media_video_provenance_review")
        records.append(
            {
                "schema_version": "twitter-profile-media-record-v77c",
                "platform": "X/Twitter",
                "source_url": source_url,
                "canonical_url": str(row.get("canonical_url") or (f"https://x.com/{account_context_candidate}/status/{status_id}" if account_context_candidate else "")),
                "timeline_canonical_url": canonical_url,
                "status_id": status_id,
                "conversation_id": str(row.get("conversation_id") or ""),
                "created_at": str(row.get("created_at") or ""),
                "post_text": str(row.get("post_text") or ""),
                "author_name": str(row.get("author_name") or ""),
                "screen_name": str(row.get("screen_name") or ""),
                "in_reply_to_screen_name": str(row.get("in_reply_to_screen_name") or ""),
                "in_reply_to_status_id": str(row.get("in_reply_to_status_id") or ""),
                "media_urls": list(media_urls),
                "media_references": [
                    {
                        "media_url": url,
                        "reference_type": "external_platform_media_url",
                        "media_download_performed": False,
                        "local_media_path": "",
                        "sha256": "",
                    }
                    for url in media_urls
                ],
                "links": list(row.get("links") or []),
                "reply_count": row.get("reply_count"),
                "retweet_count": row.get("retweet_count"),
                "quote_count": row.get("quote_count"),
                "like_count": row.get("like_count"),
                "bookmark_count": row.get("bookmark_count"),
                "view_count": row.get("view_count"),
                "source_query_name": str(row.get("source_query_name") or ""),
                "source_page_number": row.get("source_page_number"),
                "provenance": str(row.get("provenance") or "browser_session_graphql_timeline_entry_v74"),
                "capture_output_cycle": source_cycles_by_id.get(status_id, ""),
                "capture_output_dir": source_cycle_dirs_by_id.get(status_id, ""),
                "capture_replay_mode": replay_modes_by_id.get(status_id, ""),
                "account_context_candidate": account_context_candidate,
                "account_context_from_source_url": account_context_candidate,
                "account_context_basis": "source_profile_url",
                "account_context_inferred_from_profile_url": True,
                "account_context_requires_review": True,
                "author_name_missing": author_missing,
                "screen_name_missing": screen_missing,
                "author_row_identity_missing_review": author_missing or screen_missing,
                "source_role_candidate": "PRIMARY_ORIGINAL_AUTHORED_SOURCE_FOR_POST_TEXT_ONLY" if row.get("post_text") else "REVIEW_REQUIRED_SOURCE_ROLE_CANDIDATE",
                "source_role_limitation": "post_text_only_and_account_context_requires_review_when row author/screen fields are blank",
                "final_source_role_decision": False,
                "claim_subject_affiliation_gap": True,
                "media_download_performed": False,
                "review_lanes": review_lanes,
            }
        )
    return tuple(records)


def _preservation_status(output_root: Path, cycles: Sequence[TwitterCycleCloseout]) -> dict[str, Any]:
    screenshot_files = [path for path in output_root.rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    dom_files = [path for path in output_root.rglob("*") if path.is_file() and path.name.lower() in {"rendered_dom_snapshot.html", "rendered-page.html"}]
    return {
        "rendered_dom_status": "available" if dom_files else "missing",
        "rendered_dom_paths": [str(path) for path in dom_files],
        "screenshot_references": "present" if screenshot_files else "none",
        "screenshot_paths": [str(path) for path in screenshot_files],
        "full_page_capture_references": "present" if any("full" in path.name.lower() for path in screenshot_files) else "none",
        "local_output_file_hashes": "present" if any(cycle.file_hashes for cycle in cycles) else "missing",
        "archive_ready_manifest": True,
    }


def build_twitter_live_output_closeout(
    *,
    output_root: str | Path,
    source_url: str,
    profile_tab: str = "replies",
    cycle_folders: Sequence[str | Path] = (),
) -> tuple[TwitterLiveOutputCloseout, tuple[dict[str, Any], ...]]:
    root = Path(os.path.expandvars(str(output_root or ""))).expanduser().resolve()
    cycles_paths = discover_cycle_folders(root, cycle_folders=cycle_folders)
    canonical = canonical_timeline_url(source_url, profile_tab)
    account_context = account_context_from_source_url(source_url)
    cycles: list[TwitterCycleCloseout] = []
    all_ids: set[str] = set()
    entries_by_id: dict[str, Mapping[str, Any]] = {}
    source_cycles_by_id: dict[str, str] = {}
    source_cycle_dirs_by_id: dict[str, str] = {}
    replay_modes_by_id: dict[str, str] = {}
    auth_cycle: TwitterCycleCloseout | None = None
    for path in cycles_paths:
        cycle, ids, entries = summarize_cycle(path, set(all_ids))
        cycles.append(cycle)
        all_ids.update(ids)
        replay_mode = cycle.replay_modes[-1] if cycle.replay_modes else ""
        for row in entries:
            status_id = str(row.get("status_id") or "")
            if not status_id:
                continue
            entries_by_id[status_id] = row
            if status_id in source_cycles_by_id:
                continue
            entries_by_id[status_id] = row
            source_cycles_by_id[status_id] = cycle.cycle_name
            source_cycle_dirs_by_id[status_id] = cycle.cycle_path
            replay_modes_by_id[status_id] = replay_mode
        if cycle.response_status == 403 or cycle.latest_decision == "stop_auth_or_access_boundary" or cycle.stop_reason == "auth_or_access_boundary":
            auth_cycle = cycle
    records = build_profile_media_records(
        entries_by_id,
        source_url=source_url,
        canonical_url=canonical,
        account_context_candidate=account_context,
        source_cycles_by_id=source_cycles_by_id,
        source_cycle_dirs_by_id=source_cycle_dirs_by_id,
        replay_modes_by_id=replay_modes_by_id,
    )
    author_missing = sum(1 for record in records if record["author_row_identity_missing_review"])
    screen_missing = sum(1 for record in records if record["screen_name_missing"])
    media_count = sum(1 for record in records if record["media_urls"])
    reply_count = sum(1 for record in records if record["in_reply_to_status_id"] or record["in_reply_to_screen_name"])
    auth = {
        "detected": auth_cycle is not None,
        "cycle_name": auth_cycle.cycle_name if auth_cycle else "",
        "response_status": auth_cycle.response_status if auth_cycle else None,
        "latest_decision": auth_cycle.latest_decision if auth_cycle else "",
        "safe_to_continue_live": False if auth_cycle else True,
        "live_rerun_recommended": False,
        "review_required": bool(auth_cycle),
    }
    safety = {
        "browser_launch_performed": False,
        "web_download_performed": False,
        "media_download_performed": False,
        "official_x_api_used": False,
        "write_actions_performed": False,
        "credential_automation_performed": False,
        "captcha_bypass_performed": False,
        "proxy_or_evasion_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
    }
    bridge = {
        "record_count": len(records),
        "account_context_candidate": account_context,
        "account_context_basis": "source_profile_url",
        "account_context_requires_review": True,
        "account_context_inferred_from_profile_url": True,
        "author_row_identity_missing_count": author_missing,
        "screen_name_missing_count": screen_missing,
        "media_reference_count": media_count,
        "reply_count": reply_count,
        "final_source_role_decision": False,
    }
    warnings: list[str] = []
    if auth_cycle:
        warnings.append("auth_or_access_boundary_detected_review_required_no_live_rerun_recommended")
    if author_missing:
        warnings.append("author_screen_identity_blank_in_rows_context_only_from_source_url")
    closeout = TwitterLiveOutputCloseout(
        source_url=source_url,
        canonical_url=canonical,
        profile_tab=profile_tab,
        output_root=str(root),
        cycle_count=len(cycles),
        total_unique_status_ids=len(all_ids),
        cycles=tuple(cycles),
        auth_or_access_boundary=auth,
        profile_media_bridge=bridge,
        preservation_status=_preservation_status(root, cycles),
        safety_flags=safety,
        warnings=tuple(warnings),
    )
    return closeout, records


def write_twitter_live_output_closeout(
    *,
    closeout: TwitterLiveOutputCloseout,
    profile_media_records: Sequence[Mapping[str, Any]],
    output_json: str | Path = "",
    profile_media_records_jsonl: str | Path = "",
    confirm_write: str = "",
) -> dict[str, Any]:
    result = {
        "schema_version": TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_SCHEMA_VERSION,
        "status": "blocked_confirmation_required",
        "confirmation_required": WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C,
        "output_json": str(output_json or ""),
        "profile_media_records_jsonl": str(profile_media_records_jsonl or ""),
        "file_write_performed": False,
        "browser_launch_performed": False,
        "web_download_performed": False,
        "media_download_performed": False,
        "write_actions_performed": False,
        "warnings": ["write_blocked_confirmation_required"],
    }
    if str(confirm_write or "") != WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C:
        return result
    if output_json:
        _write_json(output_json, closeout.to_dict())
    if profile_media_records_jsonl:
        _write_jsonl(profile_media_records_jsonl, profile_media_records)
    result["status"] = "twitter_capture_live_output_closeout_written"
    result["file_write_performed"] = bool(output_json or profile_media_records_jsonl)
    result["warnings"] = []
    return result


def render_twitter_live_output_closeout_text(closeout: TwitterLiveOutputCloseout) -> str:
    data = closeout.to_dict()
    lines = [
        "V77C TWITTER/X LIVE OUTPUT CLOSEOUT",
        f"offline_closeout_only: {data['offline_closeout_only']}",
        f"source_url: {data['source_url']}",
        f"canonical_url: {data['canonical_url']}",
        f"profile_tab: {data['profile_tab']}",
        f"cycles: {data['cycle_count']}",
        f"total_unique_status_ids: {data['total_unique_status_ids']}",
    ]
    for cycle in data["cycles"]:
        name = str(cycle["cycle_name"])
        short = name[-4:] if len(name) >= 4 else name
        lines.append(f"cycle {short} entries: {cycle['entries_count']}")
        lines.append(f"cycle {short} stop_reason: {cycle['stop_reason']}")
        lines.append(f"cycle {short} response_status: {cycle['response_status']}")
        lines.append(f"cycle {short} cursor_template_repair needed: {cycle['cursor_template_repair'].get('needed')}")
        lines.append(f"cycle {short} cursor resume/template available: {cycle['next_cursor_url_available']}")
    bridge = data["profile_media_bridge"]
    auth = data["auth_or_access_boundary"]
    safety = data["safety_flags"]
    lines.extend(
        [
            f"auth_or_access_boundary_detected: {auth.get('detected')}",
            f"safe_to_continue_live: {auth.get('safe_to_continue_live')}",
            f"live_rerun_recommended: {auth.get('live_rerun_recommended')}",
            f"profile_media_records: {bridge.get('record_count')}",
            f"account_context_candidate: {bridge.get('account_context_candidate')}",
            f"author_row_identity_missing_count: {bridge.get('author_row_identity_missing_count')}",
            f"screen_name_missing_count: {bridge.get('screen_name_missing_count')}",
            f"media_reference_count: {bridge.get('media_reference_count')}",
            f"reply_count: {bridge.get('reply_count')}",
            f"final_source_role_decision: {bridge.get('final_source_role_decision')}",
            f"official_x_api_used: {safety.get('official_x_api_used')}",
            f"browser_launch_performed: {safety.get('browser_launch_performed')}",
            f"web_download_performed: {safety.get('web_download_performed')}",
            f"media_download_performed: {safety.get('media_download_performed')}",
            f"write_actions_performed: {safety.get('write_actions_performed')}",
            "warnings: " + (", ".join(data["warnings"]) if data["warnings"] else "NONE"),
        ]
    )
    return "\n".join(lines)
