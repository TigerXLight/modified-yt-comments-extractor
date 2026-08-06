from evidence_item_queue import (
    ASRPairingMetadata,
    EvidenceItemLink,
    EvidenceItemQueue,
    EvidenceItemRole,
    EvidenceItemStatus,
    EvidenceLinkOrigin,
    EvidenceQueueItem,
    SourceRoleReviewMetadata,
    queue_source_role_reviews_to_claim_notes,
)
from evidence_schema import CurrentnessStatus, PrimarySourceStatus, SourceRole
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
        claim_text="The local source directly states a bounded claim.",
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
    source_review_item = EvidenceQueueItem(
        item_id="source-review-1",
        item_role=EvidenceItemRole.SOURCE_URL,
        source_url="https://example.test/source",
        item_status=EvidenceItemStatus.NEEDS_REVIEW,
        source_role_reviews=(source_role_review,),
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
        ),
        links=(explicit_link, derived_link),
        asr_pairings=(local_only_pairing, incomplete_pairing),
    )
    queue_dict = queue.to_dict()
    assert len(queue_dict["items"]) == 10
    assert queue_dict["items"][0]["item_role"] == "SOURCE_URL"
    assert queue_dict["links"][1]["link_origin"] == "DERIVED_FROM_APP_STATE"
    assert queue_dict["asr_pairings"][0]["reference_accuracy_percent"] == 74.19
    assert queue_dict["asr_pairings"][1]["reference_accuracy_percent"] is None
    claim_notes = queue_source_role_reviews_to_claim_notes(queue)
    assert len(claim_notes) == 1
    claim_note_dict = claim_notes[0].to_dict()
    assert claim_note_dict["claim_text"] == source_role_review.claim_text
    assert claim_note_dict["claim_source_role"] == "PRIMARY_ORIGINAL_AUTHORED"
    assert claim_note_dict["primary_source_status"] == "PRIMARY_SOURCE_LOCATED"
    assert claim_note_dict["currentness_status"] == "CURRENT"
    assert claim_note_dict["captured_at_utc"] == "2026-08-06T10:05:00Z"
    assert claim_note_dict["verification_notes"] == source_role_review.reviewer_notes

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
