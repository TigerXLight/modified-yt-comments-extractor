from __future__ import annotations

import gzip
import json
import tempfile
import zipfile
from pathlib import Path

from source_warc_replay_hardening import (
    count_gzip_members,
    inspect_wacz,
    iter_warc_records,
    normalize_closeout_url,
    recompress_warc_for_pywb,
)


def make_record(record_id: str, payload: bytes) -> bytes:
    headers = (
        "WARC/1.0\r\n"
        "WARC-Type: response\r\n"
        f"WARC-Record-ID: <urn:uuid:{record_id}>\r\n"
        "WARC-Target-URI: https://example.test/\r\n"
        "Content-Type: text/plain\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "\r\n"
    ).encode("ascii")
    return headers + payload + b"\r\n\r\n"


def test_url_normalization() -> None:
    assert normalize_closeout_url("https://example.test/a?x=1^&y=2") == "https://example.test/a?x=1&y=2"
    assert normalize_closeout_url("[https://example.test/a?x=1^&y=2](https://example.test/a?x=1^&y=2)") == "https://example.test/a?x=1&y=2"


def test_warc_recompression() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw = make_record("00000000-0000-0000-0000-000000000001", b"hello") + make_record("00000000-0000-0000-0000-000000000002", b"world")
        assert len(list(iter_warc_records(raw))) == 2
        single = root / "single.warc.gz"
        single.write_bytes(gzip.compress(raw))
        assert count_gzip_members(single) == 1
        out = root / "multi.warc.gz"
        report = recompress_warc_for_pywb(single, out)
        assert report.status == "PYWB_INDEXABLE_WARC_GZ_GENERATED"
        assert report.record_count == 2
        assert report.gzip_member_count == 2
        assert count_gzip_members(out) == 2


def test_wacz_inspection() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "archive.wacz"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("datapackage.json", json.dumps({"profile": "wacz", "name": "test"}))
            zf.writestr("archive/data.warc.gz", b"dummy")
            zf.writestr("pages/pages.jsonl", "")
            zf.writestr("indexes/index.cdx", "")
        info = inspect_wacz(path)
        assert info["exists"] is True
        assert info["zip_readable"] is True
        assert info["datapackage_profile"] == "wacz"
        assert "REVIEW_REQUIRED" in info["status"]


def main() -> None:
    test_url_normalization()
    test_warc_recompression()
    test_wacz_inspection()
    print("source_warc_replay_hardening_test OK")


if __name__ == "__main__":
    main()
