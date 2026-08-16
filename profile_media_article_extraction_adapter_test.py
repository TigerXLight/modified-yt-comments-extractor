from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_article_extraction_adapter import (
    WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW,
    extract_article_from_file,
    extract_article_from_html,
    render_article_extraction_text,
    write_article_source_preview,
)

SAMPLE_HTML = """<!doctype html>
<html>
<head>
<title>Fallback title should lose</title>
<link rel="canonical" href="https://example.test/news/2026/jun/21/example-case" />
<meta property="og:title" content="21 Jun - Example article folder - White" />
<meta property="og:site_name" content="Belfast Telegraph" />
<meta name="author" content="Reporter Name" />
<meta property="article:published_time" content="2026-06-21T10:00:00Z" />
<meta name="description" content="A structural extraction smoke article." />
<meta property="og:image" content="https://example.test/images/person.jpg" />
</head>
<body>
<article>
<h1>21 Jun - Example article folder - White</h1>
<p>Police said the report repeated a court claim about the incident.</p>
<p>A witness told the newspaper that they saw part of the event.</p>
<p><a href="/source-document">source document</a></p>
</article>
</body>
</html>"""


def test_extract_article_from_html_uses_structural_fallback_without_network() -> None:
    result = extract_article_from_html(
        SAMPLE_HTML,
        source_url="https://example.test/news/2026/jun/21/example-case",
        extractor_order=("stdlib_html",),
    )
    payload = result.to_dict()
    assert result.status == "success"
    assert result.title == "21 Jun - Example article folder - White"
    assert result.site_name == "Belfast Telegraph"
    assert result.byline == "Reporter Name"
    assert result.published_date == "2026-06-21T10:00:00Z"
    assert result.canonical_url == "https://example.test/news/2026/jun/21/example-case"
    assert "Police said" in result.main_text
    assert "court_or_legal_claim" in result.attribution_markings
    assert "police_or_authority_claim" in result.attribution_markings
    assert "contains_propagated_or_authority_claim_language" in result.source_basis_candidates
    assert "claim_subject_affiliation_review" in result.review_lanes
    assert result.source_role_candidate == "SECONDARY_WITNESS_ACCOUNT" or result.source_role_candidate == "REVIEW_REQUIRED"
    assert result.source_role_is_final is False
    assert payload["folder_scan_performed"] is False
    assert payload["web_download_performed"] is False
    assert payload["crawling_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False


def test_extract_article_from_file_and_guarded_write_preview() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "article.html"
        output_path = Path(tmp) / "source_preview.json"
        html_path.write_text(SAMPLE_HTML, encoding="utf-8")
        result = extract_article_from_file(html_path, source_url="https://example.test/article", extractor_order=("stdlib_html",))
        blocked = write_article_source_preview(result, output_path, confirmation="WRONG")
        assert blocked["status"] == "blocked_confirmation_required"
        assert blocked["file_write_performed"] is False
        assert not output_path.exists()
        written = write_article_source_preview(result, output_path, confirmation=WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW)
        assert written["status"] == "source_preview_written"
        assert written["file_write_performed"] is True
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["source_title"] == "21 Jun - Example article folder - White"
        assert payload["source_bucket"] == "Articles"
        assert payload["source_role"] == "UNKNOWN_SOURCE_ROLE"
        assert payload["source_role_is_final"] is False
        assert payload["media_download_performed"] is False


def test_optional_reference_order_skips_missing_without_failing() -> None:
    result = extract_article_from_html(
        SAMPLE_HTML,
        source_url="https://example.test/article",
        reference_root="Z:/definitely/not/here",
    )
    runs = {run.extractor_name: run.status for run in result.extractor_runs}
    assert runs["stdlib_html"] == "success"
    assert result.title == "21 Jun - Example article folder - White"
    text = render_article_extraction_text(result)
    assert "Profile/Media Article Extraction Adapter" in text
    assert "Web download performed: False" in text
    assert "Automatic classification performed: False" in text


if __name__ == "__main__":
    test_extract_article_from_html_uses_structural_fallback_without_network()
    test_extract_article_from_file_and_guarded_write_preview()
    test_optional_reference_order_skips_missing_without_failing()
    print("profile_media_article_extraction_adapter v76l OK")
