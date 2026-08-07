from __future__ import annotations

from source_adapter_archive_result_intake_bridge import build_source_adapter_archive_result_intake_bridge
from source_adapter_archive_result_intake_bridge_test import fixture_archive_handoff_bridge, fixture_operator_results
from source_adapter_archive_review_bridge import (
    ARCHIVE_REVIEW_BRIDGE_STATUS,
    build_source_adapter_archive_review_bridge,
)
from source_adapter_archive_review_bridge_verifier import verify_source_adapter_archive_review_bridge


def fixture_archive_result_intake_bridge() -> dict:
    archive_handoff_bridge = fixture_archive_handoff_bridge()
    return build_source_adapter_archive_result_intake_bridge(
        archive_handoff_bridge,
        fixture_operator_results(archive_handoff_bridge),
        operator_id="archive_result_operator_fixture",
        intake_notes=["operator result received"],
    )


def main() -> None:
    package = build_source_adapter_archive_review_bridge(
        fixture_archive_result_intake_bridge(),
        archive_reviewer_decision={"decision": "APPROVED"},
        reviewer_id="archive_reviewer_fixture",
        review_notes=["archive receipt reviewed"],
    )
    assert package["archive_review_bridge_status"] == ARCHIVE_REVIEW_BRIDGE_STATUS
    assert package["archive_review_count"] == 1
    assert package["source_adapter_archive_review_batch"]["archive_review_count"] == 1
    assert package["source_adapter_archive_review_batch"]["approved_count"] == 1
    assert package["source_adapter_pipeline_closeout_batch_handoff"]["ready_for_pipeline_closeout"] is True
    first = package["archive_review_outputs"][0]
    assert first["archive_review_package"]["review_status"] == "ARCHIVE_REVIEW_COMPLETE"
    assert first["archive_review_decision"]["decision"] == "APPROVED"
    assert first["archive_review_closeout"]["closeout_status"] == "ARCHIVE_COMPLETE"
    assert first["archive_review_package"]["reviewer_id"] == "archive_reviewer_fixture"
    assert package["implementation_logic"]["shared_stage_executed"] == "source_archive_review"
    assert verify_source_adapter_archive_review_bridge(package)["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Review Bridge self-test passed.")
