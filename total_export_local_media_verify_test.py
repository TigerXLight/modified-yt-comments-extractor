import hashlib
import tempfile
from pathlib import Path

from total_export_local_media import build_local_media_record
from total_export_local_media_verify import (
    LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW,
    LOCAL_MEDIA_VERIFY_STATUS_NOT_CHECKED,
    LOCAL_MEDIA_VERIFY_STATUS_SHA256_MISMATCH,
    LOCAL_MEDIA_VERIFY_STATUS_SIZE_MISMATCH,
    LOCAL_MEDIA_VERIFY_STATUS_VERIFIED,
    build_local_media_verification_markdown,
    build_local_media_verification_text,
    local_media_verification_result_to_dict,
    verify_local_media_record,
    verify_local_media_records,
)


def _record_for_path(
    path: Path,
    *,
    size: int = 0,
    sha256: str = "",
    package_id: str = "verification-package",
):
    return build_local_media_record(
        source_url="https://example.com/source",
        normalized_url="https://example.com/source",
        package_id=package_id,
        local_media_path=str(path),
        local_file_size_bytes=size,
        local_file_sha256=sha256,
        exists_at_registration=True,
        status="registered",
        inspect_local_file=False,
    )


def run_self_test() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        sample_bytes = b"sample local media verification bytes\n"
        media_path = temp_path / "sample_clip.mp4"
        media_path.write_bytes(sample_bytes)
        expected_hash = hashlib.sha256(sample_bytes).hexdigest()

        verified_record = _record_for_path(
            media_path,
            size=len(sample_bytes),
            sha256=expected_hash,
        )
        verified = verify_local_media_record(verified_record, compute_hash=True)
        assert verified.status == LOCAL_MEDIA_VERIFY_STATUS_VERIFIED
        assert verified.current_exists is True
        assert verified.recorded_size_bytes == len(sample_bytes)
        assert verified.current_size_bytes == len(sample_bytes)
        assert verified.recorded_sha256 == expected_hash
        assert verified.current_sha256 == expected_hash
        assert verified.size_matches is True
        assert verified.sha256_matches is True

        missing_record = _record_for_path(
            temp_path / "missing_clip.mp4",
            size=len(sample_bytes),
            sha256=expected_hash,
        )
        missing = verify_local_media_record(missing_record)
        assert missing.status == LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE
        assert missing.current_exists is False
        assert "Local media file was not found" in missing.warnings[0]

        size_mismatch_record = _record_for_path(
            media_path,
            size=len(sample_bytes) + 1,
            sha256=expected_hash,
        )
        size_mismatch = verify_local_media_record(size_mismatch_record)
        assert size_mismatch.status == LOCAL_MEDIA_VERIFY_STATUS_SIZE_MISMATCH
        assert size_mismatch.size_matches is False
        assert size_mismatch.sha256_matches is True

        sha_mismatch_record = _record_for_path(
            media_path,
            size=len(sample_bytes),
            sha256="0" * 64,
        )
        sha_mismatch = verify_local_media_record(sha_mismatch_record)
        assert sha_mismatch.status == LOCAL_MEDIA_VERIFY_STATUS_SHA256_MISMATCH
        assert sha_mismatch.size_matches is True
        assert sha_mismatch.sha256_matches is False

        hash_skipped = verify_local_media_record(verified_record, compute_hash=False)
        assert hash_skipped.status == LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW
        assert hash_skipped.current_sha256 == ""
        assert any("SHA-256 was not computed" in warning for warning in hash_skipped.warnings)

        blank_hash_record = _record_for_path(
            media_path,
            size=len(sample_bytes),
            sha256="",
        )
        blank_hash = verify_local_media_record(blank_hash_record, compute_hash=True)
        assert blank_hash.status == LOCAL_MEDIA_VERIFY_STATUS_NEEDS_REVIEW
        assert blank_hash.current_sha256 == expected_hash
        assert blank_hash.sha256_matches is False
        assert any("Recorded SHA-256 is blank" in warning for warning in blank_hash.warnings)

        blank_path_record = build_local_media_record(
            source_url="https://example.com/source",
            normalized_url="https://example.com/source",
            package_id="verification-package",
            local_media_path="",
            exists_at_registration=False,
            status="registered",
            inspect_local_file=False,
        )
        blank_path = verify_local_media_record(blank_path_record)
        assert blank_path.status == LOCAL_MEDIA_VERIFY_STATUS_NOT_CHECKED

        result = verify_local_media_records(
            (
                verified_record,
                missing_record,
                size_mismatch_record,
                sha_mismatch_record,
                blank_hash_record,
                blank_path_record,
            )
        )
        assert result.record_count == 6
        assert result.checked_count == 5
        assert result.missing_count == 1
        assert result.size_mismatch_count == 1
        assert result.sha256_mismatch_count == 1
        assert len(result.items) == 6

        result_dict = local_media_verification_result_to_dict(result)
        assert list(result_dict) == [
            "checked_count",
            "errors",
            "items",
            "missing_count",
            "record_count",
            "sha256_mismatch_count",
            "size_mismatch_count",
            "warnings",
        ]
        assert result_dict["items"][0]["status"] == LOCAL_MEDIA_VERIFY_STATUS_VERIFIED
        assert "does not download" in result_dict["warnings"][0]

        text = build_local_media_verification_text(result)
        assert "Local media verification report" in text
        assert "Record count: 6" in text
        assert "Missing local files: 1" in text
        assert "SHA-256 mismatches: 1" in text
        assert "no downloads, fetching" in text

        markdown = build_local_media_verification_markdown(result)
        assert "# Local Media Verification Report" in markdown
        assert "| Local path | Status | Current exists | Recorded size | Current size | Size match | SHA-256 match | Warnings |" in markdown
        assert "not proof that a remote source is unavailable" in markdown
        assert "No downloading, archive checking, scraping" in markdown


if __name__ == "__main__":
    run_self_test()
    print("Local media verification self-test passed.")
