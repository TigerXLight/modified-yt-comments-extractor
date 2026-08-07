from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("CAPTURE_MANUAL_LIVE_SMOKE_ACTION_IMPLEMENTATION.md")


def test_action_docs_state_implementation_not_observation_only() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    required = (
        "not an observation-only import layer",
        "concrete named actions",
        "when explicitly approved, launch the operator's browser",
        "no browser launch happens without an explicit approval token",
        "no completed or verified capture is claimed",
    )
    missing = [item for item in required if item not in text]
    assert not missing, f"missing required docs text: {missing}"


if __name__ == "__main__":
    test_action_docs_state_implementation_not_observation_only()
    print("Manual live smoke action docs self-test passed.")
