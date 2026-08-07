from __future__ import annotations

from pathlib import Path


def test_docs_cover_contract() -> None:
    text = Path("SOURCE_TOTAL_EXPORT_PACKAGE.md").read_text(encoding="utf-8")
    required = [
        "source_capture_bundle_v1",
        "source_evidence_queue",
        "does not fetch URLs",
        "does not serialize full local paths",
        "reuse this package stage",
    ]
    for needle in required:
        assert needle in text


if __name__ == "__main__":
    test_docs_cover_contract()
    print("Source Total Export package docs self-test passed.")
