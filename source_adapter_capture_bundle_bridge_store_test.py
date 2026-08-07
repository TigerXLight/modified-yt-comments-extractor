from __future__ import annotations


def fixture_extraction_bridge() -> dict:
    return {
        "extraction_bridge_status": "SHARED_EXTRACTIONS_PREPARED",
        "source_adapter_extraction_bridge_id": "source_adapter_extraction_bridge.example",
        "source_adapter_capture_bundle_handoff": {"handoff_status": "READY_FOR_SHARED_CAPTURE_BUNDLE"},
        "content_extractions": [
            {
                "adapter_id": "article",
                "source_url": "https://article.example/story",
                "content_id": "article.content.1234",
                "title": "Bridge title",
                "body_text": "Bridge body.",
                "body_sha256": "b" * 64,
                "body_paragraph_count": 1,
            }
        ],
        "comment_extractions": [
            {
                "adapter_id": "article",
                "source_url": "https://article.example/story",
                "comment_extraction_id": "article.comments.1234",
                "comment_sha256": "c" * 64,
                "comment_count": 1,
                "comments": [{"id": "c1", "author": "Reader", "text": "Bridge comment"}],
            }
        ],
        "extraction_routes": [
            {
                "adapter_id": "article",
                "source_url": "https://article.example/story",
                "collection_id": "article.collection.1234",
                "artifacts": [
                    {"role": "article_html_or_text", "filename": "article.html", "byte_count": 32, "sha256": "a" * 64},
                    {"role": "comments_json_or_text", "filename": "comments.json", "byte_count": 16, "sha256": "d" * 64},
                ],
            }
        ],
    }

import tempfile
from pathlib import Path

from source_adapter_capture_bundle_bridge import build_source_adapter_capture_bundle_bridge
from source_adapter_capture_bundle_bridge_store import store_source_adapter_capture_bundle_bridge


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        package = build_source_adapter_capture_bundle_bridge(fixture_extraction_bridge())
        receipt = store_source_adapter_capture_bundle_bridge(package, Path(tmp))
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 5
        assert receipt["verification"]["verified"] is True
        assert len(list(Path(tmp).glob("*.json"))) == 5


if __name__ == "__main__":
    main()
    print("Source Adapter Capture Bundle Bridge store self-test passed.")
