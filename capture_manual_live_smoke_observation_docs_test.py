from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET.md")


def test_manual_live_smoke_observation_docs_preserve_safety_boundary() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    required = (
        "metadata-only boundary",
        "operator-supplied",
        "does not perform live HTTP",
        "browser automation",
        "credential reads",
        "must not claim a completed or verified capture",
    )
    missing = [item for item in required if item not in text]
    assert not missing, f"missing required docs text: {missing}"


if __name__ == "__main__":
    test_manual_live_smoke_observation_docs_preserve_safety_boundary()
    print("Manual live smoke observation docs self-test passed.")
