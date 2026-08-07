from __future__ import annotations

from source_adapter_archive_result_intake_bridge import build_source_adapter_archive_result_intake_bridge
from source_adapter_archive_result_intake_bridge_test import fixture_archive_handoff_bridge, fixture_operator_results
from source_adapter_archive_result_intake_bridge_verifier import verify_source_adapter_archive_result_intake_bridge


def main() -> None:
    archive_handoff_bridge = fixture_archive_handoff_bridge()
    package = build_source_adapter_archive_result_intake_bridge(archive_handoff_bridge, fixture_operator_results(archive_handoff_bridge))
    verification = verify_source_adapter_archive_result_intake_bridge(package)
    assert verification["verified"] is True
    broken = dict(package)
    broken["archive_result_intake_bridge_status"] = "BROKEN"
    assert verify_source_adapter_archive_result_intake_bridge(broken)["verified"] is False


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Result Intake Bridge verifier self-test passed.")
