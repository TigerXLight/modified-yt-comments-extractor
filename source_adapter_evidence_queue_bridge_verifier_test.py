from __future__ import annotations

from copy import deepcopy

from source_adapter_evidence_queue_bridge import build_source_adapter_evidence_queue_bridge
from source_adapter_evidence_queue_bridge_test import fixture_total_export_bridge
from source_adapter_evidence_queue_bridge_verifier import verify_source_adapter_evidence_queue_bridge


def main() -> None:
    package = build_source_adapter_evidence_queue_bridge(fixture_total_export_bridge())
    ok = verify_source_adapter_evidence_queue_bridge(package)
    assert ok["verified"] is True
    broken = deepcopy(package)
    broken["source_adapter_evidence_review_batch_handoff"]["queue_item_ids"] = []
    failed = verify_source_adapter_evidence_queue_bridge(broken)
    assert failed["verified"] is False
    assert any("queue_item_ids" in issue for issue in failed["issues"])


if __name__ == "__main__":
    main()
    print("Source Adapter Evidence Queue Bridge verifier self-test passed.")
