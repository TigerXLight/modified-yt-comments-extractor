from __future__ import annotations

import tempfile
from pathlib import Path

from capture_msn_manual_article_extraction import extract_msn_manual_article
from capture_msn_manual_capture_bundle import build_msn_manual_capture_bundle
from capture_msn_manual_comments_extraction import extract_msn_manual_comments
from capture_msn_manual_total_export_package_store import msn_manual_total_export_package_store_result_to_json, store_msn_manual_total_export_package


def test_store_writes_manifest_article_comments_and_packet_without_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        article = extract_msn_manual_article(
            source_url="https://www.msn.com/en-gb/news/example/story-id",
            artifact_text="Headline\nArticle text body with enough copied content for review.",
            artifact_file_name="article.txt",
        )
        comments = extract_msn_manual_comments(
            source_url="https://www.msn.com/en-gb/news/example/story-id",
            artifact_text="Alice: First comment",
            artifact_file_name="comments.txt",
        )
        bundle = build_msn_manual_capture_bundle(article=article, comments=comments)
        result = store_msn_manual_total_export_package(output_dir=Path(tmp), bundle=bundle, package_id="msn_total_export_example")
        names = {file.file_name for file in result.files}
        assert "page_capture/msn_total_export_example_article_text.txt" in names
        assert "metadata/msn_total_export_example_comments.json" in names
        assert "metadata/msn_total_export_example_manifest.json" in names
        assert "metadata/msn_total_export_example_msn_manual_total_export_packet.json" in names
        assert (Path(tmp) / "page_capture" / "msn_total_export_example_article_text.txt").read_text(encoding="utf-8") == "Article text body with enough copied content for review."
        assert str(tmp) not in msn_manual_total_export_package_store_result_to_json(result)


if __name__ == "__main__":
    test_store_writes_manifest_article_comments_and_packet_without_paths()
    print("MSN manual Total Export package store self-test passed.")
