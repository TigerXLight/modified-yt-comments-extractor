from __future__ import annotations

from pathlib import Path


def test_source_approved_release_docs_capture_safety_contract() -> None:
    text = Path("SOURCE_APPROVED_RELEASE.md").read_text(encoding="utf-8")
    assert "adapter-neutral approved-release stage" in text
    assert "Only `APPROVED` Evidence Review decisions" in text
    assert "no URL fetching" in text
    assert "browser launching" in text
    assert "credential reading" in text
    assert "Future source adapters should reuse" in text


if __name__ == "__main__":
    test_source_approved_release_docs_capture_safety_contract()
    print("Source Approved Release docs self-test passed.")
