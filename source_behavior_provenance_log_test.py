from source_behavior_provenance_log import (
    BehaviorActionType,
    BehaviorLogEntry,
    build_example_behavior_provenance_log,
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


def main() -> None:
    test_behavior_log_is_hash_chained()
    test_secret_like_detail_is_redacted()
    test_witness_roles_distinguish_author_and_operator()
    test_source_operational_behavior_log_records_review_flow()
    test_source_operational_behavior_log_detects_tamper()
    print("source_behavior_provenance_log_test: OK")


if __name__ == "__main__":
    main()
