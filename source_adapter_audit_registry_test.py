from source_adapter_audit_registry import (
    AUDIT_STATUS_AUDIT_REQUIRED,
    AUDIT_STATUS_METADATA_AUDIT_READY,
    AUDIT_STATUS_METADATA_BRIDGE_AVAILABLE,
    AUDIT_STATUS_METADATA_SCAFFOLDED,
    build_source_adapter_audit_registry,
    source_adapter_audit_entries_requiring_review,
    source_adapter_audit_entry_by_method,
    source_adapter_audit_registry_to_json,
    validate_source_adapter_audit_registry,
)


REQUIRED_METHODS = {
    "msn_article_comments_shadow_manual_import",
    "twitter_x_public_post_archive",
    "twitter_x_reply_thread_archive",
    "youtube_media_transcript",
    "youtube_comments",
    "generic_article_html",
    "generic_article_comments",
    "manual_local_import",
    "archive_only_import",
}


def test_source_adapter_audit_registry_covers_required_method_profiles() -> None:
    registry = build_source_adapter_audit_registry()
    data = registry.to_dict()
    method_ids = {entry.method_id for entry in registry.entries}

    assert method_ids == REQUIRED_METHODS
    assert registry.entry_count == len(REQUIRED_METHODS)
    assert registry.audit_required_count == 0
    assert registry.not_yet_executed_count == registry.entry_count
    assert data["review_status"] == "USER_REVIEW_REQUIRED"
    assert data["metadata_only"] is True
    assert data["local_only"] is True
    assert data["live_execution_performed"] is False
    assert data["provider_call_performed"] is False
    assert data["browser_automation_performed"] is False
    assert data["archive_submission_performed"] is False
    assert data["download_performed"] is False
    assert data["file_move_performed"] is False
    assert data["automatic_classification"] is False
    assert data["sensitive_inference_prohibited"] is True
    validate_source_adapter_audit_registry(data)


def test_source_adapter_audit_entries_record_required_mappings_and_gaps() -> None:
    registry = build_source_adapter_audit_registry()
    msn = source_adapter_audit_entry_by_method(
        registry, "msn_article_comments_shadow_manual_import"
    )
    twitter_public = source_adapter_audit_entry_by_method(
        registry, "twitter_x_public_post_archive"
    )
    youtube_comments = source_adapter_audit_entry_by_method(registry, "youtube_comments")
    manual_import = source_adapter_audit_entry_by_method(registry, "manual_local_import")
    archive_only = source_adapter_audit_entry_by_method(registry, "archive_only_import")

    assert msn is not None
    assert msn.adapter_id == "msn"
    assert msn.audit_status == AUDIT_STATUS_METADATA_BRIDGE_AVAILABLE
    assert msn.comment_support == "manual_observation_supported"
    assert "ARTICLE_TEXT" in msn.required_artifacts
    assert "review_state" in msn.evidence_database_mapping
    assert "total_export_asset_metadata" in msn.total_export_mapping
    assert msn.operator_approval_required is True

    assert twitter_public is not None
    assert twitter_public.audit_status == AUDIT_STATUS_METADATA_AUDIT_READY
    assert twitter_public.execution_status == "not_yet_executed"
    assert twitter_public.archive_strategy == "operator_supplied_or_future_approved_wayback_archive_today_metadata"
    assert "canonical_url_expectation" in twitter_public.method_audit_metadata
    assert "archive_receipt_reference_policy" in twitter_public.method_audit_metadata
    assert twitter_public.provider_call_performed is False

    assert youtube_comments is not None
    assert youtube_comments.audit_status == AUDIT_STATUS_METADATA_BRIDGE_AVAILABLE
    assert youtube_comments.comment_support == "existing_output_metadata_only"
    assert youtube_comments.live_manual_mode == "manual_operator_only"

    assert manual_import is not None
    assert manual_import.audit_status == AUDIT_STATUS_METADATA_SCAFFOLDED
    assert manual_import.credential_requirement == "none"
    assert manual_import.media_support == "local_file_metadata_only"

    assert archive_only is not None
    assert archive_only.audit_status == AUDIT_STATUS_METADATA_AUDIT_READY
    assert archive_only.archive_strategy == "operator_supplied_no_provider_call"
    assert archive_only.method_audit_metadata["archive_url_required"] is True
    assert archive_only.method_audit_metadata["no_live_site_requirement"] is True
    assert archive_only.archive_submission_performed is False

    review_entries = source_adapter_audit_entries_requiring_review(registry)
    assert review_entries == ()


