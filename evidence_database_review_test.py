from evidence_database_index import (
    CLASSIFICATION_NOT_EVIDENCED,
    CLASSIFICATION_PROPOSED,
    CLASSIFICATION_REJECTED,
    CLASSIFICATION_SUPERSEDED,
    CLASSIFICATION_UNKNOWN,
    CLASSIFICATION_USER_CONFIRMED,
    EvidenceClassificationValue,
    build_evidence_item_identity,
)
from evidence_database_review import (
    APPLY_RESULT_STATUS_DRY_RUN,
    DECISION_ACCEPT_PROPOSAL,
    DECISION_MARK_NOT_EVIDENCED,
    EVIDENCE_DATABASE_REVIEW_SCOPE,
    ROOT_REGISTRATION_STATUS_DUPLICATE_ROOT,
    ROOT_REGISTRATION_STATUS_MISSING_ROOT,
    ROOT_REGISTRATION_STATUS_READY,
    EvidenceDatabaseApplyPlan,
    EvidenceDatabaseApplyResult,
    EvidenceDatabasePreviewRequest,
    EvidenceDatabasePreviewResult,
    EvidenceDatabaseRootRegistrationResult,
    EvidenceDatabaseReviewDecision,
    EvidenceDatabaseReviewDecisionType,
    EvidenceDatabaseReviewSession,
    EvidenceDatabaseRootRegistrationDraft,
    build_dry_run_apply_result,
    build_empty_preview_result,
    build_non_executing_apply_plan,
    build_review_session,
    review_stable_json_dumps,
    review_database_root_registration,
    review_session_with_registered_root,
)
from pathlib import Path
from tempfile import TemporaryDirectory


def _assert_timestamp(value: str) -> None:
    assert value.endswith("Z"), value
    assert "T" in value, value


