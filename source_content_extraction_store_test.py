from pathlib import Path
from tempfile import TemporaryDirectory

from source_content_extraction import SourceContentArtifact, build_source_content_extraction
from source_content_extraction_store import write_source_content_extraction_store


def test_store_writes_three_files_with_hashes() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        artifact = root / "article.txt"
        artifact.write_text("Title\nBody text.", encoding="utf-8")
        extraction = build_source_content_extraction(
            adapter_id="store_adapter",
            source_url="https://store.example/item",
            artifacts=[SourceContentArtifact("article_text", str(artifact))],
        )
        result = write_source_content_extraction_store(extraction, root / "out")
        assert result["schema_version"] == "source_content_extraction_store_v1"
        assert result["output_file_count"] == 3
        for item in result["stored_files"]:
            assert (root / "out" / item["filename"]).exists()
            assert item["sha256"]
            assert item["byte_count"] > 0


if __name__ == "__main__":
    test_store_writes_three_files_with_hashes()
    print("Source content extraction store self-test passed.")
