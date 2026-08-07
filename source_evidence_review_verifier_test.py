from __future__ import annotations

from source_evidence_review import build_source_evidence_review
from source_evidence_review_test import _queue_item
from source_evidence_review_verifier import verify_source_evidence_review


def main() -> None:
    completed = ["verify_source_identity", "review_content_text", "review_comments", "decide_evidence_status"]
    outputs = build_source_evidence_review(
        evidence_queue_item=_queue_item(),
        reviewer_decision={"decision": "APPROVED", "completed_action_ids": completed},
    )
    result = verify_source_evidence_review(outputs.evidence_review_package, outputs.evidence_review_decision, outputs.release_handoff)
    assert result["schema_version"] == "source_evidence_review_verifier_v1"
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["decision"] == "APPROVED"
    print("Source Evidence Review verifier self-test passed.")


if __name__ == "__main__":
    main()
