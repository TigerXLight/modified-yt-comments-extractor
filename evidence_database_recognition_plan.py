from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class DatabaseRecognitionStatus(str, Enum):
    RECOGNIZED = "recognized"
    NEEDS_REVIEW = "needs_review"
    UNKNOWN_LAYOUT = "unknown_layout"
    UNSAFE_FOR_AUTOMATIC_MOVE = "unsafe_for_automatic_move"


class MigrationApprovalStatus(str, Enum):
    PREVIEW_ONLY = "preview_only"
    OPERATOR_APPROVAL_REQUIRED = "operator_approval_required"
    APPROVED_NOT_EXECUTED = "approved_not_executed"
    EXECUTED_WITH_RECEIPT = "executed_with_receipt"
    REJECTED_UNSAFE = "rejected_unsafe"


@dataclass(frozen=True)
class DatabaseTaxonomyPath:
    database_name: str
    category_parts: tuple[str, ...]
    month_label: str | None = None
    publisher: str | None = None
    item_label: str | None = None

    def to_tuple(self) -> tuple[str, ...]:
        parts = ("Database", self.database_name, *self.category_parts)
        if self.month_label:
            parts += (self.month_label,)
        if self.publisher:
            parts += (self.publisher,)
        if self.item_label:
            parts += (self.item_label,)
        return parts

    def to_display_path(self) -> str:
        return " > ".join(self.to_tuple())

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["display_path"] = self.to_display_path()
        return data


@dataclass(frozen=True)
class DatabaseRecognitionPlan:
    root_path_label: str
    status: DatabaseRecognitionStatus
    taxonomy_version_id: str
    recognized_paths: tuple[DatabaseTaxonomyPath, ...] = ()
    unknown_paths: tuple[str, ...] = ()
    review_notes: tuple[str, ...] = ()
    automatic_classification_performed: bool = False
    file_movement_performed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "root_path_label": self.root_path_label,
            "status": self.status.value,
            "taxonomy_version_id": self.taxonomy_version_id,
            "recognized_path_count": len(self.recognized_paths),
            "recognized_paths": [path.to_dict() for path in self.recognized_paths],
            "unknown_paths": list(self.unknown_paths),
            "review_notes": list(self.review_notes),
            "automatic_classification_performed": self.automatic_classification_performed,
            "file_movement_performed": self.file_movement_performed,
        }


@dataclass(frozen=True)
class ClassificationFieldChange:
    field_name: str
    old_value: str
    new_value: str
    reason: str
    source_record_ref: str
    protected_or_sensitive_review_required: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseMigrationPreview:
    preview_id: str
    item_id: str
    from_path: DatabaseTaxonomyPath
    to_path: DatabaseTaxonomyPath
    field_changes: tuple[ClassificationFieldChange, ...]
    approval_status: MigrationApprovalStatus = MigrationApprovalStatus.PREVIEW_ONLY
    affected_folder_count: int = 0
    affected_item_count: int = 1
    old_path_history_preserved: bool = True
    update_receipt_required: bool = True
    automatic_classification_performed: bool = False
    file_movement_performed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "preview_id": self.preview_id,
            "item_id": self.item_id,
            "from_path": self.from_path.to_dict(),
            "to_path": self.to_path.to_dict(),
            "field_changes": [change.to_dict() for change in self.field_changes],
            "approval_status": self.approval_status.value,
            "affected_folder_count": self.affected_folder_count,
            "affected_item_count": self.affected_item_count,
            "old_path_history_preserved": self.old_path_history_preserved,
            "update_receipt_required": self.update_receipt_required,
            "automatic_classification_performed": self.automatic_classification_performed,
            "file_movement_performed": self.file_movement_performed,
        }

    def is_safe_preview_only(self) -> bool:
        return (
            self.approval_status == MigrationApprovalStatus.PREVIEW_ONLY
            and self.old_path_history_preserved
            and self.update_receipt_required
            and not self.automatic_classification_performed
            and not self.file_movement_performed
        )


def build_example_terrorism_path(item_label: str = "Example item") -> DatabaseTaxonomyPath:
    return DatabaseTaxonomyPath(
        database_name="Terrorism",
        category_parts=("Actions", "Domestic", "Incitement", "Language", "Threat Fear"),
        month_label="June 2026",
        publisher="BelfastLive",
        item_label=item_label,
    )


def build_example_religion_reclassification_preview() -> DatabaseMigrationPreview:
    old_path = DatabaseTaxonomyPath(
        database_name="Sexual or Gender based",
        category_parts=("Female upon Male", "Actions", "Incitement", "Non-religious or not identified"),
        month_label="June 2026",
        publisher="BelfastLive",
        item_label="Example source item",
    )
    new_path = DatabaseTaxonomyPath(
        database_name="Sexual or Gender based",
        category_parts=("Female upon Male", "Actions", "Incitement", "Religious identity"),
        month_label="June 2026",
        publisher="BelfastLive",
        item_label="Example source item",
    )
    return DatabaseMigrationPreview(
        preview_id="migration_preview_religion_field_v1",
        item_id="example_source_item",
        from_path=old_path,
        to_path=new_path,
        field_changes=(
            ClassificationFieldChange(
                field_name="religious_identity_classification",
                old_value="Non-religious or not identified",
                new_value="Religious identity",
                reason="New source record contains reviewable religion field that changes prior unknown/not-identified bucket.",
                source_record_ref="source_record:example",
            ),
        ),
        affected_folder_count=2,
    )


def build_default_database_recognition_plan() -> DatabaseRecognitionPlan:
    return DatabaseRecognitionPlan(
        root_path_label="User-selected evidence database root",
        status=DatabaseRecognitionStatus.NEEDS_REVIEW,
        taxonomy_version_id="user_taxonomy_preview_v1",
        recognized_paths=(
            build_example_terrorism_path("June 2026 - Example article"),
            DatabaseTaxonomyPath(
                database_name="Rape",
                category_parts=("Adults", "Direct", "Non-religious or not identified"),
                month_label="June 2026",
                publisher="Belfast Telegraph",
                item_label="Example court report",
            ),
        ),
        review_notes=(
            "Recognize existing repository tree before proposing updates.",
            "Preview folder/item changes before any approved movement.",
            "Preserve old path history and receipts.",
        ),
    )
