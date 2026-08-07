from __future__ import annotations

from source_adapter_archive_handoff_bridge import build_source_adapter_archive_handoff_bridge
from source_adapter_archive_handoff_bridge_test import fixture_release_audit_bridge
from source_adapter_archive_result_intake_bridge import (
    ARCHIVE_RESULT_INTAKE_BRIDGE_STATUS,
    build_source_adapter_archive_result_intake_bridge,
)
from source_adapter_archive_result_intake_bridge_verifier import verify_source_adapter_archive_result_intake_bridge


def fixture_archive_handoff_bridge() -> dict:
    return build_source_adapter_archive_handoff_bridge(
        fixture_release_audit_bridge(),
        archive_providers=["archive_today", "ghostarchive"],
        operator_id="archive_operator_fixture",
        handoff_notes=["handoff prepared"],
    )


def fixture_operator_results(archive_handoff_bridge: dict) -> dict:
    archive_handoff_id = archive_handoff_bridge["archive_handoff_outputs"][0]["archive_handoff_package"]["archive_handoff_id"]
    return {
        archive_handoff_id: [
            {
                "schema_version": "source_archive_operator_result_v1",
                "provider_id": "archive_today",
                "archive_url": "https://archive.example/fixture-story",
                "archive_receipt_filename": "archive_today_receipt.json",
                "archive_screenshot_filename": "archive_today_screenshot.png",
                "operator_notes": ["Operator pasted a manual archive result."],
            }
        ]
    }


def main() -> None:
    archive_handoff_bridge = fixture_archive_handoff_bridge()
    package = build_source_adapter_archive_result_intake_bridge(
        archive_handoff_bridge,
        fixture_operator_results(archive_handoff_bridge),
        operator_id="archive_result_operator_fixture",
        intake_notes=["operator result received"],
    )
    assert package["archive_result_intake_bridge_status"] == ARCHIVE_RESULT_INTAKE_BRIDGE_STATUS
    assert package["archive_result_intake_count"] == 1
    assert package["source_adapter_archive_result_intake_batch"]["archive_result_intake_count"] == 1
    assert package["source_adapter_archive_review_batch_handoff"]["ready_for_archive_review"] is True
    first = package["archive_result_intake_outputs"][0]
    assert first["archive_result_intake_record"]["intake_status"] == "READY_FOR_ARCHIVE_REVIEW"
    assert first["archive_result_intake_record"]["operator_id"] == "archive_result_operator_fixture"
    assert first["archive_receipt_index"]["receipt_count"] == 1
    assert first["archive_review_handoff"]["required_next_stage"] == "source_archive_review"
    assert package["implementation_logic"]["shared_stage_executed"] == "source_archive_result_intake"
    assert verify_source_adapter_archive_result_intake_bridge(package)["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Result Intake Bridge self-test passed.")
