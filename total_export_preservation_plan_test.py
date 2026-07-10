from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_local_media import (
    LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_STATUS_REGISTERED,
    build_local_media_record,
)
from total_export_manual_archive import (
    ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND,
    ARCHIVE_STATUS_MANUALLY_SUPPLIED,
    build_manual_archive_record,
)
from total_export_preservation_plan import (
    build_preservation_plan,
    build_preservation_plan_markdown,
    build_preservation_plan_text,
    preservation_plan_item_to_dict,
    preservation_plan_to_dict,
)


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def _item_by_url(plan, url: str):
    for item in plan.items:
        if item.normalized_url == url or item.source_url == url:
            return item
    raise AssertionError(f"Expected plan item for {url!r}")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        media_path = Path(temp_dir) / "clip.mp4"
        media_path.write_bytes(b"local preservation plan media bytes\n")

        complete_archive = build_manual_archive_record(
            source_url=f"https://youtu.be/{VALID_ID}?t=30",
            archive_url="https://web.archive.org/web/20260710000000/https://www.youtube.com/watch?v=aB3_dE-9xYz",
            archive_status=ARCHIVE_STATUS_MANUALLY_SUPPLIED,
            entered_at_utc="2026-07-10T10:00:00Z",
        )
        complete_media = build_local_media_record(
            source_url=CANONICAL_URL,
            package_id="complete package",
            local_media_path=str(media_path),
            registered_at_utc="2026-07-10T10:01:00Z",
            status=LOCAL_MEDIA_STATUS_REGISTERED,
            compute_hash=True,
        )

        missing_media_archive = build_manual_archive_record(
            source_url="https://example.com/story",
            archive_url="https://archive.ph/example",
            archive_status=ARCHIVE_STATUS_MANUALLY_SUPPLIED,
            entered_at_utc="2026-07-10T10:02:00Z",
        )
        missing_archive_media = build_local_media_record(
            source_url="https://example.com/clip",
            local_media_path=str(media_path),
            registered_at_utc="2026-07-10T10:03:00Z",
            status=LOCAL_MEDIA_STATUS_REGISTERED,
        )
        not_found_archive = build_manual_archive_record(
            source_url="https://example.com/not-found",
            archive_status=ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND,
            archive_notes="User manually checked and did not find an archive.",
            entered_at_utc="2026-07-10T10:04:00Z",
        )
        missing_local_media = build_local_media_record(
            source_url="https://example.com/missing-media",
            local_media_path=str(Path(temp_dir) / "missing.mp4"),
            registered_at_utc="2026-07-10T10:05:00Z",
            status=LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE,
        )

        plan = build_preservation_plan(
            source_urls=[
                f"https://youtu.be/{VALID_ID}?t=30",
                "https://example.com/story",
                "https://example.com/clip",
                "https://example.com/not-found",
                "https://example.com/missing-media",
            ],
            manual_archive_records=(complete_archive, missing_media_archive, not_found_archive),
            local_media_records=(complete_media, missing_archive_media, missing_local_media),
        )

        assert plan.source_count == 5
        assert plan.sources_with_archive_count == 3
        assert plan.sources_missing_archive_count == 2
        assert plan.sources_with_local_media_count == 3
        assert plan.sources_missing_local_media_count == 2
        assert plan.sources_needing_follow_up_count == 4

        complete = _item_by_url(plan, CANONICAL_URL)
        assert complete.archive_record_count == 1
        assert complete.local_media_record_count == 1
        assert complete.package_id == "complete package"
        assert complete.archive_statuses == (ARCHIVE_STATUS_MANUALLY_SUPPLIED,)
        assert complete.local_media_statuses == (LOCAL_MEDIA_STATUS_REGISTERED,)
        assert complete.needs_archive_follow_up is False
        assert complete.needs_local_media_follow_up is False
        assert complete.recommended_actions == ()

        missing_media = _item_by_url(plan, "https://example.com/story")
        assert missing_media.archive_record_count == 1
        assert missing_media.local_media_record_count == 0
        assert missing_media.needs_archive_follow_up is False
        assert missing_media.needs_local_media_follow_up is True
        assert "Register a local media file already saved on disk if available." in missing_media.recommended_actions

        missing_archive = _item_by_url(plan, "https://example.com/clip")
        assert missing_archive.archive_record_count == 0
        assert missing_archive.local_media_record_count == 1
        assert missing_archive.needs_archive_follow_up is True
        assert missing_archive.needs_local_media_follow_up is False
        assert "Add a manually supplied archive URL if one exists." in missing_archive.recommended_actions

        not_found = _item_by_url(plan, "https://example.com/not-found")
        assert not_found.needs_archive_follow_up is True
        assert ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND in not_found.archive_statuses
        assert "Review manually_checked_not_found archive status; absence is not proof." in not_found.recommended_actions

        missing_file = _item_by_url(plan, "https://example.com/missing-media")
        assert missing_file.needs_local_media_follow_up is True
        assert LOCAL_MEDIA_STATUS_MISSING_LOCAL_FILE in missing_file.local_media_statuses
        assert "Re-check local media path/hash." in missing_file.recommended_actions

        item_dict = preservation_plan_item_to_dict(complete)
        assert list(item_dict) == [
            "source_url",
            "normalized_url",
            "package_id",
            "archive_record_count",
            "local_media_record_count",
            "archive_statuses",
            "local_media_statuses",
            "needs_archive_follow_up",
            "needs_local_media_follow_up",
            "warnings",
            "recommended_actions",
        ]

        plan_dict = preservation_plan_to_dict(plan)
        assert list(plan_dict) == [
            "errors",
            "items",
            "source_count",
            "sources_missing_archive_count",
            "sources_missing_local_media_count",
            "sources_needing_follow_up_count",
            "sources_with_archive_count",
            "sources_with_local_media_count",
            "warnings",
        ]
        assert plan_dict["items"][0]["normalized_url"] == CANONICAL_URL
        assert "missing records are unknown" in plan_dict["warnings"][0]

        text = build_preservation_plan_text(plan)
        assert "Local preservation plan report" in text
        assert "Sources needing follow-up: 4" in text
        assert "No automatic archive checks or downloads are performed." in text
        assert "no archive checks, downloads, fetching, scraping" in text

        markdown = build_preservation_plan_markdown(plan)
        assert "# Local Preservation Plan Report" in markdown
        assert "| Source URL | Archive records | Archive statuses | Archive follow-up | Local media records | Local media statuses | Local media follow-up | Recommended actions |" in markdown
        assert "Missing metadata means unknown" in markdown
        assert "No automatic archive checks" in markdown

        inferred_sources = build_preservation_plan(
            manual_archive_records=(complete_archive,),
            local_media_records=(complete_media,),
        )
        assert inferred_sources.source_count == 1
        assert inferred_sources.items[0].normalized_url == CANONICAL_URL


if __name__ == "__main__":
    run_self_test()
    print("Local preservation plan self-test passed.")
