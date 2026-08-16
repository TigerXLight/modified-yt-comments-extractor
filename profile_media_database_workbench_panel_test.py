from __future__ import annotations

from profile_media_database_workbench_panel import (
    build_profile_media_database_gui_panel_state,
    gui_panel_payload,
    render_profile_media_database_gui_panel_text,
)


def test_files_mode_panel_is_inert() -> None:
    state = build_profile_media_database_gui_panel_state(mode="FILES")
    payload = gui_panel_payload(state)
    assert payload["mode"] == "FILES"
    assert payload["status"] == "database_mode_off"
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["file_write_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert "Profile/Media HOME Repository Panel" in render_profile_media_database_gui_panel_text(state)


def test_database_mode_without_batch_json_is_visible_but_unconfigured() -> None:
    state = build_profile_media_database_gui_panel_state(mode="DATABASE", database_root="Demo Database")
    payload = gui_panel_payload(state)
    assert payload["mode"] == "DATABASE"
    assert payload["status"] == "ready_for_import"
    assert payload["database_root"] == "Demo Database"
    assert payload["batch_json_files"] == ()
    actions = {action["action_id"]: action["label"] for action in payload["actions"]}
    assert actions["load_batch_json"] == "Add / Import"
    assert actions["save_to_home_repository"] == "Save to HOME"
    assert actions["review_folder_operations"] == "Review moves"
    assert actions["reconcile_batch_after_folder_operations"] == "Update saved index"
    assert actions["run_end_to_end_workflow_check"] == "Check workflow"
    assert payload["folder_scan_performed"] is False
    assert payload["folder_creation_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["file_write_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False


def test_database_panel_projects_workbench_payload_counts() -> None:
    state = build_profile_media_database_gui_panel_state(
        mode="DATABASE",
        database_root="Demo Database",
        batch_json_files=("case.json",),
        workbench_payload={
            "index_case_count": 3,
            "index_source_count": 7,
            "index_profile_row_count": 11,
            "matched_source_count": 2,
            "matched_profile_count": 5,
            "navigation_target_count": 21,
            "review_item_count": 4,
            "saved_view_count": 6,
            "source_chain_gap_count": 1,
            "disputed_framing_count": 2,
            "unknown_source_role_count": 3,
            "parser_warning_count": 4,
            "dashboard": {
                "unique_profile_count": 5,
                "facets": [
                    {"facet_type": "source_role", "value": "PRIMARY_SELF_AUTHORED_SCOPE", "count": 1},
                    {"facet_type": "source_role", "value": "SECONDARY_WITNESS_ACCOUNT", "count": 2},
                    {"facet_type": "source_role", "value": "TERTIARY_PROPAGATED_SOURCE", "count": 3},
                ],
            },
        },
    )
    payload = gui_panel_payload(state)
    metrics = {metric["key"]: metric["value"] for metric in payload["metrics"]}
    lanes = {lane["key"]: lane["value"] for lane in payload["review_lanes"]}
    assert payload["status"] == "success"
    assert metrics["cases"] == 3
    assert metrics["sources"] == 7
    assert metrics["profile_rows"] == 11
    assert metrics["matched_sources"] == 2
    assert metrics["matched_profiles"] == 5
    assert metrics["navigation_targets"] == 21
    assert metrics["review_items"] == 4
    assert metrics["saved_views"] == 6
    display_metrics = {metric["key"]: metric["value"] for metric in payload["display_metrics"]}
    assert display_metrics["primary_sources"] == 1
    assert display_metrics["secondary_sources"] == 2
    assert display_metrics["tertiary_sources"] == 3
    assert display_metrics["persons"] == 5
    assert lanes["source_chain_gaps"] == 1
    assert lanes["disputed_framing"] == 2
    assert lanes["unknown_source_roles"] == 3
    assert lanes["parser_warnings"] == 4


def main() -> int:
    test_files_mode_panel_is_inert()
    test_database_mode_without_batch_json_is_visible_but_unconfigured()
    test_database_panel_projects_workbench_payload_counts()
    print("profile_media_database_workbench_panel v76k2 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
