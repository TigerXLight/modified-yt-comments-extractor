from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("CAPTURE_MANUAL_LIVE_SMOKE_ACTION_EXECUTION_KIT.md")


def test_execution_kit_docs_state_runnable_implementation_boundary() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    required = (
        "implementation, not observation-only metadata",
        "writes local command files",
        "Run the generated approved command",
        "artifact collection template",
        "files are read only when explicitly supplied",
        "full local paths are not serialized",
        "no completed or verified capture claim",
    )
    missing = [item for item in required if item not in text]
    assert not missing, f"missing required execution-kit docs text: {missing}"


if __name__ == "__main__":
    test_execution_kit_docs_state_runnable_implementation_boundary()
    print("Manual live smoke action execution kit docs self-test passed.")
