from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_RELEASE_INDEX_BRIDGE.md").read_text(encoding="utf-8")
    assert "source_release_index" in text
    assert "READY_FOR_SHARED_RELEASE_AUDIT" in text
    assert "multi-adapter" in text
    assert "immutable" in text


if __name__ == "__main__":
    main()
    print("Source Adapter Release Index Bridge docs self-test passed.")
