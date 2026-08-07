from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_evidence_review_bridge import build_source_adapter_evidence_review_bridge
from source_adapter_evidence_review_bridge_store import store_source_adapter_evidence_review_bridge
from source_adapter_evidence_review_bridge_test import fixture_evidence_queue_bridge


def main() -> None:
    package = build_source_adapter_evidence_review_bridge(fixture_evidence_queue_bridge(), reviewer_decision={"decision": "APPROVED"})
    with tempfile.TemporaryDirectory() as tmp:
        receipt = store_source_adapter_evidence_review_bridge(package, tmp)
        assert receipt["store_status"] == "STORED"
        assert receipt["output_file_count"] == 5
        assert receipt["verification"]["verified"] is True
        for stored in receipt["stored_files"]:
            target = Path(tmp) / stored["filename"]
            assert target.exists()
            data = target.read_bytes()
            assert len(data) == stored["byte_count"]
    print("Source Adapter Evidence Review Bridge store self-test passed.")


if __name__ == "__main__":
    main()
