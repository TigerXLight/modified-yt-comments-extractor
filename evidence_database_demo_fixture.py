from __future__ import annotations

from dataclasses import dataclass

from evidence_database_index import (
    CLASSIFICATION_NOT_EVIDENCED,
    CLASSIFICATION_PROPOSED,
    CLASSIFICATION_REJECTED,
    CLASSIFICATION_SUPERSEDED,
    CLASSIFICATION_UNKNOWN,
    CLASSIFICATION_USER_CONFIRMED,
    EVIDENCE_DATABASE_INDEX_SCHEMA_VERSION,
    EvidenceClassificationValue,
    EvidenceDatabaseRoot,
    EvidenceIndexRecord,
    EvidenceItemIdentity,
    EvidencePathRecord,
    EvidenceTaxonomyVersion,
    build_classification_state,
    build_evidence_basis,
    build_placement_proposal,
    build_reclassification_proposal,
    stable_evidence_id,
)
from evidence_database_review import (
    EvidenceDatabaseApplyPlan,
    EvidenceDatabasePreviewRequest,
    EvidenceDatabasePreviewResult,
    EvidenceDatabaseReviewDecision,
    EvidenceDatabaseReviewDecisionType,
    EvidenceDatabaseReviewSession,
    build_apply_plan_from_decisions,
    build_preview_result_from_records,
    build_review_session,
    record_review_decision,
)


EVIDENCE_DATABASE_DEMO_FIXTURE_VERSION = "evidence-database-demo-fixture-v1"
EVIDENCE_DATABASE_DEMO_TIMESTAMP = "2026-07-16T00:00:00Z"
EVIDENCE_DATABASE_DEMO_ROOT_ID = "root_synthetic_demo"
EVIDENCE_DATABASE_DEMO_TAXONOMY_ID = "taxonomy_synthetic_demo_v1"
EVIDENCE_DATABASE_DEMO_SCOPE = (
    "synthetic evidence database demo fixture only; explicit records only; "
    "no filesystem scan, no file movement, no automatic classification, no "
    "sensitive-attribute inference, no network, no provider calls, no credentials"
)


@dataclass(frozen=True)
class EvidenceDatabaseDemoFixture:
    fixture_version: str
    root: EvidenceDatabaseRoot
    taxonomy_version: EvidenceTaxonomyVersion
    records: tuple[EvidenceIndexRecord, ...]
    session: EvidenceDatabaseReviewSession
    preview_request: EvidenceDatabasePreviewRequest
    preview_result: EvidenceDatabasePreviewResult
    decisions: tuple[EvidenceDatabaseReviewDecision, ...]
    apply_plan: EvidenceDatabaseApplyPlan
    scope: str = EVIDENCE_DATABASE_DEMO_SCOPE

    def classification_values(self) -> tuple[str, ...]:
        return tuple(record.classification_state.classification_value.value for record in self.records)


def _synthetic_item_identity(label: str) -> EvidenceItemIdentity:
    item_id = stable_evidence_id("demoitem", label)
    return EvidenceItemIdentity(
        item_id=item_id,
        display_name=f"Synthetic {label.replace('_', ' ').title()} Item",
        source_url=f"https://example.test/evidence-demo/{label}",
        local_path_hint=f"synthetic_fixture/evidence_demo/{label}.txt",
        created_at_utc=EVIDENCE_DATABASE_DEMO_TIMESTAMP,
    )


def _synthetic_record(
    *,
    label: str,
    classification_value: EvidenceClassificationValue,
    user_confirmed: bool = False,
    source_evidenced: bool = False,
) -> EvidenceIndexRecord:
    identity = _synthetic_item_identity(label)
    path_record = EvidencePathRecord(
        path_record_id=stable_evidence_id("demopath", identity.item_id),
        item_id=identity.item_id,
        current_path=f"synthetic_fixture/evidence_demo/inbox/{label}.txt",
        proposed_path=f"synthetic_fixture/evidence_demo/reviewed/{classification_value.value}/{label}.txt",
        path_role="synthetic_current",
        history_note="Synthetic demo path only; no file operation performed.",
        recorded_at_utc=EVIDENCE_DATABASE_DEMO_TIMESTAMP,
        file_operation_performed=False,
    )
    basis = build_evidence_basis(
        item_id=identity.item_id,
        basis_type="synthetic_demo_note",
        source_url=identity.source_url,
        evidence_text=f"Synthetic fixture note for {classification_value.value}.",
        user_note="Fixture data only.",
        confidence="demo_only",
        basis_id=stable_evidence_id("demobasis", identity.item_id),
    )
    placement = build_placement_proposal(
        item_id=identity.item_id,
        database_root_id=EVIDENCE_DATABASE_DEMO_ROOT_ID,
        current_path=path_record.current_path,
        proposed_path=path_record.proposed_path,
        basis_ids=(basis.basis_id,),
        reason="Synthetic dry-run placement example.",
        confidence="demo_only",
        proposal_id=stable_evidence_id("demoplace", identity.item_id),
    )
    reclassification = build_reclassification_proposal(
        item_id=identity.item_id,
        previous_path=path_record.current_path,
        proposed_path=path_record.proposed_path,
        previous_classification=build_classification_state(
            classification_value=EvidenceClassificationValue.UNKNOWN,
            notes="Synthetic previous state.",
        ),
        proposed_classification=build_classification_state(
            classification_value=classification_value,
            user_confirmed=user_confirmed,
            source_evidenced=source_evidenced,
            notes="Synthetic proposed state.",
        ),
        basis_ids=(basis.basis_id,),
        reason="Synthetic dry-run reclassification example.",
        proposal_id=stable_evidence_id("demoreclass", identity.item_id),
    )
    return EvidenceIndexRecord(
        identity=identity,
        database_root_id=EVIDENCE_DATABASE_DEMO_ROOT_ID,
        taxonomy_version_id=EVIDENCE_DATABASE_DEMO_TAXONOMY_ID,
        path_records=(path_record,),
        classification_state=build_classification_state(
            classification_value=classification_value,
            dimensions={
                "fixture_category": "synthetic",
                "review_state": classification_value.value,
            },
            user_confirmed=user_confirmed,
            source_evidenced=source_evidenced,
            notes="Synthetic fixture classification; no sensitive attributes.",
        ),
        evidence_basis=(basis,),
        placement_proposals=(placement,),
        reclassification_proposals=(reclassification,),
        created_at_utc=EVIDENCE_DATABASE_DEMO_TIMESTAMP,
        updated_at_utc=EVIDENCE_DATABASE_DEMO_TIMESTAMP,
    )


