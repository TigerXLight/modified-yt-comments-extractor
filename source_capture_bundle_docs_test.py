from __future__ import annotations

from pathlib import Path


def test_docs_mentions_safety_and_shared_flow() -> None:
    text = Path("SOURCE_CAPTURE_BUNDLE.md").read_text(encoding="utf-8")
    assert "one-framework/many-adapters" in text
    assert "does not fetch URLs" in text
    assert "Total Export" in text


if __name__ == "__main__":
    test_docs_mentions_safety_and_shared_flow()
    print("Source capture bundle docs self-test passed.")
