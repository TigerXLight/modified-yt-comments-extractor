from __future__ import annotations

from profile_media_social_video_provenance import build_social_video_provenance_review


def test_social_video_provenance_separates_fields_without_downloads() -> None:
    review = build_social_video_provenance_review(
        """
        Source URL: https://www.youtube.com/watch?v=abc123
        Archive URL: https://web.archive.org/web/20260816090000/https://www.youtube.com/watch?v=abc123
        Uploader/account: Clash Report
        Speaker: Example minister
        Original programme: Example Channel News
        Clip holder: Local archive folder
        Transcripted statement: I received the clip from a public post.
        Watermark: YouTube
        """
    )
    payload = review.to_dict()
    assert payload["uploader_account"] == "Clash Report"
    assert payload["speaker"] == "Example minister"
    assert payload["original_programme_channel_source"] == "Example Channel News"
    assert payload["clip_holder"] == "Local archive folder"
    assert payload["archive_url"].startswith("https://web.archive.org/")
    assert payload["source_url"].startswith("https://www.youtube.com/")
    assert payload["platform_logo_or_watermark"] == "YouTube"
    assert payload["web_download_performed"] is False
    assert payload["media_download_performed"] is False


def test_logo_or_watermark_does_not_prove_claim_affiliation() -> None:
    review = build_social_video_provenance_review("Watermark: Clash Report\nhttps://x.com/example/status/1")
    payload = review.to_dict()
    assert payload["platform_marker_only"] is True
    assert payload["claim_subject_affiliation_gap"] is True
    assert "platform_logo_or_watermark_is_not_claim_affiliation" in payload["warnings"]
    assert "claim_subject_affiliation_review" in payload["review_lanes"]


def test_explicit_affiliation_can_clear_gap_but_not_finalize_role() -> None:
    review = build_social_video_provenance_review("Source URL: https://x.com/example/status/1\nClaim subject affiliation: yes")
    payload = review.to_dict()
    assert payload["claim_affiliation_proven"] is True
    assert payload["claim_subject_affiliation_gap"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False


if __name__ == "__main__":
    test_social_video_provenance_separates_fields_without_downloads()
    test_logo_or_watermark_does_not_prove_claim_affiliation()
    test_explicit_affiliation_can_clear_gap_but_not_finalize_role()
    print("profile_media_social_video_provenance v76p OK")
