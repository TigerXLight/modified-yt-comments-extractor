from __future__ import annotations


def fixture_capture_bundle_bridge() -> dict:
    return {
        "schema_version": "source_adapter_capture_bundle_bridge_v1",
        "capture_bundle_bridge_status": "SHARED_CAPTURE_BUNDLES_BUILT",
        "source_adapter_capture_bundle_bridge_id": "source_adapter_capture_bundle_bridge.example",
        "source_adapter_total_export_handoff": {
            "schema_version": "source_adapter_total_export_handoff_v1",
            "handoff_status": "READY_FOR_SHARED_TOTAL_EXPORT_PACKAGE",
            "ready_for_total_export_package": True,
            "required_next_stage": "source_total_export_package",
            "capture_bundle_ids": ["article.capture_bundle.1234"],
        },
        "capture_bundle_outputs": [
            {
                "capture_bundle": {
                    "schema_version": "source_capture_bundle_v1",
                    "capture_bundle_id": "article.capture_bundle.1234",
                    "adapter_id": "article",
                    "source_url": "https://article.example/story",
                    "input_stage_ids": {
                        "content_extraction_id": "article.content.1234",
                        "comment_extraction_id": "article.comments.1234",
                        "artifact_collection_id": "article.collection.1234",
                    },
                    "content": {
                        "title": "Bridge title",
                        "body_text": "Bridge body.",
                        "body_sha256": "f" * 64,
                        "content_extraction_id": "article.content.1234",
                    },
                    "comments": {
                        "available": True,
                        "comment_count": 1,
                        "comment_extraction_id": "article.comments.1234",
                    },
                    "artifact_index": [
                        {"role": "article_html_or_text", "filename": "article.html", "byte_count": 32, "sha256": "a" * 64},
                        {"role": "comments_json_or_text", "filename": "comments.json", "byte_count": 16, "sha256": "d" * 64},
                    ],
                    "total_export_handoff": {
                        "schema_version": "source_capture_total_export_handoff_v1",
                        "capture_bundle_id": "article.capture_bundle.1234",
                        "handoff_status": "READY_FOR_TOTAL_EXPORT_PACKAGE",
                    },
                },
                "capture_manifest": {
                    "schema_version": "source_capture_manifest_v1",
                    "capture_bundle_id": "article.capture_bundle.1234",
                    "adapter_id": "article",
                    "source_url": "https://article.example/story",
                    "artifact_count": 2,
                    "comment_count": 1,
                },
                "total_export_handoff": {
                    "schema_version": "source_capture_total_export_handoff_v1",
                    "capture_bundle_id": "article.capture_bundle.1234",
                    "handoff_status": "READY_FOR_TOTAL_EXPORT_PACKAGE",
                },
            }
        ],
    }

from source_adapter_total_export_bridge import build_source_adapter_total_export_bridge
from source_adapter_total_export_bridge_verifier import verify_source_adapter_total_export_bridge


def main() -> None:
    package = build_source_adapter_total_export_bridge(fixture_capture_bundle_bridge())
    verified = verify_source_adapter_total_export_bridge(package)
    assert verified["verified"] is True
    broken = dict(package)
    broken["source_adapter_evidence_queue_handoff"] = dict(package["source_adapter_evidence_queue_handoff"], handoff_status="BROKEN")
    failed = verify_source_adapter_total_export_bridge(broken)
    assert failed["verified"] is False
    assert failed["issue_count"] >= 1


if __name__ == "__main__":
    main()
    print("Source Adapter Total Export Bridge verifier self-test passed.")
