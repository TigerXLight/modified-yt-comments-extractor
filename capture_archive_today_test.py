from capture_archive_today import check_archive_today_with_lookup
from capture_status import ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER, ARCHIVE_STATUS_FOUND, ARCHIVE_STATUS_UNKNOWN


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


def run_self_test() -> None:
    test_archive_today_lookup_is_injected_and_not_live_by_default()
    test_archive_today_lookup_accepts_structured_fake_result()
    test_archive_today_challenge_is_explicit()
    test_archive_today_lookup_failure_is_fixed_and_non_secret()


if __name__ == "__main__":
    run_self_test()
    print("Capture archive.today self-test passed.")
