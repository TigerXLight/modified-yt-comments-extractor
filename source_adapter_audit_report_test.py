from source_adapter_audit_report import (
    build_source_adapter_audit_report,
    source_adapter_audit_report_to_json,
    validate_source_adapter_audit_report,
)
from source_database_review_workflow import build_source_database_review_bridge_summary
from source_record_review_workflow import build_source_record_review_workflow
from source_selector_approval_workflow import build_source_selector_approval_packet_collection
from source_named_site_priority_plan import build_source_named_site_priority_plan
from source_named_site_method_packs import build_source_named_site_method_pack_collection
from source_operator_command_packs import build_source_operator_command_pack_collection
from source_manual_smoke_checklists import build_source_manual_smoke_checklist_collection
from source_review_panel_state import build_source_audit_dashboard_state
from access_online_asr_bridge import build_access_online_asr_bridge_summary
from source_site_method_audit_registry import build_source_site_selector_audit_pack_collection
from source_site_method_audit_registry import build_source_site_method_audit_registry


def test_source_adapter_audit_report_combines_adapter_and_site_method_rows() -> None:
    site_registry = build_source_site_method_audit_registry()
    selector_packets = build_source_selector_approval_packet_collection(site_registry)
    named_packs = build_source_named_site_method_pack_collection(site_registry)
    operator_commands = build_source_operator_command_pack_collection(named_packs)
    smoke_checklists = build_source_manual_smoke_checklist_collection(named_packs)
    access_bridge = build_access_online_asr_bridge_summary()
    database_review = build_source_database_review_bridge_summary(
        database_scan_row_count=11,
        review_needed_row_count=11,
        selector_audit_required_count=1,
        rejected_unsafe_edit_count=2,
        approval_packet_count=selector_packets.packet_count,
    )
    source_record_review = build_source_record_review_workflow(())
    priority_plan = build_source_named_site_priority_plan(
        site_registry,
        database_review_workflow=database_review,
        source_record_review_workflow=source_record_review,
        selector_approval_packets=selector_packets,
        named_site_method_packs=named_packs,
        operator_command_packs=operator_commands,
        manual_smoke_checklists=smoke_checklists,
    )
    dashboard = build_source_audit_dashboard_state(
        database_review_workflow=database_review,
        source_record_review_workflow=source_record_review,
        selector_approval_packets=selector_packets,
        named_site_method_packs=named_packs,
        operator_command_packs=operator_commands,
        manual_smoke_checklists=smoke_checklists,
        access_online_asr_bridge_summary=access_bridge,
    )
    report = build_source_adapter_audit_report(
        site_method_registry=site_registry,
        database_review_workflow=database_review,
        source_record_review_workflow=source_record_review,
        selector_approval_packets=selector_packets,
        named_site_method_packs=named_packs,
        operator_command_packs=operator_commands,
        manual_smoke_checklists=smoke_checklists,
        source_audit_dashboard_state=dashboard,
        access_online_asr_bridge_summary=access_bridge,
        named_site_priority_plan=priority_plan,
        workflow_sidecar_filenames=(
            "source_evidence_workflow_state.json",
            "source_site_method_audit_registry.json",
            "source_site_selector_audit_packs.json",
            "source_database_review_workflow.json",
        )
    )
    data = report.to_dict()
    rendered = source_adapter_audit_report_to_json(report)

    assert report.row_count == 20
    assert report.selector_audit_required_count == 1
    assert report.live_approved_only_count == 1
    assert report.not_yet_executed_count == report.row_count
    assert report.selector_pack_collection_id == build_source_site_selector_audit_pack_collection().collection_id
    assert "source_site_selector_audit_packs.json" in report.workflow_sidecar_filenames
    assert "source_database_review_workflow.json" in report.workflow_sidecar_filenames
    assert data["database_review_workflow_summary"]["database_scan_row_count"] == 11
    assert data["unsafe_update_rejection_summary"]["rejected_unsafe_edit_count"] == 2
    assert data["selector_approval_packet_summary"]["packet_count"] == 1
    assert data["named_site_method_pack_summary"]["pack_count"] == 11
    assert data["operator_command_pack_summary"]["pack_count"] == 11
    assert data["operator_command_pack_summary"]["approval_required_count"] == 11
    assert data["manual_smoke_checklist_summary"]["pack_count"] == 5
    assert data["manual_smoke_checklist_summary"]["row_count"] == 11
    assert data["source_audit_dashboard_summary"]["summary"]["operator_command_pack_count"] == 11
    assert data["access_online_asr_bridge_summary"]["local_asr_benchmark_profile_guard"] == "preserve_whispercpp_vulkan_large_v3"
    assert data["done_not_done_table"]
    assert any(row["not_done_reason"] == "selector_audit_required" for row in data["done_not_done_table"])
    assert data["next_named_site_selector_priorities"][0]["method_id"] == "generic_comments_site_specific_selector"
    assert any(row.method_id == "generic_comments_site_specific_selector" for row in report.rows)
    assert any(
        row.next_review_action == "site_specific_selector_audit_required"
        for row in report.rows
    )
    assert rendered == source_adapter_audit_report_to_json(report)
    assert "live verified" not in rendered.lower()
    assert "completed evidence" not in rendered.lower()
    assert data["metadata_only"] is True
    assert data["live_execution_performed"] is False
    validate_source_adapter_audit_report(data)


def test_source_adapter_audit_report_validation_rejects_unsafe_claims() -> None:
    data = build_source_adapter_audit_report().to_dict()
    data["rows"][0]["completed_evidence_claimed"] = True

    try:
        validate_source_adapter_audit_report(data)
    except ValueError as error:
        assert "completed evidence" in str(error)
    else:
        raise AssertionError("Unsafe audit report row should be rejected")


def run_self_test() -> None:
    test_source_adapter_audit_report_combines_adapter_and_site_method_rows()
    test_source_adapter_audit_report_validation_rejects_unsafe_claims()


if __name__ == "__main__":
    run_self_test()
    print("Source adapter audit report self-test passed.")
