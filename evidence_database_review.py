from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any

from evidence_database_index import (
    CLASSIFICATION_NOT_EVIDENCED,
    CLASSIFICATION_PROPOSED,
    CLASSIFICATION_REJECTED,
    CLASSIFICATION_SUPERSEDED,
    CLASSIFICATION_UNKNOWN,
    CLASSIFICATION_USER_CONFIRMED,
    EvidenceClassificationValue,
    EvidenceDatabaseRoot,
    EvidenceIndexRecord,
    stable_evidence_id,
)
from evidence_schema import utc_now_iso


EVIDENCE_DATABASE_REVIEW_SCHEMA_VERSION = "evidence-database-review-v1"
EVIDENCE_DATABASE_REVIEW_SCOPE = (
    "local evidence database review workflow metadata only; supplied records only; "
    "no broad folder scanning, no file movement, no automatic classification execution, "
    "no sensitive-attribute inference, no source fetching, no archive access, no media "
    "download, no browser automation, no scraping, no provider calls, no credential access"
)

DECISION_ACCEPT_PROPOSAL = "accept_proposal"
DECISION_REJECT_PROPOSAL = "reject_proposal"
DECISION_MARK_UNKNOWN = "mark_unknown"
DECISION_MARK_NOT_EVIDENCED = "mark_not_evidenced"
DECISION_REQUEST_RECLASSIFICATION = "request_reclassification"

APPLY_RESULT_STATUS_DRY_RUN = "dry_run_not_executed"
APPLY_RESULT_STATUS_REJECTED = "rejected"

ROOT_REGISTRATION_STATUS_READY = "ready"
ROOT_REGISTRATION_STATUS_MISSING_ROOT = "missing_root"
ROOT_REGISTRATION_STATUS_DUPLICATE_ROOT = "duplicate_root"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class EvidenceDatabaseReviewDecisionType(_StringEnum):
    ACCEPT_PROPOSAL = DECISION_ACCEPT_PROPOSAL
    REJECT_PROPOSAL = DECISION_REJECT_PROPOSAL
    MARK_UNKNOWN = DECISION_MARK_UNKNOWN
    MARK_NOT_EVIDENCED = DECISION_MARK_NOT_EVIDENCED
    REQUEST_RECLASSIFICATION = DECISION_REQUEST_RECLASSIFICATION


def _clean(value: object) -> str:
    return str(value or "").strip()


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(item) for key, item in sorted(value.items())}
    return value


