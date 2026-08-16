"""Guarded source-intake records for Profile/Media Database mode.

V75R adds per-source intake planning for the case folder layout introduced in
V75Q.  The default is a dry-run plan: no folder scan, no folder move, no folder
rename, no media copy, no automatic classification, and no sensitive identifier
inference.  Real source-intake record writing is allowed only when the caller
passes execute=True and the exact confirmation phrase CREATE_SOURCE_INTAKE_RECORD.

The intake record is intentionally about *media/source management*, not proof
finality.  It records source role, claim basis, current/historical/undated
status, source-chain gaps, disputed framing notes, and verification notes beside
the planned source location.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

from profile_media_database import (
    ClaimBasis,
    CurrentnessStatus,
    MediaBucket,
    ProfileSourceRole,
    SourceClaimEvaluation,
    build_case_folder_layout,
    build_source_claim_evaluation,
    case_source_bucket_path,
    normalize_media_bucket,
    sanitize_path_part,
    stable_profile_id,
    utc_now_iso,
)
from profile_media_case_workspace import build_case_workspace_plan

PROFILE_MEDIA_SOURCE_INTAKE_SCHEMA_VERSION = "profile-media-source-intake-v75r"
PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION = "CREATE_SOURCE_INTAKE_RECORD"
SOURCE_CLAIM_EVALUATION_JSON = "source_claim_evaluation.json"
SOURCE_CLAIM_EVALUATION_TEXT = "source_claim_evaluation.txt"


@dataclass(frozen=True)
class ProfileMediaSourceIntakePlan:
    """Dry-run or explicitly executable per-source intake record plan."""

    database_root: str
    case_title: str
    case_root: str
    source_page: str
    source_bucket: MediaBucket | str
    source_folder_path: str
    source_title: str = ""
    source_folder_name: str = ""
    source_claim_evaluation: SourceClaimEvaluation = field(default_factory=SourceClaimEvaluation)
    manifest_json_path: str = ""
    manifest_text_path: str = ""
    plan_id: str = ""
    execute_requested: bool = False
    confirmation_phrase: str = ""
    schema_version: str = PROFILE_MEDIA_SOURCE_INTAKE_SCHEMA_VERSION
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
        return self.confirmation_phrase == PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_bucket"] = str(normalize_media_bucket(self.source_bucket).value)
        data["source_claim_evaluation"] = self.source_claim_evaluation.to_dict()
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        return data


@dataclass(frozen=True)
class ProfileMediaSourceIntakeResult:
    """Result from applying or dry-running a source-intake plan."""

    status: str
    plan_id: str
    source_folder_path: str
    manifest_json_path: str
    manifest_text_path: str
    created_directories: tuple[str, ...] = ()
    written_files: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_SOURCE_INTAKE_SCHEMA_VERSION
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


def _coerce_enum(enum_type: type, value: Any, default: Any) -> Any:
    if isinstance(value, enum_type):
        return value
    text = str(value or "").strip()
    if not text:
        return default
    try:
        return enum_type(text)
    except Exception:
        pass
    try:
        return enum_type[text]
    except Exception:
        return default


def coerce_source_role(value: Any) -> ProfileSourceRole:
    return _coerce_enum(ProfileSourceRole, value, ProfileSourceRole.UNKNOWN_SOURCE_ROLE)


def coerce_claim_basis(value: Any) -> ClaimBasis:
    return _coerce_enum(ClaimBasis, value, ClaimBasis.UNKNOWN_CLAIM_BASIS)


def coerce_currentness_status(value: Any) -> CurrentnessStatus:
    return _coerce_enum(CurrentnessStatus, value, CurrentnessStatus.UNKNOWN)


def _source_folder_name(source_page: str, source_title: str = "") -> str:
    chosen = source_title or source_page or "Unknown Source"
    return sanitize_path_part(chosen, fallback="Unknown Source")


def _ensure_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def build_source_intake_plan(
    *,
    database_root: str,
    case_title: str,
    source_page: str,
    source_bucket: MediaBucket | str,
    case_root: str = "",
    source_title: str = "",
    source_role: ProfileSourceRole | str = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    claim_basis: ClaimBasis | str = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    currentness_status: CurrentnessStatus | str = CurrentnessStatus.UNKNOWN,
    disputed_framing: bool = False,
    notes_on_context_dispute: str = "",
    source_chain_gap: bool = False,
    confidence_or_verification_notes: str = "",
    family_or_authority_claim_basis: str = "",
    identity_claim_basis: str = "",
    appearance_claim_basis: str = "",
    collaboration_or_corroboration_notes: str = "",
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaSourceIntakePlan:
    """Build a source-intake plan without touching or scanning the filesystem."""

    workspace_plan = build_case_workspace_plan(database_root=database_root, case_title=case_title, case_root=case_root)
    layout = build_case_folder_layout(workspace_plan.case_root)
    bucket = normalize_media_bucket(source_bucket)
    parent = Path(case_source_bucket_path(layout, bucket))
    folder_name = _source_folder_name(source_page=source_page, source_title=source_title)
    source_folder = parent / folder_name
    evaluation = build_source_claim_evaluation(
        source_role=coerce_source_role(source_role),
        claim_basis=coerce_claim_basis(claim_basis),
        currentness_status=coerce_currentness_status(currentness_status),
        disputed_framing=disputed_framing,
        notes_on_context_dispute=notes_on_context_dispute,
        source_chain_gap=source_chain_gap,
        confidence_or_verification_notes=confidence_or_verification_notes,
        family_or_authority_claim_basis=family_or_authority_claim_basis,
        identity_claim_basis=identity_claim_basis,
        appearance_claim_basis=appearance_claim_basis,
        collaboration_or_corroboration_notes=collaboration_or_corroboration_notes,
    )
    plan_id = stable_profile_id(
        "source_intake",
        workspace_plan.database_root,
        workspace_plan.case_title,
        workspace_plan.case_root,
        bucket.value,
        source_page,
        source_title,
        folder_name,
    )
    return ProfileMediaSourceIntakePlan(
        database_root=workspace_plan.database_root,
        case_title=workspace_plan.case_title,
        case_root=workspace_plan.case_root,
        source_page=source_page,
        source_bucket=bucket,
        source_title=source_title,
        source_folder_name=folder_name,
        source_folder_path=str(source_folder),
        source_claim_evaluation=evaluation,
        manifest_json_path=str(source_folder / SOURCE_CLAIM_EVALUATION_JSON),
        manifest_text_path=str(source_folder / SOURCE_CLAIM_EVALUATION_TEXT),
        plan_id=plan_id,
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
    )


def render_source_intake_text(plan: ProfileMediaSourceIntakePlan) -> str:
    """Render the source intake plan in an easy-to-read text form."""

    evaluation = plan.source_claim_evaluation
    lines = [
        f"Case: {plan.case_title}",
        f"Source folder: {plan.source_folder_path}",
        f"Source bucket: {normalize_media_bucket(plan.source_bucket).value}",
        f"Source page: {plan.source_page or 'UNKNOWN'}",
        f"Source title: {plan.source_title or plan.source_folder_name}",
        f"Source role: {evaluation.source_role.value}",
        f"Claim basis: {evaluation.claim_basis.value}",
        f"Status: {evaluation.currentness_status.value}",
        f"Disputed framing: {str(evaluation.disputed_framing).lower()}",
        f"Source-chain gap: {str(evaluation.source_chain_gap).lower()}",
        f"Sensitive identifier inference prohibited: {str(evaluation.weak_sensitive_inference_prohibited).lower()}",
        f"Sensitive identifiers source-evidenced only: {str(evaluation.sensitive_identifier_source_evidenced_only).lower()}",
    ]
    if evaluation.notes_on_context_dispute:
        lines.append(f"Context dispute notes: {evaluation.notes_on_context_dispute}")
    if evaluation.confidence_or_verification_notes:
        lines.append(f"Verification notes: {evaluation.confidence_or_verification_notes}")
    if evaluation.collaboration_or_corroboration_notes:
        lines.append(f"Collaboration/corroboration notes: {evaluation.collaboration_or_corroboration_notes}")
    return "\n".join(lines)


def _manifest_payload(plan: ProfileMediaSourceIntakePlan) -> dict[str, Any]:
    return {
        "schema_version": PROFILE_MEDIA_SOURCE_INTAKE_SCHEMA_VERSION,
        "plan_id": plan.plan_id,
        "created_at_utc": plan.created_at_utc,
        "database_root": plan.database_root,
        "case_title": plan.case_title,
        "case_root": plan.case_root,
        "source_folder_path": plan.source_folder_path,
        "source_bucket": normalize_media_bucket(plan.source_bucket).value,
        "source_page": plan.source_page,
        "source_title": plan.source_title,
        "source_folder_name": plan.source_folder_name,
        "source_claim_evaluation": plan.source_claim_evaluation.to_dict(),
        "media_download_performed": False,
        "file_copy_performed": False,
        "folder_move_performed": False,
        "folder_rename_performed": False,
        "folder_scan_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
    }


def apply_source_intake_plan(plan: ProfileMediaSourceIntakePlan) -> ProfileMediaSourceIntakeResult:
    """Apply a source-intake plan only when explicitly confirmed."""

    warnings: list[str] = []
    if not plan.source_page:
        warnings.append("missing_source_page")
    if normalize_media_bucket(plan.source_bucket) == MediaBucket.CASE_PROFILES:
        warnings.append("case_profiles_are_extracted_profile_outputs_not_original_media")
    if not plan.execute_requested:
        return ProfileMediaSourceIntakeResult(
            status="planned_dry_run",
            plan_id=plan.plan_id,
            source_folder_path=plan.source_folder_path,
            manifest_json_path=plan.manifest_json_path,
            manifest_text_path=plan.manifest_text_path,
            warnings=tuple(warnings + ["dry_run_no_source_intake_written"]),
        )
    if not plan.confirmation_valid:
        return ProfileMediaSourceIntakeResult(
            status="blocked_confirmation_required",
            plan_id=plan.plan_id,
            source_folder_path=plan.source_folder_path,
            manifest_json_path=plan.manifest_json_path,
            manifest_text_path=plan.manifest_text_path,
            warnings=tuple(warnings + [f"confirmation_phrase_must_equal:{PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION}"]),
        )

    case_root = Path(plan.case_root)
    source_folder = Path(plan.source_folder_path)
    manifest_json = Path(plan.manifest_json_path)
    manifest_text = Path(plan.manifest_text_path)
    blocked: list[str] = []
    created: list[str] = []
    written: list[str] = []

    for path in (source_folder, manifest_json, manifest_text):
        if not _ensure_under_root(path, case_root):
            blocked.append(str(path))
    if source_folder.exists() and not source_folder.is_dir():
        blocked.append(str(source_folder))
    if blocked:
        return ProfileMediaSourceIntakeResult(
            status="blocked_path_outside_case_or_conflict",
            plan_id=plan.plan_id,
            source_folder_path=plan.source_folder_path,
            manifest_json_path=plan.manifest_json_path,
            manifest_text_path=plan.manifest_text_path,
            blocked_paths=tuple(blocked),
            warnings=tuple(warnings),
        )

    if not source_folder.exists():
        source_folder.mkdir(parents=True, exist_ok=True)
        created.append(str(source_folder))
    manifest_json.write_text(json.dumps(_manifest_payload(plan), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    manifest_text.write_text(render_source_intake_text(plan) + "\n", encoding="utf-8", newline="\n")
    written.extend((str(manifest_json), str(manifest_text)))
    return ProfileMediaSourceIntakeResult(
        status="created" if created else "updated",
        plan_id=plan.plan_id,
        source_folder_path=plan.source_folder_path,
        manifest_json_path=plan.manifest_json_path,
        manifest_text_path=plan.manifest_text_path,
        created_directories=tuple(created),
        written_files=tuple(written),
        warnings=tuple(warnings),
        folder_creation_performed=bool(created),
        file_write_performed=True,
    )


def result_payload(result: ProfileMediaSourceIntakeResult, *, plan: ProfileMediaSourceIntakePlan | None = None) -> dict[str, Any]:
    """Return CLI-friendly result payload with optional source plan details."""

    payload: dict[str, Any] = result.to_dict()
    if plan is not None:
        payload["plan"] = plan.to_dict()
        payload["plan_text"] = render_source_intake_text(plan)
    return payload
