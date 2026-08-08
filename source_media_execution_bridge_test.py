from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from capture_media_download import build_media_component_record, build_separate_av_mux_plan
from source_media_execution_bridge import (
    MediaCollisionPolicy,
    MediaExecutionStatus,
    copy_selected_local_media_files,
    download_selected_media_resources_with_http_client,
    execute_ffmpeg_mux_plan,
    execute_yt_dlp_command,
    group_media_components_for_mux,
)


class SourceMediaExecutionBridgeTest(unittest.TestCase):
    def test_selected_local_media_copy_writes_hash_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source video.mp4"
            source.write_bytes(b"fixture-video")
            out = root / "out"
            queue = copy_selected_local_media_files(
                resources=(
                    {"resource_id": "video1", "path": str(source), "media_type": "video"},
                    {"resource_id": "skip", "path": str(source), "media_type": "video"},
                ),
                output_directory=out,
                selected_resource_ids=("video1",),
            )
            self.assertEqual(queue.status, MediaExecutionStatus.SUCCESS)
            self.assertEqual(len(queue.local_copy_receipts), 1)
            receipt = queue.local_copy_receipts[0]
            self.assertEqual(receipt.output_name, "source_video.mp4")
            self.assertTrue((out / receipt.output_name).is_file())
            self.assertEqual(receipt.size_bytes, len(b"fixture-video"))

    def test_collision_fail_is_reported_by_exception_before_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "media.mp4"
            source.write_bytes(b"one")
            out = root / "out"
            out.mkdir()
            (out / "media.mp4").write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                copy_selected_local_media_files(
                    resources=({"resource_id": "r1", "path": str(source), "media_type": "video"},),
                    output_directory=out,
                    selected_resource_ids=("r1",),
                    collision_policy=MediaCollisionPolicy.FAIL,
                )
            self.assertEqual((out / "media.mp4").read_bytes(), b"existing")

    def test_ffmpeg_mux_uses_injected_runner_only_when_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video = root / "video.mp4"
            audio = root / "audio.m4a"
            video.write_bytes(b"video")
            audio.write_bytes(b"audio")
            plan = build_separate_av_mux_plan(
                video_component=build_media_component_record(resource_id="v", role="video", path=str(video)),
                audio_component=build_media_component_record(resource_id="a", role="audio", path=str(audio)),
                output_path=str(root / "muxed.mp4"),
            )
            blocked = execute_ffmpeg_mux_plan(plan, approval_granted=False)
            self.assertEqual(blocked.status, MediaExecutionStatus.UNSUPPORTED)

            calls: list[list[str]] = []

            def runner(command, **kwargs):
                calls.append(command)
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            result = execute_ffmpeg_mux_plan(plan, runner=runner, approval_granted=True)
            self.assertEqual(result.status, MediaExecutionStatus.SUCCESS)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "ffmpeg")

    def test_subprocess_missing_and_timeout_are_classified(self) -> None:
        missing = execute_yt_dlp_command(
            command=("yt-dlp", "local-fixture://media"),
            runner=lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
            approval_granted=True,
        )
        self.assertEqual(missing.status, MediaExecutionStatus.DEPENDENCY_NOT_FOUND)

        timeout = execute_yt_dlp_command(
            command=("yt-dlp", "local-fixture://media"),
            runner=lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("yt-dlp", 1)),
            approval_granted=True,
            timeout_seconds=1,
        )
        self.assertEqual(timeout.status, MediaExecutionStatus.TIMEOUT)

    def test_dry_run_does_not_call_runner(self) -> None:
        called = False

        def runner(command, **kwargs):
            nonlocal called
            called = True
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        result = execute_yt_dlp_command(
            command=("yt-dlp", "local-fixture://media"),
            runner=runner,
            approval_granted=True,
            dry_run=True,
        )
        self.assertEqual(result.status, MediaExecutionStatus.DRY_RUN)
        self.assertFalse(called)

    def test_http_downloader_injection_allows_localhost_and_refuses_external_blob(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            receipts = download_selected_media_resources_with_http_client(
                resources=(
                    {"resource_id": "local", "url": "http://localhost/media.mp4", "media_type": "video"},
                    {"resource_id": "external", "url": "https://example.com/media.mp4", "media_type": "video"},
                    {"resource_id": "blob", "url": "blob:https://example.com/id", "media_type": "video"},
                ),
                output_directory=temp_dir,
                selected_resource_ids=("local", "external", "blob"),
                http_downloader=lambda url, timeout: b"payload",
            )
            by_id = {receipt.resource_id: receipt for receipt in receipts}
            self.assertEqual(by_id["local"].status, MediaExecutionStatus.SUCCESS)
            self.assertTrue((Path(temp_dir) / by_id["local"].output_name).is_file())
            self.assertEqual(by_id["external"].status, MediaExecutionStatus.UNSUPPORTED)
            self.assertEqual(by_id["blob"].status, MediaExecutionStatus.UNSUPPORTED)

    def test_http_download_timeout_cancel_and_track_grouping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cancelled = download_selected_media_resources_with_http_client(
                resources=({"resource_id": "local", "url": "http://localhost/media.mp4"},),
                output_directory=temp_dir,
                selected_resource_ids=("local",),
                http_downloader=lambda url, timeout: b"",
                cancel_requested=True,
            )
            self.assertEqual(cancelled[0].status, MediaExecutionStatus.CANCELLED)
            timeout = download_selected_media_resources_with_http_client(
                resources=({"resource_id": "local", "url": "http://localhost/media.mp4"},),
                output_directory=temp_dir,
                selected_resource_ids=("local",),
                http_downloader=lambda url, timeout: (_ for _ in ()).throw(TimeoutError()),
            )
            self.assertEqual(timeout[0].status, MediaExecutionStatus.TIMEOUT)
            grouping = group_media_components_for_mux(
                (
                    build_media_component_record(resource_id="v", role="video", path=""),
                    build_media_component_record(resource_id="a", role="audio", path=""),
                    build_media_component_record(resource_id="s", role="subtitle", path=""),
                )
            )
            self.assertEqual(grouping.video_count, 1)
            self.assertEqual(grouping.audio_count, 1)
            self.assertEqual(grouping.to_dict()["other_count"], 1)

    def test_media_command_cancel_does_not_call_runner(self) -> None:
        called = False

        def runner(command, **kwargs):
            nonlocal called
            called = True
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        result = execute_yt_dlp_command(
            command=("yt-dlp", "http://localhost/media"),
            runner=runner,
            approval_granted=True,
            cancel_requested=True,
        )
        self.assertEqual(result.status, MediaExecutionStatus.CANCELLED)
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
