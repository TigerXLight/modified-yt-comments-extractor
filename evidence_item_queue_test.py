from evidence_item_queue import (
    ASRPairingMetadata,
    EvidenceItemLink,
    EvidenceItemQueue,
    EvidenceItemRole,
    EvidenceItemStatus,
    EvidenceLinkOrigin,
    EvidenceQueueItem,
)


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
        ),
        links=(explicit_link, derived_link),
        asr_pairings=(local_only_pairing, incomplete_pairing),
    )
    queue_dict = queue.to_dict()
    assert len(queue_dict["items"]) == 9
    assert queue_dict["items"][0]["item_role"] == "SOURCE_URL"
    assert queue_dict["links"][1]["link_origin"] == "DERIVED_FROM_APP_STATE"
    assert queue_dict["asr_pairings"][0]["reference_accuracy_percent"] == 74.19
    assert queue_dict["asr_pairings"][1]["reference_accuracy_percent"] is None


if __name__ == "__main__":
    run_self_test()
    print("Evidence item queue self-test passed.")
