from __future__ import annotations

from pathlib import Path


def test_docs_describe_release_section_closeout() -> None:
    text = Path("CAPTURE_MSN_MANUAL_RELEASE_SECTION_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "release section closeout" in text.lower()
    assert "explicit JSON files only" in text
    assert "no live HTTP" in text
    assert "no browser automation" in text
    assert "no full local path serialization" in text


if __name__ == "__main__":
    test_docs_describe_release_section_closeout()
    print("MSN manual release section closeout docs self-test passed.")
