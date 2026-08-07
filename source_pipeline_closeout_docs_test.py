from __future__ import annotations

from pathlib import Path


def test_docs_define_manual_safe_closeout() -> None:
    text = Path("SOURCE_PIPELINE_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "Shared Source Pipeline Closeout",
        "SOURCE_PIPELINE_COMPLETE",
        "does not fetch URLs",
        "does not fetch URLs, launch browsers",
        "adapter specs and fixture matrices",
    ]
    for needle in required:
        assert needle in text


if __name__ == "__main__":
    test_docs_define_manual_safe_closeout()
    print("Source Pipeline Closeout docs self-test passed.")
