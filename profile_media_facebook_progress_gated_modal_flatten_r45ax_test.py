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
assert 'r45bc_dead_click_rule' in src
assert 'r45axAddSkipKey' in src
assert 'R45AX_DEAD_CLICK_KEY_SKIPPED' in src
assert 'dead_click_skipped' in src
assert 'no_progress' in src
assert 'r45bd_messenger_guard_rule' in src
assert 'r45axMessengerOverlayState' in src
assert 'r45axCloseMessengerOverlays' in src
assert 'R45AX_MESSENGER_OVERLAY_BLOCKED' in src
assert 'R45AX_UNEXPECTED_PAGE_CLOSED' in src
assert 'click_elapsed_ms' in src
assert 'timing_delta' in src
assert 'messenger_opened' in src
assert 'r45be_target_drift_rule' in src
assert 'r45ax_target_guard_now' in src
assert 'R45AX_TARGET_DRIFT_BLOCKED' in src
assert 'BLOCKED_TARGET_DRIFT_AFTER_CLICK' in src
assert 'R45AX_SCROLL_STALLED_BLOCKED' in src
assert 'stalled_scroll_cycles' in src
assert r'facebook\.com$/i' in src or r'facebook\.com' in src
assert 'browser_profile_file_parsing_enabled' in src and 'False' in src
print('profile_media_facebook_progress_gated_modal_flatten_r45ax_test: PASS')

assert 'r45bg_hover_guard_rule' in src
assert 'r45ax_park_mouse' in src
assert 'R45AX_PROFILE_HOVER_CARD_CLOSED' in src
assert 'r45axProfileHoverOverlayState' in src
assert 'r45axCloseProfileHoverCards' in src
assert 'profile_hover_closed' in src

assert '--expected-total-comments' in src
assert 'expected_total_comments' in src
assert 'r45ax_filter_expected_progress' in src
assert 'R45AX_PROGRESS_IGNORED_EXPECTED_TOTAL_MISMATCH' in src
assert 'R45BI_EXPECTED_TOTAL_GATE' in src
assert 'r45bi_expected_total_gate_rule' in src
assert 'r45bi_expected_total_gate_present' in src
assert 'BLOCKED_MESSENGER_OVERLAY_STILL_OPEN' in src
assert 'r45ax_write_failure_artifacts' in src
assert 'no coordinate fallback' in src
assert 'mouse_park_only' in src
assert 'r45bl_replied_bucket_fast_path_rule' in src
assert 'reply_count_right' in src
assert "clickLabel:n + (n === '1' ? ' reply' : ' replies')" in src
assert 'R45AX_REPLIED_BUCKET_NO_PROGRESS_SKIPPED' in src
assert 'replied_bucket_fast_skipped' in src
assert 'r45ax_click_wait_ms' in src
assert 'r45axMessengerSideEffectState' in src
assert 'window.r45axMessengerSideEffectState = r45axMessengerSideEffectState' in src
assert 'r45bl_replied_bucket_right_biased_present' in src
assert 'rowRank' in src and 'sourceRank(a.source)-sourceRank(b.source)' in src
