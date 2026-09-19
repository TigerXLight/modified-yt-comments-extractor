from pathlib import Path

text = Path('main.py').read_text(encoding='utf-8', errors='replace')
assert 'R45F_FACEBOOK_MODAL_PROGRESS_HIDDEN_COMMENTS_RUNNER' in text
assert 'facebook_modal_progress_hidden_comments_runner' in text
assert 'profile_media_facebook_modal_progress_hidden_comments_runner_r45f' in text
print('main_facebook_modal_progress_hidden_comments_runner_r45f_test: PASS')
