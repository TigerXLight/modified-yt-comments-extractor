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
    assert 'JS_CLICK_REPLIED_REPLY_BUCKETS_R45N' in inspect.getsource(r45j)
    assert '--no-replied-reply-bucket-expand' in inspect.getsource(r45j.build_arg_parser)
    assert 'Name replied' in r45j.contract()['r45n_replied_reply_bucket_expand_fix']
    assert 'async (opts) =>' in r45j.JS_CLICK_REPLIED_REPLY_BUCKETS_R45N
    assert 'R45N_REPLIED_REPLY_BUCKET_PROGRESS' in r45j.JS_CLICK_REPLIED_REPLY_BUCKETS_R45N
    assert 'progressiveTopDown' in r45j.JS_CLICK_REPLIED_REPLY_BUCKETS_R45N
    run_live_src = inspect.getsource(r45j.run_live)
    assert 'facebook_preserved_visual_comments_column.png' in run_live_src
    assert '_capture_locator_bands' in inspect.getsource(r45j)
    assert 'preserved_visual_comments_column_screenshot_paths' in run_live_src
    assert '--max-screenshot-band-height' in inspect.getsource(r45j.build_arg_parser)
    assert 'p.chromium.launch(**launch_kwargs)' in run_live_src
    assert 'browser.new_context(**context_kwargs)' in run_live_src
    assert 'launch_persistent_context(args.user_data_dir, **launch_kwargs, **context_kwargs)' in run_live_src
    assert "chromium_kwargs: Dict[str, Any] = {'headless': False, 'viewport': None" not in run_live_src
    assert 'comments column' in c['r45l_comment_column_crop_fix'].lower()
    assert 'viewport' in c['r45m_playwright_viewport_launch_fix'].lower()
    assert 'maximum-height' in c['r45o_screenshot_band_rule']
    assert 'async' in c['r45o_replied_bucket_async_fix']
    assert 'top-to-bottom' in c['r45o_progressive_top_down_rule']
    assert 'clickable ancestor' in c['r45p_replied_bucket_click_target_fix']
    assert 'viewport-relative' in c['r45p_max_band_viewport_clip_fix']
    assert 'does not go back up' in c['r45q_downward_frontier_rule']
    assert 'newly exposed' in c['r45r_local_exhaust_rule']
    assert 'does not start the replied-bucket follow-up' in c['r45s_first_visible_click_rule']
    assert 'heartbeat for each single first-visible click' in c['r45t_visible_click_heartbeat_rule']
    assert '_main_expand_still_incomplete' in inspect.getsource(r45j)
    assert '--local-exhaust-passes' in inspect.getsource(r45j.build_arg_parser)
    assert 'clickVisibleUntilExhausted' in r45j.r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'requestedLocalPasses' in r45j.r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'Math.max(500' in r45j.r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'click exactly one first visible' in r45j.r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'candidates[0]' in r45j.r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'R45T_FIRST_VISIBLE_CLICK' in r45j.r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'dispatchHumanLikeClick' in r45j.r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert '_guard_or_reopen_target_page' in inspect.getsource(r45j)
    assert 'R45J_TARGET_PAGE_GUARD_BLOCKED' in inspect.getsource(r45j)
    assert 'r45u_target_page_guard_rule' in r45j.contract()
    assert 'Playwright-side mouse clicks' in c['r45v_playwright_mouse_downward_rule']
    assert 'cannot open a native file chooser' in c['r45w_no_file_chooser_rule']
    assert 'expand-comments only' in c['r45x_expansion_only_rule']
    assert '_playwright_mouse_downward_expand' in inspect.getsource(r45j)
    assert 'R45X_EXPAND_CLICK' in inspect.getsource(r45j)
    assert 'page.mouse.down()' in inspect.getsource(r45j)
    assert 'isComposerOrUploadSurface' in r45j.JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V
    assert 'input[type="file"]' in r45j.JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V
    assert 'R45X_EXPAND_ONLY_PROBE' in r45j.JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V
    assert 'broad_scan_used' in r45j.JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V
    assert r'View\s+all' in r45j.JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V
    assert "page.on('filechooser'" in inspect.getsource(r45j.run_live)
    assert 'scrollTopForRescan' not in r45j.r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert '--progressive-top-down-sweeps' in inspect.getsource(r45j.build_arg_parser)
    assert 'clicking inert text' in r45j.JS_CLICK_REPLIED_REPLY_BUCKETS_R45N
    assert 'preserve' in c['preserved_visual_rule'].lower()
    assert 'args.screenshot' not in inspect.getsource(r45j.run_live)
    assert 'clone_body_replacement_used' in r45j.JS_MARK_AND_CLEAN_PRESERVED_COMMENTS
    assert 'window.scrollTo(0, y)' in inspect.getsource(r45j._capture_locator_bands)
    assert "'y': 0" in inspect.getsource(r45j._capture_locator_bands)


if __name__ == '__main__':
    test_contract_and_static_assets()
    print('profile_media_facebook_preserved_visual_screenshot_runner_r45j_test: PASS')
