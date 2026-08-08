from source_adapter_priority_site_pack_execution_closeout import (
    DEFAULT_CAPABILITY_IDS,
    HANDOFF_STATUS,
    STATUS,
    build_source_adapter_priority_site_pack_execution_closeout,
    example_runtime_fixture_smoke_final_closeout_package,
)


def main() -> None:
    package = build_source_adapter_priority_site_pack_execution_closeout(
        example_runtime_fixture_smoke_final_closeout_package(),
        operator_id="tester",
    ).as_dict()
    assert package["priority_site_pack_execution_closeout_status"] == STATUS
    assert package["capability_count"] == len(DEFAULT_CAPABILITY_IDS)
    assert package["priority_site_pack_count"] >= 7
    matrix = package["source_adapter_priority_site_fixture_pack_matrix"]
    site_pack_ids = {row["site_pack_id"] for row in matrix["priority_site_pack_rows"]}
    assert {"msn_article_comments", "x_social_thread", "youtube_media_transcript", "gov_register_page"}.issubset(site_pack_ids)
    handoff = package["source_adapter_priority_site_pack_execution_handoff"]
    assert handoff["handoff_status"] == HANDOFF_STATUS
    assert handoff["ready_for_local_fixture_authoring"] is True
    assert handoff["ready_for_operator_approved_manual_smoke"] is True
    roadmap = package["source_adapter_priority_site_roadmap_closeout"]
    assert roadmap["keys_accounts_lookup_surface"] == "keys_accounts.ui.credential_reference_selector"
    assert roadmap["priority_site_pack_count"] == package["priority_site_pack_count"]
    print("Source Adapter Priority Site Pack Execution Closeout self-test passed.")


if __name__ == "__main__":
    main()
