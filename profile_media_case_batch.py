"""Batch case intake for Profile/Media Database mode.

V75V lets a user describe a complete case in one small JSON payload, including
multiple source records and multiple profile records.  It is a convenience layer
above the guarded V75U materialization pack.

The default remains dry-run.  Real folder creation and metadata writes require
execute=True and the exact confirmation phrase APPLY_PROFILE_MEDIA_BATCH_CASE.
Even in execute mode, this module does not scan folders, move folders, rename
folders, copy media, download media, classify automatically, or infer sensitive
identifiers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from profile_media_case_materialize import (
    PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION,
    ProfileMediaCaseMaterializePlan,
    apply_case_materialize_plan,
    build_case_materialize_plan,
    render_case_materialize_text,
)
from profile_media_database import stable_profile_id, utc_now_iso

PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION = "profile-media-case-batch-v75v"
PROFILE_MEDIA_CASE_BATCH_CONFIRMATION = "APPLY_PROFILE_MEDIA_BATCH_CASE"

_FORBIDDEN_OPERATION_FIELDS = (
    "scan_folders",
    "folder_scan",
    "move_folders",
    "folder_move",
    "rename_folders",
    "folder_rename",
    "copy_media",
    "file_copy",
    "download_media",
    "media_download",
    "automatic_classification",
    "auto_classify",
    "infer_sensitive_identifiers",
    "sensitive_identifier_inference",
)

_SOURCE_DEFAULTS: dict[str, Any] = {
    "source_page": "",
    "source_title": "",
    "source_bucket": "Articles",
    "source_role": "UNKNOWN_SOURCE_ROLE",
    "claim_basis": "UNKNOWN_CLAIM_BASIS",
    "currentness_status": "UNKNOWN",
    "disputed_framing": False,
    "notes_on_context_dispute": "",
    "source_chain_gap": False,
    "confidence_or_verification_notes": "",
    "family_or_authority_claim_basis": "",
    "identity_claim_basis": "",
    "appearance_claim_basis": "",
    "collaboration_or_corroboration_notes": "",
}

_PROFILE_DEFAULTS: dict[str, Any] = {
    "profile_text": "",
    "canonical_name": "",
    "source_bucket": "Articles",
    "source_role": "UNKNOWN_SOURCE_ROLE",
    "claim_basis": "UNKNOWN_CLAIM_BASIS",
    "currentness_status": "UNKNOWN",
}


@dataclass(frozen=True)
class ProfileMediaCaseBatchPlan:
    """A JSON-driven dry-run or explicitly executable case batch plan."""

    database_root: str
    case_title: str
    case_root: str
    source_specs: tuple[dict[str, Any], ...]
    profile_specs: tuple[dict[str, Any], ...]
    materialize_plan: ProfileMediaCaseMaterializePlan
    plan_id: str = ""
    execute_requested: bool = False
    confirmation_phrase: str = ""
    schema_version: str = PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    forbidden_operation_warnings: tuple[str, ...] = ()

    @property
    def confirmation_valid(self) -> bool:
        return self.confirmation_phrase == PROFILE_MEDIA_CASE_BATCH_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["materialize_plan"] = self.materialize_plan.to_dict()
        data["source_count"] = len(self.source_specs)
        data["profile_count"] = len(self.profile_specs)
        data["confirmation_required"] = self.execute_requested
        data["confirmation_valid"] = self.confirmation_valid
        data["batch_confirmation"] = PROFILE_MEDIA_CASE_BATCH_CONFIRMATION
        data["materialize_confirmation"] = PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION
        data["forbidden_operation_warning_count"] = len(self.forbidden_operation_warnings)
        return data


@dataclass(frozen=True)
class ProfileMediaCaseBatchResult:
    """Result from applying a JSON-driven case batch plan."""

    status: str
    plan_id: str
    database_root: str
    case_root: str
    child_status: str = ""
    created_directories: tuple[str, ...] = ()
    already_existing_directories: tuple[str, ...] = ()
    written_files: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION
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


def load_case_batch_json(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 case batch JSON file."""

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("case batch JSON root must be an object")
    return payload


def write_demo_case_batch_json(path: str | Path, *, database_root: str = "", case_title: str = "Example Case") -> str:
    """Write a safe demo batch JSON file for CLI smoke tests."""

    payload = build_demo_case_batch_payload(database_root=database_root, case_title=case_title)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target)


