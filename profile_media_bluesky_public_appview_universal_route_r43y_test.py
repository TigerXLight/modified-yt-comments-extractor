from __future__ import annotations

import shutil
from pathlib import Path

from profile_media_bluesky_public_appview_universal_route_r43y import (
    R43Y_PASS_STATUS,
    BlueskyPublicAppviewUniversalRouteRequestR43Y,
    build_bluesky_public_appview_universal_route_contract_r43y,
    build_bluesky_public_appview_universal_route_r43y,
    build_report,
)
from profile_media_universal_social_account_tracking_r43e import coerce_universal_social_account_tracking_request_r43e
from profile_media_universal_social_batch_workbench_app_shell_commands_r43l import coerce_universal_social_batch_workbench_app_shell_command_request_r43l
from profile_media_universal_social_batch_queue_workbench_panel_r43j import coerce_universal_social_batch_queue_workbench_panel_request_r43j
from profile_media_universal_social_batch_queue_workbench_controls_r43i import coerce_universal_social_batch_queue_workbench_request_r43i
from profile_media_universal_social_batch_queue_resume_dedupe_progress_r43h import coerce_universal_social_batch_queue_request_r43h
from profile_media_universal_social_batch_account_intake_platform_url_detection_r43g import coerce_universal_social_batch_account_intake_request_r43g
from profile_media_universal_social_export_surface_ui_routing_r43f import coerce_universal_social_export_surface_request_r43f


def _clean_root(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_public_network_flag_is_available_on_all_universal_route_requests() -> None:
    assert coerce_universal_social_account_tracking_request_r43e({"public_network_enabled": True}).public_network_enabled is True
    assert coerce_universal_social_export_surface_request_r43f({"public_network_enabled": True}).public_network_enabled is True
    assert coerce_universal_social_batch_account_intake_request_r43g({"public_network_enabled": True}).public_network_enabled is True
    assert coerce_universal_social_batch_queue_request_r43h({"public_network_enabled": True}).public_network_enabled is True
    assert coerce_universal_social_batch_queue_workbench_request_r43i({"public_network_enabled": True}).public_network_enabled is True
    assert coerce_universal_social_batch_queue_workbench_panel_request_r43j({"public_network_enabled": True}).public_network_enabled is True
    assert coerce_universal_social_batch_workbench_app_shell_command_request_r43l({"public_network_enabled": True}).public_network_enabled is True


def test_r43y_routes_normal_bluesky_profile_through_app_shell_to_r43w_without_real_network(tmp_path: Path) -> None:
    root = _clean_root(tmp_path / "route")
    runner = build_bluesky_public_appview_universal_route_r43y(output_root=root)
    result = runner.run_route_smoke(
        BlueskyPublicAppviewUniversalRouteRequestR43Y(
            account_url="https://bsky.app/profile/bsky.app",
            account_handle="bsky.app",
            capture_timestamp="20260918T073100Z",
            output_root=str(root),
            public_network_enabled=True,
            explicit_live_mode=True,
            fixture_mode=False,
            max_items=2,
        )
    )
    assert result.status == R43Y_PASS_STATUS, result.warnings
    assert result.route_status == "dispatched_to_bluesky_adapter_via_r43e_adapter_map"
    assert result.r43w_status.startswith("PASS_R43W_")
    assert result.adapter_status.startswith("PASS_R43V_")
    assert result.ledger_status.startswith("PASS_R43U_")
    assert result.public_network_enabled_reached_r43w is True
    assert result.explicit_live_mode_reached_r43w is True
    assert result.real_network_performed_by_r43y_test is False
    assert result.browser_session_started is False
    assert result.cookie_or_token_extraction_performed is False
    assert result.remote_media_downloads_performed is False
    assert result.record_count >= 2
    assert result.media_count >= 1
    assert all(Path(path).is_file() for path in result.fake_appview_payload_paths)


def test_r43y_contract_and_report_pass(tmp_path: Path) -> None:
    root = _clean_root(tmp_path / "report")
    contract = build_bluesky_public_appview_universal_route_contract_r43y()
    assert contract["explicit_public_network_gate_required"] is True
    assert "R43W -> R43V -> R43U" in contract["downstream_route_for_bluesky_public_appview"]
    report = build_report(root)
    assert report.status == R43Y_PASS_STATUS, [c for c in report.checks if c["status"] != "pass"]
    assert report.sample_result["r43w_status"].startswith("PASS_R43W_")
    assert report.sample_result["public_network_enabled_reached_r43w"] is True


def run_self_test() -> None:
    root = _clean_root(Path("profile_media_live_captures") / "r43y_bluesky_public_appview_universal_route_test")
    test_public_network_flag_is_available_on_all_universal_route_requests()
    test_r43y_routes_normal_bluesky_profile_through_app_shell_to_r43w_without_real_network(root / "direct")
    test_r43y_contract_and_report_pass(root / "report")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_bluesky_public_appview_universal_route_r43y_test: PASS")
