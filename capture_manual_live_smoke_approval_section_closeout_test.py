from __future__ import annotations

import tempfile

from capture_manual_live_smoke_approval_packet_store_cli import (
    build_capture_manual_live_smoke_approval_packet_store_cli_result,
)
from capture_manual_live_smoke_approval_section_closeout import (
    build_capture_manual_live_smoke_approval_section_closeout_report,
    capture_manual_live_smoke_approval_section_closeout_report_to_json,
)


def test_section_closeout_reports_manual_review_ready_boundary() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        store_cli = build_capture_manual_live_smoke_approval_packet_store_cli_result(
            [{"site_id": "msn", "requested_action": "manual_comment_scroll_check"}],
            temp_dir,
        ).to_dict()
        packet = {
            "schema_version": "capture_manual_live_smoke_approval_packet_v1",
            "target_count": 1,
            "runtime_execution_performed": False,
            "live_network_request_performed": False,
            "browser_automation_performed": False,
            "completed_capture_claimed": False,
        }
        report = build_capture_manual_live_smoke_approval_section_closeout_report([packet, store_cli])
        data = report.to_dict()
        assert data["schema_version"] == "capture_manual_live_smoke_approval_section_closeout_v1"
        assert data["roadmap_section"] == "REV4 manual live site-smoke approval boundary"
        assert data["section_ready_for_manual_review"] is True
        assert data["review_status"] == "USER_REVIEW_REQUIRED"
        assert data["execution_mode"] == "MANUAL_OPERATOR_ONLY"
        assert data["live_network_request_performed"] is False
        assert data["completed_capture_claimed"] is False
        assert "request_separate_user_approval_before_any_live_or_manual_site_smoke" in data["next_actions"]
        payload = capture_manual_live_smoke_approval_section_closeout_report_to_json(report)
        assert temp_dir not in payload


def test_section_closeout_keeps_issues_visible() -> None:
    report = build_capture_manual_live_smoke_approval_section_closeout_report(
        {"schema_version": "capture_manual_live_smoke_approval_packet_v1", "browser_automation_performed": True}
    )
    data = report.to_dict()
    assert data["section_ready_for_manual_review"] is False
    assert data["issue_count"] >= 1
    assert "fix_manual_approval_packet_issues" in data["next_actions"]


if __name__ == "__main__":
    test_section_closeout_reports_manual_review_ready_boundary()
    test_section_closeout_keeps_issues_visible()
    print("Manual live smoke approval section closeout self-test passed.")
