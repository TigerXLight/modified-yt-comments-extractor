#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
src = Path('profile_media_facebook_progress_gated_modal_flatten_r45ax.py').read_text(encoding='utf-8')
assert 'YTCE_R45AX_PROGRESS_GATED_MODAL_FLATTEN' in src
assert '657 of 715' in src
assert 'Fahad Malik replied · 3 replies' in src
assert 'r45axProgressFromText' in src
assert 'r45axProgressFromPage' in src
assert 'document.documentElement.innerHTML' in src
assert 'R45AX_PROGRESS_GATE_NOT_SATISFIED' in src
assert 'R45AX_AUDIT_RESTART_TOP' in src
assert 'completed_by_full_zero_control_audit' in src
assert 'r45ax_live_before_flatten.html' in src
assert 'r45axFlattenForScreenshot' in src
assert 'add_script_tag' not in src
assert 'R45AX_SCRIPT_INSTALL' in src
assert 'r45ba_scroll_container_rule' in src
assert 'no_real_scrollable_comments_container' in src
assert 'BLOCKED_NO_REAL_SCROLLABLE_COMMENTS_SCROLLER' in src
assert 'scrollHeight==clientHeight' in src
assert 'r45axExpansionLabelInfo' in src
assert 'replied\\s*(?:[·•.\\-]\\s*)?\\d+\\s+repl' in src
assert re.search(r'View all \\d\+ replies', src)
assert 'hidden_platform_api_scraping_enabled' in src and 'False' in src
assert 'browser_profile_file_parsing_enabled' in src and 'False' in src
print('profile_media_facebook_progress_gated_modal_flatten_r45ax_test: PASS')
