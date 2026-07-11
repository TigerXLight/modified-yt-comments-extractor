from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Dict, Optional

from evidence_schema import PrimarySourceStatus, SourceRole, utc_now_iso


EVIDENCE_DATABASE_TAXONOMY_SCOPE = (
    "local read-only evidence database taxonomy schema and dry-run metadata only; "
    "no folder scanning, no file movement, no folder creation, no automatic classification, "
    "sensitive inference, source fetching, archive access, media download, browser "
    "automation, GUI, storage/database implementation, or runtime wiring"
)


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ClassificationStatus(_StringEnum):
    UNKNOWN_OR_NOT_IDENTIFIED = "UNKNOWN_OR_NOT_IDENTIFIED"
    KNOWN = "KNOWN"
    PARTIALLY_KNOWN = "PARTIALLY_KNOWN"
    CONFLICTING = "CONFLICTING"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class UserReviewStatus(_StringEnum):
    NOT_REVIEWED = "NOT_REVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class ReclassificationChangeType(_StringEnum):
    UNKNOWN_TO_KNOWN = "UNKNOWN_TO_KNOWN"
    CATEGORY_PATH_CHANGE = "CATEGORY_PATH_CHANGE"
    CLASSIFICATION_CORRECTION = "CLASSIFICATION_CORRECTION"
    ALIAS_NORMALIZATION = "ALIAS_NORMALIZATION"
    NO_CHANGE = "NO_CHANGE"


class DryRunItemStatus(_StringEnum):
    NO_OP = "NO_OP"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFLICT = "CONFLICT"
    MISSING_METADATA = "MISSING_METADATA"
    UNKNOWN_OR_NOT_IDENTIFIED = "UNKNOWN_OR_NOT_IDENTIFIED"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            key: _value_for_dict(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _value_for_dict(item) for key, item in value.items()}
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    return _value_for_dict(instance)


