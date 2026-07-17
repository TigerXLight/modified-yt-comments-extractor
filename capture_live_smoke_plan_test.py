import json

from capture_contracts import (
    ARTIFACT_TYPE_ARCHIVE_RESULT,
    ARTIFACT_TYPE_COMMENTS_JSONL,
    ARTIFACT_TYPE_LIVECHAT_JSONL,
    ARTIFACT_TYPE_MEDIA_INVENTORY,
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_RENDERED_RECORDING,
)
from capture_live_smoke_plan import (
    APPROVAL_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY,
    APPROVAL_STATUS_NOT_APPROVED,
    LIVE_SMOKE_STATUS_APPROVAL_REQUIRED,
    LIVE_SMOKE_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY,
    LIVE_SMOKE_STATUS_COMPLETED_MANUALLY,
    LiveSmokeSiteApproval,
    build_imported_manual_live_smoke_plan,
    build_live_smoke_plan,
    live_smoke_plan_to_json,
)


def test_default_live_smoke_plan_requires_approval_and_cannot_execute() -> None:
    plan = build_live_smoke_plan(candidate_site_label="Example News")
    data = plan.to_dict()

    assert plan.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert plan.workflow_status == LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    assert plan.executable_by_application is False
    assert data["executable_by_application"] is False
    assert data["execution_commands"] == []
    assert data["live_network_actions_performed"] == "none"
    assert data["artifact_files_created"] == "none"
    assert "APPROVAL_REQUIRED" in data["safety_notes"]
    assert "MANUAL_LIVE_SITE_SMOKE_PENDING" in data["safety_notes"]
    assert "LIVE_SITE_MANUALLY_VERIFIED" not in repr(data)


def test_site_approval_only_marks_manual_operator_review_not_execution() -> None:
    approval = LiveSmokeSiteApproval(
        site_label="Example News",
        source_url="https://example.invalid/manual-only",
        approved_by="manual reviewer",
        approved_at_utc="2026-07-17T12:00:00Z",
        approved_actions=("manual page review", "manual comments note"),
    )

    plan = build_live_smoke_plan(
        candidate_site_label="Example News",
        source_url_placeholder="https://example.invalid/manual-only",
        source_adapter_family="news_website",
        approval=approval,
    )

    assert plan.approval_status == APPROVAL_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
    assert plan.workflow_status == LIVE_SMOKE_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY
    assert plan.executable_by_application is False
    assert plan.execution_commands == ()
    assert any("manual operator" in note.lower() for note in plan.safety_notes)


def test_mismatched_approval_keeps_plan_not_approved() -> None:
    approval = LiveSmokeSiteApproval(
        site_label="Other Site",
        source_url="https://example.invalid/manual-only",
        approved_by="manual reviewer",
        approved_at_utc="2026-07-17T12:00:00Z",
    )

    plan = build_live_smoke_plan(
        candidate_site_label="Example News",
        source_url_placeholder="https://example.invalid/manual-only",
        approval=approval,
    )

    assert plan.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert plan.workflow_status == LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    assert any("did not match" in note for note in plan.safety_notes)


def test_completed_manually_is_only_imported_manual_metadata() -> None:
    default = build_live_smoke_plan(candidate_site_label="Example News")
    imported = build_imported_manual_live_smoke_plan(
        candidate_site_label="Example News",
        source_url_placeholder="https://example.invalid/manual-only",
        source_adapter_family="news_website",
        workflow_status=LIVE_SMOKE_STATUS_COMPLETED_MANUALLY,
        imported_manual_result={
            "operator_note": "User reported manual review completed outside Codex.",
            "artifact_files_created": "not by this scaffold",
        },
    )

    assert default.workflow_status != LIVE_SMOKE_STATUS_COMPLETED_MANUALLY
    assert imported.workflow_status == LIVE_SMOKE_STATUS_COMPLETED_MANUALLY
    assert imported.imported_manual_result["artifact_files_created"] == "not by this scaffold"
    assert imported.executable_by_application is False


def test_checklist_contains_expected_scopes_and_artifact_declaration_types() -> None:
    plan = build_live_smoke_plan(candidate_site_label="Example News")
    items = {item.scope: item for item in plan.checklist_items}

    assert set(items) == set(plan.intended_scopes)
    assert items["webpage_snapshot_manual_review"].expected_artifact_declaration_type == ARTIFACT_TYPE_RAW_HTML
    assert items["comments_presence_manual_review"].expected_artifact_declaration_type == ARTIFACT_TYPE_COMMENTS_JSONL
    assert items["livechat_availability_manual_review"].expected_artifact_declaration_type == ARTIFACT_TYPE_LIVECHAT_JSONL
    assert items["media_discovery_manual_review"].expected_artifact_declaration_type == ARTIFACT_TYPE_MEDIA_INVENTORY
    assert items["rendered_citation_manual_operator_note"].expected_artifact_declaration_type == ARTIFACT_TYPE_RENDERED_RECORDING
    assert items["archive_availability_manual_note"].expected_artifact_declaration_type == ARTIFACT_TYPE_ARCHIVE_RESULT
    assert "WARC/WACZ" in items["warc_wacz_future_manual_note"].expected_artifact_declaration_type
    assert "EXPORT_METADATA_ONLY" in items["export_queue_metadata_review"].expected_artifact_declaration_type
    assert all(item.result_placeholder == "not_run" for item in plan.checklist_items)
    assert all("If separately approved" in item.manual_instruction for item in plan.checklist_items)
    assert all("operator" in item.manual_instruction.lower() for item in plan.checklist_items)


def test_safety_prohibitions_are_visible_and_no_command_is_emitted() -> None:
    plan = build_live_smoke_plan(candidate_site_label="Example News")
    rendered = live_smoke_plan_to_json(plan)
    parsed = json.loads(rendered)

    for phrase in (
        "no CAPTCHA solving",
        "no stealth/fingerprint evasion",
        "no proxy rotation",
        "no credential/cookie use",
        "no DRM/CDM/EME/HDCP/protected-buffer circumvention",
        "no broad folder scan",
        "no evidence file move",
        "no provider/network call without later approval",
    ):
        assert phrase in parsed["safety_prohibitions"]
        assert phrase in rendered

    forbidden_execution_markers = (
        "requests.get",
        "requests.post",
        "playwright.chromium.launch",
        "archivebox add",
        "yt-dlp",
        "ffmpeg ",
        "warcio",
        "subprocess",
        "selenium",
    )
    assert parsed["execution_commands"] == []
    command_text = " ".join(parsed["execution_commands"])
    for marker in forbidden_execution_markers:
        assert marker not in command_text
    assert parsed["live_network_actions_performed"] == "none"


def run_self_test() -> None:
    test_default_live_smoke_plan_requires_approval_and_cannot_execute()
    test_site_approval_only_marks_manual_operator_review_not_execution()
    test_mismatched_approval_keeps_plan_not_approved()
    test_completed_manually_is_only_imported_manual_metadata()
    test_checklist_contains_expected_scopes_and_artifact_declaration_types()
    test_safety_prohibitions_are_visible_and_no_command_is_emitted()


if __name__ == "__main__":
    run_self_test()
    print("Capture live smoke plan self-test passed.")
