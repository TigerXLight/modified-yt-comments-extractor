from __future__ import annotations

from source_evidence_queue import build_source_evidence_queue


def _package() -> dict:
    return {
        "schema_version": "source_total_export_package_v1",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "export_profile": "fixture_profile",
        "export_status": "READY_FOR_EVIDENCE_QUEUE",
        "content": {
            "title": "Fixture headline",
            "body_sha256": "a" * 64,
            "body_char_count": 42,
            "content_extraction_id": "fixture.content.1",
        },
        "comments": {
            "available": True,
            "comment_count": 2,
            "comment_extraction_id": "fixture.comments.1",
        },
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "b" * 64, "byte_count": 100},
            {"role": "comments_json_or_text", "filename": "comments.json", "sha256": "c" * 64, "byte_count": 80},
        ],
        "evidence_queue_handoff": {
            "schema_version": "source_total_export_evidence_queue_handoff_v1",
            "total_export_package_id": "fixture_adapter.total_export_package.1234",
            "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
            "adapter_id": "fixture_adapter",
            "source_url": "https://fixture.test/story",
            "handoff_status": "READY_FOR_EVIDENCE_QUEUE",
            "required_next_stage": "source_evidence_queue",
        },
    }


def main() -> None:
    outputs = build_source_evidence_queue(total_export_package=_package(), queue_notes=["fixture note"])
    item = outputs.evidence_queue_item
    assert item["schema_version"] == "source_evidence_queue_v1"
    assert item["queue_status"] == "READY_FOR_EVIDENCE_REVIEW"
    assert item["review_state"] == "PENDING_REVIEW"
    assert item["adapter_id"] == "fixture_adapter"
    assert item["comment_summary"]["comment_count"] == 2
    assert item["artifact_count"] == 2
    assert any(action["action_id"] == "review_comments" for action in item["review_actions"])
    assert outputs.evidence_review_handoff["handoff_status"] == "READY_FOR_EVIDENCE_REVIEW"
    assert outputs.evidence_queue_index["ready_for_review_count"] == 1
    assert outputs.operator_summary["manual_or_live_actions_started"] is False
    print("Source Evidence Queue self-test passed.")


if __name__ == "__main__":
    main()
