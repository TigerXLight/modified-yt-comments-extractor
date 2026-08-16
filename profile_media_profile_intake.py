"""Guarded profile-intake records for Profile/Media Database mode.

V75S converts the user's profile-text blocks into planned case-local and
global/header profile records.  It preserves the two-level Profiles model:

* Database/Profiles is the global/header collection across cases.
* Case/Profiles contains profile material extracted from that case only.

The default is dry-run.  Real profile-record writing is allowed only when the
caller passes execute=True and the exact confirmation phrase
WRITE_PROFILE_RECORDS.  The module does not scan folders, copy media, move or
rename folders, classify automatically, download anything, or infer sensitive
identifiers from weak signals.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from profile_media_case_workspace import build_case_workspace_plan
from profile_media_database import (
    ClaimBasis,
    CurrentnessStatus,
    MediaBucket,
    ProfileCollectionLevel,
    ProfileRecord,
    ProfileSourceRole,
    build_global_profile_from_case_profile,
    build_manifest,
    build_profile_record,
    normalize_media_bucket,
    parse_profile_text_blocks,
    sanitize_path_part,
    stable_profile_id,
    utc_now_iso,
)
from profile_media_source_intake import coerce_claim_basis, coerce_currentness_status, coerce_source_role

PROFILE_MEDIA_PROFILE_INTAKE_SCHEMA_VERSION = "profile-media-profile-intake-v75s"
PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION = "WRITE_PROFILE_RECORDS"
PROFILE_RECORD_JSON = "profile_record.json"
PROFILE_RECORD_TEXT = "profile_record.txt"


@dataclass(frozen=True)
class ProfileMediaProfileIntakePlan:
    """Dry-run or explicitly executable profile-intake record plan."""

    database_root: str
    case_title: str
    case_root: str
    case_id: str
    canonical_name: str
    profile_text: str
    case_profile: ProfileRecord
    global_profile: ProfileRecord
    case_profile_folder_path: str
    global_profile_folder_path: str
    case_profile_json_path: str
    case_profile_text_path: str
    global_profile_json_path: str
    global_profile_text_path: str
    source_bucket: MediaBucket | str = MediaBucket.ARTICLES
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    plan_id: str = ""
    execute_requested: bool = False
    confirmation_phrase: str = ""
    schema_version: str = PROFILE_MEDIA_PROFILE_INTAKE_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    @property
    def confirmation_valid(self) -> bool:
        return self.confirmation_phrase == PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_bucket"] = normalize_media_bucket(self.source_bucket).value
        data["source_role"] = self.source_role.value
        data["claim_basis"] = self.claim_basis.value
        data["currentness_status"] = self.currentness_status.value
        data["case_profile"] = self.case_profile.to_dict()
        data["global_profile"] = self.global_profile.to_dict()
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["case_identifier_count"] = len(self.case_profile.identifiers)
        data["global_identifier_count"] = len(self.global_profile.identifiers)
        data["parser_warning_count"] = sum(len(block.parser_warnings) for block in self.case_profile.text_blocks)
        data["parser_warnings"] = sorted({warning for block in self.case_profile.text_blocks for warning in block.parser_warnings})
        return data


@dataclass(frozen=True)
class ProfileMediaProfileIntakeResult:
    """Result from applying or dry-running a profile-intake plan."""

    status: str
    plan_id: str
    case_profile_folder_path: str
    global_profile_folder_path: str
    case_profile_json_path: str
    case_profile_text_path: str
    global_profile_json_path: str
    global_profile_text_path: str
    created_directories: tuple[str, ...] = ()
    written_files: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_PROFILE_INTAKE_SCHEMA_VERSION
    folder_creation_performed: bool = False
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_directory_count"] = len(self.created_directories)
        data["written_file_count"] = len(self.written_files)
        data["blocked_path_count"] = len(self.blocked_paths)
        return data


def _ensure_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False



def _is_name_only_block(block: Any) -> bool:
    return bool(block.name) and not block.date and not block.text and not block.identifiers and not block.local_address and not block.source_page


def _merge_name_only_prefix_blocks(blocks: tuple[Any, ...]) -> tuple[Any, ...]:
    """Treat a blank line after `Name:` as visual spacing, not a new record.

    The older generic parser treats blank lines as record separators.  For the
    case/profile intake workflow, users commonly write:

    Name: Example

    Date: ...

    This helper preserves that as one profile entry instead of creating a
    warning-heavy name-only entry.
    """

    if not blocks:
        return ()
    merged: list[Any] = []
    pending_name = ""
    for block in blocks:
        if not merged and not pending_name and _is_name_only_block(block):
            pending_name = block.name
            continue
        if pending_name and not block.name:
            block = replace(block, name=pending_name)
            pending_name = ""
        merged.append(block)
    if pending_name:
        merged.append(blocks[0])
    return tuple(merged)

def _profile_folder_name(name: str) -> str:
    return sanitize_path_part(name or "Unknown Person", fallback="Unknown Person")


def build_profile_intake_plan(
    *,
    database_root: str,
    case_title: str,
    profile_text: str,
    canonical_name: str = "",
    case_root: str = "",
    source_bucket: MediaBucket | str = MediaBucket.ARTICLES,
    source_role: ProfileSourceRole | str = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    claim_basis: ClaimBasis | str = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    currentness_status: CurrentnessStatus | str = CurrentnessStatus.UNKNOWN,
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaProfileIntakePlan:
    """Build a profile-intake plan without touching or scanning the filesystem."""

    workspace_plan = build_case_workspace_plan(database_root=database_root, case_title=case_title, case_root=case_root)
    role = coerce_source_role(source_role)
    basis = coerce_claim_basis(claim_basis)
    currentness = coerce_currentness_status(currentness_status)
    bucket = normalize_media_bucket(source_bucket)
    case_id = stable_profile_id("case", workspace_plan.database_root, workspace_plan.case_title, workspace_plan.case_root)
    blocks = parse_profile_text_blocks(
        profile_text,
        default_source_bucket=bucket.value,
        default_source_role=role,
        default_claim_basis=basis,
        default_currentness_status=currentness,
    )
    blocks = _merge_name_only_prefix_blocks(blocks)
    inferred_name = canonical_name or next((block.name for block in blocks if block.name), "")
    case_profile = build_profile_record(
        canonical_name=inferred_name,
        text_blocks=blocks,
        collection_level=ProfileCollectionLevel.CASE_LOCAL_PROFILES,
        case_id=case_id,
    )
    global_profile = build_global_profile_from_case_profile(case_profile)
    folder_name = _profile_folder_name(case_profile.canonical_name)
    case_profile_folder = Path(workspace_plan.case_root) / "Profiles" / folder_name
    global_profile_folder = Path(workspace_plan.database_root) / "Profiles" / folder_name
    plan_id = stable_profile_id(
        "profile_intake",
        workspace_plan.database_root,
        workspace_plan.case_title,
        case_profile.profile_id,
        global_profile.profile_id,
        profile_text,
    )
    return ProfileMediaProfileIntakePlan(
        database_root=workspace_plan.database_root,
        case_title=workspace_plan.case_title,
        case_root=workspace_plan.case_root,
        case_id=case_id,
        canonical_name=case_profile.canonical_name,
        profile_text=profile_text,
        case_profile=case_profile,
        global_profile=global_profile,
        case_profile_folder_path=str(case_profile_folder),
        global_profile_folder_path=str(global_profile_folder),
        case_profile_json_path=str(case_profile_folder / PROFILE_RECORD_JSON),
        case_profile_text_path=str(case_profile_folder / PROFILE_RECORD_TEXT),
        global_profile_json_path=str(global_profile_folder / PROFILE_RECORD_JSON),
        global_profile_text_path=str(global_profile_folder / PROFILE_RECORD_TEXT),
        source_bucket=bucket,
        source_role=role,
        claim_basis=basis,
        currentness_status=currentness,
        plan_id=plan_id,
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
    )


def render_profile_record_text(record: ProfileRecord, *, heading: str = "Profile") -> str:
    """Render a profile record in the user's easy-to-read profile format."""

    lines = [heading, f"Name: {record.canonical_name or 'UNKNOWN'}", f"Collection: {record.collection_level.value}"]
    if record.case_id:
        lines.append(f"Case ID: {record.case_id}")
    lines.append(f"Profile ID: {record.profile_id}")
    for index, block in enumerate(record.text_blocks, start=1):
        lines.extend(
            [
                "",
                f"Entry {index}:",
                f"Date: {block.date or 'UNKNOWN'}",
                f"Text: {block.text or 'UNKNOWN'}",
                "Identifiers:",
            ]
        )
        if block.identifiers:
            lines.extend(f"- {identifier}" for identifier in block.identifiers)
        else:
            lines.append("- UNKNOWN")
        lines.append(f"Address: {block.local_address or 'UNKNOWN'}")
        lines.append(f"Source: {block.source_page or 'UNKNOWN'}")
        lines.append(f"Source bucket: {block.source_bucket or 'UNKNOWN'}")
        lines.append(f"Source role: {block.source_role.value}")
        lines.append(f"Claim basis: {block.claim_basis.value}")
        lines.append(f"Status: {block.currentness_status.value}")
        lines.append("Sensitive identifier inference prohibited: true")
        lines.append("Sensitive identifiers source-evidenced only: true")
        if block.parser_warnings:
            lines.append("Parser warnings: " + ", ".join(block.parser_warnings))
    return "\n".join(lines)


