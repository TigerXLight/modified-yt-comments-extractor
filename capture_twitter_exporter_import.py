from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from evidence_item_queue import EvidenceItemRole, EvidenceItemStatus, EvidenceQueueItem


TWITTER_EXPORTER_IMPORT_SCHEMA_VERSION = "twitter_exporter_import.v1"
TWITTER_EXPORTER_QUEUE_REVIEW_SCHEMA_VERSION = "twitter_exporter_queue_review_item.v1"
TWITTER_EXPORTER_IMPORTER_NAME = "Twitter Exporter"
TWITTER_EXPORTER_IMPORTER_SOURCE = "twitter_exporter_user_supplied_local_file"
TWITTER_EXPORTER_SOURCE_PLATFORM = "twitter_x"
TWITTER_EXPORTER_SOURCE_KIND = "local_export"
TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED = "USER_REVIEW_REQUIRED"
TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT = "USER_SUPPLIED_LOCAL_EXPORT"
TWITTER_EXPORTER_SCOPE = (
    "Twitter/X exporter local-output import only; no X/Twitter API, browser automation, "
    "extension automation, network, archive, download, screenshot/OCR, credential, broad "
    "folder scan, evidence file move, or automatic classification behavior"
)

MAX_ZIP_ENTRIES = 5000
MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_SINGLE_FILE_BYTES = 50 * 1024 * 1024

SUPPORTED_TEXT_SUFFIXES = {".txt", ".json", ".jsonl", ".csv", ".tsv"}
UNSUPPORTED_BINARY_SUFFIXES = {
    ".avif",
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".png",
    ".webm",
    ".webp",
}

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_TWEET_ID_RE = re.compile(r"(?:status|statuses)/(\d+)")
_HANDLE_RE = re.compile(r"@([A-Za-z0-9_]{1,20})")
_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class TwitterExporterRecord:
    record_id: str
    record_type: str = "tweet"
    tweet_id: str = ""
    conversation_id: str = ""
    author_handle: str = ""
    author_display_name: str = ""
    author_id: str = ""
    created_at_text: str = ""
    text: str = ""
    url: str = ""
    reply_to: str = ""
    quote_tweet_id: str = ""
    repost_of: str = ""
    like_count: int | None = None
    retweet_count: int | None = None
    reply_count: int | None = None
    view_count: int | None = None
    list_name: str = ""
    list_id: str = ""
    raw_source_file_name: str = ""
    row_index: int = 0
    parse_confidence: str = "low"
    missing_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "author_display_name": self.author_display_name,
            "author_handle": self.author_handle,
            "author_id": self.author_id,
            "conversation_id": self.conversation_id,
            "created_at_text": self.created_at_text,
            "like_count": self.like_count,
            "list_id": self.list_id,
            "list_name": self.list_name,
            "missing_fields": list(self.missing_fields),
            "parse_confidence": self.parse_confidence,
            "quote_tweet_id": self.quote_tweet_id,
            "raw_source_file_name": self.raw_source_file_name,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "reply_count": self.reply_count,
            "reply_to": self.reply_to,
            "repost_of": self.repost_of,
            "retweet_count": self.retweet_count,
            "row_index": self.row_index,
            "text": self.text,
            "tweet_id": self.tweet_id,
            "url": self.url,
            "view_count": self.view_count,
        }


@dataclass(frozen=True)
class TwitterExporterMemberMetadata:
    member_name: str
    media_type: str
    size_bytes: int
    sha256: str = ""
    parsed_record_count: int = 0
    skipped: bool = False
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_type": self.media_type,
            "member_name": self.member_name,
            "parsed_record_count": self.parsed_record_count,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "skipped": self.skipped,
            "warning": self.warning,
        }


