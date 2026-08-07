from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DOC = REPO_ROOT / "CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET.md"


def test_manual_smoke_docs_record_safety_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    required_phrases = (
        "REV4 manual live site-smoke approval packet",
        "metadata-only checklist",
        "does not run live site capture",
        "browser automation",
        "archive submission",
        "media download",
        "WARC/WACZ capture",
        "ArchiveBox",
        "credential reads",
        "separate user approval",
        "MANUAL_OPERATOR_ONLY",
    )
    for phrase in required_phrases:
        assert phrase in text


if __name__ == "__main__":
    test_manual_smoke_docs_record_safety_boundary()
    print("Manual live smoke approval docs self-test passed.")
