from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAYBACK_CDX_ENDPOINT = "https://web.archive.org/cdx"
WAYBACK_TIMEMAP_JSON_PREFIX = "https://web.archive.org/web/timemap/json/"
WAYBACK_TIMEGATE_PREFIX = "https://web.archive.org/web/"
WAYBACK_SAVE_PREFIX = "https://web.archive.org/save/"
TIMETRAVEL_LIST_PREFIX = "https://timetravel.mementoweb.org/list/"


@dataclass
class MementoRecord:
    timestamp: str
    original: str
    statuscode: str = ""
    mimetype: str = ""
    digest: str = ""
    length: str = ""
    archive_url: str = ""
    query_variant: str = ""


@dataclass
class ArchiveQueryResult:
    label: str
    query_url: str
    status: str
    memento_count: int = 0
    first_memento: MementoRecord | None = None
    latest_memento: MementoRecord | None = None
    error: str = ""


@dataclass
class TimeMapLookupResult:
    label: str
    timemap_url: str
    status: str
    memento_count: int = 0
    first_memento_url: str = ""
    latest_memento_url: str = ""
    error: str = ""


@dataclass
class ArchiveDiscoveryResult:
    input_url: str
    target_url: str
    checked_at_utc: str
    network_enabled: bool
    status: str
    memento_count: int
    first_memento: MementoRecord | None = None
    latest_memento: MementoRecord | None = None
    recent_mementos: list[MementoRecord] = field(default_factory=list)
    query_variants: list[str] = field(default_factory=list)
    query_results: list[ArchiveQueryResult] = field(default_factory=list)
    timemap_results: list[TimeMapLookupResult] = field(default_factory=list)
    timemap_url: str = ""
    timegate_url: str = ""
    manual_archive_candidates: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_markdown_link(value: str) -> str:
    match = re.fullmatch(r"\s*\[[^\]]+\]\((.+)\)\s*", value)
    if match:
        return match.group(1).strip()
    return value


def normalize_target_url(url: str) -> str:
    """Normalize URLs copied from CMD, Markdown, or chat without changing real URL intent."""
    value = (url or "").strip().strip('"').strip("'").strip()
    value = _extract_markdown_link(value)
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    # CMD/chat escaping must never enter archive sidecars or CDX queries.
    value = value.replace("^&", "&")
    value = value.replace("\\&", "&")
    value = value.replace("\\_", "_")
    value = value.replace("\\:", ":")
    value = value.replace("\\/", "/")
    value = value.replace(" ", "%20")
    return value


