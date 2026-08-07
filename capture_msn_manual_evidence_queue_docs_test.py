from __future__ import annotations

from pathlib import Path

DOC_PATH = Path("CAPTURE_MSN_MANUAL_EVIDENCE_QUEUE_INTEGRATION.md")


def test_docs_describe_implemented_queue_bridge_not_observation_only() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    required = [
        "not an observation-only note",
        "reads an explicit MSN manual action Total Export pipeline JSON report",
        "builds a deterministic Evidence Queue item",
        "writes the queue item and queue index JSON",
        "does not claim that a capture is complete or independently verified",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_describe_implemented_queue_bridge_not_observation_only()
    print("MSN manual Evidence Queue docs self-test passed.")
