from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from profile_media_database import ClaimBasis, CurrentnessStatus, MediaBucket, ProfileCollectionLevel, ProfileSourceRole
from profile_media_profile_intake import (
    PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION,
    apply_profile_intake_plan,
    build_profile_intake_plan,
    render_profile_intake_text,
    render_profile_record_text,
    result_payload,
)


PROFILE_TEXT = """Name: Example Person

Date: 2026-06-05
Text: Example source text from a source page.
Identifiers:
- Description: Example description
- Clothing: Blue jacket
- Religion: Source-stated only
Address: C:\\Cases\\Example Case\\Sources\\Articles\\Example Article
Source: BelfastLive
"""


def test_profile_intake_dry_run_preserves_two_profile_levels() -> None:
    root = Path(tempfile.mkdtemp(prefix="ytce_v75s_profile_dry_"))
    try:
        plan = build_profile_intake_plan(
            database_root=str(root),
            case_title="Example Case",
            profile_text=PROFILE_TEXT,
            source_bucket=MediaBucket.ARTICLES,
            source_role=ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE,
            claim_basis=ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING,
            currentness_status=CurrentnessStatus.CURRENT,
        )
        result = apply_profile_intake_plan(plan)
        payload = result_payload(result, plan=plan)
        assert result.status == "planned_dry_run"
        assert result.folder_creation_performed is False
        assert result.file_write_performed is False
        assert result.folder_scan_performed is False
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert result.file_copy_performed is False
        assert result.automatic_classification_performed is False
        assert result.sensitive_identifier_inference_performed is False
        assert "Profiles" in plan.case_profile_folder_path
        assert "Profiles" in plan.global_profile_folder_path
        assert "Cases" in plan.case_profile_folder_path
        assert "Cases" not in plan.global_profile_folder_path
        assert plan.case_profile.collection_level == ProfileCollectionLevel.CASE_LOCAL_PROFILES
        assert plan.global_profile.collection_level == ProfileCollectionLevel.GLOBAL_HEADER_PROFILES
        assert len(plan.case_profile.text_blocks) == 1
        assert payload["plan"]["parser_warning_count"] == 0
        assert len(plan.case_profile.identifiers) == 3
        assert payload["plan"]["case_identifier_count"] == 3
        assert "Sensitive identifier inference prohibited: true" in payload["plan_text"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_profile_intake_blocks_unconfirmed_execute() -> None:
    root = Path(tempfile.mkdtemp(prefix="ytce_v75s_profile_block_"))
    try:
        plan = build_profile_intake_plan(database_root=str(root), case_title="Example Case", profile_text=PROFILE_TEXT, execute=True)
        result = apply_profile_intake_plan(plan)
        assert result.status == "blocked_confirmation_required"
        assert result.file_write_performed is False
        assert result.folder_creation_performed is False
        assert any("WRITE_PROFILE_RECORDS" in warning for warning in result.warnings)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_profile_intake_confirmed_write_only_records() -> None:
    root = Path(tempfile.mkdtemp(prefix="ytce_v75s_profile_exec_"))
    try:
        plan = build_profile_intake_plan(
            database_root=str(root),
            case_title="Example Case",
            profile_text=PROFILE_TEXT,
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION,
        )
        result = apply_profile_intake_plan(plan)
        assert result.status == "created"
        assert result.folder_creation_performed is True
        assert result.file_write_performed is True
        assert result.folder_scan_performed is False
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert result.file_copy_performed is False
        assert result.automatic_classification_performed is False
        assert result.sensitive_identifier_inference_performed is False
        assert len(result.written_files) == 4
        case_json = json.loads(Path(plan.case_profile_json_path).read_text(encoding="utf-8"))
        global_json = json.loads(Path(plan.global_profile_json_path).read_text(encoding="utf-8"))
        assert case_json["collection_note"] == "case-local profile extracted from this case only"
        assert global_json["collection_note"] == "global/header profile collection across cases"
        assert case_json["sensitive_identifier_inference_performed"] is False
        assert "Case-local Profile" in Path(plan.case_profile_text_path).read_text(encoding="utf-8")
        assert "Global/Header Profile" in Path(plan.global_profile_text_path).read_text(encoding="utf-8")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_renderers_include_user_format_terms() -> None:
    plan = build_profile_intake_plan(database_root="C:/Database", case_title="Example Case", profile_text=PROFILE_TEXT)
    plan_text = render_profile_intake_text(plan)
    record_text = render_profile_record_text(plan.case_profile)
    assert "Name: Example Person" in record_text
    assert "Date: 2026-06-05" in record_text
    assert "Identifiers:" in record_text
    assert "Address:" in record_text
    assert "Source: BelfastLive" in record_text
    assert "Case profile folder:" in plan_text
    assert "Global profile folder:" in plan_text


if __name__ == "__main__":
    test_profile_intake_dry_run_preserves_two_profile_levels()
    test_profile_intake_blocks_unconfirmed_execute()
    test_profile_intake_confirmed_write_only_records()
    test_renderers_include_user_format_terms()
    print("profile_media_profile_intake v75s OK")
