from profile_media_facebook_live_comments_focus_capture_r45b import (
    MARKER,
    FOCUS_CSS,
    FOCUS_SNIPPET,
    parse_print_clean_text,
    compare_text_against_reference,
    comments_to_text,
    build_contract,
)


def main():
    sample = """Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet. They normally go by a middle name. This doesn't mean more muslim babies are being born than others.

    1d
    Reply

Dan Melin
Look I'm all for Restore, but this graph is so skewed. If we have 100 children. 20% are called Muhammad, 11% called Noah and so on and so forth all the way down; that's 20 kids called Muhammad and 80 kids not called that. It just so happens we have more variety 🤷

    1d
    Reply
"""
    comments = parse_print_clean_text(sample)
    assert len(comments) == 2, comments
    assert comments[0].author == "Tony Bentley"
    assert "Mohhamed" in comments[0].body
    assert comments[1].author == "Dan Melin"
    assert MARKER in FOCUS_SNIPPET
    assert "display: none" in FOCUS_CSS
    assert "pointer-events: auto" in FOCUS_CSS
    comparison = compare_text_against_reference(comments_to_text(comments), sample)
    assert comparison["coverage_ratio"] >= 0.95, comparison
    contract = build_contract()
    assert contract["hidden_platform_api_scraping_enabled"] is False
    assert contract["login_automation_enabled"] is False
    assert contract["cookie_or_token_extraction_enabled"] is False
    assert contract["browser_profile_file_copying_enabled"] is False
    print("profile_media_facebook_live_comments_focus_capture_r45b_test: PASS")


if __name__ == "__main__":
    main()
