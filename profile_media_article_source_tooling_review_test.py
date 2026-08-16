from __future__ import annotations

from profile_media_article_source_tooling_review import (
    build_article_source_tooling_review,
    render_article_source_tooling_review_text,
)


def test_only_structural_extractors_are_included() -> None:
    review = build_article_source_tooling_review()
    names = [item.name for item in review.candidates]
    assert names == ["trafilatura", "newspaper4k", "metadata_parser"]
    assert review.recommended_integration_order == ("metadata_parser", "trafilatura", "newspaper4k")
    assert review.status == "article_extraction_adapter_implemented_extractors_optional"
    assert review.media_download_performed is False
    assert review.automatic_classification_performed is False


def test_benchmark_frameworks_are_excluded_from_product_logic() -> None:
    review = build_article_source_tooling_review()
    excluded = {item.name: item.reason for item in review.excluded_frameworks}
    assert "FEVER" in excluded
    assert "AVeriTeC" in excluded
    assert "MICE multimodal benchmark framing" in excluded
    assert "affiliated with the evaluated claim" in review.image_claim_affiliation_rule
    text = render_article_source_tooling_review_text(review)
    assert "Excluded benchmark/verdict frameworks" in text
    assert "affiliation gap" in text
    assert "V76L adapter implementation" in text


if __name__ == "__main__":
    test_only_structural_extractors_are_included()
    test_benchmark_frameworks_are_excluded_from_product_logic()
    print("profile_media_article_source_tooling_review v76l OK")
