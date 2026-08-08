from source_grabbed_record import (
    build_grabbed_source_record,
    grabbed_source_record_to_json,
    validate_grabbed_source_record,
)


def test_grabbed_source_record_is_deterministic_and_metadata_only() -> None:
    first = build_grabbed_source_record(
        source_row_id="source_row_1",
        source_url="https://www.msn.com/en-gb/news/example/ar-AA123456",
        canonical_url="https://www.msn.com/en-gb/news/example/ar-AA123456",
        adapter_id="msn",
        relative_artifact_paths=(
            "capture/source_row_1/raw.html",
            r"C:\Users\fahad\secret\raw.html",
            "unsafe-name-only.json",
        ),
        selected_modes=("comments", "webpage"),
        evidence_item_ids=("queue_2", "queue_1"),
        total_export_item_ids=("manifest_asset_1",),
        archive_metadata=(
            {
                "service_id": "wayback",
                "status": "not_checked",
                "archive_url": "https://web.archive.org/example",
                "provider_call_performed": False,
                "submission_performed": False,
            },
        ),
        operator_approval_reference="execution_gate_plan_123",
        article_reference_ids=("artifact_article",),
        comment_reference_ids=("artifact_comments",),
        media_reference_ids=("artifact_media",),
        transcript_reference_ids=("artifact_transcript",),
        archive_url_references=("https://web.archive.org/example",),
        screenshot_reference_ids=("artifact_screenshot",),
        snapshot_reference_ids=("artifact_snapshot",),
        manual_observation_reference_ids=("manual_observation_1",),
        provider_receipt_reference_ids=("archive_status:wayback:not_checked",),
        selector_audit_reference_ids=("selector_audit_generic_comments",),
        database_review_receipt_reference_ids=("database_review_receipt_1",),
        release_action_receipt_reference_ids=("release_action_receipt_1",),
        created_at_utc="2026-08-08T12:00:00Z",
    )
    second = build_grabbed_source_record(
        source_row_id="source_row_1",
        source_url="https://www.msn.com/en-gb/news/example/ar-AA123456",
        canonical_url="https://www.msn.com/en-gb/news/example/ar-AA123456",
        adapter_id="msn",
        relative_artifact_paths=(
            "unsafe-name-only.json",
            "capture/source_row_1/raw.html",
            r"C:\Users\fahad\secret\raw.html",
        ),
        selected_modes=("webpage", "comments"),
        evidence_item_ids=("queue_1", "queue_2"),
        total_export_item_ids=("manifest_asset_1",),
        archive_metadata=(
            {
                "archive_service": "wayback",
                "archive_status": "not_checked",
                "archive_url": "https://web.archive.org/example",
                "provider_call_performed": False,
                "submission_performed": False,
            },
        ),
        operator_approval_reference="execution_gate_plan_123",
        article_reference_ids=("artifact_article",),
        comment_reference_ids=("artifact_comments",),
        media_reference_ids=("artifact_media",),
        transcript_reference_ids=("artifact_transcript",),
        archive_url_references=("https://web.archive.org/example",),
        screenshot_reference_ids=("artifact_screenshot",),
        snapshot_reference_ids=("artifact_snapshot",),
        manual_observation_reference_ids=("manual_observation_1",),
        provider_receipt_reference_ids=("archive_status:wayback:not_checked",),
        selector_audit_reference_ids=("selector_audit_generic_comments",),
        database_review_receipt_reference_ids=("database_review_receipt_1",),
        release_action_receipt_reference_ids=("release_action_receipt_1",),
        created_at_utc="2026-08-08T12:00:00Z",
    )

    assert first.to_dict() == second.to_dict()
    assert first.capture_method_profile_id == "msn_article_comments_shadow_manual_import"
    assert first.capture_method_family == "article_comments_manual_observation"
    assert first.relative_artifact_paths == ("capture/source_row_1/raw.html",)
    assert first.archive_receipts[0].provider_call_performed is False
    assert first.archive_receipts[0].submission_performed is False
    assert first.article_reference_ids == ("artifact_article",)
    assert first.comment_reference_ids == ("artifact_comments",)
    assert first.media_reference_ids == ("artifact_media",)
    assert first.transcript_reference_ids == ("artifact_transcript",)
    assert first.archive_url_references == ("https://web.archive.org/example",)
    assert first.screenshot_reference_ids == ("artifact_screenshot",)
    assert first.snapshot_reference_ids == ("artifact_snapshot",)
    assert first.manual_observation_reference_ids == ("manual_observation_1",)
    assert first.provider_receipt_reference_ids == ("archive_status:wayback:not_checked",)
    assert first.selector_audit_reference_ids == ("selector_audit_generic_comments",)
    assert first.database_review_receipt_reference_ids == ("database_review_receipt_1",)
    assert first.release_action_receipt_reference_ids == ("release_action_receipt_1",)
    assert first.to_dict()["article_reference_count"] == 1
    assert first.to_dict()["provider_receipt_reference_count"] == 1
    assert first.to_dict()["selector_audit_reference_count"] == 1
    assert first.to_dict()["database_review_receipt_reference_count"] == 1
    assert first.to_dict()["release_action_receipt_reference_count"] == 1
    assert first.file_existence_claimed is False
    assert first.full_local_path_included is False
    assert first.raw_payload_included is False
    assert first.live_capture_performed is False
    assert first.browser_automation_performed is False
    assert first.evidence_file_move_performed is False
    assert len(first.content_digest_sha256) == 64
    validate_grabbed_source_record(first.to_dict())

    rendered = grabbed_source_record_to_json(first)
    assert r"C:\Users\fahad" not in rendered
    assert "secret" not in rendered


def test_grabbed_source_record_validation_rejects_unsafe_claims() -> None:
    record = build_grabbed_source_record(
        source_row_id="source_row_1",
        source_url="https://x.com/example/status/123",
        canonical_url="https://x.com/example/status/123",
        adapter_id="twitter_x",
        relative_artifact_paths=("capture/source_row_1/summary.json",),
        selected_modes=("comments",),
    ).to_dict()
    record["browser_automation_performed"] = True

    try:
        validate_grabbed_source_record(record)
    except ValueError as error:
        assert "browser_automation_performed" in str(error)
    else:
        raise AssertionError("Unsafe grabbed source record claim should be rejected")


def run_self_test() -> None:
    test_grabbed_source_record_is_deterministic_and_metadata_only()
    test_grabbed_source_record_validation_rejects_unsafe_claims()


if __name__ == "__main__":
    run_self_test()
    print("Source grabbed record self-test passed.")
