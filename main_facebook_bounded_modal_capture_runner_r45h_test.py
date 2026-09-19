#!/usr/bin/env python3
from pathlib import Path
text = Path('main.py').read_text(encoding='utf-8', errors='replace')
assert 'R45H_FACEBOOK_BOUNDED_MODAL_CAPTURE_RUNNER' in text
assert 'facebook_bounded_modal_capture_runner' in text
assert 'profile_media_facebook_bounded_modal_capture_runner_r45h' in text
print('main_facebook_bounded_modal_capture_runner_r45h_test: PASS')
