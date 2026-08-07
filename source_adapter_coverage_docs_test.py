from __future__ import annotations

from pathlib import Path


def test_docs_capture_shared_adapter_strategy():
    text = Path("CAPTURE_SOURCE_ADAPTER_COVERAGE_FRAMEWORK.md").read_text(encoding="utf-8")
    assert "stops the MSN pattern" in text
    assert "shared pipeline stages" in text
    assert "lightweight in-app browser" in text
    assert "does not fetch pages" in text


if __name__ == "__main__":
    test_docs_capture_shared_adapter_strategy()
    print("Source Adapter coverage framework docs self-test passed.")
