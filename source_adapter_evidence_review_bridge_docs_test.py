from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_EVIDENCE_REVIEW_BRIDGE.md").read_text(encoding="utf-8")
    required = [
        "Source Adapter Evidence Review Bridge",
        "source_evidence_review",
        "READY_FOR_SHARED_EVIDENCE_REVIEW",
        "per-queue-item decisions",
        "approved-release batch handoff",
        "shared review contract",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    assert not missing, f"missing documentation phrases: {missing}"
    print("Source Adapter Evidence Review Bridge docs self-test passed.")


if __name__ == "__main__":
    main()
