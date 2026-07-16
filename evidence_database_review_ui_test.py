from pathlib import Path
from tempfile import TemporaryDirectory

from evidence_database_index import (
    EvidenceClassificationState,
    EvidenceClassificationValue,
    EvidenceIndexRecord,
    build_evidence_item_identity,
    build_placement_proposal,
)
from evidence_database_review import (
    EvidenceDatabasePreviewRequest,
    EvidenceDatabaseReviewDecisionType,
    build_apply_plan_from_decisions,
    build_empty_preview_result,
    build_preview_result_from_records,
    build_review_session,
    record_review_decision,
)
from evidence_database_review_ui import (
    EVIDENCE_DATABASE_REVIEW_DESTRUCTIVE_STATUS,
    EVIDENCE_DATABASE_REVIEW_DRY_RUN_WARNING,
    EVIDENCE_DATABASE_REVIEW_UI_SCHEMA_VERSION,
    EvidenceDatabaseReviewWindowController,
    build_review_window_controller_from_import_bundle,
    build_evidence_database_review_window_controller,
    build_evidence_database_review_window_state,
    build_evidence_database_review_window_text,
    build_synthetic_demo_review_window_controller,
    review_ui_stable_json_dumps,
    write_synthetic_demo_review_export_file,
)
from evidence_database_review_io import read_evidence_database_review_export_file


def _sample_record(
    *,
    display_name: str,
    classification_value: EvidenceClassificationValue,
) -> EvidenceIndexRecord:
    identity = build_evidence_item_identity(
        display_name=display_name,
        source_url=f"https://example.test/{display_name.replace(' ', '-').lower()}",
    )
    placement = build_placement_proposal(
        item_id=identity.item_id,
        database_root_id="root_a",
        current_path=f"inbox/{display_name}",
        proposed_path=f"reviewed/{display_name}",
    )
    return EvidenceIndexRecord(
        identity=identity,
        database_root_id="root_a",
        taxonomy_version_id="taxonomy_user_v1",
        classification_state=EvidenceClassificationState(
            classification_value=classification_value,
            user_confirmation_required=(
                classification_value is not EvidenceClassificationValue.USER_CONFIRMED
            ),
        ),
        placement_proposals=(placement,),
    )


