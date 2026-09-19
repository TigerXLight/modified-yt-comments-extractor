#!/usr/bin/env python3
from pathlib import Path
import tempfile

import profile_media_facebook_auto_expand_comments_runner_r45d as r45d


def test_url_sanitizer():
    raw = '[https://www.facebook.com/permalink.php?story_fbid=abc&id=123](https://www.facebook.com/permalink.php?story_fbid=abc\\&id=123)'
    assert r45d.sanitize_target_url(raw) == 'https://www.facebook.com/permalink.php?story_fbid=abc&id=123'


def test_static_capture_pass():
    sample = '''Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore
Alex Barron
Context is everything
'''
    with tempfile.TemporaryDirectory() as td:
        result = r45d.build_static_capture(sample, Path(td), reference_text=sample, min_coverage=0.99)
        assert result['status'] == r45d.STATUS_PASS
        assert result['comment_count'] >= 2
        assert result['comparison']['coverage_ratio'] == 1.0
        assert Path(result['receipt_path']).exists()


def test_static_capture_needs_more_expansion():
    candidate = "Tony Bentley\nMohhamed etc is the first name\n"
    reference = candidate + "\nDan Melin\nLook I'm all for Restore\nAlex Barron\nContext is everything\n"
    with tempfile.TemporaryDirectory() as td:
        result = r45d.build_static_capture(candidate, Path(td), reference_text=reference, min_coverage=0.90)
        assert result['status'] == r45d.STATUS_NEEDS_MORE_EXPANSION
        assert result['comparison']['coverage_ratio'] < 0.90


def test_contract_safety():
    c = r45d.contract()
    assert c['hidden_platform_api_scraping_enabled'] is False
    assert c['cookie_or_token_extraction_enabled'] is False
    assert c['browser_profile_file_copying_enabled'] is False
    assert c['login_automation_enabled'] is False


if __name__ == '__main__':
    test_url_sanitizer()
    test_static_capture_pass()
    test_static_capture_needs_more_expansion()
    test_contract_safety()
    print('profile_media_facebook_auto_expand_comments_runner_r45d_test: PASS')
