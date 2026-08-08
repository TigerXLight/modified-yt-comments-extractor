from source_grabbed_record import build_grabbed_source_record
from source_record_review_workflow import (
    REFERENCE_BUCKETS,
    build_source_record_review_annotation_receipt,
    build_source_record_review_workflow,
    source_record_review_workflow_to_json,
)
from source_site_method_audit_registry import build_source_site_method_audit_registry


def _generic_comments_site_method_id() -> str:
    registry = build_source_site_method_audit_registry()
    for row in registry.rows:
        if row.method_id == "generic_comments_site_specific_selector":
            return row.site_method_id
    raise AssertionError("Generic comments site-method audit row missing")


def _record():
    selector_id = _generic_comments_site_method_id()
    return build_grabbed_source_record(
        source_row_id="source_row_1",
        source_url="https://example.test/article",
        canonical_url="https://example.test/article",
        adapter_id="generic_article",
        relative_artifact_paths=("metadata/source_record.json",),
        selected_modes=("webpage", "comments"),
        article_reference_ids=("article_ref_1",),
        comment_reference_ids=("comment_ref_1",),
        media_reference_ids=("media_ref_1",),
        transcript_reference_ids=("transcript_ref_1",),
        archive_url_references=("archive_ref_1",),
        screenshot_reference_ids=("screenshot_ref_1",),
        snapshot_reference_ids=("snapshot_ref_1",),
        manual_observation_reference_ids=("manual_observation_ref_1",),
        provider_receipt_reference_ids=("provider_receipt_ref_1",),
        selector_audit_reference_ids=(selector_id,),
        database_review_receipt_reference_ids=("database_review_receipt_1",),
        release_action_receipt_reference_ids=("release_action_receipt_1",),
        created_at_utc="2026-08-08T12:00:00Z",
    )


def test_source_record_review_workflow_summarizes_all_typed_reference_buckets() -> None:
    registry = build_source_site_method_audit_registry()
    record = _record()
    receipt = build_source_record_review_annotation_receipt(
        grabbed_source_record_id=record.grabbed_source_record_id,
        operator_note="Cross-link source record to generic comments selector audit.",
        cross_linked_audit_row_ids=record.selector_audit_reference_ids,
    )

    workflow = build_source_record_review_workflow(
        (record,),
        site_method_registry=registry,
        annotation_receipts=(receipt,),
    )
    data = workflow.to_dict()
    rendered = source_record_review_workflow_to_json(workflow)
    row = data["rows"][0]

    assert workflow.workflow_id.startswith("source_record_review_workflow_")
    assert workflow.source_record_count == 1
    assert workflow.reference_bucket_count == len(REFERENCE_BUCKETS)
    assert workflow.reference_count == len(REFERENCE_BUCKETS)
    assert workflow.selector_audit_cross_link_count == 1
    assert workflow.annotation_receipt_count == 1
    assert row["metadata_only"] is True
    assert row["user_review_required"] is True
    assert row["file_move_performed"] is False
    assert row["live_execution_performed"] is False
    assert row["completed_evidence_claimed"] is False
    assert row["automatic_classification_performed"] is False
    assert row["selector_audit_cross_links"][0]["method_id"] == "generic_comments_site_specific_selector"
    assert row["annotation_receipts"][0]["operator_note"].startswith("Cross-link")
    assert "completed evidence" not in rendered.lower()
    assert "C:\\Users\\fahad" not in rendered


def test_source_record_review_workflow_is_deterministic_and_metadata_only() -> None:
    registry = build_source_site_method_audit_registry()
    record = _record()

    first = build_source_record_review_workflow((record,), site_method_registry=registry)
    second = build_source_record_review_workflow((record,), site_method_registry=registry)

    assert first.to_dict() == second.to_dict()
    assert first.no_file_movement_performed is True
    assert first.no_live_execution_performed is True
    assert first.no_completed_evidence_claimed is True
    assert first.no_automatic_classification_performed is True


def run_self_test() -> None:
    test_source_record_review_workflow_summarizes_all_typed_reference_buckets()
    test_source_record_review_workflow_is_deterministic_and_metadata_only()


if __name__ == "__main__":
    run_self_test()
    print("Source record review workflow self-test passed.")
