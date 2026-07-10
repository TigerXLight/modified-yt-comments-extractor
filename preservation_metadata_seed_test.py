import json
from pathlib import Path

from total_export_local_media import build_local_media_record
from total_export_manual_archive import build_manual_archive_record
from total_export_preservation_plan import (
    build_preservation_plan,
    build_preservation_plan_markdown,
    build_preservation_plan_text,
    preservation_plan_to_dict,
)
from total_export_preservation_plan_cli import build_plan_from_input_data


SEED_PATH = Path("PRESERVATION_METADATA_SEED.json")
CANONICAL_URL = "https://www.youtube.com/watch?v=aB3_dE-9xYz"


def _load_seed() -> dict[str, object]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _manual_archive_records(seed: dict[str, object]):
    records = []
    for item in seed["manual_archive_records"]:
        records.append(
            build_manual_archive_record(
                source_url=item.get("source_url", ""),
                normalized_url=item.get("normalized_url", ""),
                archive_url=item.get("archive_url", ""),
                archive_service_name=item.get("archive_service_name", ""),
                archive_capture_time=item.get("archive_capture_time", ""),
                archive_status=item.get("archive_status", ""),
                archive_notes=item.get("archive_notes", ""),
                entered_at_utc=item.get("entered_at_utc", ""),
                verified_by_user_at_utc=item.get("verified_by_user_at_utc", ""),
            )
        )
    return tuple(records)


def _local_media_records(seed: dict[str, object]):
    records = []
    for item in seed["local_media_records"]:
        records.append(
            build_local_media_record(
                source_url=item.get("source_url", ""),
                normalized_url=item.get("normalized_url", ""),
                package_id=item.get("package_id", ""),
                local_media_path=item.get("local_media_path", ""),
                local_media_filename=item.get("local_media_filename", ""),
                local_file_size_bytes=item.get("local_file_size_bytes", 0),
                local_file_sha256=item.get("local_file_sha256", ""),
                media_type=item.get("media_type", ""),
                duration_seconds=item.get("duration_seconds"),
                media_notes=item.get("media_notes", ""),
                registered_at_utc=item.get("registered_at_utc", ""),
                verified_at_utc=item.get("verified_at_utc", ""),
                exists_at_registration=item.get("exists_at_registration"),
                hash_algorithm=item.get("hash_algorithm", ""),
                status=item.get("status", ""),
                compute_hash=False,
                inspect_local_file=False,
            )
        )
    return tuple(records)


def run_self_test() -> None:
    seed = _load_seed()
    assert set(seed) == {
        "metadata",
        "source_urls",
        "manual_archive_records",
        "local_media_records",
    }
    metadata = seed["metadata"]
    assert metadata["schema"] == "local_preservation_metadata_seed"
    assert metadata["version"] == 1
    assert metadata["local_only"] is True
    assert "No archive checks" in " ".join(metadata["notes"])

    source_urls = tuple(seed["source_urls"])
    assert CANONICAL_URL in source_urls
    assert "https://example.com/story-with-archive-only" in source_urls
    assert "https://example.com/story-with-media-only" in source_urls
    assert "https://example.com/story-manual-archive-not-found" in source_urls
    assert "https://example.com/story-missing-local-file" in source_urls

    manual_records = _manual_archive_records(seed)
    assert len(manual_records) == 3
    assert manual_records[0].normalized_url == CANONICAL_URL
    assert manual_records[0].archive_status == "manually_supplied"
    assert manual_records[2].archive_status == "manually_checked_not_found"

    media_records = _local_media_records(seed)
    assert len(media_records) == 3
    assert media_records[0].normalized_url == CANONICAL_URL
    assert media_records[0].local_file_size_bytes == 12345
    assert media_records[0].local_file_sha256 == "0" * 64
    assert media_records[0].exists_at_registration is True
    assert media_records[2].status == "missing_local_file"
    assert media_records[2].exists_at_registration is False

    plan = build_preservation_plan(
        source_urls=source_urls,
        manual_archive_records=manual_records,
        local_media_records=media_records,
    )
    assert plan.source_count == 5
    assert plan.sources_with_archive_count == 3
    assert plan.sources_missing_archive_count == 2
    assert plan.sources_with_local_media_count == 3
    assert plan.sources_missing_local_media_count == 2
    assert plan.sources_needing_follow_up_count == 4

    text = build_preservation_plan_text(plan)
    assert "Local preservation plan report" in text
    assert "Sources needing follow-up: 4" in text
    assert "No automatic archive checks or downloads are performed." in text

    markdown = build_preservation_plan_markdown(plan)
    assert "# Local Preservation Plan Report" in markdown
    assert "| Source URL | Archive records | Archive statuses | Archive follow-up | Local media records | Local media statuses | Local media follow-up | Recommended actions |" in markdown
    assert "Missing metadata means unknown" in markdown

    as_dict = preservation_plan_to_dict(plan)
    assert list(as_dict) == [
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
    assert as_dict["items"][0]["normalized_url"] == CANONICAL_URL

    cli_plan = build_plan_from_input_data(seed)
    assert cli_plan.source_count == plan.source_count
    assert cli_plan.sources_needing_follow_up_count == plan.sources_needing_follow_up_count
    assert cli_plan.items[0].normalized_url == CANONICAL_URL

    docs = Path("PRESERVATION_METADATA_SEED.md").read_text(encoding="utf-8")
    assert "example data only" in docs
    assert "does not fetch sources" in docs
    assert "No archive checks/submission" in docs


if __name__ == "__main__":
    run_self_test()
    print("Preservation metadata seed self-test passed.")
