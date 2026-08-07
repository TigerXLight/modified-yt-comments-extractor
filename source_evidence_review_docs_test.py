from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_EVIDENCE_REVIEW.md").read_text(encoding="utf-8")
    required = [
        "adapter-neutral Evidence Review stage",
        "APPROVED",
        "REJECTED",
        "REVISION_REQUESTED",
        "no URL fetching",
        "shared review contract",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    assert not missing, f"missing documentation phrases: {missing}"
    print("Source Evidence Review docs self-test passed.")


if __name__ == "__main__":
    main()
