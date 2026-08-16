"""Navigation targets for Profile/Media Database workbench rows.

The navigation layer converts the read-only V75W index into explicit row targets
that a future main Database UI can use for opening a case, source, or profile
record.  It stores addresses and breadcrumbs only; it does not open files,
scan folders, create folders, move folders, rename folders, copy media,
download media, classify automatically, or infer sensitive identifiers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import sanitize_path_part, stable_profile_id, utc_now_iso
from profile_media_database_index import (
    ProfileMediaDatabaseIndex,
    build_database_index_from_batch_json_files,
    build_database_index_from_payloads,
)

PROFILE_MEDIA_DATABASE_NAVIGATION_SCHEMA_VERSION = "profile-media-database-navigation-v76a"


@dataclass(frozen=True)
class ProfileMediaNavigationTarget:
    """A UI-neutral target for case/source/profile navigation."""

    target_type: str
    title: str
    case_title: str
    local_address: str
    breadcrumb: tuple[str, ...]
    target_id: str = ""
    source_bucket: str = ""
    source_role: str = ""
    claim_basis: str = ""
    source_page: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def normalized(self) -> "ProfileMediaNavigationTarget":
        target_id = self.target_id or stable_profile_id(
            "nav_target", self.target_type, self.case_title, self.title, self.local_address
        )
        return ProfileMediaNavigationTarget(
            target_type=self.target_type,
            title=self.title,
            case_title=self.case_title,
            local_address=self.local_address,
            breadcrumb=tuple(part for part in self.breadcrumb if part),
            target_id=target_id,
            source_bucket=self.source_bucket,
            source_role=self.source_role,
            claim_basis=self.claim_basis,
            source_page=self.source_page,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        item = self.normalized()
        data = asdict(item)
        data["metadata"] = dict(item.metadata)
        data["breadcrumb_text"] = " > ".join(item.breadcrumb)
        return data


@dataclass(frozen=True)
class ProfileMediaNavigationIndex:
    """Read-only set of navigation targets for Database workbench mode."""

    database_root: str
    targets: tuple[ProfileMediaNavigationTarget, ...]
    schema_version: str = PROFILE_MEDIA_DATABASE_NAVIGATION_SCHEMA_VERSION
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
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "database_root": self.database_root,
            "target_count": len(self.targets),
            "targets": [target.to_dict() for target in self.targets],
            "case_target_count": sum(1 for target in self.targets if target.target_type == "case"),
            "source_target_count": sum(1 for target in self.targets if target.target_type == "source"),
            "profile_target_count": sum(1 for target in self.targets if target.target_type == "profile"),
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


def _path_breadcrumb(local_address: str) -> tuple[str, ...]:
    parts = [part for part in str(local_address or "").replace("\\", "/").split("/") if part]
    return tuple(parts)


def _case_address(case_title: str) -> str:
    return f"Cases/{sanitize_path_part(case_title or 'Untitled Case', fallback='Untitled Case')}"


def build_navigation_index_from_index(index: ProfileMediaDatabaseIndex) -> ProfileMediaNavigationIndex:
    """Build navigation targets from an explicit database index."""

    targets: list[ProfileMediaNavigationTarget] = []
    for case_title in sorted(set(index.cases)):
        address = _case_address(case_title)
        targets.append(ProfileMediaNavigationTarget(
            target_type="case",
            title=case_title,
            case_title=case_title,
            local_address=address,
            breadcrumb=_path_breadcrumb(address),
            metadata={
                "source_count": sum(1 for row in index.sources if row.case_title == case_title),
                "profile_row_count": sum(1 for row in index.profiles if row.case_title == case_title),
            },
        ))
    for row in index.sources:
        targets.append(ProfileMediaNavigationTarget(
            target_type="source",
            title=row.source_title,
            case_title=row.case_title,
            local_address=row.local_address,
            breadcrumb=_path_breadcrumb(row.local_address),
            source_bucket=row.source_bucket,
            source_role=row.source_role,
            claim_basis=row.claim_basis,
            source_page=row.source_page,
            metadata={
                "source_chain_gap": row.source_chain_gap,
                "disputed_framing": row.disputed_framing,
                "currentness_status": row.currentness_status,
            },
        ))
    for row in index.profiles:
        address = f"Cases/{sanitize_path_part(row.case_title, fallback='Untitled Case')}/Profiles/{sanitize_path_part(row.canonical_name, fallback='Unknown Person')}"
        targets.append(ProfileMediaNavigationTarget(
            target_type="profile",
            title=row.canonical_name,
            case_title=row.case_title,
            local_address=address,
            breadcrumb=_path_breadcrumb(address),
            source_bucket=row.source_bucket,
            source_role=row.source_role,
            claim_basis=row.claim_basis,
            source_page="; ".join(row.source_pages),
            metadata={
                "identifier_count": row.identifier_count,
                "text_block_count": row.text_block_count,
                "parser_warnings": list(row.parser_warnings),
                "source_pages": list(row.source_pages),
                "local_addresses": list(row.local_addresses),
            },
        ))
    return ProfileMediaNavigationIndex(
        database_root=index.database_root,
        targets=tuple(target.normalized() for target in targets),
        warnings=index.warnings,
    )


def build_navigation_index_from_payloads(payloads: Iterable[Mapping[str, Any]]) -> ProfileMediaNavigationIndex:
    """Build navigation targets from explicit in-memory batch payloads only."""

    return build_navigation_index_from_index(build_database_index_from_payloads(payloads))


def build_navigation_index_from_batch_json_files(paths: Iterable[str | Path]) -> ProfileMediaNavigationIndex:
    """Build navigation targets from explicit batch JSON file paths only."""

    return build_navigation_index_from_index(build_database_index_from_batch_json_files(paths))


def filter_navigation_targets(navigation: ProfileMediaNavigationIndex, *, text: str = "", target_type: str = "") -> tuple[ProfileMediaNavigationTarget, ...]:
    """Filter navigation targets without touching the filesystem."""

    needle = str(text or "").strip().lower()
    wanted_type = str(target_type or "").strip().lower()
    rows: list[ProfileMediaNavigationTarget] = []
    for target in navigation.targets:
        normalized = target.normalized()
        haystack = "\n".join([
            normalized.target_type,
            normalized.title,
            normalized.case_title,
            normalized.local_address,
            normalized.source_bucket,
            normalized.source_role,
            normalized.claim_basis,
            normalized.source_page,
            " > ".join(normalized.breadcrumb),
        ]).lower()
        if wanted_type and normalized.target_type.lower() != wanted_type:
            continue
        if needle and needle not in haystack:
            continue
        rows.append(normalized)
    return tuple(rows)


def render_navigation_text(navigation: ProfileMediaNavigationIndex, *, text: str = "", target_type: str = "") -> str:
    """Render navigation targets for CLI proof and future main UI diagnostics."""

    targets = filter_navigation_targets(navigation, text=text, target_type=target_type)
    lines = [
        "Profile/Media Database Navigation",
        f"Status: {navigation.status}",
        f"Database root: {navigation.database_root}",
        f"Targets: {len(targets)} of {len(navigation.targets)}",
        "Folder scan performed: false",
        "Folder creation performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "File write performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
        "",
        "Targets:",
    ]
    if not targets:
        lines.append("- none")
    for target in targets:
        data = target.to_dict()
        lines.append(f"- {data['target_type']}: {data['title']} — {data['breadcrumb_text']}")
    return "\n".join(lines)


def navigation_payload(navigation: ProfileMediaNavigationIndex, *, include_text: bool = False) -> dict[str, Any]:
    """Return JSON-safe navigation payload."""

    data = navigation.to_dict()
    if include_text:
        data["navigation_text"] = render_navigation_text(navigation)
    return data
