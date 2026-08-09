from __future__ import annotations

import gzip
import hashlib
from collections import defaultdict, deque
from io import BytesIO
import json
import os
import re
import subprocess
import tempfile
import zipfile
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from source_replay_static_snapshot import (
    DEFAULT_REPLAY_RUNTIME_LIMITATION_NOTES,
    REPLAYWEB_RUNTIME_PARTIAL_RENDER,
    STATIC_EVIDENCE_VIEW_READY,
    StaticReplayCommentsEvidence,
    StaticReplayEvidenceInput,
    build_static_evidence_url,
    build_static_replay_evidence_page,
)


REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION = "source_local_web_archive_actions_v1"

VIEWER_NOT_CONFIGURED = "VIEWER_NOT_CONFIGURED"
VIEWER_CONFIGURED = "VIEWER_CONFIGURED"
USER_LOCAL_INSTALL_NOT_AVAILABLE = "USER_LOCAL_INSTALL_NOT_AVAILABLE"
STRUCTURAL_WACZ_VALID = "STRUCTURAL_WACZ_VALID"
REPLAY_OPENED = "REPLAY_OPENED"
REPLAY_PARTIAL = "REPLAY_PARTIAL"
REPLAY_VISUALLY_VERIFIED = "REPLAY_VISUALLY_VERIFIED"
USER_VISUAL_CONFIRMATION_REQUIRED = "USER_VISUAL_CONFIRMATION_REQUIRED"
REPLAY_FAILED = "REPLAY_FAILED"
WACZ_REPLAY_COMPATIBILITY_REPAIRED = "WACZ_REPLAY_COMPATIBILITY_REPAIRED"
REPLAYWEB_PAGE_COMPATIBLE = "REPLAYWEB_PAGE_COMPATIBLE"
REPLAYWEB_PAGE_PACKAGE_READY = "REPLAYWEB_PAGE_PACKAGE_READY"
WACZ_12_COMPATIBILITY_PROFILE = "wacz12"
REPLAYWEB_PAGE_COMPATIBILITY_PROFILE = "replayweb-page"

SHOW_FILES_READY = "SHOW_FILES_READY"
SHOW_FILES_PREVIEWED = "SHOW_FILES_PREVIEWED"
OPEN_ARCHIVE_PREVIEWED = "OPEN_ARCHIVE_PREVIEWED"

LOCAL_WEB_ARCHIVE_SCOPE = (
    "Local Web Archive ReplayWeb.page action state; verifies caller-selected local WACZ "
    "and manifest artifacts, builds safe argument-array launch previews, and performs no "
    "live site access, archive submission, credential use, browser-profile access, or "
    "external viewer launch unless a caller explicitly supplies an execution launcher"
)

REPLAYWEB_RELEASES_LATEST_API_URL = (
    "https://api.github.com/repos/webrecorder/replayweb.page/releases/latest"
)
REPLAYWEB_OFFICIAL_RELEASES_URL = "https://github.com/webrecorder/replayweb.page/releases/latest"
REPLAYWEB_OFFICIAL_WEB_APP_URL = "https://replayweb.page/"

