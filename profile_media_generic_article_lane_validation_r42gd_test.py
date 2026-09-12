import json
import subprocess
import sys
import tempfile
from pathlib import Path

from profile_media_generic_article_lane_validation_r42gd import (
    PLATFORM_EXCLUSION_SAMPLE_URLS,
    SIDE_EFFECT_BOUNDARY,
    STATUS_MATERIAL_RECEIPT_REQUIRED,
    STATUS_NOT_TESTED,
    STATUS_TESTED_TRUE,
    build_facet_states,
    build_offline_article_fixture_html,
    parse_offline_article_html,
    validate_generic_article_lane,
    write_report,
)


def _facet(report, name):
    for state in report.facet_states:
        if state.facet == name:
            return state
    raise AssertionError(f"missing facet: {name}")


def _record(records, needle):
    for record in records:
        if needle in record.input_url:
            return record
    raise AssertionError(f"missing record containing {needle}")


def run_self_test() -> None:
    html = build_offline_article_fixture_html()
    article = parse_offline_article_html(
        html,
        source_url="https://metro.co.uk/2026/09/12/example-public-article-12345678/",
    )
    assert article.title == "R42GD Example Public Article"
    assert article.byline == "Example Reporter"
    assert article.published_date == "2026-09-12T00:00:00Z"
    assert article.canonical_url == "https://metro.co.uk/2026/09/12/example-public-article-12345678/"
    assert "normal article text available for review" in article.main_text
    assert article.image_urls == ("https://metro.co.uk/example-image.jpg",)
    assert article.outbound_links == ("https://example.test/source-document",)
    assert article.side_effects == SIDE_EFFECT_BOUNDARY

    states = {state.facet: state for state in build_facet_states(article)}
    assert states["title"].status == STATUS_TESTED_TRUE
    assert states["byline"].status == STATUS_TESTED_TRUE
    assert states["published_date"].status == STATUS_TESTED_TRUE
    assert states["canonical_url"].status == STATUS_TESTED_TRUE
    assert states["article_text"].status == STATUS_TESTED_TRUE
    assert states["screenshot"].status == STATUS_NOT_TESTED
    assert states["warc"].status == STATUS_NOT_TESTED
    assert states["archive_lookup"].status == STATUS_NOT_TESTED
    assert states["source_role_material"].status == STATUS_MATERIAL_RECEIPT_REQUIRED
    assert states["comments"].status == STATUS_NOT_TESTED

    report = validate_generic_article_lane(Path(__file__).resolve().parent)
    assert report.passed, json.dumps(report.to_dict(), indent=2)
    assert report.side_effects == SIDE_EFFECT_BOUNDARY
    assert _facet(report, "comments").status == STATUS_NOT_TESTED
    assert _facet(report, "screenshot").status == STATUS_NOT_TESTED
    assert _facet(report, "archive_lookup").status == STATUS_NOT_TESTED
    assert _facet(report, "source_role_material").status == STATUS_MATERIAL_RECEIPT_REQUIRED

    assert report.generic_article_urls
    assert all(record.family_id == "generic_article" and record.supported for record in report.generic_article_urls), [
        record.to_dict() for record in report.generic_article_urls
    ]
    assert len(report.platform_exclusions) == len(PLATFORM_EXCLUSION_SAMPLE_URLS)
    assert all(not (record.family_id == "generic_article" and record.supported) for record in report.platform_exclusions), [
        record.to_dict() for record in report.platform_exclusions
    ]
    assert _record(report.platform_exclusions, "bbc.co.uk/programmes").family_id == "bbc_sounds"
    assert _record(report.platform_exclusions, "x.com").family_id == "twitter_x"
    assert _record(report.platform_exclusions, "instagram.com").family_id == "instagram"
    assert _record(report.platform_exclusions, "youtube.com").family_id == "youtube"
    assert _record(report.platform_exclusions, "spotify.com/track").supported is False
    assert _record(report.platform_exclusions, ".mp4").family_id == "generic_webpage_media"
    assert _record(report.platform_exclusions, "web.archive.org").family_id == "archive_wayback"
    assert _record(report.platform_exclusions, "archive.ph").family_id == "archive_today"

    with tempfile.TemporaryDirectory() as temp_dir:
        output_root = Path(temp_dir) / "r42gd_report"
        json_path, md_path = write_report(report, output_root)
        assert json_path.is_file()
        assert md_path.is_file()
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["passed"] is True
        assert "R42GD" in md_path.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as temp_dir:
        output_root = Path(temp_dir) / "r42gd_cli"
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "profile_media_generic_article_lane_validation_r42gd.py"),
                "--source-root",
                str(Path(__file__).resolve().parent),
                "--output-root",
                str(output_root),
                "--url",
                "https://example.com/2026/09/12/another-ordinary-article",
                "--url",
                "https://www.bbc.co.uk/news/articles/example-news-item",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert "R42GD generic article/webpage lane validation" in completed.stdout
        assert "Passed: true" in completed.stdout
        assert "GENERIC: https://example.com/2026/09/12/another-ordinary-article -> family=generic_article" in completed.stdout
        assert "GENERIC: https://www.bbc.co.uk/news/articles/example-news-item -> family=generic_article" in completed.stdout
        assert (output_root / "r42gd_generic_article_webpage_lane_validation.json").is_file()
        assert (output_root / "r42gd_generic_article_webpage_lane_validation.md").is_file()


if __name__ == "__main__":
    run_self_test()
    print("profile_media_generic_article_lane_validation_r42gd_test OK")
