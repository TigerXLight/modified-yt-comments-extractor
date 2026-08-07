from __future__ import annotations

from pathlib import Path


def test_docs_name_and_safety_scope() -> None:
    text = Path("SOURCE_ADAPTER_FIXTURE_REVIEW.md").read_text(encoding="utf-8")
    assert "Source Adapter Fixture Review" in text
    assert "does not fetch URLs" in text
    assert "does not" in text and "launch browsers" in text
    assert "shared local source pipeline" in text


if __name__ == "__main__":
    test_docs_name_and_safety_scope()
    print("Source Adapter Fixture Review docs self-test passed.")
