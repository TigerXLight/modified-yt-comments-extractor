"""Review report helpers for Profile/Media Database sessions.

The report highlights records requiring human review: source-chain gaps,
disputed framing, unknown source roles, parser warnings, and blocked/unknown
mode states.  It is a read-only report generated from an existing session
snapshot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from profile_media_database import utc_now_iso
from profile_media_database_session import ProfileMediaDatabaseSessionSnapshot

PROFILE_MEDIA_DATABASE_REVIEW_REPORT_SCHEMA_VERSION = "profile-media-database-review-report-v75z"


@dataclass(frozen=True)
class ProfileMediaReviewReportItem:
    """A single review item from the current Database session."""

    item_type: str
    severity: str
    title: str
    case_title: str = ""
    source_bucket: str = ""
    source_role: str = ""
    claim_basis: str = ""
    local_address: str = ""
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaReviewReport:
    """Read-only review report for a Database session."""

    status: str
    items: tuple[ProfileMediaReviewReportItem, ...]
    source_chain_gap_count: int = 0
    disputed_framing_count: int = 0
    unknown_source_role_count: int = 0
    parser_warning_count: int = 0
    warning_count: int = 0
    schema_version: str = PROFILE_MEDIA_DATABASE_REVIEW_REPORT_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "review_item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "source_chain_gap_count": self.source_chain_gap_count,
            "disputed_framing_count": self.disputed_framing_count,
            "unknown_source_role_count": self.unknown_source_role_count,
            "parser_warning_count": self.parser_warning_count,
            "warning_count": self.warning_count,
            "folder_scan_performed": self.folder_scan_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }


def build_review_report_from_session(snapshot: ProfileMediaDatabaseSessionSnapshot) -> ProfileMediaReviewReport:
    """Build a read-only review report from an existing session snapshot."""

    items: list[ProfileMediaReviewReportItem] = []
    source_chain_gap_count = 0
    disputed_framing_count = 0
    unknown_source_role_count = 0
    parser_warning_count = 0
    if snapshot.mode_view is None:
        for warning in snapshot.warnings:
            items.append(ProfileMediaReviewReportItem("session_warning", "medium", warning, reason=warning))
        return ProfileMediaReviewReport(status=snapshot.status, items=tuple(items), warning_count=len(snapshot.warnings))

    for row in snapshot.mode_view.search_result.matched_sources:
        if row.source_chain_gap:
            source_chain_gap_count += 1
            items.append(ProfileMediaReviewReportItem(
                item_type="source_chain_gap",
                severity="high",
                title=row.source_title,
                case_title=row.case_title,
                source_bucket=row.source_bucket,
                source_role=row.source_role,
                claim_basis=row.claim_basis,
                local_address=row.local_address,
                reason="Original source is not cited or cannot be located.",
                metadata={"source_page": row.source_page, "notes": row.confidence_or_verification_notes},
            ))
        if row.disputed_framing:
            disputed_framing_count += 1
            items.append(ProfileMediaReviewReportItem(
                item_type="disputed_framing",
                severity="medium",
                title=row.source_title,
                case_title=row.case_title,
                source_bucket=row.source_bucket,
                source_role=row.source_role,
                claim_basis=row.claim_basis,
                local_address=row.local_address,
                reason="Original author/uploader disputes, corrects, or clarifies framing/context.",
                metadata={"source_page": row.source_page, "notes_on_context_dispute": row.notes_on_context_dispute},
            ))
        if not row.source_role or "UNKNOWN" in row.source_role.upper():
            unknown_source_role_count += 1
            items.append(ProfileMediaReviewReportItem(
                item_type="unknown_source_role",
                severity="medium",
                title=row.source_title,
                case_title=row.case_title,
                source_bucket=row.source_bucket,
                source_role=row.source_role,
                claim_basis=row.claim_basis,
                local_address=row.local_address,
                reason="Source role needs manual classification.",
                metadata={"source_page": row.source_page},
            ))

    for row in snapshot.mode_view.search_result.matched_profiles:
        if row.parser_warnings:
            parser_warning_count += len(row.parser_warnings)
            items.append(ProfileMediaReviewReportItem(
                item_type="profile_parser_warnings",
                severity="low",
                title=row.canonical_name,
                case_title=row.case_title,
                source_bucket=row.source_bucket,
                source_role=row.source_role,
                claim_basis=row.claim_basis,
                local_address="; ".join(row.local_addresses),
                reason="Profile text has missing or malformed fields.",
                metadata={"parser_warnings": list(row.parser_warnings)},
            ))
        if not row.source_role or "UNKNOWN" in row.source_role.upper():
            unknown_source_role_count += 1
            items.append(ProfileMediaReviewReportItem(
                item_type="unknown_profile_source_role",
                severity="medium",
                title=row.canonical_name,
                case_title=row.case_title,
                source_bucket=row.source_bucket,
                source_role=row.source_role,
                claim_basis=row.claim_basis,
                local_address="; ".join(row.local_addresses),
                reason="Profile source role needs manual classification.",
                metadata={"source_pages": list(row.source_pages)},
            ))
    return ProfileMediaReviewReport(
        status="success",
        items=tuple(items),
        source_chain_gap_count=source_chain_gap_count,
        disputed_framing_count=disputed_framing_count,
        unknown_source_role_count=unknown_source_role_count,
        parser_warning_count=parser_warning_count,
        warning_count=len(snapshot.warnings),
    )


def render_review_report_text(report: ProfileMediaReviewReport) -> str:
    """Render the review report for logs, CLI, and future main Database UI."""

    lines = [
        "Profile/Media Database Review Report",
        f"Status: {report.status}",
        f"Review items: {len(report.items)}",
        f"Source-chain gaps: {report.source_chain_gap_count}",
        f"Disputed framing: {report.disputed_framing_count}",
        f"Unknown source roles: {report.unknown_source_role_count}",
        f"Parser warnings: {report.parser_warning_count}",
        "Folder scan performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
        "",
        "Items:",
    ]
    if not report.items:
        lines.append("- none")
    for item in report.items:
        details = f"{item.case_title} > {item.source_bucket}" if item.case_title or item.source_bucket else "session"
        lines.append(f"- {item.severity.upper()} {item.item_type}: {item.title} ({details}) — {item.reason}")
    return "\n".join(lines)
