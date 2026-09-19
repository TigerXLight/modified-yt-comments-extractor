#!/usr/bin/env python3
from pathlib import Path


def test_main_registration():
    text = Path('main.py').read_text(encoding='utf-8', errors='replace')
    assert 'R45J_FACEBOOK_PRESERVED_VISUAL_SCREENSHOT_RUNNER' in text
    assert 'facebook_preserved_visual_screenshot_runner' in text
    assert 'profile_media_facebook_preserved_visual_screenshot_runner_r45j' in text


if __name__ == '__main__':
    test_main_registration()
    print('main_facebook_preserved_visual_screenshot_runner_r45j_test: PASS')
