from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from profile_media_case_workspace import (
    PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION,
    apply_case_workspace_plan,
    build_case_workspace_plan,
    render_case_workspace_plan_text,
)


def _assert_no_side_effect_flags(result) -> None:
    assert result.folder_scan_performed is False
    assert result.folder_move_performed is False
    assert result.folder_rename_performed is False
    assert result.file_copy_performed is False
    assert result.automatic_classification_performed is False
    assert result.sensitive_identifier_inference_performed is False


def test_dry_run_does_not_create_workspace() -> None:
    with TemporaryDirectory() as tmp:
        database_root = Path(tmp) / "Database"
        plan = build_case_workspace_plan(database_root=str(database_root), case_title="Example Case")
        result = apply_case_workspace_plan(plan)
        assert result.status == "planned_dry_run"
        assert database_root.exists() is False
        assert result.folder_creation_performed is False
        _assert_no_side_effect_flags(result)


def test_confirmation_required_for_execute() -> None:
    with TemporaryDirectory() as tmp:
        database_root = Path(tmp) / "Database"
        plan = build_case_workspace_plan(
            database_root=str(database_root),
            case_title="Example Case",
            execute=True,
            confirmation_phrase="WRONG",
        )
        result = apply_case_workspace_plan(plan)
        assert result.status == "blocked_confirmation_required"
        assert database_root.exists() is False
        assert result.folder_creation_performed is False
        _assert_no_side_effect_flags(result)


def test_execute_creates_exact_case_workspace_shape() -> None:
    with TemporaryDirectory() as tmp:
        database_root = Path(tmp) / "Database"
        plan = build_case_workspace_plan(
            database_root=str(database_root),
            case_title="Example Case",
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION,
        )
        result = apply_case_workspace_plan(plan)
        assert result.status == "created"
        assert result.folder_creation_performed is True
        _assert_no_side_effect_flags(result)
        expected = [
            database_root / "Profiles",
            database_root / "Cases" / "Example Case" / "Profiles",
            database_root / "Cases" / "Example Case" / "People",
            database_root / "Cases" / "Example Case" / "Sources" / "Articles",
            database_root / "Cases" / "Example Case" / "Sources" / "Social Media" / "Offline",
            database_root / "Cases" / "Example Case" / "Sources" / "Social Media" / "Online",
            database_root / "Cases" / "Example Case" / "Sources" / "Internal Media",
            database_root / "Cases" / "Example Case" / "Reference Extants",
        ]
        for path in expected:
            assert path.is_dir(), path
        assert not (database_root / "Cases" / "Example Case" / "Sources" / "Profiles").exists()


def test_workspace_plan_text_keeps_social_media_nested() -> None:
    with TemporaryDirectory() as tmp:
        plan = build_case_workspace_plan(database_root=str(Path(tmp) / "Database"), case_title="Example Case")
        text = render_case_workspace_plan_text(plan)
        assert "Profiles [global_profiles]" in text
        assert "Cases [cases]" in text
        assert "  Profiles [global_profiles]" in text
        assert "    Example Case [case]" in text
        assert text.index("Cases [cases]") < text.index("Example Case [case]")
        assert text.index("Profiles [global_profiles]") < text.index("Cases [cases]")
        assert "Sources [sources]" in text
        assert "Articles [articles]" in text
        assert "Social Media [social_media]" in text
        assert "Offline [social_media_offline]" in text
        assert "Online [social_media_online]" in text
        assert "Internal Media [internal_media]" in text
        assert "Reference Extants [reference_extants]" in text


if __name__ == "__main__":
    test_dry_run_does_not_create_workspace()
    test_confirmation_required_for_execute()
    test_execute_creates_exact_case_workspace_shape()
    test_workspace_plan_text_keeps_social_media_nested()
    print("profile_media_case_workspace v75t OK")
