from __future__ import annotations

from source_adapter_total_export_bridge import build_source_adapter_total_export_bridge
from source_adapter_total_export_bridge_test import fixture_capture_bundle_bridge
from source_adapter_evidence_queue_bridge import EVIDENCE_QUEUE_BRIDGE_STATUS, build_source_adapter_evidence_queue_bridge
from source_adapter_evidence_queue_bridge_verifier import verify_source_adapter_evidence_queue_bridge


def fixture_total_export_bridge() -> dict:
    return build_source_adapter_total_export_bridge(fixture_capture_bundle_bridge(), package_notes=["reviewed"])


def main() -> None:
    package = build_source_adapter_evidence_queue_bridge(fixture_total_export_bridge(), queue_notes=["queued"])
    assert package["evidence_queue_bridge_status"] == EVIDENCE_QUEUE_BRIDGE_STATUS
    assert package["queue_item_count"] == 1
    assert package["source_adapter_evidence_queue_batch"]["queue_item_count"] == 1
    assert package["source_adapter_evidence_review_batch_handoff"]["ready_for_evidence_review"] is True
    first = package["evidence_queue_outputs"][0]
    assert first["evidence_queue_item"]["queue_status"] == "READY_FOR_EVIDENCE_REVIEW"
    assert first["evidence_queue_item"]["content_summary"]["title"] == "Bridge title"
    assert first["evidence_review_handoff"]["handoff_status"] == "READY_FOR_EVIDENCE_REVIEW"
    assert package["implementation_logic"]["shared_stage_executed"] == "source_evidence_queue"
    assert verify_source_adapter_evidence_queue_bridge(package)["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Evidence Queue Bridge self-test passed.")
