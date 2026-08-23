from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_database_batch_import_assistant import validate_batch_json_file
from profile_media_source_package_preview import (
    WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_CONFIRMATION,
    build_profile_media_source_package_preview,
    normalise_source_package_artifact_kind,
    render_profile_media_source_package_preview_text,
    source_bucket_for_package_artifact_kind,
    source_package_preview_payload,
    write_profile_media_source_package_preview_json,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_metro_source_artifacts_build_importable_batch_payload() -> None:
    preview = build_profile_media_source_package_preview(
        database_root=r"T:\ProfileMediaHOME",
        case_title="Metro source evidence review",
        source_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        source_title="People shout seagull eater street far right lies",
        artifacts=[
            {
                "artifact_kind": "video",
                "display_name": "1024x576_MP4_6022863600552461299.mp4",
                "local_path": r"T:\Temp\session\1024x576_MP4_6022863600552461299.mp4",
                "width": 576,
                "height": 1024,
                "byte_size": 5300000,
                "reference_url": "https://videos.example.invalid/1024x576.mp4",
            },
            {
                "artifact_kind": "image",
                "display_name": "metro-image.webp",
                "local_path": r"T:\Temp\session\metro-image.webp",
                "width": 1200,
                "height": 675,
            },
            {
                "artifact_kind": "article_text",
                "display_name": "metro-article.txt",
                "local_path": r"T:\Temp\session\metro-article.txt",
            },
            {
                "artifact_kind": "screenshot",
                "display_name": "metro-page.png",
                "local_path": r"T:\Temp\session\metro-page.png",
            },
        ],
    )
    payload = preview.batch_payload
    _assert(preview.status == "preview_ready", preview.status)
    _assert(preview.artifact_count == 4, str(preview.artifact_count))
    _assert(preview.source_count == 5, str(preview.source_count))
    _assert(payload["schema_version"].startswith("profile-media-case-batch-"), payload["schema_version"])
    _assert(payload["case_title"] == "Metro source evidence review", payload["case_title"])
    _assert(len(payload["sources"]) == 5, str(payload["sources"]))
    _assert(payload["profiles"] == [], "V82A must not infer profiles")
    _assert(payload["source_package_preview"]["artifact_count"] == 4, str(payload["source_package_preview"]))
    _assert(payload["source_package_preview"]["temporary_local_paths_preserved"] is True, str(payload["source_package_preview"]))
    _assert(payload["source_package_preview"]["media_download_performed"] is False, "preview builder must not download")
    _assert(payload["source_package_preview"]["file_copy_performed"] is False, "preview builder must not copy")
    text = render_profile_media_source_package_preview_text(preview)
    _assert("Profiles: 0" in text, text)
    _assert("1024x576_MP4_6022863600552461299.mp4" in text, text)


def test_preview_json_write_is_confirmation_gated_and_import_validator_accepts_it() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "metro_profile_media_import.json"
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Metro source evidence review",
            source_url="https://metro.co.uk/example",
            source_title="Metro example",
            artifacts=[{"artifact_kind": "image", "display_name": "image.webp", "local_path": str(Path(tmp) / "image.webp")}],
        )
        blocked = write_profile_media_source_package_preview_json(preview, output, confirmation_phrase="WRONG")
        _assert(blocked.status == "blocked_confirmation_required", blocked.status)
        _assert(blocked.file_write_performed is False, "wrong confirmation should not write JSON")
        _assert(not output.exists(), "wrong confirmation wrote a file")

        written = write_profile_media_source_package_preview_json(
            preview,
            output,
            confirmation_phrase=WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_CONFIRMATION,
        )
        _assert(written.status == "written", written.status)
        _assert(written.file_write_performed is True, "confirmed write should report file write")
        data = json.loads(output.read_text(encoding="utf-8"))
        _assert(len(data["sources"]) == 2, str(data))
        validation = validate_batch_json_file(output)
        _assert(validation.status in {"accepted", "accepted_with_warnings"}, validation.status)
        _assert(validation.source_count == 2, str(validation.source_count))


def test_kind_and_bucket_mapping_are_review_conservative() -> None:
    _assert(normalise_source_package_artifact_kind("video", path="clip.mp4") == "video", "video kind failed")
    _assert(normalise_source_package_artifact_kind("", path="article.txt") == "article_text", "txt should map to article text")
    _assert(source_bucket_for_package_artifact_kind("article_text") == "Articles", "article bucket")
    _assert(source_bucket_for_package_artifact_kind("video") == "Reference Extants", "video should remain reference extant")
    _assert(source_bucket_for_package_artifact_kind("screenshot") == "Reference Extants", "screenshot should remain reference extant")


def test_payload_includes_text_without_mutation_flags() -> None:
    preview = build_profile_media_source_package_preview(
        case_title="Untitled source evidence",
        source_url="https://example.test/article",
        artifacts=[],
    )
    payload = source_package_preview_payload(preview, include_text=True)
    _assert("preview_text" in payload, str(payload.keys()))
    _assert(payload["folder_scan_performed"] is False, "no scan")
    _assert(payload["media_download_performed"] is False, "no download")
    _assert(payload["automatic_classification_performed"] is False, "no classification")
    _assert(payload["sensitive_identifier_inference_performed"] is False, "no sensitive inference")
    _assert(payload["batch_payload"]["profiles"] == [], "no inferred profiles")


if __name__ == "__main__":
    test_metro_source_artifacts_build_importable_batch_payload()
    test_preview_json_write_is_confirmation_gated_and_import_validator_accepts_it()
    test_kind_and_bucket_mapping_are_review_conservative()
    test_payload_includes_text_without_mutation_flags()
    print("profile_media_source_package_preview v82a OK")