@dataclass(frozen=True)
class TwitterExporterImportBundle:
    import_bundle_id: str
    import_status: str
    local_file_name: str
    local_file_sha256: str
    local_file_size_bytes: int
    archive_member_count: int = 0
    parsed_record_count: int = 0
    skipped_record_count: int = 0
    source_platform: str = TWITTER_EXPORTER_SOURCE_PLATFORM
    importer_source: str = TWITTER_EXPORTER_IMPORTER_SOURCE
    importer_name: str = TWITTER_EXPORTER_IMPORTER_NAME
    source_kind: str = TWITTER_EXPORTER_SOURCE_KIND
    review_status: str = TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED
    provenance_status: str = TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT
    user_review_required: bool = True
    manual_operator_only: bool = True
    local_user_supplied_export: bool = True
    live_verification_claimed: bool = False
    api_capture_claimed: bool = False
    browser_automation_claimed: bool = False
    extension_automation_claimed: bool = False
    archive_provider_result_claimed: bool = False
    downloaded_media_claimed: bool = False
    screenshot_claimed: bool = False
    ocr_claimed: bool = False
    automatic_classification: bool = False
    records: tuple[TwitterExporterRecord, ...] = ()
    members: tuple[TwitterExporterMemberMetadata, ...] = ()
    warnings: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    schema_version: str = TWITTER_EXPORTER_IMPORT_SCHEMA_VERSION
    scope: str = TWITTER_EXPORTER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_capture_claimed": self.api_capture_claimed,
            "archive_member_count": self.archive_member_count,
            "archive_provider_result_claimed": self.archive_provider_result_claimed,
            "automatic_classification": self.automatic_classification,
            "browser_automation_claimed": self.browser_automation_claimed,
            "downloaded_media_claimed": self.downloaded_media_claimed,
            "extension_automation_claimed": self.extension_automation_claimed,
            "import_bundle_id": self.import_bundle_id,
            "import_status": self.import_status,
            "importer_name": self.importer_name,
            "importer_source": self.importer_source,
            "live_verification_claimed": self.live_verification_claimed,
            "local_file_name": self.local_file_name,
            "local_file_sha256": self.local_file_sha256,
            "local_file_size_bytes": self.local_file_size_bytes,
            "local_user_supplied_export": self.local_user_supplied_export,
            "manual_operator_only": self.manual_operator_only,
            "members": [member.to_dict() for member in self.members],
            "ocr_claimed": self.ocr_claimed,
            "parsed_record_count": self.parsed_record_count,
            "provenance_status": self.provenance_status,
            "records": [record.to_dict() for record in self.records],
            "review_status": self.review_status,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "screenshot_claimed": self.screenshot_claimed,
            "skipped_record_count": self.skipped_record_count,
            "source_kind": self.source_kind,
            "source_platform": self.source_platform,
            "user_review_required": self.user_review_required,
            "validation_errors": list(self.validation_errors),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class TwitterExporterQueueReviewItem:
    item_id: str
    bundle: TwitterExporterImportBundle
    schema_version: str = TWITTER_EXPORTER_QUEUE_REVIEW_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        bundle_data = self.bundle.to_dict()
        return {
            "api_capture_claimed": False,
            "archive_provider_result_claimed": False,
            "automatic_classification": False,
            "browser_automation_claimed": False,
            "downloaded_media_claimed": False,
            "extension_automation_claimed": False,
            "import_bundle": bundle_data,
            "item_id": self.item_id,
            "live_verification_claimed": False,
            "local_file_name": self.bundle.local_file_name,
            "local_file_sha256": self.bundle.local_file_sha256,
            "ocr_claimed": False,
            "parsed_record_count": self.bundle.parsed_record_count,
            "provenance_status": self.bundle.provenance_status,
            "review_status": self.bundle.review_status,
            "schema_version": self.schema_version,
            "screenshot_claimed": False,
            "source_kind": self.bundle.source_kind,
            "source_platform": self.bundle.source_platform,
            "user_review_required": True,
        }

    def to_evidence_queue_item(self) -> EvidenceQueueItem:
        return EvidenceQueueItem(
            item_id=self.item_id,
            item_role=EvidenceItemRole.MANUAL_EVIDENCE_NOTE,
            display_name=f"Twitter/X exporter local import: {self.bundle.local_file_name}",
            local_path="",
            file_hash=self.bundle.local_file_sha256,
            file_size_bytes=self.bundle.local_file_size_bytes,
            is_manual_import=True,
            item_status=EvidenceItemStatus.NEEDS_REVIEW,
            created_at_utc="",
            updated_at_utc="",
            user_notes=_stable_json(self.to_dict()),
        )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_id(prefix: str, data: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _read_bounded_file(path: Path, *, max_single_file_bytes: int) -> bytes:
    if not path.exists():
        raise ValueError(f"Twitter exporter import file does not exist: {path.name}")
    if path.is_dir():
        raise ValueError("Twitter exporter import requires a file path, not a directory")
    size = path.stat().st_size
    if size > max_single_file_bytes:
        raise ValueError("Twitter exporter import file exceeds max_single_file_bytes")
    return path.read_bytes()


def _decode_text(data: bytes) -> tuple[str, tuple[str, ...]]:
    try:
        return data.decode("utf-8-sig"), ()
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace"), ("Input was decoded with replacement characters.",)


def _clean_key(key: str) -> str:
    return str(key or "").strip().lower().replace(" ", "_").replace("-", "_")


def _first(mapping: Mapping[str, Any], *keys: str) -> str:
    cleaned = {_clean_key(key): value for key, value in mapping.items()}
    for key in keys:
        value = cleaned.get(_clean_key(key))
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _tweet_id_from_url(url: str) -> str:
    match = _TWEET_ID_RE.search(url or "")
    return match.group(1) if match else ""


def _stable_record_id(
    *,
    record: Mapping[str, Any],
    member_name: str,
    row_index: int,
) -> str:
    tweet_id = str(record.get("tweet_id") or "").strip()
    if tweet_id:
        return f"twitter_x_tweet_{tweet_id}"
    return _stable_id(
        "twitter_x_record",
        {
            "author_handle": str(record.get("author_handle") or ""),
            "created_at_text": str(record.get("created_at_text") or ""),
            "member_name": member_name,
            "row_index": row_index,
            "text": str(record.get("text") or ""),
            "url": str(record.get("url") or ""),
        },
    )


def _record_from_mapping(
    mapping: Mapping[str, Any],
    *,
    member_name: str,
    row_index: int,
) -> TwitterExporterRecord:
    url = _first(mapping, "url", "tweet_url", "permalink", "link")
    tweet_id = _first(mapping, "tweet_id", "id", "id_str", "status_id") or _tweet_id_from_url(url)
    text = _first(mapping, "text", "full_text", "content", "tweet", "body")
    author_handle = _first(mapping, "author_handle", "username", "screen_name", "handle")
    if author_handle.startswith("@"):
        author_handle = author_handle[1:]
    record_values = {
        "author_handle": author_handle,
        "created_at_text": _first(mapping, "created_at", "created_at_text", "date", "time", "timestamp"),
        "text": text,
        "tweet_id": tweet_id,
        "url": url,
    }
    missing = tuple(key for key in ("tweet_id", "text", "author_handle", "created_at_text", "url") if not record_values[key])
    confidence = "high" if tweet_id and text else "medium" if text or url else "low"
    return TwitterExporterRecord(
        record_id=_stable_record_id(record=record_values, member_name=member_name, row_index=row_index),
        record_type=_first(mapping, "record_type", "type") or "tweet",
        tweet_id=tweet_id,
        conversation_id=_first(mapping, "conversation_id", "conversation_id_str"),
        author_handle=author_handle,
        author_display_name=_first(mapping, "author_display_name", "name", "display_name", "author"),
        author_id=_first(mapping, "author_id", "user_id", "user_id_str"),
        created_at_text=record_values["created_at_text"],
        text=text,
        url=url,
        reply_to=_first(mapping, "reply_to", "in_reply_to_status_id", "parent_id"),
        quote_tweet_id=_first(mapping, "quote_tweet_id", "quoted_status_id"),
        repost_of=_first(mapping, "repost_of", "retweeted_status_id", "retweet_of"),
        like_count=_int_or_none(_first(mapping, "like_count", "likes", "favorite_count")),
        retweet_count=_int_or_none(_first(mapping, "retweet_count", "retweets", "repost_count")),
        reply_count=_int_or_none(_first(mapping, "reply_count", "replies")),
        view_count=_int_or_none(_first(mapping, "view_count", "views")),
        list_name=_first(mapping, "list_name", "list"),
        list_id=_first(mapping, "list_id"),
        raw_source_file_name=member_name,
        row_index=row_index,
        parse_confidence=confidence,
        missing_fields=missing,
    )


def _record_from_text_block(block: str, *, member_name: str, row_index: int) -> TwitterExporterRecord:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    mapping: dict[str, Any] = {}
    body_lines: list[str] = []
    for line in lines:
        if ":" in line and len(line.split(":", 1)[0]) <= 40:
            key, value = line.split(":", 1)
            mapping[key.strip()] = value.strip()
            continue
        body_lines.append(line)
    if body_lines and not _first(mapping, "text", "content", "tweet"):
        mapping["text"] = "\n".join(body_lines)
    joined = "\n".join(lines)
    if not _first(mapping, "url", "tweet_url", "permalink", "link"):
        url_match = _URL_RE.search(joined)
        if url_match:
            mapping["url"] = url_match.group(0).rstrip(".,)")
    if not _first(mapping, "author_handle", "username", "screen_name", "handle"):
        handle_match = _HANDLE_RE.search(joined)
        if handle_match:
            mapping["author_handle"] = handle_match.group(1)
    return _record_from_mapping(mapping, member_name=member_name, row_index=row_index)


def _objects_from_json_payload(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, Mapping))
    if isinstance(value, Mapping):
        for key in ("tweets", "data", "items", "records", "statuses"):
            nested = value.get(key)
            if isinstance(nested, list):
                return tuple(item for item in nested if isinstance(item, Mapping))
        return (value,)
    return ()


