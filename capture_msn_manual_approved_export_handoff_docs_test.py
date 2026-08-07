from __future__ import annotations

from pathlib import Path


def main() -> None:
    doc = Path("CAPTURE_MSN_MANUAL_APPROVED_EXPORT_HANDOFF.md")
    text = doc.read_text(encoding="utf-8")
    for required in (
        "approved-review handoff",
        "Total Export release",
        "does not perform live HTTP",
        "credential reads",
        "verifier",
    ):
        assert required in text
    print("MSN manual approved export handoff docs self-test passed.")


if __name__ == "__main__":
    main()
