import json

from source_manual_smoke_checklists import (
    build_source_manual_smoke_checklist_collection,
    source_manual_smoke_checklist_collection_to_json,
    validate_source_manual_smoke_checklist_collection,
)


def test_manual_smoke_checklists_cover_named_site_groups_without_execution() -> None:
    collection = build_source_manual_smoke_checklist_collection()
    data = collection.to_dict()

    assert collection.pack_count == 5
    assert collection.row_count == 11
    assert collection.approval_required_count == 11
    assert data["no_live_execution_status"] == "no_live_execution_performed"
    assert data["live_execution_performed"] is False
    assert data["browser_automation_performed"] is False
    assert data["provider_call_performed"] is False
    assert data["archive_submission_performed"] is False
    assert data["download_performed"] is False
    assert data["file_move_performed"] is False
    assert data["completed_evidence_claimed"] is False
    validate_source_manual_smoke_checklist_collection(data)


def test_manual_smoke_checklist_rows_include_expected_receipts_and_boundaries() -> None:
    collection = build_source_manual_smoke_checklist_collection()
    rows = {
        row.method_id: row
        for pack in collection.packs
        for row in pack.rows
    }

    assert "operator_approval_receipt" in rows["msn_shadow_dom_comments"].expected_receipt_refs
    assert "selector_audit_receipt" in rows["generic_comments_site_specific_selector"].expected_receipt_refs
    assert rows["generic_comments_site_specific_selector"].operator_approval_required is True
    assert rows["generic_comments_site_specific_selector"].executed is False
    assert "universal selector support" in rows["generic_comments_site_specific_selector"].manual_instruction
    assert rows["archive_only_import"].no_live_execution_status == "not_live_executed"
    assert rows["youtube_media_transcript"].completed_evidence_claimed is False


def test_manual_smoke_checklist_json_is_deterministic_and_summary_only() -> None:
    first = build_source_manual_smoke_checklist_collection()
    second = build_source_manual_smoke_checklist_collection()
    first_json = source_manual_smoke_checklist_collection_to_json(first)
    second_json = source_manual_smoke_checklist_collection_to_json(second)
    payload = json.loads(first_json)

    assert first_json == second_json
    assert payload["pack_count"] == 5
    assert payload["row_count"] == 11
    assert "C:\\" not in first_json
    assert "T:\\" not in first_json
    assert "completed evidence" not in first_json.lower()


def run_self_test() -> None:
    test_manual_smoke_checklists_cover_named_site_groups_without_execution()
    test_manual_smoke_checklist_rows_include_expected_receipts_and_boundaries()
    test_manual_smoke_checklist_json_is_deterministic_and_summary_only()


if __name__ == "__main__":
    run_self_test()
    print("Source manual smoke checklists self-test passed.")
