from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


EVIDENCE_MOVEMENT_APPROVAL_SCHEMA_VERSION = "evidence_movement_approval_v1"


class EvidenceMovementMode(str, Enum):
    COPY = "copy"
    MOVE = "move"


class EvidenceMovementStatus(str, Enum):
    PREVIEW_ONLY = "preview_only"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED_NOT_EXECUTED = "approved_not_executed"
    EXECUTED_WITH_RECEIPT = "executed_with_receipt"
    REJECTED_UNSAFE = "rejected_unsafe"


SENSITIVE_TOKENS = (
    "religion",
    "ethnicity",
    "nationality",
    "politics",
    "protected_attribute",
    "race",
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


def _stable_json(data: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(data), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _is_sensitive_dimension(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(token in lowered for token in SENSITIVE_TOKENS)


@dataclass(frozen=True)
class EvidenceMovementPreview:
    movement_id: str
    old_path: str
    new_path: str
    mode: EvidenceMovementMode
    taxonomy_changes: Mapping[str, str]
    approval_required: bool = True
    dry_run: bool = True
    status: EvidenceMovementStatus = EvidenceMovementStatus.PREVIEW_ONLY
    old_path_history_preserved: bool = True
    rollback_no_delete_note: str = "Source path is preserved in history; destructive delete requires separate approval."
    automatic_classification: bool = False
    completed_evidence_claimed: bool = False
    file_movement_performed: bool = False
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = EVIDENCE_MOVEMENT_APPROVAL_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceMovementReceipt:
    receipt_id: str
    movement_id: str
    old_path_name: str
    new_path_name: str
    mode: EvidenceMovementMode
    hash_before: str
    hash_after: str
    destination_verified: bool
    old_path_history_preserved: bool = True
    movement_performed: bool = False
    completed_evidence_receipt_generated: bool = False
    completed_evidence_claimed: bool = False
    approved_by_operator: bool = False
    destructive_delete_performed: bool = False
    schema_version: str = EVIDENCE_MOVEMENT_APPROVAL_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CompletedEvidenceReceipt:
    receipt_id: str
    movement_receipt_id: str
    artifact_name: str
    verified_sha256: str
    verified_artifact_exists: bool
    completed_evidence_claimed: bool
    user_review_required: bool = True
    automatic_classification: bool = False
    schema_version: str = EVIDENCE_MOVEMENT_APPROVAL_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def preview_evidence_movement(
    *,
    old_path: str,
    new_path: str,
    taxonomy_changes: Mapping[str, str] | None = None,
    mode: EvidenceMovementMode = EvidenceMovementMode.COPY,
    dry_run: bool = True,
    approval_granted: bool = False,
    automatic_classification: bool = False,
    completed_evidence_claimed: bool = False,
) -> EvidenceMovementPreview:
    changes = dict(taxonomy_changes or {})
    reasons: list[str] = []
    if not approval_granted:
        reasons.append("operator_approval_required")
    if automatic_classification:
        reasons.append("automatic_classification_rejected")
    if completed_evidence_claimed:
        reasons.append("completed_evidence_requires_verified_receipt")
    for key in changes:
        if _is_sensitive_dimension(key):
            reasons.append(f"protected_sensitive_dimension_rejected:{key}")
    status = EvidenceMovementStatus.PREVIEW_ONLY
    if reasons:
        status = EvidenceMovementStatus.APPROVAL_REQUIRED
    if any(reason.startswith("protected_sensitive") or reason.endswith("rejected") for reason in reasons):
        status = EvidenceMovementStatus.REJECTED_UNSAFE
    return EvidenceMovementPreview(
        movement_id="movement_preview_" + _sha16((old_path, new_path, changes, mode.value)),
        old_path=str(old_path),
        new_path=str(new_path),
        mode=mode,
        taxonomy_changes=changes,
        approval_required=not approval_granted,
        dry_run=dry_run,
        status=status,
        automatic_classification=automatic_classification,
        completed_evidence_claimed=completed_evidence_claimed,
        rejection_reasons=tuple(reasons),
    )


def execute_approved_fixture_movement(
    preview: EvidenceMovementPreview,
    *,
    approval_granted: bool,
    fixture_root: str,
) -> EvidenceMovementReceipt:
    root = Path(fixture_root).resolve()
    old_path = Path(preview.old_path).resolve()
    new_path = Path(preview.new_path).resolve()
    if not approval_granted:
        raise ValueError("operator approval is required before fixture movement execution")
    if preview.status == EvidenceMovementStatus.REJECTED_UNSAFE:
        raise ValueError("unsafe movement preview cannot be executed")
    if root not in old_path.parents and old_path != root:
        raise ValueError("old path must stay inside the supplied fixture root")
    if root not in new_path.parents and new_path != root:
        raise ValueError("new path must stay inside the supplied fixture root")
    if not old_path.is_file():
        raise FileNotFoundError("fixture old path does not exist")
    before = _sha256_file(old_path)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    if preview.mode == EvidenceMovementMode.MOVE:
        shutil.move(str(old_path), str(new_path))
    else:
        shutil.copy2(str(old_path), str(new_path))
    after = _sha256_file(new_path)
    return EvidenceMovementReceipt(
        receipt_id="movement_receipt_" + _sha16((preview.movement_id, before, after)),
        movement_id=preview.movement_id,
        old_path_name=old_path.name,
        new_path_name=new_path.name,
        mode=preview.mode,
        hash_before=before,
        hash_after=after,
        destination_verified=new_path.is_file() and before == after,
        movement_performed=True,
        approved_by_operator=True,
    )


def build_completed_evidence_receipt(
    movement_receipt: EvidenceMovementReceipt,
) -> CompletedEvidenceReceipt:
    verified = (
        movement_receipt.destination_verified
        and movement_receipt.hash_before == movement_receipt.hash_after
        and bool(movement_receipt.hash_after)
    )
    return CompletedEvidenceReceipt(
        receipt_id="completed_evidence_receipt_" + _sha16(movement_receipt.to_dict()),
        movement_receipt_id=movement_receipt.receipt_id,
        artifact_name=movement_receipt.new_path_name,
        verified_sha256=movement_receipt.hash_after,
        verified_artifact_exists=verified,
        completed_evidence_claimed=verified,
    )


def build_default_evidence_movement_plan() -> dict[str, Any]:
    preview = preview_evidence_movement(
        old_path="fixture_old/source.txt",
        new_path="fixture_new/source.txt",
        taxonomy_changes={
            "category": "reviewed_source",
            "publisher": "operator_confirmed_publisher",
        },
        approval_granted=False,
    )
    return {
        "schema_version": EVIDENCE_MOVEMENT_APPROVAL_SCHEMA_VERSION,
        "plan_id": "evidence_movement_plan_" + _sha16(preview.to_dict()),
        "preview": preview.to_dict(),
        "movement_receipts": [],
        "completed_evidence_receipts": [],
        "approval_required": True,
        "dry_run_default": True,
        "fixture_tested_only": True,
        "real_user_file_movement_performed": False,
    }


def evidence_movement_plan_to_json(plan: Mapping[str, Any]) -> str:
    return _stable_json(plan, pretty=True)
