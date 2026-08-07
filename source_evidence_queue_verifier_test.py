from __future__ import annotations

from source_evidence_queue import build_source_evidence_queue
from source_evidence_queue_test import _package
from source_evidence_queue_verifier import verify_source_evidence_queue


def main() -> None:
    outputs = build_source_evidence_queue(total_export_package=_package())
    result = verify_source_evidence_queue(outputs.evidence_queue_item)
    assert result["verified"] is True
    assert result["issue_count"] == 0

    broken = dict(outputs.evidence_queue_item)
    broken["queue_status"] = "DRAFT"
    result = verify_source_evidence_queue(broken)
    assert result["verified"] is False
    assert "queue_status must be READY_FOR_EVIDENCE_REVIEW" in result["issues"]
    print("Source Evidence Queue verifier self-test passed.")


if __name__ == "__main__":
    main()