@dataclass(frozen=True)
class DatabaseRootRegistration:
    database_root: str
    database_label: str = ""
    taxonomy_version: str = ""
    registered_at_utc: str = field(default_factory=utc_now_iso)
    last_indexed_at_utc: str = ""
    last_updated_at_utc: str = ""
    default_date_bucket_format: str = ""
    path_separator_policy: str = ""
    case_title_policy: str = ""
    unknown_label_policy: str = "unknown/not identified is valid"
    sensitive_classification_policy: str = (
        "explicit source evidence or user confirmation required"
    )
    dry_run_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class TaxonomyMappingEntry:
    taxonomy_map_id: str
    database_root: str
    path_pattern: str = ""
    dimension_order: Optional[int] = None
    dimension_name: str = ""
    dimension_value: str = ""
    normalization_rule_id: str = ""
    required_review: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ClassificationDimension:
    dimension_name: str
    dimension_value: str = ""
    classification_status: ClassificationStatus = (
        ClassificationStatus.UNKNOWN_OR_NOT_IDENTIFIED
    )
    is_sensitive: bool = False
    explicit_source_evidence_present: bool = False
    user_confirmed: bool = False
    unknown_or_not_identified_is_valid: bool = True
    weak_clue_inference_prohibited: bool = True
    user_approval_required: bool = True
    classification_basis: str = ""
    classification_source_url: str = ""
    classification_source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    classification_source_status: PrimarySourceStatus = (
        PrimarySourceStatus.MANUAL_SOURCE_NOTE
    )
    sensitive_classification_warning: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ReclassificationHistoryRecord:
    history_id: str
    item_id: str
    previous_category_path: str = ""
    new_category_path: str = ""
    suggested_category_path: str = ""
    change_type: ReclassificationChangeType = (
        ReclassificationChangeType.NO_CHANGE
    )
    change_reason: str = ""
    classification_basis: str = ""
    classification_source_url: str = ""
    classification_source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    classification_source_status: PrimarySourceStatus = (
        PrimarySourceStatus.MANUAL_SOURCE_NOTE
    )
    user_review_status: UserReviewStatus = UserReviewStatus.NOT_REVIEWED
    user_reviewed_at_utc: str = ""
    changed_at_utc: str = field(default_factory=utc_now_iso)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ReclassificationSuggestion:
    suggestion_id: str
    item_id: str
    change_type: ReclassificationChangeType
    previous_category_path: str = ""
    suggested_category_path: str = ""
    evidence_basis: str = ""
    classification_source_url: str = ""
    classification_source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    classification_source_status: PrimarySourceStatus = (
        PrimarySourceStatus.MANUAL_SOURCE_NOTE
    )
    source_timestamp: str = ""
    sensitive_classification_warning: str = ""
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    missing_metadata: tuple[str, ...] = field(default_factory=tuple)
    user_review_status: UserReviewStatus = UserReviewStatus.NOT_REVIEWED
    user_reviewed_at_utc: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)
    requires_explicit_user_approval: bool = True
    automatic_action_permitted: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class AliasNormalizationSuggestion:
    suggestion_id: str
    item_id: str = ""
    field_or_dimension_name: str = ""
    current_value: str = ""
    suggested_value: str = ""
    normalization_rule_id: str = ""
    reason: str = ""
    user_review_status: UserReviewStatus = UserReviewStatus.NOT_REVIEWED
    user_reviewed_at_utc: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)
    requires_explicit_user_approval: bool = True
    automatic_action_permitted: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class EvidenceDatabaseItem:
    item_id: str
    database_root: str
    database_label: str = ""
    taxonomy_version: str = ""
    category_path: str = ""
    suggested_category_path: str = ""
    previous_category_path: str = ""
    classification_dimensions: tuple[ClassificationDimension, ...] = field(
        default_factory=tuple
    )
    classification_status: ClassificationStatus = (
        ClassificationStatus.UNKNOWN_OR_NOT_IDENTIFIED
    )
    classification_basis: str = ""
    classification_source_url: str = ""
    classification_source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    classification_source_status: PrimarySourceStatus = (
        PrimarySourceStatus.MANUAL_SOURCE_NOTE
    )
    classification_updated_at_utc: str = ""
    user_review_status: UserReviewStatus = UserReviewStatus.NOT_REVIEWED
    user_reviewed_at_utc: str = ""
    source_outlet: str = ""
    article_or_export_title: str = ""
    event_or_article_date: str = ""
    month_bucket: str = ""
    export_package_id: str = ""
    manifest_path: str = ""
    source_urls: tuple[str, ...] = field(default_factory=tuple)
    archive_urls: tuple[str, ...] = field(default_factory=tuple)
    local_evidence_paths: tuple[str, ...] = field(default_factory=tuple)
    queue_item_ids: tuple[str, ...] = field(default_factory=tuple)
    capture_session_ids: tuple[str, ...] = field(default_factory=tuple)
    indexed_at_utc: str = ""
    last_updated_at_utc: str = ""
    notes: str = ""
    history: tuple[ReclassificationHistoryRecord, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class DryRunItem:
    item_id: str
    status: DryRunItemStatus
    existing_path: str = ""
    parsed_dimensions: tuple[ClassificationDimension, ...] = field(
        default_factory=tuple
    )
    suggested_destination_path: str = ""
    reason_for_suggestion: str = ""
    evidence_basis: str = ""
    sensitive_classification_warning: str = ""
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    missing_metadata: tuple[str, ...] = field(default_factory=tuple)
    unknown_or_not_identified_state: str = ""
    user_action_required: bool = False
    no_op: bool = False
    reclassification_suggestion_id: str = ""
    alias_suggestion_ids: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class DryRunReport:
    report_id: str
    database_root: str
    generated_at_utc: str = field(default_factory=utc_now_iso)
    items: tuple[DryRunItem, ...] = field(default_factory=tuple)
    no_changes_applied: bool = True
    requires_user_review: bool = True
    scope: str = EVIDENCE_DATABASE_TAXONOMY_SCOPE
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "database_root": self.database_root,
            "generated_at_utc": self.generated_at_utc,
            "item_count": len(self.items),
            "items": [_value_for_dict(item) for item in self.items],
            "no_changes_applied": self.no_changes_applied,
            "requires_user_review": self.requires_user_review,
            "scope": self.scope,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class EvidenceDatabaseTaxonomy:
    database_roots: tuple[DatabaseRootRegistration, ...] = field(
        default_factory=tuple
    )
    taxonomy_mappings: tuple[TaxonomyMappingEntry, ...] = field(
        default_factory=tuple
    )
    items: tuple[EvidenceDatabaseItem, ...] = field(default_factory=tuple)
    reclassification_suggestions: tuple[ReclassificationSuggestion, ...] = field(
        default_factory=tuple
    )
    alias_normalization_suggestions: tuple[
        AliasNormalizationSuggestion, ...
    ] = field(default_factory=tuple)
    history_records: tuple[ReclassificationHistoryRecord, ...] = field(
        default_factory=tuple
    )
    dry_run_reports: tuple[DryRunReport, ...] = field(default_factory=tuple)
    scope: str = EVIDENCE_DATABASE_TAXONOMY_SCOPE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope,
            "database_root_count": len(self.database_roots),
            "database_roots": [_value_for_dict(item) for item in self.database_roots],
            "taxonomy_mapping_count": len(self.taxonomy_mappings),
            "taxonomy_mappings": [
                _value_for_dict(item) for item in self.taxonomy_mappings
            ],
            "item_count": len(self.items),
            "items": [_value_for_dict(item) for item in self.items],
            "reclassification_suggestion_count": len(
                self.reclassification_suggestions
            ),
            "reclassification_suggestions": [
                _value_for_dict(item)
                for item in self.reclassification_suggestions
            ],
            "alias_normalization_suggestion_count": len(
                self.alias_normalization_suggestions
            ),
            "alias_normalization_suggestions": [
                _value_for_dict(item)
                for item in self.alias_normalization_suggestions
            ],
            "history_record_count": len(self.history_records),
            "history_records": [
                _value_for_dict(item) for item in self.history_records
            ],
            "dry_run_report_count": len(self.dry_run_reports),
            "dry_run_reports": [
                _value_for_dict(item) for item in self.dry_run_reports
            ],
        }
