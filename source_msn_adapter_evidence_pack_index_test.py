from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_evidence_pack_index import build_evidence_pack_index, write_evidence_pack_index


def test_evidence_pack_indexes_and_hashes_key_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "reports").mkdir()
        (root / "reports" / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json").write_text('{"status":"PASS"}', encoding="utf-8")
        (root / "media" ).mkdir()
        (root / "media" / "article-image.jpg").write_bytes(b"image")
        (root / "archive").mkdir()
        (root / "archive" / "rendered-page.warc.gz").write_bytes(b"warc")
        index = build_evidence_pack_index(root)
        assert index.total_files_indexed == 3
        assert {entry.category for entry in index.entries} >= {"report", "media", "archive"}
        assert all(len(entry.sha256) == 64 for entry in index.entries)
        json_path, md_path = write_evidence_pack_index(index, root / "reports")
        assert json_path.exists()
        assert md_path.exists()


def main() -> int:
    test_evidence_pack_indexes_and_hashes_key_outputs()
    print("MSN evidence pack index self-test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
