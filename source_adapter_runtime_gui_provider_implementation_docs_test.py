from __future__ import annotations

from pathlib import Path


def main() -> None:
    doc = Path("SOURCE_ADAPTER_RUNTIME_GUI_PROVIDER_IMPLEMENTATION.md")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    for required in [
        "Runtime GUI Provider Implementation",
        "GUI/controller routes",
        "provider execution adapters",
        "KEYS/ACCOUNTS",
        "receipt capture contracts",
    ]:
        assert required in text
    print("Source Adapter Runtime GUI Provider Implementation docs self-test passed.")


if __name__ == "__main__":
    main()
