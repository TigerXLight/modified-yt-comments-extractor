from __future__ import annotations

from source_adapter_approved_release_bridge import APPROVED_RELEASE_BRIDGE_STATUS, build_source_adapter_approved_release_bridge
from source_adapter_approved_release_bridge_verifier import verify_source_adapter_approved_release_bridge
from source_adapter_evidence_review_bridge import build_source_adapter_evidence_review_bridge
from source_adapter_evidence_review_bridge_test import fixture_evidence_queue_bridge


def fixture_evidence_review_bridge() -> dict:
    return build_source_adapter_evidence_review_bridge(
        fixture_evidence_queue_bridge(),
        reviewer_decision={"decision": "APPROVED", "reviewer_id": "reviewer_fixture"},
        review_notes=["reviewed"],
    )


def main() -> None:
    package = build_source_adapter_approved_release_bridge(
        fixture_evidence_review_bridge(),
        releaser_id="releaser_fixture",
        release_notes=["released"],
    )
    assert package["approved_release_bridge_status"] == APPROVED_RELEASE_BRIDGE_STATUS
    assert package["approved_release_count"] == 1
    assert package["source_adapter_approved_release_batch"]["approved_release_count"] == 1
    assert package["source_adapter_release_index_batch_handoff"]["ready_for_release_index"] is True
    first = package["approved_release_outputs"][0]
    assert first["approved_release_package"]["release_status"] == "READY_FOR_RELEASE_INDEX"
    assert first["approved_release_package"]["releaser_id"] == "releaser_fixture"
    assert first["release_index_handoff"]["handoff_status"] == "READY_FOR_RELEASE_INDEX"
    assert package["implementation_logic"]["shared_stage_executed"] == "source_approved_release"
    assert verify_source_adapter_approved_release_bridge(package)["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Approved Release Bridge self-test passed.")
