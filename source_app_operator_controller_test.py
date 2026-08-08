from __future__ import annotations

import tempfile
from pathlib import Path

from source_app_operator_controller import (
    build_access_online_asr_preservation_controller_state,
    build_app_operator_controller_state,
    build_archive_media_archivebox_launch_controller_state,
    build_database_movement_controller_state,
    build_local_e2e_total_export_controller_state,
    build_manual_live_smoke_helper_controller_state,
    build_operator_approval_controller_state,
    build_source_url_files_controller_state,
    build_unified_execution_controller_state,
)
from source_operator_approval_gateway import (
    OperatorExecutionAction,
    OperatorExecutionScope,
    build_operator_approval_token,
)


def test_source_url_files_controller_exposes_expected_app_state() -> None:
    state = build_source_url_files_controller_state()

    assert state["url_enter_accepts_source"] is True
    assert state["resolved_title_row_available"] is True
    assert state["image_icon_state"] is True
    assert state["video_audio_icon_state"] is True
    assert state["archive_org_icon_state"] is True
    assert state["archive_today_icon_state"] is True
    assert state["comments_source_dropdown_state"] == "enabled"
    assert state["livechat_source_dropdown_state"] == "enabled"
    assert state["comments_screenshot_tick"] is True
    assert state["livechat_screenshot_tick"] is True
    assert state["files_hierarchy_pinned"] is True
    assert state["clear_editor_deletes_file"] is False
    assert state["transcript_replacement_deletes_previous"] is False
    assert state["audio_playback_requires_transcript"] is False
    assert state["validation_errors"] == []


def test_operator_approval_controller_blocks_unapproved_and_allows_local_temp() -> None:
    blocked = build_operator_approval_controller_state()
    assert blocked["summary"]["blocked_count"] == blocked["summary"]["action_count"]
    assert "external_network" in blocked["required_approval_flags"]
    assert "user_evidence" in blocked["required_approval_flags"]
    assert "subprocess" in blocked["required_approval_flags"]
    assert blocked["asr_readiness_state"] == "readiness_only_no_asr_run"

    token = build_operator_approval_token(
        actions=(OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,),
        scope=OperatorExecutionScope.LOCAL_TEMP,
        approved_by_operator=True,
        approval_note="fixture test",
    )
    approved = build_operator_approval_controller_state(
        token=token,
        requested_scope=OperatorExecutionScope.LOCAL_TEMP,
    )
    row = next(row for row in approved["approval_preview_rows"] if row["action"] == "browser_local_capture")
    assert row["allowed_to_execute"] is True


def test_unified_execution_controller_preview_and_local_temp_modes() -> None:
    preview = build_unified_execution_controller_state(preview_only=True)
    assert preview["preview_mode"] is True
    assert preview["status"] == "blocked"

    with tempfile.TemporaryDirectory() as tmp:
        executed = build_unified_execution_controller_state(output_root=tmp, preview_only=False)
        assert executed["approved_local_temp_execution"] is True
        assert executed["status"] == "completed"
        assert executed["artifact_paths"]
        assert executed["hashes"]


def test_local_e2e_total_export_controller_writes_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state = build_local_e2e_total_export_controller_state(output_root=tmp)
        assert state["status"] == "written"
        assert state["asset_count"] > 0
        assert state["offline_bundle_written"] is True
        assert Path(tmp, state["package_directory_name"], state["manifest_file_name"]).is_file()


def test_database_movement_controller_requires_approval_and_executes_temp_copy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source_root = Path(tmp) / "source"
        dest_root = Path(tmp) / "dest"
        source_root.mkdir()
        (source_root / "item.txt").write_text("fixture", encoding="utf-8")

        preview = build_database_movement_controller_state(
            source_root=source_root,
            destination_root=dest_root,
            execute=False,
        )
        assert preview["approval_token_required"] is True
        assert preview["approval_token_supplied"] is False
        assert preview["no_automatic_classification"] is True

        executed = build_database_movement_controller_state(
            source_root=source_root,
            destination_root=dest_root,
            execute=True,
        )
        assert executed["approval_token_supplied"] is True
        assert executed["completed_evidence_receipt_created"] is True


def test_live_smoke_helper_is_dry_run_and_approval_gated() -> None:
    state = build_manual_live_smoke_helper_controller_state()
    assert state["live_execution_performed"] is False
    assert state["approval_required"] is True
    assert state["collection"]["plan_count"] >= 8
    assert all(not decision["command_executed"] for decision in state["dry_run_decisions"])


def test_archive_media_archivebox_launch_surface_uses_fake_and_preview_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state = build_archive_media_archivebox_launch_controller_state(output_root=tmp)
        assert state["fake_http_used"] is True
        assert state["external_network_performed"] is False
        assert state["real_subprocess_performed"] is False
        assert state["local_media_copy_receipt_count"] == 1
        assert state["ffmpeg_mux_preview"]["dry_run"] is True
        assert state["yt_dlp_preview"]["dry_run"] is True
        assert state["archivebox_command_previews"]


def test_access_online_asr_preservation_state_does_not_read_credentials_or_run_asr() -> None:
    state = build_access_online_asr_preservation_controller_state()
    assert state["keys_accounts_sidebar_label"] == "KEYS/ACCOUNTS"
    assert state["added_providers_vs_catalogue_split"] is True
    assert state["local_asr_preferred_profile"]["model"] == "large-v3"
    assert state["credentials_read"] is False
    assert state["provider_call_performed"] is False
    assert state["asr_job_run"] is False


def test_app_operator_controller_aggregates_all_surfaces() -> None:
    state = build_app_operator_controller_state()
    data = state.to_dict()
    assert data["controller_surface_count"] == 9
    assert data["no_live_execution_performed"] is True
    assert data["no_credentials_read"] is True
    assert data["no_asr_run"] is True
    assert data["source_url_files"]["url_enter_accepts_source"] is True
    assert data["operator_approval"]["summary"]["action_count"] > 0
    assert data["receipt_import_review"]["unsafe_claim_rejection_enabled"] is True


if __name__ == "__main__":
    test_source_url_files_controller_exposes_expected_app_state()
    test_operator_approval_controller_blocks_unapproved_and_allows_local_temp()
    test_unified_execution_controller_preview_and_local_temp_modes()
    test_local_e2e_total_export_controller_writes_package()
    test_database_movement_controller_requires_approval_and_executes_temp_copy()
    test_live_smoke_helper_is_dry_run_and_approval_gated()
    test_archive_media_archivebox_launch_surface_uses_fake_and_preview_paths()
    test_access_online_asr_preservation_state_does_not_read_credentials_or_run_asr()
    test_app_operator_controller_aggregates_all_surfaces()