REQUIRED_WACZ_ENTRIES = frozenset(
    {
        "datapackage.json",
        "pages/pages.jsonl",
        "indexes/index.cdx.gz",
    }
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
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_path_name(path: str | Path) -> str:
    return Path(path).name


def _load_json_file(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ReplayWebReleaseAsset:
    name: str
    browser_download_url: str
    size_bytes: int
    content_type: str = ""
    official_source: str = REPLAYWEB_OFFICIAL_RELEASES_URL

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ReplayWebReleaseMetadata:
    status: str
    tag_name: str = ""
    release_name: str = ""
    html_url: str = ""
    windows_assets: tuple[ReplayWebReleaseAsset, ...] = ()
    official_api_url: str = REPLAYWEB_RELEASES_LATEST_API_URL
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["windows_asset_count"] = len(self.windows_assets)
        return data


@dataclass(frozen=True)
class ReplayWebViewerDetection:
    status: str
    executable_path: str = ""
    executable_name: str = ""
    executable_sha256: str = ""
    version_hint: str = ""
    detection_source: str = ""
    searched_names: tuple[str, ...] = ()
    configuration_help: str = (
        "Set REPLAYWEBPAGE_PATH to the ReplayWeb.page desktop executable, or install the "
        "official user-local ReplayWeb.page desktop app."
    )
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LocalWebArchiveVerificationResult:
    status: str
    wacz_name: str
    wacz_sha256: str = ""
    wacz_size_bytes: int = 0
    manifest_name: str = ""
    manifest_sha256: str = ""
    zip_integrity_ok: bool = False
    required_entries_present: bool = False
    missing_required_entries: tuple[str, ...] = ()
    datapackage_profile: str = ""
    wacz_version: str = ""
    wacz_spec_target: str = "1.2.0"
    legacy_declared_wacz_version: str = ""
    deprecated_datapackage_fields: tuple[str, ...] = ()
    index_sorted: bool = False
    index_search_keys_canonical: bool = False
    replay_lookup_ready: bool = False
    page_count: int = 0
    index_line_count: int = 0
    warc_record_count: int = 0
    expected_source_url_found: bool = False
    replayweb_acceptance_basis: str = "structural verification only"
    comments_json_count: int = 0
    comments_jsonl_count: int = 0
    declared_comment_count: int = 0
    top_level_comment_count: int = 0
    reply_count: int = 0
    comments_complete: bool = False
    comments_evidence_status: str = "not_checked"
    faithful_comments_screenshot_name: str = ""
    faithful_comments_screenshot_sha256: str = ""
    derived_comments_visual_name: str = ""
    derived_comments_visual_sha256: str = ""
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION
    scope: str = LOCAL_WEB_ARCHIVE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LocalWebArchiveRepairResult:
    status: str
    input_name: str
    output_name: str
    input_sha256: str = ""
    output_sha256: str = ""
    output_size_bytes: int = 0
    rewritten_index_count: int = 0
    removed_legacy_fields: tuple[str, ...] = ()
    verification_status: str = ""
    verification_statuses: tuple[str, ...] = ()
    static_evidence_status: str = ""
    static_evidence_page_url: str = ""
    replay_runtime_status: str = ""
    replay_runtime_notes: tuple[str, ...] = ()
    original_preserved: bool = True
    errors: tuple[str, ...] = ()
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION
    scope: str = LOCAL_WEB_ARCHIVE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LocalWebArchiveCommandPreview:
    status: str
    argv: tuple[str, ...] = ()
    shell: bool = False
    executed: bool = False
    message: str = ""
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["argv_name_only"] = tuple(_safe_path_name(item) if index == 0 else item for index, item in enumerate(self.argv))
        return data


@dataclass(frozen=True)
class LocalWebArchiveActionState:
    archive_name: str
    capture_locally_status: str
    open_archive_status: str
    show_files_status: str
    verify_status: str
    replay_visual_status: str
    viewer: ReplayWebViewerDetection
    verification: LocalWebArchiveVerificationResult
    open_preview: LocalWebArchiveCommandPreview
    show_files_preview: LocalWebArchiveCommandPreview
    browser_pwa_status: str
    browser_pwa_note: str
    no_live_site_access_performed: bool = True
    no_archive_submit_performed: bool = True
    no_credentials_or_cookies_used: bool = True
    no_second_source_tested: bool = True
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION
    scope: str = LOCAL_WEB_ARCHIVE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def parse_replayweb_release_metadata(payload: Mapping[str, Any]) -> ReplayWebReleaseMetadata:
    assets: list[ReplayWebReleaseAsset] = []
    for asset in payload.get("assets") or ():
        if not isinstance(asset, Mapping):
            continue
        name = str(asset.get("name") or "")
        lowered = name.lower()
        if not (lowered.endswith(".exe") or lowered.endswith(".zip")):
            continue
        if "replayweb.page" not in lowered:
            continue
        assets.append(
            ReplayWebReleaseAsset(
                name=name,
                browser_download_url=str(asset.get("browser_download_url") or ""),
                size_bytes=int(asset.get("size") or 0),
                content_type=str(asset.get("content_type") or ""),
                official_source=str(payload.get("html_url") or REPLAYWEB_OFFICIAL_RELEASES_URL),
            )
        )
    return ReplayWebReleaseMetadata(
        status="OFFICIAL_RELEASE_METADATA_PARSED",
        tag_name=str(payload.get("tag_name") or ""),
        release_name=str(payload.get("name") or ""),
        html_url=str(payload.get("html_url") or ""),
        windows_assets=tuple(sorted(assets, key=lambda item: item.name)),
    )


def default_replaywebpage_candidate_paths(env: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    values = dict(os.environ if env is None else env)
    local_app_data = values.get("LOCALAPPDATA", "")
    user_profile = values.get("USERPROFILE", "")
    candidates: list[Path] = []
    if local_app_data:
        candidates.extend(
            [
                Path(local_app_data) / "Programs" / "ReplayWeb.page" / "ReplayWeb.page.exe",
                Path(local_app_data) / "ReplayWeb.page" / "ReplayWeb.page.exe",
            ]
        )
    if user_profile:
        candidates.extend(
            [
                Path(user_profile) / "AppData" / "Local" / "Programs" / "ReplayWeb.page" / "ReplayWeb.page.exe",
                Path(user_profile) / "Downloads" / "ReplayWeb.page.exe",
            ]
        )
    candidates.append(Path(__file__).resolve().parent / ".local_tools" / "ReplayWeb.page" / "ReplayWeb.page.exe")
    return tuple(candidates)


def _version_hint_from_name(path: Path) -> str:
    match = re.search(r"ReplayWeb\.page[-_ ]?([0-9]+(?:\.[0-9]+){1,3}(?:[-A-Za-z0-9.]*?)?)(?:\.(?:exe|zip|dmg|appimage))?$", path.name, re.IGNORECASE)
    return match.group(1) if match else ""


def detect_replaywebpage_viewer(
    *,
    env: Mapping[str, str] | None = None,
    candidate_paths: Sequence[str | Path] | None = None,
) -> ReplayWebViewerDetection:
    values = dict(os.environ if env is None else env)
    candidates: list[tuple[str, Path]] = []
    env_path = str(values.get("REPLAYWEBPAGE_PATH") or "").strip()
    if env_path:
        candidates.append(("REPLAYWEBPAGE_PATH", Path(env_path)))
    for path in candidate_paths or default_replaywebpage_candidate_paths(values):
        candidates.append(("auto_detect", Path(path)))

    seen: set[str] = set()
    searched: list[str] = []
    for source, path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        searched.append(path.name or key)
        if path.is_file():
            return ReplayWebViewerDetection(
                status=VIEWER_CONFIGURED,
                executable_path=str(path),
                executable_name=path.name,
                executable_sha256=_sha256_file(path),
                version_hint=_version_hint_from_name(path),
                detection_source=source,
                searched_names=tuple(searched),
            )
    return ReplayWebViewerDetection(
        status=VIEWER_NOT_CONFIGURED,
        searched_names=tuple(searched),
    )


def _safe_json_loads(payload: bytes | str) -> Any:
    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    return json.loads(text)


def _parse_pages_jsonl(payload: bytes) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for line in payload.decode("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, Mapping) and item.get("url"):
            rows.append(item)
    return rows


def _warc_record_count_from_zip(bundle: zipfile.ZipFile, names: Sequence[str]) -> tuple[int, list[str]]:
    errors: list[str] = []
    count = 0
    try:
        from warcio.archiveiterator import ArchiveIterator
    except Exception as error:
        return 0, [f"warcio unavailable: {error}"]
    for name in names:
        try:
            with bundle.open(name, "r") as stream:
                count += sum(1 for _record in ArchiveIterator(stream))
        except Exception as error:
            errors.append(f"{name}: {error}")
    return count, errors


def _artifact_by_label(artifacts: Sequence[Mapping[str, Any]], contains: str) -> Mapping[str, Any] | None:
    needle = contains.lower()
    for artifact in artifacts:
        if needle in str(artifact.get("label") or "").lower():
            return artifact
    return None


def _count_jsonl_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def _comments_json_count(path: Path) -> int:
    if not path.is_file():
        return 0
    payload = _load_json_file(path)
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, Mapping):
        rows = payload.get("rows")
        if isinstance(rows, list):
            return len(rows)
        return int(payload.get("row_count") or 0)
    return 0


def _manifest_comments_summary(
    manifest: Mapping[str, Any],
    *,
    expected_comment_count: int = 0,
) -> dict[str, Any]:
    artifacts = [item for item in manifest.get("artifacts") or () if isinstance(item, Mapping)]
    comments_json = _artifact_by_label(artifacts, "android_mobile_chromium_comments_json") or _artifact_by_label(artifacts, "comments_json")
    comments_jsonl = _artifact_by_label(artifacts, "android_mobile_chromium_comments_incremental_jsonl") or _artifact_by_label(artifacts, "comments_incremental_jsonl")
    reconciliation = _artifact_by_label(artifacts, "android_mobile_chromium_comments_provider_reconciliation") or _artifact_by_label(artifacts, "comments_provider_reconciliation")
    faithful = _artifact_by_label(artifacts, "android_mobile_chromium_faithful_comments_screenshot") or _artifact_by_label(artifacts, "faithful_comments_screenshot")
    derived = _artifact_by_label(artifacts, "android_mobile_chromium_derived_comments_full_thread_screenshot") or _artifact_by_label(artifacts, "derived_comments_full_thread_screenshot")

    comments_count = _comments_json_count(Path(str(comments_json.get("path") or ""))) if comments_json else 0
    jsonl_count = _count_jsonl_lines(Path(str(comments_jsonl.get("path") or ""))) if comments_jsonl else 0
    declared = 0
    top_level = 0
    replies = 0
    complete = False
    if reconciliation:
        path = Path(str(reconciliation.get("path") or ""))
        if path.is_file():
            data = _load_json_file(path)
            if isinstance(data, Mapping):
                api = data.get("api_reconciliation")
                provider = data.get("provider_reconciliation")
                if isinstance(api, Mapping):
                    declared = int(api.get("declared_total_count") or api.get("total_count") or 0)
                    top_level = int(api.get("root_record_count") or top_level or 0)
                    replies = int(api.get("reply_record_count") or replies or 0)
                if isinstance(provider, Mapping):
                    complete = bool(provider.get("comments_complete"))
                    declared = declared or int(provider.get("declared_total_count") or 0)
                    top_level = int(
                        provider.get("provider_root_count")
                        or provider.get("root_record_count")
                        or provider.get("root_count")
                        or top_level
                        or 0
                    )
                    replies = int(
                        provider.get("provider_reply_count")
                        or provider.get("reply_record_count")
                        or provider.get("reply_count")
                        or replies
                        or 0
                    )
                top_level = top_level or int(data.get("provider_root_count") or 0)
                replies = replies or int(data.get("provider_reply_count") or 0)
    expected = expected_comment_count or declared
    evidence_ok = comments_count > 0 and (not expected or comments_count == expected)
    if declared:
        evidence_ok = evidence_ok and comments_count == declared
    return {
        "comments_json_count": comments_count,
        "comments_jsonl_count": jsonl_count,
        "declared_comment_count": declared,
        "top_level_comment_count": top_level,
        "reply_count": replies,
        "comments_complete": bool(complete or (expected and comments_count == expected and declared == expected)),
        "comments_evidence_status": "COMMENTS_EVIDENCE_VERIFIED" if evidence_ok else "COMMENTS_EVIDENCE_PARTIAL",
        "faithful_comments_screenshot_name": Path(str(faithful.get("path") or "")).name if faithful else "",
        "faithful_comments_screenshot_sha256": str(faithful.get("sha256") or "") if faithful else "",
        "derived_comments_visual_name": Path(str(derived.get("path") or "")).name if derived else "",
        "derived_comments_visual_sha256": str(derived.get("sha256") or "") if derived else "",
    }


def _cdxj_searchable_url(url: str) -> str:
    parsed = urlsplit(str(url or "").lower())
    host = parsed.hostname or ""
    host_key = ",".join(reversed(host.split(".")))
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return f"{host_key}){path}"


def _cdxj_filename_for_wacz(filename: str) -> str:
    name = str(filename or "")
    if name.startswith("archive/"):
        return Path(name).name
    return name


def _fragmentless_url(url: str) -> str:
    parsed = urlsplit(str(url or ""))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _warc_request_path(url: str) -> str:
    parsed = urlsplit(str(url or ""))
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return path


def _parse_cdxj_line(line: str) -> tuple[str, str, Mapping[str, Any]]:
    searchable, timestamp, payload = line.split(" ", 2)
    row = json.loads(payload)
    if not isinstance(row, Mapping):
        raise ValueError("CDXJ payload is not an object")
    required = {"url", "digest", "mime", "filename", "offset", "length", "status"}
    missing = sorted(required - set(row))
    if missing:
        raise ValueError("CDXJ payload missing required fields: " + ", ".join(missing))
    return searchable, timestamp, row


def _cdxj_entries_from_payload(payload: bytes, *, compressed: bool) -> list[tuple[str, dict[str, Any]]]:
    raw = gzip.decompress(payload) if compressed else payload
    entries: list[tuple[str, dict[str, Any]]] = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        _searchable, timestamp, row = _parse_cdxj_line(line)
        entries.append((timestamp, dict(row)))
    return entries


def _cdxj_payload_from_entries(entries: Sequence[tuple[str, Mapping[str, Any]]], *, compressed: bool) -> bytes:
    lines = []
    for timestamp, row in entries:
        item = dict(row)
        if item.get("filename"):
            item["filename"] = _cdxj_filename_for_wacz(str(item.get("filename") or ""))
        lines.append(
            f"{_cdxj_searchable_url(str(item.get('url') or ''))} {timestamp} "
            + json.dumps(item, sort_keys=True, separators=(",", ":"))
        )
    lines.sort(key=lambda line: line.encode("utf-8"))
    output = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    return gzip.compress(output, mtime=0) if compressed else output


def _rewrite_cdxj_for_replay(payload: bytes, *, compressed: bool) -> bytes:
    return _cdxj_payload_from_entries(_cdxj_entries_from_payload(payload, compressed=compressed), compressed=compressed)


def _timestamp14_from_warc_date(value: str) -> str:
    return re.sub(r"[^0-9]", "", value)[:14].ljust(14, "0")


def _replayweb_page_repack_warc_gzip(
    *,
    warc_payload: bytes,
    original_name: str,
    output_name: str,
    cdx_entries: Sequence[tuple[str, Mapping[str, Any]]],
) -> tuple[bytes, list[tuple[str, dict[str, Any]]]]:
    try:
        from warcio.archiveiterator import ArchiveIterator
        from warcio.statusandheaders import StatusAndHeaders
        from warcio.warcwriter import WARCWriter
    except Exception as error:  # pragma: no cover - exercised in user venv where warcio is available
        raise RuntimeError(f"warcio unavailable for ReplayWeb.page WARC gzip repack: {error}") from error

    by_url: dict[str, deque[tuple[str, dict[str, Any]]]] = defaultdict(deque)
    for timestamp, row in cdx_entries:
        if str(row.get("filename") or "") == original_name:
            by_url[str(row.get("url") or "")].append((timestamp, dict(row)))

    output = BytesIO()
    writer = WARCWriter(output, gzip=True)
    rewritten_entries: list[tuple[str, dict[str, Any]]] = []
    for record in ArchiveIterator(BytesIO(warc_payload)):
        target_url = str(record.rec_headers.get_header("WARC-Target-URI") or "")
        start = output.tell()
        if record.rec_type == "request":
            # Older generated MSN WARC request records can contain the malformed
            # request line `HTTP/1.1 GET /path HTTP/1.1`. ReplayWeb imports those
            # as synthetic `_wb_method=HTTP/1.1` resources, which leaves browser
            # replay unable to resolve the matching page even when the response
            # record is present. Rebuild request records with the method in the
            # StatusAndHeaders protocol slot so the stored request line is
            # `GET /path HTTP/1.1`. Response records are not modified here.
            request_headers = StatusAndHeaders(
                f"{_warc_request_path(target_url)} HTTP/1.1",
                list(record.http_headers.headers)
                if record.http_headers
                else [("Host", urlsplit(target_url).netloc)],
                protocol="GET",
            )
            writer.write_record(
                writer.create_warc_record(
                    target_url,
                    "request",
                    payload=BytesIO(b""),
                    http_headers=request_headers,
                    warc_headers_dict={"WARC-Date": str(record.rec_headers.get_header("WARC-Date") or "")},
                )
            )
        else:
            writer.write_record(record)
        length = output.tell() - start
        if record.rec_type != "response":
            continue
        if by_url[target_url]:
            timestamp, row = by_url[target_url].popleft()
        else:
            timestamp = _timestamp14_from_warc_date(str(record.rec_headers.get_header("WARC-Date") or ""))
            row = {
                "digest": str(record.rec_headers.get_header("WARC-Payload-Digest") or ""),
                "mime": str(record.http_headers.get_header("Content-Type") if record.http_headers else "")
                or "application/octet-stream",
                "status": int(record.http_headers.get_statuscode() if record.http_headers else 0),
                "url": target_url,
            }
        row["filename"] = _cdxj_filename_for_wacz(output_name)
        row["offset"] = start
        row["length"] = length
        row["url"] = str(row.get("url") or target_url)
        rewritten_entries.append((timestamp, row))

    missing = [(timestamp, row) for rows in by_url.values() for timestamp, row in rows]
    if missing:
        missing_urls = ", ".join(sorted(str(row.get("url") or "") for _timestamp, row in missing)[:5])
        raise ValueError("Could not map CDXJ response rows into gzipped WARC member: " + missing_urls)
    return output.getvalue(), rewritten_entries


def _rewrite_pages_jsonl_for_replay(payload: bytes) -> bytes:
    output: list[str] = []
    for line in payload.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, Mapping) and row.get("url"):
            row = dict(row)
            row["url"] = _fragmentless_url(str(row.get("url") or ""))
        output.append(json.dumps(row, sort_keys=True, separators=(",", ":")))
    return ("\n".join(output) + ("\n" if output else "")).encode("utf-8")


def _pages_rows_from_payload(payload: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in payload.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return rows


def _pages_payload_with_static_evidence(
    payload: bytes,
    *,
    static_url: str,
    title: str,
    timestamp_utc: str,
) -> bytes:
    rows = _pages_rows_from_payload(_rewrite_pages_jsonl_for_replay(payload))
    output: list[dict[str, Any]] = []
    header = rows[0] if rows and rows[0].get("format") else {"format": "json-pages-1.0", "id": "pages", "title": "All Pages"}
    output.append(dict(header))
    output.append(
        {
            "derived": True,
            "replay_runtime_status": REPLAYWEB_RUNTIME_PARTIAL_RENDER,
            "source": "source_evidence_static_replay_fallback",
            "title": title or "Static evidence view",
            "ts": timestamp_utc,
            "url": static_url,
        }
    )
    for row in rows[1:] if rows and rows[0].get("format") else rows:
        if str(row.get("url") or "") == static_url:
            continue
        output.append(dict(row))
    return ("\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in output) + "\n").encode(
        "utf-8"
    )


def _comments_evidence_from_verification(
    verification: LocalWebArchiveVerificationResult,
) -> StaticReplayCommentsEvidence | None:
    if (
        not verification.comments_evidence_status
        or verification.comments_evidence_status == "not_checked"
        or not any(
            (
                verification.comments_json_count,
                verification.comments_jsonl_count,
                verification.declared_comment_count,
                verification.top_level_comment_count,
                verification.reply_count,
            )
        )
    ):
        return None
    return StaticReplayCommentsEvidence(
        status=verification.comments_evidence_status,
        comments_json_count=verification.comments_json_count,
        comments_jsonl_count=verification.comments_jsonl_count,
        declared_comment_count=verification.declared_comment_count,
        top_level_comment_count=verification.top_level_comment_count,
        reply_count=verification.reply_count,
        comments_complete=verification.comments_complete,
        faithful_comments_screenshot_name=verification.faithful_comments_screenshot_name,
        faithful_comments_screenshot_sha256=verification.faithful_comments_screenshot_sha256,
        derived_comments_visual_name=verification.derived_comments_visual_name,
        derived_comments_visual_sha256=verification.derived_comments_visual_sha256,
    )


def _static_evidence_warc_gzip(
    *,
    static_url: str,
    html_payload: bytes,
    timestamp_utc: str,
    output_name: str,
) -> tuple[bytes, tuple[str, dict[str, Any]]]:
    try:
        from warcio.statusandheaders import StatusAndHeaders
        from warcio.warcwriter import WARCWriter
    except Exception as error:  # pragma: no cover - exercised in user venv where warcio is available
        raise RuntimeError(f"warcio unavailable for static evidence WARC generation: {error}") from error

    output = BytesIO()
    writer = WARCWriter(output, gzip=True)
    request_headers = StatusAndHeaders(
        f"{_warc_request_path(static_url)} HTTP/1.1",
        [("Host", urlsplit(static_url).netloc)],
        protocol="GET",
    )
    writer.write_record(
        writer.create_warc_record(
            static_url,
            "request",
            payload=BytesIO(b""),
            http_headers=request_headers,
            warc_headers_dict={"WARC-Date": timestamp_utc},
        )
    )
    response_headers = StatusAndHeaders(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(html_payload))),
        ],
        protocol="HTTP/1.1",
    )
    start = output.tell()
    response_record = writer.create_warc_record(
        static_url,
        "response",
        payload=BytesIO(html_payload),
        http_headers=response_headers,
        warc_headers_dict={"WARC-Date": timestamp_utc},
    )
    writer.write_record(response_record)
    length = output.tell() - start
    timestamp = _timestamp14_from_warc_date(timestamp_utc)
    row = {
        "digest": str(response_record.rec_headers.get_header("WARC-Payload-Digest") or ""),
        "filename": _cdxj_filename_for_wacz(output_name),
        "length": length,
        "mime": "text/html",
        "offset": start,
        "status": 200,
        "url": static_url,
    }
    return output.getvalue(), (timestamp, row)


