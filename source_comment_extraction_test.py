from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_comment_extraction import SourceCommentArtifact, build_source_comment_extraction, build_source_comment_extraction_from_collection, extract_comments_from_artifact_text


def test_extracts_json_replies() -> None:
    raw = json.dumps({"comments": [{"id": "c1", "author": {"name": "Amina"}, "text": "First comment", "replies": [{"id": "r1", "user": "Bilal", "message": "Reply text"}]}]})
    comments, method, warnings = extract_comments_from_artifact_text(raw)
    assert method == "shared_json_or_ndjson_comment_fields"
    assert warnings == []
    assert len(comments) == 2
    assert comments[1].parent_id == "c1"
    assert comments[1].depth == 1


def test_extracts_plain_text_comments() -> None:
    comments, method, _warnings = extract_comments_from_artifact_text("Amina: First\n\nBilal: Second")
    assert method == "shared_plain_text_comment_heuristic"
    assert [comment.author for comment in comments] == ["Amina", "Bilal"]
    assert [comment.text for comment in comments] == ["First", "Second"]


def test_builds_from_explicit_artifact_without_full_path_serialization() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        artifact = base / "comments.json"
        artifact.write_text(json.dumps([{"id": "c1", "author": "Nadia", "body": "A useful comment"}]), encoding="utf-8")
        extraction = build_source_comment_extraction(
            adapter_id="example_news",
            source_url="https://example.com/story",
            artifacts=[SourceCommentArtifact(role="comments_json_or_text", path="comments.json")],
            base_dir=base,
        )
        assert extraction["schema_version"] == "source_comment_extraction_v1"
        assert extraction["comment_count"] == 1
        assert extraction["selected_artifact"]["filename"] == "comments.json"
        assert str(base) not in json.dumps(extraction)
        assert extraction["operator_summary"]["live_network_used"] is False


def test_builds_from_collection_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "comments.ndjson").write_text('{"id":"c1","user":"One","text":"Hello"}\n{"id":"c2","user":"Two","text":"World"}\n', encoding="utf-8")
        manifest = base / "collection.json"
        manifest.write_text(
            json.dumps(
                {
                    "adapter_id": "adapter",
                    "source_url": "https://example.com/a",
                    "artifacts": [{"role": "comments_json_or_text", "path": "comments.ndjson"}],
                }
            ),
            encoding="utf-8",
        )
        extraction = build_source_comment_extraction_from_collection(artifact_collection_path=manifest)
        assert extraction["comment_count"] == 2
        assert extraction["extraction_handoff"]["next_stage"] == "source_capture_bundle_or_total_export_package"


if __name__ == "__main__":
    test_extracts_json_replies()
    test_extracts_plain_text_comments()
    test_builds_from_explicit_artifact_without_full_path_serialization()
    test_builds_from_collection_manifest()
    print("Source comment extraction self-test passed.")
