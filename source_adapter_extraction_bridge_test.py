from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from source_adapter_extraction_bridge import EXTRACTION_BRIDGE_STATUS, build_source_adapter_extraction_bridge


def _fixture(tmp_path: Path) -> tuple[dict, list[dict]]:
    article = tmp_path / "article.html"
    comments = tmp_path / "comments.json"
    article.write_bytes(b"<html><h1>Bridge title</h1><article><p>Bridge body.</p></article></html>")
    comments.write_bytes(b'[{"id":"c1","author":"Reader","text":"Bridge comment"}]')
    intake = {
        "artifact_intake_status": "ARTIFACT_FILES_VALIDATED",
        "source_adapter_artifact_intake_id": "source_adapter_artifact_intake.example",
        "source_artifact_collection_handoff": {"handoff_status": "READY_FOR_SHARED_EXTRACTION"},
        "source_artifact_collections": [
            {
                "collection_id": "source_artifacts.example",
                "adapter_id": "article",
                "source_url": "https://article.example/story",
                "collection_status": "READY_FOR_EXTRACTION",
                "artifacts": [
                    {"role": "article_html_or_text", "filename": "article.html", "byte_count": article.stat().st_size, "sha256": hashlib.sha256(article.read_bytes()).hexdigest(), "content_kind": "text"},
                    {"role": "comments_json_or_text", "filename": "comments.json", "byte_count": comments.stat().st_size, "sha256": hashlib.sha256(comments.read_bytes()).hexdigest(), "content_kind": "text"},
                ],
            }
        ],
    }
    bindings = [
        {"adapter_id": "article", "artifact_role": "article_html_or_text", "artifact_basename": "article.html", "path": str(article)},
        {"adapter_id": "article", "artifact_role": "comments_json_or_text", "artifact_basename": "comments.json", "path": str(comments)},
    ]
    return intake, bindings


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        intake, bindings = _fixture(Path(tmp))
        package = build_source_adapter_extraction_bridge(intake, bindings)
        assert package["extraction_bridge_status"] == EXTRACTION_BRIDGE_STATUS
        assert package["content_extraction_count"] == 1
        assert package["comment_extraction_count"] == 1
        assert package["content_extractions"][0]["title"] == "Bridge title"
        assert package["comment_extractions"][0]["comment_count"] == 1
        assert package["source_adapter_capture_bundle_handoff"]["ready_for_shared_capture_bundle"] is True
        assert package["safety_contract"]["network_fetch_performed"] is False
        assert package["extraction_routes"][0]["artifacts"][0]["full_path_serialized"] is False


if __name__ == "__main__":
    main()
    print("Source Adapter Extraction Bridge self-test passed.")