def build_demo_case_batch_payload(*, database_root: str = "", case_title: str = "Example Case") -> dict[str, Any]:
    """Return a representative two-source/two-profile batch payload."""

    return {
        "schema_version": PROFILE_MEDIA_CASE_BATCH_SCHEMA_VERSION,
        "database_root": database_root,
        "case_title": case_title,
        "sources": [
            {
                "source_page": "BelfastLive",
                "source_title": "June 2026 - Example Article",
                "source_bucket": "Articles",
                "source_role": "TERTIARY_PROPAGATED_SOURCE",
                "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
                "currentness_status": "CURRENT",
                "source_chain_gap": True,
                "confidence_or_verification_notes": "Demo source-chain gap retained for review.",
            },
            {
                "source_page": "Example Search Result",
                "source_title": "Example social media document",
                "source_bucket": "Social Media/Online",
                "source_role": "SECONDARY_WITNESS_SOURCE",
                "claim_basis": "WITNESS_ACCOUNT",
                "currentness_status": "CURRENT",
                "disputed_framing": True,
                "notes_on_context_dispute": "Demo uploader disputes surrounding framing.",
            },
        ],
        "profiles": [
            {
                "profile_text": "Name: Example Person\nDate: 2026-06-05\nText: Demo article mentions Example Person.\nIdentifiers:\n- identifier_type: role\n  value: named person in article\n  source_evidenced: true\nAddress: Cases/Example Case/Sources/Articles/June 2026 - Example Article\nSource: BelfastLive",
                "source_bucket": "Articles",
                "source_role": "TERTIARY_PROPAGATED_SOURCE",
                "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
                "currentness_status": "CURRENT",
            },
            {
                "profile_text": "Name: Second Example\nDate: 2026-06-06\nText: Demo social media source mentions Second Example.\nIdentifiers:\n- identifier_type: source_relation\n  value: appears in social media source\n  source_evidenced: true\nAddress: Cases/Example Case/Sources/Social Media/Online/Example social media document\nSource: Example Search Result",
                "source_bucket": "Social Media/Online",
                "source_role": "SECONDARY_WITNESS_SOURCE",
                "claim_basis": "WITNESS_ACCOUNT",
                "currentness_status": "CURRENT",
            },
        ],
    }


def _list_of_objects(value: Any, field_name: str) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    items: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"{field_name}[{index}] must be an object")
        items.append(dict(item))
    return tuple(items)


