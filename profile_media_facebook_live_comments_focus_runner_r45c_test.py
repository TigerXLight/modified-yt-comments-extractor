from pathlib import Path
import tempfile
import profile_media_facebook_live_comments_focus_runner_r45c as r45c


def test_compare_and_exports():
    with tempfile.TemporaryDirectory() as td:
        text = """Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore, but this graph is so skewed.
Alex Barron
Context is everything
"""
        result = r45c.build_static_capture(text, Path(td), reference_text=text, source_url='unit')
        assert result['status'] == r45c.STATUS_PASS
        assert result['comment_count'] >= 2
        assert result['comparison']['coverage_ratio'] == 1.0
        assert result['comparison']['sentinel_report']['Tony Bentley'] is True
        assert Path(result['focus_css_path']).exists()
        assert Path(result['focus_snippet_path']).exists()
        assert result['side_effect_flags']['cookie_or_token_extraction_performed'] is False


if __name__ == '__main__':
    test_compare_and_exports()
    print('profile_media_facebook_live_comments_focus_runner_r45c_test: PASS')
