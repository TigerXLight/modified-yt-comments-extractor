import json

from capture_execution_gate import (
    EXECUTION_STATUS_APPROVAL_REQUIRED,
    EXECUTION_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY,
    ExecutionGateApprovalMetadata,
    build_execution_gate_plan,
    build_execution_gate_plan_text,
    build_execution_gate_request,
    execution_gate_plan_to_action_log_events,
)
from capture_execution_gate_cli import run_cli


def run_self_test() -> None:
    request = build_execution_gate_request(
        action_kind="LIVE_SITE_CAPTURE",
        source_label="MSN",
        source_url="https://www.msn.com/example?token=not-used",
        intended_scope="manual smoke",
    )
    assert request.approval_status == EXECUTION_STATUS_APPROVAL_REQUIRED
    assert request.application_execution_allowed is False
    assert request.source_url_recorded is True
    assert request.source_host_label == "www.msn.com"
    assert "https://www.msn.com" not in json.dumps(request.to_dict())

    plan = build_execution_gate_plan((request,))
    plan_dict = plan.to_dict()
    assert plan.status == EXECUTION_STATUS_APPROVAL_REQUIRED
    assert plan.approval_required is True
    assert plan.application_execution_allowed is False
    assert plan.command_count == 0
    assert plan.live_network_allowed is False
    assert plan.browser_automation_allowed is False
    assert plan.archive_provider_allowed is False
    assert plan.download_allowed is False
    assert plan.file_move_allowed is False
    assert plan.broad_folder_scan_allowed is False
    assert plan.provider_call_allowed is False
    assert plan.automatic_classification is False
    assert plan.sensitive_inference_prohibited is True
    assert "no_credentials_cookies_accounts_auth_headers_or_browser_profiles" in plan_dict["safety_prohibitions"]

    approval = ExecutionGateApprovalMetadata(
        approved_by_label_recorded=True,
        approved_at_utc="2026-08-06T12:00:00Z",
        approved_action_ids=(request.request_id,),
        approval_reference_id="manual-approval-placeholder",
        safety_boundaries_acknowledged=True,
    )
    approved_plan = build_execution_gate_plan((request,), approval_metadata=approval)
    assert approved_plan.status == EXECUTION_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
    assert approved_plan.approval_required is False
    assert approved_plan.application_execution_allowed is False
    assert approved_plan.decisions[0].approved_for_manual_operator_only is True
    assert approved_plan.decisions[0].command_emitted is False

    event = execution_gate_plan_to_action_log_events(
        approved_plan,
        session_id="execution-gate-test",
        timestamp_utc="2026-08-06T12:00:00Z",
    )[0]
    event_dict = event.to_dict()
    assert event_dict["result"] == EXECUTION_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
    assert event_dict["request_summary"]["command_count"] == 0
    assert event_dict["request_summary"]["live_network_allowed"] is False
    assert event_dict["request_summary"]["automatic_classification"] is False

    text = build_execution_gate_plan_text(approved_plan)
    assert "Application execution allowed: false" in text
    assert "Commands emitted: 0" in text

    cli_json = run_cli(
        [
            "--action",
            "ARCHIVE_CHECK",
            "--source-url",
            "https://example.test/page",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(cli_json)
    assert parsed["status"] == EXECUTION_STATUS_APPROVAL_REQUIRED
    assert parsed["command_count"] == 0
    assert "https://example.test/page" not in cli_json

    try:
        build_execution_gate_request(action_kind="DRM_CIRCUMVENTION")
    except ValueError as exc:
        assert "Unsupported execution-gate action kind" in str(exc)
    else:
        raise AssertionError("unsupported action should fail closed")


if __name__ == "__main__":
    run_self_test()
    print("Capture execution gate self-test passed.")
