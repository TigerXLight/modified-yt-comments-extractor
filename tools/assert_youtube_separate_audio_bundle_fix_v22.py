from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = (root / "youtube_media_download_backend.py").read_text(encoding="utf-8")
cli = (root / "youtube_media_download_backend_cli.py").read_text(encoding="utf-8")
test = (root / "youtube_media_download_backend_test.py").read_text(encoding="utf-8")

assert "extra_commands: tuple[tuple[str, ...], ...] = ()" in backend
assert "separate_audio: bool = False" in backend
assert "bestaudio/best" in backend
assert "Separate bestaudio extraction is queued" in backend
assert "commands = (plan.command,) + tuple(plan.extra_commands or ())" in backend
assert "--no-separate-audio" in cli
assert "separate_audio=not args.no_separate_audio" in cli
assert "YOUTUBE_MEDIA_SEPARATE_AUDIO=" in cli
assert "YOUTUBE_MEDIA_EXTRA_COMMANDS=" in cli
assert "test_build_youtube_ytdlp_download_plan_can_queue_separate_audio" in test
assert "test_run_youtube_ytdlp_download_plan_runs_extra_audio_command" in test
print("YOUTUBE_SEPARATE_AUDIO_BUNDLE_FIX_V22_STATIC_CHECK_OK")