def build_synthetic_evidence_database_demo_fixture() -> EvidenceDatabaseDemoFixture:
    root = EvidenceDatabaseRoot(
        root_id=EVIDENCE_DATABASE_DEMO_ROOT_ID,
        root_path="synthetic_fixture/evidence_demo/root",
        label="Synthetic Evidence Demo Root",
        taxonomy_version_id=EVIDENCE_DATABASE_DEMO_TAXONOMY_ID,
        registered_at_utc=EVIDENCE_DATABASE_DEMO_TIMESTAMP,
        dry_run_required=True,
        moves_require_explicit_approval=True,
        broad_scan_allowed=False,
        notes="Synthetic fixture root only; not a real filesystem root.",
    )
    taxonomy = EvidenceTaxonomyVersion(
        taxonomy_version_id=EVIDENCE_DATABASE_DEMO_TAXONOMY_ID,
        label="Synthetic Evidence Demo Taxonomy",
        schema_version=EVIDENCE_DATABASE_INDEX_SCHEMA_VERSION,
        dimension_order=("fixture_category", "review_state"),
        sensitive_dimensions=(),
        created_at_utc=EVIDENCE_DATABASE_DEMO_TIMESTAMP,
        notes="Synthetic fixture taxonomy with no sensitive dimensions assigned.",
    )
    records = (
        _synthetic_record(
            label=CLASSIFICATION_UNKNOWN,
            classification_value=EvidenceClassificationValue.UNKNOWN,
        ),
        _synthetic_record(
            label=CLASSIFICATION_NOT_EVIDENCED,
            classification_value=EvidenceClassificationValue.NOT_EVIDENCED,
        ),
        _synthetic_record(
            label=CLASSIFICATION_PROPOSED,
            classification_value=EvidenceClassificationValue.PROPOSED,
            source_evidenced=True,
        ),
        _synthetic_record(
            label=CLASSIFICATION_USER_CONFIRMED,
            classification_value=EvidenceClassificationValue.USER_CONFIRMED,
            user_confirmed=True,
        ),
        _synthetic_record(
            label=CLASSIFICATION_REJECTED,
            classification_value=EvidenceClassificationValue.REJECTED,
        ),
        _synthetic_record(
            label=CLASSIFICATION_SUPERSEDED,
            classification_value=EvidenceClassificationValue.SUPERSEDED,
        ),
    )
    session = build_review_session(
        selected_root_id=root.root_id,
        taxonomy_version_id=taxonomy.taxonomy_version_id,
        registered_root_ids=(root.root_id,),
        session_id="reviewsession_synthetic_demo",
    )
    preview_request = EvidenceDatabasePreviewRequest(
        session_id=session.session_id,
        root_id=root.root_id,
        request_id="preview_synthetic_demo",
        created_at_utc=EVIDENCE_DATABASE_DEMO_TIMESTAMP,
    )
    preview_result = build_preview_result_from_records(
        preview_request,
        records,
        warnings=("synthetic_fixture_only",),
    )
    decisions = (
        record_review_decision(
            decision_type=EvidenceDatabaseReviewDecisionType.ACCEPT_PROPOSAL,
            item_id=records[2].identity.item_id,
            proposal_id=records[2].placement_proposals[0].proposal_id,
            target_classification_value=EvidenceClassificationValue.PROPOSED,
            note="Synthetic accepted proposal example.",
            user_confirmed=True,
            decision_id="decision_synthetic_accept_proposed",
        ),
        record_review_decision(
            decision_type=EvidenceDatabaseReviewDecisionType.MARK_NOT_EVIDENCED,
            item_id=records[1].identity.item_id,
            target_classification_value=EvidenceClassificationValue.NOT_EVIDENCED,
            note="Synthetic not-evidenced example.",
            user_confirmed=True,
            decision_id="decision_synthetic_not_evidenced",
        ),
        record_review_decision(
            decision_type=EvidenceDatabaseReviewDecisionType.REJECT_PROPOSAL,
            item_id=records[4].identity.item_id,
            proposal_id=records[4].placement_proposals[0].proposal_id,
            note="Synthetic rejected proposal example.",
            user_confirmed=False,
            decision_id="decision_synthetic_reject",
        ),
    )
    apply_plan = build_apply_plan_from_decisions(
        session_id=session.session_id,
        decisions=decisions,
        records=records,
        plan_id="applyplan_synthetic_demo",
        warnings=("synthetic_fixture_apply_plan_not_executed",),
    )
    return EvidenceDatabaseDemoFixture(
        fixture_version=EVIDENCE_DATABASE_DEMO_FIXTURE_VERSION,
        root=root,
        taxonomy_version=taxonomy,
        records=records,
        session=session,
        preview_request=preview_request,
        preview_result=preview_result,
        decisions=decisions,
        apply_plan=apply_plan,
    )
