from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from source_local_web_archive_repair_cli import main
from source_msn_rendered_browser_validation import CapturedResponse, write_standard_warc


SOURCE_URL = "https://www.msn.com/en-gb/news/example/ar-AA123?PC=EMMX01"


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _legacy_fixture(path: Path) -> bytes:
    warc_path = path.with_suffix(".data.warc")
    warc_result = write_standard_warc(
        output_warc_path=warc_path,
        responses=(
            CapturedResponse(
                url=SOURCE_URL + "#comments",
                status=200,
                headers={"content-type": "text/html; charset=utf-8"},
                body=b"<html><title>Fixture</title><body>comments</body></html>",
                resource_type="document",
            ),
            CapturedResponse(
                url="https://assets.msn.com/A.js",
                status=200,
                headers={"content-type": "application/javascript"},
                body=b"console.log('fixture');",
                resource_type="script",
            ),
        ),
        timestamp_utc="2026-08-09T00:00:00Z",
    )
    warc = warc_path.read_bytes()
    pages = (
        json.dumps({"format": "json-pages-1.0", "id": "pages", "title": "All Pages"})
        + "\n"
        + json.dumps({"url": SOURCE_URL + "#comments", "ts": "2026-08-09T00:00:00Z", "title": "Fixture"})
        + "\n"
    ).encode("utf-8")
    rows = []
    for row in reversed(list(warc_result["index_rows"])):
        rows.append(
            f"{str(row['urlkey']).upper()} {row['timestamp']} "
            + json.dumps(
                {
                    "digest": row["digest"],
                    "filename": row["filename"],
                    "length": row["length"],
                    "mime": row["mime"],
                    "offset": row["offset"],
                    "status": row["status"],
                    "url": row["url"],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    index = gzip.compress(("\n".join(rows) + "\n").encode("utf-8"), mtime=0)
    resources = {
        "archive/data.warc": warc,
        "indexes/index.cdx.gz": index,
        "pages/pages.jsonl": pages,
    }
    package = {
        "created": "2026-08-09T00:00:00Z",
        "home": {"url": SOURCE_URL + "#comments", "ts": "2026-08-09T00:00:00Z"},
        "mainPageUrl": SOURCE_URL + "#comments",
        "profile": "data-package",
        "resources": [
            {
                "bytes": len(payload),
                "hash": "sha256:" + hashlib.sha256(payload).hexdigest(),
                "name": Path(name).name,
                "path": name,
            }
            for name, payload in sorted(resources.items())
        ],
        "wacz_version": "1.2.0",
    }
    resources["datapackage.json"] = _json_bytes(package)
    resources["datapackage-digest.json"] = _json_bytes(
        {
            "hash": "sha256:" + hashlib.sha256(resources["datapackage.json"]).hexdigest(),
            "path": "datapackage.json",
        }
    )
    with zipfile.ZipFile(path, "w") as bundle:
        for name, payload in sorted(resources.items()):
            info = zipfile.ZipInfo(name)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED if name.startswith("archive/") or name.endswith(".gz") else zipfile.ZIP_DEFLATED
            bundle.writestr(info, payload)
    return warc


def test_repair_cli_defaults_to_replayweb_page_profile_and_preserves_input() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "archive.wacz"
        output = root / "archive.replayweb-fixed.wacz"
        original_warc = _legacy_fixture(source)
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()

        exit_code = main(
            [
                "--input-wacz",
                str(source),
                "--output-wacz",
                str(output),
                "--expected-source-url",
                SOURCE_URL + "#comments",
            ]
        )

        assert exit_code == 0
        assert output.is_file()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
        with zipfile.ZipFile(output, "r") as bundle:
            package = json.loads(bundle.read("datapackage.json").decode("utf-8"))
            assert package["profile"] == "data-package"
            assert package["home"]["url"] == SOURCE_URL
            assert package["mainPageUrl"] == SOURCE_URL
            assert package["wacz_version"] == "1.2.0"
            assert "archive/data.warc" not in bundle.namelist()
            repaired_warc = gzip.decompress(bundle.read("archive/data.warc.gz"))
            assert original_warc != repaired_warc
            assert b"GET /en-gb/news/example/ar-AA123?PC=EMMX01 HTTP/1.1" in repaired_warc
            assert b"GET /A.js HTTP/1.1" in repaired_warc
            assert b"HTTP/1.1 GET /en-gb/news/example/ar-AA123?PC=EMMX01 HTTP/1.1" not in repaired_warc
            assert b"HTTP/1.1 GET /A.js HTTP/1.1" not in repaired_warc
            assert any(item["path"] == "archive/data.warc.gz" for item in package["resources"])
            index_lines = gzip.decompress(bundle.read("indexes/index.cdx.gz")).decode("utf-8").splitlines()
            assert index_lines == sorted(index_lines, key=lambda line: line.encode("utf-8"))
            assert index_lines[0].startswith("com,msn,assets)/a.js ")
            assert index_lines[1].startswith("com,msn,www)/en-gb/news/example/ar-aa123?pc=emmx01 ")
            assert all('"filename":"data.warc.gz"' in line for line in index_lines)



def test_repair_cli_can_write_strict_wacz12_profile() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "archive.wacz"
        output = root / "archive.strict-wacz12.wacz"
        _legacy_fixture(source)

        exit_code = main(
            [
                "--input-wacz",
                str(source),
                "--output-wacz",
                str(output),
                "--expected-source-url",
                SOURCE_URL + "#comments",
                "--compatibility-profile",
                "wacz12",
            ]
        )

        assert exit_code == 0
        with zipfile.ZipFile(output, "r") as bundle:
            package = json.loads(bundle.read("datapackage.json").decode("utf-8"))
            assert package["profile"] == "wacz"
            assert package["home"]["url"] == SOURCE_URL
            assert "mainPageUrl" not in package
            assert "wacz_version" not in package


def test_repair_cli_can_add_static_evidence_page_without_replacing_original_page() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "archive.wacz"
        output = root / "archive.static-evidence.wacz"
        _legacy_fixture(source)
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        static_url = "https://source-evidence.local/replay/msn/ar-AA123/static-evidence.html"

        exit_code = main(
            [
                "--input-wacz",
                str(source),
                "--output-wacz",
                str(output),
                "--expected-source-url",
                SOURCE_URL + "#comments",
                "--add-static-evidence-page",
                "--static-evidence-url",
                static_url,
                "--runtime-limitation-note",
                "Normalized WACZ article entry click: Archived Page Not Found.",
            ]
        )

        assert exit_code == 0
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
        with zipfile.ZipFile(output, "r") as bundle:
            names = bundle.namelist()
            assert "archive/source-evidence-static.warc.gz" in names
            static_warc = gzip.decompress(bundle.read("archive/source-evidence-static.warc.gz")).decode(
                "utf-8",
                errors="replace",
            )
            assert "GET /replay/msn/ar-AA123/static-evidence.html HTTP/1.1" in static_warc
            assert "Derived static replay/evidence view generated from local archived evidence" in static_warc
            assert "<script" not in static_warc.lower()
            assert "<iframe" not in static_warc.lower()

            pages = [
                json.loads(line)
                for line in bundle.read("pages/pages.jsonl").decode("utf-8").splitlines()
                if line.strip()
            ]
            assert pages[1]["url"] == static_url
            assert pages[1]["derived"] is True
            assert any(row.get("url") == SOURCE_URL for row in pages)

            index_lines = gzip.decompress(bundle.read("indexes/index.cdx.gz")).decode("utf-8").splitlines()
            assert any(static_url in line for line in index_lines)
            assert index_lines == sorted(index_lines, key=lambda line: line.encode("utf-8"))


def test_repair_cli_writes_standalone_static_outputs_for_wacz_lookup_fallback() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "archive.wacz"
        output = root / "archive.static-evidence.wacz"
        static_dir = root / "standalone"
        _legacy_fixture(source)
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        static_url = "https://source-evidence.local/replay/msn/ar-AA123/static-evidence.html"

        exit_code = main(
            [
                "--input-wacz",
                str(source),
                "--output-wacz",
                str(output),
                "--expected-source-url",
                SOURCE_URL + "#comments",
                "--add-static-evidence-page",
                "--static-output-dir",
                str(static_dir),
                "--static-evidence-url",
                static_url,
                "--runtime-limitation-note",
                "WACZ static page listed but ReplayWeb WACZ lookup returned Archived Page Not Found.",
            ]
        )

        assert exit_code == 0
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
        html_path = static_dir / "static-evidence.html"
        warc_gz_path = static_dir / "static-evidence.warc.gz"
        warc_path = static_dir / "static-evidence.warc"
        page_html_path = static_dir / "static-page-view.html"
        page_warc_gz_path = static_dir / "static-page-view.warc.gz"
        page_warc_path = static_dir / "static-page-view.warc"
        text_html_path = static_dir / "static-text-view.html"
        text_warc_gz_path = static_dir / "static-text-view.warc.gz"
        text_warc_path = static_dir / "static-text-view.warc"
        article_txt_path = static_dir / "static-article.txt"
        comments_txt_path = static_dir / "static-comments.txt"
        page_text_txt_path = static_dir / "static-page-text.txt"
        page_text_md_path = static_dir / "static-page-text.md"
        assert html_path.is_file()
        assert warc_gz_path.is_file()
        assert warc_path.is_file()
        assert page_html_path.is_file()
        assert page_warc_gz_path.is_file()
        assert page_warc_path.is_file()
        assert text_html_path.is_file()
        assert text_warc_gz_path.is_file()
        assert text_warc_path.is_file()
        assert article_txt_path.is_file()
        assert comments_txt_path.is_file()
        assert page_text_txt_path.is_file()
        assert page_text_md_path.is_file()
        html_text = html_path.read_text(encoding="utf-8")
        assert "Derived static replay/evidence view generated from local archived evidence" in html_text
        assert "Archived Page Not Found" in html_text
        assert "<script" not in html_text.lower()
        assert "<iframe" not in html_text.lower()
        raw_warc_gz = gzip.decompress(warc_gz_path.read_bytes()).decode("utf-8", errors="replace")
        assert "WARC-Target-URI: " + static_url in raw_warc_gz
        assert "GET /replay/msn/ar-AA123/static-evidence.html HTTP/1.1" in raw_warc_gz
        assert "HTTP/1.1 200 OK" in raw_warc_gz
        assert "Content-Type: text/html; charset=utf-8" in raw_warc_gz
        assert "REPLAY_VISUALLY_VERIFIED" not in raw_warc_gz
        page_html_text = page_html_path.read_text(encoding="utf-8")
        assert "Derived static archived webpage view generated from local captured evidence" in page_html_text
        assert "Captured article body text was not available in the local manifest" in page_html_text
        assert "<script" not in page_html_text.lower()
        assert "<iframe" not in page_html_text.lower()
        raw_page_warc_gz = gzip.decompress(page_warc_gz_path.read_bytes()).decode("utf-8", errors="replace")
        assert "WARC-Target-URI: https://source-evidence.local/replay/msn/ar-AA123/static-page-view.html" in raw_page_warc_gz
        assert "GET /replay/msn/ar-AA123/static-page-view.html HTTP/1.1" in raw_page_warc_gz
        assert "HTTP/1.1 200 OK" in raw_page_warc_gz
        assert "Content-Type: text/html; charset=utf-8" in raw_page_warc_gz
        assert "REPLAY_VISUALLY_VERIFIED" not in raw_page_warc_gz
        text_html = text_html_path.read_text(encoding="utf-8")
        assert "<details open>" in text_html
        assert "<summary>Comments evidence - not supplied</summary>" in text_html
        raw_text_warc_gz = gzip.decompress(text_warc_gz_path.read_bytes()).decode("utf-8", errors="replace")
        assert "GET /replay/msn/ar-AA123/static-text-view.html HTTP/1.1" in raw_text_warc_gz
        assert "HTTP/1.1 200 OK" in raw_text_warc_gz
        assert "Content-Type: text/html; charset=utf-8" in raw_text_warc_gz
        article_txt = article_txt_path.read_text(encoding="utf-8")
        comments_txt = comments_txt_path.read_text(encoding="utf-8")
        page_text_md = page_text_md_path.read_text(encoding="utf-8")
        assert "<" not in article_txt
        assert ">" not in article_txt
        assert "Structured comment counts were supplied" not in article_txt
        assert "Comments evidence" in comments_txt
        assert page_text_md.startswith("# Static Page Text")


def test_repair_cli_refuses_in_place_static_evidence_output() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "archive.wacz"
        _legacy_fixture(source)

        exit_code = main(
            [
                "--input-wacz",
                str(source),
                "--output-wacz",
                str(source),
                "--add-static-evidence-page",
            ]
        )

        assert exit_code == 2


def run_self_test() -> None:
    test_repair_cli_defaults_to_replayweb_page_profile_and_preserves_input()
    test_repair_cli_can_write_strict_wacz12_profile()
    test_repair_cli_can_add_static_evidence_page_without_replacing_original_page()
    test_repair_cli_writes_standalone_static_outputs_for_wacz_lookup_fallback()
    test_repair_cli_refuses_in_place_static_evidence_output()


if __name__ == "__main__":
    run_self_test()
    print("source_local_web_archive_repair_cli.py: OK")
