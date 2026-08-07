from __future__ import annotations

from pathlib import Path


def test_docs_cover_release_boundary() -> None:
    text = Path("CAPTURE_MSN_MANUAL_APPROVED_RELEASE_PACKAGE.md").read_text(encoding="utf-8")
    assert "approved export handoff JSON" in text
    assert "Total Export release path" in text
    assert "no live HTTP" in text
    assert "capture_msn_manual_approved_release_package_cli.py" in text


if __name__ == "__main__":
    test_docs_cover_release_boundary()
    print("MSN manual approved release package docs self-test passed.")
