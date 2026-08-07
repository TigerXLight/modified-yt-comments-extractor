from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_EVIDENCE_QUEUE_BRIDGE.md").read_text(encoding="utf-8")
    assert "Adapter Evidence Queue Bridge" in text
    assert "source_evidence_queue" in text
    assert "full shared-section wiring" in text


if __name__ == "__main__":
    main()
    print("Source Adapter Evidence Queue Bridge docs self-test passed.")
