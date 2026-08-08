from source_selector_approval_workflow import (
    build_source_selector_approval_packet_collection,
    group_selector_audit_rows_by_site_profile,
    list_selector_audit_required_rows,
    source_selector_approval_packet_collection_to_json,
)
from source_site_method_audit_registry import build_source_site_method_audit_registry


def test_selector_audit_required_rows_are_grouped_and_kept_not_live_executed() -> None:
    registry = build_source_site_method_audit_registry()
    rows = list_selector_audit_required_rows(registry)
    grouped = group_selector_audit_rows_by_site_profile(rows)
    collection = build_source_selector_approval_packet_collection(registry)
    data = collection.to_dict()
    rendered = source_selector_approval_packet_collection_to_json(collection)

    assert len(rows) == 1
    assert rows[0].method_id == "generic_comments_site_specific_selector"
    assert rows[0].status == "selector_audit_required"
    assert grouped == {"generic_comments_site_selector": (rows[0].site_method_id,)}
    assert collection.packet_count == 1
    assert collection.selector_audit_required_count == 1
    assert collection.live_approved_only_count == 1
    assert collection.manual_smoke_checklist_row_count == 4
    assert collection.not_live_executed_receipt_count == 1
    assert collection.ready_for_operator_review_count == 1
    packet = data["packets"][0]
    assert packet["method_id"] == "generic_comments_site_specific_selector"
    assert packet["approval_status"] == "APPROVAL_REQUIRED"
    assert packet["ready_for_operator_review"] is True
    assert packet["live_execution_performed"] is False
    assert packet["completed_evidence_claimed"] is False
    assert packet["not_live_executed_receipt"]["status"] == "not_live_executed"
    assert packet["not_live_executed_receipt"]["browser_automation_performed"] is False
    assert {row["scope"] for row in packet["manual_smoke_checklist_rows"]} == {
        "archive_only_fallback",
        "manual_observation_fallback",
        "operator_approval_packet",
        "selector_boundary_review",
    }
    assert "live success" not in rendered.lower()
    assert "completed evidence" not in rendered.lower()
    assert "C:\\Users\\fahad" not in rendered


def test_selector_approval_packets_are_deterministic_and_metadata_only() -> None:
    registry = build_source_site_method_audit_registry()

    first = build_source_selector_approval_packet_collection(registry)
    second = build_source_selector_approval_packet_collection(registry)

    assert first.to_dict() == second.to_dict()
    assert first.metadata_only is True
    assert first.user_review_required is True
    assert first.no_live_execution_performed is True
    assert first.no_completed_evidence_claimed is True
    assert first.no_automatic_classification_performed is True


def run_self_test() -> None:
    test_selector_audit_required_rows_are_grouped_and_kept_not_live_executed()
    test_selector_approval_packets_are_deterministic_and_metadata_only()


if __name__ == "__main__":
    run_self_test()
    print("Source selector approval workflow self-test passed.")
