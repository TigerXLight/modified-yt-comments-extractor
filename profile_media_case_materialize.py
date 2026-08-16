"""Explicit case materialization pack for Profile/Media Database mode.

V75U combines the already-guarded workspace, source-intake, profile-intake,
and case-manifest layers into one controlled operation.  The default remains a
planning dry-run.  Real folder creation and metadata-file writing require
execute=True and the exact confirmation phrase MATERIALIZE_PROFILE_MEDIA_CASE.

This module still does not scan folders, move folders, rename folders, copy
media, download media, classify automatically, or infer sensitive identifiers.
It only creates the known Database/Profile/Case folders and writes the JSON/TXT
metadata records that previous V75 stages already planned.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from profile_media_case_manifest import (
    PROFILE_MEDIA_CASE_MANIFEST_CONFIRMATION,
    ProfileMediaCaseManifestPlan,
    apply_case_manifest_plan,
    build_case_manifest_plan,
    render_case_manifest_text,
)
from profile_media_case_workspace import (
    PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION,
    apply_case_workspace_plan,
    build_case_workspace_plan,
)
from profile_media_database import stable_profile_id, utc_now_iso
from profile_media_profile_intake import (
    PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION,
    apply_profile_intake_plan,
    build_profile_intake_plan,
)
from profile_media_source_intake import (
    PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION,
    apply_source_intake_plan,
    build_source_intake_plan,
)

PROFILE_MEDIA_CASE_MATERIALIZE_SCHEMA_VERSION = "profile-media-case-materialize-v75u"
PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION = "MATERIALIZE_PROFILE_MEDIA_CASE"


@dataclass(frozen=True)
class ProfileMediaCaseMaterializePlan:
    """Dry-run or explicitly executable case materialization plan."""

    database_root: str
    case_title: str
    case_root: str
    manifest_plan: ProfileMediaCaseManifestPlan
    source_specs: tuple[dict[str, Any], ...] = ()
    profile_specs: tuple[dict[str, Any], ...] = ()
    plan_id: str = ""
    execute_requested: bool = False
    confirmation_phrase: str = ""
    schema_version: str = PROFILE_MEDIA_CASE_MATERIALIZE_SCHEMA_VERSION
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
        return self.confirmation_phrase == PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["manifest_plan"] = self.manifest_plan.to_dict()
        data["source_count"] = len(self.source_specs)
        data["profile_count"] = len(self.profile_specs)
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["materialize_confirmation"] = PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION
        data["child_confirmations"] = {
            "workspace": PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION,
            "source_intake": PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION,
            "profile_intake": PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION,
            "case_manifest": PROFILE_MEDIA_CASE_MANIFEST_CONFIRMATION,
        }
        return data


@dataclass(frozen=True)
class ProfileMediaCaseMaterializeResult:
    """Result from dry-running or explicitly materializing a case pack."""

    status: str
    plan_id: str
    database_root: str
    case_root: str
    created_directories: tuple[str, ...] = ()
    already_existing_directories: tuple[str, ...] = ()
    written_files: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()
    child_statuses: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_CASE_MATERIALIZE_SCHEMA_VERSION
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
        data["already_existing_directory_count"] = len(self.already_existing_directories)
        data["written_file_count"] = len(self.written_files)
        data["blocked_path_count"] = len(self.blocked_paths)
        return data


def _normalise_specs(items: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None) -> tuple[dict[str, Any], ...]:
    return tuple(dict(item) for item in (items or ()))


def _ensure_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _source_spec_from_plan(plan: Any) -> dict[str, Any]:
    evaluation = plan.source_claim_evaluation
    return {
        "source_page": plan.source_page,
        "source_title": plan.source_title,
        "source_bucket": plan.source_bucket,
        "source_role": evaluation.source_role,
        "claim_basis": evaluation.claim_basis,
        "currentness_status": evaluation.currentness_status,
        "disputed_framing": evaluation.disputed_framing,
        "notes_on_context_dispute": evaluation.notes_on_context_dispute,
        "source_chain_gap": evaluation.source_chain_gap,
        "confidence_or_verification_notes": evaluation.confidence_or_verification_notes,
        "family_or_authority_claim_basis": evaluation.family_or_authority_claim_basis,
        "identity_claim_basis": evaluation.identity_claim_basis,
        "appearance_claim_basis": evaluation.appearance_claim_basis,
        "collaboration_or_corroboration_notes": evaluation.collaboration_or_corroboration_notes,
    }


def _profile_spec_from_plan(plan: Any) -> dict[str, Any]:
    return {
        "profile_text": plan.profile_text,
        "canonical_name": plan.canonical_name,
        "source_bucket": plan.source_bucket,
        "source_role": plan.source_role,
        "claim_basis": plan.claim_basis,
        "currentness_status": plan.currentness_status,
    }


def build_case_materialize_plan(
    *,
    database_root: str,
    case_title: str,
    case_root: str = "",
    source_specs: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
    profile_specs: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
    source_role: Any = "UNKNOWN_SOURCE_ROLE",
    claim_basis: Any = "UNKNOWN_CLAIM_BASIS",
    currentness_status: Any = "UNKNOWN",
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaCaseMaterializePlan:
    """Build a case materialization plan without touching the filesystem."""

    normalised_sources = _normalise_specs(source_specs)
    normalised_profiles = _normalise_specs(profile_specs)
    manifest_plan = build_case_manifest_plan(
        database_root=database_root,
        case_title=case_title,
        case_root=case_root,
        source_specs=normalised_sources,
        profile_specs=normalised_profiles,
        source_role=source_role,
        claim_basis=claim_basis,
        currentness_status=currentness_status,
    )
    plan_id = stable_profile_id(
        "case_materialize",
        manifest_plan.database_root,
        manifest_plan.case_title,
        manifest_plan.case_root,
        manifest_plan.plan_id,
    )
    return ProfileMediaCaseMaterializePlan(
        database_root=manifest_plan.database_root,
        case_title=manifest_plan.case_title,
        case_root=manifest_plan.case_root,
        manifest_plan=manifest_plan,
        source_specs=normalised_sources,
        profile_specs=normalised_profiles,
        plan_id=plan_id,
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
    )


def render_case_materialize_text(plan: ProfileMediaCaseMaterializePlan) -> str:
    """Render the materialization plan for human review."""

    lines = [
        f"Case: {plan.case_title}",
        f"Database root: {plan.database_root}",
        f"Case root: {plan.case_root}",
        f"Source count: {len(plan.source_specs)}",
        f"Profile count: {len(plan.profile_specs)}",
        f"Execute requested: {str(plan.execute_requested).lower()}",
        "Folder creation allowed only with confirmation: MATERIALIZE_PROFILE_MEDIA_CASE",
        "File writes allowed only with confirmation: MATERIALIZE_PROFILE_MEDIA_CASE",
        "Folder scan performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
        "",
        "Case manifest review:",
        render_case_manifest_text(plan.manifest_plan),
    ]
    return "\n".join(lines)


def apply_case_materialize_plan(plan: ProfileMediaCaseMaterializePlan) -> ProfileMediaCaseMaterializeResult:
    """Materialize a case only when the explicit V75U confirmation is present."""

    warnings: list[str] = []
    if not plan.source_specs:
        warnings.append("no_sources_in_materialize_plan")
    if not plan.profile_specs:
        warnings.append("no_profiles_in_materialize_plan")

    if not plan.execute_requested:
        return ProfileMediaCaseMaterializeResult(
            status="planned_dry_run",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            warnings=tuple(warnings + ["dry_run_no_case_materialized"]),
        )
    if not plan.confirmation_valid:
        return ProfileMediaCaseMaterializeResult(
            status="blocked_confirmation_required",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            warnings=tuple(warnings + [f"confirmation_phrase_must_equal:{PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION}"]),
        )

    database_root = Path(plan.database_root)
    case_root = Path(plan.case_root)
    if not _ensure_under_root(case_root, database_root):
        return ProfileMediaCaseMaterializeResult(
            status="blocked_case_root_outside_database_root",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            blocked_paths=(str(case_root),),
            warnings=tuple(warnings + ["case_root_must_be_inside_database_root"]),
        )

    created_dirs: list[str] = []
    existing_dirs: list[str] = []
    written_files: list[str] = []
    blocked_paths: list[str] = []
    child_statuses: list[str] = []

    workspace_plan = build_case_workspace_plan(
        database_root=plan.database_root,
        case_title=plan.case_title,
        case_root=plan.case_root,
        execute=True,
        confirmation_phrase=PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION,
    )
    workspace_result = apply_case_workspace_plan(workspace_plan)
    child_statuses.append(f"workspace:{workspace_result.status}")
    created_dirs.extend(workspace_result.created_directories)
    existing_dirs.extend(workspace_result.already_existing_directories)
    blocked_paths.extend(workspace_result.blocked_paths)
    warnings.extend(workspace_result.warnings)
    if workspace_result.status.startswith("blocked"):
        return ProfileMediaCaseMaterializeResult(
            status="blocked_workspace",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            created_directories=tuple(created_dirs),
            already_existing_directories=tuple(existing_dirs),
            written_files=tuple(written_files),
            blocked_paths=tuple(blocked_paths),
            child_statuses=tuple(child_statuses),
            warnings=tuple(warnings),
            folder_creation_performed=bool(created_dirs),
        )

    for source_plan in plan.manifest_plan.source_plans:
        spec = _source_spec_from_plan(source_plan)
        executable_source_plan = build_source_intake_plan(
            database_root=plan.database_root,
            case_title=plan.case_title,
            case_root=plan.case_root,
            source_page=spec["source_page"],
            source_title=spec["source_title"],
            source_bucket=spec["source_bucket"],
            source_role=spec["source_role"],
            claim_basis=spec["claim_basis"],
            currentness_status=spec["currentness_status"],
            disputed_framing=spec["disputed_framing"],
            notes_on_context_dispute=spec["notes_on_context_dispute"],
            source_chain_gap=spec["source_chain_gap"],
            confidence_or_verification_notes=spec["confidence_or_verification_notes"],
            family_or_authority_claim_basis=spec["family_or_authority_claim_basis"],
            identity_claim_basis=spec["identity_claim_basis"],
            appearance_claim_basis=spec["appearance_claim_basis"],
            collaboration_or_corroboration_notes=spec["collaboration_or_corroboration_notes"],
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION,
        )
        source_result = apply_source_intake_plan(executable_source_plan)
        child_statuses.append(f"source:{source_result.status}")
        created_dirs.extend(source_result.created_directories)
        written_files.extend(source_result.written_files)
        blocked_paths.extend(source_result.blocked_paths)
        warnings.extend(source_result.warnings)

    for profile_plan in plan.manifest_plan.profile_plans:
        spec = _profile_spec_from_plan(profile_plan)
        executable_profile_plan = build_profile_intake_plan(
            database_root=plan.database_root,
            case_title=plan.case_title,
            case_root=plan.case_root,
            profile_text=spec["profile_text"],
            canonical_name=spec["canonical_name"],
            source_bucket=spec["source_bucket"],
            source_role=spec["source_role"],
            claim_basis=spec["claim_basis"],
            currentness_status=spec["currentness_status"],
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION,
        )
        profile_result = apply_profile_intake_plan(executable_profile_plan)
        child_statuses.append(f"profile:{profile_result.status}")
        created_dirs.extend(profile_result.created_directories)
        written_files.extend(profile_result.written_files)
        blocked_paths.extend(profile_result.blocked_paths)
        warnings.extend(profile_result.warnings)

    executable_manifest_plan = build_case_manifest_plan(
        database_root=plan.database_root,
        case_title=plan.case_title,
        case_root=plan.case_root,
        source_specs=tuple(_source_spec_from_plan(source_plan) for source_plan in plan.manifest_plan.source_plans),
        profile_specs=tuple(_profile_spec_from_plan(profile_plan) for profile_plan in plan.manifest_plan.profile_plans),
        execute=True,
        confirmation_phrase=PROFILE_MEDIA_CASE_MANIFEST_CONFIRMATION,
    )
    manifest_result = apply_case_manifest_plan(executable_manifest_plan)
    child_statuses.append(f"manifest:{manifest_result.status}")
    written_files.extend(manifest_result.written_files)
    blocked_paths.extend(manifest_result.blocked_paths)
    warnings.extend(manifest_result.warnings)

    blocked_child = any(status.split(":", 1)[-1].startswith("blocked") for status in child_statuses)
    return ProfileMediaCaseMaterializeResult(
        status="blocked_child_operation" if blocked_child else "materialized",
        plan_id=plan.plan_id,
        database_root=plan.database_root,
        case_root=plan.case_root,
        created_directories=tuple(dict.fromkeys(created_dirs)),
        already_existing_directories=tuple(dict.fromkeys(existing_dirs)),
        written_files=tuple(dict.fromkeys(written_files)),
        blocked_paths=tuple(dict.fromkeys(blocked_paths)),
        child_statuses=tuple(child_statuses),
        warnings=tuple(dict.fromkeys(warnings)),
        folder_creation_performed=bool(created_dirs),
        file_write_performed=bool(written_files),
    )


def result_payload(result: ProfileMediaCaseMaterializeResult, *, plan: ProfileMediaCaseMaterializePlan | None = None) -> dict[str, Any]:
    """Return CLI-friendly result payload with optional plan details."""

    payload: dict[str, Any] = result.to_dict()
    if plan is not None:
        payload["plan"] = plan.to_dict()
        payload["plan_text"] = render_case_materialize_text(plan)
    return payload
