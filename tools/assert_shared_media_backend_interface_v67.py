from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_youtube_queue_uses_shared_media_backend() -> None:
    source = (ROOT / "youtube_gui_media_queue.py").read_text(encoding="utf-8")
    assert "from shared_media_backend import" in source
    assert "build_shared_jdownloader_media_request" in source
    assert "run_shared_jdownloader_media_backend" in source
    assert "from jdownloader_internal_job import" not in source
    assert "build_youtube_job_request(" not in source
    assert "run_internal_youtube_job" not in source
    assert "build_internal_youtube_download_command" not in source


def test_source_adapters_do_not_import_jdownloader_internals() -> None:
    source = (ROOT / "source_adapters.py").read_text(encoding="utf-8")
    assert "jdownloader_internal_" not in source
    assert "run_shared_jdownloader_media_backend" not in source


def test_shared_backend_module_documents_adapter_backend_boundary() -> None:
    source = (ROOT / "shared_media_backend.py").read_text(encoding="utf-8")
    assert "source_adapter_declares_shared_backend_executes" in source
    assert "Source adapters describe what media they want" in source
    assert "run_shared_jdownloader_media_backend" in source


def main() -> None:
    test_youtube_queue_uses_shared_media_backend()
    test_source_adapters_do_not_import_jdownloader_internals()
    test_shared_backend_module_documents_adapter_backend_boundary()
    print("assert_shared_media_backend_interface_v67 OK")


if __name__ == "__main__":
    main()
