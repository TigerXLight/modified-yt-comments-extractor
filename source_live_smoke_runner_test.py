from __future__ import annotations

from source_live_smoke_runner import (
    LiveSmokeRunnerStatus,
    build_live_smoke_runner_plan_collection,
    evaluate_live_smoke_runner_plan,
    import_manual_live_smoke_result,
)
from source_operator_approval_gateway import (
    OperatorExecutionScope,
    build_operator_approval_token,
)


def test_live_smoke_runner_collection_covers_named_site_methods_without_execution() -> None:
    collection = build_live_smoke_runner_plan_collection(source_url="https://example.invalid/story")
    assert collection.plan_count == 11
    assert collection.to_dict()["approval_required_count"] == 11
    method_ids = {plan.method_id for plan in collection.plans}
    assert "msn_article" in method_ids
    assert "msn_shadow_dom_comments" in method_ids
    assert "twitter_x_public_post_archive_manual_import" in method_ids
    assert "twitter_x_reply_thread_archive_manual_import" in method_ids
    assert "youtube_media_transcript" in method_ids
    assert "youtube_comments" in method_ids
    assert "generic_article_html" in method_ids
    assert "generic_comments_site_specific_selector" in method_ids
    assert "archive_only_import" in method_ids
    assert all(plan.status == LiveSmokeRunnerStatus.DRY_RUN_PREVIEW for plan in collection.plans)
    assert all(plan.live_execution_performed is False for plan in collection.plans)
    assert all("--dry-run" in plan.dry_run_command_preview for plan in collection.plans)


def test_live_smoke_runner_blocks_without_live_approval_and_never_executes() -> None:
    plan = build_live_smoke_runner_plan_collection().plans[0]
    decision = evaluate_live_smoke_runner_plan(plan)
    assert decision.status == LiveSmokeRunnerStatus.APPROVAL_REQUIRED
    assert decision.command_executed is False
    assert decision.result_imported_to_workflow is False


def test_live_smoke_runner_can_be_approved_but_still_not_executed_by_helper() -> None:
    plan = next(
        item
        for item in build_live_smoke_runner_plan_collection().plans
        if item.method_id == "archive_only_import"
    )
    actions = tuple(decision.action for decision in evaluate_live_smoke_runner_plan(plan).approval_decisions)
    token = build_operator_approval_token(
        actions=actions,
        scope=OperatorExecutionScope.LIVE_EXTERNAL,
        approved_by_operator=True,
        allow_external_network=True,
    )
    decision = evaluate_live_smoke_runner_plan(plan, token=token)
    assert decision.status == LiveSmokeRunnerStatus.APPROVED_NOT_EXECUTED
    assert decision.command_executed is False


def test_live_smoke_runner_cancellation_and_result_import_are_metadata_only() -> None:
    plan = build_live_smoke_runner_plan_collection().plans[0]
    cancelled = evaluate_live_smoke_runner_plan(plan, cancel_requested=True)
    assert cancelled.status == LiveSmokeRunnerStatus.CANCELLED
    imported = import_manual_live_smoke_result(
        plan,
        operator_result_summary={
            "receipt_name": "manual_receipt.json",
            "artifact_count": 2,
            "operator_note_present": True,
        },
    )
    assert imported.status == LiveSmokeRunnerStatus.RESULT_IMPORTED
    assert imported.command_executed is False
    assert imported.imported_result_summary["raw_payload_included"] is False
    assert imported.imported_result_summary["completed_evidence_claimed"] is False


if __name__ == "__main__":
    test_live_smoke_runner_collection_covers_named_site_methods_without_execution()
    test_live_smoke_runner_blocks_without_live_approval_and_never_executes()
    test_live_smoke_runner_can_be_approved_but_still_not_executed_by_helper()
    test_live_smoke_runner_cancellation_and_result_import_are_metadata_only()
    print("source_live_smoke_runner_test.py passed")
