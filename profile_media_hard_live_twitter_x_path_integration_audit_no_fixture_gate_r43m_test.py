from __future__ import annotations

import json
from pathlib import Path

from profile_media_hard_live_twitter_x_path_integration_audit_no_fixture_gate_r43m import (
    R43M_MARKER,
    R43M_PASS_STATUS,
    build_report,
    prove_app_shell_to_r42gz_boundary,
    write_report,
)


def test_monkeypatched_app_shell_path_reaches_r42gz_without_browser_start() -> None:
    proof = prove_app_shell_to_r42gz_boundary(
        "profile_media_live_captures/r43m_hard_live_twitter_x_path_integration_audit_no_fixture_gate/test_live_boundary"
    )

    assert proof["stub_runner_invoked"] is True
    assert proof["stub_runner_call_count"] >= 1
    assert proof["fixture_mode_used"] is False
    assert proof["browser_started_during_test"] is False
    assert proof["network_access_during_test"] is False
    assert proof["remote_media_downloads_during_test"] is False
    assert proof["live_boundary_module"] == "profile_media_independent_fast_media_webview2_lane_r42gz"
    assert proof["live_boundary_function"] == "IndependentFastMediaWebView2LaneBackendR42GZ.observe_media"
    assert proof["app_shell_route_chain"] == "R43L -> R43J/R43K -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D"

    blob = json.dumps(proof, sort_keys=True)
    assert "](" not in blob
    assert "]\\(" not in blob


def test_report_passes_with_live_boundary_and_safe_control_plane_checks() -> None:
    output_root = "profile_media_live_captures/r43m_hard_live_twitter_x_path_integration_audit_no_fixture_gate/test_report"
    report = build_report(output_root)
    json_path, _md_path = write_report(report, output_root)
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))

    assert payload["marker"] == R43M_MARKER
    assert payload["status"] == R43M_PASS_STATUS
    assert payload["bad_checks"] == []
    checks = {check["name"]: check["status"] for check in payload["checks"]}
    for required in (
        "main_registers_r43l_app_shell",
        "r43l_delegates_to_r43j_or_r43k_only",
        "r43j_delegates_to_r43i_only",
        "r43i_delegates_to_r43h_only",
        "r43h_delegates_to_r43g_only",
        "r43g_delegates_to_r43f_only",
        "r43f_delegates_to_r43e_only",
        "r43e_dispatches_twitter_x_to_r43d",
        "r43d_dispatches_twitter_x_to_r43b",
        "r43b_live_mode_reaches_r42gz_boundary",
        "r42gz_reaches_r42gy_or_r42gv_media_observation_boundary",
        "r42gy_r42gv_media_observation_store_available",
        "no_fixture_sample_probe_path_used_for_live_gate",
        "monkeypatched_live_boundary_invoked_without_browser_start",
        "control_plane_no_hidden_api_cookie_token_or_challenge_bypass_behaviour",
        "no_browser_started_during_tests",
        "no_network_access_during_tests",
        "no_source_role_or_review_window_side_effects",
        "no_remote_media_downloads_during_tests",
        "youtube_capture_engine_unchanged",
        "plain_machine_urls",
    ):
        assert checks[required] == "pass"

    proof = payload["live_boundary_proof"]
    assert proof["stub_runner_invoked"] is True
    assert proof["fixture_mode_used"] is False
    assert proof["browser_started_during_test"] is False
    assert proof["network_access_during_test"] is False
    assert proof["remote_media_downloads_during_test"] is False


if __name__ == "__main__":
    test_monkeypatched_app_shell_path_reaches_r42gz_without_browser_start()
    test_report_passes_with_live_boundary_and_safe_control_plane_checks()
    print("PASS profile_media_hard_live_twitter_x_path_integration_audit_no_fixture_gate_r43m_test")
