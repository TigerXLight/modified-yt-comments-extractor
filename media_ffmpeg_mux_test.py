from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from media_ffmpeg_mux import FFmpegMuxRequest, build_ffmpeg_mux_command, mux_audio_video


def _fake_runner(command):
    if tuple(command)[1:] == ("-version",):
        return subprocess.CompletedProcess(command, 0, stdout="ffmpeg version test\n", stderr="")
    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def test_build_ffmpeg_mux_command_uses_part_output_and_template() -> None:
    req = FFmpegMuxRequest(
        video_path="video.mp4",
        audio_path="audio.m4a",
        output_path="merged.mp4",
        command_template=("-i", "%video", "-i", "%audio", "-f", "mp4", "%out", "-y"),
    )
    cmd = build_ffmpeg_mux_command(req)
    assert cmd[0] == "ffmpeg"
    assert "video.mp4" in cmd
    assert "audio.m4a" in cmd
    assert "merged.part.mp4" in cmd


def test_mux_audio_video_dry_run_records_hashes_and_version() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        video = root / "video.mp4"
        audio = root / "audio.m4a"
        video.write_bytes(b"video")
        audio.write_bytes(b"audio")
        result = mux_audio_video(
            FFmpegMuxRequest(
                video_path=str(video),
                audio_path=str(audio),
                output_path=str(root / "out.mp4"),
                execute=False,
            ),
            runner=_fake_runner,
        )
        assert result.status == "planned"
        assert result.video_sha256
        assert result.audio_sha256
        assert result.ffmpeg_version == "ffmpeg version test"
        assert result.execute is False


if __name__ == "__main__":
    test_build_ffmpeg_mux_command_uses_part_output_and_template()
    test_mux_audio_video_dry_run_records_hashes_and_version()
    print("media_ffmpeg_mux_test OK")
