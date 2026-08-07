from __future__ import annotations

from source_adapter_release_index_bridge import build_source_adapter_release_index_bridge
from source_adapter_release_index_bridge_test import fixture_approved_release_bridge
from source_adapter_release_audit_bridge import RELEASE_AUDIT_BRIDGE_STATUS, build_source_adapter_release_audit_bridge
from source_adapter_release_audit_bridge_verifier import verify_source_adapter_release_audit_bridge


def fixture_release_index_bridge() -> dict:
    return build_source_adapter_release_index_bridge(
        fixture_approved_release_bridge(),
        indexer_id="indexer_fixture",
        release_notes=["indexed"],
    )


def main() -> None:
    package = build_source_adapter_release_audit_bridge(
        fixture_release_index_bridge(),
        auditor_id="auditor_fixture",
        audit_notes=["audited"],
    )
    assert package["release_audit_bridge_status"] == RELEASE_AUDIT_BRIDGE_STATUS
    assert package["release_audit_count"] == 1
    assert package["source_adapter_release_audit_batch"]["release_audit_count"] == 1
    assert package["source_adapter_archive_handoff_batch_handoff"]["ready_for_archive_handoff"] is True
    first = package["release_audit_outputs"][0]
    assert first["release_audit_report"]["audit_status"] == "READY_FOR_ARCHIVE_HANDOFF"
    assert first["release_audit_report"]["audited_by"] == "auditor_fixture"
    assert first["archive_handoff"]["handoff_status"] == "READY_FOR_ARCHIVE_HANDOFF"
    assert package["implementation_logic"]["shared_stage_executed"] == "source_release_audit"
    assert verify_source_adapter_release_audit_bridge(package)["verified"] is True


if __name__ == "__main__":
    main()
    print("Source Adapter Release Audit Bridge self-test passed.")
