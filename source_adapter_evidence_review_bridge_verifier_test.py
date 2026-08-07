from __future__ import annotations

from source_adapter_evidence_review_bridge import build_source_adapter_evidence_review_bridge
from source_adapter_evidence_review_bridge_test import fixture_evidence_queue_bridge
from source_adapter_evidence_review_bridge_verifier import verify_source_adapter_evidence_review_bridge


def main() -> None:
    package = build_source_adapter_evidence_review_bridge(fixture_evidence_queue_bridge(), reviewer_decision={"decision": "APPROVED"})
    verification = verify_source_adapter_evidence_review_bridge(package)
    assert verification["verified"] is True
    broken = dict(package, evidence_review_bridge_status="BROKEN")
    assert verify_source_adapter_evidence_review_bridge(broken)["verified"] is False
    print("Source Adapter Evidence Review Bridge verifier self-test passed.")


if __name__ == "__main__":
    main()
