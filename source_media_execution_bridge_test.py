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
    execute_ffmpeg_mux_plan,
    execute_yt_dlp_command,
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


if __name__ == "__main__":
    unittest.main()

