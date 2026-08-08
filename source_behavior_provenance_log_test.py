from source_behavior_provenance_log import (
    BehaviorActionType,
    BehaviorLogEntry,
    build_example_behavior_provenance_log,
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


def main() -> None:
    test_behavior_log_is_hash_chained()
    test_secret_like_detail_is_redacted()
    test_witness_roles_distinguish_author_and_operator()
    print("source_behavior_provenance_log_test: OK")


if __name__ == "__main__":
    main()
