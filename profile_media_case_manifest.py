"""Guarded case manifest records for Profile/Media Database mode.

V75T joins the workspace, source-intake, and profile-intake planning layers
into one case-level manifest.  The manifest is an index for a case folder; it
links planned Profiles records to planned Sources records without scanning the
filesystem or treating media as final proof.

The default is dry-run.  Real manifest writing is allowed only when the caller
passes execute=True and the exact confirmation phrase WRITE_CASE_MANIFEST.  This
module does not scan folders, copy media, move or rename folders, download
anything, classify automatically, or infer sensitive identifiers from weak
signals.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from profile_media_case_workspace import build_case_workspace_plan, render_case_workspace_plan_text
from profile_media_database import (
    ClaimBasis,
    CurrentnessStatus,
    MediaBucket,
    ProfileSourceRole,
    normalize_media_bucket,
    stable_profile_id,
    utc_now_iso,
)
from profile_media_profile_intake import (
    ProfileMediaProfileIntakePlan,
    build_profile_intake_plan,
    render_profile_intake_text,
)
from profile_media_source_intake import (
    ProfileMediaSourceIntakePlan,
    build_source_intake_plan,
    coerce_claim_basis,
    coerce_currentness_status,
    coerce_source_role,
    render_source_intake_text,
)

PROFILE_MEDIA_CASE_MANIFEST_SCHEMA_VERSION = "profile-media-case-manifest-v75t"
PROFILE_MEDIA_CASE_MANIFEST_CONFIRMATION = "WRITE_CASE_MANIFEST"
CASE_MANIFEST_JSON = "case_manifest.json"
CASE_MANIFEST_TEXT = "case_manifest.txt"


@dataclass(frozen=True)
class ProfileMediaCaseManifestPlan:
    """Dry-run or explicitly executable case-level manifest plan."""

    database_root: str
    case_title: str
    case_root: str
    manifest_json_path: str
    manifest_text_path: str
    workspace_plan: Any
    source_plans: tuple[ProfileMediaSourceIntakePlan, ...] = ()
    profile_plans: tuple[ProfileMediaProfileIntakePlan, ...] = ()
    plan_id: str = ""
    execute_requested: bool = False
    confirmation_phrase: str = ""
    schema_version: str = PROFILE_MEDIA_CASE_MANIFEST_SCHEMA_VERSION
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
        return self.confirmation_phrase == PROFILE_MEDIA_CASE_MANIFEST_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["workspace_plan"] = self.workspace_plan.to_dict()
        data["source_plans"] = [plan.to_dict() for plan in self.source_plans]
        data["profile_plans"] = [plan.to_dict() for plan in self.profile_plans]
        data["source_count"] = len(self.source_plans)
        data["profile_count"] = len(self.profile_plans)
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["source_buckets"] = sorted({normalize_media_bucket(plan.source_bucket).value for plan in self.source_plans})
        data["profile_names"] = [plan.canonical_name for plan in self.profile_plans]
        return data


@dataclass(frozen=True)
class ProfileMediaCaseManifestResult:
    """Result from applying or dry-running a case manifest plan."""

    status: str
    plan_id: str
    manifest_json_path: str
    manifest_text_path: str
    written_files: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_CASE_MANIFEST_SCHEMA_VERSION
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
        data["written_file_count"] = len(self.written_files)
        data["blocked_path_count"] = len(self.blocked_paths)
        return data


def _ensure_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _normalise_source_specs(source_specs: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None) -> tuple[dict[str, Any], ...]:
    return tuple(dict(spec) for spec in (source_specs or ()))


def _normalise_profile_specs(profile_specs: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None) -> tuple[dict[str, Any], ...]:
    return tuple(dict(spec) for spec in (profile_specs or ()))


def build_case_manifest_plan(
    *,
    database_root: str,
    case_title: str,
    case_root: str = "",
    source_specs: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
    profile_specs: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
    source_role: ProfileSourceRole | str = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    claim_basis: ClaimBasis | str = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    currentness_status: CurrentnessStatus | str = CurrentnessStatus.UNKNOWN,
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaCaseManifestPlan:
    """Build a case manifest plan without touching or scanning the filesystem."""

    workspace_plan = build_case_workspace_plan(database_root=database_root, case_title=case_title, case_root=case_root)
    default_role = coerce_source_role(source_role)
    default_basis = coerce_claim_basis(claim_basis)
    default_currentness = coerce_currentness_status(currentness_status)

    source_plans = []
    for spec in _normalise_source_specs(source_specs):
        source_plans.append(
            build_source_intake_plan(
                database_root=workspace_plan.database_root,
                case_title=workspace_plan.case_title,
                case_root=workspace_plan.case_root,
                source_page=str(spec.get("source_page", "")),
                source_title=str(spec.get("source_title", "")),
                source_bucket=spec.get("source_bucket", MediaBucket.ARTICLES),
                source_role=spec.get("source_role", default_role),
                claim_basis=spec.get("claim_basis", default_basis),
                currentness_status=spec.get("currentness_status", default_currentness),
                disputed_framing=bool(spec.get("disputed_framing", False)),
                notes_on_context_dispute=str(spec.get("notes_on_context_dispute", "")),
                source_chain_gap=bool(spec.get("source_chain_gap", False)),
                confidence_or_verification_notes=str(spec.get("confidence_or_verification_notes", "")),
                family_or_authority_claim_basis=str(spec.get("family_or_authority_claim_basis", "")),
                identity_claim_basis=str(spec.get("identity_claim_basis", "")),
                appearance_claim_basis=str(spec.get("appearance_claim_basis", "")),
                collaboration_or_corroboration_notes=str(spec.get("collaboration_or_corroboration_notes", "")),
            )
        )

    profile_plans = []
    for spec in _normalise_profile_specs(profile_specs):
        profile_plans.append(
            build_profile_intake_plan(
                database_root=workspace_plan.database_root,
                case_title=workspace_plan.case_title,
                case_root=workspace_plan.case_root,
                profile_text=str(spec.get("profile_text", "")),
                canonical_name=str(spec.get("canonical_name", "")),
                source_bucket=spec.get("source_bucket", MediaBucket.ARTICLES),
                source_role=spec.get("source_role", default_role),
                claim_basis=spec.get("claim_basis", default_basis),
                currentness_status=spec.get("currentness_status", default_currentness),
            )
        )

    manifest_json = Path(workspace_plan.case_root) / CASE_MANIFEST_JSON
    manifest_text = Path(workspace_plan.case_root) / CASE_MANIFEST_TEXT
    plan_id = stable_profile_id(
        "case_manifest",
        workspace_plan.database_root,
        workspace_plan.case_title,
        workspace_plan.case_root,
        *(plan.plan_id for plan in source_plans),
        *(plan.plan_id for plan in profile_plans),
    )
    return ProfileMediaCaseManifestPlan(
        database_root=workspace_plan.database_root,
        case_title=workspace_plan.case_title,
        case_root=workspace_plan.case_root,
        manifest_json_path=str(manifest_json),
        manifest_text_path=str(manifest_text),
        workspace_plan=workspace_plan,
        source_plans=tuple(source_plans),
        profile_plans=tuple(profile_plans),
        plan_id=plan_id,
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
    )


def render_case_manifest_text(plan: ProfileMediaCaseManifestPlan) -> str:
    """Render the case manifest plan in an easy-to-read review form."""

    lines = [
        f"Case: {plan.case_title}",
        f"Case root: {plan.case_root}",
        f"Database root: {plan.database_root}",
        f"Manifest JSON: {plan.manifest_json_path}",
        f"Manifest text: {plan.manifest_text_path}",
        f"Source count: {len(plan.source_plans)}",
        f"Profile count: {len(plan.profile_plans)}",
        "Sensitive identifier inference prohibited: true",
        "Sensitive identifiers source-evidenced only: true",
        "Filesystem scan performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "",
        "Case folder structure:",
        render_case_workspace_plan_text(plan.workspace_plan),
    ]
    if plan.source_plans:
        lines.extend(["", "Sources:"])
        for index, source_plan in enumerate(plan.source_plans, start=1):
            lines.extend([f"", f"Source {index}:", render_source_intake_text(source_plan)])
    if plan.profile_plans:
        lines.extend(["", "Profiles:"])
        for index, profile_plan in enumerate(plan.profile_plans, start=1):
            lines.extend([f"", f"Profile {index}:", render_profile_intake_text(profile_plan)])
    return "\n".join(lines)


def _manifest_payload(plan: ProfileMediaCaseManifestPlan) -> dict[str, Any]:
    return {
        "schema_version": PROFILE_MEDIA_CASE_MANIFEST_SCHEMA_VERSION,
        "plan_id": plan.plan_id,
        "created_at_utc": plan.created_at_utc,
        "database_root": plan.database_root,
        "case_title": plan.case_title,
        "case_root": plan.case_root,
        "manifest_json_path": plan.manifest_json_path,
        "manifest_text_path": plan.manifest_text_path,
        "workspace_plan": plan.workspace_plan.to_dict(),
        "sources": [source_plan.to_dict() for source_plan in plan.source_plans],
        "profiles": [profile_plan.to_dict() for profile_plan in plan.profile_plans],
        "source_count": len(plan.source_plans),
        "profile_count": len(plan.profile_plans),
        "source_buckets": sorted({normalize_media_bucket(source_plan.source_bucket).value for source_plan in plan.source_plans}),
        "profile_names": [profile_plan.canonical_name for profile_plan in plan.profile_plans],
        "media_download_performed": False,
        "file_copy_performed": False,
        "folder_move_performed": False,
        "folder_rename_performed": False,
        "folder_scan_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
        "sensitive_identifier_source_evidenced_only": True,
        "weak_sensitive_inference_prohibited": True,
    }


def apply_case_manifest_plan(plan: ProfileMediaCaseManifestPlan) -> ProfileMediaCaseManifestResult:
    """Apply a case manifest plan only when explicitly confirmed."""

    warnings: list[str] = []
    if not plan.source_plans:
        warnings.append("no_sources_in_manifest")
    if not plan.profile_plans:
        warnings.append("no_profiles_in_manifest")
    if not plan.execute_requested:
        return ProfileMediaCaseManifestResult(
            status="planned_dry_run",
            plan_id=plan.plan_id,
            manifest_json_path=plan.manifest_json_path,
            manifest_text_path=plan.manifest_text_path,
            warnings=tuple(warnings + ["dry_run_no_case_manifest_written"]),
        )
    if not plan.confirmation_valid:
        return ProfileMediaCaseManifestResult(
            status="blocked_confirmation_required",
            plan_id=plan.plan_id,
            manifest_json_path=plan.manifest_json_path,
            manifest_text_path=plan.manifest_text_path,
            warnings=tuple(warnings + [f"confirmation_phrase_must_equal:{PROFILE_MEDIA_CASE_MANIFEST_CONFIRMATION}"]),
        )

    case_root = Path(plan.case_root)
    manifest_json = Path(plan.manifest_json_path)
    manifest_text = Path(plan.manifest_text_path)
    blocked: list[str] = []
    for path in (manifest_json, manifest_text):
        if not _ensure_under_root(path, case_root):
            blocked.append(str(path))
    if not case_root.exists():
        return ProfileMediaCaseManifestResult(
            status="blocked_case_root_missing",
            plan_id=plan.plan_id,
            manifest_json_path=plan.manifest_json_path,
            manifest_text_path=plan.manifest_text_path,
            blocked_paths=(str(case_root),),
            warnings=tuple(warnings + ["create_case_workspace_before_manifest_write"]),
        )
    if blocked:
        return ProfileMediaCaseManifestResult(
            status="blocked_path_outside_case",
            plan_id=plan.plan_id,
            manifest_json_path=plan.manifest_json_path,
            manifest_text_path=plan.manifest_text_path,
            blocked_paths=tuple(blocked),
            warnings=tuple(warnings),
        )

    manifest_json.write_text(json.dumps(_manifest_payload(plan), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    manifest_text.write_text(render_case_manifest_text(plan) + "\n", encoding="utf-8", newline="\n")
    return ProfileMediaCaseManifestResult(
        status="updated",
        plan_id=plan.plan_id,
        manifest_json_path=plan.manifest_json_path,
        manifest_text_path=plan.manifest_text_path,
        written_files=(str(manifest_json), str(manifest_text)),
        warnings=tuple(warnings),
        file_write_performed=True,
    )


def result_payload(result: ProfileMediaCaseManifestResult, *, plan: ProfileMediaCaseManifestPlan | None = None) -> dict[str, Any]:
    """Return CLI-friendly result payload with optional manifest plan details."""

    payload: dict[str, Any] = result.to_dict()
    if plan is not None:
        payload["plan"] = plan.to_dict()
        payload["plan_text"] = render_case_manifest_text(plan)
    return payload
