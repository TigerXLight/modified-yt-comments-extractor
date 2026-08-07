from __future__ import annotations

from pathlib import Path


def main() -> None:
    doc = Path("CAPTURE_MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE.md").read_text(encoding="utf-8")
    required = [
        "Evidence Review package",
        "Total Export package",
        "queue",
        "explicit files supplied by the operator",
        "safe filenames and hashes",
    ]
    for phrase in required:
        assert phrase in doc, phrase
    print("MSN manual Evidence Review package docs self-test passed.")


if __name__ == "__main__":
    main()
