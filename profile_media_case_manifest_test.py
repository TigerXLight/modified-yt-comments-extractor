from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_case_manifest import (
    PROFILE_MEDIA_CASE_MANIFEST_CONFIRMATION,
    apply_case_manifest_plan,
    build_case_manifest_plan,
    render_case_manifest_text,
)
from profile_media_case_workspace import apply_case_workspace_plan, build_case_workspace_plan, PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION


def _profile_text() -> str:
    return """Name: Example Person
Date: June 2026
Text: Example case-local profile text.
Identifiers:
- Source-stated identifier only
Address: C:\\Cases\\Example\\Sources\\Articles\\Example Article
Source: BelfastLive
"""


def test_case_manifest_dry_run_links_sources_and_profiles() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        plan = build_case_manifest_plan(
            database_root=tmp,
            case_title="Example Case",
            source_specs=(
                {
                    "source_page": "BelfastLive",
                    "source_title": "June 2026 - Example Article",
                    "source_bucket": "Articles",
                    "source_role": "TERTIARY_PROPAGATED_SOURCE",
                    "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
                    "currentness_status": "CURRENT",
                    "source_chain_gap": True,
                },
            ),
            profile_specs=(
                {
                    "profile_text": _profile_text(),
                    "source_bucket": "Articles",
                    "source_role": "TERTIARY_PROPAGATED_SOURCE",
                    "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
                    "currentness_status": "CURRENT",
                },
            ),
        )
        result = apply_case_manifest_plan(plan)
        assert result.status == "planned_dry_run"
        assert result.file_write_performed is False
        assert result.folder_scan_performed is False
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert result.automatic_classification_performed is False
        assert result.sensitive_identifier_inference_performed is False
        payload = plan.to_dict()
        assert payload["source_count"] == 1
        assert payload["profile_count"] == 1
        assert payload["source_buckets"] == ["Articles"]
        assert payload["profile_names"] == ["Example Person"]
        text = render_case_manifest_text(plan)
        assert "Sources:" in text
        assert "Profiles:" in text
        assert "Sensitive identifier inference prohibited: true" in text
        assert "BelfastLive" in text


def test_case_manifest_write_requires_existing_workspace_and_confirmation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        plan = build_case_manifest_plan(
            database_root=tmp,
            case_title="Example Case",
            source_specs=({"source_page": "BelfastLive", "source_bucket": "Articles"},),
            profile_specs=({"profile_text": _profile_text()},),
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_CASE_MANIFEST_CONFIRMATION,
        )
        blocked = apply_case_manifest_plan(plan)
        assert blocked.status == "blocked_case_root_missing"
        assert "create_case_workspace_before_manifest_write" in blocked.warnings

        workspace_plan = build_case_workspace_plan(
            database_root=tmp,
            case_title="Example Case",
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION,
        )
        workspace_result = apply_case_workspace_plan(workspace_plan)
        assert workspace_result.status in {"created", "updated"}

        written = apply_case_manifest_plan(plan)
        assert written.status == "updated"
        assert written.file_write_performed is True
        assert Path(plan.manifest_json_path).exists()
        assert Path(plan.manifest_text_path).exists()
        assert written.folder_scan_performed is False
        assert written.folder_move_performed is False
        assert written.folder_rename_performed is False
        assert written.automatic_classification_performed is False
        assert written.sensitive_identifier_inference_performed is False


def test_case_manifest_blocks_bad_confirmation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        plan = build_case_manifest_plan(
            database_root=tmp,
            case_title="Example Case",
            source_specs=({"source_page": "BelfastLive", "source_bucket": "Articles"},),
            profile_specs=({"profile_text": _profile_text()},),
            execute=True,
            confirmation_phrase="WRONG",
        )
        result = apply_case_manifest_plan(plan)
        assert result.status == "blocked_confirmation_required"
        assert any("WRITE_CASE_MANIFEST" in warning for warning in result.warnings)
        assert result.file_write_performed is False


if __name__ == "__main__":
    test_case_manifest_dry_run_links_sources_and_profiles()
    test_case_manifest_write_requires_existing_workspace_and_confirmation()
    test_case_manifest_blocks_bad_confirmation()
    print("profile_media_case_manifest v75t OK")
