from capture_archive_wayback import check_wayback_with_lookup, mock_found_wayback_result
from capture_status import ARCHIVE_STATUS_FOUND, ARCHIVE_STATUS_NOT_FOUND_CONFIRMED, ARCHIVE_STATUS_UNKNOWN


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


def run_self_test() -> None:
    test_wayback_lookup_is_injected_and_not_live_by_default()
    test_wayback_lookup_accepts_structured_fake_result()
    test_wayback_lookup_failure_is_fixed_and_non_secret()
    test_mock_found_wayback_result_is_deterministic()


if __name__ == "__main__":
    run_self_test()
    print("Capture Wayback self-test passed.")
