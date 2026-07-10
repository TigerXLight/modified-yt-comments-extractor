from total_export_manual_archive import (
    ARCHIVE_SERVICE_ARCHIVE_TODAY,
    ARCHIVE_SERVICE_INTERNET_ARCHIVE,
    ARCHIVE_SERVICE_UNKNOWN,
    ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED,
    ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND,
    ARCHIVE_STATUS_MANUALLY_SUPPLIED,
    ARCHIVE_STATUS_NOT_CHECKED,
    build_manual_archive_record,
    build_manual_archive_report_markdown,
    build_manual_archive_report_text,
    detect_archive_service_name,
    manual_archive_record_to_dict,
    manual_archive_records_to_dict,
    normalize_manual_archive_status,
)


def run_self_test() -> None:
    assert detect_archive_service_name("https://web.archive.org/web/20260710000000/https://example.com") == ARCHIVE_SERVICE_INTERNET_ARCHIVE
    assert detect_archive_service_name("https://archive.org/details/example") == ARCHIVE_SERVICE_INTERNET_ARCHIVE
    assert detect_archive_service_name("https://archive.ph/abc12") == ARCHIVE_SERVICE_ARCHIVE_TODAY
    assert detect_archive_service_name("https://archive.today/abc12") == ARCHIVE_SERVICE_ARCHIVE_TODAY
    assert detect_archive_service_name("https://example.com/archive") == ARCHIVE_SERVICE_UNKNOWN
    assert detect_archive_service_name("") == ARCHIVE_SERVICE_UNKNOWN

    assert normalize_manual_archive_status(" manually supplied ") == ARCHIVE_STATUS_MANUALLY_SUPPLIED
    assert normalize_manual_archive_status("manually-checked-not-found") == ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND
    assert normalize_manual_archive_status("") == ARCHIVE_STATUS_NOT_CHECKED
    assert normalize_manual_archive_status("not a real status") == ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED

    youtube_record = build_manual_archive_record(
        source_url="https://youtu.be/aB3_dE-9xYz?t=30",
        archive_url="https://web.archive.org/web/20260710000000/https://www.youtube.com/watch?v=aB3_dE-9xYz",
        archive_notes="User pasted this archive URL manually.",
        entered_at_utc="2026-07-10T10:00:00Z",
    )
    assert youtube_record.source_url == "https://youtu.be/aB3_dE-9xYz?t=30"
    assert youtube_record.normalized_url == "https://www.youtube.com/watch?v=aB3_dE-9xYz"
    assert youtube_record.archive_service_name == ARCHIVE_SERVICE_INTERNET_ARCHIVE
    assert youtube_record.archive_status == ARCHIVE_STATUS_MANUALLY_SUPPLIED
    assert youtube_record.entered_at_utc == "2026-07-10T10:00:00Z"

    missing_record = build_manual_archive_record(
        source_url="https://example.com/story",
        archive_status="manual follow up needed",
        archive_notes="User has not supplied an archive URL yet.",
        entered_at_utc="2026-07-10T11:00:00Z",
    )
    assert missing_record.normalized_url == "https://example.com/story"
    assert missing_record.archive_url == ""
    assert missing_record.archive_status == ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED

    not_found_record = build_manual_archive_record(
        source_url="https://example.com/older-story",
        archive_status=ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND,
        archive_notes="User says they manually checked and did not find an archive.",
        entered_at_utc="2026-07-10T12:00:00Z",
    )
    assert not_found_record.archive_status == ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND

    record_dict = manual_archive_record_to_dict(youtube_record)
    assert list(record_dict) == [
        "source_url",
        "normalized_url",
        "archive_url",
        "archive_service_name",
        "archive_capture_time",
        "archive_status",
        "archive_notes",
        "entered_at_utc",
        "verified_by_user_at_utc",
    ]
    assert record_dict["archive_url"].startswith("https://web.archive.org/")

    records_dict = manual_archive_records_to_dict((youtube_record, missing_record, not_found_record))
    assert records_dict["record_count"] == 3
    assert records_dict["status_counts"][ARCHIVE_STATUS_MANUALLY_SUPPLIED] == 1
    assert records_dict["status_counts"][ARCHIVE_STATUS_MANUAL_FOLLOW_UP_NEEDED] == 1
    assert records_dict["status_counts"][ARCHIVE_STATUS_MANUALLY_CHECKED_NOT_FOUND] == 1
    assert "no archive services are checked" in records_dict["warning"]

    text = build_manual_archive_report_text((youtube_record, missing_record, not_found_record))
    assert "Manual archive URL metadata report" in text
    assert "internet_archive" in text
    assert "manual_follow_up_needed" in text
    assert "Missing archive metadata is unknown" in text
    assert "local/user-entered notes" in text

    markdown = build_manual_archive_report_markdown((youtube_record, missing_record, not_found_record))
    assert "# Manual Archive URL Metadata Report" in markdown
    assert "| Source URL | Archive URL | Service | Status | User verified at | Notes |" in markdown
    assert "not proof that no archive exists" in markdown
    assert "not external service results" in markdown


if __name__ == "__main__":
    run_self_test()
    print("Manual archive URL metadata self-test passed.")
