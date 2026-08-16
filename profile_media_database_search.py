"""Read-only query layer for Profile/Media Database indexes.

V75X searches the explicit, batch-driven index produced by V75W.  It is not a
folder crawler and it does not mutate case repositories.  Callers provide one
or more already-known batch JSON files, then query the compiled in-memory
index by profile name, case title, source bucket, source role, claim basis,
currentness status, source-chain gap, disputed framing, parser-warning state,
or a general text term.

This module does not scan folders, create folders, move folders, rename
folders, copy media, download media, classify automatically, or infer sensitive
identifiers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from profile_media_database import utc_now_iso
from profile_media_database_index import (
    ProfileMediaDatabaseIndex,
    ProfileMediaProfileIndexRow,
    ProfileMediaSourceIndexRow,
    build_database_index_from_batch_json_files,
)

PROFILE_MEDIA_DATABASE_SEARCH_SCHEMA_VERSION = "profile-media-database-search-v75x"


@dataclass(frozen=True)
class ProfileMediaDatabaseSearchQuery:
    """User-visible search criteria for database mode."""

    profile_name: str = ""
    case_title: str = ""
    source_bucket: str = ""
    source_role: str = ""
    claim_basis: str = ""
    currentness_status: str = ""
    text: str = ""
    source_chain_gap: bool | None = None
    disputed_framing: bool | None = None
    has_parser_warnings: bool | None = None
    limit: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaDatabaseSearchResult:
    """Read-only search result with matched source/profile rows."""

    query: ProfileMediaDatabaseSearchQuery
    matched_sources: tuple[ProfileMediaSourceIndexRow, ...]
    matched_profiles: tuple[ProfileMediaProfileIndexRow, ...]
    index_case_count: int
    index_source_count: int
    index_profile_row_count: int
    schema_version: str = PROFILE_MEDIA_DATABASE_SEARCH_SCHEMA_VERSION
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
        data = asdict(self)
        data["query"] = self.query.to_dict()
        data["matched_sources"] = [row.to_dict() for row in self.matched_sources]
        data["matched_profiles"] = [row.to_dict() for row in self.matched_profiles]
        data["matched_source_count"] = len(self.matched_sources)
        data["matched_profile_count"] = len(self.matched_profiles)
        data["total_match_count"] = len(self.matched_sources) + len(self.matched_profiles)
        data["warning_count"] = len(self.warnings)
        return data


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains(value: Any, needle: str) -> bool:
    if not needle:
        return True
    return needle in _norm(value)


def _matches_bool(value: bool, expected: bool | None) -> bool:
    return True if expected is None else bool(value) is expected


def _source_text(row: ProfileMediaSourceIndexRow) -> str:
    return "\n".join(
        [
            row.case_title,
            row.source_title,
            row.source_page,
            row.source_bucket,
            row.source_role,
            row.claim_basis,
            row.currentness_status,
            row.notes_on_context_dispute,
            row.confidence_or_verification_notes,
            row.local_address,
        ]
    )


def _profile_text(row: ProfileMediaProfileIndexRow) -> str:
    return "\n".join(
        [
            row.case_title,
            row.canonical_name,
            row.source_bucket,
            row.source_role,
            row.claim_basis,
            row.currentness_status,
            "\n".join(row.parser_warnings),
            "\n".join(row.local_addresses),
            "\n".join(row.source_pages),
        ]
    )


def _source_matches(row: ProfileMediaSourceIndexRow, query: ProfileMediaDatabaseSearchQuery) -> bool:
    if _norm(query.profile_name) or query.has_parser_warnings is not None:
        return False
    text_query = _norm(query.text)
    return (
        _contains(row.case_title, _norm(query.case_title))
        and _contains(row.source_bucket, _norm(query.source_bucket))
        and _contains(row.source_role, _norm(query.source_role))
        and _contains(row.claim_basis, _norm(query.claim_basis))
        and _contains(row.currentness_status, _norm(query.currentness_status))
        and _matches_bool(row.source_chain_gap, query.source_chain_gap)
        and _matches_bool(row.disputed_framing, query.disputed_framing)
        and _contains(_source_text(row), text_query)
    )


def _profile_matches(row: ProfileMediaProfileIndexRow, query: ProfileMediaDatabaseSearchQuery) -> bool:
    if query.source_chain_gap is not None or query.disputed_framing is not None:
        return False
    text_query = _norm(query.text)
    has_warnings = bool(row.parser_warnings)
    return (
        _contains(row.canonical_name, _norm(query.profile_name))
        and _contains(row.case_title, _norm(query.case_title))
        and _contains(row.source_bucket, _norm(query.source_bucket))
        and _contains(row.source_role, _norm(query.source_role))
        and _contains(row.claim_basis, _norm(query.claim_basis))
        and _contains(row.currentness_status, _norm(query.currentness_status))
        and _matches_bool(has_warnings, query.has_parser_warnings)
        and _contains(_profile_text(row), text_query)
    )


def _limited(rows: list[Any], limit: int) -> tuple[Any, ...]:
    if limit and limit > 0:
        return tuple(rows[:limit])
    return tuple(rows)


def search_database_index(
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
) -> ProfileMediaDatabaseSearchResult:
    """Search an already-built V75W database index without filesystem crawling."""

    query = ProfileMediaDatabaseSearchQuery(
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
    source_matches = [row for row in index.sources if _source_matches(row, query)]
    profile_matches = [row for row in index.profiles if _profile_matches(row, query)]
    return ProfileMediaDatabaseSearchResult(
        query=query,
        matched_sources=_limited(source_matches, limit),
        matched_profiles=_limited(profile_matches, limit),
        index_case_count=len(index.cases),
        index_source_count=len(index.sources),
        index_profile_row_count=len(index.profiles),
        warnings=index.warnings,
    )


def search_database_batch_json_files(paths: Iterable[str | Path], **kwargs: Any) -> ProfileMediaDatabaseSearchResult:
    """Build a read-only index from explicit batch JSON files and query it."""

    index = build_database_index_from_batch_json_files(paths)
    return search_database_index(index, **kwargs)


def render_database_search_text(result: ProfileMediaDatabaseSearchResult) -> str:
    """Render a compact human-readable query report."""

    query_data = result.query.to_dict()
    active_criteria = {key: value for key, value in query_data.items() if value not in ("", None, 0)}
    lines = [
        "Profile/Media Database Search",
        f"Status: {result.status}",
        f"Index cases: {result.index_case_count}",
        f"Index sources: {result.index_source_count}",
        f"Index profile rows: {result.index_profile_row_count}",
        f"Matched sources: {len(result.matched_sources)}",
        f"Matched profiles: {len(result.matched_profiles)}",
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
    if active_criteria:
        lines.extend(["", "Criteria:"])
        for key, value in sorted(active_criteria.items()):
            lines.append(f"- {key}: {value}")
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in result.warnings)
    lines.extend(["", "Sources:"])
    if result.matched_sources:
        for row in result.matched_sources:
            flags = []
            if row.source_chain_gap:
                flags.append("source-chain gap")
            if row.disputed_framing:
                flags.append("disputed framing")
            flag_text = f" ({'; '.join(flags)})" if flags else ""
            lines.append(f"- {row.case_title} > {row.source_bucket} > {row.source_title} [{row.source_role} / {row.claim_basis}]{flag_text}")
    else:
        lines.append("- none")
    lines.extend(["", "Profiles:"])
    if result.matched_profiles:
        for row in result.matched_profiles:
            lines.append(f"- {row.canonical_name} > {row.case_title} [{row.source_bucket} / {row.source_role} / {row.claim_basis}]")
    else:
        lines.append("- none")
    return "\n".join(lines)


def result_payload(result: ProfileMediaDatabaseSearchResult, *, include_text: bool = False) -> dict[str, Any]:
    """Return CLI-friendly search output."""

    payload = result.to_dict()
    if include_text:
        payload["search_text"] = render_database_search_text(result)
    return payload
