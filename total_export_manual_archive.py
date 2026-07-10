from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Sequence
from urllib.parse import urlparse

from evidence_schema import utc_now_iso
from youtube_url_utils import normalize_youtube_url


ARCHIVE_STATUS_NOT_CHECKED = "not_checked"
ARCHIVE_STATUS_MANUALLY_SUPPLIED = "manually_supplied"
ARCHIVE_STATUS_MANUALLY_CHECKED_FOUND = "manually_checked_found"
ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND = "manually_checked_not_found"
ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED = "manual_follow_up_needed"
ARCHIVE_STATUS_NOT_APPLICABLE = "not_applicable"

MANUAL_ARCHIVE_STATUSES = (
    ARCHIVE_STATUS_NOT_CHECKED,
    ARCHIVE_STATUS_MANUALLY_SUPPLIED,
    ARCHIVE_STATUS_MANUALLY_CHECKED_FOUND,
    ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND,
    ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED,
    ARCHIVE_STATUS_NOT_APPLICABLE,
)

ARCHIVE_SERVICE_INTERNET_ARCHIVE = "internet_archive"
ARCHIVE_SERVICE_ARCHIVE_TODAY = "archive_today"
ARCHIVE_SERVICE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class ManualArchiveRecord:
    source_url: str
    normalized_url: str = ""
    archive_url: str = ""
    archive_service_name: str = ARCHIVE_SERVICE_UNKNOWN
    archive_capture_time: str = ""
    archive_status: str = ARCHIVE_STATUS_NOT_CHECKED
    archive_notes: str = ""
    entered_at_utc: str = field(default_factory=utc_now_iso)
    verified_by_user_at_utc: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _clean_string(value: str) -> str:
    return str(value or "").strip()


def normalize_manual_archive_status(value: str) -> str:
    normalized = _clean_string(value).casefold().replace("-", "_").replace(" ", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")
    if not normalized:
        return ARCHIVE_STATUS_NOT_CHECKED
    if normalized in MANUAL_ARCHIVE_STATUSES:
        return normalized
    return ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def detect_archive_service_name(archive_url: str) -> str:
    parsed = urlparse(_clean_string(archive_url))
    host = (parsed.hostname or "").lower()
    if not host:
        return ARCHIVE_SERVICE_UNKNOWN

    if _host_matches(host, "archive.org"):
        return ARCHIVE_SERVICE_INTERNET_ARCHIVE

    if any(
        _host_matches(host, domain)
        for domain in ("archive.ph", "archive.today", "archive.is", "archive.vn")
    ):
        return ARCHIVE_SERVICE_ARCHIVE_TODAY

    return ARCHIVE_SERVICE_UNKNOWN


def normalize_source_url(value: str) -> str:
    source_url = _clean_string(value)
    if not source_url:
        return ""
    try:
        return normalize_youtube_url(source_url)
    except ValueError:
        return source_url


def build_manual_archive_record(
    *,
    source_url: str,
    normalized_url: str = "",
    archive_url: str = "",
    archive_service_name: str = "",
    archive_capture_time: str = "",
    archive_status: str = "",
    archive_notes: str = "",
    entered_at_utc: str = "",
    verified_by_user_at_utc: str = "",
) -> ManualArchiveRecord:
    cleaned_archive_url = _clean_string(archive_url)
    selected_status = normalize_manual_archive_status(archive_status)
    if not archive_status and cleaned_archive_url:
        selected_status = ARCHIVE_STATUS_MANUALLY_SUPPLIED
    if not archive_status and not cleaned_archive_url:
        selected_status = ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED

    return ManualArchiveRecord(
        source_url=_clean_string(source_url),
        normalized_url=_clean_string(normalized_url) or normalize_source_url(source_url),
        archive_url=cleaned_archive_url,
        archive_service_name=(
            _clean_string(archive_service_name)
            or detect_archive_service_name(cleaned_archive_url)
        ),
        archive_capture_time=_clean_string(archive_capture_time),
        archive_status=selected_status,
        archive_notes=_clean_string(archive_notes),
        entered_at_utc=_clean_string(entered_at_utc) or utc_now_iso(),
        verified_by_user_at_utc=_clean_string(verified_by_user_at_utc),
    )


def manual_archive_record_to_dict(record: ManualArchiveRecord) -> dict[str, str]:
    return record.to_dict()


def manual_archive_records_to_dict(
    records: Sequence[ManualArchiveRecord],
) -> dict[str, object]:
    status_counts: dict[str, int] = {}
    for record in records:
        status_counts[record.archive_status] = status_counts.get(record.archive_status, 0) + 1
    return {
        "record_count": len(records),
        "records": [manual_archive_record_to_dict(record) for record in records],
        "status_counts": dict(sorted(status_counts.items())),
        "warning": "Manual archive metadata is local/user-entered only; no archive services are checked.",
    }


def _format_value(value: str) -> str:
    return value or "(none)"


def build_manual_archive_report_text(records: Sequence[ManualArchiveRecord]) -> str:
    lines = [
        "Manual archive URL metadata report",
        "Scope: local/user-entered notes only; no archive checks or submissions are performed.",
        f"Record count: {len(records)}",
    ]
    if not records:
        lines.append("- (none)")
    for record in records:
        lines.append(
            f"- Source: {_format_value(record.normalized_url or record.source_url)} "
            f"[status={record.archive_status}; service={record.archive_service_name}; "
            f"archive_url={_format_value(record.archive_url)}]"
        )
        if record.archive_notes:
            lines.append(f"  Notes: {record.archive_notes}")
    lines.extend(
        [
            "Caution:",
            "- Archive URL presence does not prove correctness unless the user verifies it.",
            "- Missing archive metadata is unknown, not proof that no archive exists.",
            "- Statuses are local/user-entered notes, not external service results.",
        ]
    )
    return "\n".join(lines)


def build_manual_archive_report_markdown(records: Sequence[ManualArchiveRecord]) -> str:
    lines = [
        "# Manual Archive URL Metadata Report",
        "",
        "Local/user-entered notes only. This report does not check archive services or submit URLs.",
        "",
        "| Source URL | Archive URL | Service | Status | User verified at | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.normalized_url or record.source_url or "(none)",
                    record.archive_url or "(none)",
                    record.archive_service_name or ARCHIVE_SERVICE_UNKNOWN,
                    record.archive_status,
                    record.verified_by_user_at_utc or "(none)",
                    record.archive_notes or "",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- Archive URL presence does not prove correctness unless the user verifies it.",
            "- Missing archive metadata is unknown, not proof that no archive exists.",
            "- Statuses are local/user-entered notes, not external service results.",
        ]
    )
    return "\n".join(lines)
