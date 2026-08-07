from __future__ import annotations

import tempfile
from pathlib import Path

from source_artifact_collection import SourceArtifactInput, build_source_artifact_collection, parse_artifact_spec


def test_builds_collection_from_explicit_files_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article = root / "article.html"
        metadata = root / "metadata.json"
        article.write_text("<h1>Title</h1><p>Body</p>", encoding="utf-8")
        metadata.write_text('{"source":"fixture"}', encoding="utf-8")
        collection = build_source_artifact_collection(
            adapter_id="news-site",
            source_url="https://news.example/story/1",
            artifacts=[
                SourceArtifactInput("article_html_or_text", article),
                SourceArtifactInput("metadata_json", metadata),
            ],
            capture_job={"capture_job_id": "job.123", "live_network_default": False},
        )
        assert collection["schema_version"] == "source_artifact_collection_v1"
        assert collection["collection_status"] == "READY_FOR_EXTRACTION"
        assert collection["artifact_count"] == 2
        assert collection["artifacts"][0]["filename"] == "article.html"
        assert not collection["artifacts"][0]["source_path_recorded"]
        assert collection["safety"]["network_fetch_performed"] is False


def test_reports_missing_required_roles() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "article.txt"
        path.write_text("Article text", encoding="utf-8")
        collection = build_source_artifact_collection(
            adapter_id="adapter",
            source_url="https://example.com/a",
            artifacts=[SourceArtifactInput("article_html_or_text", path)],
        )
        assert collection["collection_status"] == "NEEDS_REQUIRED_ARTIFACTS"
        assert collection["missing_required_roles"] == ["metadata_json"]


def test_parse_artifact_spec() -> None:
    parsed = parse_artifact_spec("metadata_json=C:/tmp/metadata.json")
    assert parsed.role == "metadata_json"
    assert parsed.path.name == "metadata.json"


def main() -> None:
    test_builds_collection_from_explicit_files_only()
    test_reports_missing_required_roles()
    test_parse_artifact_spec()
    print("Source artifact collection self-test passed.")


if __name__ == "__main__":
    main()
