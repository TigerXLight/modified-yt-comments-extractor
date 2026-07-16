import json

from capture_action_log import (
    ACTOR_TYPE_APPLICATION,
    ACTOR_TYPE_EXTERNAL_TOOL,
    ACTOR_TYPE_USER,
    REDACTED_VALUE,
    action_log_event_to_json,
    build_action_log_event,
    compute_action_event_hash,
    sanitize_action_log_value,
)


def test_action_log_event_hash_is_deterministic_and_chained() -> None:
    first = build_action_log_event(
        session_id="session_1",
        actor_type=ACTOR_TYPE_USER,
        action_type="request_capture",
        result="SUCCESS",
        timestamp_utc="2026-07-16T00:00:00Z",
    )
    second = build_action_log_event(
        session_id="session_1",
        actor_type=ACTOR_TYPE_APPLICATION,
        action_type="write_artifact",
        result="SUCCESS",
        timestamp_utc="2026-07-16T00:00:01Z",
        previous_event_hash=first.event_hash,
    )
    repeated = build_action_log_event(
        session_id="session_1",
        actor_type=ACTOR_TYPE_APPLICATION,
        action_type="write_artifact",
        result="SUCCESS",
        timestamp_utc="2026-07-16T00:00:01Z",
        previous_event_hash=first.event_hash,
    )

    assert first.event_hash == compute_action_event_hash(first.to_dict_without_hash())
    assert second.event_hash == repeated.event_hash
    assert second.previous_event_hash == first.event_hash
    assert second.event_hash != first.event_hash


def test_action_log_sanitizes_secret_like_request_summary_fields() -> None:
    event = build_action_log_event(
        session_id="session_2",
        actor_type=ACTOR_TYPE_EXTERNAL_TOOL,
        action_type="archivebox_command_preview",
        result="DEPENDENCY_MISSING",
        timestamp_utc="2026-07-16T00:00:00Z",
        request_summary={
            "url": "https://localhost.test/article/static",
            "api_key": "SHOULD_NOT_APPEAR",
            "nested": {
                "Authorization": "Bearer SHOULD_NOT_APPEAR",
                "safe": "visible",
            },
        },
        warnings=("model only",),
    )

    data = event.to_dict()
    assert data["request_summary"]["api_key"] == REDACTED_VALUE
    assert data["request_summary"]["nested"]["Authorization"] == REDACTED_VALUE
    assert data["request_summary"]["nested"]["safe"] == "visible"
    rendered = action_log_event_to_json(event)
    assert "SHOULD_NOT_APPEAR" not in rendered
    assert "Bearer" not in rendered


def test_action_log_json_matches_schema_shape_without_dataclasses() -> None:
    event = build_action_log_event(
        session_id="session_3",
        actor_type=ACTOR_TYPE_APPLICATION,
        action_type="capture_contract_created",
        result="MODEL_ONLY",
        timestamp_utc="2026-07-16T00:00:00Z",
        artifact_ids=("artifact_1", "artifact_2"),
        app_version="test",
    )

    data = json.loads(action_log_event_to_json(event))
    for key in (
        "schema_version",
        "event_id",
        "timestamp_utc",
        "session_id",
        "actor_type",
        "action_type",
        "result",
        "previous_event_hash",
        "event_hash",
    ):
        assert key in data
    assert data["artifact_ids"] == ["artifact_1", "artifact_2"]
    assert data["request_summary"] is None


def test_sanitizer_recurses_through_lists_and_tuples() -> None:
    data = sanitize_action_log_value(
        {
            "items": (
                {"credential": "secret-value"},
                {"normal": ["ok", {"session_token": "secret-value"}]},
            )
        }
    )

    assert data == {
        "items": [
            {"credential": REDACTED_VALUE},
            {"normal": ["ok", {"session_token": REDACTED_VALUE}]},
        ]
    }


def test_unknown_actor_type_is_rejected() -> None:
    try:
        build_action_log_event(
            session_id="session_4",
            actor_type="NETWORK_CLIENT",
            action_type="bad",
            result="FAILED",
        )
    except ValueError as exc:
        assert "Unknown action-log actor type" in str(exc)
    else:
        raise AssertionError("unknown actor type should fail")


def run_self_test() -> None:
    test_action_log_event_hash_is_deterministic_and_chained()
    test_action_log_sanitizes_secret_like_request_summary_fields()
    test_action_log_json_matches_schema_shape_without_dataclasses()
    test_sanitizer_recurses_through_lists_and_tuples()
    test_unknown_actor_type_is_rejected()


if __name__ == "__main__":
    run_self_test()
    print("Capture action log self-test passed.")
