from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_case_materialize import (
    PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION,
    apply_case_materialize_plan,
    build_case_materialize_plan,
    result_payload,
)


def _source_spec() -> dict[str, object]:
    return {
        "source_page": "BelfastLive",
        "source_title": "June 2026 - Example Article",
        "source_bucket": "Articles",
        "source_role": "TERTIARY_PROPAGATED_SOURCE",
        "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
        "currentness_status": "CURRENT",
        "source_chain_gap": True,
        "confidence_or_verification_notes": "Agency wording not independently traced.",
    }


def _profile_spec() -> dict[str, object]:
    return {
        "profile_text": "Name: Example Person\nDate: June 2026\nText: Source-stated profile note.\nIdentifiers:\n- source-stated descriptor\nAddress: C:/Cases/Example\nSource: BelfastLive",
        "source_bucket": "Articles",
        "source_role": "TERTIARY_PROPAGATED_SOURCE",
        "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
        "currentness_status": "CURRENT",
    }


def test_dry_run_does_not_create_root() -> None:
    with tempfile.TemporaryDirectory() as td:
        database_root = Path(td) / "Profile Media DB"
        plan = build_case_materialize_plan(
            database_root=str(database_root),
            case_title="Example Case",
            source_specs=(_source_spec(),),
            profile_specs=(_profile_spec(),),
        )
        result = apply_case_materialize_plan(plan)
        assert result.status == "planned_dry_run"
        assert result.folder_creation_performed is False
        assert result.file_write_performed is False
        assert not database_root.exists()
        payload = result_payload(result, plan=plan)
        assert payload["plan"]["source_count"] == 1
        assert "Case manifest review" in payload["plan_text"]


def test_execute_requires_exact_materialize_confirmation() -> None:
    with tempfile.TemporaryDirectory() as td:
        database_root = Path(td) / "Profile Media DB"
        plan = build_case_materialize_plan(
            database_root=str(database_root),
            case_title="Example Case",
            source_specs=(_source_spec(),),
            profile_specs=(_profile_spec(),),
            execute=True,
            confirmation_phrase="WRONG",
        )
        result = apply_case_materialize_plan(plan)
        assert result.status == "blocked_confirmation_required"
        assert result.folder_creation_performed is False
        assert not database_root.exists()


def test_execute_materializes_workspace_sources_profiles_and_manifest() -> None:
    with tempfile.TemporaryDirectory() as td:
        database_root = Path(td) / "Profile Media DB"
        plan = build_case_materialize_plan(
            database_root=str(database_root),
            case_title="Example Case",
            source_specs=(_source_spec(),),
            profile_specs=(_profile_spec(),),
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION,
        )
        result = apply_case_materialize_plan(plan)
        assert result.status == "materialized"
        assert result.folder_creation_performed is True
        assert result.file_write_performed is True
        assert result.folder_scan_performed is False
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert result.file_copy_performed is False
        assert result.media_download_performed is False
        assert result.automatic_classification_performed is False
        assert result.sensitive_identifier_inference_performed is False
        assert Path(plan.case_root).is_dir()
        assert (Path(plan.case_root) / "case_manifest.json").is_file()
        assert (Path(plan.case_root) / "Sources" / "Articles" / "June 2026 - Example Article" / "source_claim_evaluation.json").is_file()
        assert (Path(plan.case_root) / "Profiles" / "Example Person" / "profile_record.json").is_file()
        assert (database_root / "Profiles" / "Example Person" / "profile_record.json").is_file()
        manifest = json.loads((Path(plan.case_root) / "case_manifest.json").read_text(encoding="utf-8"))
        assert manifest["source_count"] == 1
        assert manifest["profile_count"] == 1
        assert manifest["folder_scan_performed"] is False
        assert manifest["sensitive_identifier_inference_performed"] is False


def test_execute_blocks_case_root_outside_database_root() -> None:
    with tempfile.TemporaryDirectory() as td:
        database_root = Path(td) / "Profile Media DB"
        outside = Path(td) / "Outside Case Root"
        plan = build_case_materialize_plan(
            database_root=str(database_root),
            case_title="Example Case",
            case_root=str(outside),
            source_specs=(_source_spec(),),
            profile_specs=(_profile_spec(),),
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION,
        )
        result = apply_case_materialize_plan(plan)
        assert result.status == "blocked_case_root_outside_database_root"
        assert result.folder_creation_performed is False
        assert not outside.exists()


def main() -> None:
    test_dry_run_does_not_create_root()
    test_execute_requires_exact_materialize_confirmation()
    test_execute_materializes_workspace_sources_profiles_and_manifest()
    test_execute_blocks_case_root_outside_database_root()
    print("profile_media_case_materialize v75u OK")


if __name__ == "__main__":
    main()
