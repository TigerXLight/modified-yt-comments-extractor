from __future__ import annotations

from pathlib import Path


def test_source_archive_handoff_docs_cover_manual_safety() -> None:
    text = Path("SOURCE_ARCHIVE_HANDOFF.md").read_text(encoding="utf-8")
    required = [
        "manual archive handoff",
        "does not fetch URLs",
        "does not fetch URLs, launch browsers, submit archive requests",
        "source_archive_result_intake_handoff",
        "safe basenames",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, f"missing documentation phrases: {missing}"


if __name__ == "__main__":
    test_source_archive_handoff_docs_cover_manual_safety()
    print("Source Archive Handoff docs self-test passed.")
