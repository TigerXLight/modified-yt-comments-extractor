from __future__ import annotations

from source_adapter_approved_release_bridge import build_source_adapter_approved_release_bridge
from source_adapter_approved_release_bridge_test import fixture_evidence_review_bridge
from source_adapter_approved_release_bridge_verifier import verify_source_adapter_approved_release_bridge


def main() -> None:
    package = build_source_adapter_approved_release_bridge(fixture_evidence_review_bridge())
    report = verify_source_adapter_approved_release_bridge(package)
    assert report["verified"] is True
    assert report["issue_count"] == 0
    broken = dict(package)
    broken["approved_release_outputs"] = []
    assert verify_source_adapter_approved_release_bridge(broken)["verified"] is False


if __name__ == "__main__":
    main()
    print("Source Adapter Approved Release Bridge verifier self-test passed.")