def build_static_replay_evidence_input_for_wacz(
    wacz_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    expected_source_url: str = "",
    expected_comment_count: int = 0,
    static_evidence_url: str = "",
    static_evidence_title: str = "",
    static_evidence_capture_timestamp: str = "",
    static_evidence_runtime_notes: Sequence[str] = (),
) -> StaticReplayEvidenceInput:
    source = Path(wacz_path)
    input_sha = _sha256_file(source)
    with zipfile.ZipFile(source, "r") as bundle:
        names = bundle.namelist()
        datapackage = _safe_json_loads(bundle.read("datapackage.json")) if "datapackage.json" in names else {}
        package = dict(datapackage) if isinstance(datapackage, Mapping) else {}
        home = package.get("home")
        home_url = str(home.get("url") or "") if isinstance(home, Mapping) else ""
        legacy_home = str(package.get("mainPageUrl") or "")
        page_rows = (
            _pages_rows_from_payload(bundle.read("pages/pages.jsonl"))
            if "pages/pages.jsonl" in names
            else []
        )
    first_page = next((row for row in page_rows if row.get("url")), {})
    static_source_url = _fragmentless_url(expected_source_url or home_url or legacy_home or str(first_page.get("url") or ""))
    if not static_source_url:
        raise ValueError("Static evidence output requires a source URL from metadata or --expected-source-url")
    timestamp_utc = (
        static_evidence_capture_timestamp
        or str(first_page.get("ts") or "")
        or str(package.get("created") or "")
        or "2026-08-09T00:00:00Z"
    )
    title = static_evidence_title or str(first_page.get("title") or "") or "Static evidence view"
    runtime_notes = tuple(static_evidence_runtime_notes)
    if not runtime_notes and "msn.com" in static_source_url.lower():
        runtime_notes = (
            "Normalized WACZ manual ReplayWeb result: article entry click returned Archived Page Not Found.",
            "Normalized WACZ manual ReplayWeb result: article URL without #comments returned Archived Page Not Found.",
            "Normalized WACZ manual ReplayWeb result: comments visible: no.",
            "Normalized raw WARC manual ReplayWeb result: _wb_method=HTTP/1.1 symptom absent, but page only partially rendered.",
            "Normalized raw WARC manual ReplayWeb result: privacy modal, black/empty page area, severe browser lag, and comments visible: no.",
        )
    elif not runtime_notes:
        runtime_notes = DEFAULT_REPLAY_RUNTIME_LIMITATION_NOTES
    source_verification = verify_local_web_archive_package(
        source,
        manifest_path=manifest_path,
        expected_source_url=static_source_url,
        expected_comment_count=expected_comment_count,
        allow_replayweb_page_legacy_profile=True,
    )
    return StaticReplayEvidenceInput(
        source_url=static_source_url,
        title=title,
        capture_timestamp=timestamp_utc,
        original_wacz_sha256=input_sha,
        normalized_wacz_sha256="not applicable for standalone static output",
        warc_record_count=source_verification.warc_record_count,
        replay_runtime_status=REPLAYWEB_RUNTIME_PARTIAL_RENDER,
        replay_runtime_notes=runtime_notes,
        comments_evidence=_comments_evidence_from_verification(source_verification),
        static_url=static_evidence_url or build_static_evidence_url(static_source_url, site_hint="msn"),
    )


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(payload), indent=2, sort_keys=True) + "\n").encode("utf-8")


