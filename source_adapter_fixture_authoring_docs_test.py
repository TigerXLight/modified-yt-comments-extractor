from __future__ import annotations

from pathlib import Path


def test_docs_cover_safety_and_outputs() -> None:
    text = Path("SOURCE_ADAPTER_FIXTURE_AUTHORING.md").read_text(encoding="utf-8")
    assert "does not fetch URLs" in text
    assert "launch browsers" in text
    assert "fixture-authoring package" in text
    assert "safe basenames" in text
    assert "MSN-sized" in text


if __name__ == "__main__":
    test_docs_cover_safety_and_outputs()
    print("Source Adapter Fixture Authoring docs self-test passed.")
