from __future__ import annotations

from source_adapter_release_audit_bridge import build_source_adapter_release_audit_bridge
from source_adapter_release_audit_bridge_test import fixture_release_index_bridge
from source_adapter_release_audit_bridge_verifier import verify_source_adapter_release_audit_bridge


def main() -> None:
    package = build_source_adapter_release_audit_bridge(fixture_release_index_bridge())
    result = verify_source_adapter_release_audit_bridge(package)
    assert result["verified"] is True
    assert result["handoff_status"] == "READY_FOR_SHARED_ARCHIVE_HANDOFF"
    broken = dict(package)
    broken["source_adapter_archive_handoff_batch_handoff"] = dict(package["source_adapter_archive_handoff_batch_handoff"], ready_for_archive_handoff=False)
    failed = verify_source_adapter_release_audit_bridge(broken)
    assert failed["verified"] is False
    assert any("ready_for_archive_handoff" in issue for issue in failed["issues"])


if __name__ == "__main__":
    main()
    print("Source Adapter Release Audit Bridge verifier self-test passed.")
