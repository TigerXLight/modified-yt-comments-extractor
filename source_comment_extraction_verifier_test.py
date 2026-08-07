from __future__ import annotations

from source_comment_extraction_verifier import verify_source_comment_extraction


def test_verifier_accepts_valid_extraction() -> None:
    report = verify_source_comment_extraction(
        {
            "schema_version": "source_comment_extraction_v1",
            "comment_extraction_id": "adapter.comments.1234",
            "adapter_id": "adapter",
            "comment_count": 1,
            "comment_sha256": "b" * 64,
            "selected_artifact": {"filename": "comments.json"},
            "comments": [{"comment_id": "c1", "text": "hello"}],
            "operator_summary": {
                "live_network_used": False,
                "folder_scan_used": False,
                "full_local_paths_serialized": False,
            },
        }
    )
    assert report["verified"] is True
    assert report["issue_count"] == 0


def test_verifier_rejects_full_path_filename() -> None:
    report = verify_source_comment_extraction(
        {
            "schema_version": "source_comment_extraction_v1",
            "comment_extraction_id": "adapter.comments.1234",
            "adapter_id": "adapter",
            "comment_count": 0,
            "comment_sha256": "b" * 64,
            "selected_artifact": {"filename": "C:/temp/comments.json"},
            "comments": [],
            "operator_summary": {
                "live_network_used": False,
                "folder_scan_used": False,
                "full_local_paths_serialized": False,
            },
        }
    )
    assert report["verified"] is False
    assert "selected_artifact_filename_contains_path" in report["issues"]


if __name__ == "__main__":
    test_verifier_accepts_valid_extraction()
    test_verifier_rejects_full_path_filename()
    print("Source comment extraction verifier self-test passed.")
