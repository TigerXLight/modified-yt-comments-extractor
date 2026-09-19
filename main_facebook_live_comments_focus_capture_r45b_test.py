from pathlib import Path


def main():
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")
    required = [
        "YTCE_R45B_FACEBOOK_LIVE_COMMENTS_FOCUS_CAPTURE",
        "facebook_live_comments_focus_capture",
        "R45B_FACEBOOK_LIVE_COMMENTS_FOCUS_CAPTURE_ROUTE",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing
    print("main_facebook_live_comments_focus_capture_r45b_test: PASS")


if __name__ == "__main__":
    main()
