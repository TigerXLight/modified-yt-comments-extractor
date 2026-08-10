from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_certification_archive import build_certification_archive, find_evidence_files


def test_certification_archive_hashes_and_zips_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "root"
        root.mkdir()
        (root / "MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.json").write_text("{}", encoding="utf-8")
        (root / "MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.md").write_text("# ok", encoding="utf-8")
        (root / "ignored.txt").write_text("ignored", encoding="utf-8")

        found = find_evidence_files(root)
        assert len(found) == 2

        out = Path(tmp) / "archive"
        index = build_certification_archive(root, out, make_zip=True)
        assert len(index.files) == 2
        assert all(len(item.sha256) == 64 for item in index.files)
        assert (out / "MSN_SOURCE_ADAPTER_CERTIFICATION_ARCHIVE_INDEX.json").exists()
        assert (out / "MSN_SOURCE_ADAPTER_CERTIFICATION_ARCHIVE_INDEX.md").exists()
        assert (out / "MSN_SOURCE_ADAPTER_CERTIFICATION_ARCHIVE.zip").exists()


if __name__ == "__main__":
    test_certification_archive_hashes_and_zips_evidence()
    print("MSN certification archive self-test passed.")
