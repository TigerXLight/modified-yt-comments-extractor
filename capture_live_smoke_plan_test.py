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
    DEFAULT_LIVE_SMOKE_SCOPES,
    LIVE_SMOKE_STATUS_APPROVAL_REQUIRED,
    LIVE_SMOKE_STATUS_APPROVED_FOR_MANUAL_OPERATOR_ONLY,
    LIVE_SMOKE_STATUS_COMPLETED_MANUALLY,
    MANUAL_ACTION_SCOPE_ARCHIVE,
    MANUAL_ACTION_SCOPE_COMMENTS,
    MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
    MANUAL_ACTION_SCOPE_LIVECHAT,
    MANUAL_ACTION_SCOPE_MEDIA,
    MANUAL_ACTION_SCOPE_RENDERED_CITATION,
    MANUAL_ACTION_SCOPE_WARC_WACZ,
    MANUAL_ACTION_SCOPE_WEBPAGE,
    SOURCE_URL_APPROVAL_REQUIRED_PLACEHOLDER,
    LiveSmokeSiteApproval,
    build_imported_manual_live_smoke_plan,
    build_live_smoke_plan_from_template,
    build_live_smoke_plan,
    build_named_site_live_smoke_plan_template,
    live_smoke_plan_to_json,
    manual_action_scope_catalog,
    validate_live_smoke_plan_template,
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
    assert "live-site verified" not in repr(data).lower()


