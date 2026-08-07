from __future__ import annotations

from source_adapter_release_index_bridge import build_source_adapter_release_index_bridge
from source_adapter_release_index_bridge_test import fixture_approved_release_bridge
from source_adapter_release_index_bridge_verifier import verify_source_adapter_release_index_bridge


def main() -> None:
    package = build_source_adapter_release_index_bridge(fixture_approved_release_bridge())
    ok = verify_source_adapter_release_index_bridge(package)
    assert ok["verified"] is True
    broken = dict(package)
    broken["source_adapter_release_audit_batch_handoff"] = dict(package["source_adapter_release_audit_batch_handoff"], handoff_status="PENDING")
    bad = verify_source_adapter_release_index_bridge(broken)
    assert bad["verified"] is False
    assert bad["issue_count"] >= 1


if __name__ == "__main__":
    main()
    print("Source Adapter Release Index Bridge verifier self-test passed.")
