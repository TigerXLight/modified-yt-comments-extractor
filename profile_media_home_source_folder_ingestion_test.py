from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_home_source_folder_ingestion import (
    PROFILE_MEDIA_HOME_SOURCE_FOLDER_INGESTION_SCHEMA_VERSION,
    WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW,
    build_home_source_folder_evaluation_preview,
    extract_plain_text_from_rtf,
    extract_urls_from_text,
    render_home_source_folder_evaluation_text,
    write_home_source_folder_evaluation_preview,
)

FIXTURE = Path("testdata/profile_media_database_v76o_home_source_folder_fixture")


def test_source_txt_url_extraction_and_archive_split() -> None:
    preview = build_home_source_folder_evaluation_preview(FIXTURE, extractor_order=("stdlib_html",))
    payload = preview.to_dict()
    assert payload["schema_version"] == PROFILE_MEDIA_HOME_SOURCE_FOLDER_INGESTION_SCHEMA_VERSION
    assert payload["source_txt_present"] is True
    assert payload["folder_scan_performed"] is True
    assert payload["home_database_scan_performed"] is False
    assert "https://example.test/news/local-court-report" in payload["source_urls"]
    assert "https://web.archive.org/web/20260816090000/https://example.test/news/local-court-report" in payload["archive_urls"]
    assert any("x.com/example/status" in url for url in payload["source_urls"])
    assert any("youtube.com/watch" in url for url in payload["source_urls"])


def test_article_txt_html_rtf_detection_and_preview() -> None:
    preview = build_home_source_folder_evaluation_preview(FIXTURE, extractor_order=("stdlib_html",))
    payload = preview.to_dict()
    assert len(payload["article_files"]) >= 2
    assert len(payload["rtf_files"]) == 1
    assert len(payload["text_files"]) == 1
    assert payload["html_files"] == []
    assert payload["extracted_article_preview"]["status"] == "success"
    assert "14 Jun - 'Shut up you traitorous appeaser. - White" in payload["extracted_article_preview"]["main_text"]
    assert "source_chain_basis_review" in payload["review_lanes"]
    assert "authority_or_court_claim_language_present" in payload["source_basis_candidates"]


def test_rtf_extraction_preserves_readable_text() -> None:
    text = extract_plain_text_from_rtf(r"{\rtf1\ansi I wrote this\par Police said \'a3 okay\par}")
    assert "I wrote this" in text
    assert "Police said" in text
    assert "£" in text


def test_media_and_screenshot_references_are_recorded_only() -> None:
    preview = build_home_source_folder_evaluation_preview(FIXTURE, extractor_order=("stdlib_html",))
    payload = preview.to_dict()
    assert len(payload["screenshot_references"]) == 1
    assert len(payload["media_references"]) == 1
    screenshot = payload["screenshot_references"][0]
    media = payload["media_references"][0]
    assert screenshot["recorded_reference_only"] is True
    assert media["recorded_reference_only"] is True
    assert screenshot["opened_for_text_extraction"] is False
    assert media["opened_for_text_extraction"] is False
    assert payload["media_download_performed"] is False
    assert payload["web_download_performed"] is False
    assert payload["crawling_performed"] is False


def test_review_lanes_keep_source_criticism_non_final() -> None:
    preview = build_home_source_folder_evaluation_preview(FIXTURE, extractor_order=("stdlib_html",))
    payload = preview.to_dict()
    assert payload["final_source_role_decision"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert payload["first_person_author_self_claim_review"]["status"] == "review_required_first_person_scope"
    assert payload["witness_connectivity_review"]["status"] == "review_required_witness_connectivity_not_established"
    assert payload["claim_subject_affiliation_review"]["status"] == "review_required_affiliation_gap"
    assert payload["social_media_video_provenance_review"]["status"] == "review_required_social_media_video_provenance"
    assert payload["source_role_candidate"] == "TERTIARY_PROPAGATED_SOURCE_REVIEW_REQUIRED"
    assert len(payload["source_role_segments"]) >= 2
    first_person_segments = [item for item in payload["source_role_segments"] if item["first_person_author_self_claim_review"]]
    assert first_person_segments
    assert first_person_segments[0]["author_scope_only"] is True
    assert any(item["source_role_candidate"] == "TERTIARY_PROPAGATED_SOURCE_REVIEW_REQUIRED" for item in payload["source_role_segments"])


def test_social_video_provenance_is_included_in_preview() -> None:
    preview = build_home_source_folder_evaluation_preview(FIXTURE, extractor_order=("stdlib_html",))
    payload = preview.to_dict()
    provenance = payload["social_video_provenance"]
    assert provenance["uploader_account"] == "Clash Report"
    assert provenance["speaker"] == "Example speaker"
    assert provenance["original_programme_channel_source"] == "Example Channel News"
    assert provenance["clip_holder"] == "Local source folder"
    assert provenance["source_url"].startswith("https://x.com/") or provenance["source_url"].startswith("https://www.youtube.com/")
    assert provenance["archive_url"].startswith("https://web.archive.org/")
    assert provenance["media_download_performed"] is False


def test_confirmation_token_blocks_and_allows_preview_write() -> None:
    preview = build_home_source_folder_evaluation_preview(FIXTURE, extractor_order=("stdlib_html",))
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "preview.json"
        blocked = write_home_source_folder_evaluation_preview(preview, output, confirm_write="WRONG")
        assert blocked["status"] == "blocked_confirmation_required"
        assert blocked["file_write_performed"] is False
        assert not output.exists()
        written = write_home_source_folder_evaluation_preview(
            preview,
            output,
            confirm_write=WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW,
        )
        assert written["status"] == "home_source_folder_evaluation_preview_written"
        assert written["file_write_performed"] is True
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["file_write_performed"] is True
        assert payload["home_database_scan_performed"] is False
        assert payload["source_txt_present"] is True


def test_text_renderer_and_url_helper_are_deterministic() -> None:
    urls = extract_urls_from_text("See https://example.test/a, and https://x.com/a/status/1")
    assert urls == ("https://example.test/a", "https://x.com/a/status/1")
    preview = build_home_source_folder_evaluation_preview(FIXTURE, extractor_order=("stdlib_html",))
    text = render_home_source_folder_evaluation_text(preview)
    assert "Profile/Media HOME Source Folder Ingestion Preview V76O" in text
    assert "home_database_scan_performed: False" in text
    assert "media_download_performed: False" in text
    assert "first_person_author_self_claim_review" in text
    assert "Source-role segments:" in text


if __name__ == "__main__":
    test_source_txt_url_extraction_and_archive_split()
    test_article_txt_html_rtf_detection_and_preview()
    test_rtf_extraction_preserves_readable_text()
    test_media_and_screenshot_references_are_recorded_only()
    test_review_lanes_keep_source_criticism_non_final()
    test_social_video_provenance_is_included_in_preview()
    test_confirmation_token_blocks_and_allows_preview_write()
    test_text_renderer_and_url_helper_are_deterministic()
    print("profile_media_home_source_folder_ingestion v76o OK")
