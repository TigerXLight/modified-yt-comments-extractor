from __future__ import annotations

import tempfile
from pathlib import Path

from evidence_movement_approval import EvidenceMovementCollisionPolicy, EvidenceMovementMode
from evidence_database_operator_workflow import (
    DatabaseOperatorWorkflowStatus,
    build_database_migration_operator_preview,
    execute_database_migration_operator_preview,
    propose_database_taxonomy_path,
    scan_temp_evidence_database_tree,
)


def test_scan_temp_database_tree_and_preview_safe_copy() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "incoming" / "story.txt"
        source.parent.mkdir()
        source.write_text("source evidence", encoding="utf-8")
        scan = scan_temp_evidence_database_tree(root)
        assert scan.row_count == 1
        assert scan.broad_scan_performed is False
        taxonomy = propose_database_taxonomy_path(
            database_name="Source Review",
            category_parts=("Articles", "Manual Review"),
            month_label="August 2026",
            publisher="Example Publisher",
            item_label="Story",
        )
        preview = build_database_migration_operator_preview(
            root=root,
            scan_row=scan.rows[0],
            taxonomy_path=taxonomy,
        )
        assert preview.status == DatabaseOperatorWorkflowStatus.PREVIEW_READY
        assert preview.automatic_classification is False
        assert preview.protected_attribute_inference_performed is False
        assert preview.old_new_path_history
        assert not (root / preview.proposed_relative_path).exists()

        executed = execute_database_migration_operator_preview(
            preview,
            approved_root=root,
            approved_by_operator=True,
        )
        assert executed.status == DatabaseOperatorWorkflowStatus.EXECUTED_WITH_RECEIPT
        assert executed.movement_receipt.destination_verified is True
        assert executed.completed_evidence_receipt is not None
        assert executed.completed_evidence_receipt.completed_evidence_claimed is True
        assert source.is_file()
        assert (root / preview.proposed_relative_path).is_file()


def test_move_requires_destructive_approval_and_preserves_history() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "incoming" / "move.txt"
        source.parent.mkdir()
        source.write_text("move me", encoding="utf-8")
        scan = scan_temp_evidence_database_tree(root)
        taxonomy = propose_database_taxonomy_path(
            database_name="Source Review",
            category_parts=("Moved",),
            item_label="Move",
        )
        preview = build_database_migration_operator_preview(
            root=root,
            scan_row=scan.rows[0],
            taxonomy_path=taxonomy,
            mode=EvidenceMovementMode.MOVE,
        )
        blocked = execute_database_migration_operator_preview(
            preview,
            approved_root=root,
            approved_by_operator=True,
            destructive_file_move_approved=False,
        )
        assert blocked.status == DatabaseOperatorWorkflowStatus.FAILED_WITH_RECEIPT
        assert "move_requires_destructive_file_move_approval" in blocked.rollback_or_failure_receipt
        assert source.exists()

        moved = execute_database_migration_operator_preview(
            preview,
            approved_root=root,
            approved_by_operator=True,
            destructive_file_move_approved=True,
        )
        assert moved.status == DatabaseOperatorWorkflowStatus.EXECUTED_WITH_RECEIPT
        assert not source.exists()
        assert preview.old_new_path_history[0][0].endswith("move.txt")


def test_collision_and_sensitive_or_automatic_updates_are_rejected_or_receipted() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "incoming" / "story.txt"
        source.parent.mkdir()
        source.write_text("one", encoding="utf-8")
        scan = scan_temp_evidence_database_tree(root)
        taxonomy = propose_database_taxonomy_path(
            database_name="Source Review",
            category_parts=("Articles",),
            item_label="Story",
        )
        preview = build_database_migration_operator_preview(
            root=root,
            scan_row=scan.rows[0],
            taxonomy_path=taxonomy,
        )
        destination = root / preview.proposed_relative_path
        destination.parent.mkdir(parents=True)
        destination.write_text("existing", encoding="utf-8")
        collision = execute_database_migration_operator_preview(
            preview,
            approved_root=root,
            approved_by_operator=True,
            collision_policy=EvidenceMovementCollisionPolicy.FAIL,
        )
        assert collision.status == DatabaseOperatorWorkflowStatus.FAILED_WITH_RECEIPT
        assert "FileExistsError" in collision.rollback_or_failure_receipt or "destination collision" in collision.rollback_or_failure_receipt

        sensitive = propose_database_taxonomy_path(
            database_name="Source Review",
            category_parts=("religion",),
            item_label="Story",
        )
        rejected = build_database_migration_operator_preview(
            root=root,
            scan_row=scan.rows[0],
            taxonomy_path=sensitive,
        )
        assert rejected.status == DatabaseOperatorWorkflowStatus.REJECTED_UNSAFE
        assert "protected_sensitive_dimension_rejected" in rejected.rejection_reasons

        automatic = build_database_migration_operator_preview(
            root=root,
            scan_row=scan.rows[0],
            taxonomy_path=taxonomy,
            automatic_classification=True,
        )
        assert automatic.status == DatabaseOperatorWorkflowStatus.REJECTED_UNSAFE
        assert "automatic_classification_rejected" in automatic.rejection_reasons


if __name__ == "__main__":
    test_scan_temp_database_tree_and_preview_safe_copy()
    test_move_requires_destructive_approval_and_preserves_history()
    test_collision_and_sensitive_or_automatic_updates_are_rejected_or_receipted()
    print("evidence_database_operator_workflow_test.py passed")
