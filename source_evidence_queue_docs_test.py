from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_EVIDENCE_QUEUE.md").read_text(encoding="utf-8")
    assert "Shared source Evidence Queue" in text
    assert "source_evidence_review" in text
    assert "does not fetch URLs" in text
    assert "does not serialize full local paths" in text
    print("Source Evidence Queue docs self-test passed.")


if __name__ == "__main__":
    main()
