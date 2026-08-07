from pathlib import Path
from tempfile import TemporaryDirectory

from source_content_extraction import SourceContentArtifact, build_source_content_extraction, build_source_content_extraction_from_collection


def test_extracts_html_title_and_body_without_full_paths() -> None:
    with TemporaryDirectory() as td:
        p = Path(td) / "article.html"
        p.write_text("<html><title>Browser title</title><article><h1>Main title</h1><p>First paragraph.</p><p>Second paragraph.</p></article></html>", encoding="utf-8")
        extraction = build_source_content_extraction(
            adapter_id="example_news",
            source_url="https://example.com/story/1",
            artifacts=[SourceContentArtifact(role="article_html_or_text", path=str(p))],
        )
    assert extraction["schema_version"] == "source_content_extraction_v1"
    assert extraction["title"] == "Main title"
    assert extraction["body_paragraph_count"] >= 2
    assert extraction["selected_artifact"]["filename"] == "article.html"
    assert td not in str(extraction)
    assert extraction["operator_summary"]["live_network_used"] is False


def test_builds_from_collection_payload_with_relative_artifact() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "saved.txt").write_text("Plain title\nParagraph one.\nParagraph two.", encoding="utf-8")
        collection = root / "collection.json"
        collection.write_text(
            '{"adapter_id":"plain","source_url":"https://plain.example/a","artifacts":[{"role":"article_text","path":"saved.txt"}]}',
            encoding="utf-8",
        )
        extraction = build_source_content_extraction_from_collection(artifact_collection_path=collection)
    assert extraction["adapter_id"] == "plain"
    assert extraction["title"] == "Plain title"
    assert extraction["body_sha256"]
    assert extraction["extraction_handoff"]["next_stage"] == "source_comment_extraction_or_capture_bundle"


if __name__ == "__main__":
    test_extracts_html_title_and_body_without_full_paths()
    test_builds_from_collection_payload_with_relative_artifact()
    print("Source content extraction self-test passed.")
