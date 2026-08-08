from source_evidence_release_readiness import (
    RELEASE_TARGET_KINDS,
    build_source_evidence_release_readiness,
    source_evidence_release_readiness_to_json,
    validate_source_evidence_release_readiness,
)


def _readiness():
    return build_source_evidence_release_readiness(
        source_row_id="source_row_123",
        adapter_id="msn",
        selected_modes=("comments", "webpage"),
        execution_gate_status="APPROVAL_REQUIRED",
        execution_gate_action_kinds=("ARCHIVE_SUBMIT", "LIVE_SITE_CAPTURE"),
        queue_item_count=5,
        total_export_asset_count=7,
        review_manifest_package_id="source-review",
        queue_review_store_id="queue-review-store",
        created_at_utc="2026-08-08T12:00:00Z",
    )


def test_release_readiness_is_metadata_only_and_approval_required() -> None:
    readiness = _readiness()
    data = readiness.to_dict()

    assert data["release_status"] == "RELEASE_APPROVAL_REQUIRED"
    assert data["review_status"] == "USER_REVIEW_REQUIRED"
    assert data["metadata_only"] is True
    assert data["approval_required"] is True
    assert data["manual_operator_required"] is True
    assert data["release_upload_performed"] is False
    assert data["file_library_publish_performed"] is False
    assert data["operator_signoff_performed"] is False
    assert data["completed_release_claimed"] is False
    assert data["file_existence_claimed"] is False
    assert data["automatic_classification"] is False
    assert data["target_count"] == len(RELEASE_TARGET_KINDS)
    assert [target["target_kind"] for target in data["targets"]] == list(RELEASE_TARGET_KINDS)
    assert all(target["release_upload_performed"] is False for target in data["targets"])
    validate_source_evidence_release_readiness(data)


def test_release_readiness_is_deterministic_and_summary_only() -> None:
    first = _readiness()
    second = _readiness()

    assert first.to_dict() == second.to_dict()
    encoded = source_evidence_release_readiness_to_json(first)
    assert "release_upload_target_receipt" in encoded
    assert "file_library_publish_receipt" in encoded
    assert "operator_signoff_receipt" in encoded
    assert "C:\\Users\\fahad" not in encoded
    assert '"raw_payload_included": false' in encoded
    assert "completed_release_claimed" in encoded


def test_release_readiness_validation_rejects_execution_claims() -> None:
    data = _readiness().to_dict()
    data["release_upload_performed"] = True
    try:
        validate_source_evidence_release_readiness(data)
    except ValueError as error:
        assert "release_upload_performed" in str(error)
    else:
        raise AssertionError("Release readiness validation should reject upload claims")


def run_self_test() -> None:
    test_release_readiness_is_metadata_only_and_approval_required()
    test_release_readiness_is_deterministic_and_summary_only()
    test_release_readiness_validation_rejects_execution_claims()


if __name__ == "__main__":
    run_self_test()
    print("Source evidence release readiness self-test passed.")
