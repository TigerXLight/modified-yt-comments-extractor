#!/usr/bin/env python3
from pathlib import Path
text = Path('main.py').read_text(encoding='utf-8', errors='replace')
assert 'R45E_FACEBOOK_SCROLL_LOAD_AUTO_EXPAND_RUNNER' in text
assert 'facebook_scroll_load_auto_expand_runner' in text
assert 'profile_media_facebook_scroll_load_auto_expand_runner_r45e' in text
print('main_facebook_scroll_load_auto_expand_runner_r45e_test: PASS')
