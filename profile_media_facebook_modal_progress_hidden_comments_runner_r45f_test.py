from pathlib import Path
from tempfile import TemporaryDirectory
import profile_media_facebook_modal_progress_hidden_comments_runner_r45f as r45f


def test_url_sanitizer_and_hidden_patterns():
    raw = '[https://www.facebook.com/permalink.php?story_fbid=abc&id=123](https://www.facebook.com/permalink.php?story_fbid=abc\\&id=123)'
    assert r45f.sanitize_target_url(raw) == 'https://www.facebook.com/permalink.php?story_fbid=abc&id=123'
    r45f.patch_r45d_globals()
    joined = '\n'.join(r45f.r45d.EXPAND_PATTERNS).lower()
    assert 'view\\s+hidden' in joined
    assert 'view\\s+\\d+\\s+repl' in joined


def test_script_targets_modal_progress():
    js = r45f.JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND
    assert 'parseProgress' in js
    assert '[role="dialog"]' in js
    assert 'hidden comments' in js.lower()
    assert 'final_progress' in js


def test_static_comparison_passes():
    text = '''Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore, but this graph is so skewed.
Alex Barron
Context is everything
'''
    with TemporaryDirectory() as td:
        result = r45f.build_static_capture(text, Path(td), reference_text=text, min_coverage=0.99)
    assert result['status'] == r45f.STATUS_PASS
    assert result['comparison']['coverage_ratio'] == 1.0
    assert result['side_effect_flags']['facebook_modal_progress_hidden_comments_runner_invoked'] is True

if __name__ == '__main__':
    test_url_sanitizer_and_hidden_patterns()
    test_script_targets_modal_progress()
    test_static_comparison_passes()
    print('profile_media_facebook_modal_progress_hidden_comments_runner_r45f_test: PASS')
