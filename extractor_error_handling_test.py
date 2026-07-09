from extractor import (
    CommentsDisabledError,
    QuotaExceededError,
    VideoNotFoundError,
    YouTubeCommentExtractor,
)


def _capture_friendly_error(message: str) -> Exception:
    extractor = YouTubeCommentExtractor.__new__(YouTubeCommentExtractor)
    try:
        extractor._raise_friendly_error(Exception(message))
    except Exception as error:
        return error
    raise AssertionError(f"Expected friendly error for message: {message!r}")


def _assert_error_type(message: str, expected_type: type[Exception]) -> None:
    error = _capture_friendly_error(message)
    assert isinstance(error, expected_type), (
        f"Expected {expected_type.__name__} for {message!r}, "
        f"got {type(error).__name__}: {error}"
    )


def run_self_test() -> None:
    _assert_error_type(
        '{"error":{"errors":[{"reason":"quotaExceeded"}],"code":403}}',
        QuotaExceededError,
    )
    _assert_error_type(
        "HttpError 403: QUOTAEXCEEDED for this project",
        QuotaExceededError,
    )
    _assert_error_type(
        "commentsDisabled: Comments are disabled for this video",
        CommentsDisabledError,
    )
    _assert_error_type(
        '{"error":{"errors":[{"reason":"notFound"}],"code":404}}',
        VideoNotFoundError,
    )

    generic_forbidden = _capture_friendly_error(
        '{"error":{"errors":[{"reason":"forbidden"}],"code":403}}'
    )
    assert isinstance(generic_forbidden, RuntimeError)
    assert not isinstance(generic_forbidden, QuotaExceededError)

    # Deferred upstream parity gap:
    # `dailyLimitExceeded` does not contain the literal word "quota", so the current
    # string-based classifier does not promise quota handling for that reason yet.
    # A future behavior port should add a typed/JSON error-reason helper before
    # asserting that dailyLimitExceeded maps to QuotaExceededError.


if __name__ == "__main__":
    run_self_test()
    print("Extractor error handling self-test passed.")
