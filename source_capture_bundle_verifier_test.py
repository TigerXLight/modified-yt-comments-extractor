from __future__ import annotations

from source_capture_bundle import build_source_capture_bundle
from source_capture_bundle_verifier import verify_source_capture_bundle


def test_verify_source_capture_bundle() -> None:
    outputs = build_source_capture_bundle(
        content_extraction={"content_extraction_id": "content.1", "adapter_id": "example", "title": "Title"}
    )
    result = verify_source_capture_bundle(outputs.capture_bundle)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verify_rejects_bad_schema() -> None:
    result = verify_source_capture_bundle({"schema_version": "wrong"})
    assert result["verified"] is False
    assert result["issue_count"] >= 1


if __name__ == "__main__":
    test_verify_source_capture_bundle()
    test_verify_rejects_bad_schema()
    print("Source capture bundle verifier self-test passed.")
