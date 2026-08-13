from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = (root / "youtube_media_download_backend.py").read_text(encoding="utf-8")
cli = (root / "youtube_media_download_backend_cli.py").read_text(encoding="utf-8")
test = (root / "youtube_media_download_backend_test.py").read_text(encoding="utf-8")

assert "class ExternalCommandResolution" in backend
assert "def resolve_ytdlp_command" in backend
assert "importlib.util.find_spec(\"yt_dlp\")" in backend
assert "venv\\\\Scripts\\\\python.exe -m pip install -U yt-dlp" in backend
assert "*_command_prefix(yt_dlp_path)" in backend
assert "yt_dlp_path: str | Path | Sequence[str]" in backend
assert "resolve_ytdlp_command(args.yt_dlp" in cli
assert "YOUTUBE_MEDIA_YTDLP_NOT_FOUND=" in cli
assert "YOUTUBE_MEDIA_YTDLP_COMMAND=" in cli
assert "yt_dlp_path=yt_dlp_command" in cli
assert "test_build_youtube_ytdlp_download_plan_accepts_command_sequence" in test
print("YOUTUBE_YTDLP_RESOLVER_DOWNLOAD_FIX_V20_STATIC_CHECK_OK")
