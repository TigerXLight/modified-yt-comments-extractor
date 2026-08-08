from source_named_site_priority_plan import (
    build_source_named_site_priority_plan,
    source_named_site_priority_plan_to_json,
    validate_source_named_site_priority_plan,
)
from source_database_review_workflow import build_source_database_review_bridge_summary
from source_record_review_workflow import build_source_record_review_workflow
from source_selector_approval_workflow import build_source_selector_approval_packet_collection
from source_named_site_method_packs import build_source_named_site_method_pack_collection
from source_operator_command_packs import build_source_operator_command_pack_collection
from source_manual_smoke_checklists import build_source_manual_smoke_checklist_collection
from source_review_panel_state import build_source_audit_dashboard_state
from source_site_method_audit_registry import build_source_site_method_audit_registry


def test_named_site_priority_plan_lists_future_operator_approval_targets() -> None:
    registry = build_source_site_method_audit_registry()
    selector_packets = build_source_selector_approval_packet_collection(registry)
    named_packs = build_source_named_site_method_pack_collection(registry)
    operator_commands = build_source_operator_command_pack_collection(named_packs)
    smoke_checklists = build_source_manual_smoke_checklist_collection(named_packs)
    database_review = build_source_database_review_bridge_summary(
        database_scan_row_count=11,
        review_needed_row_count=11,
        selector_audit_required_count=1,
        approval_packet_count=selector_packets.packet_count,
    )
    source_record_review = build_source_record_review_workflow(())
    dashboard = build_source_audit_dashboard_state(
        database_review_workflow=database_review,
        source_record_review_workflow=source_record_review,
        selector_approval_packets=selector_packets,
        named_site_method_packs=named_packs,
        operator_command_packs=operator_commands,
        manual_smoke_checklists=smoke_checklists,
    )
    plan = build_source_named_site_priority_plan(
        registry,
        database_review_workflow=database_review,
        source_record_review_workflow=source_record_review,
        selector_approval_packets=selector_packets,
        named_site_method_packs=named_packs,
        operator_command_packs=operator_commands,
        manual_smoke_checklists=smoke_checklists,
        source_audit_dashboard_state=dashboard,
    )
    data = plan.to_dict()
    rendered = source_named_site_priority_plan_to_json(plan)

    assert plan.row_count == 9
    assert plan.approval_required_count == 9
    assert plan.selector_audit_required_count == 1
    assert [row.priority_rank for row in plan.rows] == list(range(1, 10))
    assert plan.rows[0].method_id == "msn_article"
    assert any(row.method_id == "generic_comments_site_specific_selector" for row in plan.rows)
    generic_comments = next(
        row for row in plan.rows if row.method_id == "generic_comments_site_specific_selector"
    )
    assert generic_comments.next_action == "perform_named_site_selector_audit_with_explicit_approval"
    assert "site_specific_selector_review_note" in generic_comments.planned_operator_inputs
    assert data["review_workflow_summary"]["database_review"]["database_scan_row_count"] == 11
    assert data["review_workflow_summary"]["source_record_review"]["source_record_count"] == 0
    assert data["selector_approval_packet_summary"]["packet_count"] == 1
    assert data["named_site_method_pack_summary"]["pack_count"] == 11
    assert data["operator_command_pack_summary"]["pack_count"] == 11
    assert data["manual_smoke_checklist_summary"]["row_count"] == 11
    assert data["source_audit_dashboard_summary"]["summary"]["selector_audit_required_count"] == 1
    assert "APPROVAL_REQUIRED" in rendered
    assert "live verified" not in rendered.lower()
    assert "completed evidence" not in rendered.lower()
    assert data["metadata_only"] is True
    assert data["live_execution_performed"] is False
    validate_source_named_site_priority_plan(data)


def test_named_site_priority_plan_validation_rejects_execution_claims() -> None:
    data = build_source_named_site_priority_plan().to_dict()
    data["rows"][0]["download_performed"] = True

    try:
        validate_source_named_site_priority_plan(data)
    except ValueError as error:
        assert "download_performed" in str(error)
    else:
        raise AssertionError("Unsafe named-site priority row should be rejected")


def run_self_test() -> None:
    test_named_site_priority_plan_lists_future_operator_approval_targets()
    test_named_site_priority_plan_validation_rejects_execution_claims()


if __name__ == "__main__":
    run_self_test()
    print("Source named-site priority plan self-test passed.")
