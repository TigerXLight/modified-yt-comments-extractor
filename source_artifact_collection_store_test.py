from __future__ import annotations

import tempfile
from pathlib import Path

from source_artifact_collection import SourceArtifactInput, build_source_artifact_collection
from source_artifact_collection_store import store_source_artifact_collection


def test_store_writes_collection_ledger_and_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.txt"
        metadata = root / "metadata.json"
        article.write_text("Article", encoding="utf-8")
        metadata.write_text("{}", encoding="utf-8")
        collection = build_source_artifact_collection(
            adapter_id="adapter",
            source_url="https://example.com/story",
            artifacts=[SourceArtifactInput("article_html_or_text", article), SourceArtifactInput("metadata_json", metadata)],
        )
        receipt = store_source_artifact_collection(collection, root / "out")
        assert receipt["schema_version"] == "source_artifact_collection_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 3
        assert receipt["verification"]["verified"] is True
        for stored in receipt["stored_files"]:
            assert (root / "out" / stored["filename"]).is_file()
            assert stored["byte_count"] > 0
            assert len(stored["sha256"]) == 64


def main() -> None:
    test_store_writes_collection_ledger_and_handoff()
    print("Source artifact collection store self-test passed.")


if __name__ == "__main__":
    main()
