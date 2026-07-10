from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

from evidence_schema import utc_now_iso
from youtube_url_utils import normalize_youtube_url


LOCAL_MEDIA_STATUS_REGISTERED = "registered"
LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE = "missing_local_file"
LOCAL_MEDIA_STATUS_HASH_MISMATCH = "hash_mismatch"
LOCAL_MEDIA_STATUS_NEEDS_REVIEW = "needs_review"
LOCAL_MEDIA_STATUS_NOT_APPLICABLE = "not_applicable"

LOCAL_MEDIA_STATUSES = (
    LOCAL_MEDIA_STATUS_REGISTERED,
    LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_STATUS_HASH_MISMATCH,
    LOCAL_MEDIA_STATUS_NEEDS_REVIEW,
    LOCAL_MEDIA_STATUS_NOT_APPLICABLE,
)

LOCAL_MEDIA_TYPE_VIDEO = "video"
LOCAL_MEDIA_TYPE_AUDIO = "audio"
LOCAL_MEDIA_TYPE_IMAGE = "image"
LOCAL_MEDIA_TYPE_UNKNOWN = "unknown"

HASH_ALGORITHM_SHA256 = "sha256"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


@dataclass(frozen=True)
class LocalMediaRecord:
    source_url: str = ""
    normalized_url: str = ""
    package_id: str = ""
    local_media_path: str = ""
    local_media_filename: str = ""
    local_file_size_bytes: int = 0
    local_file_sha256: str = ""
    media_type: str = LOCAL_MEDIA_TYPE_UNKNOWN
    duration_seconds: float | None = None
    media_notes: str = ""
    registered_at_utc: str = field(default_factory=utc_now_iso)
    verified_at_utc: str = ""
    exists_at_registration: bool = False
    hash_algorithm: str = HASH_ALGORITHM_SHA256
    status: str = LOCAL_MEDIA_STATUS_NEEDS_REVIEW

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _clean_string(value: object) -> str:
    return str(value or "").strip()


