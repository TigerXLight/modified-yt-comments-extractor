from __future__ import annotations

import json
import tempfile
from pathlib import Path

from jdownloader_internal_download_monitor import (
    build_download_manifest,
    classify_download_file,
    collect_completed_files,
    wait_for_download_completion,
    write_download_manifest,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


def test_classifies_files_and_writes_manifest_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        video = root / "clip.mp4"
        audio = root / "clip.m4a"
        metadata = root / "clip.info.json"
        part = root / "clip.mp4.part"
        video.write_bytes(b"video")
        audio.write_bytes(b"audio")
        metadata.write_text("{}", encoding="utf-8")
        part.write_bytes(b"unfinished")

        records = collect_completed_files(root)
        kinds = {record.kind for record in records}
        assert kinds == {"video", "audio", "metadata"}
        assert all(".part" not in record.path for record in records)
        assert classify_download_file("x.webp") == "image"

        manifest = build_download_manifest(
            source_url="https://youtu.be/example",
            output_dir=root,
            status="success",
            phase="completed",
            engine={
                "runtime_dir": "third_party/jdownloader/runtime/JDownloader 2",
                "pid": 123,
                "project_local_runtime": True,
                "external_appdata_used_as_primary": False,
                "cold_start_ms": 1,
                "warm_job": False,
            },
            timings={
                "engine_start_ms": 1,
                "job_submit_ms": 2,
                "link_resolution_ms": 3,
                "download_wait_ms": 4,
                "postprocess_import_ms": 5,
                "total_ms": 15,
            },
            files=records,
            submission_status="accepted_or_unknown",
            submission_attempts=(
                {
                    "route": "/flash/add",
                    "method": "POST",
                    "url": "http://127.0.0.1:9666/flash/add",
                    "parameters": ["urls", "package", "dir"],
                    "timeout_seconds": 1,
                    "http_status": 200,
                },
            ),
        )
        target = write_download_manifest(manifest, root / "jdownloader-internal-download-manifest.json")
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["backend_id"] == "jdownloader_internal"
        assert data["phase"] == "completed"
        assert data["engine"]["project_local_runtime"] is True
        assert data["engine"]["external_appdata_used_as_primary"] is False
        assert data["submission_status"] == "accepted_or_unknown"
        assert data["submission_attempts"][0]["route"] == "/flash/add"
        assert len(data["files"]) == 3


def test_wait_for_download_completion_success_and_timeout() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "done.mp4").write_bytes(b"done")
        clock = FakeClock()
        success = wait_for_download_completion(
            root,
            timeout_seconds=5,
            poll_interval_seconds=1,
            stable_checks_required=1,
            clock=clock,
            sleeper=clock.sleep,
        )
        assert success.status == "success"
        assert success.files[0].kind == "video"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "active.mp4.part").write_bytes(b"partial")
        clock = FakeClock()
        timeout = wait_for_download_completion(
            root,
            timeout_seconds=2,
            poll_interval_seconds=1,
            stable_checks_required=1,
            clock=clock,
            sleeper=clock.sleep,
        )
        assert timeout.status == "timeout"
        assert "No completed files" in timeout.errors[0]


def main() -> None:
    test_classifies_files_and_writes_manifest_shape()
    test_wait_for_download_completion_success_and_timeout()
    print("jdownloader_internal_download_monitor_test OK")


if __name__ == "__main__":
    main()
