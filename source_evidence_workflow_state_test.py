from capture_controller import build_operational_capture_plan
from source_evidence_workflow_state import (
    build_source_evidence_workflow_state,
    source_evidence_workflow_state_to_json,
)
from source_resource_state import build_discussion_capture_options, build_source_resource_row


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"


def _plan():
    row = build_source_resource_row(MSN_URL)
    discussion = build_discussion_capture_options(
        (row,),
        selected_row_id=row.row_id,
        webpage_selected=True,
        webpage_screenshot_requested=True,
        comments_selected=True,
        comments_screenshot_requested=True,
        livechat_selected=False,
        livechat_screenshot_requested=False,
    )
    return build_operational_capture_plan(row=row, discussion=discussion)


def test_source_evidence_workflow_state_connects_controller_queue_store_export() -> None:
    plan = _plan()
    state = build_source_evidence_workflow_state(
        plan,
        package_id="source review",
        app_version="test-app",
        database_root_id="db-root",
        taxonomy_version_id="taxonomy-v1",
    )
    data = state.to_dict()

    assert state.review_status == "USER_REVIEW_REQUIRED"
    assert state.execution_state == "EXECUTION_GATED"
    assert state.execution_gate_status == "APPROVAL_REQUIRED"
    assert state.execution_gate_plan_id == plan.execution_gate_plan.plan_id
    assert "LIVE_SITE_CAPTURE" in state.execution_gate_action_kinds
    assert "BROWSER_AUTOMATION" in state.execution_gate_action_kinds
    assert state.queue_item_count == len(state.connection.queue.items)
    assert state.queue_link_count == len(state.connection.queue.links)
    assert state.total_export_asset_count == len(state.connection.total_export_manifest.assets)
    assert state.review_manifest_asset_count == len(state.review_manifest.assets)
    assert state.grabbed_source_record is plan.grabbed_source_record
    assert state.grabbed_source_record_id.startswith("grabbed_source_")
    assert state.grabbed_source_artifact_count > 0
    assert state.database_scan_record_count == len(state.connection.evidence_index_records) + 22
    assert state.database_scan_matched_count == state.database_scan_record_count
    assert state.access_provider_gate_summary_id.startswith("access_provider_gate_")
    assert state.access_provider_gate_record_count > 0
    assert state.access_provider_gate_approval_required_count > 0
    assert state.source_adapter_audit_registry_id.startswith("source_adapter_audit_registry_")
    assert state.source_adapter_audit_entry_count == 9
    assert state.source_adapter_audit_required_count == 0
    assert state.source_site_method_audit_registry_id.startswith("source_site_method_audit_registry_")
    assert state.source_site_method_audit_row_count == 11
    assert state.source_site_method_selector_audit_required_count == 1
    assert state.source_site_method_live_approved_only_count == 1
    assert state.source_adapter_audit_report_id.startswith("source_adapter_audit_report_")
    assert state.source_adapter_audit_report_row_count == 20
    assert state.source_adapter_audit_report_selector_audit_required_count == 1
    assert state.source_named_site_priority_plan_id.startswith("source_named_site_priority_plan_")
    assert state.source_named_site_priority_plan_row_count == 9
    assert state.source_named_site_priority_plan_approval_required_count == 9
    assert state.source_named_site_method_packs_id.startswith("source_named_site_method_packs_")
    assert state.source_named_site_method_pack_count == 11
    assert state.source_named_site_method_pack_msn_count == 2
    assert state.source_named_site_method_pack_twitter_x_count == 2
    assert state.source_named_site_method_pack_youtube_count == 2
    assert state.source_named_site_method_pack_generic_archive_count == 5
    assert state.source_named_site_method_pack_selector_audit_required_count == 1
    assert state.source_database_review_workflow_id.startswith("source_database_review_workflow_")
    assert state.source_database_review_scan_row_count == state.database_scan_record_count
    assert state.source_database_review_needed_row_count >= 1
    assert state.source_database_review_pending_safe_edit_count == 0
    assert state.source_database_review_rejected_unsafe_edit_count == 0
    assert state.source_record_review_workflow_id.startswith("source_record_review_workflow_")
    assert state.source_record_review_record_count == 1
    assert state.source_record_review_reference_count > 0
    assert state.source_record_review_selector_cross_link_count > 0
    assert state.source_selector_approval_packets_id.startswith("source_selector_approval_packets_")
    assert state.source_selector_approval_packet_count == 1
    assert state.source_selector_manual_smoke_checklist_row_count == 4
    assert state.source_selector_not_live_executed_receipt_count == 1
    assert state.release_action_plan_id == state.release_action_plan.release_action_plan_id
    assert state.release_action_receipt_count == 4
    assert state.operator_signoff_required is True
    assert state.queue_review_store_id.startswith("evidence_queue_review_store_")
    assert data["queue_review_store_document"]["metadata_only"] is True
    assert data["queue_review_store_document"]["payload_sha256"]
    assert data["review_manifest"]["assets"]
    assert data["connection"]["review_preview"]["supplied_records_only"] is True
    assert data["grabbed_source_record"]["review_state"] == "USER_REVIEW_REQUIRED"
    assert data["database_scan_result"]["broad_scan_performed"] is False
    assert any(
        row["display_name"] == "Generic comments site-specific selector"
        for row in data["database_scan_result"]["rows"]
    )
    assert data["access_provider_gate_summary"]["credential_lookup_performed"] is False
    assert data["source_adapter_audit_registry"]["entry_count"] == 9
    assert data["source_adapter_audit_registry"]["audit_required_count"] == 0
    assert data["source_adapter_audit_registry"]["live_execution_performed"] is False
    assert data["source_site_method_audit_registry"]["row_count"] == 11
    assert data["source_site_method_audit_registry"]["selector_audit_required_count"] == 1
    assert data["source_site_method_audit_registry"]["live_execution_performed"] is False
    assert data["source_adapter_audit_report"]["row_count"] == 20
    assert data["source_adapter_audit_report"]["selector_audit_required_count"] == 1
    assert data["source_adapter_audit_report"]["live_execution_performed"] is False
    assert data["source_named_site_priority_plan"]["row_count"] == 9
    assert data["source_named_site_priority_plan"]["approval_required_count"] == 9
    assert data["source_named_site_priority_plan"]["live_execution_performed"] is False
    assert data["source_named_site_method_packs"]["pack_count"] == 11
    assert data["source_named_site_method_packs"]["selector_audit_required_count"] == 1
    assert data["source_named_site_method_packs"]["live_execution_performed"] is False
    assert data["source_database_review_workflow"]["scan_row_count"] == state.database_scan_record_count
    assert data["source_database_review_workflow"]["bridge_summary"]["approval_packet_count"] == 1
    assert data["source_database_review_workflow"]["named_site_method_pack_row_count"] == 11
    assert data["source_database_review_workflow"]["bridge_summary"]["named_site_method_pack_count"] == 11
    assert data["source_record_review_workflow"]["source_record_count"] == 1
    assert data["source_record_review_workflow"]["named_site_method_pack_count"] == 11
    assert data["source_selector_approval_packets"]["packet_count"] == 1
    assert data["source_selector_approval_packets"]["named_site_method_pack_summary"]["pack_count"] == 11
    assert data["source_selector_approval_packets"]["no_live_execution_performed"] is True
    assert any(
        asset["description"] == "Source Evidence workflow state metadata bundle sidecar."
        for asset in data["review_manifest"]["assets"]
    )