def run_self_test() -> None:
    assert [item.value for item in EvidenceDatabaseReviewDecisionType] == [
        "accept_proposal",
        "reject_proposal",
        "mark_unknown",
        "mark_not_evidenced",
        "request_reclassification",
    ]
    assert DECISION_ACCEPT_PROPOSAL == "accept_proposal"
    assert DECISION_MARK_NOT_EVIDENCED == "mark_not_evidenced"

    draft = EvidenceDatabaseRootRegistrationDraft(
        root_path="T:/Evidence Database",
        label="Evidence Database",
        taxonomy_version_id="taxonomy_user_v1",
    )
    draft_dict = draft.to_dict()
    assert draft_dict["draft_id"].startswith("rootdraft_")
    assert draft.root_exists is False
    assert draft.user_supplied is True
    assert draft.broad_scan_allowed is False
    assert draft.dry_run_required is True
    assert draft.moves_require_explicit_approval is True
    assert "no broad folder scanning" in draft.scope
    _assert_timestamp(draft.created_at_utc)

    session = build_review_session(
        selected_root_id="root_1",
        taxonomy_version_id="taxonomy_user_v1",
        registered_root_ids=("root_1",),
    )
    assert isinstance(session, EvidenceDatabaseReviewSession)
    assert session.session_id == build_review_session(
        selected_root_id="root_1",
        taxonomy_version_id="taxonomy_user_v1",
        registered_root_ids=("root_1",),
    ).session_id
    assert session.dry_run_only is True
    assert session.user_confirmation_required is True
    assert session.destructive_actions_enabled is False
    assert session.broad_scan_allowed is False

    request = EvidenceDatabasePreviewRequest(
        session_id=session.session_id,
        root_id=session.selected_root_id,
        record_ids=("item_2", "item_1"),
    )
    request_dict = request.to_dict()
    assert request_dict["request_id"].startswith("preview_")
    assert request.supplied_records_only is True
    assert request.broad_scan_requested is False
    assert request.include_classification_values == (
        CLASSIFICATION_UNKNOWN,
        CLASSIFICATION_NOT_EVIDENCED,
        CLASSIFICATION_PROPOSED,
        CLASSIFICATION_USER_CONFIRMED,
        CLASSIFICATION_REJECTED,
        CLASSIFICATION_SUPERSEDED,
    )

    preview = build_empty_preview_result(request)
    assert isinstance(preview, EvidenceDatabasePreviewResult)
    assert preview.record_count == 0
    assert preview.supplied_records_only is True
    assert preview.broad_scan_performed is False
    assert preview.file_operation_performed is False
    assert preview.to_dict()["group_counts"] == {
        "not_evidenced": 0,
        "proposed": 0,
        "rejected": 0,
        "superseded": 0,
        "unknown": 0,
        "user_confirmed": 0,
    }

    identity = build_evidence_item_identity(
        display_name="Example",
        source_url="https://example.test/item",
    )
    decision = EvidenceDatabaseReviewDecision(
        decision_type=EvidenceDatabaseReviewDecisionType.ACCEPT_PROPOSAL,
        item_id=identity.item_id,
        proposal_id="proposal_1",
        target_classification_value=EvidenceClassificationValue.PROPOSED,
        note="Review note",
    )
    decision_dict = decision.to_dict()
    assert decision_dict["decision_id"].startswith("decision_")
    assert decision.user_confirmed is False
    assert decision.user_confirmation_required is True
    assert decision_dict["user_confirmation_required"] is True
    assert "Review note" in review_stable_json_dumps(decision_dict)

    confirmed_decision = EvidenceDatabaseReviewDecision(
        decision_type=EvidenceDatabaseReviewDecisionType.MARK_NOT_EVIDENCED,
        item_id=identity.item_id,
        target_classification_value=EvidenceClassificationValue.NOT_EVIDENCED,
        user_confirmed=True,
    )
    assert confirmed_decision.user_confirmation_required is False

    plan = build_non_executing_apply_plan(
        session_id=session.session_id,
        decisions=(decision, confirmed_decision),
    )
    assert isinstance(plan, EvidenceDatabaseApplyPlan)
    assert plan.dry_run is True
    assert plan.execute_file_moves is False
    assert plan.execute_classification_changes is False
    assert plan.file_operation_performed is False
    assert plan.destructive_action_not_implemented is True
    assert plan.user_confirmation_required is True
    assert plan.to_dict()["decisions"][0]["user_confirmation_required"] is True

    result = build_dry_run_apply_result(plan)
    assert isinstance(result, EvidenceDatabaseApplyResult)
    assert result.status == APPLY_RESULT_STATUS_DRY_RUN
    assert result.dry_run is True
    assert result.applied is False
    assert result.file_operations_performed is False
    assert result.classification_changes_executed is False
    assert result.destructive_action_not_implemented is True
    assert result.applied_decision_ids == (confirmed_decision.stable_decision_id,)
    assert result.warnings == (
        "dry_run_only_no_changes_executed",
        "file_movement_not_implemented",
    )

    rendered = review_stable_json_dumps(
        {
            "draft": draft.to_dict(),
            "preview": preview.to_dict(),
            "session": session.to_dict(),
        }
    )
    assert rendered == review_stable_json_dumps(
        {
            "draft": draft.to_dict(),
            "preview": preview.to_dict(),
            "session": session.to_dict(),
        }
    )
    assert EVIDENCE_DATABASE_REVIEW_SCOPE in rendered
    assert "requests" not in rendered
    assert "selenium" not in rendered
    assert "scan(" not in rendered
    assert "move(" not in rendered

    with TemporaryDirectory() as temp_dir:
        root_dir = Path(temp_dir) / "Evidence Root"
        root_dir.mkdir()
        valid_draft = EvidenceDatabaseRootRegistrationDraft(
            root_path=str(root_dir),
            label="Review root",
            taxonomy_version_id="taxonomy_user_v1",
            broad_scan_allowed=True,
        )
        registration = review_database_root_registration(valid_draft)
        assert isinstance(registration, EvidenceDatabaseRootRegistrationResult)
        assert registration.status == ROOT_REGISTRATION_STATUS_READY
        assert registration.ok is True
        assert registration.root is not None
        assert registration.root.root_path.endswith("Evidence Root")
        assert registration.root.dry_run_required is True
        assert registration.root.moves_require_explicit_approval is True
        assert registration.root.broad_scan_allowed is False
        assert registration.broad_scan_allowed is False
        assert registration.broad_scan_performed is False
        assert registration.file_operation_performed is False
        assert registration.warnings == ("broad_scan_disabled_for_review_controller",)
        assert registration.to_dict()["ok"] is True

        updated_session = review_session_with_registered_root(session, registration)
        assert updated_session.selected_root_id == registration.root_id
        assert updated_session.registered_root_ids == ("root_1", registration.root_id)
        assert updated_session.broad_scan_allowed is False
        assert updated_session.destructive_actions_enabled is False

        duplicate = review_database_root_registration(
            EvidenceDatabaseRootRegistrationDraft(
                root_path=str(root_dir).replace("\\", "/"),
                label="Duplicate",
            ),
            existing_roots=(registration.root,),
        )
        assert duplicate.status == ROOT_REGISTRATION_STATUS_DUPLICATE_ROOT
        assert duplicate.ok is False
        assert duplicate.duplicate_root_id == registration.root_id
        assert duplicate.errors == ("duplicate_database_root",)
        assert duplicate.broad_scan_performed is False

        missing = review_database_root_registration(
            EvidenceDatabaseRootRegistrationDraft(
                root_path=str(Path(temp_dir) / "missing"),
                label="Missing",
            )
        )
        assert missing.status == ROOT_REGISTRATION_STATUS_MISSING_ROOT
        assert missing.ok is False
        assert missing.root is None
        assert missing.errors == ("database_root_missing_or_not_directory",)
        assert missing.broad_scan_performed is False
        assert list(root_dir.iterdir()) == []


if __name__ == "__main__":
    run_self_test()
    print("Evidence database review self-test passed.")
