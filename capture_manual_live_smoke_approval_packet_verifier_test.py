from __future__ import annotations

import tempfile

from capture_manual_live_smoke_approval_packet_store_cli import (
    build_capture_manual_live_smoke_approval_packet_store_cli_result,
)
from capture_manual_live_smoke_approval_packet_verifier import (
    capture_manual_live_smoke_approval_packet_verifier_report_to_json,
    verify_capture_manual_live_smoke_approval_packet,
)


def _safe_store_cli_result(temp_dir: str):
    return build_capture_manual_live_smoke_approval_packet_store_cli_result(
        [
            {
                "site_id": "msn",
                "requested_action": "manual_comment_observation",
            }
        ],
        temp_dir,
    ).to_dict()


def test_verifier_accepts_safe_store_cli_result() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = _safe_store_cli_result(temp_dir)
        packet = {
            "schema_version": "capture_manual_live_smoke_approval_packet_v1",
            "target_count": 1,
            "runtime_execution_performed": False,
            "live_network_request_performed": False,
            "browser_automation_performed": False,
            "completed_capture_claimed": False,
        }
        report = verify_capture_manual_live_smoke_approval_packet([packet, result])
        data = report.to_dict()
        assert data["schema_version"] == "capture_manual_live_smoke_approval_packet_verifier_v1"
        assert data["approval_packet_ready_for_user_review"] is True
        assert data["issue_count"] == 0
        assert "capture_manual_live_smoke_approval_packet_store_cli_v1" in data["observed_schema_versions"]
        assert data["stored_file_names"] == ["capture_manual_live_smoke_approval_packet.json"]
        payload = capture_manual_live_smoke_approval_packet_verifier_report_to_json(report)
        assert temp_dir not in payload


def test_verifier_rejects_unsafe_flags() -> None:
    report = verify_capture_manual_live_smoke_approval_packet(
        {
            "schema_version": "capture_manual_live_smoke_approval_packet_v1",
            "target_count": 1,
            "live_network_request_performed": True,
            "completed_capture_claimed": True,
        }
    )
    data = report.to_dict()
    assert data["approval_packet_ready_for_user_review"] is False
    assert data["issue_count"] >= 2
    codes = {issue["code"] for issue in data["issues"]}
    assert "unsafe_live_network_request_performed" in codes
    assert "unsafe_completed_capture_claimed" in codes


if __name__ == "__main__":
    test_verifier_accepts_safe_store_cli_result()
    test_verifier_rejects_unsafe_flags()
    print("Manual live smoke approval packet verifier self-test passed.")