def test_source_adapter_audit_resolution_rows_include_method_specific_metadata() -> None:
    registry = build_source_adapter_audit_registry()
    twitter_reply = source_adapter_audit_entry_by_method(registry, "twitter_x_reply_thread_archive")
    generic_html = source_adapter_audit_entry_by_method(registry, "generic_article_html")
    generic_comments = source_adapter_audit_entry_by_method(registry, "generic_article_comments")

    assert twitter_reply is not None
    assert twitter_reply.audit_status == AUDIT_STATUS_METADATA_AUDIT_READY
    assert twitter_reply.comment_support == "manual_or_local_export_thread_metadata"
    assert twitter_reply.method_audit_metadata["parent_post_reference_policy"]
    assert twitter_reply.method_audit_metadata["reply_ids_policy"]
    assert twitter_reply.method_audit_metadata["thread_boundary_policy"]
    assert twitter_reply.method_audit_metadata["manual_observation_metadata"] == (
        "visible reply count",
        "deleted_or_unavailable_reply_state",
        "sort/filter context",
        "operator note",
    )

    assert generic_html is not None
    assert generic_html.audit_status == AUDIT_STATUS_METADATA_AUDIT_READY
    assert "FINAL_DOM" in generic_html.required_artifacts
    assert generic_html.method_audit_metadata["canonical_url_policy"]
    assert generic_html.method_audit_metadata["text_extraction_receipt_policy"]
    assert generic_html.method_audit_metadata["review_status"] == "USER_REVIEW_REQUIRED"

    assert generic_comments is not None
    assert generic_comments.audit_status == AUDIT_STATUS_METADATA_AUDIT_READY
    assert generic_comments.comment_support == "manual_or_fixture_only_site_specific_selectors_audit_required"
    assert generic_comments.method_audit_metadata["site_specific_selector_status"] == AUDIT_STATUS_AUDIT_REQUIRED
    assert generic_comments.method_audit_metadata["tracked_selector_audit_method_id"] == (
        "generic_comments_site_specific_selector"
    )
    assert generic_comments.method_audit_metadata["source_boundary_policy"]


def test_source_adapter_audit_registry_serializes_without_execution_claims() -> None:
    registry = build_source_adapter_audit_registry()
    rendered = source_adapter_audit_registry_to_json(registry)

    assert rendered == source_adapter_audit_registry_to_json(registry)
    assert "not_yet_executed" in rendered
    assert "metadata_audit_ready" in rendered
    assert "site_specific_selector_status" in rendered
    assert "live verified" not in rendered.lower()
    assert "completed evidence" not in rendered.lower()
    assert "C:\\Users\\fahad" not in rendered
    assert "api_key_value" not in rendered
    assert '"live_execution_performed": false' in rendered
    assert '"browser_automation_performed": false' in rendered
    assert '"file_move_performed": false' in rendered


def test_source_adapter_audit_registry_validation_rejects_unsafe_flags() -> None:
    data = build_source_adapter_audit_registry().to_dict()
    data["entries"][0]["download_performed"] = True

    try:
        validate_source_adapter_audit_registry(data)
    except ValueError as error:
        assert "download_performed" in str(error)
    else:
        raise AssertionError("Unsafe audit registry flag should be rejected")

    data = build_source_adapter_audit_registry().to_dict()
    data["entries"][0]["method_audit_metadata"]["browser_automation_performed"] = True
    try:
        validate_source_adapter_audit_registry(data)
    except ValueError as error:
        assert "browser_automation_performed" in str(error)
    else:
        raise AssertionError("Unsafe audit registry method metadata flag should be rejected")


def run_self_test() -> None:
    test_source_adapter_audit_registry_covers_required_method_profiles()
    test_source_adapter_audit_entries_record_required_mappings_and_gaps()
    test_source_adapter_audit_resolution_rows_include_method_specific_metadata()
    test_source_adapter_audit_registry_serializes_without_execution_claims()
    test_source_adapter_audit_registry_validation_rejects_unsafe_flags()


if __name__ == "__main__":
    run_self_test()
    print("Source adapter audit registry self-test passed.")
