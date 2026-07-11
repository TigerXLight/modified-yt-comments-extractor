from __future__ import annotations

import dataclasses
import re

from evidence_database_taxonomy import (
    EVIDENCE_DATABASE_TAXONOMY_SCOPE,
    AliasNormalizationSuggestion,
    ClassificationDimension,
    ClassificationStatus,
    DatabaseRootRegistration,
    DryRunItem,
    DryRunItemStatus,
    DryRunReport,
    EvidenceDatabaseItem,
    EvidenceDatabaseTaxonomy,
    ReclassificationChangeType,
    ReclassificationHistoryRecord,
    ReclassificationSuggestion,
    TaxonomyMappingEntry,
    UserReviewStatus,
)
from evidence_schema import PrimarySourceStatus, SourceRole


UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _enum_values(enum_type: type) -> tuple[str, ...]:
    return tuple(item.value for item in enum_type)


def run_self_test() -> None:
    assert _enum_values(ClassificationStatus) == (
        "UNKNOWN_OR_NOT_IDENTIFIED",
        "KNOWN",
        "PARTIALLY_KNOWN",
        "CONFLICTING",
        "NEEDS_REVIEW",
    )
    assert _enum_values(UserReviewStatus) == (
        "NOT_REVIEWED",
        "ACCEPTED",
        "REJECTED",
        "DEFERRED",
    )
    assert _enum_values(ReclassificationChangeType) == (
        "UNKNOWN_TO_KNOWN",
        "CATEGORY_PATH_CHANGE",
        "CLASSIFICATION_CORRECTION",
        "ALIAS_NORMALIZATION",
        "NO_CHANGE",
    )
    assert _enum_values(DryRunItemStatus) == (
        "NO_OP",
        "REVIEW_REQUIRED",
        "CONFLICT",
        "MISSING_METADATA",
        "UNKNOWN_OR_NOT_IDENTIFIED",
    )

    nonexistent_root = r"Z:\illustrative\database\does-not-exist"
    root = DatabaseRootRegistration(
        database_root=nonexistent_root,
        database_label="Research evidence",
        taxonomy_version="user-v1",
        default_date_bucket_format="YYYY-MM",
    )
    assert root.database_root == nonexistent_root
    assert root.dry_run_required is True
    assert root.unknown_label_policy == "unknown/not identified is valid"
    assert UTC_TIMESTAMP_RE.fullmatch(root.registered_at_utc)
    root_dict = root.to_dict()
    assert root_dict["database_root"] == nonexistent_root
    assert root_dict["dry_run_required"] is True

    mapping = TaxonomyMappingEntry(
        taxonomy_map_id="map-1",
        database_root=nonexistent_root,
        path_pattern="{topic}/{custom_user_bucket}/{month}/{title}",
        dimension_order=2,
        dimension_name="custom_user_bucket",
        dimension_value="Research Set A",
        required_review=True,
    )
    assert mapping.dimension_name == "custom_user_bucket"
    assert mapping.required_review is True

    unknown_religion = ClassificationDimension(
        dimension_name="religion_identity_status",
        dimension_value="not identified",
        is_sensitive=True,
        user_approval_required=True,
        sensitive_classification_warning=(
            "Do not infer religion from names, locations, photos, clothing, or stereotypes."
        ),
    )
    assert unknown_religion.classification_status is (
        ClassificationStatus.UNKNOWN_OR_NOT_IDENTIFIED
    )
    assert unknown_religion.unknown_or_not_identified_is_valid is True
    assert unknown_religion.weak_clue_inference_prohibited is True
    assert unknown_religion.explicit_source_evidence_present is False
    assert unknown_religion.user_confirmed is False
    assert unknown_religion.user_approval_required is True

    known_religion = ClassificationDimension(
        dimension_name="religion_identity_status",
        dimension_value="explicitly stated category",
        classification_status=ClassificationStatus.KNOWN,
        is_sensitive=True,
        explicit_source_evidence_present=True,
        user_confirmed=False,
        user_approval_required=True,
        classification_basis="A later source explicitly states the relevant identity.",
        classification_source_url="https://example.test/later-source",
        classification_source_role=SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE,
        classification_source_status=(
            PrimarySourceStatus.SECONDARY_FRAMING_ONLY
        ),
        sensitive_classification_warning="User approval remains required.",
    )
    known_dict = known_religion.to_dict()
    assert known_dict["classification_status"] == "KNOWN"
    assert known_dict["classification_source_role"] == (
        "SECONDARY_OUTSIDE_PERSPECTIVE"
    )
    assert known_dict["classification_source_status"] == (
        "SECONDARY_FRAMING_ONLY"
    )

    suggestion = ReclassificationSuggestion(
        suggestion_id="reclass-1",
        item_id="item-1",
        change_type=ReclassificationChangeType.UNKNOWN_TO_KNOWN,
        previous_category_path=(
            "Non-religious or not identified/2026-06/Outlet/Article"
        ),
        suggested_category_path="Explicit category/2026-06/Outlet/Article",
        evidence_basis="Later source explicitly records the classification.",
        classification_source_url="https://example.test/later-source",
        classification_source_role=SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE,
        classification_source_status=(
            PrimarySourceStatus.SECONDARY_FRAMING_ONLY
        ),
        sensitive_classification_warning="Sensitive classification review required.",
        conflicts=("Existing path records an unknown state.",),
    )
    assert suggestion.user_review_status is UserReviewStatus.NOT_REVIEWED
    assert suggestion.requires_explicit_user_approval is True
    assert suggestion.automatic_action_permitted is False
    assert UTC_TIMESTAMP_RE.fullmatch(suggestion.created_at_utc)
    suggestion_dict = suggestion.to_dict()
    assert suggestion_dict["change_type"] == "UNKNOWN_TO_KNOWN"
    assert suggestion_dict["conflicts"] == [
        "Existing path records an unknown state."
    ]

    for decision in (
        UserReviewStatus.ACCEPTED,
        UserReviewStatus.REJECTED,
        UserReviewStatus.DEFERRED,
    ):
        reviewed = dataclasses.replace(
            suggestion,
            suggestion_id=f"reclass-{decision.value.lower()}",
            user_review_status=decision,
            user_reviewed_at_utc="2026-07-12T12:00:00Z",
        )
        assert reviewed.user_review_status is decision
        assert reviewed.automatic_action_permitted is False

    alias = AliasNormalizationSuggestion(
        suggestion_id="alias-1",
        item_id="item-1",
        field_or_dimension_name="action_type",
        current_value="incitment",
        suggested_value="incitement",
        normalization_rule_id="spelling-1",
        reason="Spelling normalization suggestion.",
    )
    assert alias.requires_explicit_user_approval is True
    assert alias.automatic_action_permitted is False
    assert alias.user_review_status is UserReviewStatus.NOT_REVIEWED

    history = ReclassificationHistoryRecord(
        history_id="history-1",
        item_id="item-1",
        previous_category_path=(
            "Non-religious or not identified/2026-06/Outlet/Article"
        ),
        new_category_path="Explicit category/2026-06/Outlet/Article",
        suggested_category_path="Explicit category/2026-06/Outlet/Article",
        change_type=ReclassificationChangeType.UNKNOWN_TO_KNOWN,
        change_reason="Accepted after explicit user review.",
        classification_basis="Later source explicitly records the classification.",
        classification_source_url="https://example.test/later-source",
        classification_source_role=SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE,
        classification_source_status=(
            PrimarySourceStatus.SECONDARY_FRAMING_ONLY
        ),
        user_review_status=UserReviewStatus.ACCEPTED,
        user_reviewed_at_utc="2026-07-12T12:00:00Z",
        changed_at_utc="2026-07-12T12:01:00Z",
    )
    history_dict = history.to_dict()
    assert history_dict["previous_category_path"].startswith(
        "Non-religious or not identified/"
    )
    assert history_dict["new_category_path"].startswith("Explicit category/")
    assert history_dict["classification_source_role"] == (
        "SECONDARY_OUTSIDE_PERSPECTIVE"
    )
    assert history_dict["user_review_status"] == "ACCEPTED"

    item = EvidenceDatabaseItem(
        item_id="item-1",
        database_root=nonexistent_root,
        database_label="Research evidence",
        taxonomy_version="user-v1",
        category_path=(
            "Non-religious or not identified/2026-06/Outlet/Article"
        ),
        suggested_category_path="Explicit category/2026-06/Outlet/Article",
        previous_category_path=(
            "Non-religious or not identified/2026-06/Outlet/Article"
        ),
        classification_dimensions=(unknown_religion, known_religion),
        classification_status=ClassificationStatus.NEEDS_REVIEW,
        source_outlet="Example Outlet",
        article_or_export_title="Example Article",
        event_or_article_date="2026-06-20",
        month_bucket="2026-06",
        export_package_id="package-1",
        manifest_path=r"Z:\illustrative\package\manifest.json",
        source_urls=("https://example.test/article",),
        archive_urls=("https://archive.example.test/article",),
        local_evidence_paths=(r"Z:\illustrative\evidence\article.html",),
        queue_item_ids=("queue-1", "queue-2"),
        capture_session_ids=("capture-1",),
        history=(history,),
    )
    item_dict = item.to_dict()
    assert item_dict["classification_dimensions"][0][
        "classification_status"
    ] == "UNKNOWN_OR_NOT_IDENTIFIED"
    assert item_dict["source_urls"] == ["https://example.test/article"]
    assert item_dict["queue_item_ids"] == ["queue-1", "queue-2"]
    assert item_dict["capture_session_ids"] == ["capture-1"]
    assert item_dict["history"][0]["change_type"] == "UNKNOWN_TO_KNOWN"

    review_item = DryRunItem(
        item_id="item-1",
        status=DryRunItemStatus.REVIEW_REQUIRED,
        existing_path=item.category_path,
        parsed_dimensions=(unknown_religion,),
        suggested_destination_path=item.suggested_category_path,
        reason_for_suggestion="Possible unknown-to-known update.",
        evidence_basis=suggestion.evidence_basis,
        sensitive_classification_warning=(
            suggestion.sensitive_classification_warning
        ),
        conflicts=suggestion.conflicts,
        user_action_required=True,
        no_op=False,
        reclassification_suggestion_id=suggestion.suggestion_id,
        alias_suggestion_ids=(alias.suggestion_id,),
    )
    no_op_item = DryRunItem(
        item_id="item-2",
        status=DryRunItemStatus.NO_OP,
        existing_path="Topic/2026-06/Outlet/Unchanged",
        no_op=True,
        user_action_required=False,
    )
    unknown_item = DryRunItem(
        item_id="item-3",
        status=DryRunItemStatus.UNKNOWN_OR_NOT_IDENTIFIED,
        existing_path="Unknown/2026-06/Outlet/Article",
        unknown_or_not_identified_state="Valid unknown state; not an error.",
        user_action_required=False,
        no_op=True,
    )
    report = DryRunReport(
        report_id="dry-run-1",
        database_root=nonexistent_root,
        items=(review_item, no_op_item, unknown_item),
    )
    report_dict = report.to_dict()
    assert report.no_changes_applied is True
    assert report.requires_user_review is True
    assert report_dict["item_count"] == 3
    assert report_dict["items"][0]["status"] == "REVIEW_REQUIRED"
    assert report_dict["items"][1]["no_op"] is True
    assert report_dict["items"][2]["status"] == (
        "UNKNOWN_OR_NOT_IDENTIFIED"
    )
    assert "no folder scanning" in report.scope
    assert "no file movement" in report.scope

    taxonomy = EvidenceDatabaseTaxonomy(
        database_roots=(root,),
        taxonomy_mappings=(mapping,),
        items=(item,),
        reclassification_suggestions=(suggestion,),
        alias_normalization_suggestions=(alias,),
        history_records=(history,),
        dry_run_reports=(report,),
    )
    taxonomy_dict = taxonomy.to_dict()
    assert taxonomy_dict["database_root_count"] == 1
    assert taxonomy_dict["taxonomy_mapping_count"] == 1
    assert taxonomy_dict["item_count"] == 1
    assert taxonomy_dict["reclassification_suggestion_count"] == 1
    assert taxonomy_dict["alias_normalization_suggestion_count"] == 1
    assert taxonomy_dict["history_record_count"] == 1
    assert taxonomy_dict["dry_run_report_count"] == 1
    assert taxonomy_dict["dry_run_reports"][0]["no_changes_applied"] is True
    assert taxonomy_dict["scope"] == EVIDENCE_DATABASE_TAXONOMY_SCOPE

    assert root.database_root == nonexistent_root
    assert item.local_evidence_paths == (
        r"Z:\illustrative\evidence\article.html",
    )
    assert not hasattr(root, "scan")
    assert not hasattr(root, "index")
    assert not hasattr(item, "move")
    assert not hasattr(item, "rename")
    assert not hasattr(suggestion, "apply")
    assert not hasattr(alias, "apply")
    assert not hasattr(report, "execute")


if __name__ == "__main__":
    run_self_test()
    print("Evidence database taxonomy self-test passed.")
