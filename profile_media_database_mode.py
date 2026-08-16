"""UI-neutral Database mode view builder for Profile/Media Database.

V75Y bridges the read-only V75W index and V75X search layer into a compact
view model that a main Database-mode panel can consume.  This is not the left
sidebar toggle and it is not a sidebar filter.  It prepares case, source, and
profile rows from explicit batch JSON files only.

This module does not scan folders, create folders, move folders, rename
folders, copy media, download media, classify automatically, or infer sensitive
identifiers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_case_batch import build_case_batch_plan, load_case_batch_json
from profile_media_database import utc_now_iso
from profile_media_database_index import (
    ProfileMediaDatabaseIndex,
    ProfileMediaProfileIndexRow,
    ProfileMediaSourceIndexRow,
    build_database_index_from_batch_json_files,
    build_database_index_from_payloads,
)
from profile_media_database_search import (
    ProfileMediaDatabaseSearchResult,
    search_database_index,
)

PROFILE_MEDIA_DATABASE_MODE_SCHEMA_VERSION = "profile-media-database-mode-v75y"


@dataclass(frozen=True)
class ProfileMediaDatabaseModeRow:
    """One row/card in the Database mode main-panel model."""

    row_type: str
    title: str
    subtitle: str = ""
    case_title: str = ""
    local_address: str = ""
    source_bucket: str = ""
    source_role: str = ""
    claim_basis: str = ""
    currentness_status: str = ""
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["metadata"] = dict(self.metadata)
        return data


@dataclass(frozen=True)
class ProfileMediaDatabaseModeSection:
    """A named set of rows for the Database mode main panel."""

    section_id: str
    title: str
    rows: tuple[ProfileMediaDatabaseModeRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "row_count": len(self.rows),
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class ProfileMediaDatabaseModeView:
    """UI-neutral state for the main Database mode pane."""

    mode: str
    database_root: str
    search_result: ProfileMediaDatabaseSearchResult
    sections: tuple[ProfileMediaDatabaseModeSection, ...]
    schema_version: str = PROFILE_MEDIA_DATABASE_MODE_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    status: str = "success"
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        search_data = self.search_result.to_dict()
        sections = [section.to_dict() for section in self.sections]
        row_count = sum(section["row_count"] for section in sections)
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "mode": self.mode,
            "database_root": self.database_root,
            "index_case_count": self.search_result.index_case_count,
            "index_source_count": self.search_result.index_source_count,
            "index_profile_row_count": self.search_result.index_profile_row_count,
            "matched_source_count": len(self.search_result.matched_sources),
            "matched_profile_count": len(self.search_result.matched_profiles),
            "section_count": len(self.sections),
            "row_count": row_count,
            "sections": sections,
            "query": search_data["query"],
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
        }


def _tag_list(*values: Any) -> tuple[str, ...]:
    tags: list[str] = []
    for value in values:
        if value is True:
            continue
        if value:
            text = str(value).strip()
            if text and text not in tags:
                tags.append(text)
    return tuple(tags)


def _source_mode_row(row: ProfileMediaSourceIndexRow) -> ProfileMediaDatabaseModeRow:
    tags = [row.source_bucket, row.source_role, row.claim_basis, row.currentness_status]
    if row.source_chain_gap:
        tags.append("source-chain gap")
    if row.disputed_framing:
        tags.append("disputed framing")
    return ProfileMediaDatabaseModeRow(
        row_type="source",
        title=row.source_title or "Untitled Source",
        subtitle=row.source_page,
        case_title=row.case_title,
        local_address=row.local_address,
        source_bucket=row.source_bucket,
        source_role=row.source_role,
        claim_basis=row.claim_basis,
        currentness_status=row.currentness_status,
        tags=_tag_list(*tags),
        metadata={
            "source_chain_gap": row.source_chain_gap,
            "disputed_framing": row.disputed_framing,
            "notes_on_context_dispute": row.notes_on_context_dispute,
            "confidence_or_verification_notes": row.confidence_or_verification_notes,
        },
    )


def _profile_mode_row(row: ProfileMediaProfileIndexRow) -> ProfileMediaDatabaseModeRow:
    tags = [row.source_bucket, row.source_role, row.claim_basis, row.currentness_status]
    if row.parser_warnings:
        tags.append("parser warnings")
    return ProfileMediaDatabaseModeRow(
        row_type="profile",
        title=row.canonical_name or "Unknown Person",
        subtitle=row.case_title,
        case_title=row.case_title,
        local_address="; ".join(row.local_addresses),
        source_bucket=row.source_bucket,
        source_role=row.source_role,
        claim_basis=row.claim_basis,
        currentness_status=row.currentness_status,
        tags=_tag_list(*tags),
        metadata={
            "text_block_count": row.text_block_count,
            "identifier_count": row.identifier_count,
            "parser_warnings": list(row.parser_warnings),
            "source_pages": list(row.source_pages),
            "local_addresses": list(row.local_addresses),
        },
    )


def _case_rows(index: ProfileMediaDatabaseIndex) -> tuple[ProfileMediaDatabaseModeRow, ...]:
    rows: list[ProfileMediaDatabaseModeRow] = []
    for case_title in index.cases:
        source_count = sum(1 for row in index.sources if row.case_title == case_title)
        profile_count = sum(1 for row in index.profiles if row.case_title == case_title)
        rows.append(
            ProfileMediaDatabaseModeRow(
                row_type="case",
                title=case_title,
                subtitle=f"{source_count} sources; {profile_count} profile rows",
                case_title=case_title,
                local_address=f"Cases/{case_title}",
                tags=("case",),
                metadata={"source_count": source_count, "profile_row_count": profile_count},
            )
        )
    return tuple(rows)


def build_database_mode_view(
    index: ProfileMediaDatabaseIndex,
    *,
    profile_name: str = "",
    case_title: str = "",
    source_bucket: str = "",
    source_role: str = "",
    claim_basis: str = "",
    currentness_status: str = "",
    text: str = "",
    source_chain_gap: bool | None = None,
    disputed_framing: bool | None = None,
    has_parser_warnings: bool | None = None,
    limit: int = 0,
) -> ProfileMediaDatabaseModeView:
    """Build a UI-neutral main-panel view from an already-built read-only index."""

    result = search_database_index(
        index,
        profile_name=profile_name,
        case_title=case_title,
        source_bucket=source_bucket,
        source_role=source_role,
        claim_basis=claim_basis,
        currentness_status=currentness_status,
        text=text,
        source_chain_gap=source_chain_gap,
        disputed_framing=disputed_framing,
        has_parser_warnings=has_parser_warnings,
        limit=limit,
    )
    sections = (
        ProfileMediaDatabaseModeSection("cases", "Cases", _case_rows(index)),
        ProfileMediaDatabaseModeSection("sources", "Sources", tuple(_source_mode_row(row) for row in result.matched_sources)),
        ProfileMediaDatabaseModeSection("profiles", "Profiles", tuple(_profile_mode_row(row) for row in result.matched_profiles)),
    )
    return ProfileMediaDatabaseModeView(
        mode="DATABASE",
        database_root=index.database_root,
        search_result=result,
        sections=sections,
        warnings=tuple(index.warnings),
    )


def build_database_mode_view_from_payloads(payloads: Iterable[Mapping[str, Any]], **kwargs: Any) -> ProfileMediaDatabaseModeView:
    """Build Database mode view from explicit in-memory batch payloads only."""

    index = build_database_index_from_payloads(payloads)
    return build_database_mode_view(index, **kwargs)


def build_database_mode_view_from_batch_json_files(paths: Iterable[str | Path], **kwargs: Any) -> ProfileMediaDatabaseModeView:
    """Build Database mode view from explicit batch JSON files only."""

    index = build_database_index_from_batch_json_files(paths)
    return build_database_mode_view(index, **kwargs)


def render_database_mode_view_text(view: ProfileMediaDatabaseModeView) -> str:
    """Render a compact main-panel style text view for CLI proof and tests."""

    data = view.to_dict()
    lines = [
        "Profile/Media Database Mode View",
        f"Status: {view.status}",
        f"Mode: {view.mode}",
        f"Database root: {view.database_root}",
        f"Index cases: {view.search_result.index_case_count}",
        f"Index sources: {view.search_result.index_source_count}",
        f"Index profile rows: {view.search_result.index_profile_row_count}",
        f"Matched sources: {len(view.search_result.matched_sources)}",
        f"Matched profiles: {len(view.search_result.matched_profiles)}",
        "Folder scan performed: false",
        "Folder creation performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "File write performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
    ]
    active_query = {key: value for key, value in data["query"].items() if value not in ("", None, 0)}
    if active_query:
        lines.extend(["", "Active query:"])
        for key, value in sorted(active_query.items()):
            lines.append(f"- {key}: {value}")
    for section in view.sections:
        lines.extend(["", f"{section.title}:"])
        if not section.rows:
            lines.append("- none")
            continue
        for row in section.rows:
            tag_text = f" [{'; '.join(row.tags)}]" if row.tags else ""
            subtitle = f" — {row.subtitle}" if row.subtitle else ""
            lines.append(f"- {row.title}{subtitle}{tag_text}")
    return "\n".join(lines)


def database_mode_payload(view: ProfileMediaDatabaseModeView, *, include_text: bool = False) -> dict[str, Any]:
    """Return CLI-friendly payload for Database mode view."""

    payload = view.to_dict()
    if include_text:
        payload["view_text"] = render_database_mode_view_text(view)
    return payload
