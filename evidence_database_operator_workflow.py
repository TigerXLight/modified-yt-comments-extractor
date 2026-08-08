from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from evidence_database_recognition_plan import DatabaseTaxonomyPath
from evidence_movement_approval import (
    CompletedEvidenceReceipt,
    EvidenceMovementCollisionPolicy,
    EvidenceMovementMode,
    EvidenceMovementPreview,
    EvidenceMovementReceipt,
    build_completed_evidence_receipt,
    build_evidence_movement_approval_token,
    execute_approved_evidence_movement,
    preview_evidence_movement,
)


EVIDENCE_DATABASE_OPERATOR_WORKFLOW_SCHEMA_VERSION = "evidence_database_operator_workflow_v1"


class DatabaseOperatorWorkflowStatus(str, Enum):
    SCANNED = "scanned"
    PREVIEW_READY = "preview_ready"
    APPROVAL_REQUIRED = "approval_required"
    EXECUTED_WITH_RECEIPT = "executed_with_receipt"
    REJECTED_UNSAFE = "rejected_unsafe"
    FAILED_WITH_RECEIPT = "failed_with_receipt"


SENSITIVE_TOKENS = (
    "religion",
    "ethnicity",
    "nationality",
    "politics",
    "race",
    "protected_attribute",
    "gender_identity",
)


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
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(value: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(value), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(value), sort_keys=True, separators=(",", ":"))


