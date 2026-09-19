from profile_media_facebook_visible_print_clean_comment_capture_r45a import (
    SELF_TEST_TEXT,
    build_contract,
    html_to_text,
    parse_print_clean_text_export,
    sanitize_facebook_html,
)


def main() -> int:
    nodes = parse_print_clean_text_export(SELF_TEST_TEXT)
    assert len(nodes) >= 3, nodes
    names = [n.author for n in nodes]
    assert "Tony Bentley" in names
    assert "Dan Melin" in names
    assert "Alex Barron" in names
    assert "first name of all muslim boys" in nodes[0].text
    clean = sanitize_facebook_html('<html><style>x</style><script>alert(1)</script><body><div class="x" style="float:right">Visible</div></body></html>')
    assert "script" not in clean.lower()
    assert "style" not in clean.lower()
    assert "Visible" in clean
    assert "Visible" in html_to_text(clean)
    contract = build_contract()
    assert contract["hidden_platform_api_scraping_enabled"] is False
    assert contract["login_automation_enabled"] is False
    assert contract["cookie_or_token_extraction_enabled"] is False
    assert contract["browser_profile_file_copying_enabled"] is False
    assert "YouTube" in contract["youtube_parity_rule"]
    assert "interactive" in contract["interactive_preclean_rule"]
    assert "Print Edit WE" in contract["print_clean_rule"]
    print("profile_media_facebook_visible_print_clean_comment_capture_r45a_test: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