def _record_payload(record: ProfileRecord, *, plan: ProfileMediaProfileIntakePlan, collection_note: str) -> dict[str, Any]:
    manifest = build_manifest(
        database_root=plan.database_root,
        global_profiles=[plan.global_profile],
        cases=[],
    )
    return {
        "schema_version": PROFILE_MEDIA_PROFILE_INTAKE_SCHEMA_VERSION,
        "collection_note": collection_note,
        "plan_id": plan.plan_id,
        "created_at_utc": plan.created_at_utc,
        "database_root": plan.database_root,
        "case_title": plan.case_title,
        "case_root": plan.case_root,
        "profile": record.to_dict(),
        "manifest_id": manifest.manifest_id,
        "source_bucket": normalize_media_bucket(plan.source_bucket).value,
        "source_role": plan.source_role.value,
        "claim_basis": plan.claim_basis.value,
        "currentness_status": plan.currentness_status.value,
        "file_copy_performed": False,
        "folder_move_performed": False,
        "folder_rename_performed": False,
        "folder_scan_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
        "sensitive_identifier_source_evidenced_only": True,
        "weak_sensitive_inference_prohibited": True,
    }


def apply_profile_intake_plan(plan: ProfileMediaProfileIntakePlan) -> ProfileMediaProfileIntakeResult:
    """Apply a profile-intake plan only when explicitly confirmed."""

    warnings: list[str] = []
    if not plan.canonical_name:
        warnings.append("missing_profile_name")
    if not plan.profile_text.strip():
        warnings.append("missing_profile_text")
    warnings.extend(sorted({warning for block in plan.case_profile.text_blocks for warning in block.parser_warnings}))
    if not plan.execute_requested:
        return ProfileMediaProfileIntakeResult(
            status="planned_dry_run",
            plan_id=plan.plan_id,
            case_profile_folder_path=plan.case_profile_folder_path,
            global_profile_folder_path=plan.global_profile_folder_path,
            case_profile_json_path=plan.case_profile_json_path,
            case_profile_text_path=plan.case_profile_text_path,
            global_profile_json_path=plan.global_profile_json_path,
            global_profile_text_path=plan.global_profile_text_path,
            warnings=tuple(warnings + ["dry_run_no_profile_records_written"]),
        )
    if not plan.confirmation_valid:
        return ProfileMediaProfileIntakeResult(
            status="blocked_confirmation_required",
            plan_id=plan.plan_id,
            case_profile_folder_path=plan.case_profile_folder_path,
            global_profile_folder_path=plan.global_profile_folder_path,
            case_profile_json_path=plan.case_profile_json_path,
            case_profile_text_path=plan.case_profile_text_path,
            global_profile_json_path=plan.global_profile_json_path,
            global_profile_text_path=plan.global_profile_text_path,
            warnings=tuple(warnings + [f"confirmation_phrase_must_equal:{PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION}"]),
        )

    database_root = Path(plan.database_root)
    case_root = Path(plan.case_root)
    profile_paths = [
        Path(plan.case_profile_folder_path),
        Path(plan.global_profile_folder_path),
        Path(plan.case_profile_json_path),
        Path(plan.case_profile_text_path),
        Path(plan.global_profile_json_path),
        Path(plan.global_profile_text_path),
    ]
    blocked = []
    for path in profile_paths:
        if not (_ensure_under_root(path, database_root) or _ensure_under_root(path, case_root)):
            blocked.append(str(path))
    for folder in (Path(plan.case_profile_folder_path), Path(plan.global_profile_folder_path)):
        if folder.exists() and not folder.is_dir():
            blocked.append(str(folder))
    if blocked:
        return ProfileMediaProfileIntakeResult(
            status="blocked_path_outside_database_or_conflict",
            plan_id=plan.plan_id,
            case_profile_folder_path=plan.case_profile_folder_path,
            global_profile_folder_path=plan.global_profile_folder_path,
            case_profile_json_path=plan.case_profile_json_path,
            case_profile_text_path=plan.case_profile_text_path,
            global_profile_json_path=plan.global_profile_json_path,
            global_profile_text_path=plan.global_profile_text_path,
            blocked_paths=tuple(blocked),
            warnings=tuple(warnings),
        )

    created: list[str] = []
    written: list[str] = []
    for folder in (Path(plan.case_profile_folder_path), Path(plan.global_profile_folder_path)):
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            created.append(str(folder))

    payloads = (
        (Path(plan.case_profile_json_path), _record_payload(plan.case_profile, plan=plan, collection_note="case-local profile extracted from this case only")),
        (Path(plan.global_profile_json_path), _record_payload(plan.global_profile, plan=plan, collection_note="global/header profile collection across cases")),
    )
    for path, payload in payloads:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
        written.append(str(path))
    text_payloads = (
        (Path(plan.case_profile_text_path), render_profile_record_text(plan.case_profile, heading="Case-local Profile")),
        (Path(plan.global_profile_text_path), render_profile_record_text(plan.global_profile, heading="Global/Header Profile")),
    )
    for path, payload in text_payloads:
        path.write_text(payload + "\n", encoding="utf-8", newline="\n")
        written.append(str(path))

    return ProfileMediaProfileIntakeResult(
        status="created" if created else "updated",
        plan_id=plan.plan_id,
        case_profile_folder_path=plan.case_profile_folder_path,
        global_profile_folder_path=plan.global_profile_folder_path,
        case_profile_json_path=plan.case_profile_json_path,
        case_profile_text_path=plan.case_profile_text_path,
        global_profile_json_path=plan.global_profile_json_path,
        global_profile_text_path=plan.global_profile_text_path,
        created_directories=tuple(created),
        written_files=tuple(written),
        warnings=tuple(warnings),
        folder_creation_performed=bool(created),
        file_write_performed=True,
    )


