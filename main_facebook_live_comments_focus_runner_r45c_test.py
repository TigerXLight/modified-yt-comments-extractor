from pathlib import Path


def test_main_registration():
    text = Path('main.py').read_text(encoding='utf-8', errors='replace')
    assert 'R45C_FACEBOOK_LIVE_COMMENTS_FOCUS_RUNNER' in text
    assert 'profile_media_facebook_live_comments_focus_runner_r45c' in text


if __name__ == '__main__':
    test_main_registration()
    print('main_facebook_live_comments_focus_runner_r45c_test: PASS')