def _sha16(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:16]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_part(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", ".", " "} else "_" for ch in str(value or "").strip())
    return safe.strip() or "unknown"


def _contains_sensitive(value: Any) -> bool:
    text = _stable_json(value).lower()
    return any(token in text for token in SENSITIVE_TOKENS)


@dataclass(frozen=True)
class EvidenceDatabaseScanRow:
    row_id: str
    file_name: str
    relative_parent: str
    sha256: str
    size_bytes: int
    review_status: str = "USER_REVIEW_REQUIRED"
    file_checked_in_temp_fixture: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceDatabaseOperatorScanResult:
    scan_id: str
    root_label: str
    rows: tuple[EvidenceDatabaseScanRow, ...]
    status: DatabaseOperatorWorkflowStatus = DatabaseOperatorWorkflowStatus.SCANNED
    broad_scan_performed: bool = False
    temp_fixture_only: bool = True
    schema_version: str = EVIDENCE_DATABASE_OPERATOR_WORKFLOW_SCHEMA_VERSION

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["row_count"] = self.row_count
        return data


@dataclass(frozen=True)
class EvidenceDatabaseMigrationOperatorPreview:
    preview_id: str
    source_row_id: str
    source_file_name: str
    proposed_taxonomy_path: DatabaseTaxonomyPath
    proposed_relative_path: str
    movement_preview: EvidenceMovementPreview
    old_new_path_history: tuple[tuple[str, str], ...]
    approval_required: bool = True
    automatic_classification: bool = False
    protected_attribute_inference_performed: bool = False
    status: DatabaseOperatorWorkflowStatus = DatabaseOperatorWorkflowStatus.PREVIEW_READY
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = EVIDENCE_DATABASE_OPERATOR_WORKFLOW_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceDatabaseOperatorExecutionResult:
    execution_id: str
    status: DatabaseOperatorWorkflowStatus
    preview: EvidenceDatabaseMigrationOperatorPreview
    movement_receipt: EvidenceMovementReceipt
    completed_evidence_receipt: CompletedEvidenceReceipt | None = None
    rollback_or_failure_receipt: str = ""
    temp_fixture_only: bool = True
    real_user_evidence_moved: bool = False
    automatic_classification: bool = False
    protected_attribute_inference_performed: bool = False
    schema_version: str = EVIDENCE_DATABASE_OPERATOR_WORKFLOW_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def scan_temp_evidence_database_tree(root: str | Path) -> EvidenceDatabaseOperatorScanResult:
    root_path = Path(root).resolve()
    rows: list[EvidenceDatabaseScanRow] = []
    for path in sorted(root_path.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root_path)
        rows.append(
            EvidenceDatabaseScanRow(
                row_id="evidence_database_scan_row_" + _sha16(relative.as_posix()),
                file_name=path.name,
                relative_parent=relative.parent.as_posix(),
                sha256=_sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )
    return EvidenceDatabaseOperatorScanResult(
        scan_id="evidence_database_operator_scan_" + _sha16([row.to_dict() for row in rows]),
        root_label=root_path.name,
        rows=tuple(rows),
    )


def propose_database_taxonomy_path(
    *,
    database_name: str,
    category_parts: Sequence[str],
    month_label: str = "",
    publisher: str = "",
    item_label: str = "",
) -> DatabaseTaxonomyPath:
    return DatabaseTaxonomyPath(
        database_name=_safe_part(database_name),
        category_parts=tuple(_safe_part(part) for part in category_parts),
        month_label=_safe_part(month_label) if month_label else None,
        publisher=_safe_part(publisher) if publisher else None,
        item_label=_safe_part(item_label) if item_label else None,
    )


def build_database_migration_operator_preview(
    *,
    root: str | Path,
    scan_row: EvidenceDatabaseScanRow,
    taxonomy_path: DatabaseTaxonomyPath,
    mode: EvidenceMovementMode = EvidenceMovementMode.COPY,
    automatic_classification: bool = False,
) -> EvidenceDatabaseMigrationOperatorPreview:
    root_path = Path(root).resolve()
    source_path = root_path / scan_row.relative_parent / scan_row.file_name
    proposed_relative = Path(*taxonomy_path.to_tuple()).joinpath(scan_row.file_name).as_posix()
    destination_path = root_path / proposed_relative
    taxonomy_changes: Mapping[str, str] = {
        "database_name": taxonomy_path.database_name,
        "category_path": " > ".join(taxonomy_path.category_parts),
        "month_label": taxonomy_path.month_label or "",
        "publisher": taxonomy_path.publisher or "",
        "item_label": taxonomy_path.item_label or "",
    }
    rejection_reasons: list[str] = []
    if automatic_classification:
        rejection_reasons.append("automatic_classification_rejected")
    if _contains_sensitive(taxonomy_changes):
        rejection_reasons.append("protected_sensitive_dimension_rejected")
    movement = preview_evidence_movement(
        old_path=str(source_path),
        new_path=str(destination_path),
        taxonomy_changes=taxonomy_changes,
        mode=mode,
        approval_granted=not rejection_reasons,
        automatic_classification=automatic_classification,
    )
    status = DatabaseOperatorWorkflowStatus.REJECTED_UNSAFE if rejection_reasons else DatabaseOperatorWorkflowStatus.PREVIEW_READY
    return EvidenceDatabaseMigrationOperatorPreview(
        preview_id="evidence_database_migration_preview_" + _sha16((scan_row.to_dict(), taxonomy_path.to_dict(), mode.value)),
        source_row_id=scan_row.row_id,
        source_file_name=scan_row.file_name,
        proposed_taxonomy_path=taxonomy_path,
        proposed_relative_path=proposed_relative,
        movement_preview=movement,
        old_new_path_history=((scan_row.relative_parent + "/" + scan_row.file_name, proposed_relative),),
        automatic_classification=automatic_classification,
        protected_attribute_inference_performed=False,
        status=status,
        rejection_reasons=tuple(rejection_reasons),
    )


def execute_database_migration_operator_preview(
    preview: EvidenceDatabaseMigrationOperatorPreview,
    *,
    approved_root: str | Path,
    approved_by_operator: bool,
    collision_policy: EvidenceMovementCollisionPolicy = EvidenceMovementCollisionPolicy.FAIL,
    destructive_file_move_approved: bool = False,
) -> EvidenceDatabaseOperatorExecutionResult:
    token = build_evidence_movement_approval_token(
        preview.movement_preview,
        approved_by_operator=approved_by_operator,
        operator_label="database-operator",
        destructive_file_move_approved=destructive_file_move_approved,
    )
    movement_receipt = execute_approved_evidence_movement(
        preview.movement_preview,
        approval_token=token,
        approved_root=str(approved_root),
        collision_policy=collision_policy,
    )
    completed = build_completed_evidence_receipt(movement_receipt) if movement_receipt.destination_verified else None
    status = (
        DatabaseOperatorWorkflowStatus.EXECUTED_WITH_RECEIPT
        if movement_receipt.destination_verified
        else DatabaseOperatorWorkflowStatus.FAILED_WITH_RECEIPT
    )
    return EvidenceDatabaseOperatorExecutionResult(
        execution_id="evidence_database_operator_execution_" + _sha16((preview.to_dict(), movement_receipt.to_dict())),
        status=status,
        preview=preview,
        movement_receipt=movement_receipt,
        completed_evidence_receipt=completed,
        rollback_or_failure_receipt=movement_receipt.failure_reason,
    )


def evidence_database_operator_workflow_to_json(value: Any) -> str:
    return _stable_json(value, pretty=True)
