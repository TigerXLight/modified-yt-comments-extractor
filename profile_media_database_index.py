"""Explicit batch-driven index for Profile/Media Database mode.

V75W builds a database-level index from one or more user-supplied case batch
JSON files.  It is intentionally not a folder crawler: callers must provide
explicit JSON payloads or already-loaded dictionaries.  The index is a fast,
read-only view of cases, global profile names, case-local profile records, and
source claim-evaluation metadata.

This module does not scan folders, create folders, move folders, rename
folders, copy media, download media, classify automatically, or infer sensitive
identifiers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_case_batch import (
    PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION,
    build_case_batch_plan,
    load_case_batch_json,
)
from profile_media_database import parse_profile_text_blocks, stable_profile_id, utc_now_iso
from profile_media_source_role_policy import normalize_source_role_value

PROFILE_MEDIA_DATABASE_INDEX_SCHEMA_VERSION = "profile-media-database-index-v75w"


@dataclass(frozen=True)
class ProfileMediaSourceIndexRow:
    """One source row in the database-wide index."""

    case_title: str
    source_title: str
    source_page: str
    source_bucket: str
    source_role: str
    claim_basis: str
    currentness_status: str
    source_chain_gap: bool = False
    disputed_framing: bool = False
    notes_on_context_dispute: str = ""
    confidence_or_verification_notes: str = ""
    local_address: str = ""
    row_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaProfileIndexRow:
    """One case-local profile row in the database-wide index."""

    case_title: str
    canonical_name: str
    source_bucket: str
    source_role: str
    claim_basis: str
    currentness_status: str
    text_block_count: int = 0
    identifier_count: int = 0
    parser_warnings: tuple[str, ...] = ()
    local_addresses: tuple[str, ...] = ()
    source_pages: tuple[str, ...] = ()
    row_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaDatabaseIndex:
    """Read-only index compiled from explicit case batch JSON payloads."""

    database_root: str
    cases: tuple[str, ...]
    sources: tuple[ProfileMediaSourceIndexRow, ...]
    profiles: tuple[ProfileMediaProfileIndexRow, ...]
    schema_version: str = PROFILE_MEDIA_DATABASE_INDEX_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        unique_profile_names = sorted({row.canonical_name for row in self.profiles if row.canonical_name})
        source_buckets = sorted({row.source_bucket for row in self.sources if row.source_bucket})
        source_roles = sorted({row.source_role for row in self.sources if row.source_role})
        claim_bases = sorted({row.claim_basis for row in self.sources if row.claim_basis})
        profile_case_map: dict[str, list[str]] = {}
        for row in self.profiles:
            profile_case_map.setdefault(row.canonical_name or "Unknown Person", []).append(row.case_title)
        data = asdict(self)
        data["sources"] = [row.to_dict() for row in self.sources]
        data["profiles"] = [row.to_dict() for row in self.profiles]
        data["case_count"] = len(self.cases)
        data["source_count"] = len(self.sources)
        data["profile_row_count"] = len(self.profiles)
        data["unique_profile_count"] = len(unique_profile_names)
        data["unique_profile_names"] = unique_profile_names
        data["source_buckets"] = source_buckets
        data["source_roles"] = source_roles
        data["claim_bases"] = claim_bases
        data["source_chain_gap_count"] = sum(1 for row in self.sources if row.source_chain_gap)
        data["disputed_framing_count"] = sum(1 for row in self.sources if row.disputed_framing)
        data["unknown_source_role_count"] = sum(1 for row in self.sources if row.source_role in ("", "UNKNOWN_SOURCE_ROLE"))
        data["profile_case_map"] = {name: sorted(set(cases)) for name, cases in sorted(profile_case_map.items())}
        data["warning_count"] = len(self.warnings)
        return data


@dataclass(frozen=True)
class ProfileMediaDatabaseIndexResult:
    """CLI-friendly result for a database index build."""

    status: str
    index: ProfileMediaDatabaseIndex
    schema_version: str = PROFILE_MEDIA_DATABASE_INDEX_SCHEMA_VERSION
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    file_copy_or_media_download_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["index"] = self.index.to_dict()
        data["case_count"] = len(self.index.cases)
        data["source_count"] = len(self.index.sources)
        data["profile_row_count"] = len(self.index.profiles)
        data["unique_profile_count"] = len({row.canonical_name for row in self.index.profiles if row.canonical_name})
        data["warnings"] = self.index.warnings
        return data


def _first_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _profile_name_from_text(profile_text: str, fallback: str = "") -> tuple[str, int, int, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    blocks = parse_profile_text_blocks(profile_text)
    names = [block.name for block in blocks if block.name]
    canonical_name = names[0] if names else fallback.strip()
    identifier_count = sum(len(block.identifiers) for block in blocks)
    warnings = sorted({warning for block in blocks for warning in block.parser_warnings})
    local_addresses = tuple(sorted({block.local_address for block in blocks if block.local_address}))
    source_pages = tuple(sorted({block.source_page for block in blocks if block.source_page}))
    return canonical_name or "Unknown Person", len(blocks), identifier_count, tuple(warnings), local_addresses, source_pages


def _case_database_root(existing: str, candidate: str) -> str:
    if existing:
        return existing
    return candidate


def build_database_index_from_payloads(payloads: Iterable[Mapping[str, Any]]) -> ProfileMediaDatabaseIndex:
    """Build an index from explicit case batch payloads only."""

    cases: list[str] = []
    source_rows: list[ProfileMediaSourceIndexRow] = []
    profile_rows: list[ProfileMediaProfileIndexRow] = []
    warnings: list[str] = []
    database_root = ""

    for batch_number, payload in enumerate(payloads, start=1):
        plan = build_case_batch_plan(payload=payload)
        database_root = _case_database_root(database_root, plan.database_root)
        if database_root and plan.database_root and plan.database_root != database_root:
            warnings.append(f"mixed_database_root:batch_{batch_number}")
        case_title = plan.case_title
        cases.append(case_title)

        for index, source in enumerate(plan.source_specs, start=1):
            source_title = _first_text(source.get("source_title")) or "Untitled Source"
            source_page = _first_text(source.get("source_page"))
            source_bucket = _first_text(source.get("source_bucket")) or "Articles"
            raw_source_role = _first_text(source.get("source_role")) or "UNKNOWN_SOURCE_ROLE"
            source_role_decision = normalize_source_role_value(raw_source_role)
            source_role = source_role_decision.normalized_value
            if source_role_decision.warning:
                warnings.append(f"batch_{batch_number}:source_{index}:{source_role_decision.warning}")
            claim_basis = _first_text(source.get("claim_basis")) or "UNKNOWN_CLAIM_BASIS"
            currentness_status = _first_text(source.get("currentness_status")) or "UNKNOWN"
            local_address = f"Cases/{case_title}/Sources/{source_bucket}/{source_title}"
            row_id = stable_profile_id("source_index", case_title, source_bucket, source_page, source_title, str(index))
            source_rows.append(
                ProfileMediaSourceIndexRow(
                    case_title=case_title,
                    source_title=source_title,
                    source_page=source_page,
                    source_bucket=source_bucket,
                    source_role=source_role,
                    claim_basis=claim_basis,
                    currentness_status=currentness_status,
                    source_chain_gap=_bool_value(source.get("source_chain_gap")),
                    disputed_framing=_bool_value(source.get("disputed_framing")),
                    notes_on_context_dispute=_first_text(source.get("notes_on_context_dispute")),
                    confidence_or_verification_notes=_first_text(source.get("confidence_or_verification_notes")),
                    local_address=local_address,
                    row_id=row_id,
                )
            )

        for index, profile in enumerate(plan.profile_specs, start=1):
            profile_text = _first_text(profile.get("profile_text"))
            fallback_name = _first_text(profile.get("canonical_name"))
            canonical_name, block_count, identifier_count, parser_warnings, local_addresses, source_pages = _profile_name_from_text(profile_text, fallback=fallback_name)
            source_bucket = _first_text(profile.get("source_bucket")) or "Articles"
            raw_profile_source_role = _first_text(profile.get("source_role")) or "UNKNOWN_SOURCE_ROLE"
            profile_source_role_decision = normalize_source_role_value(raw_profile_source_role)
            source_role = profile_source_role_decision.normalized_value
            if profile_source_role_decision.warning:
                warnings.append(f"batch_{batch_number}:profile_{index}:{profile_source_role_decision.warning}")
            claim_basis = _first_text(profile.get("claim_basis")) or "UNKNOWN_CLAIM_BASIS"
            currentness_status = _first_text(profile.get("currentness_status")) or "UNKNOWN"
            row_id = stable_profile_id("profile_index", case_title, canonical_name, source_bucket, str(index))
            profile_rows.append(
                ProfileMediaProfileIndexRow(
                    case_title=case_title,
                    canonical_name=canonical_name,
                    source_bucket=source_bucket,
                    source_role=source_role,
                    claim_basis=claim_basis,
                    currentness_status=currentness_status,
                    text_block_count=block_count,
                    identifier_count=identifier_count,
                    parser_warnings=parser_warnings,
                    local_addresses=local_addresses,
                    source_pages=source_pages,
                    row_id=row_id,
                )
            )
            if parser_warnings:
                warnings.append(f"profile_parser_warnings:{case_title}:{canonical_name}:{','.join(parser_warnings)}")

    if not cases:
        warnings.append("no_case_batches_indexed")
    return ProfileMediaDatabaseIndex(
        database_root=database_root,
        cases=tuple(dict.fromkeys(cases)),
        sources=tuple(source_rows),
        profiles=tuple(profile_rows),
        warnings=tuple(warnings),
    )


def build_database_index_from_batch_json_files(paths: Iterable[str | Path]) -> ProfileMediaDatabaseIndex:
    """Build an index from explicit batch JSON files; never scans a folder."""

    payloads = [load_case_batch_json(path) for path in paths]
    return build_database_index_from_payloads(payloads)


def render_database_index_text(index: ProfileMediaDatabaseIndex) -> str:
    """Render a readable database-wide index summary."""

    payload = index.to_dict()
    lines = [
        "Profile/Media Database Index",
        f"Database root: {index.database_root}",
        f"Case count: {payload['case_count']}",
        f"Source count: {payload['source_count']}",
        f"Profile row count: {payload['profile_row_count']}",
        f"Unique global profile names: {payload['unique_profile_count']}",
        f"Source-chain gap count: {payload['source_chain_gap_count']}",
        f"Disputed framing count: {payload['disputed_framing_count']}",
        f"Unknown source-role count: {payload['unknown_source_role_count']}",
        "Folder scan performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
    ]
    if index.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in index.warnings)
    lines.extend(["", "Cases:"])
    for case_title in index.cases:
        lines.append(f"- {case_title}")
    lines.extend(["", "Profiles:"])
    for name, cases in payload["profile_case_map"].items():
        lines.append(f"- {name}: {', '.join(cases)}")
    lines.extend(["", "Sources:"])
    for row in index.sources:
        flags = []
        if row.source_chain_gap:
            flags.append("source-chain gap")
        if row.disputed_framing:
            flags.append("disputed framing")
        flag_text = f" ({'; '.join(flags)})" if flags else ""
        lines.append(f"- {row.case_title} > {row.source_bucket} > {row.source_title} [{row.source_role} / {row.claim_basis}]{flag_text}")
    return "\n".join(lines)


def result_payload(index: ProfileMediaDatabaseIndex, *, include_text: bool = False) -> dict[str, Any]:
    """Return CLI-friendly result data with optional human text."""

    result = ProfileMediaDatabaseIndexResult(status="success", index=index)
    payload = result.to_dict()
    if include_text:
        payload["index_text"] = render_database_index_text(index)
    return payload
