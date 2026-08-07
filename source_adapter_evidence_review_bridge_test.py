from __future__ import annotations

from source_adapter_evidence_queue_bridge import build_source_adapter_evidence_queue_bridge
from source_adapter_evidence_queue_bridge_test import fixture_total_export_bridge
from source_adapter_evidence_review_bridge import EVIDENCE_REVIEW_BRIDGE_STATUS, build_source_adapter_evidence_review_bridge
from source_adapter_evidence_review_bridge_verifier import verify_source_adapter_evidence_review_bridge


def fixture_evidence_queue_bridge() -> dict:
    return build_source_adapter_evidence_queue_bridge(fixture_total_export_bridge(), queue_notes=["review queue"])


def main() -> None:
    package = build_source_adapter_evidence_review_bridge(
        fixture_evidence_queue_bridge(),
        reviewer_decision={"decision": "APPROVED", "reviewer_id": "reviewer_fixture"},
        review_notes=["reviewed"],
    )
    assert package["evidence_review_bridge_status"] == EVIDENCE_REVIEW_BRIDGE_STATUS
    assert package["evidence_review_count"] == 1
    assert package["source_adapter_evidence_review_batch"]["approved_for_release_count"] == 1
    assert package["source_adapter_approved_release_batch_handoff"]["ready_for_approved_release"] is True
    first = package["evidence_review_outputs"][0]
    assert first["evidence_review_decision"]["decision"] == "APPROVED"
    assert first["release_handoff"]["handoff_status"] == "READY_FOR_APPROVED_RELEASE"
    assert package["implementation_logic"]["shared_stage_executed"] == "source_evidence_review"
    assert verify_source_adapter_evidence_review_bridge(package)["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Evidence Review Bridge self-test passed.")
