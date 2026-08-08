from __future__ import annotations

from source_operator_approval_gateway import (
    OperatorApprovalStatus,
    OperatorExecutionAction,
    OperatorExecutionScope,
    build_operator_approval_gateway_summary,
    build_operator_approval_token,
    evaluate_operator_approval,
)


def test_preview_and_missing_approval_block_execution() -> None:
    preview = evaluate_operator_approval(
        OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
        requested_scope=OperatorExecutionScope.PREVIEW_ONLY,
    )
    assert preview.status == OperatorApprovalStatus.PREVIEW_ONLY
    assert preview.allowed_to_execute is False

    missing = evaluate_operator_approval(
        OperatorExecutionAction.MEDIA_DOWNLOAD_COPY,
        requested_scope=OperatorExecutionScope.LOCAL_TEMP,
    )
    assert missing.status == OperatorApprovalStatus.BLOCKED_MISSING_APPROVAL
    assert "operator_approval_token_required" in missing.reasons


def test_approved_local_temp_actions_are_allowed() -> None:
    token = build_operator_approval_token(
        actions=(
            OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
            OperatorExecutionAction.MEDIA_DOWNLOAD_COPY,
            OperatorExecutionAction.OFFLINE_BUNDLE_WRITE,
        ),
        scope=OperatorExecutionScope.LOCAL_TEMP,
        approved_by_operator=True,
    )
    summary = build_operator_approval_gateway_summary(
        (
            OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
            OperatorExecutionAction.MEDIA_DOWNLOAD_COPY,
            OperatorExecutionAction.OFFLINE_BUNDLE_WRITE,
        ),
        token=token,
        requested_scope=OperatorExecutionScope.LOCAL_TEMP,
    )
    assert summary.blocked_count == 0
    assert summary.approved_count == 3
    assert {decision.status for decision in summary.decisions} == {
        OperatorApprovalStatus.APPROVED_LOCAL_TEMP_EXECUTION
    }


def test_external_archive_submit_subprocess_user_evidence_and_asr_need_specific_flags() -> None:
    token = build_operator_approval_token(
        actions=(
            OperatorExecutionAction.ARCHIVE_SUBMIT,
            OperatorExecutionAction.FFMPEG_MUX,
            OperatorExecutionAction.EVIDENCE_FILE_MOVE,
            OperatorExecutionAction.ASR_EXECUTION_READINESS,
        ),
        scope=OperatorExecutionScope.LIVE_EXTERNAL,
        approved_by_operator=True,
    )
    archive = evaluate_operator_approval(
        OperatorExecutionAction.ARCHIVE_SUBMIT,
        token=token,
        requested_scope=OperatorExecutionScope.LIVE_EXTERNAL,
    )
    assert archive.allowed_to_execute is False
    assert "external_network_approval_required" in archive.reasons
    assert "archive_submit_approval_required" in archive.reasons

    approved = build_operator_approval_token(
        actions=(
            OperatorExecutionAction.ARCHIVE_SUBMIT,
            OperatorExecutionAction.FFMPEG_MUX,
            OperatorExecutionAction.EVIDENCE_FILE_MOVE,
            OperatorExecutionAction.ASR_EXECUTION_READINESS,
        ),
        scope=OperatorExecutionScope.LIVE_EXTERNAL,
        approved_by_operator=True,
        allow_external_network=True,
        allow_archive_submit=True,
        allow_subprocess_execution=True,
        allow_user_evidence_movement=True,
        allow_asr_execution=True,
    )
    for action in (
        OperatorExecutionAction.ARCHIVE_SUBMIT,
        OperatorExecutionAction.FFMPEG_MUX,
        OperatorExecutionAction.EVIDENCE_FILE_MOVE,
        OperatorExecutionAction.ASR_EXECUTION_READINESS,
    ):
        decision = evaluate_operator_approval(
            action,
            token=approved,
            requested_scope=OperatorExecutionScope.LIVE_EXTERNAL,
        )
        assert decision.allowed_to_execute is True


if __name__ == "__main__":
    test_preview_and_missing_approval_block_execution()
    test_approved_local_temp_actions_are_allowed()
    test_external_archive_submit_subprocess_user_evidence_and_asr_need_specific_flags()
    print("source_operator_approval_gateway_test.py passed")
