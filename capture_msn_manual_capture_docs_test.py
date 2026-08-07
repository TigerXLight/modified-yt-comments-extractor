from __future__ import annotations

from pathlib import Path

DOC_PATH = Path("CAPTURE_MSN_MANUAL_CAPTURE_IMPLEMENTATION.md")


def test_docs_state_data_capture_implementation_not_observation_only() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    required = [
        "not observation-only",
        "article title/body/source metadata extraction",
        "MSN comments extraction",
        "Total Export-ready JSON bundles",
        "article/comment text is captured",
        "does not claim completed or verified capture",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_state_data_capture_implementation_not_observation_only()
    print("MSN manual capture implementation docs self-test passed.")
