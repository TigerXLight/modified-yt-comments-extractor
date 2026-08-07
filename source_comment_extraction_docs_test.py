from __future__ import annotations

from pathlib import Path


def test_docs_record_shared_boundary() -> None:
    text = Path("SOURCE_COMMENT_EXTRACTION.md").read_text(encoding="utf-8")
    required = [
        "one-framework/many-adapters",
        "explicit operator-supplied artifacts",
        "no URL fetching",
        "no browser launch",
        "no folder scanning",
        "no credential access",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_record_shared_boundary()
    print("Source comment extraction docs self-test passed.")
