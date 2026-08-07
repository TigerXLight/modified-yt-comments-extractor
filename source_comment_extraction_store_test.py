from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_comment_extraction_store import store_source_comment_extraction


def test_store_writes_expected_files() -> None:
    extraction = {
        "schema_version": "source_comment_extraction_v1",
        "comment_extraction_id": "adapter.comments.abc123",
        "adapter_id": "adapter",
        "source_url": "https://example.com/story",
        "comment_count": 1,
        "comment_sha256": "a" * 64,
        "selected_artifact": {"role": "comments_json_or_text", "filename": "comments.json"},
        "comments": [{"comment_id": "c1", "author": "A", "text": "Hello", "parent_id": "", "depth": 0}],
    }
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_comment_extraction(extraction, tmp)
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 3
        filenames = {item["filename"] for item in receipt["stored_files"]}
        assert "adapter.comments.abc123.comment_extraction.json" in filenames
        assert "adapter.comments.abc123.comment_index.json" in filenames
        assert "adapter.comments.abc123.capture_bundle_handoff.json" in filenames
        for item in receipt["stored_files"]:
            assert len(item["sha256"]) == 64
            assert (Path(tmp) / item["filename"]).exists()


if __name__ == "__main__":
    test_store_writes_expected_files()
    print("Source comment extraction store self-test passed.")
