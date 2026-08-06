from evidence_item_queue import (
    ASRPairingMetadata,
    EvidenceItemLink,
    EvidenceItemQueue,
    EvidenceItemRole,
    EvidenceItemStatus,
    EvidenceLinkOrigin,
    EvidenceQueueItem,
    ManualMediaSourceChainDirection,
    ManualMediaSourceChainLink,
    ManualMediaSourceChainRelationKind,
    ManualPublisherFramingCorrectionKind,
    ManualPublisherFramingCorrectionNote,
    SourceRoleReviewMetadata,
    build_closed_loop_source_chain_review_summary,
    build_closed_loop_source_chain_review_summary_text,
    build_manual_media_source_chain_review_summary,
    build_manual_media_source_chain_review_summary_text,
    build_manual_media_source_chain_review_flow_summary,
    build_manual_media_source_chain_review_flow_summary_text,
    build_manual_publisher_framing_correction_review_summary,
    build_manual_publisher_framing_correction_review_flow_summary,
    build_manual_publisher_framing_correction_review_flow_summary_text,
    build_manual_publisher_framing_correction_review_summary_text,
    build_source_role_review_ui_summary,
    build_source_role_review_flow_summary,
    build_source_role_review_flow_summary_text,
    closed_loop_source_chain_review_summary_to_json,
    manual_media_source_chain_links_to_ui_rows,
    manual_media_source_chain_links_to_action_log_events,
    manual_media_source_chain_receipt_id,
    manual_media_source_chain_review_flow_summary_to_json,
    manual_media_source_chain_review_summary_to_json,
    manual_publisher_framing_correction_receipt_id,
    manual_publisher_framing_correction_review_flow_summary_to_json,
    manual_publisher_framing_correction_review_summary_to_json,
    manual_publisher_framing_corrections_to_action_log_events,
    manual_publisher_framing_corrections_to_ui_rows,
    queue_source_role_reviews_to_action_log_events,
    queue_source_role_reviews_to_claim_notes,
    queue_source_role_reviews_to_ui_rows,
    source_role_review_flow_summary_to_json,
    source_role_review_receipt_id,
)
from evidence_schema import CurrentnessStatus, PrimarySourceStatus, SourceRole
from capture_action_log import action_log_event_to_json
from total_export_manifest import TotalExportManifest


EXPECTED_ITEM_ROLES = [
    "SOURCE_URL",
    "LOCAL_MEDIA",
    "REFERENCE_TEXT",
    "SUBTITLE_FILE",
    "TRANSCRIPT_FILE",
    "SCREENSHOT",
    "HTML_SNAPSHOT",
    "VISIBLE_TEXT_SNAPSHOT",
    "ARCHIVE_URL",
    "MANUAL_EVIDENCE_NOTE",
    "ASR_RESULT",
    "TOTAL_EXPORT_PACKAGE",
    "DATABASE_CATEGORY_SUGGESTION",
]

EXPECTED_ITEM_STATUSES = [
    "ADDED",
    "LINKED",
    "READY",
    "NEEDS_REVIEW",
    "MISSING_LOCAL_FILE",
    "DUPLICATE_CANDIDATE",
    "EXCLUDED_FROM_EXPORT",
    "INCLUDED_IN_EXPORT",
    "REMOVED_FROM_WORKING_SET",
]


def _assert_utc_timestamp(value: str) -> None:
    assert value.endswith("Z"), value
    assert "T" in value, value


