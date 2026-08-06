from evidence_item_queue import (
    ASRPairingMetadata,
    EvidenceItemLink,
    EvidenceItemQueue,
    EvidenceItemRole,
    EvidenceItemStatus,
    EvidenceLinkOrigin,
    EvidenceQueueItem,
    SourceRoleReviewMetadata,
    build_source_role_review_ui_summary,
    build_source_role_review_flow_summary,
    build_source_role_review_flow_summary_text,
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
    )
    queue_dict = queue.to_dict()
    assert len(queue_dict["items"]) == 11
    assert queue_dict["items"][0]["item_role"] == "SOURCE_URL"
    assert queue_dict["links"][1]["link_origin"] == "DERIVED_FROM_APP_STATE"
    assert queue_dict["asr_pairings"][0]["reference_accuracy_percent"] == 74.19
    assert queue_dict["asr_pairings"][1]["reference_accuracy_percent"] is None
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
