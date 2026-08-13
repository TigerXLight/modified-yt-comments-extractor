from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = (root / "youtube_media_download_backend.py").read_text(encoding="utf-8")
cli = (root / "youtube_media_download_backend_cli.py").read_text(encoding="utf-8")
test = (root / "youtube_media_download_backend_test.py").read_text(encoding="utf-8")

assert "def youtube_metadata_text_from_discovery(" in backend
assert "def write_youtube_media_metadata_text(" in backend
assert "Title: {discovery.title}" in backend
assert "Subscribers:" in backend
assert "Description: " in backend
assert "Source: " in backend
assert "write_youtube_media_metadata_text(discovery, metadata_text_path)" in cli
assert 'YOUTUBE_MEDIA_METADATA_TEXT=' in cli
assert "YOUTUBE_MEDIA_SOURCE_URL_INPUT=" in cli
assert "test_youtube_metadata_text_sidecar_matches_project_export_shape" in test
print("YOUTUBE_METADATA_TXT_OUTPUT_FIX_V21_STATIC_CHECK_OK")
