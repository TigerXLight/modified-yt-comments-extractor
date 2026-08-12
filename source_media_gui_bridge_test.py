from __future__ import annotations

import hashlib
import http.server
import json
import socketserver
import tempfile
import threading
from pathlib import Path

from source_media_gui_bridge import (
    MEDIA_GUI_DOWNLOAD_STATUS_READY,
    MEDIA_GUI_DOWNLOAD_STATUS_UNSUPPORTED,
    run_source_media_gui_download,
    selected_direct_hostnames_from_plan,
    source_media_gui_download_result_to_json,
)
from source_resource_state import (
    RESOURCE_KIND_IMAGE,
    build_source_resource_row,
    clear_resource_selection,
    resource_dialog_state_for_row,
    select_all_resources,
)
from source_msn_adapter_media_download_cli import write_msn_media_download_plan


MSN_URL = "https://www.msn.com/en-gb/news/example/ar-AAexample"


class _ThreadedServer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.httpd: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None
        self.url = ""

    def __enter__(self) -> "_ThreadedServer":
        root = self.root

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
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


def _write_fixture_html(root: Path, media_url: str) -> Path:
    html_path = root / "rendered-page.html"
    html_path.write_text(
        "\n".join(
            [
                "<html><head>",
                "<meta property='og:title' content='MSN media GUI bridge fixture'>",
                "<meta property='og:site_name' content='The Independent'>",
                f"<meta property='og:image' content='{media_url}/hero.jpg'>",
                "</head><body><h1>MSN media GUI bridge fixture</h1>",
                "<p>Long enough article body text for extraction and validation.</p></body></html>",
            ]
        ),
        encoding="utf-8",
    )
    return html_path


def test_source_media_gui_bridge_requires_rendered_html_before_execution() -> None:
    row = build_source_resource_row(MSN_URL)
    state = clear_resource_selection(resource_dialog_state_for_row(row, RESOURCE_KIND_IMAGE))

    with tempfile.TemporaryDirectory() as tmp:
        result = run_source_media_gui_download(row=row, state=state, output_dir=tmp)

    assert result.status != MEDIA_GUI_DOWNLOAD_STATUS_READY
    assert "rendered MSN article HTML" in result.message
    assert result.resources_downloaded == 0


def test_source_media_gui_bridge_reports_non_msn_rows_as_unsupported() -> None:
    row = build_source_resource_row("https://www.youtube.com/watch?v=aB3_dE-9xYz")
    state = select_all_resources(resource_dialog_state_for_row(row, RESOURCE_KIND_IMAGE))

    with tempfile.TemporaryDirectory() as tmp:
        result = run_source_media_gui_download(row=row, state=state, output_dir=tmp)

    assert result.status == MEDIA_GUI_DOWNLOAD_STATUS_UNSUPPORTED
    assert "MSN rows only" in result.message


def test_source_media_gui_bridge_reports_non_msn_empty_rows_as_unsupported() -> None:
    row = build_source_resource_row("https://www.youtube.com/watch?v=aB3_dE-9xYz")
    state = clear_resource_selection(resource_dialog_state_for_row(row, RESOURCE_KIND_IMAGE))

    with tempfile.TemporaryDirectory() as tmp:
        result = run_source_media_gui_download(row=row, state=state, output_dir=tmp)

    assert result.status == MEDIA_GUI_DOWNLOAD_STATUS_UNSUPPORTED
    assert result.adapter_id != "msn"


def test_source_media_gui_bridge_runs_msn_review_and_selected_download() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        served = root / "served"
        served.mkdir()
        payload = b"msn gui bridge image bytes"
        (served / "hero.jpg").write_bytes(payload)

        with _ThreadedServer(served) as server:
            html_path = _write_fixture_html(root, server.url)
            row = build_source_resource_row(MSN_URL)
            state = clear_resource_selection(resource_dialog_state_for_row(row, RESOURCE_KIND_IMAGE))
            review_dir = root / "review"
            review = run_source_media_gui_download(
                row=row,
                state=state,
                rendered_html_path=html_path,
                output_dir=review_dir,
                dry_run=True,
            )

            assert review.status == MEDIA_GUI_DOWNLOAD_STATUS_READY
            assert review.resources_selected == 1
            assert review.resources_downloaded == 0
            assert review.selected_direct_hostnames == ("127.0.0.1",)

            live_dir = root / "live"
            live = run_source_media_gui_download(
                row=row,
                state=state,
                rendered_html_path=html_path,
                output_dir=live_dir,
                allowed_hostnames=review.selected_direct_hostnames,
                dry_run=False,
            )

        assert live.status == MEDIA_GUI_DOWNLOAD_STATUS_READY
        assert live.resources_downloaded == 1
        assert Path(live.summary_markdown).is_file()
        results = json.loads(Path(live.download_results_json).read_text(encoding="utf-8"))["download_results"]
        success = [item for item in results if item["status"] == "SUCCESS"]
        assert success[0]["sha256"] == hashlib.sha256(payload).hexdigest()
        assert "resources_downloaded" in source_media_gui_download_result_to_json(live)


def test_selected_direct_hostnames_from_plan_filters_selected_downloadable_resources() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        served = root / "served"
        served.mkdir()
        (served / "hero.jpg").write_bytes(b"image")
        with _ThreadedServer(served) as server:
            html_path = _write_fixture_html(root, server.url)
            plan = write_msn_media_download_plan(
                rendered_html_path=html_path,
                source_url=MSN_URL,
                output_dir=root / "out",
                select_all_images=True,
                dry_run=True,
            )

    assert selected_direct_hostnames_from_plan(plan) == ("127.0.0.1",)


if __name__ == "__main__":
    test_source_media_gui_bridge_requires_rendered_html_before_execution()
    test_source_media_gui_bridge_reports_non_msn_rows_as_unsupported()
    test_source_media_gui_bridge_reports_non_msn_empty_rows_as_unsupported()
    test_source_media_gui_bridge_runs_msn_review_and_selected_download()
    test_selected_direct_hostnames_from_plan_filters_selected_downloadable_resources()
    print("source_media_gui_bridge_test OK")
