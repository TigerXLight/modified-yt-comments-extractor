from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_home_source_folder_ingestion import (
    WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW,
    build_home_source_folder_evaluation_preview,
    render_home_source_folder_evaluation_text,
    write_home_source_folder_evaluation_preview,
)
from profile_media_nested_source_units_v77b import (
    discover_nested_source_units,
    discover_source_unit_paths,
    extract_clean_text_from_rtf_v77b,
    parse_source_txt_fields,
)


FIXTURE_ROOT = Path("testdata/profile_media_database_v77b_gb_news_nested_case/GB NEWS")
EXPECTED_TITLE = "Disgraced Donaldson told Arlene Foster on GB News ‘his faith influenced how he treated others’"
EXPECTED_PROGRAMME = "Faiths of the Nation with Arlene Foster | Monday 25th December / GBNews / YouTube"


def test_case_root_detection_and_unit_deduplication() -> None:
    units = discover_source_unit_paths(FIXTURE_ROOT)
    assert len(units) == 3
    lowered = [str(path).lower() for path in units]
    assert len(lowered) == len(set(lowered))
    assert any(str(path).endswith(r"Sources\Articles\June 2026\Belfast Telegraph\24 June") for path in units)
    assert any("PressReader" in str(path) for path in units)
    assert any("Faiths of the Nation with Arlene Foster" in str(path) for path in units)


def test_rtf_cleanup_and_main_article_selection() -> None:
    article = FIXTURE_ROOT / "Sources/Articles/June 2026/Belfast Telegraph/24 June/Article.rtf"
    clean = extract_clean_text_from_rtf_v77b(article.read_text(encoding="utf-8"))
    assert EXPECTED_TITLE in clean
    assert "fonttbl" not in clean.lower()
    discovery = discover_nested_source_units(FIXTURE_ROOT)
    payload = discovery.to_dict()
    primary = payload["primary_article_source_unit"]
    assert payload["case_root_detected"] is True
    assert primary["relative_path"].endswith("Sources/Articles/June 2026/Belfast Telegraph/24 June")
    assert primary["selected_main_article_file"].endswith("Article.rtf")
    assert primary["title"] == EXPECTED_TITLE
    assert primary["deck"].startswith("Child rapist presented himself")


def test_pressreader_is_repost_not_main_title_source() -> None:
    discovery = discover_nested_source_units(FIXTURE_ROOT).to_dict()
    reposts = discovery["repost_source_units"]
    assert len(reposts) == 1
    repost = reposts[0]
    assert repost["source_unit_kind"] == "repost_copy_source_unit"
    assert "PressReader" in repost["relative_path"]
    assert repost["title"] == ""
    assert discovery["primary_article_source_unit"]["title"] == EXPECTED_TITLE


def test_youtube_source_txt_fields_and_role_axes() -> None:
    source_txt = FIXTURE_ROOT / "Sources/Social Media/Online/YouTube/December 2023/25 December/Faiths of the Nation with Arlene Foster/Source.txt"
    fields = parse_source_txt_fields(source_txt.read_text(encoding="utf-8"))
    assert fields["title"] == "Faiths of the Nation with Arlene Foster | Monday 25th December"
    assert fields["channel"] == "GBNews"
    assert fields["source"] == "https://www.youtube.com/live/3o_O62la07k?si=tMNUG9USK1Kcvnov"
    assert "Belfast Telegraph" in fields["used as a reference in"]
    assert "Christian faith" in fields["text"]
    discovery = discover_nested_source_units(FIXTURE_ROOT).to_dict()
    social = discovery["social_video_source_units"][0]
    assert social["uploader_account_candidate"] == "GBNews"
    assert social["original_programme_source_candidate"] == EXPECTED_PROGRAMME
    axes = social["role_axes"]
    assert axes["personhood_or_witness_verification_role_candidate"] == "SECONDARY_WITNESS_OR_PERSONHOOD_VERIFICATION_REVIEW"
    assert axes["media_source_role_candidate"] == "PRIMARY_MEDIA_SOURCE_CAPTURED_OR_PUBLISHED_BY_GBNEWS"
    assert axes["speaker_statement_role_candidate"] == "DIRECT_INTERVIEW_STATEMENT_CAPTURED_IN_BROADCAST_REVIEW"
    assert axes["case_claim_role_is_final"] is False


def test_transcripts_and_captions_are_not_article_files() -> None:
    discovery = discover_nested_source_units(FIXTURE_ROOT).to_dict()
    social = discovery["social_video_source_units"][0]
    assert social["article_files"] == []
    assert len(social["transcript_references"]) == 1
    assert len(social["subtitle_or_caption_references"]) == 1
    assert len(social["video_description_references"]) == 1
    assert "transcript.txt" in social["transcript_references"][0]["relative_path"]
    assert social["subtitle_or_caption_references"][0]["relative_path"].endswith("captions.srt")
    assert "Evangelical Christian faith" in social["transcript_support_matches"]
    assert "influenced the way that I interact with others" in social["transcript_support_matches"]
    assert "Faith goes to your very being" in social["transcript_support_matches"]


def test_home_preview_preserves_nested_fields_and_safety_flags() -> None:
    preview = build_home_source_folder_evaluation_preview(FIXTURE_ROOT, extractor_order=("stdlib_html",))
    payload = preview.to_dict()
    assert payload["case_root_detected"] is True
    assert len(payload["source_units"]) == 3
    assert payload["extracted_article_preview"]["title"] == EXPECTED_TITLE
    assert payload["primary_article_source_unit"]["title"] == EXPECTED_TITLE
    assert len(payload["repost_source_units"]) == 1
    assert len(payload["social_video_source_units"]) == 1
    assert len(payload["transcript_references"]) == 1
    assert len(payload["subtitle_or_caption_references"]) == 1
    assert payload["role_axes"]
    assert payload["web_download_performed"] is False
    assert payload["crawling_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["final_source_role_decision"] is False


def test_cli_text_summary_fields_and_confirmed_write() -> None:
    preview = build_home_source_folder_evaluation_preview(FIXTURE_ROOT, extractor_order=("stdlib_html",))
    text = render_home_source_folder_evaluation_text(preview)
    assert "case_root_detected: True" in text
    assert "source_units: 3" in text
    assert EXPECTED_TITLE in text
    assert "PressReader" in text
    assert "Faiths of the Nation with Arlene Foster" in text
    assert "uploader/account candidate: GBNews" in text
    assert "PRIMARY_MEDIA_SOURCE_CAPTURED_OR_PUBLISHED_BY_GBNEWS" in text
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "preview.json"
        blocked = write_home_source_folder_evaluation_preview(preview, output, confirm_write="WRONG")
        assert blocked["file_write_performed"] is False
        assert not output.exists()
        written = write_home_source_folder_evaluation_preview(
            preview,
            output,
            confirm_write=WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW,
        )
        assert written["file_write_performed"] is True
        assert output.exists()


if __name__ == "__main__":
    test_case_root_detection_and_unit_deduplication()
    test_rtf_cleanup_and_main_article_selection()
    test_pressreader_is_repost_not_main_title_source()
    test_youtube_source_txt_fields_and_role_axes()
    test_transcripts_and_captions_are_not_article_files()
    test_home_preview_preserves_nested_fields_and_safety_flags()
    test_cli_text_summary_fields_and_confirmed_write()
    print("profile_media_nested_source_units_v77b OK")
