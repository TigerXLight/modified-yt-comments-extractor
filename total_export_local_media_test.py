import hashlib
import tempfile
from pathlib import Path

from total_export_local_media import (
    LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_STATUS_NEEDS_REVIEW,
    LOCAL_MEDIA_STATUS_REGISTERED,
    LOCAL_MEDIA_TYPE_AUDIO,
    LOCAL_MEDIA_TYPE_IMAGE,
    LOCAL_MEDIA_TYPE_UNKNOWN,
    LOCAL_MEDIA_TYPE_VIDEO,
    build_local_media_record,
    build_local_media_report_markdown,
    build_local_media_report_text,
    detect_local_media_type,
    local_media_record_to_dict,
    local_media_records_to_dict,
    normalize_local_media_status,
    sha256_file,
)


def run_self_test() -> None:
    assert detect_local_media_type("clip.mp4") == LOCAL_MEDIA_TYPE_VIDEO
    assert detect_local_media_type("clip.MKV") == LOCAL_MEDIA_TYPE_VIDEO
    assert detect_local_media_type("audio.wav") == LOCAL_MEDIA_TYPE_AUDIO
    assert detect_local_media_type("track.FLAC") == LOCAL_MEDIA_TYPE_AUDIO
    assert detect_local_media_type("image.jpeg") == LOCAL_MEDIA_TYPE_IMAGE
    assert detect_local_media_type("image.WEBP") == LOCAL_MEDIA_TYPE_IMAGE
    assert detect_local_media_type("notes.txt") == LOCAL_MEDIA_TYPE_UNKNOWN
    assert detect_local_media_type("") == LOCAL_MEDIA_TYPE_UNKNOWN

    assert normalize_local_media_status(" registered ") == LOCAL_MEDIA_STATUS_REGISTERED
    assert normalize_local_media_status("missing-local-file") == LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE
    assert normalize_local_media_status("") == LOCAL_MEDIA_STATUS_NEEDS_REVIEW
    assert normalize_local_media_status("not a real status") == LOCAL_MEDIA_STATUS_NEEDS_REVIEW

    with tempfile.TemporaryDirectory() as temp_dir:
        sample_bytes = b"sample local media bytes\n"
        media_path = Path(temp_dir) / "sample_clip.mp4"
        media_path.write_bytes(sample_bytes)
        expected_hash = hashlib.sha256(sample_bytes).hexdigest()

        assert sha256_file(str(media_path)) == expected_hash

        record = build_local_media_record(
            source_url="https://youtu.be/aB3_dE-9xYz?t=30",
            package_id="sample package",
            local_media_path=str(media_path),
            duration_seconds=12.5,
            media_notes="User supplied this local file manually.",
            registered_at_utc="2026-07-10T10:00:00Z",
            compute_hash=True,
        )
        assert record.source_url == "https://youtu.be/aB3_dE-9xYz?t=30"
        assert record.normalized_url == "https://www.youtube.com/watch?v=aB3_dE-9xYz"
        assert record.package_id == "sample package"
        assert record.local_media_filename == "sample_clip.mp4"
        assert record.local_file_size_bytes == len(sample_bytes)
        assert record.local_file_sha256 == expected_hash
        assert record.media_type == LOCAL_MEDIA_TYPE_VIDEO
        assert record.duration_seconds == 12.5
        assert record.exists_at_registration is True
        assert record.status == LOCAL_MEDIA_STATUS_REGISTERED

        missing_path = Path(temp_dir) / "missing_audio.wav"
        missing = build_local_media_record(
            source_url="https://example.com/story",
            local_media_path=str(missing_path),
            media_notes="User expected to add this file later.",
            registered_at_utc="2026-07-10T11:00:00Z",
            compute_hash=True,
        )
        assert missing.normalized_url == "https://example.com/story"
        assert missing.local_media_filename == "missing_audio.wav"
        assert missing.local_file_size_bytes == 0
        assert missing.local_file_sha256 == ""
        assert missing.media_type == LOCAL_MEDIA_TYPE_AUDIO
        assert missing.exists_at_registration is False
        assert missing.status == LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE

        record_dict = local_media_record_to_dict(record)
        assert list(record_dict) == [
            "source_url",
            "normalized_url",
            "package_id",
            "local_media_path",
            "local_media_filename",
            "local_file_size_bytes",
            "local_file_sha256",
            "media_type",
            "duration_seconds",
            "media_notes",
            "registered_at_utc",
            "verified_at_utc",
            "exists_at_registration",
            "hash_algorithm",
            "status",
        ]

        records_dict = local_media_records_to_dict((record, missing))
        assert records_dict["record_count"] == 2
        assert records_dict["status_counts"][LOCAL_MEDIA_STATUS_REGISTERED] == 1
        assert records_dict["status_counts"][LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE] == 1
        assert records_dict["media_type_counts"][LOCAL_MEDIA_TYPE_VIDEO] == 1
        assert records_dict["media_type_counts"][LOCAL_MEDIA_TYPE_AUDIO] == 1
        assert "no media is downloaded or fetched" in records_dict["warning"]

        text = build_local_media_report_text((record, missing))
        assert "Local media registration metadata report" in text
        assert str(media_path) in text
        assert "registered" in text
        assert "missing_local_file" in text
        assert "extension/string-only" in text
        assert "not proof that a remote source is unavailable" in text

        markdown = build_local_media_report_markdown((record, missing))
        assert "# Local Media Registration Metadata Report" in markdown
        assert "| Source URL | Local path | Type | Status | Size bytes | SHA-256 | Notes |" in markdown
        assert expected_hash in markdown
        assert "does not download, fetch, probe media, or transcribe" in markdown

    assert sha256_file(str(Path(tempfile.gettempdir()) / "definitely_missing_media_file.mp4")) == ""


if __name__ == "__main__":
    run_self_test()
    print("Local media registration metadata self-test passed.")
