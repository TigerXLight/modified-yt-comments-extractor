from evidence_schema import (
    AccessMode,
    CaptureMethod,
    ClaimEvidenceNote,
    CurrentnessStatus,
    EvidenceProvenance,
    MediaSourceChainNote,
    PrimarySourceStatus,
    SourceRole,
)


def _assert_utc_timestamp(value: str) -> None:
    assert value.endswith("Z"), value
    assert "T" in value, value


def run_self_test() -> None:
    provenance = EvidenceProvenance(
        source_url="https://www.youtube.com/watch?v=aB3_dE-9xYz",
        source_platform="youtube",
        adapter_name="youtube",
        access_mode=AccessMode.PUBLIC_ACCESS,
        capture_method=CaptureMethod.API,
        source_role=SourceRole.PRIMARY_ORIGINAL_AUTHORED,
        primary_source_status=PrimarySourceStatus.PRIMARY_SOURCE_LOCATED,
    )
    _assert_utc_timestamp(provenance.capture_time_utc)
    provenance_dict = provenance.to_dict()
    assert provenance_dict["access_mode"] == "PUBLIC_ACCESS"
    assert provenance_dict["capture_method"] == "API"
    assert provenance_dict["source_role"] == "PRIMARY_ORIGINAL_AUTHORED"

    claim_note = ClaimEvidenceNote(
        claim_text="A self-authored post shows a visible appearance detail.",
        claim_type="appearance",
        claim_source_role=SourceRole.PRIMARY_ORIGINAL_AUTHORED,
        currentness_status=CurrentnessStatus.HISTORICAL,
    )
    _assert_utc_timestamp(claim_note.captured_at_utc)
    assert claim_note.to_dict()["currentness_status"] == "HISTORICAL"

    media_note = MediaSourceChainNote(
        media_observed_on_url="https://example.com/story",
        same_media_seen_on_other_urls=("https://example.com/repost",),
    )
    _assert_utc_timestamp(media_note.capture_time_utc)
    assert media_note.to_dict()["same_media_seen_on_other_urls"] == [
        "https://example.com/repost"
    ]


if __name__ == "__main__":
    run_self_test()
    print("Evidence schema self-test passed.")
