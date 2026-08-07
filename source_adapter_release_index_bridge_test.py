from __future__ import annotations

from source_adapter_approved_release_bridge import build_source_adapter_approved_release_bridge
from source_adapter_approved_release_bridge_test import fixture_evidence_review_bridge
from source_adapter_release_index_bridge import RELEASE_INDEX_BRIDGE_STATUS, build_source_adapter_release_index_bridge
from source_adapter_release_index_bridge_verifier import verify_source_adapter_release_index_bridge


def fixture_approved_release_bridge() -> dict:
    return build_source_adapter_approved_release_bridge(
        fixture_evidence_review_bridge(),
        releaser_id="releaser_fixture",
        release_notes=["released"],
    )


def main() -> None:
    package = build_source_adapter_release_index_bridge(
        fixture_approved_release_bridge(),
        indexer_id="indexer_fixture",
        release_notes=["indexed"],
    )
    assert package["release_index_bridge_status"] == RELEASE_INDEX_BRIDGE_STATUS
    assert package["release_index_count"] == 1
    assert package["source_adapter_release_index_batch"]["release_index_count"] == 1
    assert package["source_adapter_release_audit_batch_handoff"]["ready_for_release_audit"] is True
    first = package["release_index_outputs"][0]
    assert first["release_index_record"]["release_index_status"] == "READY_FOR_RELEASE_EXPORT_BUNDLE"
    assert first["release_index_record"]["indexed_by"] == "indexer_fixture"
    assert first["export_bundle_handoff"]["handoff_status"] == "READY_FOR_RELEASE_EXPORT_BUNDLE"
    assert package["implementation_logic"]["shared_stage_executed"] == "source_release_index"
    assert verify_source_adapter_release_index_bridge(package)["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Release Index Bridge self-test passed.")
