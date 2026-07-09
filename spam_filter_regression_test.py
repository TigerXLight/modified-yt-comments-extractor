from extractor import YouTubeCommentExtractor
from spam_filter import SpamDetector, detect_spam_campaigns


def _assert_not_spam(detector: SpamDetector, text: str) -> None:
    result = detector.analyze(text)
    assert not result.is_spam, f"Expected non-spam for {text!r}; score={result.score}, reason={result.reason}"


def _assert_spam(detector: SpamDetector, text: str) -> None:
    result = detector.analyze(text)
    assert result.is_spam, f"Expected spam for {text!r}; score={result.score}, reason={result.reason}"


def test_short_organic_praise_is_not_spam() -> None:
    detector = SpamDetector()
    for text in [
        "Great video",
        "Loved this",
        "Love this!",
        "This helped a lot",
        "Thanks for explaining",
        "Very useful, thank you",
    ]:
        _assert_not_spam(detector, text)


def test_contact_language_is_not_spam_by_itself() -> None:
    detector = SpamDetector()
    for text in [
        "Contact support if it fails.",
        "I contacted the channel owner about the typo.",
        "For help, contact your school administrator.",
    ]:
        _assert_not_spam(detector, text)


def test_phone_examples_are_not_spam_without_solicitation() -> None:
    detector = SpamDetector()
    for text in [
        "The example phone number is 555-0100.",
        "In documentation, use +1 555 0100 as a placeholder.",
        "Do not call random phone numbers you see in comments.",
    ]:
        _assert_not_spam(detector, text)

    extractor = YouTubeCommentExtractor.__new__(YouTubeCommentExtractor)
    for text in [
        "The example phone number is 555-0100.",
        "In documentation, use +1 555 0100 as a placeholder.",
    ]:
        is_spam, reason = extractor.is_spam(text)
        assert not is_spam, f"Extractor simple spam check flagged {text!r}: {reason}"


def test_adult_context_is_not_spam_without_solicitation() -> None:
    detector = SpamDetector()
    for text in [
        "The documentary discusses adult education policy.",
        "This is an adult learning course.",
        "The word adult here means grown-up, not explicit content.",
    ]:
        _assert_not_spam(detector, text)


def test_obvious_scam_examples_still_trigger() -> None:
    detector = SpamDetector()
    for text in [
        "WhatsApp me for crypto profit +1 555 777 9999",
        "Telegram investment guaranteed returns, contact me now",
        "Check my profile for adult content",
        "OnlyFans link click the link now",
    ]:
        _assert_spam(detector, text)


def test_campaign_detector_still_catches_long_duplicate_promotions() -> None:
    for repeated_short_praise in [
        "Love this!",
        "Great video",
        "Loved this",
        "Thanks!",
    ]:
        assert detect_spam_campaigns([repeated_short_praise] * 5) == set()

    comments = [
        "Telegram investment guaranteed returns contact me now",
        "Telegram investment guaranteed returns contact me now",
        "Telegram investment guaranteed returns contact me now",
    ]
    assert detect_spam_campaigns(comments) == {0, 1, 2}


def run_self_test() -> None:
    test_short_organic_praise_is_not_spam()
    test_contact_language_is_not_spam_by_itself()
    test_phone_examples_are_not_spam_without_solicitation()
    test_adult_context_is_not_spam_without_solicitation()
    test_obvious_scam_examples_still_trigger()
    test_campaign_detector_still_catches_long_duplicate_promotions()


if __name__ == "__main__":
    run_self_test()
    print("Spam filter regression self-test passed.")
