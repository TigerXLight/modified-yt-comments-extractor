from __future__ import annotations

from pathlib import Path


def test_release_index_docs_and_sources_cover_safety_boundary() -> None:
    doc = Path("CAPTURE_MSN_MANUAL_RELEASE_INDEX.md").read_text(encoding="utf-8")
    source = Path("capture_msn_manual_release_index.py").read_text(encoding="utf-8")
    assert "release-index boundary" in doc
    assert "explicit JSON files only" in doc
    assert "no live HTTP" in doc
    assert "MSN_MANUAL_RELEASE_INDEX_READY" in source
    assert "READY_FOR_RELEASE_INDEX_CONSUMPTION" in source


if __name__ == "__main__":
    test_release_index_docs_and_sources_cover_safety_boundary()
    print("MSN manual release index docs self-test passed.")