def test_site_approval_only_marks_manual_operator_review_not_execution() -> None:
    approval = LiveSmokeSiteApproval(
        site_label="Example News",
        source_url="https://example.invalid/manual-only",
        approved_by="manual reviewer",
        approved_at_utc="2026-07-17T12:00:00Z",
        approved_actions=(
            MANUAL_ACTION_SCOPE_WEBPAGE,
            MANUAL_ACTION_SCOPE_COMMENTS,
        ),
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


def test_approval_fails_without_named_site() -> None:
    approval = LiveSmokeSiteApproval(
        site_label="approval_required",
        source_url="https://example.invalid/manual-only",
        approved_by="manual reviewer",
        approved_at_utc="2026-07-17T12:00:00Z",
        approved_actions=(MANUAL_ACTION_SCOPE_WEBPAGE,),
    )

    plan = build_live_smoke_plan(
        candidate_site_label="approval_required",
        source_url_placeholder="https://example.invalid/manual-only",
        approval=approval,
    )

    assert plan.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert plan.workflow_status == LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    assert any("explicit named site label is required" in note for note in plan.safety_notes)


def test_approval_fails_without_named_source_url() -> None:
    approval = LiveSmokeSiteApproval(
        site_label="Example News",
        source_url=SOURCE_URL_APPROVAL_REQUIRED_PLACEHOLDER,
        approved_by="manual reviewer",
        approved_at_utc="2026-07-17T12:00:00Z",
        approved_actions=(MANUAL_ACTION_SCOPE_WEBPAGE,),
    )

    plan = build_live_smoke_plan(
        candidate_site_label="Example News",
        source_url_placeholder=SOURCE_URL_APPROVAL_REQUIRED_PLACEHOLDER,
        approval=approval,
    )

    assert plan.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert plan.workflow_status == LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    assert any("explicit named source URL is required" in note for note in plan.safety_notes)


def test_approval_fails_without_named_manual_actions() -> None:
    approval = LiveSmokeSiteApproval(
        site_label="Example News",
        source_url="https://example.invalid/manual-only",
        approved_by="manual reviewer",
        approved_at_utc="2026-07-17T12:00:00Z",
        approved_actions=(),
    )

    plan = build_live_smoke_plan(
        candidate_site_label="Example News",
        source_url_placeholder="https://example.invalid/manual-only",
        approval=approval,
    )

    assert plan.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert plan.workflow_status == LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    assert any("at least one named manual action/scope is required" in note for note in plan.safety_notes)


def test_approval_fails_for_unknown_manual_actions() -> None:
    approval = LiveSmokeSiteApproval(
        site_label="Example News",
        source_url="https://example.invalid/manual-only",
        approved_by="manual reviewer",
        approved_at_utc="2026-07-17T12:00:00Z",
        approved_actions=(MANUAL_ACTION_SCOPE_WEBPAGE, "launch_live_browser"),
    )

    plan = build_live_smoke_plan(
        candidate_site_label="Example News",
        source_url_placeholder="https://example.invalid/manual-only",
        approval=approval,
    )

    assert plan.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert plan.workflow_status == LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    assert any("unknown approved manual action/scope" in note for note in plan.safety_notes)


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
    assert any("does not match candidate site" in note for note in plan.safety_notes)


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
    assert tuple(items) == DEFAULT_LIVE_SMOKE_SCOPES
    assert items[MANUAL_ACTION_SCOPE_WEBPAGE].expected_artifact_declaration_type == ARTIFACT_TYPE_RAW_HTML
    assert items[MANUAL_ACTION_SCOPE_COMMENTS].expected_artifact_declaration_type == ARTIFACT_TYPE_COMMENTS_JSONL
    assert items[MANUAL_ACTION_SCOPE_LIVECHAT].expected_artifact_declaration_type == ARTIFACT_TYPE_LIVECHAT_JSONL
    assert items[MANUAL_ACTION_SCOPE_MEDIA].expected_artifact_declaration_type == ARTIFACT_TYPE_MEDIA_INVENTORY
    assert items[MANUAL_ACTION_SCOPE_RENDERED_CITATION].expected_artifact_declaration_type == ARTIFACT_TYPE_RENDERED_RECORDING
    assert items[MANUAL_ACTION_SCOPE_ARCHIVE].expected_artifact_declaration_type == ARTIFACT_TYPE_ARCHIVE_RESULT
    assert "WARC/WACZ" in items[MANUAL_ACTION_SCOPE_WARC_WACZ].expected_artifact_declaration_type
    assert "EXPORT_METADATA_ONLY" in items[MANUAL_ACTION_SCOPE_EXPORT_QUEUE].expected_artifact_declaration_type
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


def test_named_site_template_defaults_to_not_approved_and_approval_required() -> None:
    template = build_named_site_live_smoke_plan_template()
    validation = validate_live_smoke_plan_template(template)
    data = template.to_dict()

    assert template.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert template.workflow_status == LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    assert template.execution_mode == "manual_operator_only"
    assert template.executable_by_application is False
    assert data["execution_commands"] == []
    assert "placeholder site label" in validation.errors
    assert "placeholder source URL" in validation.errors
    assert "missing approver metadata" in validation.errors
    assert "missing safety acknowledgement" in validation.errors


def test_named_site_template_validation_rejects_missing_and_placeholder_fields() -> None:
    missing = build_named_site_live_smoke_plan_template(
        site_label="",
        source_url="",
        manual_action_scope_ids=(),
        approver_metadata="",
        safety_boundary_acknowledged=False,
    )
    placeholder = build_named_site_live_smoke_plan_template(
        site_label="approval_required",
        source_url=SOURCE_URL_APPROVAL_REQUIRED_PLACEHOLDER,
        manual_action_scope_ids=(MANUAL_ACTION_SCOPE_WEBPAGE,),
        approver_metadata="APPROVER_METADATA_REQUIRED",
        safety_boundary_acknowledged=False,
    )

    missing_validation = validate_live_smoke_plan_template(missing)
    placeholder_validation = validate_live_smoke_plan_template(placeholder)

    assert "missing site label" in missing_validation.errors
    assert "missing source URL" in missing_validation.errors
    assert "missing manual action/scope IDs" in missing_validation.errors
    assert "missing approver metadata" in missing_validation.errors
    assert "missing safety acknowledgement" in missing_validation.errors
    assert "placeholder site label" in placeholder_validation.errors
    assert "placeholder source URL" in placeholder_validation.errors


def test_named_site_template_validation_rejects_unknown_scopes() -> None:
    template = build_named_site_live_smoke_plan_template(
        site_label="Example News",
        source_url="https://example.invalid/manual-only",
        manual_action_scope_ids=(MANUAL_ACTION_SCOPE_WEBPAGE, "launch_live_browser"),
        approver_metadata="approval ticket 123",
        safety_boundary_acknowledged=True,
    )
    validation = validate_live_smoke_plan_template(template)

    assert validation.is_valid is False
    assert "unknown manual action/scope IDs: launch_live_browser" in validation.errors


def test_valid_named_site_template_builds_unapproved_manual_operator_plan() -> None:
    template = build_named_site_live_smoke_plan_template(
        site_label="Example News",
        source_url="https://example.invalid/manual-only",
        source_adapter_family="news_website",
        manual_action_scope_ids=(MANUAL_ACTION_SCOPE_WEBPAGE, MANUAL_ACTION_SCOPE_COMMENTS),
        approver_metadata="approval placeholder for future user approval",
        safety_boundary_acknowledged=True,
    )
    validation = validate_live_smoke_plan_template(template)
    plan = build_live_smoke_plan_from_template(template)

    assert validation.is_valid is True
    assert validation.errors == ()
    assert template.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert template.execution_mode == "manual_operator_only"
    assert plan.approval_status == APPROVAL_STATUS_NOT_APPROVED
    assert plan.workflow_status == LIVE_SMOKE_STATUS_APPROVAL_REQUIRED
    assert plan.executable_by_application is False
    assert plan.intended_scopes == (MANUAL_ACTION_SCOPE_WEBPAGE, MANUAL_ACTION_SCOPE_COMMENTS)
    assert plan.execution_commands == ()


def test_template_helper_path_cannot_produce_completed_manually() -> None:
    template = build_named_site_live_smoke_plan_template(
        site_label="Example News",
        source_url="https://example.invalid/manual-only",
        manual_action_scope_ids=(MANUAL_ACTION_SCOPE_WEBPAGE,),
        approver_metadata="approval placeholder for future user approval",
        safety_boundary_acknowledged=True,
    )
    plan = build_live_smoke_plan_from_template(template)

    assert template.workflow_status != LIVE_SMOKE_STATUS_COMPLETED_MANUALLY
    assert plan.workflow_status != LIVE_SMOKE_STATUS_COMPLETED_MANUALLY


def test_manual_action_scope_catalog_contains_expected_named_scopes() -> None:
    catalog = manual_action_scope_catalog()
    items = {item.scope: item for item in catalog}

    assert tuple(items) == (
        MANUAL_ACTION_SCOPE_WEBPAGE,
        MANUAL_ACTION_SCOPE_COMMENTS,
        MANUAL_ACTION_SCOPE_LIVECHAT,
        MANUAL_ACTION_SCOPE_MEDIA,
        MANUAL_ACTION_SCOPE_RENDERED_CITATION,
        MANUAL_ACTION_SCOPE_ARCHIVE,
        MANUAL_ACTION_SCOPE_WARC_WACZ,
        MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
    )
    assert items[MANUAL_ACTION_SCOPE_WEBPAGE].expected_artifact_declaration_type == ARTIFACT_TYPE_RAW_HTML
    assert items[MANUAL_ACTION_SCOPE_COMMENTS].expected_artifact_declaration_type == ARTIFACT_TYPE_COMMENTS_JSONL
    assert all(item.result_placeholder == "not_run" for item in catalog)


def run_self_test() -> None:
    test_default_live_smoke_plan_requires_approval_and_cannot_execute()
    test_site_approval_only_marks_manual_operator_review_not_execution()
    test_approval_fails_without_named_site()
    test_approval_fails_without_named_source_url()
    test_approval_fails_without_named_manual_actions()
    test_approval_fails_for_unknown_manual_actions()
    test_mismatched_approval_keeps_plan_not_approved()
    test_completed_manually_is_only_imported_manual_metadata()
    test_checklist_contains_expected_scopes_and_artifact_declaration_types()
    test_safety_prohibitions_are_visible_and_no_command_is_emitted()
    test_named_site_template_defaults_to_not_approved_and_approval_required()
    test_named_site_template_validation_rejects_missing_and_placeholder_fields()
    test_named_site_template_validation_rejects_unknown_scopes()
    test_valid_named_site_template_builds_unapproved_manual_operator_plan()
    test_template_helper_path_cannot_produce_completed_manually()
    test_manual_action_scope_catalog_contains_expected_named_scopes()


if __name__ == "__main__":
    run_self_test()
    print("Capture live smoke plan self-test passed.")
