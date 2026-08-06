import json

from evidence_activity_log import (
    ActivityActorType,
    ActivityType,
    ActivityLogPrivacyPolicy,
    behavior_activity_log_summary_to_json,
    behavior_activity_record_to_json,
    build_behavior_activity_log_summary,
    build_behavior_activity_log_summary_text,
    build_behavior_activity_record,
)


def _sample_record():
    return build_behavior_activity_record(
        session_id="session-1",
        activity_type=ActivityType.SOURCE_URL_ADDED,
        actor_type=ActivityActorType.USER,
        activity_time_utc="2026-08-06T12:00:00Z",
        actor_label="operator",
        item_id="source-row-1",
        source_url="https://example.test/article",
        before_state_hash="before_abc",
        after_state_hash="after_def",
        changed_fields=("source_url", "source_url", "status"),
        user_note="operator note text not stored",
        evidence_basis="manual operator supplied",
        export_package_id="export-1",
        database_root_label="registered root label not path",
        metadata_summary={
            "row_count": 1,
            "scope": "source_url_intake",
            "nested": {"safe_flag": True},
        },
    )


def test_behavior_activity_record_is_deterministic_and_summary_only() -> None:
    record = _sample_record()
    repeated = _sample_record()

    assert record == repeated
    assert record.activity_id.startswith("activity_")
    assert record.source_url_recorded is True
    assert record.source_url_hash.startswith("source_url_")
    assert record.source_host_label == "example.test"
    assert record.changed_fields == ("source_url", "status")
    assert record.actor_label_recorded is True
    assert record.user_note_recorded is True
    assert record.evidence_basis_recorded is True
    assert record.database_root_recorded is True
    assert record.metadata_only is True
    assert record.local_only is True
    assert record.telemetry_enabled is False
    assert record.persistence_enabled is False
    assert record.file_read_performed is False
    assert record.file_check_performed is False
    assert record.file_move_performed is False
    assert record.file_existence_claimed is False
    assert record.full_local_path_included is False
    assert record.raw_payload_included is False
    assert record.completed_evidence_claimed is False
    assert record.verified_evidence_claimed is False
    assert record.automatic_classification is False
    assert record.protected_attribute_inference is False

    data = json.loads(behavior_activity_record_to_json(record))
    assert data["activity_type"] == "SOURCE_URL_ADDED"
    assert data["actor_type"] == "USER"
    assert data["metadata_summary"]["nested"]["safe_flag"] is True
    assert "https://example.test/article" not in json.dumps(data)
    assert "operator note text not stored" not in json.dumps(data)
    assert "manual operator supplied" not in json.dumps(data)


def test_behavior_activity_summary_is_order_stable_and_counts_only() -> None:
    source_record = _sample_record()
    export_record = build_behavior_activity_record(
        session_id="session-1",
        activity_type=ActivityType.EXPORT_QUEUE_REVIEWED,
        actor_type=ActivityActorType.APPLICATION,
        activity_time_utc="2026-08-06T12:01:00Z",
        item_id="queue-summary-1",
        changed_fields=("review_status",),
        metadata_summary={"queue_item_count": 3},
    )

    summary = build_behavior_activity_log_summary((export_record, source_record))
    repeated = build_behavior_activity_log_summary((source_record, export_record))

    assert summary == repeated
    assert summary.summary_id.startswith("activity_summary_")
    assert summary.status == "USER_REVIEW_REQUIRED"
    assert summary.record_count == 2
    assert summary.source_url_recorded_count == 1
    assert summary.source_host_labels == ("example.test",)
    assert summary.changed_field_count == 3
    assert summary.user_note_recorded_count == 1
    assert summary.evidence_basis_recorded_count == 1
    assert summary.activity_type_counts == (
        {"activity_type": "EXPORT_QUEUE_REVIEWED", "count": 1},
        {"activity_type": "SOURCE_URL_ADDED", "count": 1},
    )
    assert summary.actor_type_counts == (
        {"actor_type": "APPLICATION", "count": 1},
        {"actor_type": "USER", "count": 1},
    )
    assert summary.telemetry_enabled is False
    assert summary.persistence_enabled is False
    assert summary.file_read_performed is False
    assert summary.file_check_performed is False
    assert summary.file_move_performed is False
    assert summary.file_existence_claimed is False
    assert summary.completed_evidence_claimed is False
    assert summary.verified_evidence_claimed is False
    assert summary.automatic_classification is False
    assert summary.protected_attribute_inference is False

    rendered_json = behavior_activity_log_summary_to_json(summary)
    rendered_text = build_behavior_activity_log_summary_text(summary)
    assert "https://example.test/article" not in rendered_json
    assert "T:\\Evidence" not in rendered_json
    assert "Raw payload/full local path flags: false" in rendered_text


