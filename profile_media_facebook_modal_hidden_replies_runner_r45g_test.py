#!/usr/bin/env python3
from pathlib import Path
import tempfile
import profile_media_facebook_modal_hidden_replies_runner_r45g as r45g


def test_static_comparison_passes():
    text = """Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore, but this graph is so skewed.
Alex Barron
Context is everything
"""
    with tempfile.TemporaryDirectory() as td:
        result = r45g.build_static_capture(text, Path(td), reference_text=text, min_coverage=0.99)
    assert result['status'] == r45g.STATUS_PASS
    assert result['comparison']['coverage_ratio'] == 1.0
    assert result['side_effect_flags']['visible_hidden_replies_clicks_supported'] is True


def test_hidden_replies_patterns_present():
    r45g.patch_r45d_globals()
    joined = '\n'.join(r45g.r45d.EXPAND_PATTERNS).lower()
    assert 'hidden\\s+repl' in joined
    assert 'view\\s+hidden\\s+repl' in joined
    assert 'hidden repl' in r45g.JS_MODAL_HIDDEN_REPLIES_AUTO_EXPAND.lower()
    assert 'view hidden comments' in r45g.JS_MODAL_HIDDEN_REPLIES_AUTO_EXPAND.lower()


if __name__ == '__main__':
    test_static_comparison_passes()
    test_hidden_replies_patterns_present()
    print('profile_media_facebook_modal_hidden_replies_runner_r45g_test: PASS')