def review_stable_json_dumps(data: Any) -> str:
    return json.dumps(_value_for_dict(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class EvidenceDatabaseRootRegistrationDraft:
    root_path: str
    label: str = ""
    taxonomy_version_id: str = ""
    draft_id: str = ""
    user_supplied: bool = True
    root_exists: bool = False
    broad_scan_allowed: bool = False
    dry_run_required: bool = True
    moves_require_explicit_approval: bool = True
    warnings: tuple[str, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["draft_id"] = self.stable_draft_id
        return data

    @property
    def stable_draft_id(self) -> str:
        return self.draft_id or stable_evidence_id(
            "rootdraft",
            self.root_path,
            self.label,
            self.taxonomy_version_id,
        )


@dataclass(frozen=True)
class EvidenceDatabaseRootRegistrationResult:
    status: str
    draft_id: str = ""
    root: EvidenceDatabaseRoot | None = None
    root_id: str = ""
    duplicate_root_id: str = ""
    root_exists: bool = False
    broad_scan_allowed: bool = False
    broad_scan_performed: bool = False
    file_operation_performed: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    @property
    def ok(self) -> bool:
        return self.status == ROOT_REGISTRATION_STATUS_READY

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["ok"] = self.ok
        return data


@dataclass(frozen=True)
class EvidenceDatabaseReviewSession:
    session_id: str
    selected_root_id: str = ""
    taxonomy_version_id: str = ""
    registered_root_ids: tuple[str, ...] = ()
    review_mode: str = "dry_run_review"
    dry_run_only: bool = True
    user_confirmation_required: bool = True
    destructive_actions_enabled: bool = False
    broad_scan_allowed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceDatabasePreviewRequest:
    session_id: str
    root_id: str = ""
    record_ids: tuple[str, ...] = ()
    include_classification_values: tuple[str, ...] = (
        CLASSIFICATION_UNKNOWN,
        CLASSIFICATION_NOT_EVIDENCED,
        CLASSIFICATION_PROPOSED,
        CLASSIFICATION_USER_CONFIRMED,
        CLASSIFICATION_REJECTED,
        CLASSIFICATION_SUPERSEDED,
    )
    supplied_records_only: bool = True
    broad_scan_requested: bool = False
    request_id: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    @property
    def stable_request_id(self) -> str:
        return self.request_id or stable_evidence_id(
            "preview",
            self.session_id,
            self.root_id,
            *self.record_ids,
            *self.include_classification_values,
        )

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["request_id"] = self.stable_request_id
        return data


@dataclass(frozen=True)
class EvidenceDatabasePreviewRow:
    item_id: str
    display_name: str = ""
    classification_value: EvidenceClassificationValue = EvidenceClassificationValue.UNKNOWN
    database_root_id: str = ""
    taxonomy_version_id: str = ""
    placement_proposal_count: int = 0
    reclassification_proposal_count: int = 0
    user_confirmation_required: bool = True
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceDatabasePreviewResult:
    request_id: str
    grouped_record_ids: dict[str, tuple[str, ...]] = field(default_factory=dict)
    rows: tuple[EvidenceDatabasePreviewRow, ...] = ()
    record_count: int = 0
    supplied_records_only: bool = True
    broad_scan_performed: bool = False
    file_operation_performed: bool = False
    warnings: tuple[str, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["group_counts"] = {
            key: len(value)
            for key, value in sorted(self.grouped_record_ids.items())
        }
        return data


@dataclass(frozen=True)
class EvidenceDatabaseReviewDecision:
    decision_type: EvidenceDatabaseReviewDecisionType
    item_id: str
    proposal_id: str = ""
    target_classification_value: EvidenceClassificationValue = EvidenceClassificationValue.UNKNOWN
    note: str = ""
    user_confirmed: bool = False
    decision_id: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    @property
    def stable_decision_id(self) -> str:
        return self.decision_id or stable_evidence_id(
            "decision",
            self.item_id,
            self.proposal_id,
            self.decision_type.value,
            self.target_classification_value.value,
            self.note,
        )

    @property
    def user_confirmation_required(self) -> bool:
        return not self.user_confirmed

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["decision_id"] = self.stable_decision_id
        data["user_confirmation_required"] = self.user_confirmation_required
        return data


@dataclass(frozen=True)
class EvidenceDatabaseApplyPlan:
    plan_id: str
    session_id: str = ""
    decisions: tuple[EvidenceDatabaseReviewDecision, ...] = ()
    dry_run: bool = True
    execute_file_moves: bool = False
    execute_classification_changes: bool = False
    file_operation_performed: bool = False
    destructive_action_not_implemented: bool = True
    user_confirmation_required: bool = True
    warnings: tuple[str, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at_utc": self.created_at_utc,
            "decisions": [decision.to_dict() for decision in self.decisions],
            "destructive_action_not_implemented": self.destructive_action_not_implemented,
            "dry_run": self.dry_run,
            "execute_classification_changes": self.execute_classification_changes,
            "execute_file_moves": self.execute_file_moves,
            "file_operation_performed": self.file_operation_performed,
            "plan_id": self.plan_id,
            "scope": self.scope,
            "session_id": self.session_id,
            "user_confirmation_required": self.user_confirmation_required,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class EvidenceDatabaseApplyResult:
    plan_id: str
    status: str = APPLY_RESULT_STATUS_DRY_RUN
    applied_decision_ids: tuple[str, ...] = ()
    dry_run: bool = True
    applied: bool = False
    file_operations_performed: bool = False
    classification_changes_executed: bool = False
    destructive_action_not_implemented: bool = True
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    scope: str = EVIDENCE_DATABASE_REVIEW_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def build_review_session(
    *,
    selected_root_id: str = "",
    taxonomy_version_id: str = "",
    registered_root_ids: tuple[str, ...] = (),
    session_id: str = "",
) -> EvidenceDatabaseReviewSession:
    return EvidenceDatabaseReviewSession(
        session_id=session_id
        or stable_evidence_id(
            "reviewsession",
            selected_root_id,
            taxonomy_version_id,
            *registered_root_ids,
        ),
        selected_root_id=selected_root_id,
        taxonomy_version_id=taxonomy_version_id,
        registered_root_ids=registered_root_ids,
    )


def _normalize_root_path(value: str) -> str:
    return _clean(value).replace("\\", "/").rstrip("/")


def _root_id_for_path(value: str) -> str:
    return stable_evidence_id("root", _normalize_root_path(value).casefold())


def review_database_root_registration(
    draft: EvidenceDatabaseRootRegistrationDraft,
    *,
    existing_roots: tuple[EvidenceDatabaseRoot, ...] = (),
    path_exists_func: Any | None = None,
) -> EvidenceDatabaseRootRegistrationResult:
    normalized_path = _normalize_root_path(draft.root_path)
    root_id = _root_id_for_path(normalized_path)
    warnings = list(draft.warnings)
    if draft.broad_scan_allowed:
        warnings.append("broad_scan_disabled_for_review_controller")

    existing_by_path = {
        _normalize_root_path(root.root_path).casefold(): root
        for root in existing_roots
    }
    existing_by_id = {root.root_id: root for root in existing_roots}
    duplicate = existing_by_path.get(normalized_path.casefold()) or existing_by_id.get(root_id)
    if duplicate is not None:
        return EvidenceDatabaseRootRegistrationResult(
            status=ROOT_REGISTRATION_STATUS_DUPLICATE_ROOT,
            draft_id=draft.stable_draft_id,
            root_id=root_id,
            duplicate_root_id=duplicate.root_id,
            root_exists=True,
            broad_scan_allowed=False,
            warnings=tuple(warnings),
            errors=("duplicate_database_root",),
        )

    exists_checker = path_exists_func
    if exists_checker is None:
        from pathlib import Path

        exists_checker = lambda path: Path(path).is_dir()
    root_exists = bool(exists_checker(draft.root_path))
    if not root_exists:
        return EvidenceDatabaseRootRegistrationResult(
            status=ROOT_REGISTRATION_STATUS_MISSING_ROOT,
            draft_id=draft.stable_draft_id,
            root_id=root_id,
            root_exists=False,
            broad_scan_allowed=False,
            warnings=tuple(warnings),
            errors=("database_root_missing_or_not_directory",),
        )

    root = EvidenceDatabaseRoot(
        root_id=root_id,
        root_path=normalized_path,
        label=draft.label,
        taxonomy_version_id=draft.taxonomy_version_id,
        dry_run_required=True,
        moves_require_explicit_approval=True,
        broad_scan_allowed=False,
        notes="Registered through review controller metadata only; no scan performed.",
    )
    return EvidenceDatabaseRootRegistrationResult(
        status=ROOT_REGISTRATION_STATUS_READY,
        draft_id=draft.stable_draft_id,
        root=root,
        root_id=root.root_id,
        root_exists=True,
        broad_scan_allowed=False,
        broad_scan_performed=False,
        file_operation_performed=False,
        warnings=tuple(warnings),
    )


def review_session_with_registered_root(
    session: EvidenceDatabaseReviewSession,
    registration: EvidenceDatabaseRootRegistrationResult,
) -> EvidenceDatabaseReviewSession:
    if not registration.ok or not registration.root_id:
        return session
    existing = tuple(item for item in session.registered_root_ids if item)
    if registration.root_id in existing:
        registered = existing
    else:
        registered = existing + (registration.root_id,)
    return EvidenceDatabaseReviewSession(
        session_id=session.session_id,
        selected_root_id=registration.root_id,
        taxonomy_version_id=(
            registration.root.taxonomy_version_id if registration.root else session.taxonomy_version_id
        ),
        registered_root_ids=registered,
        review_mode=session.review_mode,
        dry_run_only=True,
        user_confirmation_required=True,
        destructive_actions_enabled=False,
        broad_scan_allowed=False,
        created_at_utc=session.created_at_utc,
        scope=session.scope,
    )


def build_empty_preview_result(
    request: EvidenceDatabasePreviewRequest,
    *,
    warnings: tuple[str, ...] = (),
) -> EvidenceDatabasePreviewResult:
    return EvidenceDatabasePreviewResult(
        request_id=request.stable_request_id,
        grouped_record_ids={value.value: () for value in EvidenceClassificationValue},
        rows=(),
        record_count=0,
        supplied_records_only=True,
        broad_scan_performed=False,
        file_operation_performed=False,
        warnings=warnings,
    )


def build_preview_result_from_records(
    request: EvidenceDatabasePreviewRequest,
    records: tuple[EvidenceIndexRecord, ...],
    *,
    warnings: tuple[str, ...] = (),
) -> EvidenceDatabasePreviewResult:
    allowed_ids = set(request.record_ids)
    include_values = set(request.include_classification_values)
    rows: list[EvidenceDatabasePreviewRow] = []
    grouped: dict[str, list[str]] = {value.value: [] for value in EvidenceClassificationValue}
    for record in records:
        item_id = preview_record_id(record)
        if allowed_ids and item_id not in allowed_ids:
            continue
        classification_value = record.classification_state.classification_value
        if classification_value.value not in include_values:
            continue
        grouped.setdefault(classification_value.value, []).append(item_id)
        row_warnings: list[str] = []
        if record.classification_state.sensitive_dimensions_present:
            row_warnings.append("sensitive_dimensions_require_review")
        if record.classification_state.user_confirmation_required:
            row_warnings.append("user_confirmation_required")
        rows.append(
            EvidenceDatabasePreviewRow(
                item_id=item_id,
                display_name=record.identity.display_name,
                classification_value=classification_value,
                database_root_id=record.database_root_id,
                taxonomy_version_id=record.taxonomy_version_id,
                placement_proposal_count=len(record.placement_proposals),
                reclassification_proposal_count=len(record.reclassification_proposals),
                user_confirmation_required=record.classification_state.user_confirmation_required,
                warnings=tuple(row_warnings),
            )
        )
    grouped_record_ids = {
        key: tuple(sorted(value))
        for key, value in sorted(grouped.items())
    }
    return EvidenceDatabasePreviewResult(
        request_id=request.stable_request_id,
        grouped_record_ids=grouped_record_ids,
        rows=tuple(sorted(rows, key=lambda row: (row.classification_value.value, row.item_id))),
        record_count=len(rows),
        supplied_records_only=True,
        broad_scan_performed=False,
        file_operation_performed=False,
        warnings=warnings,
    )


def build_non_executing_apply_plan(
    *,
    session_id: str,
    decisions: tuple[EvidenceDatabaseReviewDecision, ...] = (),
    plan_id: str = "",
    warnings: tuple[str, ...] = (),
) -> EvidenceDatabaseApplyPlan:
    return EvidenceDatabaseApplyPlan(
        plan_id=plan_id
        or stable_evidence_id(
            "applyplan",
            session_id,
            *(decision.stable_decision_id for decision in decisions),
        ),
        session_id=session_id,
        decisions=decisions,
        dry_run=True,
        execute_file_moves=False,
        execute_classification_changes=False,
        file_operation_performed=False,
        destructive_action_not_implemented=True,
        user_confirmation_required=any(
            decision.user_confirmation_required for decision in decisions
        ),
        warnings=warnings,
    )


def build_dry_run_apply_result(plan: EvidenceDatabaseApplyPlan) -> EvidenceDatabaseApplyResult:
    return EvidenceDatabaseApplyResult(
        plan_id=plan.plan_id,
        status=APPLY_RESULT_STATUS_DRY_RUN,
        applied_decision_ids=tuple(
            decision.stable_decision_id
            for decision in plan.decisions
            if decision.user_confirmed
        ),
        dry_run=True,
        applied=False,
        file_operations_performed=False,
        classification_changes_executed=False,
        destructive_action_not_implemented=True,
        warnings=(
            "dry_run_only_no_changes_executed",
            "file_movement_not_implemented",
        ),
    )


def preview_record_id(record: EvidenceIndexRecord) -> str:
    return record.identity.item_id
