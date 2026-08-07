from __future__ import annotations

from pathlib import Path


def test_docs_cover_manual_safety_and_adapter_scope() -> None:
    text = Path("SOURCE_ADAPTER_FIXTURE_MATRIX.md").read_text(encoding="utf-8")
    assert "does not fetch URLs" in text
    assert "does not fetch URLs, launch browsers, scan folders, read credentials" in text
    assert "one framework with many adapter specs" in text
    assert "MSN-sized pipelines" in text


if __name__ == "__main__":
    test_docs_cover_manual_safety_and_adapter_scope()
    print("Source Adapter Fixture Matrix docs self-test passed.")
