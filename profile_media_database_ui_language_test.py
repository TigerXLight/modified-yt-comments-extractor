from __future__ import annotations

from profile_media_database_ui_language import (
    BACKEND_TERMS_HIDDEN_FROM_COMMON_UI,
    INTERNAL_MEDIA_ROLE,
    PRIMARY_SOURCE_ROLE,
    SECONDARY_SOURCE_ROLE,
    TERTIARY_SOURCE_ROLE,
    common_user_action_label,
    home_repository_status_payload,
    render_home_repository_status,
    source_role_display,
    source_role_summary_from_dashboard,
)


def test_source_role_icons_and_labels_are_common_user_visible() -> None:
    primary = source_role_display(PRIMARY_SOURCE_ROLE, count=2).to_dict()
    secondary = source_role_display(SECONDARY_SOURCE_ROLE, count=3).to_dict()
    tertiary = source_role_display(TERTIARY_SOURCE_ROLE, count=4).to_dict()
    internal = source_role_display(INTERNAL_MEDIA_ROLE, count=1).to_dict()
    assert primary["label"] == "Primary"
    assert secondary["label"] == "Secondary"
    assert tertiary["label"] == "Tertiary"
    assert internal["label"] == "Internal"
    assert primary["asset_hint"].endswith("icons8-contacts-32.png")
    assert secondary["asset_hint"].endswith("icons8-user-account-32.png")
    assert tertiary["asset_hint"].endswith("icons8-people-32.png")
    assert internal["asset_hint"].endswith("icons8-writer-male-32.png")
    assert primary["automatic_classification_performed"] is False
    assert tertiary["sensitive_identifier_inference_performed"] is False


def test_common_user_actions_avoid_backend_terms() -> None:
    assert common_user_action_label("save_to_home_repository") == "SAVE"
    assert common_user_action_label("load_batch_json") == "Add / Import"
    assert common_user_action_label("clear_batch") == "Unload"
    assert common_user_action_label("plan_existing_folder_import") == "Plan folder import"
    assert "batch JSON" in BACKEND_TERMS_HIDDEN_FROM_COMMON_UI
    assert "materialize" in BACKEND_TERMS_HIDDEN_FROM_COMMON_UI


def test_home_repository_status_payload_has_left_sidebar_order() -> None:
    payload = home_repository_status_payload(
        home_root="Demo HOME",
        primary_count=1,
        secondary_count=2,
        tertiary_count=3,
        internal_media_count=4,
        person_count=5,
        review_count=6,
    )
    assert payload["home_repository"] == "Demo HOME"
    assert payload["visible_metric_order"] == [
        "primary_sources",
        "secondary_sources",
        "tertiary_sources",
        "persons",
        "review_items",
    ]
    assert payload["internal_media"] == 4
    assert payload["folder_scan_performed"] is False
    assert payload["media_download_performed"] is False
    text = render_home_repository_status(payload)
    assert "Primary: 1" in text
    assert "Review items: 6" in text


def test_source_role_summary_reads_dashboard_facets_without_inferring() -> None:
    summary = source_role_summary_from_dashboard(
        {
            "dashboard": {
                "facets": [
                    {"facet_type": "source_role", "value": PRIMARY_SOURCE_ROLE, "count": 1},
                    {"facet_type": "source_role", "value": SECONDARY_SOURCE_ROLE, "count": 2},
                    {"facet_type": "source_role", "value": TERTIARY_SOURCE_ROLE, "count": 3},
                    {"facet_type": "source_role", "value": INTERNAL_MEDIA_ROLE, "count": 4},
                ]
            }
        }
    )
    counts = {row["source_role"]: row["count"] for row in summary["roles"]}
    assert counts[PRIMARY_SOURCE_ROLE] == 1
    assert counts[SECONDARY_SOURCE_ROLE] == 2
    assert counts[TERTIARY_SOURCE_ROLE] == 3
    assert counts[INTERNAL_MEDIA_ROLE] == 4
    assert summary["automatic_classification_performed"] is False


if __name__ == "__main__":
    test_source_role_icons_and_labels_are_common_user_visible()
    test_common_user_actions_avoid_backend_terms()
    test_home_repository_status_payload_has_left_sidebar_order()
    test_source_role_summary_reads_dashboard_facets_without_inferring()
    print("profile_media_database_ui_language v76k2 OK")
