from __future__ import annotations

import tempfile
from pathlib import Path

from source_local_webpage_viewer import LOCAL_VIEWER_READY, write_local_webpage_viewer


SOURCE_URL = (
    "https://www.msn.com"
    "/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"
    "?ocid=edgemobile&PC=EMMX01#comments"
)


def _write(path: Path, text: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")


def test_local_viewer_writes_index_scripts_and_relative_links() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "rendered-page.html", "<html><body>Article</body></html>")
        _write(root / "rendered-page.warc.gz", b"warc-gz")
        _write(root / "archive.viewable-live-capture.wacz", b"wacz")
        _write(root / "validation.json", '{"status":"manual_review_required"}')
        _write(root / "capture-manifest.json", "{}")
        _write(root / "screenshots" / "article-top.png", b"png")
        _write(root / "screenshots" / "full-page.png", b"png")
        _write(root / "screenshots" / "comments-region.png", b"png")

        result = write_local_webpage_viewer(capture_output_dir=root, source_url=SOURCE_URL)

        assert result.status == LOCAL_VIEWER_READY
        assert Path(result.index_path).is_file()
        assert Path(result.manifest_path).is_file()
        assert Path(result.open_cmd_path).is_file()
        assert Path(result.edge_app_cmd_path).is_file()
        html = Path(result.index_path).read_text(encoding="utf-8")
        lowered = html.lower()
        assert "<script" not in lowered
        assert "<iframe" not in lowered
        assert "http://fonts." not in lowered
        assert "https://fonts." not in lowered
        assert "<details open>" in lowered
        assert "<summary>replayweb files</summary>" in lowered
        assert "../rendered-page.html" in html
        assert "../rendered-page.warc.gz" in html
        assert "../archive.viewable-live-capture.wacz" in html
        assert "../screenshots/article-top.png" in html
        assert str(root) not in html


def test_local_viewer_handles_missing_optional_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "validation.json", '{"status":"blocked"}')

        result = write_local_webpage_viewer(capture_output_dir=root, source_url=SOURCE_URL)

        assert Path(result.index_path).is_file()
        html = Path(result.index_path).read_text(encoding="utf-8")
        assert "Local MSN Capture Viewer" in html
        assert "../validation.json" in html
        assert "../rendered-page.html" not in html


def run_self_test() -> None:
    test_local_viewer_writes_index_scripts_and_relative_links()
    test_local_viewer_handles_missing_optional_files()


if __name__ == "__main__":
    run_self_test()
    print("source_local_webpage_viewer.py: OK")