def _parse_json_text(text: str, *, member_name: str) -> tuple[TwitterExporterRecord, ...]:
    payload = json.loads(text)
    return tuple(
        _record_from_mapping(item, member_name=member_name, row_index=index)
        for index, item in enumerate(_objects_from_json_payload(payload), start=1)
    )


def _parse_jsonl_text(text: str, *, member_name: str) -> tuple[TwitterExporterRecord, ...]:
    records: list[TwitterExporterRecord] = []
    for index, line in enumerate((line for line in text.splitlines() if line.strip()), start=1):
        payload = json.loads(line)
        if isinstance(payload, Mapping):
            records.append(_record_from_mapping(payload, member_name=member_name, row_index=index))
    return tuple(records)


def _parse_delimited_text(text: str, *, member_name: str, delimiter: str) -> tuple[TwitterExporterRecord, ...]:
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return tuple(
        _record_from_mapping(row, member_name=member_name, row_index=index)
        for index, row in enumerate(reader, start=1)
    )


def _parse_plain_text(text: str, *, member_name: str) -> tuple[TwitterExporterRecord, ...]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks and text.strip():
        blocks = [text.strip()]
    return tuple(
        _record_from_text_block(block, member_name=member_name, row_index=index)
        for index, block in enumerate(blocks, start=1)
    )


