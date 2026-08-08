from source_site_method_audit_registry import (
    SITE_METHOD_STATUS_METADATA_AUDIT_READY,
    SITE_METHOD_STATUS_SELECTOR_AUDIT_REQUIRED,
    build_source_site_selector_audit_pack_collection,
    build_source_site_method_audit_registry,
    source_site_selector_audit_pack_by_method,
    source_site_selector_audit_pack_collection_to_json,
    source_site_method_audit_registry_to_json,
    source_site_method_audit_row_by_method,
    source_site_method_audit_rows_by_status,
    validate_source_site_selector_audit_pack_collection,
    validate_source_site_method_audit_registry,
)


REQUIRED_METHODS = {
    "msn_article",
    "msn_shadow_dom_comments",
    "twitter_x_public_post_archive_manual_import",
    "twitter_x_reply_thread_archive_manual_import",
    "youtube_media_transcript",
    "youtube_comments",
    "generic_article_html",
    "generic_comments_manual_import",
    "generic_comments_site_specific_selector",
    "generic_comments_archive_only_import",
    "archive_only_import",
}


def test_site_method_audit_registry_covers_named_site_methods() -> None:
    registry = build_source_site_method_audit_registry()
    data = registry.to_dict()

    assert {row.method_id for row in registry.rows} == REQUIRED_METHODS
    assert registry.row_count == len(REQUIRED_METHODS)
    assert registry.selector_audit_required_count == 1
    assert registry.metadata_audit_ready_count == len(REQUIRED_METHODS) - 1
    assert registry.not_yet_executed_count == len(REQUIRED_METHODS)
    assert registry.live_approved_only_count == 1
    assert data["review_status"] == "USER_REVIEW_REQUIRED"
    assert data["metadata_only"] is True
    assert data["local_only"] is True
    assert data["live_execution_performed"] is False
    assert data["browser_automation_performed"] is False
    assert data["provider_call_performed"] is False
    assert data["archive_submission_performed"] is False
    assert data["download_performed"] is False
    assert data["file_move_performed"] is False
    assert data["automatic_classification"] is False
    assert data["sensitive_inference_prohibited"] is True
    validate_source_site_method_audit_registry(data)


def test_generic_comments_selector_gap_is_explicit_tracked_row() -> None:
    registry = build_source_site_method_audit_registry()
    selector = source_site_method_audit_row_by_method(
        registry,
        "generic_comments_site_specific_selector",
    )
    manual = source_site_method_audit_row_by_method(registry, "generic_comments_manual_import")
    archive_only = source_site_method_audit_row_by_method(
        registry,
        "generic_comments_archive_only_import",
    )

    assert selector is not None
    assert selector.status == SITE_METHOD_STATUS_SELECTOR_AUDIT_REQUIRED
    assert selector.selector_audit_required is True
    assert selector.live_approved_only is True
    assert selector.method_audit_metadata["site_specific_selector_required_before_live_execution"] is True
    assert selector.method_audit_metadata["manual_observation_import_available_now"] is True
    assert selector.method_audit_metadata["archive_only_comment_evidence_review_available_now"] is True
    assert selector.method_audit_metadata["universal_selector_support_claimed"] is False
    assert "named_site_selector_audit" in selector.operator_approval_requirement

    assert manual is not None
    assert manual.status == SITE_METHOD_STATUS_METADATA_AUDIT_READY
    assert manual.comment_support == "manual_observation_or_local_import_available_now"

    assert archive_only is not None
    assert archive_only.status == SITE_METHOD_STATUS_METADATA_AUDIT_READY
    assert archive_only.comment_support == "archive_only_review_available_now"

    selector_rows = source_site_method_audit_rows_by_status(
        registry,
        SITE_METHOD_STATUS_SELECTOR_AUDIT_REQUIRED,
    )
    assert selector_rows == (selector,)


def test_site_method_registry_serializes_without_execution_claims() -> None:
    registry = build_source_site_method_audit_registry()
    rendered = source_site_method_audit_registry_to_json(registry)

    assert rendered == source_site_method_audit_registry_to_json(registry)
    assert "selector_audit_required" in rendered
    assert "generic_comments_site_specific_selector" in rendered
    assert "live verified" not in rendered.lower()
    assert "completed evidence" not in rendered.lower()
    assert "C:\\Users\\fahad" not in rendered
    assert '"live_execution_performed": false' in rendered
    assert '"browser_automation_performed": false' in rendered
    assert '"file_move_performed": false' in rendered


def test_selector_audit_pack_collection_tracks_typed_grabbed_source_buckets() -> None:
    registry = build_source_site_method_audit_registry()
    collection = build_source_site_selector_audit_pack_collection(registry)
    data = collection.to_dict()
    rendered = source_site_selector_audit_pack_collection_to_json(collection)

    assert collection.pack_count == registry.row_count
    assert collection.selector_audit_required_count == registry.selector_audit_required_count
    assert collection.live_approved_only_count == registry.live_approved_only_count
    assert rendered == source_site_selector_audit_pack_collection_to_json(collection)
    assert data["metadata_only"] is True
    assert data["live_execution_performed"] is False
    validate_source_site_selector_audit_pack_collection(data)

    msn_article = source_site_selector_audit_pack_by_method(collection, "msn_article")
    assert msn_article is not None
    assert "article_reference_ids" in msn_article.typed_grabbed_source_reference_buckets
    assert "snapshot_reference_ids" in msn_article.typed_grabbed_source_reference_buckets
    assert "selector_audit_reference_ids" in msn_article.typed_grabbed_source_reference_buckets

    generic_comments = source_site_selector_audit_pack_by_method(
        collection,
        "generic_comments_site_specific_selector",
    )
    assert generic_comments is not None
    assert generic_comments.selector_audit_required is True
    assert "comment_reference_ids" in generic_comments.typed_grabbed_source_reference_buckets
    assert "manual_observation_reference_ids" in generic_comments.typed_grabbed_source_reference_buckets
    assert "live verified" not in rendered.lower()
    assert "completed evidence" not in rendered.lower()


def test_site_method_registry_validation_rejects_unsafe_flags() -> None:
    data = build_source_site_method_audit_registry().to_dict()
    data["rows"][0]["live_execution_performed"] = True

    try:
        validate_source_site_method_audit_registry(data)
    except ValueError as error:
        assert "live_execution_performed" in str(error)
    else:
        raise AssertionError("Unsafe site/method audit row flag should be rejected")

    data = build_source_site_method_audit_registry().to_dict()
    data["rows"][0]["method_audit_metadata"]["completed_evidence_claimed"] = True
    try:
        validate_source_site_method_audit_registry(data)
    except ValueError as error:
        assert "completed_evidence_claimed" in str(error)
    else:
        raise AssertionError("Unsafe site/method audit metadata flag should be rejected")


def run_self_test() -> None:
    test_site_method_audit_registry_covers_named_site_methods()
    test_generic_comments_selector_gap_is_explicit_tracked_row()
    test_site_method_registry_serializes_without_execution_claims()
    test_selector_audit_pack_collection_tracks_typed_grabbed_source_buckets()
    test_site_method_registry_validation_rejects_unsafe_flags()


if __name__ == "__main__":
    run_self_test()
    print("Source site/method audit registry self-test passed.")
