from evidence_database_recognition_plan import (
    DatabaseRecognitionStatus,
    MigrationApprovalStatus,
    build_default_database_recognition_plan,
    build_example_religion_reclassification_preview,
    build_example_terrorism_path,
)


def test_database_paths_preserve_user_tree_shape() -> None:
    path = build_example_terrorism_path("June 2026 - Example article")
    display = path.to_display_path()
    assert display.startswith("Database > Terrorism > Actions > Domestic")
    assert "Threat Fear" in display
    assert "BelfastLive" in display


def test_recognition_plan_is_review_not_move() -> None:
    plan = build_default_database_recognition_plan()
    data = plan.to_dict()
    assert plan.status == DatabaseRecognitionStatus.NEEDS_REVIEW
    assert data["automatic_classification_performed"] is False
    assert data["file_movement_performed"] is False
    assert data["recognized_path_count"] >= 2


def test_reclassification_preview_does_not_execute_move() -> None:
    preview = build_example_religion_reclassification_preview()
    data = preview.to_dict()
    assert preview.approval_status == MigrationApprovalStatus.PREVIEW_ONLY
    assert preview.is_safe_preview_only() is True
    assert data["file_movement_performed"] is False
    assert data["automatic_classification_performed"] is False
    assert data["old_path_history_preserved"] is True
    assert data["field_changes"][0]["field_name"] == "religious_identity_classification"


def main() -> None:
    test_database_paths_preserve_user_tree_shape()
    test_recognition_plan_is_review_not_move()
    test_reclassification_preview_does_not_execute_move()
    print("evidence_database_recognition_plan_test: OK")


if __name__ == "__main__":
    main()