def render_profile_intake_text(plan: ProfileMediaProfileIntakePlan) -> str:
    """Render the profile-intake plan in a compact reviewable form."""

    return "\n".join(
        [
            f"Case: {plan.case_title}",
            f"Name: {plan.canonical_name or 'UNKNOWN'}",
            f"Case profile folder: {plan.case_profile_folder_path}",
            f"Global profile folder: {plan.global_profile_folder_path}",
            f"Source bucket: {normalize_media_bucket(plan.source_bucket).value}",
            f"Source role: {plan.source_role.value}",
            f"Claim basis: {plan.claim_basis.value}",
            f"Status: {plan.currentness_status.value}",
            f"Text block count: {len(plan.case_profile.text_blocks)}",
            f"Identifier count: {len(plan.case_profile.identifiers)}",
            "Sensitive identifier inference prohibited: true",
            "Sensitive identifiers source-evidenced only: true",
        ]
    )


def result_payload(result: ProfileMediaProfileIntakeResult, *, plan: ProfileMediaProfileIntakePlan | None = None) -> dict[str, Any]:
    """Return CLI-friendly result payload with optional profile plan details."""

    payload: dict[str, Any] = result.to_dict()
    if plan is not None:
        payload["plan"] = plan.to_dict()
        payload["plan_text"] = render_profile_intake_text(plan)
    return payload
