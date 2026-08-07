from __future__ import annotations

from source_evidence_review import build_source_evidence_review


def _queue_item() -> dict:
    return {
        "schema_version": "source_evidence_queue_v1",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "queue_status": "READY_FOR_EVIDENCE_REVIEW",
        "review_state": "PENDING_REVIEW",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "content_summary": {"title": "Fixture headline", "body_sha256": "a" * 64, "body_char_count": 42},
        "comment_summary": {"available": True, "comment_count": 2},
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "b" * 64, "byte_count": 100},
            {"role": "comments_json_or_text", "filename": "comments.json", "sha256": "c" * 64, "byte_count": 80},
        ],
        "review_actions": [
            {"action_id": "verify_source_identity", "label": "Verify source identity", "required": True},
            {"action_id": "review_content_text", "label": "Review content", "required": True},
            {"action_id": "review_comments", "label": "Review comments", "required": True},
            {"action_id": "decide_evidence_status", "label": "Decide status", "required": True},
        ],
    }


def main() -> None:
    completed = ["verify_source_identity", "review_content_text", "review_comments", "decide_evidence_status"]
    outputs = build_source_evidence_review(
        evidence_queue_item=_queue_item(),
        reviewer_decision={"decision": "APPROVED", "completed_action_ids": completed, "reviewer_id": "reviewer.fixture"},
        review_notes=["fixture note"],
    )
    package = outputs.evidence_review_package
    assert package["schema_version"] == "source_evidence_review_v1"
    assert package["review_package_status"] == "READY_FOR_REVIEW_DECISION"
    assert package["artifact_count"] == 2
    assert outputs.evidence_review_checklist["checklist_status"] == "COMPLETE"
    assert outputs.evidence_review_decision["decision"] == "APPROVED"
    assert outputs.evidence_review_decision["approved_for_release"] is True
    assert outputs.release_handoff["handoff_status"] == "READY_FOR_APPROVED_RELEASE"
    assert outputs.release_handoff["required_next_stage"] == "source_approved_release"
    assert outputs.operator_summary["manual_or_live_actions_started"] is False
    print("Source Evidence Review self-test passed.")


if __name__ == "__main__":
    main()
