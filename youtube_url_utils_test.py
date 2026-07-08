from youtube_url_utils import extract_youtube_video_id, normalize_youtube_url


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def _assert_valid(value: str) -> None:
    assert extract_youtube_video_id(value) == VALID_ID
    assert normalize_youtube_url(value) == CANONICAL_URL


def run_self_test() -> None:
    for value in [
        VALID_ID,
        f"https://www.youtube.com/watch?v={VALID_ID}",
        f"https://youtube.com/watch?v={VALID_ID}",
        f"https://www.youtube.com/watch?v={VALID_ID}&t=30s&list=PL123",
        f"https://youtu.be/{VALID_ID}",
        f"https://youtu.be/{VALID_ID}?t=30s",
        f"https://www.youtube.com/shorts/{VALID_ID}",
        f"https://youtube.com/shorts/{VALID_ID}?feature=share",
        f"https://www.youtube.com/embed/{VALID_ID}",
        f"https://youtube.com/embed/{VALID_ID}?start=30",
    ]:
        _assert_valid(value)

    for value in [
        "",
        "not a youtube url",
        "https://example.com/watch?v=aB3_dE-9xYz",
        "https://www.youtube.com/watch?v=too-short",
        "https://www.youtube.com/watch?v=aB3_dE-9xYzMORE",
        "https://www.youtube.com/shorts/aB3_dE-9x!",
        "https://www.notyoutube.com/watch?v=aB3_dE-9xYz",
    ]:
        try:
            extract_youtube_video_id(value)
        except ValueError:
            continue
        raise AssertionError(f"Expected invalid YouTube input: {value!r}")


if __name__ == "__main__":
    run_self_test()
    print("YouTube URL utility self-test passed.")
