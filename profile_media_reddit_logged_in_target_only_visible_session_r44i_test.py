from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_reddit_logged_in_target_only_visible_session_r44i import (
    DEFAULT_TARGET_URL,
    MARKER,
    PASS_STATUS,
    _blocker_status_from_text,
    _contract,
    _run_self_test,
    _sanitize_current_reddit_dom_html,
    build_reddit_logged_in_target_only_visible_session_contract_r44i,
)


def test_contract_and_default_target_are_old_reddit_target_only() -> None:
    assert DEFAULT_TARGET_URL.startswith("https://en.reddit.com/r/EdSheeran/comments/1whbgzk/")
    contract = build_reddit_logged_in_target_only_visible_session_contract_r44i()
    assert contract["mode_id"] == "reddit_logged_in_target_only_visible_session"
    assert "direct-launch-target-url" in contract["target_url_rule"]
    assert contract["cookie_or_token_extraction_enabled"] is False
    assert contract["login_automation_enabled"] is False
    assert contract["hidden_platform_api_scraping_enabled"] is False
    assert contract["remote_media_downloads_enabled"] is False


def test_sanitizer_keeps_target_and_removes_current_reddit_noise() -> None:
    raw = """
    <html><body>
      <shreddit-post><a href='https://www.reddit.com/r/EdSheeran/comments/1whbgzk/'>[ Removed by moderator ]</a></shreddit-post>
      <aside>Related posts <a href='https://www.reddit.com/r/EdSheeran/comments/1wge713/'>wrong post</a><img src='https://www.redditstatic.com/shreddit/assets/right-rail/streetwear.jpg'></aside>
      <shreddit-comment id='t1_pa1bbed'><a href='https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1bbed/'>comment</a><p>target comment</p></shreddit-comment>
      <reddit-cookie-banner>Accept All</reddit-cookie-banner>
      <shreddit-ad-post>Shop Now</shreddit-ad-post>
    </body></html>
    """
    sanitized = _sanitize_current_reddit_dom_html(raw)
    assert "1whbgzk" in sanitized
    assert "pa1bbed" in sanitized
    assert "1wge713" not in sanitized
    assert "streetwear" not in sanitized
    assert "Accept All" not in sanitized
    assert "Shop Now" not in sanitized


def test_old_reddit_sanitizer_keeps_comment_area() -> None:
    raw = """
    <html><body>
      <div class='content'>
        <p>all 351 comments</p>
        <div class='commentarea'>sorted by: old <div class='thing id-t1_pa1fs0p'>comment body</div></div>
      </div>
      <div class='side'>sidebar should be removed</div>
    </body></html>
    """
    sanitized = _sanitize_current_reddit_dom_html(raw)
    assert "all 351 comments" in sanitized
    assert "id-t1_pa1fs0p" in sanitized
    assert "sidebar should be removed" not in sanitized


def test_blocker_detection() -> None:
    status, _detail = _blocker_status_from_text("https://www.reddit.com/", "You've been blocked by network security.")
    assert status == "BLOCKED_REDDIT_NETWORK_SECURITY"
    status, _detail = _blocker_status_from_text("https://en.reddit.com/login/?reason=lor2", "Log in to use old Reddit")
    assert status == "BLOCKED_REDDIT_LOGIN_REQUIRED"


def test_self_test_report() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = _run_self_test(Path(tmp))
    assert report["marker"] == MARKER
    assert report["status"] == PASS_STATUS
    assert all(item["status"] == "pass" for item in report["checks"]), json.dumps(report, indent=2)


def run_self_test() -> None:
    test_contract_and_default_target_are_old_reddit_target_only()
    test_sanitizer_keeps_target_and_removes_current_reddit_noise()
    test_old_reddit_sanitizer_keeps_comment_area()
    test_blocker_detection()
    test_self_test_report()
    print("profile_media_reddit_logged_in_target_only_visible_session_r44i_test: PASS")


if __name__ == "__main__":
    run_self_test()