def test_source_evidence_workflow_state_serializes_without_execution_or_payload_claims() -> None:
    state = build_source_evidence_workflow_state(_plan(), package_id="source review")
    rendered = source_evidence_workflow_state_to_json(state)
    summary = state.to_summary_text()
    combined = rendered + "\n" + summary

    assert rendered == source_evidence_workflow_state_to_json(state)
    assert "Runtime executed: false" in summary
    assert "Grabbed source record: grabbed_source_" in summary
    assert "Database scan records:" in summary
    assert "Access/provider gate: access_provider_gate_" in summary
    assert "Access/provider approvals required:" in summary
    assert "Source adapter audit registry: source_adapter_audit_registry_" in summary
    assert "Source adapter audit-required entries:" in summary
    assert "Source site/method audit registry: source_site_method_audit_registry_" in summary
    assert "Source site/method selector audit-required rows:" in summary
    assert "Source adapter audit report: source_adapter_audit_report_" in summary
    assert "Source adapter audit report selector audit-required rows:" in summary
    assert "Named-site priority plan: source_named_site_priority_plan_" in summary
    assert "Named-site priority approvals required:" in summary
    assert "Database review workflow: source_database_review_workflow_" in summary
    assert "Database pending safe edits:" in summary
    assert "Source record review workflow: source_record_review_workflow_" in summary
    assert "Selector approval packets: source_selector_approval_packets_" in summary
    assert "Selector not-live-executed receipts:" in summary
    assert "Release action plan: source_release_plan_" in summary
    assert "Operator signoff required: true" in summary
    assert "USER_REVIEW_REQUIRED" in summary
    for forbidden in (
        "completed evidence",
        "verified evidence",
        "final evidence",
        "live verified",
        "api_key",
        "Authorization",
        "Cookie",
        "C:\\\\Users\\\\fahad",
        "DO NOT SHOW RAW PAYLOAD",
        "downloaded media",
        "archive complete",
    ):
        assert forbidden not in combined
    assert '"runtime_executed": false' in rendered
    assert '"file_move_performed": false' in rendered
    assert '"file_existence_claimed": false' in rendered


def run_self_test() -> None:
    test_source_evidence_workflow_state_connects_controller_queue_store_export()
    test_source_evidence_workflow_state_serializes_without_execution_or_payload_claims()


if __name__ == "__main__":
    run_self_test()
    print("Source evidence workflow state self-test passed.")
