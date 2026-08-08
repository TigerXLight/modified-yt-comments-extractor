from source_adapter_audit_registry import (
    AUDIT_STATUS_AUDIT_REQUIRED,
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
    assert registry.audit_required_count >= 5
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
    assert twitter_public.audit_status == AUDIT_STATUS_AUDIT_REQUIRED
    assert twitter_public.execution_status == "not_yet_executed"
    assert twitter_public.archive_strategy == "archive_fallback_required_before_live_review"
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
    assert archive_only.audit_status == AUDIT_STATUS_AUDIT_REQUIRED
    assert archive_only.archive_strategy == "operator_supplied_no_provider_call"
    assert archive_only.archive_submission_performed is False

    review_entries = source_adapter_audit_entries_requiring_review(registry)
    assert {entry.method_id for entry in review_entries} == {
        "archive_only_import",
        "generic_article_comments",
        "generic_article_html",
        "twitter_x_public_post_archive",
        "twitter_x_reply_thread_archive",
    }


def test_source_adapter_audit_registry_serializes_without_execution_claims() -> None:
    registry = build_source_adapter_audit_registry()
    rendered = source_adapter_audit_registry_to_json(registry)

    assert rendered == source_adapter_audit_registry_to_json(registry)
    assert "not_yet_executed" in rendered
    assert "audit_required" in rendered
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


def run_self_test() -> None:
    test_source_adapter_audit_registry_covers_required_method_profiles()
    test_source_adapter_audit_entries_record_required_mappings_and_gaps()
    test_source_adapter_audit_registry_serializes_without_execution_claims()
    test_source_adapter_audit_registry_validation_rejects_unsafe_flags()


if __name__ == "__main__":
    run_self_test()
    print("Source adapter audit registry self-test passed.")
