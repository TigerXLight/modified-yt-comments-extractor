#!/usr/bin/env python3
from pathlib import Path
import tempfile
import profile_media_facebook_scroll_load_auto_expand_runner_r45e as r45e

def test_sanitize_markdown_url():
    raw = '[https://www.facebook.com/permalink.php?story_fbid=abc&id=123](https://www.facebook.com/permalink.php?story_fbid=abc\\&id=123)'
    assert r45e.sanitize_target_url(raw) == 'https://www.facebook.com/permalink.php?story_fbid=abc&id=123'

def test_scroll_load_script_present():
    assert 'findScrollTargets' in r45e.JS_SCROLL_LOAD_AUTO_EXPAND
    assert 'scrollTop' in r45e.JS_SCROLL_LOAD_AUTO_EXPAND
    assert 'window.scrollBy' in r45e.JS_SCROLL_LOAD_AUTO_EXPAND
    assert 'Re-scan after each scroll' in r45e.JS_SCROLL_LOAD_AUTO_EXPAND

def test_static_comparison_passes():
    text = '''Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore, but this graph is so skewed.
Alex Barron
Context is everything
'''
    with tempfile.TemporaryDirectory() as td:
        result = r45e.build_static_capture(text, Path(td), reference_text=text, min_coverage=0.99)
        assert result['status'] == r45e.STATUS_PASS
        assert result['comparison']['coverage_ratio'] == 1.0
        assert result['side_effect_flags']['hidden_platform_api_scraping_performed'] is False
        assert result['side_effect_flags']['cookie_or_token_extraction_performed'] is False

def test_contract_documents_r45d_gap_fix():
    c = r45e.contract()
    assert c['mode_id'] == 'facebook_scroll_load_auto_expand_runner'
    assert 'R45D clicked controls already loaded' in c['r45d_gap_fixed']
    assert c['hidden_platform_api_scraping_enabled'] is False
    assert c['browser_profile_file_parsing_enabled'] is False

if __name__ == '__main__':
    test_sanitize_markdown_url()
    test_scroll_load_script_present()
    test_static_comparison_passes()
    test_contract_documents_r45d_gap_fix()
    print('profile_media_facebook_scroll_load_auto_expand_runner_r45e_test: PASS')
