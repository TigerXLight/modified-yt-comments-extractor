from __future__ import annotations

from pathlib import Path


def test_docs_cover_review_decision_boundary() -> None:
    text = Path("CAPTURE_MSN_MANUAL_EVIDENCE_REVIEW_DECISION.md").read_text(encoding="utf-8")
    required = [
        "reviewer decision",
        "APPROVED",
        "REJECTED",
        "REVISION_REQUESTED",
        "Total Export",
        "no full local filesystem paths",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_cover_review_decision_boundary()
    print("MSN manual Evidence Review decision docs self-test passed.")
