from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_APPROVED_RELEASE_BRIDGE.md").read_text(encoding="utf-8")
    required = [
        "Source Adapter Approved Release Bridge",
        "source_adapter_evidence_review_bridge_v1",
        "source_approved_release",
        "READY_FOR_SHARED_RELEASE_INDEX",
        "multi-adapter batches",
        "Approval gates",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    main()
    print("Source Adapter Approved Release Bridge docs self-test passed.")
