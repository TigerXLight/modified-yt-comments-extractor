from __future__ import annotations

from pathlib import Path


def test_runtime_wiring_bridge_docs_cover_capability_surface() -> None:
    text = Path("SOURCE_ADAPTER_RUNTIME_WIRING_BRIDGE.md").read_text(encoding="utf-8")
    assert "Runtime Wiring Bridge" in text
    assert "URL fetch/load" in text
    assert "browser launch" in text
    assert "folder scan" in text
    assert "credential lookup" in text
    assert "archive submission" in text
    assert "release upload" in text
    assert "app/registry mutation" in text
    assert "file-library publication" in text
    assert "operator approval" in text


if __name__ == "__main__":
    test_runtime_wiring_bridge_docs_cover_capability_surface()
    print("Source Adapter Runtime Wiring Bridge docs self-test passed.")
