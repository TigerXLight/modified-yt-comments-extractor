from capture_archive_wayback import (
    build_wayback_availability_from_fixture,
    build_wayback_mock_submit_result,
    build_wayback_submit_plan,
    check_wayback_with_lookup,
    list_wayback_snapshots_from_fixture,
    mock_found_wayback_result,
)
from capture_status import (
    ARCHIVE_STATUS_FOUND,
    ARCHIVE_STATUS_NOT_FOUND_CONFIRMED,
    ARCHIVE_STATUS_SUBMISSION_COMPLETED,
    ARCHIVE_STATUS_SUBMISSION_STARTED,
    ARCHIVE_STATUS_UNKNOWN,
)


def test_wayback_lookup_is_injected_and_not_live_by_default() -> None:
    result = check_wayback_with_lookup("https://example.test/page")

    assert result.archive_status == ARCHIVE_STATUS_UNKNOWN
    assert result.snapshot_url == ""
    assert "No live Wayback lookup" in result.warnings[0]
    assert "no live archive" in result.scope


def test_wayback_lookup_accepts_structured_fake_result() -> None:
    def lookup(url: str):
        assert url == "https://example.test/page"
        return {
            "archive_status": ARCHIVE_STATUS_NOT_FOUND_CONFIRMED,
            "warnings": ("fixture only",),
        }

    result = check_wayback_with_lookup("https://example.test/page", lookup=lookup)

    assert result.archive_status == ARCHIVE_STATUS_NOT_FOUND_CONFIRMED
    assert result.warnings == ("fixture only",)


def test_wayback_lookup_failure_is_fixed_and_non_secret() -> None:
    def lookup(url: str):
        raise RuntimeError("secret response body")

    result = check_wayback_with_lookup("https://example.test/page", lookup=lookup)

    assert result.archive_status == ARCHIVE_STATUS_UNKNOWN
    assert "secret response body" not in repr(result.to_dict())


def test_mock_found_wayback_result_is_deterministic() -> None:
    result = mock_found_wayback_result(
        "https://example.test/page",
        snapshot_url="https://web.archive.org/web/20260716000000/https://example.test/page",
        saved_at="2026-07-16T00:00:00Z",
    )

    assert result.archive_status == ARCHIVE_STATUS_FOUND
    assert result.saved_at == "2026-07-16T00:00:00Z"
    assert result.to_dict()["archive_url"] == result.snapshot_url


def test_wayback_fixture_listing_and_availability_are_separate_from_submit() -> None:
    snapshots = (
        {
            "snapshot_url": "https://web.archive.org/web/20250101000000/https://example.test/page",
            "saved_at": "2025-01-01T00:00:00Z",
        },
        {
            "snapshot_url": "https://web.archive.org/web/20260101000000/https://example.test/page",
            "saved_at": "2026-01-01T00:00:00Z",
        },
    )

    listed = list_wayback_snapshots_from_fixture("https://example.test/page", snapshots)
    available = build_wayback_availability_from_fixture(
        "https://example.test/page",
        snapshots=snapshots,
    )

    assert [item.operation for item in listed] == ["LIST", "LIST"]
    assert available.archive_status == ARCHIVE_STATUS_FOUND
    assert available.operation == "CHECK"
    assert available.saved_at == "2026-01-01T00:00:00Z"
    assert "submission" not in repr(available.to_dict()).lower()


def test_wayback_fixture_not_found_and_submit_plan_do_not_perform_network() -> None:
    missing = build_wayback_availability_from_fixture("https://example.test/missing")
    plan = build_wayback_submit_plan(
        "https://example.test/page",
        requested_at_utc="2026-07-16T00:00:00Z",
    )
    started = build_wayback_mock_submit_result(
        "https://example.test/page",
        submitted_at_utc="2026-07-16T00:00:01Z",
        submission_id="fixture-submit-1",
    )
    completed = build_wayback_mock_submit_result(
        "https://example.test/page",
        submitted_at_utc="2026-07-16T00:00:02Z",
        archive_url="https://web.archive.org/web/20260716000002/https://example.test/page",
        completed=True,
    )

    assert missing.archive_status == ARCHIVE_STATUS_NOT_FOUND_CONFIRMED
    assert plan.explicit_user_intent_required is True
    assert plan.submission_execution == "not executed"
    assert started.archive_status == ARCHIVE_STATUS_SUBMISSION_STARTED
    assert completed.archive_status == ARCHIVE_STATUS_SUBMISSION_COMPLETED
    rendered = repr((plan.to_dict(), started.to_dict(), completed.to_dict()))
    assert "requests.get" not in rendered
    assert "urlopen" not in rendered


def run_self_test() -> None:
    test_wayback_lookup_is_injected_and_not_live_by_default()
    test_wayback_lookup_accepts_structured_fake_result()
    test_wayback_lookup_failure_is_fixed_and_non_secret()
    test_mock_found_wayback_result_is_deterministic()
    test_wayback_fixture_listing_and_availability_are_separate_from_submit()
    test_wayback_fixture_not_found_and_submit_plan_do_not_perform_network()


if __name__ == "__main__":
    run_self_test()
    print("Capture Wayback self-test passed.")
