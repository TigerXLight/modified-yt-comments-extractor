from capture_controller import build_operational_capture_plan
from evidence_database_index import (
    EvidenceIndexManifest,
    evidence_index_manifest_with_hash,
    evidence_index_record_from_source_named_site_method_pack,
    evidence_index_record_from_source_site_method_audit_row,
)
from source_database_review_workflow import (
    SourceDatabaseReviewPendingEditState,
    preview_source_database_review_update,
)
from source_evidence_workflow_state import build_source_evidence_workflow_state
from source_review_panel_state import (
    build_database_review_panel_state,
    build_named_site_method_pack_panel_state,
    build_selector_approval_panel_state,
    build_source_audit_dashboard_state,
    build_source_record_review_panel_state,
    source_review_panel_state_to_json,
)
from source_resource_state import build_discussion_capture_options, build_source_resource_row


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"


def _state():
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
    plan = build_operational_capture_plan(row=row, discussion=discussion)
    return build_source_evidence_workflow_state(plan, package_id="source review")


def _generic_comments_item_id(state):
    for record in state.database_scan_result.rows:
        if record.display_name == "Generic comments site-specific selector":
            return record.item_id
    raise AssertionError("Generic comments site-method row missing")


def _review_manifest(state):
    records = tuple(
        evidence_index_record_from_source_site_method_audit_row(row)
        for row in state.source_site_method_audit_registry.rows
    ) + tuple(
        evidence_index_record_from_source_named_site_method_pack(pack)
        for pack in state.source_named_site_method_packs.packs
    )
    return evidence_index_manifest_with_hash(
        EvidenceIndexManifest(manifest_id="panel_state_review_manifest", records=records)
    )


def test_database_review_panel_state_exposes_safe_edit_and_rejection_previews() -> None:
    state = _state()
    item_id = _generic_comments_item_id(state)
    manifest = _review_manifest(state)
    accepted = preview_source_database_review_update(
        manifest,
        SourceDatabaseReviewPendingEditState(
            target_item_id=item_id,
            status="selector_audit_required",
            operator_review_note="Keep selector review queued.",
            selector_audit_note="Named-site selector audit is pending approval.",
            manual_observation_note="Manual observation can be used now.",
            archive_fallback_note="Archive-only evidence can be reviewed.",
            source_record_cross_reference_note="Cross-link source record selector refs.",
            total_export_inclusion_note="Include as metadata-only review item.",
        ),
    )
    rejected = preview_source_database_review_update(
        manifest,
        SourceDatabaseReviewPendingEditState(
            target_item_id=item_id,
            operator_review_note="Use C:\\Users\\fahad\\secret.txt and API key.",
            completed_evidence_claimed=True,
        ),
    )

    safe_panel = build_database_review_panel_state(
        state.source_database_review_workflow,
        edit_preview=accepted,
    )
    rejected_panel = build_database_review_panel_state(
        state.source_database_review_workflow,
        edit_preview=rejected,
    )

    assert safe_panel.panel_kind == "database_review"
    assert safe_panel.row_count == state.source_database_review_scan_row_count
    assert safe_panel.pending_safe_edit_preview["accepted_for_preview"] is True
    assert safe_panel.summary["safe_edit_pending_count"] == 1
    assert safe_panel.receipt_summary_row_count == 1
    assert rejected_panel.rejected_unsafe_edit_preview["accepted_for_preview"] is False
    assert "completed_evidence_claim_rejected" in rejected_panel.rejected_unsafe_edit_preview["errors"]
    assert "credential_cookie_account_or_absolute_path_text_rejected" in rejected_panel.rejected_unsafe_edit_preview["errors"]
    assert rejected_panel.summary["rejected_unsafe_edit_count"] == 1

    rendered = source_review_panel_state_to_json(safe_panel)
    assert "no_live_execution_performed" in rendered
    assert "C:\\Users\\fahad" not in rendered
    assert '"completed_evidence_claimed": false' in rendered


def test_review_panel_states_and_dashboard_are_summary_only() -> None:
    state = _state()
    record_panel = build_source_record_review_panel_state(state.source_record_review_workflow)
    selector_panel = build_selector_approval_panel_state(state.source_selector_approval_packets)
    pack_panel = build_named_site_method_pack_panel_state(state.source_named_site_method_packs)
    dashboard = build_source_audit_dashboard_state(
        database_review_workflow=state.source_database_review_workflow,
        source_record_review_workflow=state.source_record_review_workflow,
        selector_approval_packets=state.source_selector_approval_packets,
        named_site_method_packs=state.source_named_site_method_packs,
    )

    assert record_panel.summary["source_record_count"] == 1
    assert selector_panel.summary["approval_packet_count"] == 1
    assert pack_panel.summary["named_site_method_pack_count"] == 11
    assert dashboard.summary["database_scan_count"] == state.source_database_review_scan_row_count
    assert dashboard.summary["review_needed_count"] == state.source_database_review_needed_row_count
    assert dashboard.summary["source_record_count"] == 1
    assert dashboard.summary["selector_approval_packet_count"] == 1
    assert dashboard.summary["named_site_method_pack_count"] == 11
    assert dashboard.summary["selector_audit_required_count"] == 1
    assert dashboard.summary["no_live_execution_status"] == "no_live_execution_performed"
    rendered = source_review_panel_state_to_json(dashboard)
    assert "completed evidence" not in rendered.lower()
    assert "C:\\Users\\fahad" not in rendered


def run_self_test() -> None:
    test_database_review_panel_state_exposes_safe_edit_and_rejection_previews()
    test_review_panel_states_and_dashboard_are_summary_only()


if __name__ == "__main__":
    run_self_test()
    print("Source review panel state self-test passed.")
