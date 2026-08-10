from __future__ import annotations

import hashlib
import http.server
import json
import socketserver
import tempfile
import threading
from pathlib import Path

from source_msn_adapter_media_download_cli import (
    MSN_MEDIA_DOWNLOAD_RESULTS_JSON,
    MSN_MEDIA_DOWNLOAD_SUMMARY_MD,
    write_msn_media_download_plan,
)


class _ThreadedServer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.httpd: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None
        self.url = ""

    def __enter__(self) -> "_ThreadedServer":
        root = self.root

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(root), **kwargs)

            def log_message(self, format, *args):  # noqa: A002, ANN001
                return

        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{port}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        assert self.httpd is not None
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)


def test_msn_media_download_plan_downloads_explicit_selected_images_and_records_streams() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        served = root / "served"
        served.mkdir()
        payload = b"fixture image bytes"
        (served / "hero.jpg").write_bytes(payload)
        (served / "clip.mp4").write_bytes(b"video bytes")
        with _ThreadedServer(served) as server:
            html_path = root / "rendered-page.html"
            html_path.write_text(
                "\n".join(
                    [
                        "<html><head>",
                        "<meta property='og:title' content='MSN reposted article'>",
                        "<meta property='og:site_name' content='The Independent'>",
                        f"<meta property='og:image' content='{server.url}/hero.jpg'>",
                        f"<meta property='og:video' content='{server.url}/clip.mp4'>",
                        f"<meta property='twitter:player:stream' content='{server.url}/stream.m3u8'>",
                        "</head><body><h1>MSN reposted article</h1><p>Long enough article body text for extraction and validation.</p></body></html>",
                    ]
                ),
                encoding="utf-8",
            )
            out = root / "media_out"
            dry = write_msn_media_download_plan(
                rendered_html_path=html_path,
                source_url="https://www.msn.com/en-gb/news/example/ar-AAexample",
                output_dir=out,
                select_all_images=True,
                allowed_hostnames=("127.0.0.1",),
                dry_run=True,
            )
            assert dry.counts["resources"] >= 3
            assert dry.counts["downloaded"] == 0
            live = write_msn_media_download_plan(
                rendered_html_path=html_path,
                source_url="https://www.msn.com/en-gb/news/example/ar-AAexample",
                output_dir=out,
                select_all_images=True,
                allowed_hostnames=("127.0.0.1",),
            )
            assert live.counts["downloaded"] == 1
            results_path = out / MSN_MEDIA_DOWNLOAD_RESULTS_JSON
            assert results_path.is_file()
            results = json.loads(results_path.read_text(encoding="utf-8"))["download_results"]
            success = [result for result in results if result["status"] == "SUCCESS"]
            assert len(success) == 1
            assert success[0]["sha256"] == hashlib.sha256(payload).hexdigest()
            assert Path(success[0]["output_path"]).is_file()
            assert (out / MSN_MEDIA_DOWNLOAD_SUMMARY_MD).read_text(encoding="utf-8").count("MSN Media Download") == 1
            assert any(result["status"] == "UNSUPPORTED" for result in results)


def run_tests() -> None:
    test_msn_media_download_plan_downloads_explicit_selected_images_and_records_streams()
    print("MSN media download CLI self-test passed.")


if __name__ == "__main__":
    run_tests()
