from __future__ import annotations

from twitter_capture_profile_media_provenance import (
    build_twitter_profile_media_provenance,
    render_profile_media_provenance_summary,
)


SOURCE_URL = "https://x.com/example/status/1877644315867963403"


def test_profile_media_provenance_has_v76p_required_fields() -> None:
    record = build_twitter_profile_media_provenance(
        source_url=SOURCE_URL,
        display_name="Example User",
        post_text="This is a fixture post.",
        created_at="2026-08-16T10:00:00Z",
        screenshot_references=({"path": "screenshots/status.png", "sha256": "abc"},),
        media_references=({"media_url": "https://pbs.twimg.com/media/example.jpg", "source_url": SOURCE_URL},),
        cursor_state={"cursor_out": "cursor-next"},
        rate_limit_or_cooldown_state={"rate_limit_remaining": 10},
    )
    data = record.to_dict()
    for field in (
        "source_url",
        "canonical_url",
        "platform",
        "account_handle",
        "display_name",
        "post_id",
        "status_id",
        "post_text",
        "created_at",
        "captured_at",
        "archive_url",
        "screenshot_references",
        "media_references",
        "rendered_dom_status",
        "cursor_state",
        "rate_limit_or_cooldown_state",
        "uploader_account",
        "speaker",
        "clip_holder",
        "original_programme_channel_source",
        "transcripted_statement",
        "claim_subject_affiliation_review",
        "social_media_video_provenance_review",
        "source_role_candidate",
        "final_source_role_decision",
        "warnings",
    ):
        assert field in data
    assert data["platform"] == "X/Twitter"
    assert data["account_handle"] == "example"
    assert data["status_id"] == "1877644315867963403"
    assert data["source_role_candidate"] == "PRIMARY_ORIGINAL_AUTHORED_SOURCE_FOR_POST_TEXT_ONLY"
    assert data["final_source_role_decision"] is False
    assert data["claim_subject_affiliation_review"]["claim_subject_affiliation_gap"] is True
    assert data["social_media_video_provenance_review"]["platform_logo_or_watermark_proves_claim_affiliation"] is False
    assert data["no_write_actions"] is True
    assert data["official_x_api_used"] is False
    assert data["credential_automation_performed"] is False
    summary = render_profile_media_provenance_summary(record)
    assert "final_source_role_decision: False" in summary


def test_missing_post_text_stays_review_required() -> None:
    record = build_twitter_profile_media_provenance(source_url="https://x.com/example/with_replies")
    data = record.to_dict()
    assert data["source_role_candidate"] == "REVIEW_REQUIRED_SOURCE_ROLE_CANDIDATE"
    assert data["final_source_role_decision"] is False
    assert data["account_handle"] == "example"
    assert data["post_id"] == ""


if __name__ == "__main__":
    test_profile_media_provenance_has_v76p_required_fields()
    test_missing_post_text_stays_review_required()
    print("twitter_capture_profile_media_provenance_test: PASS")
