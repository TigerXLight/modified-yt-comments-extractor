from __future__ import annotations

import tempfile
from pathlib import Path

from source_evidence_review import build_source_evidence_review
from source_evidence_review_store import store_source_evidence_review
from source_evidence_review_test import _queue_item


def main() -> None:
    completed = ["verify_source_identity", "review_content_text", "review_comments", "decide_evidence_status"]
    outputs = build_source_evidence_review(
        evidence_queue_item=_queue_item(),
        reviewer_decision={"decision": "APPROVED", "completed_action_ids": completed},
    )
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_evidence_review(outputs.as_dict(), Path(tmp))
        assert receipt["schema_version"] == "source_evidence_review_store_v1"
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 5
        assert receipt["verification"]["verified"] is True
        assert len(list(Path(tmp).glob("*.json"))) == 5
    print("Source Evidence Review store self-test passed.")


if __name__ == "__main__":
    main()
