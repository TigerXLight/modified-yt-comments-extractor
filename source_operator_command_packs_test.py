import json

from source_named_site_method_packs import build_source_named_site_method_pack_collection
from source_operator_command_packs import (
    build_source_operator_command_pack_collection,
    source_operator_command_pack_collection_to_json,
    validate_source_operator_command_pack_collection,
)


def test_operator_command_packs_cover_named_site_methods_without_execution() -> None:
    named_packs = build_source_named_site_method_pack_collection()
    commands = build_source_operator_command_pack_collection(named_packs)
    data = commands.to_dict()

    assert commands.pack_count == named_packs.pack_count
    assert commands.approval_required_count == commands.pack_count
    assert commands.selector_audit_required_count == 1
    assert data["no_live_execution_status"] == "no_live_execution_performed"
    assert data["live_execution_performed"] is False
    assert data["browser_automation_performed"] is False
    assert data["provider_call_performed"] is False
    assert data["archive_submission_performed"] is False
    assert data["download_performed"] is False
    assert data["file_move_performed"] is False
    assert data["completed_evidence_claimed"] is False
    assert data["automatic_classification"] is False
    validate_source_operator_command_pack_collection(data)


def test_operator_command_packs_include_required_boundaries_and_mappings() -> None:
    commands = build_source_operator_command_pack_collection()
    by_method = {pack.method_id: pack for pack in commands.packs}

    msn = by_method["msn_shadow_dom_comments"]
    assert "explicit_site_level_approval" in msn.required_operator_inputs
    assert "COMMENTS_JSONL" in msn.expected_artifact_refs
    assert "manual_observation_receipt" in msn.expected_receipt_refs
    assert msn.credential_boundary_note.startswith("Credentials")
    assert msn.source_evidence_mapping
    assert msn.total_export_mapping
    assert msn.executed is False

    selector = by_method["generic_comments_site_specific_selector"]
    assert "site_specific_selector_audit_note" in selector.required_operator_inputs
    assert "selector_audit_receipt" in selector.expected_receipt_refs
    assert selector.no_live_execution_status == "not_live_executed"

    archive = by_method["archive_only_import"]
    assert "archive_url" in archive.required_operator_inputs
    assert "original_url" in archive.required_operator_inputs
    assert archive.provider_call_performed is False
    assert archive.file_move_performed is False


def test_operator_command_pack_json_is_deterministic_and_summary_only() -> None:
    first = build_source_operator_command_pack_collection()
    second = build_source_operator_command_pack_collection()

    first_json = source_operator_command_pack_collection_to_json(first)
    second_json = source_operator_command_pack_collection_to_json(second)
    payload = json.loads(first_json)

    assert first_json == second_json
    assert payload["pack_count"] == 11
    assert "C:\\" not in first_json
    assert "T:\\" not in first_json
    assert "sk-" not in first_json
    assert "Authorization:" not in first_json
    assert "Cookie:" not in first_json
    assert "completed evidence" not in first_json.lower()


def run_self_test() -> None:
    test_operator_command_packs_cover_named_site_methods_without_execution()
    test_operator_command_packs_include_required_boundaries_and_mappings()
    test_operator_command_pack_json_is_deterministic_and_summary_only()


if __name__ == "__main__":
    run_self_test()
    print("Source operator command packs self-test passed.")
