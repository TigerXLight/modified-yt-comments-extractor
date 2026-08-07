from __future__ import annotations

from pathlib import Path


def test_docs_describe_safe_boundary() -> None:
    text = Path("SOURCE_ADAPTER_CAPTURE_ACTION_KIT.md").read_text(encoding="utf-8")
    assert "Adapter Capture Action Kit" in text
    assert "does not fetch URLs" in text
    assert "requires explicit operator approval" in text


if __name__ == "__main__":
    test_docs_describe_safe_boundary()
    print("Source Adapter Capture Action Kit docs self-test passed.")
