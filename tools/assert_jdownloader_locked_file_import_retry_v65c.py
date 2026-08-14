from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import jdownloader_internal_download_monitor as monitor


def test_monitor_source_handles_locked_jd_files() -> None:
    source = (ROOT / "jdownloader_internal_download_monitor.py").read_text(encoding="utf-8")
    assert "_scan_completed_files" in source
    assert "_is_transient_download_file_access_error" in source
    assert "PermissionError" in source
    assert "locked_paths" in source
    assert "still locked by JDownloader" in source
    assert '".dashaudio"' in source
    assert '".dashvideo"' in source


def test_collect_completed_files_skips_transient_locked_file() -> None:
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="ytce_v65c_locked_scan_"))
    ok = tmp / "ok.mp4"
    locked = tmp / "locked.dashAudio"
    ok.write_bytes(b"ok-video")
    locked.write_bytes(b"locked-audio")

    original_sha = monitor.sha256_file

    def fake_sha(path):
        if Path(path).name == "locked.dashAudio":
            raise PermissionError(13, "Permission denied", str(path))
        return original_sha(path)

    monitor.sha256_file = fake_sha
    try:
        records = monitor.collect_completed_files(tmp)
    finally:
        monitor.sha256_file = original_sha

    assert [Path(record.path).name for record in records] == ["ok.mp4"]


def main() -> None:
    test_monitor_source_handles_locked_jd_files()
    test_collect_completed_files_skips_transient_locked_file()
    print("assert_jdownloader_locked_file_import_retry_v65c OK")


if __name__ == "__main__":
    main()
