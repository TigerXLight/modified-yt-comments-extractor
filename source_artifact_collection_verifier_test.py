from __future__ import annotations

import tempfile
from pathlib import Path

from source_artifact_collection import SourceArtifactInput, build_source_artifact_collection
from source_artifact_collection_verifier import verify_source_artifact_collection


def test_verifier_accepts_safe_collection() -> None:
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
        verification = verify_source_artifact_collection(collection)
        assert verification["verified"] is True
        assert verification["issue_count"] == 0


def test_verifier_rejects_path_serialization() -> None:
    bad = {
        "schema_version": "source_artifact_collection_v1",
        "collection_id": "source_artifacts.bad",
        "adapter_id": "adapter",
        "source_url": "https://example.com/story",
        "collection_status": "READY_FOR_EXTRACTION",
        "artifacts": [
            {"role": "metadata_json", "filename": "C:/tmp/metadata.json", "byte_count": 1, "sha256": "0" * 64, "source_path_recorded": True}
        ],
        "safety": {"explicit_files_only": True},
    }
    verification = verify_source_artifact_collection(bad)
    assert verification["verified"] is False
    assert verification["issue_count"] >= 1


def main() -> None:
    test_verifier_accepts_safe_collection()
    test_verifier_rejects_path_serialization()
    print("Source artifact collection verifier self-test passed.")


if __name__ == "__main__":
    main()
