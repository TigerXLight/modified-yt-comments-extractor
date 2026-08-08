from capture_controller import build_operational_capture_plan
from capture_export_queue import connect_operational_capture_plan_to_export_queue
from evidence_database_index import (
    EvidenceIndexManifest,
    evidence_index_manifest_with_hash,
    evidence_index_record_from_source_site_method_audit_row,
)
from source_adapter_audit_registry import build_source_adapter_audit_registry
from source_database_review_workflow import (
    SourceDatabaseReviewFilterState,
    SourceDatabaseReviewPendingEditState,
    SourceDatabaseReviewSelectedRowState,
    build_source_database_review_view_model,
    preview_source_database_review_update,
    source_database_review_view_model_to_json,
)
from source_resource_state import build_discussion_capture_options, build_source_resource_row
from source_site_method_audit_registry import build_source_site_method_audit_registry


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


def _manifest_and_registries():
    plan = _plan()
    site_registry = build_source_site_method_audit_registry()
    records = tuple(
        evidence_index_record_from_source_site_method_audit_row(
            row,
            database_root_id="db-root",
            taxonomy_version_id="taxonomy-v1",
        )
        for row in site_registry.rows
    )
    manifest = evidence_index_manifest_with_hash(
        EvidenceIndexManifest(
            manifest_id="source_database_review_manifest",
            records=records,
        )
    )
    return plan, manifest, build_source_adapter_audit_registry(), site_registry


def _generic_comments_item_id(manifest):
    for record in manifest.records:
        if record.identity.display_name == "Generic comments site-specific selector":
            return record.identity.item_id
    raise AssertionError("Generic comments site-method audit row missing")


def test_database_review_view_model_collects_scan_review_audit_source_and_queue_rows() -> None:
    plan, manifest, adapter_registry, site_registry = _manifest_and_registries()

    view_model = build_source_database_review_view_model(
        manifest=manifest,
        source_adapter_audit_registry=adapter_registry,
        source_site_method_audit_registry=site_registry,
        grabbed_source_records=(plan.grabbed_source_record,),
        evidence_queue=connect_operational_capture_plan_to_export_queue(plan).queue,
        filter_state=SourceDatabaseReviewFilterState(show_review_needed_only=True),
        selected_row_state=SourceDatabaseReviewSelectedRowState(
            row_id=_generic_comments_item_id(manifest),
            row_kind="site_method_audit",
            display_name="Generic comments site-specific selector",
        ),
    )
    data = view_model.to_dict()
    rendered = source_database_review_view_model_to_json(view_model)

    assert view_model.view_model_id.startswith("source_database_review_workflow_")
    assert view_model.scan_row_count == 11
    assert view_model.review_needed_row_count == 11
    assert view_model.adapter_audit_row_count == 9
    assert view_model.site_method_audit_row_count == 11
    assert view_model.source_grabbed_record_count == 1
    assert view_model.evidence_queue_row_count > 0
    assert data["bridge_summary"]["selector_audit_required_count"] == 1
    assert data["bridge_summary"]["approval_packet_count"] == 0
    assert data["selected_row_state"]["row_kind"] == "site_method_audit"
    assert '"metadata_only": true' in rendered
    assert '"no_live_execution_performed": true' in rendered
    assert "completed evidence" not in rendered.lower()
    assert "C:\\Users\\fahad" not in rendered