def _normalise_source_spec(spec: Mapping[str, Any], defaults: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(_SOURCE_DEFAULTS)
    merged.update({key: value for key, value in defaults.items() if value not in (None, "")})
    merged.update({key: value for key, value in spec.items() if value is not None})
    if not str(merged.get("source_page", "")).strip() and not str(merged.get("source_title", "")).strip():
        merged["source_title"] = "Untitled Source"
    return merged


def _normalise_profile_spec(spec: Mapping[str, Any], defaults: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(_PROFILE_DEFAULTS)
    merged.update({key: value for key, value in defaults.items() if value not in (None, "")})
    merged.update({key: value for key, value in spec.items() if value is not None})
    if not str(merged.get("profile_text", "")).strip() and str(merged.get("canonical_name", "")).strip():
        merged["profile_text"] = f"Name: {str(merged['canonical_name']).strip()}"
    return merged


def find_forbidden_operation_warnings(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Find requested operations that this batch layer intentionally forbids."""

    warnings: list[str] = []
    for field_name in _FORBIDDEN_OPERATION_FIELDS:
        if bool(payload.get(field_name, False)):
            warnings.append(f"forbidden_operation_requested:{field_name}")
    return tuple(warnings)


def normalise_case_batch_payload(
    payload: Mapping[str, Any],
    *,
    database_root: str = "",
    case_title: str = "",
    case_root: str = "",
) -> dict[str, Any]:
    """Normalise case batch JSON into materialization-ready specs."""

    warnings = find_forbidden_operation_warnings(payload)
    chosen_database_root = str(database_root or payload.get("database_root", "")).strip()
    chosen_case_title = str(case_title or payload.get("case_title", "")).strip()
    chosen_case_root = str(case_root or payload.get("case_root", "")).strip()
    if not chosen_database_root:
        raise ValueError("database_root is required in JSON or CLI")
    if not chosen_case_title:
        raise ValueError("case_title is required in JSON or CLI")

    defaults = {
        "source_role": payload.get("source_role", ""),
        "claim_basis": payload.get("claim_basis", ""),
        "currentness_status": payload.get("currentness_status", ""),
    }
    source_specs = tuple(_normalise_source_spec(item, defaults) for item in _list_of_objects(payload.get("sources"), "sources"))
    profile_specs = tuple(_normalise_profile_spec(item, defaults) for item in _list_of_objects(payload.get("profiles"), "profiles"))
    return {
        "database_root": chosen_database_root,
        "case_title": chosen_case_title,
        "case_root": chosen_case_root,
        "source_specs": source_specs,
        "profile_specs": profile_specs,
        "forbidden_operation_warnings": warnings,
    }


def build_case_batch_plan(
    *,
    payload: Mapping[str, Any],
    database_root: str = "",
    case_title: str = "",
    case_root: str = "",
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaCaseBatchPlan:
    """Build a batch case plan without touching the filesystem."""

    normalised = normalise_case_batch_payload(
        payload,
        database_root=database_root,
        case_title=case_title,
        case_root=case_root,
    )
    materialize_plan = build_case_materialize_plan(
        database_root=normalised["database_root"],
        case_title=normalised["case_title"],
        case_root=normalised["case_root"],
        source_specs=normalised["source_specs"],
        profile_specs=normalised["profile_specs"],
        execute=bool(execute),
        confirmation_phrase=PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION if execute else "",
    )
    plan_id = stable_profile_id(
        "case_batch",
        normalised["database_root"],
        normalised["case_title"],
        normalised["case_root"],
        str(len(normalised["source_specs"])),
        str(len(normalised["profile_specs"])),
    )
    return ProfileMediaCaseBatchPlan(
        database_root=materialize_plan.database_root,
        case_title=materialize_plan.case_title,
        case_root=materialize_plan.case_root,
        source_specs=normalised["source_specs"],
        profile_specs=normalised["profile_specs"],
        materialize_plan=materialize_plan,
        plan_id=plan_id,
        execute_requested=bool(execute),
        confirmation_phrase=confirmation_phrase,
        forbidden_operation_warnings=tuple(normalised["forbidden_operation_warnings"]),
    )


def render_case_batch_text(plan: ProfileMediaCaseBatchPlan) -> str:
    """Render a case batch plan for review."""

    lines = [
        f"Case: {plan.case_title}",
        f"Database root: {plan.database_root}",
        f"Case root: {plan.case_root}",
        f"Source count: {len(plan.source_specs)}",
        f"Profile count: {len(plan.profile_specs)}",
        f"Execute requested: {str(plan.execute_requested).lower()}",
        f"Batch confirmation required for execution: {PROFILE_MEDIA_CASE_BATCH_CONFIRMATION}",
        f"Materialization confirmation delegated internally: {PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION}",
        "Folder scan performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
    ]
    if plan.forbidden_operation_warnings:
        lines.append("")
        lines.append("Forbidden operation requests:")
        lines.extend(f"- {warning}" for warning in plan.forbidden_operation_warnings)
    lines.extend(["", "Materialization review:", render_case_materialize_text(plan.materialize_plan)])
    return "\n".join(lines)


def apply_case_batch_plan(plan: ProfileMediaCaseBatchPlan) -> ProfileMediaCaseBatchResult:
    """Apply a batch plan only when execution is explicit and confirmed."""

    warnings: list[str] = list(plan.forbidden_operation_warnings)
    if not plan.source_specs:
        warnings.append("no_sources_in_batch_plan")
    if not plan.profile_specs:
        warnings.append("no_profiles_in_batch_plan")
    if plan.forbidden_operation_warnings:
        return ProfileMediaCaseBatchResult(
            status="blocked_forbidden_operation_requested",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            warnings=tuple(warnings),
        )
    if not plan.execute_requested:
        return ProfileMediaCaseBatchResult(
            status="planned_dry_run",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            warnings=tuple(warnings + ["dry_run_no_batch_materialized"]),
        )
    if not plan.confirmation_valid:
        return ProfileMediaCaseBatchResult(
            status="blocked_confirmation_required",
            plan_id=plan.plan_id,
            database_root=plan.database_root,
            case_root=plan.case_root,
            warnings=tuple(warnings + [f"confirmation_phrase_must_equal:{PROFILE_MEDIA_CASE_BATCH_CONFIRMATION}"]),
        )

    materialize_plan = build_case_materialize_plan(
        database_root=plan.database_root,
        case_title=plan.case_title,
        case_root=plan.case_root,
        source_specs=plan.source_specs,
        profile_specs=plan.profile_specs,
        execute=True,
        confirmation_phrase=PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION,
    )
    materialize_result = apply_case_materialize_plan(materialize_plan)
    child_payload = materialize_result.to_dict()
    return ProfileMediaCaseBatchResult(
        status="batch_materialized" if materialize_result.status == "materialized" else f"child_{materialize_result.status}",
        plan_id=plan.plan_id,
        database_root=plan.database_root,
        case_root=plan.case_root,
        child_status=materialize_result.status,
        created_directories=materialize_result.created_directories,
        already_existing_directories=materialize_result.already_existing_directories,
        written_files=materialize_result.written_files,
        blocked_paths=materialize_result.blocked_paths,
        warnings=tuple(warnings + list(materialize_result.warnings)),
        folder_creation_performed=bool(child_payload.get("folder_creation_performed", False)),
        file_write_performed=bool(child_payload.get("file_write_performed", False)),
    )


def result_payload(result: ProfileMediaCaseBatchResult, *, plan: ProfileMediaCaseBatchPlan | None = None) -> dict[str, Any]:
    """Return CLI-friendly result data with optional plan review."""

    payload: dict[str, Any] = result.to_dict()
    if plan is not None:
        payload["plan"] = plan.to_dict()
        payload["plan_text"] = render_case_batch_text(plan)
    return payload
