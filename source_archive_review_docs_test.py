from __future__ import annotations

from pathlib import Path


def test_docs_cover_manual_safe_archive_review() -> None:
    text = Path("SOURCE_ARCHIVE_REVIEW.md").read_text(encoding="utf-8")
    assert "source_archive_review.py" in text
    assert "does not fetch URLs" in text
    assert "validate online archive contents" in text
    assert "ARCHIVE_COMPLETE" in text


if __name__ == "__main__":
    test_docs_cover_manual_safe_archive_review()
    print("Source Archive Review docs self-test passed.")