def test_safe_edit_preview_records_receipt_before_apply_without_execution_claims() -> None:
    _plan, manifest, _adapter_registry, _site_registry = _manifest_and_registries()
    item_id = _generic_comments_item_id(manifest)

    preview = preview_source_database_review_update(
        manifest,
        SourceDatabaseReviewPendingEditState(
            target_item_id=item_id,
            status="selector_audit_required",
            operator_review_note="Operator noted selector review remains needed.",
            selector_audit_note="Named-site selector audit can be scheduled later.",
            manual_observation_note="Manual observation is acceptable until selectors are approved.",
            archive_fallback_note="Archive-only comment evidence remains reviewable.",
            review_queue_assignment="Queue for source-method selector review.",
            source_record_cross_reference_note="Cross-link grabbed source selector refs.",
            total_export_inclusion_note="Include as review metadata only.",
        ),
        operator_id="operator-1",
        timestamp_utc="2026-08-08T12:00:00Z",
    )
    data = preview.to_dict()

    assert preview.accepted_for_preview is True
    assert preview.proposal_row is not None
    assert preview.proposal_row.preview_only is True
    assert preview.proposal_row.ready_for_apply is False
    assert preview.receipt_summary_row is not None
    assert "classification_state.dimensions" in preview.receipt_summary_row.changed_fields
    assert data["file_move_performed"] is False
    assert data["live_execution_performed"] is False
    assert data["completed_evidence_claimed"] is False
    assert data["automatic_classification_performed"] is False


def test_unsafe_edit_preview_is_rejected_without_hiding_reasons() -> None:
    _plan, manifest, _adapter_registry, _site_registry = _manifest_and_registries()
    item_id = _generic_comments_item_id(manifest)

    preview = preview_source_database_review_update(
        manifest,
        SourceDatabaseReviewPendingEditState(
            target_item_id=item_id,
            status="metadata_audit_ready",
            operator_review_note="Use C:\\Users\\fahad\\secret.txt and cookie: abc",
            completed_evidence_claimed=True,
            live_execution_claimed=True,
            file_movement_claimed=True,
            raw_payload_insertion_claimed=True,
            local_absolute_path_insertion_claimed=True,
            credential_material_claimed=True,
            protected_sensitive_classification_claimed=True,
            automatic_classification_claimed=True,
        ),
    )

    assert preview.accepted_for_preview is False
    assert preview.proposal_row is None
    assert preview.rejected_update_row is not None
    assert "completed_evidence_claim_rejected" in preview.rejected_update_row.reasons
    assert "live_execution_claim_rejected" in preview.rejected_update_row.reasons
    assert "file_movement_claim_rejected" in preview.rejected_update_row.reasons
    assert "raw_payload_insertion_rejected" in preview.rejected_update_row.reasons
    assert "local_absolute_path_insertion_rejected" in preview.rejected_update_row.reasons
    assert "credential_cookie_account_material_rejected" in preview.rejected_update_row.reasons
    assert "protected_sensitive_classification_rejected" in preview.rejected_update_row.reasons
    assert "automatic_classification_claim_rejected" in preview.rejected_update_row.reasons
    assert preview.rejected_update_row.file_move_performed is False
    assert preview.rejected_update_row.live_execution_performed is False
    assert preview.rejected_update_row.completed_evidence_claimed is False


def test_unsafe_sensitive_or_unsupported_status_text_is_rejected() -> None:
    _plan, manifest, _adapter_registry, _site_registry = _manifest_and_registries()
    item_id = _generic_comments_item_id(manifest)

    sensitive = preview_source_database_review_update(
        manifest,
        SourceDatabaseReviewPendingEditState(
            target_item_id=item_id,
            status="metadata_audit_ready",
            selector_audit_note="Infer religion from the folder label.",
        ),
    )
    unsupported_status = preview_source_database_review_update(
        manifest,
        SourceDatabaseReviewPendingEditState(
            target_item_id=item_id,
            status="live_complete",
        ),
    )

    assert sensitive.accepted_for_preview is False
    assert sensitive.rejected_update_row is not None
    assert "protected_sensitive_text_rejected" in sensitive.rejected_update_row.reasons
    assert unsupported_status.accepted_for_preview is False
    assert unsupported_status.rejected_update_row is not None
    assert "unsupported_status_transition_rejected" in unsupported_status.rejected_update_row.reasons


def run_self_test() -> None:
    test_database_review_view_model_collects_scan_review_audit_source_and_queue_rows()
    test_safe_edit_preview_records_receipt_before_apply_without_execution_claims()
    test_unsafe_edit_preview_is_rejected_without_hiding_reasons()
    test_unsafe_sensitive_or_unsupported_status_text_is_rejected()


if __name__ == "__main__":
    run_self_test()
    print("Source database review workflow self-test passed.")
