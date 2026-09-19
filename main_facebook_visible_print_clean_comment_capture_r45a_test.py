from pathlib import Path


def main() -> int:
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")
    required = [
        "YTCE_R45A_FACEBOOK_VISIBLE_PRINT_CLEAN_COMMENT_CAPTURE",
        "profile_media_facebook_visible_print_clean_comment_capture_r45a",
        "facebook_visible_print_clean_comment_capture",
        "facebook_visible_interactive_preclean_capture",
    ]
    missing = [x for x in required if x not in text]
    assert not missing, missing
    print("main_facebook_visible_print_clean_comment_capture_r45a_test: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
