from __future__ import annotations

from tempfile import TemporaryDirectory

from source_capture_bundle import build_source_capture_bundle
from source_capture_bundle_store import store_source_capture_bundle


def test_store_source_capture_bundle() -> None:
    outputs = build_source_capture_bundle(
        content_extraction={
            "content_extraction_id": "content.1",
            "adapter_id": "example",
            "title": "Stored article",
            "body_text": "Stored body.",
        },
        comment_extraction={"comment_extraction_id": "comments.1", "comment_count": 0},
    )
    with TemporaryDirectory() as tmpdir:
        receipt = store_source_capture_bundle(outputs.as_dict(), tmpdir)
        assert receipt["schema_version"] == "source_capture_bundle_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 4
        assert receipt["verification"]["verified"] is True
        for item in receipt["stored_files"]:
            assert item["byte_count"] > 0
            assert len(item["sha256"]) == 64


if __name__ == "__main__":
    test_store_source_capture_bundle()
    print("Source capture bundle store self-test passed.")
