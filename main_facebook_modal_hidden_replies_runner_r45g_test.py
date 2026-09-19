#!/usr/bin/env python3
from pathlib import Path
text = Path('main.py').read_text(encoding='utf-8', errors='replace')
assert 'R45G_FACEBOOK_MODAL_HIDDEN_REPLIES_RUNNER' in text
assert 'facebook_modal_hidden_replies_runner' in text
assert 'profile_media_facebook_modal_hidden_replies_runner_r45g' in text
print('main_facebook_modal_hidden_replies_runner_r45g_test: PASS')
