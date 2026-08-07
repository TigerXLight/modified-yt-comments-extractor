from __future__ import annotations

from source_adapter_archive_handoff_bridge import build_source_adapter_archive_handoff_bridge
from source_adapter_archive_handoff_bridge_test import fixture_release_audit_bridge
from source_adapter_archive_handoff_bridge_verifier import verify_source_adapter_archive_handoff_bridge


def main() -> None:
    package = build_source_adapter_archive_handoff_bridge(fixture_release_audit_bridge(), archive_providers=["archive_today"])
    verification = verify_source_adapter_archive_handoff_bridge(package)
    assert verification["verified"] is True
    assert verification["handoff_status"] == "READY_FOR_SHARED_ARCHIVE_RESULT_INTAKE"

    broken = dict(package)
    broken["source_adapter_archive_result_intake_batch_handoff"] = dict(package["source_adapter_archive_result_intake_batch_handoff"], ready_for_archive_result_intake=False)
    broken_verification = verify_source_adapter_archive_handoff_bridge(broken)
    assert broken_verification["verified"] is False
    assert any("ready_for_archive_result_intake" in issue for issue in broken_verification["issues"])


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Handoff Bridge verifier self-test passed.")