def run_self_test() -> None:
    session = build_review_session(
        selected_root_id="root_a",
        taxonomy_version_id="taxonomy_user_v1",
        registered_root_ids=("root_a", "root_b"),
    )
    unknown_record = _sample_record(
        display_name="Unknown item",
        classification_value=EvidenceClassificationValue.UNKNOWN,
    )
    proposed_record = _sample_record(
        display_name="Proposed item",
        classification_value=EvidenceClassificationValue.PROPOSED,
    )
    preview = build_preview_result_from_records(
        EvidenceDatabasePreviewRequest(
            session_id=session.session_id,
            root_id=session.selected_root_id,
        ),
        (unknown_record, proposed_record),
        warnings=("explicit_records_only",),
    )
    decision = record_review_decision(
        decision_type=EvidenceDatabaseReviewDecisionType.ACCEPT_PROPOSAL,
        item_id=proposed_record.identity.item_id,
        proposal_id=proposed_record.placement_proposals[0].proposal_id,
        target_classification_value=EvidenceClassificationValue.PROPOSED,
        user_confirmed=True,
    )
    apply_plan = build_apply_plan_from_decisions(
        session_id=session.session_id,
        decisions=(decision,),
        records=(proposed_record,),
        warnings=("dry_run_plan_only",),
    )

    state = build_evidence_database_review_window_state(
        session=session,
        preview_result=preview,
        apply_plan=apply_plan,
        warnings=("ui_scaffold_only",),
    )
    assert state.schema_version == EVIDENCE_DATABASE_REVIEW_UI_SCHEMA_VERSION
    assert state.registered_root_count == 2
    assert state.preview_record_count == 2
    assert state.selected_decision_count == 1
    assert state.apply_plan_entry_count == 1
    assert state.dry_run_only is True
    assert state.supplied_records_only is True
    assert state.broad_scan_performed is False
    assert state.file_operation_performed is False
    assert state.classification_changes_executed is False
    assert state.destructive_actions_not_implemented is True
    assert state.dry_run_warning == EVIDENCE_DATABASE_REVIEW_DRY_RUN_WARNING
    assert state.destructive_action_status == EVIDENCE_DATABASE_REVIEW_DESTRUCTIVE_STATUS
    assert state.warnings == (
        "ui_scaffold_only",
        "explicit_records_only",
        "dry_run_plan_only",
    )

    state_dict = state.to_dict()
    assert state_dict["preview_group_counts"] == [
        {"classification_value": "unknown", "row_count": 1},
        {"classification_value": "not_evidenced", "row_count": 0},
        {"classification_value": "user_confirmed", "row_count": 0},
        {"classification_value": "proposed", "row_count": 1},
        {"classification_value": "rejected", "row_count": 0},
        {"classification_value": "superseded", "row_count": 0},
    ]
    assert state_dict["apply_plan_target_counts"] == [
        {"classification_value": "unknown", "row_count": 0},
        {"classification_value": "not_evidenced", "row_count": 0},
        {"classification_value": "user_confirmed", "row_count": 0},
        {"classification_value": "proposed", "row_count": 1},
        {"classification_value": "rejected", "row_count": 0},
        {"classification_value": "superseded", "row_count": 0},
    ]
    assert state_dict["dry_run_warning"].startswith("Evidence Database review is dry-run only")
    assert state_dict["broad_scan_performed"] is False
    assert state_dict["file_operation_performed"] is False
    assert state_dict["classification_changes_executed"] is False
    serialized_state = review_ui_stable_json_dumps(state_dict).lower()
    assert "api_key" not in serialized_state
    assert "secret" not in serialized_state

    text = build_evidence_database_review_window_text(state)
    assert text.startswith("Evidence Database review\n")
    assert "Warning: Evidence Database review is dry-run only." in text
    assert "Registered roots: 2" in text
    assert "- unknown: 1" in text
    assert "- proposed: 1" in text
    assert "Apply plan targets by state:" in text
    assert "- Broad scan performed: no" in text
    assert "- File operation performed: no" in text
    assert "- Classification changes executed: no" in text
    assert f"- Destructive actions: {EVIDENCE_DATABASE_REVIEW_DESTRUCTIVE_STATUS}" in text
    assert "ui_scaffold_only" in text
    assert "scan(" not in text
    assert "move(" not in text

    controller = build_evidence_database_review_window_controller(
        session=session,
        preview_result=preview,
        apply_plan=apply_plan,
    )
    assert isinstance(controller, EvidenceDatabaseReviewWindowController)
    assert controller.to_dict()["registered_root_count"] == 2
    assert controller.to_text() == build_evidence_database_review_window_text(controller.state)
    assert review_ui_stable_json_dumps(controller.to_dict()) == review_ui_stable_json_dumps(
        controller.to_dict()
    )

    demo_controller = build_synthetic_demo_review_window_controller()
    demo_dict = demo_controller.to_dict()
    assert demo_dict["registered_root_count"] == 1
    assert demo_dict["preview_record_count"] == 6
    assert demo_dict["apply_plan_entry_count"] == 3
    assert demo_dict["broad_scan_performed"] is False
    assert demo_dict["file_operation_performed"] is False
    assert demo_dict["classification_changes_executed"] is False
    assert "synthetic_fixture_only" in demo_dict["warnings"]
    assert "- user_confirmed: 1" in demo_controller.to_text()

    with TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "synthetic_demo_review.json"
        export_result = write_synthetic_demo_review_export_file(str(export_path))
        assert export_result.export_path == str(export_path)
        imported = read_evidence_database_review_export_file(str(export_path))
        assert imported.ok is True
        assert imported.bundle is not None
        imported_controller = build_review_window_controller_from_import_bundle(
            imported.bundle
        )
        imported_dict = imported_controller.to_dict()
        assert imported_dict["registered_root_count"] == 1
        assert imported_dict["preview_record_count"] == 6
        assert imported_dict["apply_plan_entry_count"] == 3
        assert imported_dict["broad_scan_performed"] is False
        assert imported_dict["file_operation_performed"] is False
        assert imported_dict["classification_changes_executed"] is False
        assert "imported_review_session" in imported_dict["warnings"]
        assert sorted(path.name for path in Path(temp_dir).iterdir()) == [
            "synthetic_demo_review.json"
        ]

    empty_session = build_review_session(
        selected_root_id="missing_root_metadata",
        taxonomy_version_id="taxonomy_user_v1",
        session_id="reviewsession_empty_fixture",
    )
    empty_preview_request = EvidenceDatabasePreviewRequest(
        session_id=empty_session.session_id,
        root_id=empty_session.selected_root_id,
        request_id="preview_empty_fixture",
    )
    empty_preview = build_empty_preview_result(empty_preview_request)
    empty_controller = build_evidence_database_review_window_controller(
        session=empty_session,
        preview_result=empty_preview,
    )
    empty_dict = empty_controller.to_dict()
    assert empty_dict["registered_root_count"] == 0
    assert empty_dict["selected_root_id"] == "missing_root_metadata"
    assert empty_dict["preview_record_count"] == 0
    assert empty_dict["dry_run_warning"].startswith("Evidence Database review is dry-run only")
    assert "Warning: Evidence Database review is dry-run only." in empty_controller.to_text()
    assert "- (none)" in empty_controller.to_text()

    duplicate_preview = build_preview_result_from_records(
        EvidenceDatabasePreviewRequest(
            session_id=session.session_id,
            root_id="root_1",
        ),
        (unknown_record, unknown_record),
    )
    duplicate_controller = build_evidence_database_review_window_controller(
        session=session,
        preview_result=duplicate_preview,
    )
    assert duplicate_controller.to_dict()["preview_record_count"] == 2
    duplicate_unknown_counts = [
        item
        for item in duplicate_controller.to_dict()["preview_group_counts"]
        if item["classification_value"] == "unknown"
    ]
    assert duplicate_unknown_counts == [{"classification_value": "unknown", "row_count": 2}]

    proposed_only_preview = build_preview_result_from_records(
        EvidenceDatabasePreviewRequest(
            session_id=session.session_id,
            root_id="root_1",
        ),
        (proposed_record,),
    )
    proposed_only_controller = build_evidence_database_review_window_controller(
        session=session,
        preview_result=proposed_only_preview,
    )
    assert proposed_only_controller.to_dict()["preview_group_counts"] == [
        {"classification_value": "unknown", "row_count": 0},
        {"classification_value": "not_evidenced", "row_count": 0},
        {"classification_value": "user_confirmed", "row_count": 0},
        {"classification_value": "proposed", "row_count": 1},
        {"classification_value": "rejected", "row_count": 0},
        {"classification_value": "superseded", "row_count": 0},
    ]

    rejected_record = _sample_record(
        display_name="Rejected item",
        classification_value=EvidenceClassificationValue.REJECTED,
    )
    superseded_record = _sample_record(
        display_name="Superseded item",
        classification_value=EvidenceClassificationValue.SUPERSEDED,
    )
    rejected_decision = record_review_decision(
        decision_type=EvidenceDatabaseReviewDecisionType.REJECT_PROPOSAL,
        item_id=rejected_record.identity.item_id,
        proposal_id=rejected_record.placement_proposals[0].proposal_id,
        target_classification_value=EvidenceClassificationValue.REJECTED,
        user_confirmed=True,
    )
    superseded_decision = record_review_decision(
        decision_type=EvidenceDatabaseReviewDecisionType.REQUEST_RECLASSIFICATION,
        item_id=superseded_record.identity.item_id,
        proposal_id=superseded_record.placement_proposals[0].proposal_id,
        target_classification_value=EvidenceClassificationValue.SUPERSEDED,
        user_confirmed=True,
    )
    rejected_superseded_plan = build_apply_plan_from_decisions(
        session_id=session.session_id,
        decisions=(rejected_decision, superseded_decision),
        records=(rejected_record, superseded_record),
    )
    rejected_superseded_controller = build_evidence_database_review_window_controller(
        session=session,
        preview_result=build_preview_result_from_records(
            EvidenceDatabasePreviewRequest(session_id=session.session_id, root_id="root_1"),
            (rejected_record, superseded_record),
        ),
        apply_plan=rejected_superseded_plan,
    )
    rejected_superseded_dict = rejected_superseded_controller.to_dict()
    assert rejected_superseded_dict["apply_plan_target_counts"] == [
        {"classification_value": "unknown", "row_count": 0},
        {"classification_value": "not_evidenced", "row_count": 0},
        {"classification_value": "user_confirmed", "row_count": 0},
        {"classification_value": "proposed", "row_count": 0},
        {"classification_value": "rejected", "row_count": 1},
        {"classification_value": "superseded", "row_count": 1},
    ]
    rejected_superseded_text = rejected_superseded_controller.to_text()
    assert "Apply plan targets by state:" in rejected_superseded_text
    assert "- rejected: 1" in rejected_superseded_text
    assert "- superseded: 1" in rejected_superseded_text


if __name__ == "__main__":
    run_self_test()
    print("Evidence database review UI self-test passed.")
