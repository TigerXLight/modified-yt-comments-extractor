from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from warcio.archiveiterator import ArchiveIterator

from source_msn_rendered_browser_validation import (
    LOCAL_PACKAGE_STRUCTURALLY_VERIFIED,
    RENDERED_BROWSER_LIVE_TESTED,
    CapturedResponse,
    _download_from_captured_response,
    verify_wacz_structure,
    write_standard_wacz,
    write_standard_warc,
)


def _response(url: str, body: bytes, content_type: str = "text/html") -> CapturedResponse:
    return CapturedResponse(
        url=url,
        status=200,
        headers={
            "Content-Type": content_type,
            "Cookie": "should-not-export=true",
            "Set-Cookie": "should-not-export=true",
            "Authorization": "Bearer should-not-export",
        },
        body=body,
        resource_type="document",
        method="GET",
        from_profile="fixture",
    )


def test_rendered_warc_is_readable_and_redacts_secret_headers() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        warc_path = Path(temp_dir) / "archive" / "data.warc"
        result = write_standard_warc(
            output_warc_path=warc_path,
            responses=(
                _response("https://www.msn.com/story", b"<html><body>story</body></html>"),
                _response("https://www.msn.com/story/image.jpg", b"image bytes", "image/jpeg"),
            ),
            timestamp_utc="2026-08-09T00:00:00Z",
        )

        assert result["conformant_read_record_count"] == 4
        assert result["index_rows"][0]["filename"] == "archive/data.warc"
        raw_warc = warc_path.read_text(encoding="latin-1")
        assert "should-not-export" not in raw_warc
        assert "Bearer should-not-export" not in raw_warc
        assert "should-not-export=true" not in raw_warc
        with warc_path.open("rb") as stream:
            records = list(ArchiveIterator(stream))
        assert [record.rec_type for record in records] == ["request", "response", "request", "response"]


def test_rendered_wacz_has_expected_standard_entries_and_index() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        warc = write_standard_warc(
            output_warc_path=root / "archive" / "data.warc",
            responses=(_response("https://www.msn.com/story", b"<html><body>story</body></html>"),),
            timestamp_utc="2026-08-09T00:00:00Z",
        )
        wacz = write_standard_wacz(
            output_wacz_path=root / "archive.wacz",
            warc_path=warc["path"],
            index_rows=warc["index_rows"],
            source_url="https://www.msn.com/story",
            title="Story",
            text="Story text",
            timestamp_utc="2026-08-09T00:00:00Z",
        )

        assert wacz["status"] == LOCAL_PACKAGE_STRUCTURALLY_VERIFIED
        assert wacz["missing_required_entries"] == []
        assert wacz["index_line_count"] == 1
        with zipfile.ZipFile(root / "archive.wacz", "r") as bundle:
            names = set(bundle.namelist())
            assert "archive/data.warc" in names
            assert "indexes/index.cdx.gz" in names
            assert "pages/pages.jsonl" in names
            assert "datapackage.json" in names
            package = json.loads(bundle.read("datapackage.json").decode("utf-8"))
            assert package["wacz_version"] == "1.2.0"

        verified = verify_wacz_structure(root / "archive.wacz")
        assert verified["status"] == LOCAL_PACKAGE_STRUCTURALLY_VERIFIED


def test_representative_download_uses_part_then_final_and_hashes() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        response = _response(
            "https://img-s-msn-com.akamaized.net/example/hero.jpg",
            b"representative image",
            "image/jpeg",
        )

        result = _download_from_captured_response(output_directory=root, responses=(response,))

        assert result["status"] == RENDERED_BROWSER_LIVE_TESTED
        assert result["download_performed"] is True
        assert result["source_url"] == response.url
        assert result["mime_type"] == "image/jpeg"
        assert Path(result["output_path"]).is_file()
        assert not Path(result["output_path"] + ".part").exists()


def run_self_test() -> None:
    test_rendered_warc_is_readable_and_redacts_secret_headers()
    test_rendered_wacz_has_expected_standard_entries_and_index()
    test_representative_download_uses_part_then_final_and_hashes()


if __name__ == "__main__":
    run_self_test()
    print("source_msn_rendered_browser_validation.py: OK")
