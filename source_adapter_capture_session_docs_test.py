from __future__ import annotations

from pathlib import Path


def test_docs_describe_safe_boundary() -> None:
    text = Path("SOURCE_ADAPTER_CAPTURE_SESSION.md").read_text(encoding="utf-8")
    assert "Adapter Capture Session" in text
    assert "does not fetch URLs" in text
    assert "does not create, read, or validate the artifact bytes" in text


if __name__ == "__main__":
    test_docs_describe_safe_boundary()
    print("Source Adapter Capture Session docs self-test passed.")