def _parse_supported_text_member(
    data: bytes,
    *,
    member_name: str,
) -> tuple[tuple[TwitterExporterRecord, ...], tuple[str, ...]]:
    text, decode_warnings = _decode_text(data)
    suffix = Path(member_name).suffix.lower()
    warnings = list(decode_warnings)
    try:
        if suffix == ".json":
            return _parse_json_text(text, member_name=member_name), tuple(warnings)
        if suffix == ".jsonl":
            return _parse_jsonl_text(text, member_name=member_name), tuple(warnings)
        if suffix == ".csv":
            return _parse_delimited_text(text, member_name=member_name, delimiter=","), tuple(warnings)
        if suffix == ".tsv":
            return _parse_delimited_text(text, member_name=member_name, delimiter="\t"), tuple(warnings)
        stripped = text.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            return _parse_json_text(text, member_name=member_name), tuple(warnings)
        if "\t" in text.splitlines()[0] if text.splitlines() else False:
            return _parse_delimited_text(text, member_name=member_name, delimiter="\t"), tuple(warnings)
        if "," in text.splitlines()[0] if text.splitlines() else False:
            return _parse_delimited_text(text, member_name=member_name, delimiter=","), tuple(warnings)
        return _parse_plain_text(text, member_name=member_name), tuple(warnings)
    except (csv.Error, json.JSONDecodeError, UnicodeError) as exc:
        warnings.append(f"Could not parse {member_name}: {exc.__class__.__name__}")
        return (), tuple(warnings)


