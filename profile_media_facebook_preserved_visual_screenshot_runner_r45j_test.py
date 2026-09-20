#!/usr/bin/env python3
import inspect
import profile_media_facebook_preserved_visual_screenshot_runner_r45j as r45j


def test_contract_and_static_assets():
    c = r45j.contract()
    assert c['marker'] == r45j.MARKER
    assert c['mode_id'] == 'facebook_preserved_visual_screenshot_runner'
    assert c['hidden_platform_api_scraping_enabled'] is False
    assert c['login_automation_enabled'] is False
    assert c['cookie_or_token_extraction_enabled'] is False
    assert 'document.body.innerHTML' not in r45j.JS_MARK_AND_CLEAN_PRESERVED_COMMENTS
    assert 'data-r45j-visual-keep-path' in r45j.JS_MARK_AND_CLEAN_PRESERVED_COMMENTS
    assert 'data-r45j-preserved-comments-root' in r45j.VISUAL_CLEAN_CSS
    assert 'blank-page fix' in r45j.VISUAL_CLEAN_CSS
    assert 'data-r45j-pre-comment-hide' in r45j.VISUAL_CLEAN_CSS
    assert 'data-r45j-comment-column-crop' in r45j.JS_MARK_AND_CLEAN_PRESERVED_COMMENTS
    assert 'r45l_comment_column_crop_used' in r45j.JS_MARK_AND_CLEAN_PRESERVED_COMMENTS
    run_live_src = inspect.getsource(r45j.run_live)
    assert 'facebook_preserved_visual_comments_column.png' in run_live_src
    assert 'p.chromium.launch(**launch_kwargs)' in run_live_src
    assert 'browser.new_context(**context_kwargs)' in run_live_src
    assert 'launch_persistent_context(args.user_data_dir, **launch_kwargs, **context_kwargs)' in run_live_src
    assert "chromium_kwargs: Dict[str, Any] = {'headless': False, 'viewport': None" not in run_live_src
    assert 'comments column' in c['r45l_comment_column_crop_fix'].lower()
    assert 'viewport' in c['r45m_playwright_viewport_launch_fix'].lower()
    assert 'preserve' in c['preserved_visual_rule'].lower()
    assert 'args.screenshot' not in inspect.getsource(r45j.run_live)
    assert 'clone_body_replacement_used' in r45j.JS_MARK_AND_CLEAN_PRESERVED_COMMENTS


if __name__ == '__main__':
    test_contract_and_static_assets()
    print('profile_media_facebook_preserved_visual_screenshot_runner_r45j_test: PASS')
