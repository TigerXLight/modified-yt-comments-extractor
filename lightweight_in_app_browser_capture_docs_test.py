from __future__ import annotations

from pathlib import Path


def test_docs_name_shared_adapter_strategy_and_safety() -> None:
    text = Path("LIGHTWEIGHT_IN_APP_BROWSER_CAPTURE.md").read_text(encoding="utf-8")
    required = [
        "Shared source-adapter browser capture boundary",
        "adapter-neutral",
        "no browser is opened by tests",
        "generated launch scripts require an explicit approval token",
    ]
    for phrase in required:
        assert phrase in text


if __name__ == "__main__":
    test_docs_name_shared_adapter_strategy_and_safety()
    print("Lightweight in-app browser capture docs self-test passed.")
