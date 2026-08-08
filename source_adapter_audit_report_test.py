from source_adapter_audit_report import (
    build_source_adapter_audit_report,
    source_adapter_audit_report_to_json,
    validate_source_adapter_audit_report,
)
from source_site_method_audit_registry import build_source_site_selector_audit_pack_collection


def test_source_adapter_audit_report_combines_adapter_and_site_method_rows() -> None:
    report = build_source_adapter_audit_report(
        workflow_sidecar_filenames=(
            "source_evidence_workflow_state.json",
            "source_site_method_audit_registry.json",
            "source_site_selector_audit_packs.json",
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