def repair_local_web_archive_wacz(
    wacz_path: str | Path,
    *,
    output_path: str | Path | None = None,
    compatibility_profile: str = WACZ_12_COMPATIBILITY_PROFILE,
    add_static_evidence_page: bool = False,
    static_evidence_url: str = "",
    static_evidence_source_url: str = "",
    static_evidence_title: str = "",
    static_evidence_capture_timestamp: str = "",
    static_evidence_runtime_notes: Sequence[str] = (),
    manifest_path: str | Path | None = None,
    expected_comment_count: int = 0,
) -> LocalWebArchiveRepairResult:
    source = Path(wacz_path)
    destination = Path(output_path) if output_path else source.with_name(source.stem + ".replayweb-fixed.wacz")
    if compatibility_profile not in {WACZ_12_COMPATIBILITY_PROFILE, REPLAYWEB_PAGE_COMPATIBILITY_PROFILE}:
        return LocalWebArchiveRepairResult(
            status=REPLAY_FAILED,
            input_name=source.name,
            output_name=destination.name,
            errors=(
                "Unsupported compatibility profile: "
                + compatibility_profile
                + "; expected wacz12 or replayweb-page",
            ),
        )
    if not source.is_file():
        return LocalWebArchiveRepairResult(
            status=REPLAY_FAILED,
            input_name=source.name,
            output_name=destination.name,
            errors=(f"Input WACZ does not exist: {source}",),
        )
    if source.resolve() == destination.resolve():
        return LocalWebArchiveRepairResult(
            status=REPLAY_FAILED,
            input_name=source.name,
            output_name=destination.name,
            input_sha256=_sha256_file(source),
            errors=("Repair output must be a different file so the original archive is preserved.",),
        )
    if destination.exists():
        return LocalWebArchiveRepairResult(
            status=REPLAY_FAILED,
            input_name=source.name,
            output_name=destination.name,
            input_sha256=_sha256_file(source),
            errors=(f"Repair output already exists and will not be overwritten: {destination}",),
        )

    input_sha = _sha256_file(source)
    removed: list[str] = []
    rewritten_indexes = 0
    removed_payload_names: set[str] = set()
    static_status = ""
    static_page_url = ""
    replay_runtime_status = ""
    replay_runtime_notes: tuple[str, ...] = ()
    try:
        with zipfile.ZipFile(source, "r") as bundle:
            names = bundle.namelist()
            if "datapackage.json" not in names:
                raise ValueError("datapackage.json is missing")
            datapackage = _safe_json_loads(bundle.read("datapackage.json"))
            if not isinstance(datapackage, Mapping):
                raise ValueError("datapackage.json is not an object")
            package = dict(datapackage)
            legacy_home = str(package.get("mainPageUrl") or "")
            home = package.get("home")
            home_url = ""
            if isinstance(home, Mapping):
                home_url = str(home.get("url") or "")
            canonical_home_url = _fragmentless_url(home_url or legacy_home)
            page_rows = (
                _pages_rows_from_payload(bundle.read("pages/pages.jsonl"))
                if "pages/pages.jsonl" in names
                else []
            )
            first_page = next((row for row in page_rows if row.get("url")), {})
            page_title = str(first_page.get("title") or "")
            page_timestamp = str(first_page.get("ts") or "")

            if compatibility_profile == WACZ_12_COMPATIBILITY_PROFILE:
                for field_name in ("wacz_version", "mainPageUrl", "mainPageDate"):
                    if field_name in package:
                        removed.append(field_name)
                        package.pop(field_name, None)
                package["profile"] = "wacz"
            else:
                # The published WACZ 1.2.0 profile is `wacz`, but the currently hosted
                # ReplayWeb.page browser app observed in manual smoke testing rejects that
                # profile with "Unknown package profile: wacz". For operational replay, keep
                # the legacy data-package profile ReplayWeb.page accepts while still fixing
                # the material replay defects: fragmentless page metadata and sorted,
                # canonical CDXJ lookup keys.
                if "mainPageDate" in package:
                    removed.append("mainPageDate")
                    package.pop("mainPageDate", None)
                package["profile"] = "data-package"
                package["wacz_version"] = str(package.get("wacz_version") or "1.2.0")
                package["mainPageUrl"] = canonical_home_url

            home = package.get("home")
            if isinstance(home, Mapping):
                fixed_home = dict(home)
                fixed_home["url"] = canonical_home_url or _fragmentless_url(str(fixed_home.get("url") or legacy_home))
                package["home"] = fixed_home
            elif canonical_home_url:
                package["home"] = {"url": canonical_home_url, "ts": str(package.get("created") or "")}

            rewritten_payloads: dict[str, bytes] = {}
            if "pages/pages.jsonl" in names:
                rewritten_payloads["pages/pages.jsonl"] = _rewrite_pages_jsonl_for_replay(
                    bundle.read("pages/pages.jsonl")
                )
            else:
                rewritten_payloads["pages/pages.jsonl"] = b'{"format":"json-pages-1.0","id":"pages","title":"All Pages"}\n'

            index_entries_by_name: dict[str, list[tuple[str, dict[str, Any]]]] = {}
            for name in names:
                if not name.startswith("indexes/"):
                    continue
                if name.endswith(".cdx.gz"):
                    index_entries_by_name[name] = _cdxj_entries_from_payload(bundle.read(name), compressed=True)
                elif name.endswith((".cdx", ".cdxj")):
                    index_entries_by_name[name] = _cdxj_entries_from_payload(bundle.read(name), compressed=False)

            if compatibility_profile == REPLAYWEB_PAGE_COMPATIBILITY_PROFILE:
                # Manual ReplayWeb.page smoke showed that profile/data-package compatibility is not enough:
                # the hosted browser app lists pages but still returns "Archived Page Not Found" when the
                # archived WARC member is stored as plain archive/data.warc. Repack uncompressed WARC
                # members into per-record gzip WARC members and rewrite CDXJ offsets to those compressed
                # members, matching the ArchiveWeb.page-style WACZ shape ReplayWeb.page random-accesses.
                all_entries: list[tuple[str, dict[str, Any]]] = []
                for entries in index_entries_by_name.values():
                    all_entries.extend((timestamp, dict(row)) for timestamp, row in entries)
                converted_filenames: set[str] = set()
                converted_entries: list[tuple[str, dict[str, Any]]] = []
                for archive_name in sorted(
                    name for name in names if name.startswith("archive/") and name.endswith(".warc")
                ):
                    gz_name = archive_name + ".gz"
                    gz_payload, gz_entries = _replayweb_page_repack_warc_gzip(
                        warc_payload=bundle.read(archive_name),
                        original_name=archive_name,
                        output_name=gz_name,
                        cdx_entries=all_entries,
                    )
                    rewritten_payloads[gz_name] = gz_payload
                    removed_payload_names.add(archive_name)
                    converted_filenames.add(archive_name)
                    converted_entries.extend(gz_entries)

                if converted_filenames:
                    replacement_entries = converted_entries + [
                        (timestamp, dict(row))
                        for timestamp, row in all_entries
                        if str(row.get("filename") or "") not in converted_filenames
                    ]
                    for name in index_entries_by_name or {"indexes/index.cdx.gz": []}:
                        rewritten_payloads[name] = _cdxj_payload_from_entries(
                            replacement_entries, compressed=name.endswith(".gz")
                        )
                        rewritten_indexes += 1
                else:
                    for name, entries in index_entries_by_name.items():
                        compressed = name.endswith(".gz")
                        rewritten_payloads[name] = _cdxj_payload_from_entries(entries, compressed=compressed)
                        rewritten_indexes += 1
            else:
                for name, entries in index_entries_by_name.items():
                    compressed = name.endswith(".gz")
                    rewritten_payloads[name] = _cdxj_payload_from_entries(entries, compressed=compressed)
                    rewritten_indexes += 1

            if add_static_evidence_page:
                static_source_url = _fragmentless_url(
                    static_evidence_source_url or canonical_home_url or str(first_page.get("url") or "")
                )
                if not static_source_url:
                    raise ValueError("Static evidence page requires a source URL from metadata or --expected-source-url")
                static_page_url = static_evidence_url or build_static_evidence_url(static_source_url, site_hint="msn")
                timestamp_utc = (
                    static_evidence_capture_timestamp
                    or page_timestamp
                    or str(package.get("created") or "")
                    or "2026-08-09T00:00:00Z"
                )
                source_verification = verify_local_web_archive_package(
                    source,
                    manifest_path=manifest_path,
                    expected_source_url=static_source_url,
                    expected_comment_count=expected_comment_count,
                    allow_replayweb_page_legacy_profile=True,
                )
                replay_runtime_notes = tuple(static_evidence_runtime_notes)
                if not replay_runtime_notes and "msn.com" in static_source_url.lower():
                    replay_runtime_notes = (
                        "Normalized WACZ manual ReplayWeb result: article entry click returned Archived Page Not Found.",
                        "Normalized WACZ manual ReplayWeb result: article URL without #comments returned Archived Page Not Found.",
                        "Normalized WACZ manual ReplayWeb result: comments visible: no.",
                        "Normalized raw WARC manual ReplayWeb result: _wb_method=HTTP/1.1 symptom absent, but page only partially rendered.",
                        "Normalized raw WARC manual ReplayWeb result: privacy modal, black/empty page area, severe browser lag, and comments visible: no.",
                    )
                elif not replay_runtime_notes:
                    replay_runtime_notes = DEFAULT_REPLAY_RUNTIME_LIMITATION_NOTES
                replay_runtime_status = REPLAYWEB_RUNTIME_PARTIAL_RENDER
                static_page = build_static_replay_evidence_page(
                    StaticReplayEvidenceInput(
                        source_url=static_source_url,
                        title=static_evidence_title or page_title or "Static evidence view",
                        capture_timestamp=timestamp_utc,
                        original_wacz_sha256=input_sha,
                        normalized_wacz_sha256="computed after derived WACZ write; see repair JSON output",
                        warc_record_count=source_verification.warc_record_count,
                        replay_runtime_status=replay_runtime_status,
                        replay_runtime_notes=replay_runtime_notes,
                        comments_evidence=_comments_evidence_from_verification(source_verification),
                        static_url=static_page_url,
                    )
                )
                if static_page.status != STATIC_EVIDENCE_VIEW_READY:
                    raise ValueError("Static evidence page validation failed: " + "; ".join(static_page.errors))
                static_archive_name = "archive/source-evidence-static.warc.gz"
                static_warc, static_cdx_entry = _static_evidence_warc_gzip(
                    static_url=static_page.static_url,
                    html_payload=static_page.html.encode("utf-8"),
                    timestamp_utc=timestamp_utc,
                    output_name=static_archive_name,
                )
                rewritten_payloads[static_archive_name] = static_warc
                static_status = static_page.status
                pages_payload = rewritten_payloads.get("pages/pages.jsonl", b"")
                rewritten_payloads["pages/pages.jsonl"] = _pages_payload_with_static_evidence(
                    pages_payload,
                    static_url=static_page.static_url,
                    title=static_evidence_title or page_title or "Static evidence view",
                    timestamp_utc=timestamp_utc,
                )
                if index_entries_by_name:
                    for name in tuple(index_entries_by_name):
                        existing_entries = _cdxj_entries_from_payload(
                            rewritten_payloads.get(name, bundle.read(name)),
                            compressed=name.endswith(".gz"),
                        )
                        rewritten_payloads[name] = _cdxj_payload_from_entries(
                            existing_entries + [static_cdx_entry],
                            compressed=name.endswith(".gz"),
                        )
                    rewritten_indexes = max(rewritten_indexes, len(index_entries_by_name))
                else:
                    rewritten_payloads["indexes/index.cdx.gz"] = _cdxj_payload_from_entries(
                        [static_cdx_entry],
                        compressed=True,
                    )
                    rewritten_indexes += 1

            resources = []
            seen_resource_paths: set[str] = set()
            for resource in package.get("resources") or ():
                if not isinstance(resource, Mapping):
                    resources.append(resource)
                    continue
                item = dict(resource)
                resource_path = str(item.get("path") or "")
                if resource_path in removed_payload_names:
                    continue
                if resource_path in rewritten_payloads:
                    payload = rewritten_payloads[resource_path]
                    item["bytes"] = len(payload)
                    item["hash"] = "sha256:" + hashlib.sha256(payload).hexdigest()
                resources.append(item)
                seen_resource_paths.add(resource_path)
            for resource_path, payload in sorted(rewritten_payloads.items()):
                if resource_path in seen_resource_paths or resource_path.startswith("indexes/") or resource_path.startswith("pages/"):
                    continue
                resources.append(
                    {
                        "bytes": len(payload),
                        "hash": "sha256:" + hashlib.sha256(payload).hexdigest(),
                        "name": Path(resource_path).name,
                        "path": resource_path,
                    }
                )
            package["resources"] = resources
            datapackage_bytes = _json_bytes(package)
            digest_bytes = _json_bytes(
                {"hash": "sha256:" + hashlib.sha256(datapackage_bytes).hexdigest(), "path": "datapackage.json"}
            )

            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                prefix=destination.name + ".",
                suffix=".part",
                dir=destination.parent,
                delete=False,
            ) as temp_handle:
                temp_destination = Path(temp_handle.name)
            try:
                with zipfile.ZipFile(temp_destination, "w") as output:
                    for name in names:
                        if (
                            name in {"datapackage.json", "datapackage-digest.json"}
                            or name in rewritten_payloads
                            or name in removed_payload_names
                        ):
                            continue
                        payload = bundle.read(name)
                        info = zipfile.ZipInfo(name)
                        info.date_time = (2026, 1, 1, 0, 0, 0)
                        info.compress_type = (
                            zipfile.ZIP_STORED
                            if name.startswith("archive/") or name.endswith(".gz")
                            else zipfile.ZIP_DEFLATED
                        )
                        output.writestr(info, payload)
                    for name, payload in sorted(rewritten_payloads.items()):
                        info = zipfile.ZipInfo(name)
                        info.date_time = (2026, 1, 1, 0, 0, 0)
                        info.compress_type = zipfile.ZIP_STORED if name.endswith(".gz") else zipfile.ZIP_DEFLATED
                        output.writestr(info, payload)
                    for name, payload in (
                        ("datapackage.json", datapackage_bytes),
                        ("datapackage-digest.json", digest_bytes),
                    ):
                        info = zipfile.ZipInfo(name)
                        info.date_time = (2026, 1, 1, 0, 0, 0)
                        info.compress_type = zipfile.ZIP_DEFLATED
                        output.writestr(info, payload)

                temp_verification = verify_local_web_archive_package(
                    temp_destination,
                    allow_replayweb_page_legacy_profile=(
                        compatibility_profile == REPLAYWEB_PAGE_COMPATIBILITY_PROFILE
                    ),
                )
                if temp_verification.status not in {STRUCTURAL_WACZ_VALID, REPLAYWEB_PAGE_COMPATIBLE, REPLAYWEB_PAGE_PACKAGE_READY}:
                    raise ValueError(
                        "Repaired WACZ failed verification: "
                        + "; ".join(temp_verification.errors or (temp_verification.status,))
                    )
                if destination.exists():
                    raise FileExistsError(
                        f"Repair output appeared during repair and will not be overwritten: {destination}"
                    )
                temp_destination.replace(destination)
            finally:
                if temp_destination.exists():
                    temp_destination.unlink()
    except Exception as error:
        return LocalWebArchiveRepairResult(
            status=REPLAY_FAILED,
            input_name=source.name,
            output_name=destination.name,
            input_sha256=input_sha,
            errors=(str(error),),
        )

    verification = verify_local_web_archive_package(
        destination,
        allow_replayweb_page_legacy_profile=(compatibility_profile == REPLAYWEB_PAGE_COMPATIBILITY_PROFILE),
    )
    status = (
        WACZ_REPLAY_COMPATIBILITY_REPAIRED
        if verification.status in {STRUCTURAL_WACZ_VALID, REPLAYWEB_PAGE_COMPATIBLE, REPLAYWEB_PAGE_PACKAGE_READY}
        else REPLAY_FAILED
    )
    return LocalWebArchiveRepairResult(
        status=status,
        input_name=source.name,
        output_name=destination.name,
        input_sha256=input_sha,
        output_sha256=_sha256_file(destination),
        output_size_bytes=destination.stat().st_size,
        rewritten_index_count=rewritten_indexes,
        removed_legacy_fields=tuple(sorted(removed)),
        verification_status=verification.status,
        verification_statuses=tuple(
            item for item in (verification.status, static_status) if item
        ),
        static_evidence_status=static_status,
        static_evidence_page_url=static_page_url,
        replay_runtime_status=replay_runtime_status,
        replay_runtime_notes=replay_runtime_notes,
        original_preserved=True,
        errors=verification.errors,
    )


