#!/usr/bin/env python3
from pathlib import Path


def test_main_registration():
    text = Path('main.py').read_text(encoding='utf-8', errors='replace')
    assert 'R45I_FACEBOOK_PRINT_CLEAN_EVIDENCE_SCREENSHOT' in text
    assert 'facebook_print_clean_evidence_screenshot' in text
    assert 'profile_media_facebook_print_clean_evidence_screenshot_r45i' in text


if __name__ == '__main__':
    test_main_registration()
    print('main_facebook_print_clean_evidence_screenshot_r45i_test: PASS')