def test_empty_behavior_activity_summary_stays_non_executing() -> None:
    summary = build_behavior_activity_log_summary(())

    assert summary.status == "NO_ACTIVITY_RECORDS"
    assert summary.record_count == 0
    assert summary.metadata_only is True
    assert summary.telemetry_enabled is False
    assert summary.persistence_enabled is False
    assert summary.file_read_performed is False
    assert summary.file_check_performed is False
    assert summary.file_move_performed is False
    assert summary.file_existence_claimed is False
    assert summary.completed_evidence_claimed is False
    assert summary.verified_evidence_claimed is False


def test_activity_privacy_policy_defaults_disable_runtime_risky_behavior() -> None:
    policy = ActivityLogPrivacyPolicy()
    data = policy.to_dict()

    assert data["metadata_only"] is True
    assert data["local_only"] is True
    assert data["telemetry_enabled"] is False
    assert data["persistence_enabled"] is False
    assert data["raw_payloads_allowed"] is False
    assert data["full_local_paths_allowed"] is False
    assert data["file_reads_allowed"] is False
    assert data["file_checks_allowed"] is False
    assert data["file_moves_allowed"] is False
    assert data["file_existence_claims_allowed"] is False
    assert data["completed_evidence_claims_allowed"] is False
    assert data["verified_evidence_claims_allowed"] is False
    assert data["automatic_classification_allowed"] is False
    assert data["protected_attribute_inference_allowed"] is False
    assert data["credentials_allowed"] is False
    assert data["network_allowed"] is False
    assert data["browser_automation_allowed"] is False


def test_activity_metadata_rejects_secrets_raw_payloads_paths_and_file_state() -> None:
    unsafe_cases = (
        {"api_key": "secret"},
        {"nested": {"Authorization": "Bearer secret"}},
        {"raw_comment": "comment body"},
        {"raw_transcript": "transcript body"},
        {"tweet_text": "tweet body"},
        {"local_path": "relative.txt"},
        {"file_exists": True},
        {"sha256": "abc123"},
        {"safe_label": "T:\\Evidence\\private.txt"},
        {"nested": ["ok", {"safe_label": "\\\\server\\share\\file.txt"}]},
    )

    for metadata in unsafe_cases:
        try:
            build_behavior_activity_record(
                session_id="session-unsafe",
                activity_type=ActivityType.REVIEW_NOTE_ADDED,
                actor_type=ActivityActorType.USER,
                activity_time_utc="2026-08-06T12:02:00Z",
                metadata_summary=metadata,
            )
        except ValueError as exc:
            assert "Unsafe" in str(exc)
        else:
            raise AssertionError(f"unsafe metadata should fail: {metadata!r}")


def test_activity_record_requires_explicit_deterministic_inputs() -> None:
    try:
        build_behavior_activity_record(
            session_id="",
            activity_type=ActivityType.SOURCE_URL_ADDED,
            actor_type=ActivityActorType.USER,
            activity_time_utc="2026-08-06T12:00:00Z",
        )
    except ValueError as exc:
        assert "session_id is required" in str(exc)
    else:
        raise AssertionError("missing session_id should fail")

    try:
        build_behavior_activity_record(
            session_id="session-1",
            activity_type=ActivityType.SOURCE_URL_ADDED,
            actor_type=ActivityActorType.USER,
            activity_time_utc="",
        )
    except ValueError as exc:
        assert "activity_time_utc is required" in str(exc)
    else:
        raise AssertionError("missing timestamp should fail")


def run_self_test() -> None:
    test_behavior_activity_record_is_deterministic_and_summary_only()
    test_behavior_activity_summary_is_order_stable_and_counts_only()
    test_empty_behavior_activity_summary_stays_non_executing()
    test_activity_privacy_policy_defaults_disable_runtime_risky_behavior()
    test_activity_metadata_rejects_secrets_raw_payloads_paths_and_file_state()
    test_activity_record_requires_explicit_deterministic_inputs()


if __name__ == "__main__":
    run_self_test()
    print("Evidence activity log self-test passed.")
