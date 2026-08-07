from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("CAPTURE_MSN_MANUAL_ACTION_TOTAL_EXPORT_PIPELINE.md")


def test_docs_state_pipeline_is_implemented_not_observation_only() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    required = [
        "not an observation-only layer",
        "generates operator action kits",
        "reads explicit operator-supplied article/comment artifact files",
        "writes a review-ready Total Export package",
        "generated `.cmd` files are the operator-run implementation path",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_state_pipeline_is_implemented_not_observation_only()
    print("MSN manual action Total Export pipeline docs self-test passed.")
