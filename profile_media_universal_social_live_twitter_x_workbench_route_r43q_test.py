from __future__ import annotations

import json
from pathlib import Path

from profile_media_universal_social_live_twitter_x_workbench_route_r43q import (
    R43Q_MARKER,
    R43Q_PASS_STATUS,
    build_report,
)


def test_r43q_live_options_reach_r43d_and_counts_bubble_to_app_shell_receipt(tmp_path: Path) -> None:
    report = build_report(tmp_path / "r43q")
    assert report.marker == R43Q_MARKER
    assert report.status == R43Q_PASS_STATUS
    assert report.bad_checks == ()

    report_json = tmp_path / "r43q" / "R43Q_UNIVERSAL_SOCIAL_LIVE_TWITTER_X_WORKBENCH_ROUTE_REPORT.json"
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["status"] == R43Q_PASS_STATUS
    assert payload["bad_checks"] == []

    receipt = json.loads(Path(payload["app_shell_receipt_path"]).read_text(encoding="utf-8"))
    summary = receipt["live_evidence_summary"]
    assert summary["r43n_status"].startswith("PASS_R43N_")
    assert summary["r43o_status"].startswith("PASS_R43O_")
    assert summary["r43p_status"].startswith("PASS_R43P_")
    assert summary["promoted_observed_post_count"] == 3
    assert summary["promoted_observed_media_count"] == 72
    assert summary["promoted_observed_screenshot_count"] == 1
    assert summary["promoted_live_observation_paths"]


def test_r43q_report_proves_safe_route_and_network_only_guards(tmp_path: Path) -> None:
    report = build_report(tmp_path / "r43q_guards")
    checks = {check["name"]: check["status"] for check in report.checks}
    assert checks["normal_safe_route_unchanged_without_live_mode"] == "pass"
    assert checks["network_only_evidence_does_not_pass"] == "pass"
    assert checks["markdown_wrapped_urls_normalized"] == "pass"
    assert checks["queue_resume_preserves_live_options"] == "pass"
    assert checks["plain_machine_urls"] == "pass"


if __name__ == "__main__":
    import tempfile

    root = Path(tempfile.mkdtemp(prefix="r43q_test_"))
    test_r43q_live_options_reach_r43d_and_counts_bubble_to_app_shell_receipt(root)
    test_r43q_report_proves_safe_route_and_network_only_guards(root)
    print("R43Q tests passed")
