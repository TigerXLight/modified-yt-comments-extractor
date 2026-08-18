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


def test_manifest_normalizes_api3128_route_identity_and_keeps_ytdlp_as_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = build_download_manifest(
            source_url="https://youtu.be/example",
            output_dir=root,
            status="success",
            phase="completed",
            engine={"status": "READY", "project_local_runtime": True, "external_appdata_used_as_primary": False},
            timings={},
            files=(),
            route_metadata={
                "api3128_enabled": True,
                "api3128_used": True,
                "api3128_package_complete_ms": 2297,
                "api3128_first_running_ms": 2311,
                "api3128_finished_ms": 3312,
                "flashgot_fallback_used": False,
                "route_used": "api3128",
            },
        )
        target = write_download_manifest(manifest, root / "jdownloader-internal-download-manifest.json")
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["route_used"] == "api3128"
        assert data["api3128_used"] is True
        assert data["flashgot_fallback_used"] is False
        assert data["route_label"].startswith("JDownloader API3128")
        assert data["yt_dlp_used"] is False
        assert data["yt_dlp_role"] == "fallback_only_after_jdownloader_routes"
        assert data["route_metadata"]["route_preference"] == "jdownloader_internal_api3128_preferred_before_yt_dlp"


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



def test_collect_completed_files_skips_temporarily_locked_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ok = root / "video.mp4"
        locked = root / "audio.dashAudio"
        ok.write_bytes(b"video")
        locked.write_bytes(b"audio")

        import jdownloader_internal_download_monitor as monitor_module

        original_sha = monitor_module.sha256_file

        def fake_sha(path):
            if Path(path).name == "audio.dashAudio":
                raise PermissionError(13, "Permission denied", str(path))
            return original_sha(path)

        try:
            monitor_module.sha256_file = fake_sha
            records = collect_completed_files(root)
        finally:
            monitor_module.sha256_file = original_sha

        assert len(records) == 1
        assert records[0].kind == "video"
        assert Path(records[0].path).name == "video.mp4"


def test_dash_audio_and_video_extensions_are_classified() -> None:
    assert classify_download_file("sample.dashAudio") == "audio"
    assert classify_download_file("sample.dashVideo") == "video"


def main() -> None:
    test_classifies_files_and_writes_manifest_shape()
    test_manifest_normalizes_api3128_route_identity_and_keeps_ytdlp_as_fallback()
    test_wait_for_download_completion_success_and_timeout()
    test_collect_completed_files_skips_temporarily_locked_files()
    test_dash_audio_and_video_extensions_are_classified()
    print("jdownloader_internal_download_monitor_test OK")


if __name__ == "__main__":
    main()
