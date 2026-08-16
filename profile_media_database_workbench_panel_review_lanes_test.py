from __future__ import annotations

from profile_media_database_workbench_panel import build_profile_media_database_gui_panel_state, gui_panel_payload


def test_panel_review_lanes_read_nested_workbench_dashboard_and_report_counts() -> None:
    state = build_profile_media_database_gui_panel_state(
        mode="DATABASE",
        database_root="Demo Database",
        batch_json_files=("batch.json",),
        workbench_payload={
            "index_case_count": 1,
            "index_source_count": 3,
            "index_profile_row_count": 2,
            "matched_source_count": 3,
            "matched_profile_count": 2,
            "navigation_target_count": 6,
            "review_item_count": 8,
            "saved_view_count": 5,
            "dashboard": {
                "metrics": [
                    {"key": "source_chain_gaps", "value": 3},
                    {"key": "disputed_framing", "value": 1},
                    {"key": "unknown_source_roles", "value": 5},
                    {"key": "parser_warnings", "value": 2},
                ]
            },
            "review_report": {
                "source_chain_gap_count": 3,
                "disputed_framing_count": 1,
                "unknown_source_role_count": 5,
                "parser_warning_count": 2,
            },
        },
    )
    lanes = {lane["key"]: lane["value"] for lane in gui_panel_payload(state)["review_lanes"]}
    assert lanes["source_chain_gaps"] == 3
    assert lanes["disputed_framing"] == 1
    assert lanes["unknown_source_roles"] == 5
    assert lanes["parser_warnings"] == 2


def main() -> int:
    test_panel_review_lanes_read_nested_workbench_dashboard_and_report_counts()
    print("profile_media_database_workbench_panel_review_lanes v76i OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