def _safe_zip_member_name(name: str) -> str:
    raw = str(name or "")
    normalized = raw.replace("\\", "/")
    if not normalized or normalized.endswith("/"):
        return ""
    if normalized.startswith("/") or normalized.startswith("//") or _DRIVE_PATH_RE.match(normalized):
        raise ValueError(f"Unsafe zip member path rejected: {raw}")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Unsafe zip member path rejected: {raw}")
    return str(path)


def _is_zip_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0o170000
    return mode == 0o120000


def _member_media_type(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix == ".json":
        return "application/json"
    if suffix == ".jsonl":
        return "application/jsonl"
    if suffix == ".csv":
        return "text/csv"
    if suffix == ".tsv":
        return "text/tab-separated-values"
    if suffix == ".txt":
        return "text/plain"
    return "application/octet-stream"


def _import_members(
    members: Iterable[tuple[str, bytes]],
) -> tuple[tuple[TwitterExporterRecord, ...], tuple[TwitterExporterMemberMetadata, ...], tuple[str, ...]]:
    records: list[TwitterExporterRecord] = []
    metadata: list[TwitterExporterMemberMetadata] = []
    warnings: list[str] = []
    for member_name, data in sorted(members, key=lambda item: item[0]):
        suffix = Path(member_name).suffix.lower()
        if suffix not in SUPPORTED_TEXT_SUFFIXES:
            warning = f"Unsupported member skipped: {member_name}"
            metadata.append(
                TwitterExporterMemberMetadata(
                    member_name=member_name,
                    media_type=_member_media_type(member_name),
                    size_bytes=len(data),
                    skipped=True,
                    warning=warning,
                )
            )
            warnings.append(warning)
            continue
        member_records, member_warnings = _parse_supported_text_member(data, member_name=member_name)
        warnings.extend(member_warnings)
        records.extend(member_records)
        metadata.append(
            TwitterExporterMemberMetadata(
                member_name=member_name,
                media_type=_member_media_type(member_name),
                size_bytes=len(data),
                sha256=_sha256_bytes(data),
                parsed_record_count=len(member_records),
                warning="; ".join(member_warnings),
            )
        )
    return tuple(records), tuple(metadata), tuple(dict.fromkeys(warnings))


def _bundle_id(*, file_hash: str, records: Sequence[TwitterExporterRecord]) -> str:
    return _stable_id(
        "twitter_exporter_import",
        {
            "file_sha256": file_hash,
            "importer_name": TWITTER_EXPORTER_IMPORTER_NAME,
            "record_ids": tuple(record.record_id for record in records),
            "schema_version": TWITTER_EXPORTER_IMPORT_SCHEMA_VERSION,
        },
    )


def _bundle_from_parts(
    *,
    path: Path,
    file_bytes: bytes,
    records: tuple[TwitterExporterRecord, ...],
    members: tuple[TwitterExporterMemberMetadata, ...],
    warnings: tuple[str, ...],
    archive_member_count: int = 0,
) -> TwitterExporterImportBundle:
    file_hash = _sha256_bytes(file_bytes)
    skipped_count = sum(1 for member in members if member.skipped)
    return TwitterExporterImportBundle(
        import_bundle_id=_bundle_id(file_hash=file_hash, records=records),
        import_status="parsed" if records else "parsed_with_no_records",
        local_file_name=path.name,
        local_file_sha256=file_hash,
        local_file_size_bytes=len(file_bytes),
        archive_member_count=archive_member_count,
        parsed_record_count=len(records),
        skipped_record_count=skipped_count,
        records=records,
        members=members,
        warnings=tuple(sorted(warnings)),
    )


def import_twitter_exporter_local_file(
    path: str | Path,
    *,
    max_zip_entries: int = MAX_ZIP_ENTRIES,
    max_total_uncompressed_bytes: int = MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES,
    max_single_file_bytes: int = MAX_SINGLE_FILE_BYTES,
) -> TwitterExporterImportBundle:
    local_path = Path(path)
    file_bytes = _read_bounded_file(local_path, max_single_file_bytes=max_single_file_bytes)
    suffix = local_path.suffix.lower()
    if suffix == ".zip":
        return import_twitter_exporter_zip(
            local_path,
            max_zip_entries=max_zip_entries,
            max_total_uncompressed_bytes=max_total_uncompressed_bytes,
            max_single_file_bytes=max_single_file_bytes,
            _outer_file_bytes=file_bytes,
        )
    if suffix not in SUPPORTED_TEXT_SUFFIXES:
        raise ValueError(f"Unsupported Twitter exporter import file type: {suffix or '(none)'}")
    records, members, warnings = _import_members(((local_path.name, file_bytes),))
    return _bundle_from_parts(
        path=local_path,
        file_bytes=file_bytes,
        records=records,
        members=members,
        warnings=warnings,
    )


def import_twitter_exporter_zip(
    path: str | Path,
    *,
    max_zip_entries: int = MAX_ZIP_ENTRIES,
    max_total_uncompressed_bytes: int = MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES,
    max_single_file_bytes: int = MAX_SINGLE_FILE_BYTES,
    _outer_file_bytes: bytes | None = None,
) -> TwitterExporterImportBundle:
    local_path = Path(path)
    file_bytes = _outer_file_bytes
    if file_bytes is None:
        file_bytes = _read_bounded_file(local_path, max_single_file_bytes=max_single_file_bytes)
    members: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > max_zip_entries:
            raise ValueError("Twitter exporter zip exceeds max_zip_entries")
        total_size = sum(info.file_size for info in infos)
        if total_size > max_total_uncompressed_bytes:
            raise ValueError("Twitter exporter zip exceeds max_total_uncompressed_bytes")
        for info in infos:
            if _is_zip_symlink(info):
                raise ValueError(f"Unsafe zip symlink member rejected: {info.filename}")
            member_name = _safe_zip_member_name(info.filename)
            if not member_name:
                continue
            if info.file_size > max_single_file_bytes:
                raise ValueError(f"Twitter exporter zip member exceeds max_single_file_bytes: {member_name}")
            data = archive.read(info)
            members.append((member_name, data))
    records, member_metadata, warnings = _import_members(members)
    return _bundle_from_parts(
        path=local_path,
        file_bytes=file_bytes,
        records=records,
        members=member_metadata,
        warnings=warnings,
        archive_member_count=len(members),
    )


def inspect_twitter_exporter_local_file(path: str | Path, **kwargs: Any) -> TwitterExporterImportBundle:
    return import_twitter_exporter_local_file(path, **kwargs)


def build_twitter_exporter_review_bundle(path: str | Path, **kwargs: Any) -> TwitterExporterImportBundle:
    return import_twitter_exporter_local_file(path, **kwargs)


def build_twitter_exporter_queue_review_item(
    bundle: TwitterExporterImportBundle,
) -> TwitterExporterQueueReviewItem:
    item_id = _stable_id(
        "twitter_exporter_queue_review",
        {
            "import_bundle_id": bundle.import_bundle_id,
            "local_file_sha256": bundle.local_file_sha256,
            "schema_version": TWITTER_EXPORTER_QUEUE_REVIEW_SCHEMA_VERSION,
        },
    )
    return TwitterExporterQueueReviewItem(item_id=item_id, bundle=bundle)


def twitter_exporter_bundle_to_evidence_queue_item(
    bundle: TwitterExporterImportBundle,
) -> EvidenceQueueItem:
    return build_twitter_exporter_queue_review_item(bundle).to_evidence_queue_item()


__all__ = [
    "MAX_SINGLE_FILE_BYTES",
    "MAX_ZIP_ENTRIES",
    "MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES",
    "TWITTER_EXPORTER_IMPORTER_NAME",
    "TWITTER_EXPORTER_IMPORTER_SOURCE",
    "TWITTER_EXPORTER_IMPORT_SCHEMA_VERSION",
    "TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT",
    "TWITTER_EXPORTER_QUEUE_REVIEW_SCHEMA_VERSION",
    "TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED",
    "TwitterExporterImportBundle",
    "TwitterExporterMemberMetadata",
    "TwitterExporterQueueReviewItem",
    "TwitterExporterRecord",
    "build_twitter_exporter_queue_review_item",
    "build_twitter_exporter_review_bundle",
    "import_twitter_exporter_local_file",
    "import_twitter_exporter_zip",
    "inspect_twitter_exporter_local_file",
    "twitter_exporter_bundle_to_evidence_queue_item",
]
