from __future__ import annotations

from profile_media_database_implementation_readiness import build_implementation_readiness_report, render_implementation_readiness_text


def test_readiness_report_marks_gui_panel_ready_when_regression_passes():
    report = build_implementation_readiness_report({"status": "success", "workbench": {"status": "success"}, "safety_audit": {"status": "passed"}})
    payload = report.to_dict()
    assert payload["status"] == "ready_for_gui_panel_integration"
    assert payload["ready_for_gui_panel"] is True
    assert payload["pending_count"] >= 1
    text = render_implementation_readiness_text(report)
    assert "Main GUI Database workbench panel" in text
    assert "Existing folder import" in text


def test_readiness_report_blocks_on_failed_regression():
    report = build_implementation_readiness_report({"status": "failed", "workbench": {"status": "success"}, "safety_audit": {"status": "passed"}})
    assert report.status == "blocked_until_regression_repaired"
    assert report.warnings


def main() -> int:
    test_readiness_report_marks_gui_panel_ready_when_regression_passes()
    test_readiness_report_blocks_on_failed_regression()
    print("profile_media_database_implementation_readiness v76b OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
