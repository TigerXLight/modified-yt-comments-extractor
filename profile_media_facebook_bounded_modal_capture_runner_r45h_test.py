#!/usr/bin/env python3
from pathlib import Path
import tempfile
import profile_media_facebook_bounded_modal_capture_runner_r45h as r45h


def test_js_has_bound_and_progress():
    assert 'maxSeconds' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'R45H_PROGRESS' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'progressiveTopDown' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'maxTopDownSweeps' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'scrollTopForRescan' not in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'clickVisibleUntilExhausted' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'requestedLocalPasses' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'Math.max(500' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'click exactly one first visible' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'candidates[0]' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'first_visible_click_mode' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'global_rescan_used: false' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND
    assert 'timedOut' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND or 'timed_out' in r45h.JS_BOUNDED_MODAL_AUTO_EXPAND


def test_hidden_replies_supported():
    joined = '\n'.join(r45h.EXPAND_PATTERNS_R45H).lower()
    assert 'view\\s+hidden\\s+repl' in joined
    assert 'hidden\\s+repl' in joined
    assert 'view\\s+(?:all|more)\\s+\\d+\\s+repl' in joined


def test_static_comparison_passes():
    # R45H is an overlay on the R45D static/export helpers. Patch R45D globals
    # before asserting the R45H status constant.
    r45h.patch_r45d_globals()
    text = '''Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore, but this graph is so skewed.
Alex Barron
Context is everything
'''
    with tempfile.TemporaryDirectory() as td:
        result = r45h.r45d.build_static_capture(text, Path(td), reference_text=text, min_coverage=0.99)
        assert result['status'] == r45h.STATUS_PASS
        assert result['marker'] == r45h.MARKER
        assert result['comparison']['coverage_ratio'] == 1.0


def test_contract_documents_gap_fix():
    c = r45h.contract()
    assert c['mode_id'] == 'facebook_bounded_modal_capture_runner'
    assert 'R45G could appear stuck' in c['r45g_gap_fixed']
    assert c['hidden_platform_api_scraping_enabled'] is False
    assert 'top-to-bottom' in c['r45o_progressive_top_down_rule']
    assert 'jump back upward' in c['r45p_progressive_rescan_rule']
    assert 'single downward frontier' in c['r45q_downward_frontier_rule']
    assert 'decouples local viewport exhaustion' in c['r45r_local_exhaust_rule']
    assert 'clicks exactly one first visible' in c['r45s_first_visible_click_rule']


if __name__ == '__main__':
    test_js_has_bound_and_progress()
    test_hidden_replies_supported()
    test_static_comparison_passes()
    test_contract_documents_gap_fix()
    print('profile_media_facebook_bounded_modal_capture_runner_r45h_test: PASS')