def verify_local_web_archive_package(
    wacz_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    expected_source_url: str = "",
    expected_wacz_sha256: str = "",
    expected_manifest_sha256: str = "",
    expected_comment_count: int = 0,
    allow_replayweb_page_legacy_profile: bool = False,
) -> LocalWebArchiveVerificationResult:
    package = Path(wacz_path)
    errors: list[str] = []
    warnings: list[str] = []
    manifest_name = Path(manifest_path).name if manifest_path else ""
    manifest_sha256 = ""
    comments_summary: dict[str, Any] = {}
    if not package.is_file():
        return LocalWebArchiveVerificationResult(
            status=REPLAY_FAILED,
            wacz_name=package.name,
            manifest_name=manifest_name,
            errors=(f"WACZ file does not exist: {package}",),
        )

    wacz_sha = _sha256_file(package)
    if expected_wacz_sha256 and wacz_sha.lower() != expected_wacz_sha256.lower():
        errors.append("WACZ SHA-256 does not match expected value")
    if manifest_path:
        manifest_file = Path(manifest_path)
        if manifest_file.is_file():
            manifest_sha256 = _sha256_file(manifest_file)
            if expected_manifest_sha256 and manifest_sha256.lower() != expected_manifest_sha256.lower():
                errors.append("Manifest SHA-256 does not match expected value")
            try:
                manifest_payload = _load_json_file(manifest_file)
                if isinstance(manifest_payload, Mapping):
                    comments_summary = _manifest_comments_summary(
                        manifest_payload,
                        expected_comment_count=expected_comment_count,
                    )
            except Exception as error:
                errors.append(f"Manifest parse failed: {error}")
        else:
            errors.append(f"Manifest file does not exist: {manifest_file}")

    names: set[str] = set()
    datapackage: Mapping[str, Any] = {}
    pages: list[Mapping[str, Any]] = []
    index_lines: list[str] = []
    warc_record_count = 0
    archive_warc_gzip_member_count = 0
    index_sorted = False
    index_search_keys_canonical = False
    deprecated_fields: tuple[str, ...] = ()
    try:
        with zipfile.ZipFile(package, "r") as bundle:
            bad_member = bundle.testzip()
            if bad_member:
                errors.append(f"ZIP integrity failed at {bad_member}")
            names = set(bundle.namelist())
            if "datapackage.json" in names:
                datapackage_raw = _safe_json_loads(bundle.read("datapackage.json"))
                if isinstance(datapackage_raw, Mapping):
                    datapackage = datapackage_raw
            if "pages/pages.jsonl" in names:
                pages = _parse_pages_jsonl(bundle.read("pages/pages.jsonl"))
            if "indexes/index.cdx.gz" in names:
                index_lines = [
                    line
                    for line in gzip.decompress(bundle.read("indexes/index.cdx.gz"))
                    .decode("utf-8", errors="replace")
                    .splitlines()
                    if line.strip()
                ]
                index_sorted = index_lines == sorted(index_lines, key=lambda line: line.encode("utf-8"))
                canonical_rows = True
                for line in index_lines:
                    try:
                        searchable, _timestamp, row = _parse_cdxj_line(line)
                        if searchable != _cdxj_searchable_url(str(row.get("url") or "")):
                            canonical_rows = False
                            break
                    except Exception as error:
                        canonical_rows = False
                        warnings.append(f"CDXJ parse warning: {error}")
                        break
                index_search_keys_canonical = canonical_rows
            warc_names = sorted(
                name for name in names if name.startswith("archive/") and name.endswith((".warc", ".warc.gz"))
            )
            archive_warc_gzip_member_count = sum(1 for name in warc_names if name.endswith(".warc.gz"))
            warc_record_count, warc_errors = _warc_record_count_from_zip(bundle, warc_names)
            warnings.extend(warc_errors)
    except Exception as error:
        errors.append(f"WACZ ZIP/read failed: {error}")

    missing = tuple(sorted(REQUIRED_WACZ_ENTRIES - names))
    if not any(name.startswith("archive/") and name.endswith((".warc", ".warc.gz")) for name in names):
        missing = tuple(sorted(set(missing) | {"archive/*.warc[.gz]"}))
    if missing:
        errors.append("Required WACZ entries are missing")

    datapackage_profile = str(datapackage.get("profile") or "")
    legacy_version = str(datapackage.get("wacz_version") or "")
    deprecated_fields = tuple(
        name for name in ("wacz_version", "mainPageUrl", "mainPageDate") if name in datapackage
    )
    replayweb_page_legacy_profile = bool(
        allow_replayweb_page_legacy_profile
        and datapackage_profile == "data-package"
        and str(datapackage.get("wacz_version") or "")
    )
    if datapackage and datapackage_profile != "wacz" and not replayweb_page_legacy_profile:
        errors.append("WACZ 1.2.0 requires datapackage profile 'wacz'")
    if deprecated_fields and not replayweb_page_legacy_profile:
        errors.append("WACZ 1.2.0 datapackage contains removed legacy fields: " + ", ".join(deprecated_fields))
    if index_lines and not index_sorted:
        errors.append("CDXJ index is not byte-wise sorted for binary-search replay lookup")
    if index_lines and not index_search_keys_canonical:
        errors.append("CDXJ searchable URL keys are not canonical lower-case lookup keys")
    if replayweb_page_legacy_profile and archive_warc_gzip_member_count <= 0:
        errors.append("ReplayWeb.page-compatible WACZ requires archive/*.warc.gz random-access members")

    source_candidates = {
        str(((datapackage.get("home") or {}) if isinstance(datapackage.get("home"), Mapping) else {}).get("url") or ""),
    }
    source_candidates.update(str(page.get("url") or "") for page in pages)
    for line in index_lines:
        try:
            _searchable, _timestamp, row = _parse_cdxj_line(line)
            source_candidates.add(str(row.get("url") or ""))
        except Exception:
            source_candidates.add(line)
    expected_found = True
    if expected_source_url:
        expected_fragmentless = _fragmentless_url(expected_source_url)
        expected_found = any(
            _fragmentless_url(candidate) == expected_fragmentless or expected_fragmentless in candidate
            for candidate in source_candidates
            if candidate
        )
        if not expected_found:
            errors.append("Expected source URL was not found in WACZ metadata/index")

    profile_lookup_ready = bool(
        (datapackage_profile == "wacz" and not deprecated_fields) or replayweb_page_legacy_profile
    )
    replay_lookup_ready = bool(
        profile_lookup_ready
        and (not index_lines or (index_sorted and index_search_keys_canonical))
        and not missing
        and (not replayweb_page_legacy_profile or archive_warc_gzip_member_count > 0)
    )
    status = REPLAY_FAILED
    if not errors:
        status = REPLAYWEB_PAGE_PACKAGE_READY if replayweb_page_legacy_profile else STRUCTURAL_WACZ_VALID
    return LocalWebArchiveVerificationResult(
        status=status,
        wacz_name=package.name,
        wacz_sha256=wacz_sha,
        wacz_size_bytes=package.stat().st_size,
        manifest_name=manifest_name,
        manifest_sha256=manifest_sha256,
        zip_integrity_ok=not any("ZIP integrity" in error for error in errors),
        required_entries_present=not missing,
        missing_required_entries=missing,
        datapackage_profile=datapackage_profile,
        wacz_version=legacy_version,
        wacz_spec_target="1.2.0",
        legacy_declared_wacz_version=legacy_version,
        deprecated_datapackage_fields=deprecated_fields,
        index_sorted=index_sorted,
        index_search_keys_canonical=index_search_keys_canonical,
        replay_lookup_ready=replay_lookup_ready,
        page_count=len(pages),
        index_line_count=len(index_lines),
        warc_record_count=warc_record_count,
        expected_source_url_found=expected_found,
        replayweb_acceptance_basis=(
            "ReplayWeb.page browser-app legacy data-package profile + WACZ package/index readiness; manual browser replay still required"
            if replayweb_page_legacy_profile
            else "WACZ 1.2.0 structure + CDXJ replay lookup verification"
        ),
        comments_json_count=int(comments_summary.get("comments_json_count") or 0),
        comments_jsonl_count=int(comments_summary.get("comments_jsonl_count") or 0),
        declared_comment_count=int(comments_summary.get("declared_comment_count") or 0),
        top_level_comment_count=int(comments_summary.get("top_level_comment_count") or 0),
        reply_count=int(comments_summary.get("reply_count") or 0),
        comments_complete=bool(comments_summary.get("comments_complete")),
        comments_evidence_status=str(comments_summary.get("comments_evidence_status") or "not_checked"),
        faithful_comments_screenshot_name=str(comments_summary.get("faithful_comments_screenshot_name") or ""),
        faithful_comments_screenshot_sha256=str(comments_summary.get("faithful_comments_screenshot_sha256") or ""),
        derived_comments_visual_name=str(comments_summary.get("derived_comments_visual_name") or ""),
        derived_comments_visual_sha256=str(comments_summary.get("derived_comments_visual_sha256") or ""),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_replaywebpage_open_preview(
    wacz_path: str | Path,
    *,
    viewer: ReplayWebViewerDetection | None = None,
) -> LocalWebArchiveCommandPreview:
    detection = viewer or detect_replaywebpage_viewer()
    if detection.status != VIEWER_CONFIGURED or not detection.executable_path:
        return LocalWebArchiveCommandPreview(
            status=VIEWER_NOT_CONFIGURED,
            message=detection.configuration_help,
        )
    return LocalWebArchiveCommandPreview(
        status=OPEN_ARCHIVE_PREVIEWED,
        argv=(detection.executable_path, str(Path(wacz_path))),
        shell=False,
        message="ReplayWeb.page desktop launch preview uses subprocess argument array.",
    )


def open_archive_with_replaywebpage(
    wacz_path: str | Path,
    *,
    viewer: ReplayWebViewerDetection | None = None,
    launcher: Callable[[Sequence[str]], Any] | None = None,
) -> LocalWebArchiveCommandPreview:
    preview = build_replaywebpage_open_preview(wacz_path, viewer=viewer)
    if preview.status != OPEN_ARCHIVE_PREVIEWED:
        return preview
    if launcher is None:
        launcher = lambda argv: subprocess.Popen(list(argv), shell=False)  # noqa: S603
    launcher(preview.argv)
    return LocalWebArchiveCommandPreview(
        status=REPLAY_OPENED,
        argv=preview.argv,
        shell=False,
        executed=True,
        message="ReplayWeb.page desktop viewer launch requested.",
    )


def build_show_local_web_archive_files_preview(wacz_path: str | Path) -> LocalWebArchiveCommandPreview:
    package = Path(wacz_path)
    if os.name == "nt":
        argv = ("explorer.exe", f"/select,{package}")
    else:
        argv = ("xdg-open", str(package.parent))
    return LocalWebArchiveCommandPreview(
        status=SHOW_FILES_READY if package.exists() else REPLAY_FAILED,
        argv=argv,
        shell=False,
        message="Show files command preview selects the WACZ or opens its containing directory.",
    )


def show_local_web_archive_files(
    wacz_path: str | Path,
    *,
    launcher: Callable[[Sequence[str]], Any] | None = None,
) -> LocalWebArchiveCommandPreview:
    preview = build_show_local_web_archive_files_preview(wacz_path)
    if preview.status != SHOW_FILES_READY:
        return preview
    if launcher is None:
        launcher = lambda argv: subprocess.Popen(list(argv), shell=False)  # noqa: S603
    launcher(preview.argv)
    return LocalWebArchiveCommandPreview(
        status=SHOW_FILES_PREVIEWED,
        argv=preview.argv,
        shell=False,
        executed=True,
        message="Local Web Archive file-manager launch requested.",
    )


def build_replayweb_browser_pwa_file_state(wacz_path: str | Path) -> dict[str, Any]:
    return {
        "status": USER_VISUAL_CONFIRMATION_REQUIRED,
        "mode": "browser_pwa",
        "url": REPLAYWEB_OFFICIAL_WEB_APP_URL,
        "wacz_name": Path(wacz_path).name,
        "direct_file_url_supported": False,
        "note": (
            "The official browser/PWA viewer requires the supported file chooser for local "
            "WACZ files; direct file:// source URLs are rejected by ReplayWeb.page."
        ),
    }


def build_local_web_archive_action_state(
    *,
    wacz_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
    expected_source_url: str = "",
    expected_wacz_sha256: str = "",
    expected_manifest_sha256: str = "",
    expected_comment_count: int = 0,
    viewer: ReplayWebViewerDetection | None = None,
) -> LocalWebArchiveActionState:
    archive = Path(wacz_path) if wacz_path else Path("")
    detection = viewer or detect_replaywebpage_viewer()
    verification = (
        verify_local_web_archive_package(
            archive,
            manifest_path=manifest_path,
            expected_source_url=expected_source_url,
            expected_wacz_sha256=expected_wacz_sha256,
            expected_manifest_sha256=expected_manifest_sha256,
            expected_comment_count=expected_comment_count,
        )
        if wacz_path
        else LocalWebArchiveVerificationResult(
            status=REPLAY_PARTIAL,
            wacz_name="",
            manifest_name=Path(manifest_path).name if manifest_path else "",
            warnings=("No WACZ selected for verification.",),
        )
    )
    open_preview = build_replaywebpage_open_preview(archive, viewer=detection)
    show_preview = build_show_local_web_archive_files_preview(archive) if wacz_path else LocalWebArchiveCommandPreview(
        status=REPLAY_PARTIAL,
        message="No WACZ selected for file-manager preview.",
    )
    pwa = build_replayweb_browser_pwa_file_state(archive)
    return LocalWebArchiveActionState(
        archive_name=archive.name,
        capture_locally_status="existing_archive_selected" if wacz_path and archive.exists() else "capture_locally_available",
        open_archive_status=open_preview.status,
        show_files_status=show_preview.status,
        verify_status=verification.status,
        replay_visual_status=USER_VISUAL_CONFIRMATION_REQUIRED,
        viewer=detection,
        verification=verification,
        open_preview=open_preview,
        show_files_preview=show_preview,
        browser_pwa_status=str(pwa["status"]),
        browser_pwa_note=str(pwa["note"]),
    )


def local_web_archive_status_lines(state: LocalWebArchiveActionState) -> tuple[str, ...]:
    viewer_line = (
        f"ReplayWeb.page viewer: configured ({state.viewer.executable_name})"
        if state.viewer.status == VIEWER_CONFIGURED
        else "ReplayWeb.page viewer: VIEWER_NOT_CONFIGURED"
    )
    archive_line = f"Selected archive: {state.archive_name or 'none'}"
    verify_line = f"Verify: {state.verify_status}"
    comments_line = "Comments evidence: not checked"
    if state.verification.comments_json_count or state.verification.declared_comment_count:
        comments_line = (
            "Comments evidence: "
            f"{state.verification.comments_json_count}/{state.verification.declared_comment_count or state.verification.comments_json_count} "
            f"({state.verification.comments_evidence_status})"
        )
    return (
        "Local Web Archive",
        "Default backend: built-in WARC/WACZ + local evidence bundle",
        archive_line,
        viewer_line,
        f"Open archive: {state.open_archive_status}",
        f"Show files: {state.show_files_status}",
        verify_line,
        f"WACZ 1.2 profile: {state.verification.datapackage_profile or 'unknown'}",
        f"CDXJ lookup index: {'ready' if state.verification.replay_lookup_ready else 'not ready'}",
        (
            "Verify issue: " + state.verification.errors[0]
            if state.verification.errors
            else "Verify issue: none"
        ),
        comments_line,
        f"Replay visual status: {state.replay_visual_status}",
        "Browser/PWA note: local WACZ files require the official file chooser",
        "ArchiveBox backend: optional advanced backend",
        "Network actions performed by status preview: none",
    )
