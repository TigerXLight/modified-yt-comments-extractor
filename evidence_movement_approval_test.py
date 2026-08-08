from __future__ import annotations

import tempfile
from pathlib import Path

from evidence_movement_approval import (
    EvidenceMovementMode,
    EvidenceMovementStatus,
    build_completed_evidence_receipt,
    build_default_evidence_movement_plan,
    execute_approved_fixture_movement,
    preview_evidence_movement,
)


def test_preview_is_dry_run_and_requires_approval_by_default() -> None:
    preview = preview_evidence_movement(
        old_path="old/source.txt",
        new_path="new/source.txt",
        taxonomy_changes={"category": "reviewed"},
    )
    assert preview.dry_run is True
    assert preview.approval_required is True
    assert preview.status == EvidenceMovementStatus.APPROVAL_REQUIRED
    assert preview.file_movement_performed is False
    assert preview.completed_evidence_claimed is False


def test_approved_fixture_copy_receipt_verifies_hash_and_completion() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        old_path = root / "old" / "source.txt"
        new_path = root / "new" / "source.txt"
        old_path.parent.mkdir()
        old_path.write_text("fixture evidence", encoding="utf-8")
        preview = preview_evidence_movement(
            old_path=str(old_path),
            new_path=str(new_path),
            taxonomy_changes={"category": "reviewed"},
            mode=EvidenceMovementMode.COPY,
            approval_granted=True,
            dry_run=False,
        )
        receipt = execute_approved_fixture_movement(
            preview,
            approval_granted=True,
            fixture_root=str(root),
        )
        assert old_path.is_file()
        assert new_path.is_file()
        assert receipt.destination_verified is True
        assert receipt.hash_before == receipt.hash_after
        completed = build_completed_evidence_receipt(receipt)
        assert completed.verified_artifact_exists is True
        assert completed.completed_evidence_claimed is True


def test_approved_fixture_move_stays_inside_fixture_root() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        old_path = root / "old" / "source.txt"
        new_path = root / "new" / "source.txt"
        old_path.parent.mkdir()
        old_path.write_text("fixture evidence", encoding="utf-8")
        preview = preview_evidence_movement(
            old_path=str(old_path),
            new_path=str(new_path),
            taxonomy_changes={"category": "reviewed"},
            mode=EvidenceMovementMode.MOVE,
            approval_granted=True,
            dry_run=False,
        )
        receipt = execute_approved_fixture_movement(preview, approval_granted=True, fixture_root=str(root))
        assert not old_path.exists()
        assert new_path.exists()
        assert receipt.mode == EvidenceMovementMode.MOVE
        assert receipt.destructive_delete_performed is False


def test_unsafe_sensitive_or_completion_claims_are_rejected() -> None:
    preview = preview_evidence_movement(
        old_path="old/source.txt",
        new_path="new/source.txt",
        taxonomy_changes={"religion": "inferred"},
        approval_granted=True,
        automatic_classification=True,
        completed_evidence_claimed=True,
    )
    assert preview.status == EvidenceMovementStatus.REJECTED_UNSAFE
    assert "automatic_classification_rejected" in preview.rejection_reasons
    assert "completed_evidence_requires_verified_receipt" in preview.rejection_reasons
    assert any(reason.startswith("protected_sensitive_dimension_rejected") for reason in preview.rejection_reasons)


def test_default_plan_is_metadata_only() -> None:
    plan = build_default_evidence_movement_plan()
    assert plan["approval_required"] is True
    assert plan["dry_run_default"] is True
    assert plan["real_user_file_movement_performed"] is False


if __name__ == "__main__":
    test_preview_is_dry_run_and_requires_approval_by_default()
    test_approved_fixture_copy_receipt_verifies_hash_and_completion()
    test_approved_fixture_move_stays_inside_fixture_root()
    test_unsafe_sensitive_or_completion_claims_are_rejected()
    test_default_plan_is_metadata_only()
    print("evidence_movement_approval_test.py passed")
