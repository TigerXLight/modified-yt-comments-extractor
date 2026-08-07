from __future__ import annotations

from pathlib import Path


def test_docs_exist_and_state_scope() -> None:
    text = Path("SOURCE_ADAPTER_CAPTURE_SETUP.md").read_text(encoding="utf-8")
    required = [
        "Source Adapter Capture Setup",
        "capture setup package",
        "artifact intake plan",
        "does not mutate app files",
        "manual or live actions are not started here",
    ]
    for phrase in required:
        assert phrase in text, phrase


if __name__ == "__main__":
    test_docs_exist_and_state_scope()
    print("Source Adapter Capture Setup docs self-test passed.")
