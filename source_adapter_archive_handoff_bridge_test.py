from __future__ import annotations

from source_adapter_release_audit_bridge import build_source_adapter_release_audit_bridge
from source_adapter_release_audit_bridge_test import fixture_release_index_bridge
from source_adapter_archive_handoff_bridge import ARCHIVE_HANDOFF_BRIDGE_STATUS, build_source_adapter_archive_handoff_bridge
from source_adapter_archive_handoff_bridge_verifier import verify_source_adapter_archive_handoff_bridge


def fixture_release_audit_bridge() -> dict:
    return build_source_adapter_release_audit_bridge(
        fixture_release_index_bridge(),
        auditor_id="auditor_fixture",
        audit_notes=["audited"],
    )


def main() -> None:
    package = build_source_adapter_archive_handoff_bridge(
        fixture_release_audit_bridge(),
        archive_providers=["archive_today", "ghostarchive"],
        operator_id="archive_operator_fixture",
        handoff_notes=["handoff prepared"],
    )
    assert package["archive_handoff_bridge_status"] == ARCHIVE_HANDOFF_BRIDGE_STATUS
    assert package["archive_handoff_count"] == 1
    assert package["source_adapter_archive_handoff_batch"]["archive_handoff_count"] == 1
    assert package["source_adapter_archive_result_intake_batch_handoff"]["ready_for_archive_result_intake"] is True
    first = package["archive_handoff_outputs"][0]
    assert first["archive_handoff_package"]["handoff_status"] == "READY_FOR_MANUAL_ARCHIVE_SUBMISSION"
    assert first["archive_handoff_package"]["prepared_by"] == "archive_operator_fixture"
    assert first["provider_tasks"]["task_status"] == "PENDING_OPERATOR_ACTION"
    assert first["result_templates"]["template_status"] == "WAITING_FOR_OPERATOR_RESULTS"
    assert first["result_intake_handoff"]["required_next_stage"] == "source_archive_result_intake"
    assert package["implementation_logic"]["shared_stage_executed"] == "source_archive_handoff"
    assert verify_source_adapter_archive_handoff_bridge(package)["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Handoff Bridge self-test passed.")
