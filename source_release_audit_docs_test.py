from __future__ import annotations

from pathlib import Path


def test_source_release_audit_docs_cover_contract() -> None:
    text = Path("SOURCE_RELEASE_AUDIT.md").read_text(encoding="utf-8")
    required = [
        "adapter-neutral",
        "source_release_index_v1",
        "READY_FOR_ARCHIVE_HANDOFF",
        "no URL fetching",
        "no URL fetching, browser launching, folder scanning, credential reading, archive submission",
        "Future source adapters should reuse this shared release-audit contract",
    ]
    for phrase in required:
        assert phrase in text


if __name__ == "__main__":
    test_source_release_audit_docs_cover_contract()
    print("Source Release Audit docs self-test passed.")
