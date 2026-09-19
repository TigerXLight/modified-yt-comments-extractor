#!/usr/bin/env python3
from pathlib import Path

text = Path('main.py').read_text(encoding='utf-8', errors='replace')
assert 'R45D_FACEBOOK_AUTO_EXPAND_COMMENTS_RUNNER' in text
assert 'profile_media_facebook_auto_expand_comments_runner_r45d' in text
assert 'facebook_auto_expand_comments_runner' in text
print('main_facebook_auto_expand_comments_runner_r45d_test: PASS')