def run_self_test() -> None:
    assert [role.value for role in EvidenceItemRole] == EXPECTED_ITEM_ROLES
    assert [status.value for status in EvidenceItemStatus] == EXPECTED_ITEM_STATUSES
    assert [origin.value for origin in EvidenceLinkOrigin] == [
        "EXPLICIT",
        "DERIVED_FROM_APP_STATE",
    ]
    assert [kind.value for kind in ManualMediaSourceChainRelationKind] == [
        "SAME_MEDIA",
        "DERIVATIVE",
        "EXCERPT",
        "REPOST",
        "RELATED",
        "UNKNOWN",
        "OTHER",
    ]
    assert [direction.value for direction in ManualMediaSourceChainDirection] == [
        "SOURCE_TO_DERIVATIVE",
        "DERIVATIVE_TO_SOURCE",
        "RELATED_UNDIRECTED",
        "UNKNOWN",
    ]
    assert [kind.value for kind in ManualPublisherFramingCorrectionKind] == [
        "SOURCE_AUTHOR_CORRECTION",
        "DISPUTED_FRAMING",
        "PUBLISHER_CREDIT_NOTE",
        "COMPETING_CLAIM",
        "CONTEXT_CORRECTION",
        "UNKNOWN",
        "OTHER",
    ]

    source_url = EvidenceQueueItem(
        item_id="source-1",
        item_role=EvidenceItemRole.SOURCE_URL,
        display_name="Context page",
        source_url="https://example.test/context",
    )
    local_media = EvidenceQueueItem(
        item_id="media-1",
        item_role=EvidenceItemRole.LOCAL_MEDIA,
        display_name="Local reference clip",
        local_path=r"T:\Evidence\reference_clip.mp4",
        media_type="video",
        mime_type="video/mp4",
        is_manual_import=True,
    )
    reference_text = EvidenceQueueItem(
        item_id="reference-1",
        item_role=EvidenceItemRole.REFERENCE_TEXT,
        local_path=r"T:\Evidence\reference.txt",
    )
    subtitle = EvidenceQueueItem(
        item_id="subtitle-1",
        item_role=EvidenceItemRole.SUBTITLE_FILE,
        local_path=r"T:\Evidence\candidate.srt",
    )
    transcript = EvidenceQueueItem(
        item_id="transcript-1",
        item_role=EvidenceItemRole.TRANSCRIPT_FILE,
        local_path=r"T:\Evidence\candidate.txt",
    )
    asr_result = EvidenceQueueItem(
        item_id="asr-result-1",
        item_role=EvidenceItemRole.ASR_RESULT,
        asr_engine_or_provider="whisper.cpp large-v3-turbo",
        asr_result_path=r"T:\Evidence\result.json",
    )

    assert source_url.item_role != local_media.item_role
    assert reference_text.item_role != transcript.item_role
    assert subtitle.item_role != transcript.item_role
    assert asr_result.item_role not in {
        subtitle.item_role,
        transcript.item_role,
    }
    assert local_media.total_export_include is False
    assert local_media.item_status is EvidenceItemStatus.ADDED
    _assert_utc_timestamp(local_media.created_at_utc)
    _assert_utc_timestamp(local_media.updated_at_utc)

    second_default_item = EvidenceQueueItem(
        item_id="media-2",
        item_role=EvidenceItemRole.LOCAL_MEDIA,
    )
    assert local_media.linked_item_ids == ()
    assert second_default_item.linked_item_ids == ()
    try:
        local_media.linked_item_ids.append("not-allowed")  # type: ignore[attr-defined]
    except AttributeError:
        pass
    else:
        raise AssertionError("linked_item_ids must remain immutable")
    assert local_media.to_dict()["linked_item_ids"] == []

    included = EvidenceQueueItem(
        item_id="included-1",
        item_role=EvidenceItemRole.SCREENSHOT,
        local_path=r"T:\Evidence\page.png",
        total_export_include=True,
        total_export_output_kind="screenshot",
        total_export_output_path="page_capture/page.png",
        item_status=EvidenceItemStatus.INCLUDED_IN_EXPORT,
    )
    included_dict = included.to_dict()
    assert included_dict["total_export_include"] is True
    assert included_dict["total_export_output_kind"] == "screenshot"
    assert included_dict["total_export_output_path"] == "page_capture/page.png"
    assert included_dict["item_status"] == "INCLUDED_IN_EXPORT"

    excluded = EvidenceQueueItem(
        item_id="excluded-1",
        item_role=EvidenceItemRole.MANUAL_EVIDENCE_NOTE,
        total_export_include=False,
        total_export_exclusion_reason="Working note only.",
        item_status=EvidenceItemStatus.EXCLUDED_FROM_EXPORT,
    )
    excluded_dict = excluded.to_dict()
    assert excluded_dict["total_export_include"] is False
    assert excluded_dict["total_export_exclusion_reason"] == "Working note only."
    assert excluded_dict["item_status"] == "EXCLUDED_FROM_EXPORT"

    explicit_link = EvidenceItemLink(
        source_item_id="media-1",
        target_item_id="reference-1",
        relationship="evaluated_against",
        link_origin=EvidenceLinkOrigin.EXPLICIT,
        notes="User-selected reference pairing.",
    )
    assert explicit_link.to_dict() == {
        "source_item_id": "media-1",
        "target_item_id": "reference-1",
        "relationship": "evaluated_against",
        "link_origin": "EXPLICIT",
        "notes": "User-selected reference pairing.",
    }

    derived_link = EvidenceItemLink(
        source_item_id="subtitle-1",
        target_item_id="asr-result-1",
        relationship="produced_by",
        link_origin=EvidenceLinkOrigin.DERIVED_FROM_APP_STATE,
    )
    assert derived_link.to_dict()["link_origin"] == "DERIVED_FROM_APP_STATE"

    local_only_pairing = ASRPairingMetadata(
        media_item_id="media-1",
        reference_text_item_id="reference-1",
        candidate_subtitle_or_transcript_item_id="transcript-1",
        asr_result_item_id="asr-result-1",
        asr_engine_or_provider="whisper.cpp large-v3-turbo",
        scoring_window="00:00-00:30",
        reference_accuracy_percent=74.19,
        reference_score_path=r"T:\Evidence\score.json",
        term_coverage_path=r"T:\Evidence\term_coverage.json",
    )
    local_only_pairing_dict = local_only_pairing.to_dict()
    assert "source_url" not in local_only_pairing_dict
    assert local_only_pairing_dict["media_item_id"] == "media-1"
    assert local_only_pairing_dict["reference_accuracy_percent"] == 74.19

    incomplete_pairing = ASRPairingMetadata(
        media_item_id="media-2",
        notes="Reference and candidate are not linked yet.",
    )
    incomplete_pairing_dict = incomplete_pairing.to_dict()
    assert incomplete_pairing_dict["reference_text_item_id"] == ""
    assert incomplete_pairing_dict[
        "candidate_subtitle_or_transcript_item_id"
    ] == ""
    assert incomplete_pairing_dict["reference_accuracy_percent"] is None

    manual_same_media_link = ManualMediaSourceChainLink(
        source_item_id="media-1",
        target_item_id="media-2",
        relation_kind=ManualMediaSourceChainRelationKind.SAME_MEDIA,
        direction=ManualMediaSourceChainDirection.RELATED_UNDIRECTED,
        operator_note_category="manual_visual_review",
        operator_note_recorded=True,
        created_at_utc="2026-08-06T12:00:00Z",
    )
    manual_derivative_link = ManualMediaSourceChainLink(
        source_item_id="source-1",
        target_item_id="media-1",
        relation_kind=ManualMediaSourceChainRelationKind.DERIVATIVE,
        direction=ManualMediaSourceChainDirection.SOURCE_TO_DERIVATIVE,
        operator_note_category="publisher_credit",
        operator_note_recorded=True,
        created_at_utc="2026-08-06T12:01:00Z",
    )
    manual_repost_link = ManualMediaSourceChainLink(
        source_item_id="media-2",
        target_item_id="source-1",
        relation_kind=ManualMediaSourceChainRelationKind.REPOST,
        direction=ManualMediaSourceChainDirection.DERIVATIVE_TO_SOURCE,
        created_at_utc="2026-08-06T12:02:00Z",
    )
    manual_unknown_link = ManualMediaSourceChainLink(
        source_item_id="media-3",
        target_item_id="media-4",
        relation_kind=ManualMediaSourceChainRelationKind.OTHER,
        direction=ManualMediaSourceChainDirection.UNKNOWN,
        created_at_utc="2026-08-06T12:03:00Z",
    )
    publisher_credit_correction = ManualPublisherFramingCorrectionNote(
        queue_item_id="source-1",
        related_item_id="media-1",
        correction_kind=ManualPublisherFramingCorrectionKind.SOURCE_AUTHOR_CORRECTION,
        source_author_name_recorded=True,
        source_author_url_recorded=True,
        correction_text_recorded=True,
        correction_source_url_recorded=True,
        note_category="publisher_credit_correction",
        created_at_utc="2026-08-06T12:04:00Z",
    )
    disputed_framing_correction = ManualPublisherFramingCorrectionNote(
        queue_item_id="media-2",
        related_item_id="source-1",
        correction_kind=ManualPublisherFramingCorrectionKind.DISPUTED_FRAMING,
        disputed_framing_recorded=True,
        competing_claim_recorded=True,
        note_category="manual_disputed_context",
        created_at_utc="2026-08-06T12:05:00Z",
    )
    same_media_link_dict = manual_same_media_link.to_dict()
    assert same_media_link_dict["manual_link_id"].startswith(
        "manual_media_source_chain_link_"
    )
    assert same_media_link_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert same_media_link_dict["provenance"] == "MANUAL_OPERATOR_SUPPLIED"
    assert same_media_link_dict["automated_matching"] is False
    assert same_media_link_dict["fingerprint_matching"] is False
    assert same_media_link_dict["automatic_duplicate_detection"] is False
    assert same_media_link_dict["automatic_classification"] is False
    assert same_media_link_dict["sensitive_inference_prohibited"] is True
    assert same_media_link_dict["raw_media_payload_included"] is False
    assert same_media_link_dict["raw_evidence_payload_included"] is False
    assert same_media_link_dict["full_local_path_included"] is False
    assert same_media_link_dict["completed_evidence_claimed"] is False
    assert manual_same_media_link.to_dict() == same_media_link_dict
    publisher_credit_correction_dict = publisher_credit_correction.to_dict()
    assert publisher_credit_correction_dict["correction_note_id"].startswith(
        "manual_publisher_framing_correction_"
    )
    assert publisher_credit_correction_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert publisher_credit_correction_dict["provenance"] == "MANUAL_OPERATOR_SUPPLIED"
    assert publisher_credit_correction_dict["metadata_only"] is True
    assert publisher_credit_correction_dict["automated_source_author_detection"] is False
    assert publisher_credit_correction_dict["automated_matching"] is False
    assert publisher_credit_correction_dict["fingerprint_matching"] is False
    assert publisher_credit_correction_dict["automatic_duplicate_detection"] is False
    assert publisher_credit_correction_dict["automatic_classification"] is False
    assert publisher_credit_correction_dict["sensitive_inference_prohibited"] is True
    assert publisher_credit_correction_dict["raw_correction_payload_included"] is False
    assert publisher_credit_correction_dict["raw_media_payload_included"] is False
    assert publisher_credit_correction_dict["raw_evidence_payload_included"] is False
    assert publisher_credit_correction_dict["full_local_path_included"] is False
    assert publisher_credit_correction_dict["completed_evidence_claimed"] is False

    nonexistent_removed = EvidenceQueueItem(
        item_id="removed-1",
        item_role=EvidenceItemRole.LOCAL_MEDIA,
        local_path=r"Z:\path\that\does\not\exist\removed.mp4",
        item_status=EvidenceItemStatus.REMOVED_FROM_WORKING_SET,
        user_notes="Removed from the workspace only; original-file state is unknown.",
    )
    nonexistent_removed_dict = nonexistent_removed.to_dict()
    assert nonexistent_removed_dict["local_path"].endswith("removed.mp4")
    assert nonexistent_removed_dict["item_status"] == "REMOVED_FROM_WORKING_SET"

    source_role_review = SourceRoleReviewMetadata(
        claim_text="RAW EVIDENCE PAYLOAD SHOULD NOT APPEAR IN UI SUMMARY.",
        claim_type="authored_statement",
        claim_source_role=SourceRole.PRIMARY_ORIGINAL_AUTHORED,
        source_role_scope="Only the quoted authored statement.",
        source_role_limitation="Does not verify unrelated claims.",
        authored_or_posted_at="2026-08-06T10:00:00Z",
        captured_at_utc="2026-08-06T10:05:00Z",
        temporal_gap_note="Captured five minutes after posting.",
        currentness_status=CurrentnessStatus.CURRENT,
        primary_source_status=PrimarySourceStatus.PRIMARY_SOURCE_LOCATED,
        evidence_basis="Manual review of explicitly supplied source text.",
        reviewer_notes="USER_REVIEW_REQUIRED before export acceptance.",
    )
    tertiary_review = SourceRoleReviewMetadata(
        claim_text="ANOTHER RAW CLAIM PAYLOAD SHOULD STAY HIDDEN.",
        claim_type="propagated_claim",
        claim_source_role=SourceRole.TERTIARY_PROPAGATED_SOURCE,
        source_role_scope="Only a repeated unattributed claim.",
        source_role_limitation="Not a primary source.",
        currentness_status=CurrentnessStatus.UNKNOWN,
        primary_source_status=PrimarySourceStatus.TERTIARY_PROPAGATED_CLAIM,
        source_chain_gap=True,
        closed_loop_reporting_flag=True,
        evidence_basis="Manual source-role note.",
    )
    source_review_item = EvidenceQueueItem(
        item_id="source-review-1",
        item_role=EvidenceItemRole.SOURCE_URL,
        source_url="https://example.test/source",
        local_path=r"T:\Evidence\do-not-display-this-full-path.txt",
        item_status=EvidenceItemStatus.NEEDS_REVIEW,
        source_role_reviews=(source_role_review,),
    )
    second_review_item = EvidenceQueueItem(
        item_id="source-review-2",
        item_role=EvidenceItemRole.MANUAL_EVIDENCE_NOTE,
        item_status=EvidenceItemStatus.NEEDS_REVIEW,
        source_role_reviews=(tertiary_review,),
    )
    review_dict = source_review_item.to_dict()["source_role_reviews"][0]
    assert review_dict["claim_source_role"] == "PRIMARY_ORIGINAL_AUTHORED"
    assert review_dict["currentness_status"] == "CURRENT"
    assert review_dict["primary_source_status"] == "PRIMARY_SOURCE_LOCATED"
    assert review_dict["review_required"] is True
    assert review_dict["user_confirmed"] is False
    assert review_dict["automatic_classification"] is False
    assert review_dict["sensitive_inference_prohibited"] is True

    queue = EvidenceItemQueue(
        items=(
            source_url,
            local_media,
            reference_text,
            subtitle,
            transcript,
            asr_result,
            included,
            excluded,
            nonexistent_removed,
            source_review_item,
            second_review_item,
        ),
        links=(explicit_link, derived_link),
        asr_pairings=(local_only_pairing, incomplete_pairing),
        manual_media_source_chain_links=(
            manual_unknown_link,
            manual_repost_link,
            manual_same_media_link,
            manual_derivative_link,
        ),
        manual_publisher_framing_corrections=(
            disputed_framing_correction,
            publisher_credit_correction,
        ),
    )
    queue_dict = queue.to_dict()
    assert len(queue_dict["items"]) == 11
    assert queue_dict["items"][0]["item_role"] == "SOURCE_URL"
    assert queue_dict["links"][1]["link_origin"] == "DERIVED_FROM_APP_STATE"
    assert queue_dict["asr_pairings"][0]["reference_accuracy_percent"] == 74.19
    assert queue_dict["asr_pairings"][1]["reference_accuracy_percent"] is None
    assert len(queue_dict["manual_media_source_chain_links"]) == 4
    assert queue_dict["manual_media_source_chain_links"][0]["relation_kind"] == "OTHER"
    assert queue_dict["manual_media_source_chain_links"][0][
        "manual_link_id"
    ].startswith("manual_media_source_chain_link_")
    assert len(queue_dict["manual_publisher_framing_corrections"]) == 2
    assert queue_dict["manual_publisher_framing_corrections"][0][
        "correction_kind"
    ] == "DISPUTED_FRAMING"
    assert queue_dict["manual_publisher_framing_corrections"][0][
        "correction_note_id"
    ].startswith("manual_publisher_framing_correction_")

    media_source_chain_rows = manual_media_source_chain_links_to_ui_rows(queue)
    repeated_media_source_chain_rows = manual_media_source_chain_links_to_ui_rows(queue)
    assert [row.to_dict() for row in media_source_chain_rows] == [
        row.to_dict() for row in repeated_media_source_chain_rows
    ]
    assert [row.source_item_id for row in media_source_chain_rows] == [
        "media-1",
        "media-2",
        "media-3",
        "source-1",
    ]
    assert [row.target_item_id for row in media_source_chain_rows] == [
        "media-2",
        "source-1",
        "media-4",
        "media-1",
    ]
    assert [row.relation_kind.value for row in media_source_chain_rows] == [
        "SAME_MEDIA",
        "REPOST",
        "OTHER",
        "DERIVATIVE",
    ]
    assert [row.direction.value for row in media_source_chain_rows] == [
        "RELATED_UNDIRECTED",
        "DERIVATIVE_TO_SOURCE",
        "UNKNOWN",
        "SOURCE_TO_DERIVATIVE",
    ]
    first_media_source_chain_row = media_source_chain_rows[0].to_dict()
    assert first_media_source_chain_row["review_status"] == "USER_REVIEW_REQUIRED"
    assert first_media_source_chain_row["provenance"] == "MANUAL_OPERATOR_SUPPLIED"
    assert first_media_source_chain_row["operator_note_recorded"] is True
    assert first_media_source_chain_row["automated_matching"] is False
    assert first_media_source_chain_row["fingerprint_matching"] is False
    assert first_media_source_chain_row["automatic_duplicate_detection"] is False
    assert first_media_source_chain_row["automatic_classification"] is False
    assert first_media_source_chain_row["sensitive_inference_prohibited"] is True
    assert first_media_source_chain_row["raw_media_payload_included"] is False
    assert first_media_source_chain_row["raw_evidence_payload_included"] is False
    assert first_media_source_chain_row["full_local_path_included"] is False
    assert first_media_source_chain_row["completed_evidence_claimed"] is False
    assert first_media_source_chain_row["verified_evidence_claimed"] is False
    assert first_media_source_chain_row["live_capture_claimed"] is False
    assert first_media_source_chain_row["api_provider_capture_claimed"] is False
    assert first_media_source_chain_row["browser_automation_claimed"] is False
    assert first_media_source_chain_row["archive_download_ocr_warc_wacz_claimed"] is False

    media_source_chain_summary = build_manual_media_source_chain_review_summary(queue)
    repeated_media_source_chain_summary = build_manual_media_source_chain_review_summary(
        queue
    )
    assert (
        media_source_chain_summary.to_dict()
        == repeated_media_source_chain_summary.to_dict()
    )
    media_source_chain_summary_dict = media_source_chain_summary.to_dict()
    assert media_source_chain_summary_dict["summary_id"].startswith(
        "manual_media_source_chain_review_"
    )
    assert media_source_chain_summary_dict["status"] == "USER_REVIEW_REQUIRED"
    assert media_source_chain_summary_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert media_source_chain_summary_dict["metadata_only"] is True
    assert media_source_chain_summary_dict["manual_operator_supplied"] is True
    assert media_source_chain_summary_dict["user_review_required"] is True
    assert media_source_chain_summary_dict["manual_link_count"] == 4
    assert media_source_chain_summary_dict["operator_note_count"] == 2
    assert media_source_chain_summary_dict["source_item_ids"] == [
        "media-1",
        "media-2",
        "media-3",
        "source-1",
    ]
    assert media_source_chain_summary_dict["target_item_ids"] == [
        "media-2",
        "source-1",
        "media-4",
        "media-1",
    ]
    assert media_source_chain_summary_dict["relation_kinds"] == [
        "SAME_MEDIA",
        "REPOST",
        "OTHER",
        "DERIVATIVE",
    ]
    assert media_source_chain_summary_dict["directions"] == [
        "RELATED_UNDIRECTED",
        "DERIVATIVE_TO_SOURCE",
        "UNKNOWN",
        "SOURCE_TO_DERIVATIVE",
    ]
    assert media_source_chain_summary_dict["automated_matching"] is False
    assert media_source_chain_summary_dict["fingerprint_matching"] is False
    assert media_source_chain_summary_dict["automatic_duplicate_detection"] is False
    assert media_source_chain_summary_dict["automatic_classification"] is False
    assert media_source_chain_summary_dict["sensitive_inference_prohibited"] is True
    assert media_source_chain_summary_dict["raw_media_payload_included"] is False
    assert media_source_chain_summary_dict["raw_evidence_payload_included"] is False
    assert media_source_chain_summary_dict["full_local_path_included"] is False
    assert media_source_chain_summary_dict["completed_evidence_claimed"] is False
    rendered_media_source_chain_summary = (
        manual_media_source_chain_review_summary_to_json(media_source_chain_summary)
    )
    rendered_media_source_chain_text = (
        build_manual_media_source_chain_review_summary_text(
            media_source_chain_summary
        )
    )
    assert "Manual media source-chain review summary" in rendered_media_source_chain_text
    assert "Manual links: 4" in rendered_media_source_chain_text
    assert "Operator-note records: 2" in rendered_media_source_chain_text
    assert "Metadata only: yes" in rendered_media_source_chain_text
    assert "Manual/operator supplied: yes" in rendered_media_source_chain_text
    for unsafe_text in (
        "RAW MEDIA PAYLOAD",
        "RAW EVIDENCE PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic match",
        "fingerprint match",
        "duplicate detected",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_media_source_chain_summary
        assert unsafe_text not in rendered_media_source_chain_text

    publisher_framing_rows = manual_publisher_framing_corrections_to_ui_rows(queue)
    repeated_publisher_framing_rows = manual_publisher_framing_corrections_to_ui_rows(
        queue
    )
    assert [row.to_dict() for row in publisher_framing_rows] == [
        row.to_dict() for row in repeated_publisher_framing_rows
    ]
    assert [row.queue_item_id for row in publisher_framing_rows] == [
        "media-2",
        "source-1",
    ]
    assert [row.related_item_id for row in publisher_framing_rows] == [
        "source-1",
        "media-1",
    ]
    assert [row.correction_kind.value for row in publisher_framing_rows] == [
        "DISPUTED_FRAMING",
        "SOURCE_AUTHOR_CORRECTION",
    ]
    first_publisher_framing_row = publisher_framing_rows[0].to_dict()
    assert first_publisher_framing_row["review_status"] == "USER_REVIEW_REQUIRED"
    assert first_publisher_framing_row["provenance"] == "MANUAL_OPERATOR_SUPPLIED"
    assert first_publisher_framing_row["metadata_only"] is True
    assert first_publisher_framing_row["disputed_framing_recorded"] is True
    assert first_publisher_framing_row["competing_claim_recorded"] is True
    assert first_publisher_framing_row["automated_source_author_detection"] is False
    assert first_publisher_framing_row["automated_matching"] is False
    assert first_publisher_framing_row["fingerprint_matching"] is False
    assert first_publisher_framing_row["automatic_duplicate_detection"] is False
    assert first_publisher_framing_row["automatic_classification"] is False
    assert first_publisher_framing_row["sensitive_inference_prohibited"] is True
    assert first_publisher_framing_row["raw_correction_payload_included"] is False
    assert first_publisher_framing_row["raw_media_payload_included"] is False
    assert first_publisher_framing_row["raw_evidence_payload_included"] is False
    assert first_publisher_framing_row["full_local_path_included"] is False
    assert first_publisher_framing_row["completed_evidence_claimed"] is False
    assert first_publisher_framing_row["verified_evidence_claimed"] is False
    assert first_publisher_framing_row["live_capture_claimed"] is False
    assert first_publisher_framing_row["api_provider_capture_claimed"] is False
    assert first_publisher_framing_row["browser_automation_claimed"] is False
    assert (
        first_publisher_framing_row["archive_download_ocr_warc_wacz_claimed"]
        is False
    )

    publisher_framing_summary = (
        build_manual_publisher_framing_correction_review_summary(queue)
    )
    repeated_publisher_framing_summary = (
        build_manual_publisher_framing_correction_review_summary(queue)
    )
    assert (
        publisher_framing_summary.to_dict()
        == repeated_publisher_framing_summary.to_dict()
    )
    publisher_framing_summary_dict = publisher_framing_summary.to_dict()
    assert publisher_framing_summary_dict["summary_id"].startswith(
        "manual_publisher_framing_review_"
    )
    assert publisher_framing_summary_dict["status"] == "USER_REVIEW_REQUIRED"
    assert publisher_framing_summary_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert publisher_framing_summary_dict["metadata_only"] is True
    assert publisher_framing_summary_dict["manual_operator_supplied"] is True
    assert publisher_framing_summary_dict["user_review_required"] is True
    assert publisher_framing_summary_dict["correction_note_count"] == 2
    assert publisher_framing_summary_dict["queue_item_ids"] == ["media-2", "source-1"]
    assert publisher_framing_summary_dict["related_item_ids"] == [
        "source-1",
        "media-1",
    ]
    assert publisher_framing_summary_dict["correction_kinds"] == [
        "DISPUTED_FRAMING",
        "SOURCE_AUTHOR_CORRECTION",
    ]
    assert publisher_framing_summary_dict["source_author_name_recorded_count"] == 1
    assert publisher_framing_summary_dict["source_author_url_recorded_count"] == 1
    assert publisher_framing_summary_dict["correction_text_recorded_count"] == 1
    assert publisher_framing_summary_dict["correction_source_url_recorded_count"] == 1
    assert publisher_framing_summary_dict["disputed_framing_recorded_count"] == 1
    assert publisher_framing_summary_dict["competing_claim_recorded_count"] == 1
    assert (
        publisher_framing_summary_dict["automated_source_author_detection"] is False
    )
    assert publisher_framing_summary_dict["automated_matching"] is False
    assert publisher_framing_summary_dict["fingerprint_matching"] is False
    assert publisher_framing_summary_dict["automatic_duplicate_detection"] is False
    assert publisher_framing_summary_dict["automatic_classification"] is False
    assert publisher_framing_summary_dict["sensitive_inference_prohibited"] is True
    assert publisher_framing_summary_dict["raw_correction_payload_included"] is False
    assert publisher_framing_summary_dict["raw_media_payload_included"] is False
    assert publisher_framing_summary_dict["raw_evidence_payload_included"] is False
    assert publisher_framing_summary_dict["full_local_path_included"] is False
    assert publisher_framing_summary_dict["completed_evidence_claimed"] is False
    assert publisher_framing_summary_dict["verified_evidence_claimed"] is False
    rendered_publisher_framing_summary = (
        manual_publisher_framing_correction_review_summary_to_json(
            publisher_framing_summary
        )
    )
    rendered_publisher_framing_text = (
        build_manual_publisher_framing_correction_review_summary_text(
            publisher_framing_summary
        )
    )
    assert (
        "Manual publisher framing/source-author correction review summary"
        in rendered_publisher_framing_text
    )
    assert "Correction notes: 2" in rendered_publisher_framing_text
    assert "Source-author names recorded: 1" in rendered_publisher_framing_text
    assert "Metadata only: yes" in rendered_publisher_framing_text
    assert "Manual/operator supplied: yes" in rendered_publisher_framing_text
    for unsafe_text in (
        "RAW CORRECTION PAYLOAD",
        "RAW MEDIA PAYLOAD",
        "RAW EVIDENCE PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic source author",
        "automatic match",
        "fingerprint match",
        "duplicate detected",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_publisher_framing_summary
        assert unsafe_text not in rendered_publisher_framing_text

    publisher_framing_receipt_id = manual_publisher_framing_correction_receipt_id(
        queue
    )
    repeated_publisher_framing_receipt_id = (
        manual_publisher_framing_correction_receipt_id(queue)
    )
    assert publisher_framing_receipt_id == repeated_publisher_framing_receipt_id
    assert publisher_framing_receipt_id.startswith(
        "manual_publisher_framing_receipt_"
    )
    publisher_framing_receipt_events = (
        manual_publisher_framing_corrections_to_action_log_events(
            queue,
            session_id="manual-publisher-framing-session",
            timestamp_utc="2026-08-06T12:20:00Z",
        )
    )
    repeated_publisher_framing_receipt_events = (
        manual_publisher_framing_corrections_to_action_log_events(
            queue,
            session_id="manual-publisher-framing-session",
            timestamp_utc="2026-08-06T12:20:00Z",
        )
    )
    assert [event.to_dict() for event in publisher_framing_receipt_events] == [
        event.to_dict() for event in repeated_publisher_framing_receipt_events
    ]
    assert len(publisher_framing_receipt_events) == 1
    publisher_framing_receipt_dict = publisher_framing_receipt_events[0].to_dict()
    assert (
        publisher_framing_receipt_dict["action_type"]
        == "manual_publisher_framing_correction_review"
    )
    assert publisher_framing_receipt_dict["result"] == "USER_REVIEW_REQUIRED"
    assert publisher_framing_receipt_dict["target_id"] == publisher_framing_receipt_id
    assert publisher_framing_receipt_dict["artifact_ids"] == list(
        publisher_framing_summary.correction_note_ids
    )
    publisher_framing_receipt_summary = publisher_framing_receipt_dict[
        "request_summary"
    ]
    assert publisher_framing_receipt_summary["metadata_only"] is True
    assert publisher_framing_receipt_summary["review_required"] is True
    assert (
        publisher_framing_receipt_summary["review_status"]
        == "USER_REVIEW_REQUIRED"
    )
    assert publisher_framing_receipt_summary["manual_operator_supplied"] is True
    assert publisher_framing_receipt_summary["correction_note_count"] == 2
    assert (
        publisher_framing_receipt_summary["automated_source_author_detection"]
        is False
    )
    assert (
        publisher_framing_receipt_summary["automatic_publisher_framing_analysis"]
        is False
    )
    assert publisher_framing_receipt_summary["automatic_correction"] is False
    assert publisher_framing_receipt_summary["automated_matching"] is False
    assert publisher_framing_receipt_summary["fingerprint_matching"] is False
    assert (
        publisher_framing_receipt_summary["automatic_duplicate_detection"] is False
    )
    assert publisher_framing_receipt_summary["automatic_classification"] is False
    assert (
        publisher_framing_receipt_summary["sensitive_inference_prohibited"] is True
    )
    assert publisher_framing_receipt_summary["completed_evidence_claimed"] is False
    assert publisher_framing_receipt_summary["verified_evidence_claimed"] is False
    assert publisher_framing_receipt_summary["runtime_or_completion_claimed"] is False
    assert (
        publisher_framing_receipt_summary["safe_metadata_rows"][0][
            "correction_kind"
        ]
        == "DISPUTED_FRAMING"
    )
    assert (
        publisher_framing_receipt_summary["safe_metadata_rows"][1][
            "correction_kind"
        ]
        == "SOURCE_AUTHOR_CORRECTION"
    )
    assert (
        publisher_framing_receipt_summary["safe_metadata_rows"][0][
            "automated_source_author_detection"
        ]
        is False
    )
    assert (
        publisher_framing_receipt_summary["safe_metadata_rows"][0][
            "automatic_publisher_framing_analysis"
        ]
        is False
    )
    single_publisher_framing_queue = EvidenceItemQueue(
        items=(source_url, local_media),
        manual_publisher_framing_corrections=(publisher_credit_correction,),
    )
    single_publisher_framing_events = (
        manual_publisher_framing_corrections_to_action_log_events(
            single_publisher_framing_queue,
            session_id="single-manual-publisher-framing-session",
            timestamp_utc="2026-08-06T12:21:00Z",
        )
    )
    assert len(single_publisher_framing_events) == 1
    single_publisher_framing_summary = single_publisher_framing_events[0].to_dict()[
        "request_summary"
    ]
    assert single_publisher_framing_summary["correction_note_count"] == 1
    assert single_publisher_framing_summary["safe_metadata_rows"][0][
        "correction_kind"
    ] == "SOURCE_AUTHOR_CORRECTION"
    rendered_publisher_framing_receipt = action_log_event_to_json(
        publisher_framing_receipt_events[0]
    )
    for unsafe_text in (
        "RAW CORRECTION PAYLOAD",
        "RAW MEDIA PAYLOAD",
        "RAW EVIDENCE PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic correction",
        "automatic analysis",
        "source-author detected",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_publisher_framing_receipt

    publisher_framing_flow_summary = (
        build_manual_publisher_framing_correction_review_flow_summary(
            queue,
            session_id="manual-publisher-framing-session",
            timestamp_utc="2026-08-06T12:20:00Z",
        )
    )
    repeated_publisher_framing_flow_summary = (
        build_manual_publisher_framing_correction_review_flow_summary(
            queue,
            session_id="manual-publisher-framing-session",
            timestamp_utc="2026-08-06T12:20:00Z",
        )
    )
    assert (
        publisher_framing_flow_summary.to_dict()
        == repeated_publisher_framing_flow_summary.to_dict()
    )
    publisher_framing_flow_dict = publisher_framing_flow_summary.to_dict()
    assert publisher_framing_flow_dict["flow_id"].startswith(
        "manual_publisher_framing_flow_"
    )
    assert publisher_framing_flow_dict["status"] == "USER_REVIEW_REQUIRED"
    assert publisher_framing_flow_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert publisher_framing_flow_dict["metadata_only"] is True
    assert publisher_framing_flow_dict["manual_operator_supplied"] is True
    assert publisher_framing_flow_dict["user_review_required"] is True
    assert publisher_framing_flow_dict["correction_note_count"] == 2
    assert publisher_framing_flow_dict["review_row_count"] == 2
    assert publisher_framing_flow_dict["review_summary_count"] == 1
    assert publisher_framing_flow_dict["provenance_receipt_count"] == 1
    assert publisher_framing_flow_dict["correction_note_ids"] == list(
        publisher_framing_summary.correction_note_ids
    )
    assert publisher_framing_flow_dict["queue_item_ids"] == ["media-2", "source-1"]
    assert publisher_framing_flow_dict["related_item_ids"] == [
        "source-1",
        "media-1",
    ]
    assert publisher_framing_flow_dict["correction_kinds"] == [
        "DISPUTED_FRAMING",
        "SOURCE_AUTHOR_CORRECTION",
    ]
    assert publisher_framing_flow_dict["summary_ids"] == [
        publisher_framing_summary.summary_id
    ]
    assert publisher_framing_flow_dict["receipt_ids"] == [
        publisher_framing_receipt_id
    ]
    assert publisher_framing_flow_dict["receipt_event_ids"] == [
        publisher_framing_receipt_dict["event_id"]
    ]
    assert publisher_framing_flow_dict["receipt_event_hashes"] == [
        publisher_framing_receipt_dict["event_hash"]
    ]
    assert (
        publisher_framing_flow_dict["automated_source_author_detection"] is False
    )
    assert (
        publisher_framing_flow_dict["automatic_publisher_framing_analysis"]
        is False
    )
    assert publisher_framing_flow_dict["automatic_correction"] is False
    assert publisher_framing_flow_dict["automated_matching"] is False
    assert publisher_framing_flow_dict["fingerprint_matching"] is False
    assert (
        publisher_framing_flow_dict["automatic_duplicate_detection"] is False
    )
    assert publisher_framing_flow_dict["automatic_classification"] is False
    assert publisher_framing_flow_dict["sensitive_inference_prohibited"] is True
    assert publisher_framing_flow_dict["raw_correction_payload_included"] is False
    assert publisher_framing_flow_dict["raw_media_payload_included"] is False
    assert publisher_framing_flow_dict["raw_evidence_payload_included"] is False
    assert publisher_framing_flow_dict["full_local_path_included"] is False
    assert publisher_framing_flow_dict["runtime_or_completion_claimed"] is False
    assert publisher_framing_flow_dict["final_evidence_state_recorded"] is False
    assert publisher_framing_flow_dict["completed_evidence_claimed"] is False
    assert publisher_framing_flow_dict["verified_evidence_claimed"] is False
    rendered_publisher_framing_flow_summary = (
        manual_publisher_framing_correction_review_flow_summary_to_json(
            publisher_framing_flow_summary
        )
    )
    rendered_publisher_framing_flow_text = (
        build_manual_publisher_framing_correction_review_flow_summary_text(
            publisher_framing_flow_summary
        )
    )
    assert (
        "Manual publisher framing/source-author correction review flow summary"
        in rendered_publisher_framing_flow_text
    )
    assert "Correction notes: 2" in rendered_publisher_framing_flow_text
    assert "Review rows: 2" in rendered_publisher_framing_flow_text
    assert "Provenance receipts: 1" in rendered_publisher_framing_flow_text
    assert "Metadata only: yes" in rendered_publisher_framing_flow_text
    assert "Manual/operator supplied: yes" in rendered_publisher_framing_flow_text
    assert "Auto-correction flag: false" in rendered_publisher_framing_flow_text
    for unsafe_text in (
        "RAW CORRECTION PAYLOAD",
        "RAW MEDIA PAYLOAD",
        "RAW EVIDENCE PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic correction",
        "automatic analysis",
        "source-author detected",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_publisher_framing_flow_summary
        assert unsafe_text not in rendered_publisher_framing_flow_text

    single_publisher_framing_flow_summary = (
        build_manual_publisher_framing_correction_review_flow_summary(
            single_publisher_framing_queue,
            session_id="single-manual-publisher-framing-session",
            timestamp_utc="2026-08-06T12:21:00Z",
        )
    )
    single_publisher_framing_flow_dict = (
        single_publisher_framing_flow_summary.to_dict()
    )
    assert single_publisher_framing_flow_dict["status"] == "USER_REVIEW_REQUIRED"
    assert single_publisher_framing_flow_dict["correction_note_count"] == 1
    assert single_publisher_framing_flow_dict["review_row_count"] == 1
    assert single_publisher_framing_flow_dict["provenance_receipt_count"] == 1
    assert single_publisher_framing_flow_dict["correction_kinds"] == [
        "SOURCE_AUTHOR_CORRECTION"
    ]
    assert (
        single_publisher_framing_flow_dict["automated_source_author_detection"]
        is False
    )
    assert (
        single_publisher_framing_flow_dict[
            "automatic_publisher_framing_analysis"
        ]
        is False
    )
    assert single_publisher_framing_flow_dict["automatic_correction"] is False
    assert single_publisher_framing_flow_dict["automatic_classification"] is False
    assert (
        single_publisher_framing_flow_dict["sensitive_inference_prohibited"]
        is True
    )

    assert (
        manual_publisher_framing_corrections_to_action_log_events(
            EvidenceItemQueue(items=(source_url, local_media)),
            session_id="empty-manual-publisher-framing-session",
            timestamp_utc="2026-08-06T12:20:00Z",
        )
        == ()
    )
    for kwargs, expected_message in (
        (
            {
                "session_id": "",
                "timestamp_utc": "2026-08-06T12:20:00Z",
            },
            "session_id is required",
        ),
        (
            {
                "session_id": "manual-publisher-framing-session",
                "timestamp_utc": "",
            },
            "timestamp_utc is required",
        ),
    ):
        try:
            manual_publisher_framing_corrections_to_action_log_events(
                queue,
                **kwargs,
            )
        except ValueError as exc:
            assert expected_message in str(exc)
        else:
            raise AssertionError(f"{expected_message} should be required")

    media_source_chain_receipt_id = manual_media_source_chain_receipt_id(queue)
    repeated_media_source_chain_receipt_id = manual_media_source_chain_receipt_id(queue)
    assert media_source_chain_receipt_id == repeated_media_source_chain_receipt_id
    assert media_source_chain_receipt_id.startswith("manual_media_source_chain_receipt_")
    media_source_chain_receipt_events = (
        manual_media_source_chain_links_to_action_log_events(
            queue,
            session_id="manual-media-source-chain-session",
            timestamp_utc="2026-08-06T12:10:00Z",
        )
    )
    repeated_media_source_chain_receipt_events = (
        manual_media_source_chain_links_to_action_log_events(
            queue,
            session_id="manual-media-source-chain-session",
            timestamp_utc="2026-08-06T12:10:00Z",
        )
    )
    assert [event.to_dict() for event in media_source_chain_receipt_events] == [
        event.to_dict() for event in repeated_media_source_chain_receipt_events
    ]
    assert len(media_source_chain_receipt_events) == 1
    media_source_chain_receipt_dict = media_source_chain_receipt_events[0].to_dict()
    assert (
        media_source_chain_receipt_dict["action_type"]
        == "manual_media_source_chain_link_review"
    )
    assert media_source_chain_receipt_dict["result"] == "USER_REVIEW_REQUIRED"
    assert media_source_chain_receipt_dict["target_id"] == media_source_chain_receipt_id
    assert media_source_chain_receipt_dict["artifact_ids"] == list(
        media_source_chain_summary.manual_link_ids
    )
    media_source_chain_receipt_summary = media_source_chain_receipt_dict[
        "request_summary"
    ]
    assert media_source_chain_receipt_summary["metadata_only"] is True
    assert media_source_chain_receipt_summary["review_required"] is True
    assert media_source_chain_receipt_summary["review_status"] == "USER_REVIEW_REQUIRED"
    assert media_source_chain_receipt_summary["manual_operator_supplied"] is True
    assert media_source_chain_receipt_summary["manual_link_count"] == 4
    assert media_source_chain_receipt_summary["automated_matching"] is False
    assert media_source_chain_receipt_summary["fingerprint_matching"] is False
    assert media_source_chain_receipt_summary["automatic_duplicate_detection"] is False
    assert media_source_chain_receipt_summary["automatic_classification"] is False
    assert media_source_chain_receipt_summary["sensitive_inference_prohibited"] is True
    assert media_source_chain_receipt_summary["completed_evidence_claimed"] is False
    assert media_source_chain_receipt_summary["runtime_or_completion_claimed"] is False
    assert (
        media_source_chain_receipt_summary["safe_metadata_rows"][0]["manual_link_id"]
        == media_source_chain_summary.manual_link_ids[0]
    )
    assert (
        media_source_chain_receipt_summary["safe_metadata_rows"][0]["relation_kind"]
        == "SAME_MEDIA"
    )
    assert (
        media_source_chain_receipt_summary["safe_metadata_rows"][3]["relation_kind"]
        == "DERIVATIVE"
    )
    assert (
        media_source_chain_receipt_summary["safe_metadata_rows"][0]["automated_matching"]
        is False
    )
    assert (
        media_source_chain_receipt_summary["safe_metadata_rows"][0][
            "fingerprint_matching"
        ]
        is False
    )
    assert (
        media_source_chain_receipt_summary["safe_metadata_rows"][0][
            "automatic_duplicate_detection"
        ]
        is False
    )
    rendered_media_source_chain_receipt = action_log_event_to_json(
        media_source_chain_receipt_events[0]
    )
    for unsafe_text in (
        "RAW MEDIA PAYLOAD",
        "RAW EVIDENCE PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic match",
        "fingerprint match",
        "duplicate detected",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_media_source_chain_receipt

    assert (
        manual_media_source_chain_links_to_action_log_events(
            EvidenceItemQueue(items=(source_url, local_media)),
            session_id="empty-manual-media-source-chain-session",
            timestamp_utc="2026-08-06T12:10:00Z",
        )
        == ()
    )
    for kwargs, expected_message in (
        ({"session_id": "", "timestamp_utc": "2026-08-06T12:10:00Z"}, "session_id"),
        (
            {"session_id": "manual-media-source-chain-session", "timestamp_utc": ""},
            "timestamp_utc",
        ),
    ):
        try:
            manual_media_source_chain_links_to_action_log_events(queue, **kwargs)
        except ValueError as exc:
            assert expected_message in str(exc)
        else:
            raise AssertionError(f"{expected_message} should be required")
    media_source_chain_flow_summary = build_manual_media_source_chain_review_flow_summary(
        queue,
        session_id="manual-media-source-chain-session",
        timestamp_utc="2026-08-06T12:10:00Z",
        previous_event_hash="previous-media-chain-hash",
        actor_id="app",
        app_version="test",
    )
    repeated_media_source_chain_flow_summary = (
        build_manual_media_source_chain_review_flow_summary(
            queue,
            session_id="manual-media-source-chain-session",
            timestamp_utc="2026-08-06T12:10:00Z",
            previous_event_hash="previous-media-chain-hash",
            actor_id="app",
            app_version="test",
        )
    )
    media_source_chain_flow_receipt_events = (
        manual_media_source_chain_links_to_action_log_events(
            queue,
            session_id="manual-media-source-chain-session",
            timestamp_utc="2026-08-06T12:10:00Z",
            previous_event_hash="previous-media-chain-hash",
            actor_id="app",
            app_version="test",
        )
    )
    assert (
        media_source_chain_flow_summary.to_dict()
        == repeated_media_source_chain_flow_summary.to_dict()
    )
    media_source_chain_flow_dict = media_source_chain_flow_summary.to_dict()
    assert media_source_chain_flow_dict["flow_id"].startswith(
        "manual_media_source_chain_flow_"
    )
    assert media_source_chain_flow_dict["status"] == "USER_REVIEW_REQUIRED"
    assert media_source_chain_flow_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert media_source_chain_flow_dict["metadata_only"] is True
    assert media_source_chain_flow_dict["manual_operator_supplied"] is True
    assert media_source_chain_flow_dict["user_review_required"] is True
    assert media_source_chain_flow_dict["manual_link_count"] == 4
    assert media_source_chain_flow_dict["review_row_count"] == len(
        media_source_chain_rows
    )
    assert media_source_chain_flow_dict["review_summary_count"] == 1
    assert media_source_chain_flow_dict["provenance_receipt_count"] == 1
    assert (
        media_source_chain_flow_dict["manual_link_ids"]
        == list(media_source_chain_summary.manual_link_ids)
    )
    assert media_source_chain_flow_dict["source_item_ids"] == [
        "media-1",
        "media-2",
        "media-3",
        "source-1",
    ]
    assert media_source_chain_flow_dict["target_item_ids"] == [
        "media-2",
        "source-1",
        "media-4",
        "media-1",
    ]
    assert media_source_chain_flow_dict["relation_kinds"] == [
        "SAME_MEDIA",
        "REPOST",
        "OTHER",
        "DERIVATIVE",
    ]
    assert media_source_chain_flow_dict["directions"] == [
        "RELATED_UNDIRECTED",
        "DERIVATIVE_TO_SOURCE",
        "UNKNOWN",
        "SOURCE_TO_DERIVATIVE",
    ]
    assert media_source_chain_flow_dict["summary_ids"] == [
        media_source_chain_summary.summary_id
    ]
    assert media_source_chain_flow_dict["receipt_ids"] == [
        media_source_chain_receipt_id
    ]
    assert media_source_chain_flow_dict["receipt_event_ids"] == [
        media_source_chain_flow_receipt_events[0].event_id
    ]
    assert media_source_chain_flow_dict["receipt_event_hashes"] == [
        media_source_chain_flow_receipt_events[0].event_hash
    ]
    assert media_source_chain_flow_dict["automated_matching"] is False
    assert media_source_chain_flow_dict["fingerprint_matching"] is False
    assert media_source_chain_flow_dict["automatic_duplicate_detection"] is False
    assert media_source_chain_flow_dict["automatic_classification"] is False
    assert media_source_chain_flow_dict["sensitive_inference_prohibited"] is True
    assert media_source_chain_flow_dict["raw_media_payload_included"] is False
    assert media_source_chain_flow_dict["raw_evidence_payload_included"] is False
    assert media_source_chain_flow_dict["full_local_path_included"] is False
    assert media_source_chain_flow_dict["runtime_or_completion_claimed"] is False
    assert media_source_chain_flow_dict["final_evidence_state_recorded"] is False
    assert media_source_chain_flow_dict["completed_evidence_claimed"] is False
    assert media_source_chain_flow_dict["verified_evidence_claimed"] is False
    rendered_media_source_chain_flow = (
        manual_media_source_chain_review_flow_summary_to_json(
            media_source_chain_flow_summary
        )
    )
    rendered_media_source_chain_flow_text = (
        build_manual_media_source_chain_review_flow_summary_text(
            media_source_chain_flow_summary
        )
    )
    assert (
        "Manual media source-chain review flow summary"
        in rendered_media_source_chain_flow_text
    )
    assert "Manual links: 4" in rendered_media_source_chain_flow_text
    assert "Review rows: 4" in rendered_media_source_chain_flow_text
    assert "Review summaries: 1" in rendered_media_source_chain_flow_text
    assert "Provenance receipts: 1" in rendered_media_source_chain_flow_text
    assert "Metadata only: yes" in rendered_media_source_chain_flow_text
    assert "Manual/operator supplied: yes" in rendered_media_source_chain_flow_text
    for unsafe_text in (
        "RAW MEDIA PAYLOAD",
        "RAW EVIDENCE PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic match",
        "fingerprint match",
        "duplicate detected",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_media_source_chain_flow
        assert unsafe_text not in rendered_media_source_chain_flow_text
    claim_notes = queue_source_role_reviews_to_claim_notes(queue)
    assert len(claim_notes) == 2
    claim_note_dict = claim_notes[0].to_dict()
    assert claim_note_dict["claim_text"] == source_role_review.claim_text
    assert claim_note_dict["claim_source_role"] == "PRIMARY_ORIGINAL_AUTHORED"
    assert claim_note_dict["primary_source_status"] == "PRIMARY_SOURCE_LOCATED"
    assert claim_note_dict["currentness_status"] == "CURRENT"
    assert claim_note_dict["captured_at_utc"] == "2026-08-06T10:05:00Z"
    assert claim_note_dict["verification_notes"] == source_role_review.reviewer_notes
    second_claim_note_dict = claim_notes[1].to_dict()
    assert second_claim_note_dict["claim_source_role"] == "TERTIARY_PROPAGATED_SOURCE"
    assert second_claim_note_dict["source_chain_gap"] is True
    assert second_claim_note_dict["closed_loop_reporting_flag"] is True

    ui_rows = queue_source_role_reviews_to_ui_rows(queue)
    second_ui_rows = queue_source_role_reviews_to_ui_rows(queue)
    assert [row.to_dict() for row in ui_rows] == [row.to_dict() for row in second_ui_rows]
    assert [row.queue_item_id for row in ui_rows] == ["source-review-1", "source-review-2"]
    first_ui_row = ui_rows[0].to_dict()
    assert first_ui_row["review_status"] == "USER_REVIEW_REQUIRED"
    assert first_ui_row["source_role"] == "PRIMARY_ORIGINAL_AUTHORED"
    assert first_ui_row["claim_text_recorded"] is True
    assert first_ui_row["claim_text_display"] == "not shown in summary; open the source item for manual review"
    assert first_ui_row["evidence_basis_recorded"] is True
    assert first_ui_row["reviewer_notes_recorded"] is True
    assert first_ui_row["automatic_classification"] is False
    assert first_ui_row["sensitive_inference_prohibited"] is True
    assert first_ui_row["raw_evidence_payload_included"] is False
    assert first_ui_row["full_local_path_included"] is False
    assert first_ui_row["completed_evidence_claimed"] is False
    assert first_ui_row["verified_evidence_claimed"] is False
    assert first_ui_row["live_capture_claimed"] is False
    assert first_ui_row["api_provider_capture_claimed"] is False
    assert first_ui_row["browser_automation_claimed"] is False
    assert first_ui_row["archive_download_ocr_warc_wacz_claimed"] is False

    ui_summary = build_source_role_review_ui_summary(queue)
    assert "Source-role / claim-level review metadata" in ui_summary
    assert "Review rows: 2" in ui_summary
    assert "USER_REVIEW_REQUIRED" in ui_summary
    assert "source-review-1" in ui_summary
    assert "source-review-2" in ui_summary
    for unsafe_text in (
        "RAW EVIDENCE PAYLOAD",
        "ANOTHER RAW CLAIM PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic classification",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
    ):
        assert unsafe_text not in ui_summary

    receipt_id = source_role_review_receipt_id(queue)
    second_receipt_id = source_role_review_receipt_id(queue)
    assert receipt_id == second_receipt_id
    assert receipt_id.startswith("source_role_review_receipt_")
    receipt_events = queue_source_role_reviews_to_action_log_events(
        queue,
        session_id="source-role-review-session",
        timestamp_utc="2026-08-06T11:00:00Z",
    )
    repeated_receipt_events = queue_source_role_reviews_to_action_log_events(
        queue,
        session_id="source-role-review-session",
        timestamp_utc="2026-08-06T11:00:00Z",
    )
    assert [event.to_dict() for event in receipt_events] == [
        event.to_dict() for event in repeated_receipt_events
    ]
    assert len(receipt_events) == 1
    receipt_dict = receipt_events[0].to_dict()
    assert receipt_dict["action_type"] == "source_role_review_metadata_receipt"
    assert receipt_dict["result"] == "USER_REVIEW_REQUIRED"
    assert receipt_dict["target_id"] == receipt_id
    receipt_summary = receipt_dict["request_summary"]
    assert receipt_summary["metadata_only"] is True
    assert receipt_summary["review_required"] is True
    assert receipt_summary["automatic_classification"] is False
    assert receipt_summary["sensitive_inference_prohibited"] is True
    assert receipt_summary["claim_note_count"] == len(claim_notes)
    assert receipt_summary["ui_row_count"] == len(ui_rows)
    assert receipt_summary["source_role_review_row_count"] == 2
    assert receipt_summary["safe_metadata_rows"][0]["queue_item_id"] == "source-review-1"
    assert receipt_summary["safe_metadata_rows"][1]["queue_item_id"] == "source-review-2"
    assert receipt_summary["safe_metadata_rows"][0]["source_role"] == "PRIMARY_ORIGINAL_AUTHORED"
    assert receipt_summary["safe_metadata_rows"][1]["source_role"] == "TERTIARY_PROPAGATED_SOURCE"
    assert receipt_summary["safe_metadata_rows"][1]["source_chain_gap"] is True
    assert receipt_summary["safe_metadata_rows"][1]["closed_loop_reporting_flag"] is True

    rendered_receipt = action_log_event_to_json(receipt_events[0])
    for unsafe_text in (
        "RAW EVIDENCE PAYLOAD",
        "ANOTHER RAW CLAIM PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic classification",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_receipt
    assert "No completed or verified evidence claim is made." not in rendered_receipt

    assert (
        queue_source_role_reviews_to_action_log_events(
            EvidenceItemQueue(items=(source_url, local_media)),
            session_id="empty-source-role-review-session",
            timestamp_utc="2026-08-06T11:00:00Z",
        )
        == ()
    )
    for kwargs, expected_message in (
        ({"session_id": "", "timestamp_utc": "2026-08-06T11:00:00Z"}, "session_id"),
        ({"session_id": "source-role-review-session", "timestamp_utc": ""}, "timestamp_utc"),
    ):
        try:
            queue_source_role_reviews_to_action_log_events(queue, **kwargs)
        except ValueError as exc:
            assert expected_message in str(exc)
        else:
            raise AssertionError(f"{expected_message} should be required")

    flow_summary = build_source_role_review_flow_summary(
        queue,
        session_id="source-role-review-session",
        timestamp_utc="2026-08-06T11:00:00Z",
        previous_event_hash="previous-review-hash",
        actor_id="app",
        app_version="test",
    )
    flow_receipt_events = queue_source_role_reviews_to_action_log_events(
        queue,
        session_id="source-role-review-session",
        timestamp_utc="2026-08-06T11:00:00Z",
        previous_event_hash="previous-review-hash",
        actor_id="app",
        app_version="test",
    )
    repeated_flow_summary = build_source_role_review_flow_summary(
        queue,
        session_id="source-role-review-session",
        timestamp_utc="2026-08-06T11:00:00Z",
        previous_event_hash="previous-review-hash",
        actor_id="app",
        app_version="test",
    )
    assert flow_summary.to_dict() == repeated_flow_summary.to_dict()
    flow_dict = flow_summary.to_dict()
    assert flow_dict["flow_id"].startswith("source_role_review_flow_")
    assert flow_dict["status"] == "USER_REVIEW_REQUIRED"
    assert flow_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert flow_dict["metadata_only"] is True
    assert flow_dict["user_review_required"] is True
    assert flow_dict["source_role_review_count"] == len(ui_rows)
    assert flow_dict["claim_note_count"] == len(claim_notes)
    assert flow_dict["ui_row_count"] == len(ui_rows)
    assert flow_dict["provenance_receipt_count"] == len(receipt_events)
    assert flow_dict["queue_item_ids"] == ["source-review-1", "source-review-2"]
    assert flow_dict["source_roles"] == [
        "PRIMARY_ORIGINAL_AUTHORED",
        "TERTIARY_PROPAGATED_SOURCE",
    ]
    assert flow_dict["primary_source_statuses"] == [
        "PRIMARY_SOURCE_LOCATED",
        "TERTIARY_PROPAGATED_CLAIM",
    ]
    assert flow_dict["currentness_statuses"] == ["CURRENT", "UNKNOWN"]
    assert flow_dict["receipt_ids"] == [receipt_id]
    assert flow_dict["receipt_event_ids"] == [flow_receipt_events[0].event_id]
    assert flow_dict["receipt_event_hashes"] == [flow_receipt_events[0].event_hash]
    assert flow_dict["automatic_classification"] is False
    assert flow_dict["sensitive_inference_prohibited"] is True
    assert flow_dict["raw_evidence_payload_included"] is False
    assert flow_dict["full_local_path_included"] is False
    assert flow_dict["runtime_or_completion_claimed"] is False
    assert flow_dict["final_evidence_state_recorded"] is False
    rendered_flow = source_role_review_flow_summary_to_json(flow_summary)
    rendered_flow_text = build_source_role_review_flow_summary_text(flow_summary)
    assert "Source-role review flow summary" in rendered_flow_text
    assert "Review rows: 2" in rendered_flow_text
    assert "Claim notes: 2" in rendered_flow_text
    assert "Provenance receipts: 1" in rendered_flow_text
    assert "Metadata only: yes" in rendered_flow_text
    assert "Auto-classify flag: false" in rendered_flow_text
    for unsafe_text in (
        "RAW EVIDENCE PAYLOAD",
        "ANOTHER RAW CLAIM PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "automatic classification",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_flow
        assert unsafe_text not in rendered_flow_text

    closed_loop_summary = build_closed_loop_source_chain_review_summary(queue)
    repeated_closed_loop_summary = build_closed_loop_source_chain_review_summary(queue)
    assert closed_loop_summary.to_dict() == repeated_closed_loop_summary.to_dict()
    closed_loop_dict = closed_loop_summary.to_dict()
    assert closed_loop_dict["summary_id"].startswith("closed_loop_source_chain_review_")
    assert closed_loop_dict["status"] == "USER_REVIEW_REQUIRED"
    assert closed_loop_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert closed_loop_dict["metadata_only"] is True
    assert closed_loop_dict["explicit_metadata_only"] is True
    assert closed_loop_dict["user_review_required"] is True
    assert closed_loop_dict["total_source_role_review_count"] == 2
    assert closed_loop_dict["flagged_review_count"] == 1
    assert closed_loop_dict["propagated_source_review_count"] == 1
    assert closed_loop_dict["source_chain_gap_count"] == 1
    assert closed_loop_dict["closed_loop_reporting_flag_count"] == 1
    assert closed_loop_dict["flagged_queue_item_ids"] == ["source-review-2"]
    assert closed_loop_dict["source_roles"] == ["TERTIARY_PROPAGATED_SOURCE"]
    assert closed_loop_dict["primary_source_statuses"] == ["TERTIARY_PROPAGATED_CLAIM"]
    assert closed_loop_dict["currentness_statuses"] == ["UNKNOWN"]
    assert closed_loop_dict["automatic_classification"] is False
    assert closed_loop_dict["sensitive_inference_prohibited"] is True
    assert closed_loop_dict["inference_performed"] is False
    assert closed_loop_dict["duplicate_detection_performed"] is False
    assert closed_loop_dict["raw_evidence_payload_included"] is False
    assert closed_loop_dict["full_local_path_included"] is False
    assert closed_loop_dict["completed_evidence_claimed"] is False
    rendered_closed_loop = closed_loop_source_chain_review_summary_to_json(
        closed_loop_summary
    )
    rendered_closed_loop_text = build_closed_loop_source_chain_review_summary_text(
        closed_loop_summary
    )
    assert "Closed-loop / propagated-source review summary" in rendered_closed_loop_text
    assert "Flagged reviews: 1" in rendered_closed_loop_text
    assert "Propagated-source reviews: 1" in rendered_closed_loop_text
    assert "Source-chain gaps: 1" in rendered_closed_loop_text
    assert "Closed-loop flags: 1" in rendered_closed_loop_text
    assert "Explicit recorded flags only: yes" in rendered_closed_loop_text
    for unsafe_text in (
        "RAW EVIDENCE PAYLOAD",
        "ANOTHER RAW CLAIM PAYLOAD",
        r"T:\Evidence",
        "completed evidence",
        "verified evidence",
        "classified",
        "live verified",
        "API capture",
        "browser automation",
        "downloaded media",
        "screenshot",
        "OCR complete",
        "archive complete",
        "WARC",
        "WACZ",
        "account",
        "cookie",
        "token",
        "protected attribute",
    ):
        assert unsafe_text not in rendered_closed_loop
        assert unsafe_text not in rendered_closed_loop_text

    empty_flow_summary = build_source_role_review_flow_summary(
        EvidenceItemQueue(items=(source_url, local_media)),
        session_id="empty-source-role-review-session",
        timestamp_utc="2026-08-06T11:00:00Z",
    )
    empty_flow_dict = empty_flow_summary.to_dict()
    assert empty_flow_dict["status"] == "NO_SOURCE_ROLE_REVIEWS"
    assert empty_flow_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert empty_flow_dict["source_role_review_count"] == 0
    assert empty_flow_dict["claim_note_count"] == 0
    assert empty_flow_dict["ui_row_count"] == 0
    assert empty_flow_dict["provenance_receipt_count"] == 0
    assert empty_flow_dict["runtime_or_completion_claimed"] is False
    assert empty_flow_dict["final_evidence_state_recorded"] is False
    empty_closed_loop_summary = build_closed_loop_source_chain_review_summary(
        EvidenceItemQueue(items=(source_url, local_media))
    )
    empty_closed_loop_dict = empty_closed_loop_summary.to_dict()
    assert empty_closed_loop_dict["status"] == "NO_CLOSED_LOOP_OR_PROPAGATED_SOURCE_FLAGS"
    assert empty_closed_loop_dict["flagged_review_count"] == 0
    assert empty_closed_loop_dict["propagated_source_review_count"] == 0
    assert empty_closed_loop_dict["source_chain_gap_count"] == 0
    assert empty_closed_loop_dict["closed_loop_reporting_flag_count"] == 0
    assert empty_closed_loop_dict["automatic_classification"] is False
    assert empty_closed_loop_dict["sensitive_inference_prohibited"] is True
    assert empty_closed_loop_dict["inference_performed"] is False
    assert empty_closed_loop_dict["completed_evidence_claimed"] is False
    empty_media_source_chain_summary = build_manual_media_source_chain_review_summary(
        EvidenceItemQueue(items=(source_url, local_media))
    )
    empty_media_source_chain_dict = empty_media_source_chain_summary.to_dict()
    assert empty_media_source_chain_dict["status"] == "NO_MANUAL_MEDIA_SOURCE_CHAIN_LINKS"
    assert empty_media_source_chain_dict["manual_link_count"] == 0
    assert empty_media_source_chain_dict["metadata_only"] is True
    assert empty_media_source_chain_dict["manual_operator_supplied"] is True
    assert empty_media_source_chain_dict["user_review_required"] is True
    assert empty_media_source_chain_dict["automated_matching"] is False
    assert empty_media_source_chain_dict["fingerprint_matching"] is False
    assert empty_media_source_chain_dict["automatic_duplicate_detection"] is False
    assert empty_media_source_chain_dict["automatic_classification"] is False
    assert empty_media_source_chain_dict["sensitive_inference_prohibited"] is True
    assert empty_media_source_chain_dict["completed_evidence_claimed"] is False
    empty_media_source_chain_flow_summary = (
        build_manual_media_source_chain_review_flow_summary(
            EvidenceItemQueue(items=(source_url, local_media)),
            session_id="empty-manual-media-source-chain-session",
            timestamp_utc="2026-08-06T12:10:00Z",
        )
    )
    empty_media_source_chain_flow_dict = empty_media_source_chain_flow_summary.to_dict()
    assert (
        empty_media_source_chain_flow_dict["status"]
        == "NO_MANUAL_MEDIA_SOURCE_CHAIN_LINKS"
    )
    assert empty_media_source_chain_flow_dict["manual_link_count"] == 0
    assert empty_media_source_chain_flow_dict["review_row_count"] == 0
    assert empty_media_source_chain_flow_dict["review_summary_count"] == 0
    assert empty_media_source_chain_flow_dict["provenance_receipt_count"] == 0
    assert empty_media_source_chain_flow_dict["manual_link_ids"] == []
    assert empty_media_source_chain_flow_dict["receipt_ids"] == []
    assert empty_media_source_chain_flow_dict["metadata_only"] is True
    assert empty_media_source_chain_flow_dict["manual_operator_supplied"] is True
    assert empty_media_source_chain_flow_dict["user_review_required"] is True
    assert empty_media_source_chain_flow_dict["automated_matching"] is False
    assert empty_media_source_chain_flow_dict["fingerprint_matching"] is False
    assert empty_media_source_chain_flow_dict["automatic_duplicate_detection"] is False
    assert empty_media_source_chain_flow_dict["automatic_classification"] is False
    assert empty_media_source_chain_flow_dict["sensitive_inference_prohibited"] is True
    assert empty_media_source_chain_flow_dict["runtime_or_completion_claimed"] is False
    assert empty_media_source_chain_flow_dict["final_evidence_state_recorded"] is False
    assert empty_media_source_chain_flow_dict["completed_evidence_claimed"] is False
    empty_publisher_framing_summary = (
        build_manual_publisher_framing_correction_review_summary(
            EvidenceItemQueue(items=(source_url, local_media))
        )
    )
    empty_publisher_framing_dict = empty_publisher_framing_summary.to_dict()
    assert (
        empty_publisher_framing_dict["status"]
        == "NO_MANUAL_PUBLISHER_FRAMING_CORRECTIONS"
    )
    assert empty_publisher_framing_dict["review_status"] == "USER_REVIEW_REQUIRED"
    assert empty_publisher_framing_dict["correction_note_count"] == 0
    assert empty_publisher_framing_dict["queue_item_ids"] == []
    assert empty_publisher_framing_dict["correction_note_ids"] == []
    assert empty_publisher_framing_dict["metadata_only"] is True
    assert empty_publisher_framing_dict["manual_operator_supplied"] is True
    assert empty_publisher_framing_dict["user_review_required"] is True
    assert (
        empty_publisher_framing_dict["automated_source_author_detection"] is False
    )
    assert empty_publisher_framing_dict["automated_matching"] is False
    assert empty_publisher_framing_dict["fingerprint_matching"] is False
    assert empty_publisher_framing_dict["automatic_duplicate_detection"] is False
    assert empty_publisher_framing_dict["automatic_classification"] is False
    assert empty_publisher_framing_dict["sensitive_inference_prohibited"] is True
    assert empty_publisher_framing_dict["completed_evidence_claimed"] is False
    empty_publisher_framing_flow_summary = (
        build_manual_publisher_framing_correction_review_flow_summary(
            EvidenceItemQueue(items=(source_url, local_media)),
            session_id="empty-manual-publisher-framing-session",
            timestamp_utc="2026-08-06T12:20:00Z",
        )
    )
    empty_publisher_framing_flow_dict = (
        empty_publisher_framing_flow_summary.to_dict()
    )
    assert (
        empty_publisher_framing_flow_dict["status"]
        == "NO_MANUAL_PUBLISHER_FRAMING_CORRECTIONS"
    )
    assert (
        empty_publisher_framing_flow_dict["review_status"]
        == "USER_REVIEW_REQUIRED"
    )
    assert empty_publisher_framing_flow_dict["correction_note_count"] == 0
    assert empty_publisher_framing_flow_dict["review_row_count"] == 0
    assert empty_publisher_framing_flow_dict["review_summary_count"] == 0
    assert empty_publisher_framing_flow_dict["provenance_receipt_count"] == 0
    assert empty_publisher_framing_flow_dict["correction_note_ids"] == []
    assert empty_publisher_framing_flow_dict["summary_ids"] == []
    assert empty_publisher_framing_flow_dict["receipt_ids"] == []
    assert empty_publisher_framing_flow_dict["metadata_only"] is True
    assert empty_publisher_framing_flow_dict["manual_operator_supplied"] is True
    assert empty_publisher_framing_flow_dict["user_review_required"] is True
    assert (
        empty_publisher_framing_flow_dict["automated_source_author_detection"]
        is False
    )
    assert (
        empty_publisher_framing_flow_dict[
            "automatic_publisher_framing_analysis"
        ]
        is False
    )
    assert empty_publisher_framing_flow_dict["automatic_correction"] is False
    assert empty_publisher_framing_flow_dict["automatic_classification"] is False
    assert (
        empty_publisher_framing_flow_dict["sensitive_inference_prohibited"]
        is True
    )
    assert empty_publisher_framing_flow_dict["runtime_or_completion_claimed"] is False
    assert empty_publisher_framing_flow_dict["final_evidence_state_recorded"] is False
    assert empty_publisher_framing_flow_dict["completed_evidence_claimed"] is False

    manifest = TotalExportManifest(
        package_id="queue-source-role-review",
        source_urls=["https://example.test/source"],
        claim_notes=list(claim_notes),
        notes="Source-role review metadata only; USER_REVIEW_REQUIRED.",
    )
    manifest_dict = manifest.to_dict()
    assert manifest_dict["claim_notes"][0]["claim_source_role"] == "PRIMARY_ORIGINAL_AUTHORED"
    assert "automatic_classification" not in manifest_dict["claim_notes"][0]


if __name__ == "__main__":
    run_self_test()
    print("Evidence item queue self-test passed.")
