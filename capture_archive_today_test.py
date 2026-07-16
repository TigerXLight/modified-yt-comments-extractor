from capture_archive_today import (
    ARCHIVE_TODAY_STATE_AVAILABLE,
    ARCHIVE_TODAY_STATE_CHALLENGE_REQUIRED,
    ARCHIVE_TODAY_STATE_FAILED,
    ARCHIVE_TODAY_STATE_MIRROR_FORMAT_ERROR,
    ARCHIVE_TODAY_STATE_NOT_FOUND,
    ARCHIVE_TODAY_STATE_POLLING,
    ARCHIVE_TODAY_STATE_SUBMITTED,
    ARCHIVE_TODAY_STATE_WIP,
    build_archive_today_challenge_handoff,
    build_archive_today_mock_result,
    build_archive_today_submit_plan,
    check_archive_today_with_lookup,
)
from capture_status import (
    ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER,
    ARCHIVE_STATUS_FORMAT_CHANGED,
    ARCHIVE_STATUS_FOUND,
    ARCHIVE_STATUS_NETWORK_ERROR,
    ARCHIVE_STATUS_NOT_FOUND_CONFIRMED,
    ARCHIVE_STATUS_SUBMISSION_STARTED,
    ARCHIVE_STATUS_UNKNOWN,
    ARCHIVE_STATUS_WIP,
)


def test_archive_today_lookup_is_injected_and_not_live_by_default() -> None:
    result = check_archive_today_with_lookup("https://example.test/page")

    assert result.archive_status == ARCHIVE_STATUS_UNKNOWN
    assert result.snapshot_url == ""
    assert "No live archive.today lookup" in result.warnings[0]
    assert "no live archive" in result.scope


def test_archive_today_lookup_accepts_structured_fake_result() -> None:
    def lookup(url: str):
        assert url == "https://example.test/page"
        return {
            "archive_status": ARCHIVE_STATUS_FOUND,
            "snapshot_url": "https://archive.ph/example",
            "saved_at": "2026-07-16",
        }

    result = check_archive_today_with_lookup("https://example.test/page", lookup=lookup)

    assert result.archive_status == ARCHIVE_STATUS_FOUND
    assert result.snapshot_url == "https://archive.ph/example"
    assert result.challenge_required is False


def test_archive_today_challenge_is_explicit() -> None:
    result = check_archive_today_with_lookup(
        "https://example.test/page",
        lookup=lambda url: {"archive_status": ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER},
    )

    assert result.archive_status == ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER
    assert result.challenge_required is True


def test_archive_today_lookup_failure_is_fixed_and_non_secret() -> None:
    def lookup(url: str):
        raise RuntimeError("secret challenge html")

    result = check_archive_today_with_lookup("https://example.test/page", lookup=lookup)

    assert result.archive_status == ARCHIVE_STATUS_UNKNOWN
    assert "secret challenge html" not in repr(result.to_dict())


def test_archive_today_fixture_states_are_mapped_without_live_access() -> None:
    cases = {
        ARCHIVE_TODAY_STATE_AVAILABLE: ARCHIVE_STATUS_FOUND,
        ARCHIVE_TODAY_STATE_NOT_FOUND: ARCHIVE_STATUS_NOT_FOUND_CONFIRMED,
        ARCHIVE_TODAY_STATE_SUBMITTED: ARCHIVE_STATUS_SUBMISSION_STARTED,
        ARCHIVE_TODAY_STATE_POLLING: ARCHIVE_STATUS_WIP,
        ARCHIVE_TODAY_STATE_WIP: ARCHIVE_STATUS_WIP,
        ARCHIVE_TODAY_STATE_MIRROR_FORMAT_ERROR: ARCHIVE_STATUS_FORMAT_CHANGED,
        ARCHIVE_TODAY_STATE_FAILED: ARCHIVE_STATUS_NETWORK_ERROR,
    }

    for fixture_state, expected_status in cases.items():
        result = build_archive_today_mock_result(
            "https://example.test/page",
            fixture_state=fixture_state,
            snapshot_url="https://archive.ph/example",
            saved_at="2026-07-16",
        )

        assert result.archive_status == expected_status
        assert result.fixture_state == fixture_state
        assert result.challenge_required is False
        assert "requests.get" not in repr(result.to_dict())


def test_archive_today_challenge_handoff_is_manual_only_and_non_bypass() -> None:
    handoff = build_archive_today_challenge_handoff(
        "https://example.test/page",
        mirror="archive.ph",
        reason="fixture challenge",
    )
    result = build_archive_today_mock_result(
        "https://example.test/page",
        fixture_state=ARCHIVE_TODAY_STATE_CHALLENGE_REQUIRED,
        mirror="archive.ph",
    )

    assert handoff.browser_handoff_only is True
    assert result.challenge_required is True
    assert result.archive_status == ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER
    rendered = repr((handoff.to_dict(), result.to_dict())).lower()
    assert "captcha" not in rendered
    assert "solver" not in rendered
    assert "stealth" not in rendered
    assert "bypass" not in rendered
    assert "token replay" not in rendered
    assert "proxy" not in rendered


def test_archive_today_submit_plan_is_explicit_and_not_executed() -> None:
    plan = build_archive_today_submit_plan("https://example.test/page", mirror="archive.is")

    assert plan.explicit_user_intent_required is True
    assert plan.submission_execution == "not executed"
    assert plan.mirror == "archive.is"
    assert "requests.post" not in repr(plan.to_dict())


def run_self_test() -> None:
    test_archive_today_lookup_is_injected_and_not_live_by_default()
    test_archive_today_lookup_accepts_structured_fake_result()
    test_archive_today_challenge_is_explicit()
    test_archive_today_lookup_failure_is_fixed_and_non_secret()
    test_archive_today_fixture_states_are_mapped_without_live_access()
    test_archive_today_challenge_handoff_is_manual_only_and_non_bypass()
    test_archive_today_submit_plan_is_explicit_and_not_executed()


if __name__ == "__main__":
    run_self_test()
    print("Capture archive.today self-test passed.")
