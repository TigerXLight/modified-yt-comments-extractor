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
assert 'r45axExpectedTotalEvidence' in src
assert "new RegExp('\\\\b\\\\d{1,5}\\\\s+of\\\\s+'" in src
assert "new RegExp('\\\\\\\\b\\\\\\\\d{1,5}" not in src
assert 'window.r45axExpectedTotalEvidence = r45axExpectedTotalEvidence' in src
assert 'audit_fast' in src
assert 'blank_audit_fast_scrolls' in src
assert 'audit_pass >= 2 and not audit_had_click' in src
assert 'BLOCKED_EXPECTED_TOTAL_MARKER_NOT_OBSERVABLE_AFTER_STABLE_AUDIT' in src
assert 'BLOCKED_EXPECTED_TOTAL_PROGRESS_UNSATISFIED_AFTER_STABLE_AUDIT' in src
assert 'expected_total_diagnostic' in src
assert 'r45bm_expected_total_diagnostic_block_present' in src
assert 'text_force_hidden' in src
assert 'element_force_hidden' in src
assert 'r45axCandidateContext' in src
assert 'contextHash' in src
assert "+'|'+(item.contextHash || '')" in src
assert 'r45bn_hidden_control_force_candidate_present' in src
assert 'r45bn_contextual_dead_key_present' in src
assert 'r45axHiddenExpansionBand' in src
assert 'r.bottom - 8' in src
assert "category === 'view_hidden' ? hiddenBand : band" in src
assert 'r45bo_bottom_hidden_comments_band_present' in src
assert 'r45axFinalBottomMaterializationProbe' in src
assert 'R45AX_FINAL_BOTTOM_MATERIALIZATION_PROBE' in src
assert 'final_bottom_materialization_result' in src
assert 'hiddenByFacebookCount' in src
assert 'sortFilterState' in src
assert 'r45bp_final_bottom_materialization_probe_present' in src
assert 'r45bp_final_bottom_diagnostics_present' in src
assert '--speed-profile' in src
assert 'safe_fast' in src
assert 'R45AX_FAST_CLICK' in src
assert 'r45ax_adaptive_click_wait_ms' in src
assert 'run_expensive_click_checks' in src
assert 'fast_clicks % 12 == 0' in src
assert 'speed_profile_safe_fast_present' in src
assert 'fast_bottom_hidden_comments_loop_present' in src
assert 'adaptive_waits_present' in src
assert 'expensive_checks_periodic_not_every_fast_click' in src
assert 'r45ax_turbo_visible_speed_profile_present' in src
assert 'r45ax_turbo_visible_batch_click_present' in src
assert 'r45ax_turbo_burst_speed_profile_present' in src
assert 'r45ax_turbo_burst_cdp_click_present' in src
assert 'r45ax_bottom_hidden_comments_turbo_chain_present' in src
assert 'r45ax_foreground_keepalive_present' in src
assert 'r45ax_active_window_keepalive_present' in src
assert 'r45ax_chromium_throttle_flags_present' in src
assert "choices=['turbo_burst','turbo_visible','safe_fast','strict']" in src
assert "default='turbo_burst'" in src
assert 'Input.dispatchMouseEvent' in src
assert 'r45ax_cdp_turbo_burst' in src
assert 'r45axTurboVisibleBatch' in src
assert 'r45axTurboBottomHiddenCommentsChain' in src
assert 'window.r45axClickSafetyAt = r45axClickSafetyAt' in src
assert 'R45AX_TURBO_BURST_START' in src
assert 'R45AX_TURBO_BURST_CLICKED' in src
assert 'R45AX_TURBO_BURST_SETTLE' in src
assert 'R45AX_TURBO_BURST_FALLBACK' in src
assert 'R45AX_TURBO_BATCH' in src
assert 'R45AX_TURBO_BOTTOM_CHAIN' in src
assert '--keep-page-foreground' in src
assert '--no-keep-page-foreground' in src
assert 'R45AX_FOREGROUND_KEEPALIVE' in src
assert 'R45AX_CHROMIUM_THROTTLE_FLAGS' in src
assert '--disable-background-timer-throttling' in src
assert '--disable-backgrounding-occluded-windows' in src
assert '--disable-renderer-backgrounding' in src
assert 'CalculateNativeWinOcclusion,IntensiveWakeUpThrottling' in src
assert 'turbo_clicks' in src
assert 'burst_candidates' in src
assert 'burst_clicked' in src
assert 'burst_clicks_per_second' in src
assert 'cdp_clicks' in src
assert 'playwright_fallback_clicks' in src
assert 'dom_clicks' in src
assert 'average_turbo_batch_ms' in src
assert 'average_turbo_click_ms' in src
assert 'expected_total_gate_preserved' in src
assert 'clicks_per_minute' in src
assert 'average_click_elapsed_ms' in src