def url_without_fragment(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def url_without_query_or_fragment(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def archive_query_variants(normalized_url: str) -> list[tuple[str, str]]:
    variants: list[tuple[str, str]] = []
    def add(label: str, value: str) -> None:
        if value and value not in [item[1] for item in variants]:
            variants.append((label, value))
    add("exact", normalized_url)
    add("without_fragment", url_without_fragment(normalized_url))
    add("without_query_or_fragment", url_without_query_or_fragment(normalized_url))
    # MSN URLs are often archived without campaign/query params, but keep exact first.
    return variants


def wayback_archive_url(timestamp: str, original: str) -> str:
    return f"https://web.archive.org/web/{timestamp}/{original}"


def build_cdx_query_url(target_url: str, *, limit: int = 200, filter_200: bool = True, collapse_digest: bool = True) -> str:
    params: list[tuple[str, str]] = [
        ("url", target_url),
        ("output", "json"),
        ("fl", "timestamp,original,statuscode,mimetype,digest,length"),
    ]
    if filter_200:
        params.append(("filter", "statuscode:200"))
    if collapse_digest:
        params.append(("collapse", "digest"))
    params.append(("limit", str(limit)))
    return WAYBACK_CDX_ENDPOINT + "?" + urllib.parse.urlencode(params)


def manual_archive_candidates(normalized_url: str) -> dict[str, str]:
    encoded = urllib.parse.quote(normalized_url, safe="")
    no_query = url_without_query_or_fragment(normalized_url)
    return {
        "wayback_save_page_now": WAYBACK_SAVE_PREFIX + normalized_url,
        "wayback_cdx_exact_json": build_cdx_query_url(normalized_url, filter_200=False, collapse_digest=False),
        "wayback_cdx_no_query_json": build_cdx_query_url(no_query, filter_200=False, collapse_digest=False),
        "wayback_timemap_json": WAYBACK_TIMEMAP_JSON_PREFIX + normalized_url,
        "wayback_timegate": WAYBACK_TIMEGATE_PREFIX + normalized_url,
        "timetravel_memento_list": TIMETRAVEL_LIST_PREFIX + encoded,
        "archive_today_manual_search": "https://archive.today/" + normalized_url,
    }


def parse_cdx_json(payload: bytes, *, query_variant: str = "") -> list[MementoRecord]:
    text = payload.decode("utf-8", "replace").strip()
    if not text:
        return []
    data = json.loads(text)
    if not isinstance(data, list) or not data:
        return []
    header = data[0]
    if not isinstance(header, list):
        return []
    records: list[MementoRecord] = []
    for row in data[1:]:
        if not isinstance(row, list):
            continue
        item = dict(zip(header, row))
        ts = str(item.get("timestamp") or "")
        original = str(item.get("original") or "")
        if not ts or not original:
            continue
        records.append(
            MementoRecord(
                timestamp=ts,
                original=original,
                statuscode=str(item.get("statuscode") or ""),
                mimetype=str(item.get("mimetype") or ""),
                digest=str(item.get("digest") or ""),
                length=str(item.get("length") or ""),
                archive_url=wayback_archive_url(ts, original),
                query_variant=query_variant,
            )
        )
    return records


def fetch_cdx_records(query_url: str, *, query_variant: str = "", timeout: int = 30) -> tuple[list[MementoRecord], str | None]:
    try:
        request = urllib.request.Request(query_url, headers={"User-Agent": "ytce-memento-discovery/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
        return parse_cdx_json(payload, query_variant=query_variant), None
    except Exception as exc:  # noqa: BLE001 - sidecar records errors instead of crashing.
        return [], f"{type(exc).__name__}: {exc}"


def _extract_memento_urls_from_timemap_payload(payload: bytes) -> list[str]:
    """Return archived URLs found in a Memento/Wayback TimeMap JSON response.

    Wayback JSON TimeMaps may vary, so this parser is deliberately tolerant: it
    walks nested lists/dicts and records any web.archive.org/web/<timestamp>/...
    strings instead of depending on a single schema version.
    """
    text = payload.decode("utf-8", "replace")
    urls = re.findall(r"https?://web\.archive\.org/web/\d{8,14}/[^\s\"'<>]+", text)
    try:
        data = json.loads(text)
    except Exception:
        return sorted(set(urls))

    def walk(value: Any) -> None:
        if isinstance(value, str):
            urls.extend(re.findall(r"https?://web\.archive\.org/web/\d{8,14}/[^\s\"'<>]+", value))
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)

    walk(data)
    return sorted(set(urls))


def fetch_timemap_summary(timemap_url: str, *, label: str = "timemap", timeout: int = 20) -> TimeMapLookupResult:
    try:
        request = urllib.request.Request(timemap_url, headers={"User-Agent": "ytce-memento-discovery/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
        urls = _extract_memento_urls_from_timemap_payload(payload)
        return TimeMapLookupResult(
            label=label,
            timemap_url=timemap_url,
            status="MEMENTOS_FOUND" if urls else "NO_TIMEMAP_MEMENTOS_FOUND",
            memento_count=len(urls),
            first_memento_url=urls[0] if urls else "",
            latest_memento_url=urls[-1] if urls else "",
        )
    except Exception as exc:  # noqa: BLE001 - sidecar records errors instead of crashing.
        return TimeMapLookupResult(label=label, timemap_url=timemap_url, status="TIMEMAP_QUERY_ERROR", error=f"{type(exc).__name__}: {exc}")


def _dedupe_records(records: list[MementoRecord]) -> list[MementoRecord]:
    seen: set[tuple[str, str, str]] = set()
    out: list[MementoRecord] = []
    for record in sorted(records, key=lambda item: item.timestamp):
        key = (record.timestamp, record.original, record.digest)
        if key in seen:
            continue
        seen.add(key)
        out.append(record)
    return out


def discover_archives(target_url: str, *, network: bool = True, checked_at_utc: str | None = None) -> ArchiveDiscoveryResult:
    normalized = normalize_target_url(target_url)
    variants = archive_query_variants(normalized)
    result = ArchiveDiscoveryResult(
        input_url=target_url,
        target_url=normalized,
        checked_at_utc=checked_at_utc or utc_now_iso(),
        network_enabled=network,
        status="NOT_CHECKED",
        memento_count=0,
        query_variants=[value for _, value in variants],
        timemap_url=WAYBACK_TIMEMAP_JSON_PREFIX + normalized,
        timegate_url=WAYBACK_TIMEGATE_PREFIX + normalized,
        manual_archive_candidates=manual_archive_candidates(normalized),
    )
    if normalized != target_url:
        result.warnings.append("Input URL was normalized before archive lookup; shell/Markdown escaping was not used in CDX queries.")
    if not normalized.startswith(("http://", "https://")):
        result.status = "INVALID_TARGET_URL"
        result.errors.append("Target URL must start with http:// or https://")
        return result
    if not network:
        result.status = "NETWORK_DISABLED_MANUAL_CANDIDATES_ONLY"
        result.warnings.append("Network lookup disabled; CDX/TimeMap candidates recorded but not queried.")
        for label, value in variants:
            result.query_results.append(ArchiveQueryResult(label=label, query_url=build_cdx_query_url(value), status="NOT_QUERIED"))
            result.timemap_results.append(TimeMapLookupResult(label=label, timemap_url=WAYBACK_TIMEMAP_JSON_PREFIX + value, status="NOT_QUERIED"))
        return result

    all_records: list[MementoRecord] = []
    for label, value in variants:
        query_url = build_cdx_query_url(value)
        records, error = fetch_cdx_records(query_url, query_variant=label)
        if error:
            result.query_results.append(ArchiveQueryResult(label=label, query_url=query_url, status="CDX_QUERY_ERROR", error=error))
            continue
        sorted_records = sorted(records, key=lambda item: item.timestamp)
        result.query_results.append(
            ArchiveQueryResult(
                label=label,
                query_url=query_url,
                status="MEMENTOS_FOUND" if sorted_records else "NO_CDX_MEMENTOS_FOUND",
                memento_count=len(sorted_records),
                first_memento=sorted_records[0] if sorted_records else None,
                latest_memento=sorted_records[-1] if sorted_records else None,
            )
        )
        all_records.extend(sorted_records)

    # A Mink/Memento-style discovery sidecar should not only print a TimeMap URL;
    # it should try the TimeMap endpoint and record whether that lookup worked.
    for label, value in variants:
        result.timemap_results.append(fetch_timemap_summary(WAYBACK_TIMEMAP_JSON_PREFIX + value, label=label))

    unique_records = _dedupe_records(all_records)
    result.memento_count = len(unique_records)
    if unique_records:
        result.first_memento = unique_records[0]
        result.latest_memento = unique_records[-1]
        result.recent_mementos = unique_records[-10:]
        result.status = "MEMENTOS_FOUND"
    else:
        cdx_errors = [q.error for q in result.query_results if q.error]
        timemap_errors = [q.error for q in result.timemap_results if q.error]
        timemap_found = [q for q in result.timemap_results if q.memento_count > 0]
        if timemap_found:
            result.status = "MEMENTOS_FOUND_TIMEMAP_ONLY"
            result.memento_count = sum(item.memento_count for item in timemap_found)
            result.warnings.append("CDX returned no usable 200-status records, but TimeMap lookup reported mementos.")
        elif cdx_errors or timemap_errors:
            result.status = "ARCHIVE_LOOKUP_PARTIAL_ERROR_NO_MEMENTOS_CONFIRMED"
            result.warnings.append("One or more archive lookup endpoints failed; no mementos were confirmed from the completed queries.")
            result.errors.extend(cdx_errors)
            result.errors.extend(timemap_errors)
        else:
            result.status = "NO_CDX_OR_TIMEMAP_MEMENTOS_FOUND"
            result.warnings.append("Internet Archive CDX and TimeMap lookups returned no confirmed mementos for exact or fallback query variants.")
    return result


def _record_to_dict(record: MementoRecord | None) -> dict[str, Any] | None:
    return asdict(record) if record else None


def result_to_dict(result: ArchiveDiscoveryResult) -> dict[str, Any]:
    data = asdict(result)
    data["first_memento"] = _record_to_dict(result.first_memento)
    data["latest_memento"] = _record_to_dict(result.latest_memento)
    data["recent_mementos"] = [asdict(item) for item in result.recent_mementos]
    data["query_results"] = [asdict(item) for item in result.query_results]
    return data


def result_to_text(result: ArchiveDiscoveryResult) -> str:
    lines: list[str] = []
    lines.append("MEMENTO / MINK-STYLE ARCHIVE DISCOVERY")
    lines.append(f"target_url: {result.target_url}")
    lines.append(f"input_url_normalized: {result.input_url != result.target_url}")
    lines.append(f"checked_at_utc: {result.checked_at_utc}")
    lines.append(f"network_enabled: {result.network_enabled}")
    lines.append(f"status: {result.status}")
    lines.append(f"memento_count: {result.memento_count}")
    lines.append(f"timemap_url: {result.timemap_url}")
    lines.append(f"timegate_url: {result.timegate_url}")
    lines.append("")
    lines.append("QUERY_VARIANTS:")
    for value in result.query_variants:
        lines.append(f"  - {value}")
    lines.append("")
    lines.append("QUERY_RESULTS:")
    for item in result.query_results:
        lines.append(f"  - {item.label}: {item.status}; count={item.memento_count}")
        lines.append(f"    cdx_query_url: {item.query_url}")
        if item.first_memento:
            lines.append(f"    first: {item.first_memento.timestamp} {item.first_memento.archive_url}")
        if item.latest_memento:
            lines.append(f"    latest: {item.latest_memento.timestamp} {item.latest_memento.archive_url}")
        if item.error:
            lines.append(f"    error: {item.error}")
    lines.append("")
    lines.append("TIMEMAP_RESULTS:")
    for item in result.timemap_results:
        lines.append(f"  - {item.label}: {item.status}; count={item.memento_count}")
        lines.append(f"    timemap_url: {item.timemap_url}")
        if item.first_memento_url:
            lines.append(f"    first: {item.first_memento_url}")
        if item.latest_memento_url:
            lines.append(f"    latest: {item.latest_memento_url}")
        if item.error:
            lines.append(f"    error: {item.error}")
    if result.first_memento:
        lines.append("")
        lines.append(f"FIRST_MEMENTO: {result.first_memento.timestamp} {result.first_memento.archive_url}")
    if result.latest_memento:
        lines.append(f"LATEST_MEMENTO: {result.latest_memento.timestamp} {result.latest_memento.archive_url}")
    lines.append("")
    lines.append("WARNINGS:")
    if result.warnings:
        for warning in result.warnings:
            lines.append(f"  - {warning}")
    else:
        lines.append("  - NONE")
    lines.append("")
    lines.append("ERRORS:")
    if result.errors:
        for error in result.errors:
            lines.append(f"  - {error}")
    else:
        lines.append("  - NONE")
    lines.append("")
    lines.append("MANUAL_ARCHIVE_CANDIDATES:")
    for name, url in result.manual_archive_candidates.items():
        lines.append(f"  - {name}: {url}")
    lines.append("")
    lines.append("RECENT_MEMENTOS:")
    if result.recent_mementos:
        for record in result.recent_mementos:
            lines.append(f"  - {record.timestamp} [{record.query_variant}] {record.archive_url}")
    else:
        lines.append("  - NONE")
    return "\n".join(lines) + "\n"


def write_discovery_sidecars(result: ArchiveDiscoveryResult, output_dir: str | Path) -> tuple[Path, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "memento_archive_discovery.json"
    txt_path = out / "memento_archive_discovery.txt"
    json_path.write_text(json.dumps(result_to_dict(result), indent=2, ensure_ascii=False), encoding="utf-8")
    txt_path.write_text(result_to_text(result), encoding="utf-8")
    return json_path, txt_path