def normalize_local_media_status(value: str) -> str:
    normalized = _clean_string(value).casefold().replace("-", "_").replace(" ", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")
    if not normalized:
        return LOCAL_MEDIA_STATUS_NEEDS_REVIEW
    if normalized in LOCAL_MEDIA_STATUSES:
        return normalized
    return LOCAL_MEDIA_STATUS_NEEDS_REVIEW


def detect_local_media_type(path_or_name: str) -> str:
    suffix = Path(_clean_string(path_or_name)).suffix.casefold()
    if suffix in VIDEO_EXTENSIONS:
        return LOCAL_MEDIA_TYPE_VIDEO
    if suffix in AUDIO_EXTENSIONS:
        return LOCAL_MEDIA_TYPE_AUDIO
    if suffix in IMAGE_EXTENSIONS:
        return LOCAL_MEDIA_TYPE_IMAGE
    return LOCAL_MEDIA_TYPE_UNKNOWN


def sha256_file(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        return ""

    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_source_url(value: str) -> str:
    source_url = _clean_string(value)
    if not source_url:
        return ""
    try:
        return normalize_youtube_url(source_url)
    except ValueError:
        return source_url


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_local_media_record(
    *,
    source_url: str = "",
    normalized_url: str = "",
    package_id: str = "",
    local_media_path: str,
    local_media_filename: str = "",
    local_file_size_bytes: int = 0,
    local_file_sha256: str = "",
    media_type: str = "",
    duration_seconds: object = None,
    media_notes: str = "",
    registered_at_utc: str = "",
    verified_at_utc: str = "",
    exists_at_registration: bool | None = None,
    hash_algorithm: str = HASH_ALGORITHM_SHA256,
    status: str = "",
    compute_hash: bool = False,
) -> LocalMediaRecord:
    cleaned_path = _clean_string(local_media_path)
    path = Path(cleaned_path) if cleaned_path else Path()
    exists = path.is_file() if cleaned_path else False
    if exists_at_registration is not None:
        exists = bool(exists_at_registration)

    filename = _clean_string(local_media_filename)
    if not filename and cleaned_path:
        filename = path.name

    size_bytes = int(local_file_size_bytes or 0)
    if path.is_file():
        size_bytes = path.stat().st_size

    file_hash = _clean_string(local_file_sha256)
    if compute_hash and path.is_file():
        file_hash = sha256_file(str(path))

    selected_media_type = _clean_string(media_type) or detect_local_media_type(filename or cleaned_path)
    selected_status = normalize_local_media_status(status)
    if not status:
        selected_status = (
            LOCAL_MEDIA_STATUS_REGISTERED
            if exists
            else LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE
        )

    return LocalMediaRecord(
        source_url=_clean_string(source_url),
        normalized_url=_clean_string(normalized_url) or normalize_source_url(source_url),
        package_id=_clean_string(package_id),
        local_media_path=cleaned_path,
        local_media_filename=filename,
        local_file_size_bytes=size_bytes,
        local_file_sha256=file_hash,
        media_type=selected_media_type or LOCAL_MEDIA_TYPE_UNKNOWN,
        duration_seconds=_optional_float(duration_seconds),
        media_notes=_clean_string(media_notes),
        registered_at_utc=_clean_string(registered_at_utc) or utc_now_iso(),
        verified_at_utc=_clean_string(verified_at_utc),
        exists_at_registration=exists,
        hash_algorithm=_clean_string(hash_algorithm) or HASH_ALGORITHM_SHA256,
        status=selected_status,
    )


def local_media_record_to_dict(record: LocalMediaRecord) -> dict[str, object]:
    return record.to_dict()


def local_media_records_to_dict(
    records: Sequence[LocalMediaRecord],
) -> dict[str, object]:
    status_counts: dict[str, int] = {}
    media_type_counts: dict[str, int] = {}
    for record in records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
        media_type_counts[record.media_type] = media_type_counts.get(record.media_type, 0) + 1
    return {
        "media_type_counts": dict(sorted(media_type_counts.items())),
        "record_count": len(records),
        "records": [local_media_record_to_dict(record) for record in records],
        "status_counts": dict(sorted(status_counts.items())),
        "warning": "Local media metadata records user-supplied local files only; no media is downloaded or fetched.",
    }


def _format_value(value: object) -> str:
    if value is None or value == "":
        return "(none)"
    return str(value)


def build_local_media_report_text(records: Sequence[LocalMediaRecord]) -> str:
    lines = [
        "Local media registration metadata report",
        "Scope: local filesystem/user-entered notes only; no downloads, fetching, media probing, or transcription are performed.",
        f"Record count: {len(records)}",
    ]
    if not records:
        lines.append("- (none)")
    for record in records:
        lines.append(
            f"- File: {_format_value(record.local_media_path)} "
            f"[status={record.status}; media_type={record.media_type}; "
            f"size={record.local_file_size_bytes}; exists={record.exists_at_registration}]"
        )
        if record.local_file_sha256:
            lines.append(f"  SHA-256: {record.local_file_sha256}")
        if record.media_notes:
            lines.append(f"  Notes: {record.media_notes}")
    lines.extend(
        [
            "Caution:",
            "- Local file presence and hashes describe only local state at registration/check time.",
            "- Missing local files are local notes, not proof that a remote source is unavailable.",
            "- Media type detection is extension/string-only.",
        ]
    )
    return "\n".join(lines)


def build_local_media_report_markdown(records: Sequence[LocalMediaRecord]) -> str:
    lines = [
        "# Local Media Registration Metadata Report",
        "",
        "Local filesystem/user-entered notes only. This report does not download, fetch, probe media, or transcribe.",
        "",
        "| Source URL | Local path | Type | Status | Size bytes | SHA-256 | Notes |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.normalized_url or record.source_url or "(none)",
                    record.local_media_path or "(none)",
                    record.media_type,
                    record.status,
                    str(record.local_file_size_bytes),
                    record.local_file_sha256 or "(none)",
                    record.media_notes or "",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- Local file presence and hashes describe only local state at registration/check time.",
            "- Missing local files are local notes, not proof that a remote source is unavailable.",
            "- Media type detection is extension/string-only.",
        ]
    )
    return "\n".join(lines)
