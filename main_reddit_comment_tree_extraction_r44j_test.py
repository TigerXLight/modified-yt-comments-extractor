from profile_media_reddit_comment_tree_extraction_r44j import (
    MARKER,
    build_reddit_comment_tree_extraction_contract_r44j,
)


def run_self_test() -> None:
    contract = build_reddit_comment_tree_extraction_contract_r44j()
    assert contract["marker"] == MARKER
    assert contract["large_thread_rule"].startswith("old Reddit limit=500")
    assert contract["no_login_fallback_route"].startswith("current www.reddit.com")
    assert contract["login_automation_enabled"] is False
    assert contract["cookie_or_token_extraction_enabled"] is False


if __name__ == "__main__":
    run_self_test()
    print("main_reddit_comment_tree_extraction_r44j_test: PASS")
