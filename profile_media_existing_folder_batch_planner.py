"""Dry-run existing-folder to batch-JSON planner for Profile/Media Database mode.

V76E accepts an explicit folder-tree listing supplied by the user or another
safe caller and builds a reviewable batch-JSON preview.  It does not crawl the
filesystem.  The planner treats every line as already-disclosed path text, then
recognizes case folders, source buckets, case-local profiles, and global-header
profile candidates.

Default behavior is preview-only: no folder scan, no folder creation, no folder
move, no folder rename, no file copy, no media download, no automatic
classification, and no sensitive identifier inference.  Optional preview JSON
writing is guarded by an exact confirmation phrase and is for a standalone
batch preview file only; it does not mutate a case folder.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import sanitize_path_part, stable_profile_id, utc_now_iso
from profile_media_source_role_policy import canonical_source_role

PROFILE_MEDIA_EXISTING_FOLDER_PLANNER_SCHEMA_VERSION = "profile-media-existing-folder-planner-v76e"
PROFILE_MEDIA_EXISTING_FOLDER_BATCH_WRITE_CONFIRMATION = "WRITE_EXISTING_FOLDER_BATCH_PREVIEW"

SOURCE_BUCKET_PARTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("Sources", "Articles"), "Articles"),
    (("Sources", "Social Media", "Online"), "Social Media/Online"),
    (("Sources", "Social Media", "Offline"), "Social Media/Offline"),
    (("Sources", "Internal Media"), "Internal Media"),
)

CASE_LOCAL_PROFILE_MARKERS = (("Profiles",),)
GLOBAL_PROFILE_MARKERS = (("Database", "Profiles"), ("Profiles",))
REFERENCE_MARKERS = (("Reference Extants",), ("People",))


def _normalise_path_text(value: object) -> str:
    text = str(value or "").strip().strip('"').strip("'")
    text = text.replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    return text.strip("/")


def _parts(value: object) -> tuple[str, ...]:
    text = _normalise_path_text(value)
    return tuple(part for part in text.split("/") if part)


def _case_from_parts(parts: tuple[str, ...], fallback_case_title: str = "") -> tuple[str, int]:
    if "Cases" in parts:
        idx = parts.index("Cases")
        if idx + 1 < len(parts):
            return parts[idx + 1], idx + 2
    if fallback_case_title:
        return fallback_case_title, 0
    # A direct case export often starts with: Case Name/Sources/...
    for marker in ("Sources", "Profiles", "People", "Reference Extants"):
        if marker in parts:
            idx = parts.index(marker)
            if idx > 0:
                return parts[idx - 1], idx
    return "", 0


def _strip_extension(text: str) -> str:
    if not text:
        return ""
    name = Path(text).name
    suffix = Path(name).suffix
    if suffix and len(suffix) <= 12:
        return name[: -len(suffix)] or name
    return name


def _segment_after(parts: tuple[str, ...], marker: tuple[str, ...]) -> str:
    for i in range(0, max(0, len(parts) - len(marker) + 1)):
        if parts[i : i + len(marker)] == marker:
            if i + len(marker) < len(parts):
                return _strip_extension(parts[i + len(marker)])
    return ""


def _source_candidate_from_parts(parts: tuple[str, ...], fallback_case_title: str = "") -> tuple[str, str, str] | None:
    case_title, _ = _case_from_parts(parts, fallback_case_title)
    if not case_title:
        return None
    for marker, bucket in SOURCE_BUCKET_PARTS:
        title = _segment_after(parts, marker)
        if title:
            return case_title, bucket, title
    return None


def _profile_candidate_from_parts(parts: tuple[str, ...], fallback_case_title: str = "") -> tuple[str, str, bool] | None:
    # Global header profiles are collected, but not converted to case-local batch rows.
    for marker in GLOBAL_PROFILE_MARKERS:
        title = _segment_after(parts, marker)
        if title and (marker == ("Database", "Profiles") or (parts and parts[0] == "Profiles")):
            return "", title, True
    case_title, _ = _case_from_parts(parts, fallback_case_title)
    if not case_title:
        return None
    title = _segment_after(parts, ("Profiles",))
    if title:
        return case_title, title, False
    return None


def _is_reference_or_people(parts: tuple[str, ...]) -> bool:
    for marker in REFERENCE_MARKERS:
        if _segment_after(parts, marker):
            return True
    return False


@dataclass(frozen=True)
class ExistingFolderSourceCandidate:
    case_title: str
    source_bucket: str
    source_title: str
    source_page: str = ""
    source_role: str = "UNKNOWN_SOURCE_ROLE"
    claim_basis: str = "UNKNOWN_CLAIM_BASIS"
    currentness_status: str = "UNKNOWN"
    source_chain_gap: bool = True
    disputed_framing: bool = False
    notes_on_context_dispute: str = ""
    confidence_or_verification_notes: str = "Generated from explicit folder-tree list; source role and claim basis need review."
    local_address: str = ""
    row_id: str = ""

    def to_batch_source(self) -> dict[str, Any]:
        return {
            "source_page": self.source_page or self.source_title,
            "source_title": self.source_title,
            "source_bucket": self.source_bucket,
            "source_role": canonical_source_role(self.source_role),
            "claim_basis": self.claim_basis,
            "currentness_status": self.currentness_status,
            "source_chain_gap": self.source_chain_gap,
            "disputed_framing": self.disputed_framing,
            "confidence_or_verification_notes": self.confidence_or_verification_notes,
            "notes_on_context_dispute": self.notes_on_context_dispute,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExistingFolderProfileCandidate:
    case_title: str
    canonical_name: str
    source_bucket: str = "Profiles"
    source_role: str = "UNKNOWN_SOURCE_ROLE"
    claim_basis: str = "UNKNOWN_CLAIM_BASIS"
    currentness_status: str = "UNKNOWN"
    local_address: str = ""
    global_header_profile: bool = False
    row_id: str = ""

    def to_batch_profile(self) -> dict[str, Any]:
        address = self.local_address or f"Cases/{self.case_title}/Profiles/{self.canonical_name}"
        profile_text = "\n".join(
            [
                f"Name: {self.canonical_name}",
                "Date: UNKNOWN",
                "Text: Existing-folder profile candidate generated from an explicit folder-tree list only.",
                "Identifiers:",
                "- identifier_type: existing_folder_candidate",
                f"  value: {self.canonical_name}",
                "  source_evidenced: false",
                f"Address: {address}",
                "Source: Existing folder tree listing",
            ]
        )
        return {
            "profile_text": profile_text,
            "source_bucket": self.source_bucket,
            "source_role": canonical_source_role(self.source_role),
            "claim_basis": self.claim_basis,
            "currentness_status": self.currentness_status,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExistingFolderPlannerEntry:
    raw_path: str
    normalized_path: str
    entry_type: str
    case_title: str = ""
    source_bucket: str = ""
    title: str = ""
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExistingFolderBatchPreviewWriteResult:
    status: str
    path: str
    warning: str = ""
    schema_version: str = PROFILE_MEDIA_EXISTING_FOLDER_PLANNER_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    file_write_performed: bool = False
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExistingFolderToBatchPlan:
    database_root: str
    requested_case_title: str
    entries: tuple[ExistingFolderPlannerEntry, ...]
    source_candidates: tuple[ExistingFolderSourceCandidate, ...]
    profile_candidates: tuple[ExistingFolderProfileCandidate, ...]
    global_profile_candidates: tuple[ExistingFolderProfileCandidate, ...]
    ignored_entries: tuple[ExistingFolderPlannerEntry, ...]
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_EXISTING_FOLDER_PLANNER_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    @property
    def cases(self) -> tuple[str, ...]:
        return tuple(sorted({item.case_title for item in (*self.source_candidates, *self.profile_candidates) if item.case_title}))

    def batch_preview(self) -> dict[str, Any]:
        case_title = self.requested_case_title or (self.cases[0] if self.cases else "Existing Folder Import Case")
        return {
            "database_root": self.database_root,
            "case_title": case_title,
            "sources": [candidate.to_batch_source() for candidate in self.source_candidates if candidate.case_title == case_title or not self.requested_case_title],
            "profiles": [candidate.to_batch_profile() for candidate in self.profile_candidates if candidate.case_title == case_title or not self.requested_case_title],
            "planner_notes": {
                "schema_version": self.schema_version,
                "dry_run_only": True,
                "source_candidates": len(self.source_candidates),
                "profile_candidates": len(self.profile_candidates),
                "global_profile_candidates": len(self.global_profile_candidates),
                "ignored_entries": len(self.ignored_entries),
                "warnings": list(self.warnings),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        preview = self.batch_preview()
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "database_root": self.database_root,
            "requested_case_title": self.requested_case_title,
            "cases": list(self.cases),
            "case_count": len(self.cases),
            "entry_count": len(self.entries),
            "source_candidate_count": len(self.source_candidates),
            "profile_candidate_count": len(self.profile_candidates),
            "global_profile_candidate_count": len(self.global_profile_candidates),
            "ignored_entry_count": len(self.ignored_entries),
            "batch_preview": preview,
            "batch_preview_source_count": len(preview.get("sources", ())),
            "batch_preview_profile_count": len(preview.get("profiles", ())),
            "entries": [entry.to_dict() for entry in self.entries],
            "source_candidates": [candidate.to_dict() for candidate in self.source_candidates],
            "profile_candidates": [candidate.to_dict() for candidate in self.profile_candidates],
            "global_profile_candidates": [candidate.to_dict() for candidate in self.global_profile_candidates],
            "ignored_entries": [entry.to_dict() for entry in self.ignored_entries],
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }


def build_existing_folder_to_batch_plan(
    folder_tree_lines: Iterable[object],
    *,
    database_root: object = "",
    case_title: object = "",
) -> ExistingFolderToBatchPlan:
    """Build a dry-run batch preview from explicit folder-tree lines only."""

    root = str(database_root or "")
    requested_case = str(case_title or "").strip()
    entries: list[ExistingFolderPlannerEntry] = []
    sources: dict[tuple[str, str, str], ExistingFolderSourceCandidate] = {}
    profiles: dict[tuple[str, str], ExistingFolderProfileCandidate] = {}
    globals_: dict[str, ExistingFolderProfileCandidate] = {}
    ignored: list[ExistingFolderPlannerEntry] = []
    warnings: list[str] = []

    for raw in folder_tree_lines:
        raw_text = str(raw or "").strip()
        if not raw_text:
            continue
        normalized = _normalise_path_text(raw_text)
        parts = _parts(normalized)
        if not parts:
            continue
        source_info = _source_candidate_from_parts(parts, requested_case)
        profile_info = _profile_candidate_from_parts(parts, requested_case)
        if source_info:
            case, bucket, title = source_info
            key = (case, bucket, title)
            entry = ExistingFolderPlannerEntry(raw_text, normalized, "source_candidate", case, bucket, title)
            entries.append(entry)
            sources.setdefault(
                key,
                ExistingFolderSourceCandidate(
                    case_title=case,
                    source_bucket=bucket,
                    source_title=title,
                    source_page="Existing folder tree listing",
                    local_address=f"Cases/{case}/Sources/{bucket}/{title}",
                    row_id=stable_profile_id("existing_source", case, bucket, title),
                ),
            )
            continue
        if profile_info:
            case, name, global_header = profile_info
            if global_header:
                entry = ExistingFolderPlannerEntry(raw_text, normalized, "global_profile_candidate", "", "Profiles", name)
                entries.append(entry)
                globals_.setdefault(
                    name,
                    ExistingFolderProfileCandidate(
                        case_title="",
                        canonical_name=name,
                        global_header_profile=True,
                        local_address=f"Database/Profiles/{name}",
                        row_id=stable_profile_id("existing_global_profile", name),
                    ),
                )
            else:
                entry = ExistingFolderPlannerEntry(raw_text, normalized, "case_profile_candidate", case, "Profiles", name)
                entries.append(entry)
                profiles.setdefault(
                    (case, name),
                    ExistingFolderProfileCandidate(
                        case_title=case,
                        canonical_name=name,
                        local_address=f"Cases/{case}/Profiles/{name}",
                        row_id=stable_profile_id("existing_case_profile", case, name),
                    ),
                )
            continue
        if _is_reference_or_people(parts):
            case, _ = _case_from_parts(parts, requested_case)
            title = parts[-1]
            entry = ExistingFolderPlannerEntry(raw_text, normalized, "reference_or_people_candidate", case, "Reference/People", title)
            entries.append(entry)
            ignored.append(entry)
            continue
        entry = ExistingFolderPlannerEntry(raw_text, normalized, "ignored", warnings=("unrecognized_existing_folder_line",))
        entries.append(entry)
        ignored.append(entry)

    if not sources and not profiles and not globals_:
        warnings.append("no_existing_folder_candidates_found")
    if len({case for case, _, _ in sources.keys()} | {case for case, _ in profiles.keys()}) > 1 and requested_case:
        warnings.append("requested_case_title_used_with_multiple_case_candidates")

    return ExistingFolderToBatchPlan(
        database_root=root,
        requested_case_title=requested_case,
        entries=tuple(entries),
        source_candidates=tuple(sources.values()),
        profile_candidates=tuple(profiles.values()),
        global_profile_candidates=tuple(globals_.values()),
        ignored_entries=tuple(ignored),
        warnings=tuple(warnings),
    )


def load_folder_tree_lines(path: str | Path) -> tuple[str, ...]:
    """Load explicit folder-tree lines from a user-selected text file; no folder scan."""

    return tuple(Path(path).read_text(encoding="utf-8").splitlines())


def write_batch_preview_if_confirmed(
    plan: ExistingFolderToBatchPlan,
    output_path: str | Path,
    *,
    confirmation_phrase: str = "",
) -> ExistingFolderBatchPreviewWriteResult:
    """Optionally write the standalone preview JSON when explicitly confirmed."""

    path = Path(output_path)
    if confirmation_phrase != PROFILE_MEDIA_EXISTING_FOLDER_BATCH_WRITE_CONFIRMATION:
        return ExistingFolderBatchPreviewWriteResult(
            status="blocked_confirmation_required",
            path=str(path),
            warning="batch preview writing requires WRITE_EXISTING_FOLDER_BATCH_PREVIEW",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.batch_preview(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ExistingFolderBatchPreviewWriteResult(status="batch_preview_written", path=str(path), file_write_performed=True)


def render_existing_folder_plan_text(plan: ExistingFolderToBatchPlan) -> str:
    payload = plan.to_dict()
    lines = [
        "Profile/Media Existing Folder Import Plan",
        "Status: dry_run_preview",
        f"Database root: {plan.database_root or '(not configured)'}",
        f"Requested case title: {plan.requested_case_title or '(auto from listing)'}",
        f"Cases: {payload['case_count']}",
        f"Source candidates: {payload['source_candidate_count']}",
        f"Case profile candidates: {payload['profile_candidate_count']}",
        f"Global profile candidates: {payload['global_profile_candidate_count']}",
        f"Ignored/reference entries: {payload['ignored_entry_count']}",
        "Folder scan performed: False",
        "Folder creation performed: False",
        "Folder move performed: False",
        "Folder rename performed: False",
        "File copy performed: False",
        f"File write performed: {plan.file_write_performed}",
        "Media download performed: False",
        "Automatic classification performed: False",
        "Sensitive identifier inference performed: False",
        "",
        "Sources:",
    ]
    if plan.source_candidates:
        for candidate in plan.source_candidates[:25]:
            lines.append(f"- {candidate.case_title} > {candidate.source_bucket} > {candidate.source_title} [{candidate.source_role} / {candidate.claim_basis}]")
        if len(plan.source_candidates) > 25:
            lines.append(f"- ... {len(plan.source_candidates) - 25} more")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Profiles:")
    if plan.profile_candidates:
        for candidate in plan.profile_candidates[:25]:
            lines.append(f"- {candidate.case_title} > {candidate.canonical_name} [{candidate.source_role} / {candidate.claim_basis}]")
        if len(plan.profile_candidates) > 25:
            lines.append(f"- ... {len(plan.profile_candidates) - 25} more")
    else:
        lines.append("- none")
    if plan.global_profile_candidates:
        lines.append("")
        lines.append("Global header profile candidates, not auto-linked to a case:")
        for candidate in plan.global_profile_candidates[:25]:
            lines.append(f"- {candidate.canonical_name}")
        if len(plan.global_profile_candidates) > 25:
            lines.append(f"- ... {len(plan.global_profile_candidates) - 25} more")
    if plan.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)
