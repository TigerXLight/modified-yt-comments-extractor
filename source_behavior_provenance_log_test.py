from source_behavior_provenance_log import (
    BehaviorActionType,
    BehaviorLogEntry,
    build_example_behavior_provenance_log,
    build_execution_bridge_behavior_log,
    build_source_operational_behavior_log,
    chain_behavior_entries,
)


def test_behavior_log_is_hash_chained() -> None:
    log = build_example_behavior_provenance_log()
    data = log.to_dict()
    assert data["chain_valid"] is True
    assert data["entry_count"] == 3
    assert data["witness_count"] == 2
    assert data["completed_evidence_claimed"] is False
    assert data["file_movement_performed"] is False


def test_secret_like_detail_is_redacted() -> None:
    entries = chain_behavior_entries(
        [
            BehaviorLogEntry(
                entry_id="secret_test",
                timestamp_utc="2026-08-08T18:00:00Z",
                action_type=BehaviorActionType.GET_CLICKED,
                session_id="session_secret",
                actor_label="operator",
                details={"api_key": "abc123", "normal": "kept"},
            )
        ]
    )
    payload = entries[0].to_dict()
    assert payload["details"]["api_key"] == "[REDACTED]"
    assert payload["details"]["normal"] == "kept"


def test_witness_roles_distinguish_author_and_operator() -> None:
    log = build_example_behavior_provenance_log()
    roles = {w.witness_role for w in log.witnesses}
    assert "article_author_or_publisher_byline" in roles
    assert "software_operator_capture_witness" in roles


def test_source_operational_behavior_log_records_review_flow() -> None:
    log = build_source_operational_behavior_log(
        session_id="session1",
        source_url="https://example.invalid/story",
        movement_preview_ref="movement_preview_1",
    )
    data = log.to_dict()
    action_types = {entry["action_type"] for entry in data["entries"]}
    assert BehaviorActionType.SOURCE_URL_MEDIA_ROW_CREATED.value in action_types
    assert BehaviorActionType.EVIDENCE_MOVEMENT_PREVIEWED.value in action_types
    assert BehaviorActionType.OPERATOR_COMMAND_PACK_CREATED.value in action_types
    assert BehaviorActionType.MANUAL_SMOKE_CHECKLIST_CREATED.value in action_types
    assert data["chain_valid"] is True
    assert data["file_movement_performed"] is False


def test_source_operational_behavior_log_detects_tamper() -> None:
    log = build_source_operational_behavior_log(
        session_id="session_tamper",
        source_url="https://example.invalid/story",
    )
    entries = list(log.entries)
    original = entries[1]
    entries[1] = BehaviorLogEntry(
        entry_id=original.entry_id,
        timestamp_utc=original.timestamp_utc,
        action_type=original.action_type,
        session_id=original.session_id,
        actor_label=original.actor_label,
        source_url=original.source_url,
        details=original.details,
        previous_entry_hash="wrong",
    )
    assert log.__class__(log_id=log.log_id, entries=tuple(entries)).validate_chain() is False


def test_execution_bridge_behavior_log_records_local_execution_events() -> None:
    log = build_execution_bridge_behavior_log(
        session_id="execution_session",
        source_url="local-fixture://story",
        screenshot_count=2,
        comment_count=3,
        livechat_event_count=4,
        media_resource_count=5,
        media_download_count=1,
        archive_request_count=2,
        offline_bundle_name="bundle.zip",
        movement_receipt_ref="movement_receipt_1",
        challenge_paused=True,
        failed_reason="fixture_failure",
    )
    data = log.to_dict()
    action_types = {entry["action_type"] for entry in data["entries"]}
    assert BehaviorActionType.SCREENSHOT_CAPTURE_EXECUTED.value in action_types
    assert BehaviorActionType.ARTICLE_CAPTURE_EXECUTED.value in action_types
    assert BehaviorActionType.COMMENTS_CAPTURE_EXECUTED.value in action_types
    assert BehaviorActionType.LIVECHAT_CAPTURE_EXECUTED.value in action_types
    assert BehaviorActionType.MEDIA_DOWNLOAD_EXECUTED.value in action_types
    assert BehaviorActionType.ARCHIVE_PROVIDER_REQUEST_EXECUTED.value in action_types
    assert BehaviorActionType.OFFLINE_BUNDLE_WRITTEN.value in action_types
    assert BehaviorActionType.EVIDENCE_MOVEMENT_EXECUTED.value in action_types
    assert BehaviorActionType.CHALLENGE_PAUSED.value in action_types
    assert BehaviorActionType.EXECUTION_FAILED.value in action_types
    assert data["chain_valid"] is True
    assert data["completed_evidence_claimed"] is False


def main() -> None:
    test_behavior_log_is_hash_chained()
    test_secret_like_detail_is_redacted()
    test_witness_roles_distinguish_author_and_operator()
    test_source_operational_behavior_log_records_review_flow()
    test_source_operational_behavior_log_detects_tamper()
    test_execution_bridge_behavior_log_records_local_execution_events()
    print("source_behavior_provenance_log_test: OK")


if __name__ == "__main__":
    main()
